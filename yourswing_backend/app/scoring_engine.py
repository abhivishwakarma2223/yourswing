"""  # noqa: D400
ranking_engine.py
=================
Production-grade swing trading ranking engine.

Architecture
------------
  RankingEngine (orchestrator)
    └─ _SymbolProcessor      : per-symbol pipeline (fetch → indicators → score)
    └─ RankingResult         : typed result container
    └─ RankingReport         : final aggregated output

Design Principles
-----------------
  * Fail-per-symbol isolation  – one bad ticker never poisons the batch
  * Lazy DB connections        – pulled from a pool, never held open
  * Deterministic ordering     – ties broken by symbol name
  * Pluggable scorer           – swap scoring_engine without touching this file
  * Zero global state          – all state lives inside RankingEngine instance
"""

from __future__ import annotations

import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

# ── Internal imports (adjust paths to match your project layout) ──────────────
from indicator_engine import calculate_indicators, add_volume_trend
from scoring_engine import score_stock

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Minimum candles required before we attempt indicator calculation.
# EMA200 needs 200, MACD needs 26+9, ATR needs 14 — 250 gives comfortable head room.
MIN_CANDLES_REQUIRED = 200
PREFERRED_CANDLES    = 250

# Worker threads for parallel symbol processing.
# IO-bound (DB reads) → threads scale well; keep ≤ 20 to avoid DB pool exhaustion.
DEFAULT_WORKERS = 10

# Signals ranked weakest → strongest (used for tie-breaking / filtering)
SIGNAL_RANK = {
    "AVOID":     0,
    "NEUTRAL":   1,
    "WEAK BUY":  2,
    "BUY":       3,
    "STRONG BUY": 4,
}


# ─────────────────────────────────────────────────────────────────────────────
# DATA CONTAINERS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RankingResult:
    """Immutable result for a single ranked symbol."""
    symbol:           str
    score:            float
    signal:           str
    signal_rank:      int
    component_scores: dict[str, float]
    component_pct:    dict[str, float]
    latest_price:     float
    rsi:              float
    volume_ratio:     float
    atr_percent:      float
    breakout:         bool
    market_bullish:   bool
    trend_alignment:  bool
    ranked_at:        datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ranked_at"] = self.ranked_at.isoformat()
        return d

    @property
    def is_actionable(self) -> bool:
        """True if signal is WEAK BUY or better."""
        return self.signal_rank >= SIGNAL_RANK["WEAK BUY"]


@dataclass
class SymbolError:
    """Captures exactly what went wrong per symbol — never swallowed silently."""
    symbol:    str
    stage:     str           # "fetch" | "indicators" | "scoring"
    reason:    str
    exc_type:  str


@dataclass
class RankingReport:
    """Complete output from one ranking run."""
    ranked:       list[RankingResult]
    errors:       list[SymbolError]
    total_input:  int
    total_scored: int
    total_failed: int
    duration_sec: float
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # ── Convenience slices ───────────────────────────────────────
    def top(self, n: int = 10) -> list[RankingResult]:
        return self.ranked[:n]

    def actionable(self) -> list[RankingResult]:
        """All symbols with WEAK BUY or better signal."""
        return [r for r in self.ranked if r.is_actionable]

    def by_signal(self, signal: str) -> list[RankingResult]:
        return [r for r in self.ranked if r.signal == signal]

    def summary(self) -> dict[str, Any]:
        signal_dist: dict[str, int] = {}
        for r in self.ranked:
            signal_dist[r.signal] = signal_dist.get(r.signal, 0) + 1
        return {
            "total_input":   self.total_input,
            "total_scored":  self.total_scored,
            "total_failed":  self.total_failed,
            "success_rate":  f"{(self.total_scored / max(self.total_input, 1)) * 100:.1f}%",
            "duration_sec":  round(self.duration_sec, 2),
            "signal_distribution": signal_dist,
            "top_3": [
                {"symbol": r.symbol, "score": r.score, "signal": r.signal}
                for r in self.ranked[:3]
            ],
        }

    def to_dataframe(self) -> pd.DataFrame:
        """Convert ranked list to a clean DataFrame for downstream use."""
        if not self.ranked:
            return pd.DataFrame()
        rows = []
        for r in self.ranked:
            row = {
                "symbol":        r.symbol,
                "score":         r.score,
                "signal":        r.signal,
                "price":         r.latest_price,
                "rsi":           r.rsi,
                "volume_ratio":  r.volume_ratio,
                "atr_pct":       r.atr_percent,
                "breakout":      r.breakout,
                "market_bullish": r.market_bullish,
            }
            row.update({f"cmp_{k}": v for k, v in r.component_scores.items()})
            rows.append(row)
        return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE LAYER
# ─────────────────────────────────────────────────────────────────────────────

class CandleRepository:
    """
    Thin repository — owns all SQL so the engine stays SQL-free.

    Why a separate class?
      If you swap PostgreSQL for ClickHouse or a Parquet cache later,
      you touch only this class, not the engine logic.
    """

    # ── Fetch active symbols ─────────────────────────────────────
    ACTIVE_SYMBOLS_SQL = """
        SELECT symbol
        FROM   stocks
        WHERE  is_active = TRUE
        ORDER  BY symbol;
    """

    # ── Fetch recent candles (parameterised) ─────────────────────
    # Using a CTE with ROW_NUMBER lets PostgreSQL pick the latest N
    # rows cheaply via the (symbol, time DESC) index without a full scan.
    CANDLES_SQL = """
        WITH ranked AS (
            SELECT
                time,
                open,
                high,
                low,
                close,
                volume,
                ROW_NUMBER() OVER (
                    PARTITION BY symbol
                    ORDER BY time DESC
                ) AS rn
            FROM   candles
            WHERE  symbol = %(symbol)s
        )
        SELECT time, open, high, low, close, volume
        FROM   ranked
        WHERE  rn <= %(limit)s
        ORDER  BY time ASC;
    """

    def __init__(self, db_conn_factory):
        """
        db_conn_factory: callable → psycopg2 / SQLAlchemy connection
        Keeping it as a factory means each call gets a fresh connection
        from the pool — safe for concurrent threads.
        """
        self._conn_factory = db_conn_factory

    def get_active_symbols(self) -> list[str]:
        conn = self._conn_factory()
        try:
            with conn.cursor() as cur:
                cur.execute(self.ACTIVE_SYMBOLS_SQL)
                rows = cur.fetchall()
            return [row[0] for row in rows]
        finally:
            conn.close()

    def get_candles(self, symbol: str, limit: int = PREFERRED_CANDLES) -> pd.DataFrame:
        """
        Returns a DataFrame with columns:
          time, open, high, low, close, volume
        Sorted ascending by time.
        Returns empty DataFrame on any DB error.
        """
        conn = self._conn_factory()
        try:
            df = pd.read_sql(
                self.CANDLES_SQL,
                conn,
                params={"symbol": symbol, "limit": limit},
                parse_dates=["time"],
            )
            if df.empty:
                return df

            df = df.sort_values("time").reset_index(drop=True)
            df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)
            df = df.set_index("time")
            return df
        finally:
            conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# PER-SYMBOL PROCESSOR
# ─────────────────────────────────────────────────────────────────────────────

class _SymbolProcessor:
    """
    Encapsulates the full pipeline for one symbol.
    Designed to run inside a thread — holds no shared mutable state.

    Pipeline stages:
      1. fetch     → raw OHLCV DataFrame
      2. validate  → enough rows, no NaN close prices
      3. indicators → calculate_indicators() + add_volume_trend()
      4. score     → score_stock() on latest row
      5. pack      → RankingResult dataclass
    """

    def __init__(self, repo: CandleRepository, candle_limit: int = PREFERRED_CANDLES):
        self._repo  = repo
        self._limit = candle_limit

    def process(self, symbol: str) -> RankingResult:
        """
        Run the full pipeline. Raises descriptive exceptions so the
        caller can tag them with the correct stage.
        """
        # Stage 1 — Fetch
        df = self._fetch(symbol)

        # Stage 2 — Validate
        self._validate(symbol, df)

        # Stage 3 — Indicators
        df = self._indicators(symbol, df)

        # Stage 4 — Score
        result = self._score(symbol, df)

        return result

    # ── Private stage methods ────────────────────────────────────

    def _fetch(self, symbol: str) -> pd.DataFrame:
        df = self._repo.get_candles(symbol, self._limit)
        if df is None or df.empty:
            raise ValueError(f"No candle data returned from database")
        return df

    def _validate(self, symbol: str, df: pd.DataFrame) -> None:
        if len(df) < MIN_CANDLES_REQUIRED:
            raise ValueError(
                f"Insufficient candles: got {len(df)}, need {MIN_CANDLES_REQUIRED}"
            )
        required_cols = {"open", "high", "low", "close", "volume"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"Missing OHLCV columns: {missing}")

        null_close = df["close"].isna().sum()
        if null_close > len(df) * 0.05:   # >5% nulls = bad data
            raise ValueError(f"Too many null close prices: {null_close}")

        # Forward-fill minor gaps (weekend carry-overs, halts)
        df.ffill(inplace=True)

    def _indicators(self, symbol: str, df: pd.DataFrame) -> pd.DataFrame:
        df = calculate_indicators(df)
        df = add_volume_trend(df)

        # Verify core indicators were actually populated
        critical = ["RSI", "EMA20", "EMA50", "EMA200", "ATR", "MACD"]
        for col in critical:
            if col not in df.columns:
                raise ValueError(f"Indicator '{col}' missing after calculation")
            if df[col].isna().all():
                raise ValueError(f"Indicator '{col}' is entirely NaN")
        return df

    def _score(self, symbol: str, df: pd.DataFrame) -> RankingResult:
        latest = df.iloc[-1].to_dict()

        # Guard: NaN close means last candle is corrupt
        if math.isnan(latest.get("close", float("nan"))):
            raise ValueError("Last candle has NaN close price")

        result = score_stock(latest)

        component_scores = {
            name: comp["score"]
            for name, comp in result["components"].items()
        }

        return RankingResult(
            symbol           = symbol,
            score            = result["total_score"],
            signal           = result["signal"],
            signal_rank      = SIGNAL_RANK.get(result["signal"], 0),
            component_scores = component_scores,
            component_pct    = result["component_pct"],
            latest_price     = float(latest.get("close", 0)),
            rsi              = float(latest.get("RSI", 0) or 0),
            volume_ratio     = float(latest.get("VOLUME_RATIO", 1) or 1),
            atr_percent      = float(latest.get("ATR_PERCENT", 0) or 0),
            breakout         = bool(latest.get("BREAKOUT", False)),
            market_bullish   = bool(latest.get("MARKET_BULLISH", False)),
            trend_alignment  = bool(latest.get("TREND_ALIGNMENT", False)),
        )


# ─────────────────────────────────────────────────────────────────────────────
# RANKING ENGINE  (main orchestrator)
# ─────────────────────────────────────────────────────────────────────────────

class RankingEngine:
    """
    Orchestrates parallel processing of all active symbols and
    returns a fully ranked RankingReport.

    Thread safety
    -------------
    Each symbol is processed in its own thread via ThreadPoolExecutor.
    The DB connection factory is called per-thread, so no connection
    is shared across threads — fully safe.

    Why ThreadPoolExecutor and not ProcessPool?
    -------------------------------------------
    The bottleneck is DB I/O, not CPU. Threads share memory and avoid
    the serialization overhead of multiprocessing. For CPU-bound TA-Lib
    calculations on 500+ stocks, switch to ProcessPoolExecutor.
    """

    def __init__(
        self,
        db_conn_factory,
        candle_limit: int  = PREFERRED_CANDLES,
        max_workers:  int  = DEFAULT_WORKERS,
    ):
        self._repo      = CandleRepository(db_conn_factory)
        self._processor = _SymbolProcessor(self._repo, candle_limit)
        self._workers   = max_workers

    # ── Public API ───────────────────────────────────────────────

    def run(self, symbols: Optional[list[str]] = None) -> RankingReport:
        """
        Full ranking run.
        Pass symbols=None to rank all active stocks from DB.
        Pass a list to rank a specific subset (useful for watchlists).
        """
        t_start = time.perf_counter()

        if symbols is None:
            logger.info("Fetching active symbols from database...")
            symbols = self._repo.get_active_symbols()

        logger.info(f"Starting ranking run for {len(symbols)} symbols "
                    f"with {self._workers} workers")

        ranked, errors = self._run_parallel(symbols)

        # Sort: primary = score DESC, secondary = signal_rank DESC, tertiary = symbol ASC
        ranked.sort(
            key=lambda r: (-r.score, -r.signal_rank, r.symbol)
        )

        duration = time.perf_counter() - t_start

        report = RankingReport(
            ranked       = ranked,
            errors       = errors,
            total_input  = len(symbols),
            total_scored = len(ranked),
            total_failed = len(errors),
            duration_sec = duration,
        )

        self._log_report_summary(report)
        return report

    def get_top_ranked_stocks(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Convenience wrapper — runs full pipeline, returns top N as dicts.
        Suitable for direct API response serialization.
        """
        report = self.run()
        return [r.to_dict() for r in report.top(limit)]

    # ── Internal ─────────────────────────────────────────────────

    def _run_parallel(
        self, symbols: list[str]
    ) -> tuple[list[RankingResult], list[SymbolError]]:

        ranked: list[RankingResult] = []
        errors: list[SymbolError]   = []

        with ThreadPoolExecutor(max_workers=self._workers) as pool:
            future_map = {
                pool.submit(self._safe_process, sym): sym
                for sym in symbols
            }

            for future in as_completed(future_map):
                symbol = future_map[future]
                try:
                    outcome = future.result()
                    if isinstance(outcome, RankingResult):
                        ranked.append(outcome)
                    else:
                        errors.append(outcome)   # SymbolError
                except Exception as exc:
                    # Absolute last-resort catch — future.result() itself failed
                    errors.append(SymbolError(
                        symbol   = symbol,
                        stage    = "unknown",
                        reason   = str(exc),
                        exc_type = type(exc).__name__,
                    ))
                    logger.exception(f"[{symbol}] Unexpected future error")

        return ranked, errors

    def _safe_process(self, symbol: str) -> RankingResult | SymbolError:
        """
        Wraps _SymbolProcessor.process() with per-stage error attribution.
        Returns either a RankingResult or a SymbolError — never raises.
        """
        t0 = time.perf_counter()
        stage = "init"
        try:
            stage = "fetch"
            df = self._processor._fetch(symbol)

            stage = "validate"
            self._processor._validate(symbol, df)

            stage = "indicators"
            df = self._processor._indicators(symbol, df)

            stage = "scoring"
            result = self._processor._score(symbol, df)

            elapsed = (time.perf_counter() - t0) * 1000
            logger.debug(f"[{symbol}] ✓ score={result.score:.1f} "
                         f"signal={result.signal} ({elapsed:.0f}ms)")
            return result

        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            logger.warning(f"[{symbol}] ✗ stage={stage} "
                           f"error={type(exc).__name__}: {exc} ({elapsed:.0f}ms)")
            return SymbolError(
                symbol   = symbol,
                stage    = stage,
                reason   = str(exc),
                exc_type = type(exc).__name__,
            )

    @staticmethod
    def _log_report_summary(report: RankingReport) -> None:
        summary = report.summary()
        logger.info(
            f"Ranking complete | "
            f"scored={report.total_scored}/{report.total_input} | "
            f"failed={report.total_failed} | "
            f"duration={report.duration_sec:.2f}s | "
            f"signals={summary['signal_distribution']}"
        )
        if report.ranked:
            logger.info(
                "Top 3: " + " | ".join(
                    f"{r.symbol} {r.score:.1f} ({r.signal})"
                    for r in report.ranked[:3]
                )
            )
        if report.errors:
            stage_counts: dict[str, int] = {}
            for e in report.errors:
                stage_counts[e.stage] = stage_counts.get(e.stage, 0) + 1
            logger.warning(f"Failure breakdown by stage: {stage_counts}")


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTIONS  (for direct import / FastAPI router use)
# ─────────────────────────────────────────────────────────────────────────────

def get_top_ranked_stocks(
    db_conn_factory,
    limit:        int = 10,
    max_workers:  int = DEFAULT_WORKERS,
) -> list[dict[str, Any]]:
    """
    One-liner entry point.

    Usage (FastAPI example):
        @router.get("/top-stocks")
        def top_stocks():
            return get_top_ranked_stocks(get_db_connection, limit=10)
    """
    engine = RankingEngine(db_conn_factory, max_workers=max_workers)
    return engine.get_top_ranked_stocks(limit=limit)


def run_full_ranking(
    db_conn_factory,
    symbols:      Optional[list[str]] = None,
    max_workers:  int = DEFAULT_WORKERS,
) -> RankingReport:
    """
    Run a full ranking and return the complete RankingReport.
    Useful for scheduled jobs, backtesting, or admin endpoints.
    """
    engine = RankingEngine(db_conn_factory, max_workers=max_workers)
    return engine.run(symbols=symbols)