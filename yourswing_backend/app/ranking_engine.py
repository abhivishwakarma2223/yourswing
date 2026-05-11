# ranking_engine.py (Fixed Production Version)

from __future__ import annotations

import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

from app.indicator_engine import calculate_indicators, get_nifty_data
from app.scoring_engine import score_stock, apply_portfolio_concentration_filter
from app.market_api import get_market_regime_dict

logger = logging.getLogger(__name__)


# ============================================================
# UTILITIES
# ============================================================


def clean_val(v: Any) -> Optional[float]:
    """Convert NaN/Inf to None for JSON-safe responses."""

    if v is None:
        return None

    try:
        f = float(v)

        if math.isnan(f) or math.isinf(f):
            return None

        return f

    except (ValueError, TypeError):
        return None


# ============================================================
# CONSTANTS
# ============================================================

MIN_CANDLES_REQUIRED = 200
PREFERRED_CANDLES = 250
DEFAULT_WORKERS = 10

SIGNAL_RANK = {
    "AVOID": 0,
    "NEUTRAL": 1,
    "WEAK BUY": 2,
    "BUY": 3,
    "STRONG BUY": 4,
}


# ============================================================
# DATA CONTAINERS
# ============================================================

@dataclass
class RankingResult:
    symbol: str
    score: float
    signal: str
    signal_rank: int
    component_scores: dict[str, float]
    component_pct: dict[str, float]
    latest_price: Optional[float]
    rsi: Optional[float]
    volume_ratio: Optional[float]
    atr_percent: Optional[float]
    breakout: bool
    market_bullish: bool
    trend_alignment: bool
    ranked_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ranked_at"] = self.ranked_at.isoformat()
        return d

    @property
    def is_actionable(self) -> bool:
        return self.signal_rank >= SIGNAL_RANK["WEAK BUY"]


@dataclass
class SymbolError:
    symbol: str
    stage: str
    reason: str
    exc_type: str


@dataclass
class RankingReport:
    ranked: list[RankingResult]
    errors: list[SymbolError]
    total_input: int
    total_scored: int
    total_failed: int
    duration_sec: float
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def top(self, n: int = 10) -> list[RankingResult]:
        return self.ranked[:n]

    def actionable(self) -> list[RankingResult]:
        return [r for r in self.ranked if r.is_actionable]

    def summary(self) -> dict[str, Any]:

        signal_dist: dict[str, int] = {}

        for r in self.ranked:
            signal_dist[r.signal] = signal_dist.get(r.signal, 0) + 1

        return {
            "total_input": self.total_input,
            "total_scored": self.total_scored,
            "total_failed": self.total_failed,
            "success_rate": f"{(self.total_scored / max(self.total_input, 1)) * 100:.1f}%",
            "duration_sec": round(self.duration_sec, 2),
            "signal_distribution": signal_dist,
        }


# ============================================================
# DATABASE LAYER
# ============================================================

class CandleRepository:

    ACTIVE_SYMBOLS_SQL = """
        SELECT symbol
        FROM stocks
        WHERE is_active = TRUE
        ORDER BY symbol;
    """

    CANDLES_SQL = """
        WITH ranked AS (
            SELECT
                c.candle_time AS time,
                c.open,
                c.high,
                c.low,
                c.close,
                c.volume,
                ROW_NUMBER() OVER (
                    PARTITION BY s.symbol
                    ORDER BY c.candle_time DESC
                ) AS rn
            FROM candles c
            JOIN stocks s ON c.stock_id = s.id
            WHERE s.symbol = %(symbol)s
        )
        SELECT
            time,
            open,
            high,
            low,
            close,
            volume
        FROM ranked
        WHERE rn <= %(limit)s
        ORDER BY time ASC;
    """

    def __init__(self, db_conn_factory):
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

    def get_candles(
        self,
        symbol: str,
        limit: int = PREFERRED_CANDLES,
    ) -> pd.DataFrame:

        conn = self._conn_factory()

        try:

            df = pd.read_sql(
                self.CANDLES_SQL,
                conn,
                params={
                    "symbol": symbol,
                    "limit": limit,
                },
                parse_dates=["time"],
            )

            if df.empty:
                return df

            df = df.sort_values("time").reset_index(drop=True)

            # IMPORTANT FIX:
            # keep time as COLUMN instead of index
            df["time"] = pd.to_datetime(df["time"])
            df["time"] = df["time"].dt.tz_localize(None)

            return df

        finally:
            conn.close()


# ============================================================
# SYMBOL PROCESSOR
# ============================================================

class _SymbolProcessor:

    def __init__(
        self,
        repo: CandleRepository,
        candle_limit: int = PREFERRED_CANDLES,
    ):

        self._repo = repo
        self._limit = candle_limit

    def process(self, symbol: str, market: dict) -> RankingResult:

        df = self._fetch(symbol)

        self._validate(symbol, df)

        df = self._indicators(symbol, df)

        result = self._score(symbol, df, market)

        return result

    # ========================================================
    # FETCH
    # ========================================================

    def _fetch(self, symbol: str) -> pd.DataFrame:

        df = self._repo.get_candles(symbol, self._limit)

        if df is None or df.empty:
            raise ValueError("No candle data returned")

        return df

    # ========================================================
    # VALIDATE
    # ========================================================

    def _validate(self, symbol: str, df: pd.DataFrame):

        if len(df) < MIN_CANDLES_REQUIRED:
            raise ValueError(
                f"Insufficient candles: {len(df)}"
            )

        required_cols = {
            "time",
            "open",
            "high",
            "low",
            "close",
            "volume",
        }

        missing = required_cols - set(df.columns)

        if missing:
            raise ValueError(
                f"Missing columns: {missing}"
            )

        null_close = df["close"].isna().sum()

        if null_close > len(df) * 0.05:
            raise ValueError(
                f"Too many null close prices"
            )

        df.ffill(inplace=True)

    # ========================================================
    # INDICATORS
    # ========================================================

    def _indicators(
        self,
        symbol: str,
        df: pd.DataFrame,
    ) -> pd.DataFrame:

        df = calculate_indicators(df)

        critical = [
            "RSI",
            "EMA20",
            "EMA50",
            "EMA200",
            "MACD",
            "ATR",
        ]

        for col in critical:

            if col not in df.columns:
                raise ValueError(
                    f"Missing indicator: {col}"
                )

            if df[col].isna().all():
                raise ValueError(
                    f"Indicator all NaN: {col}"
                )

        # Only drop rows where CORE indicators are NaN.
        # v2 helpers (HV_PERCENTILE, ROC_6M, etc.) need 252 candles
        # to fully populate — dropping all NaN rows would wipe the df.
        df = df.dropna(subset=critical).reset_index(drop=True)

        return df

    # ========================================================
    # SCORE
    # ========================================================

    def _score(
        self,
        symbol: str,
        df: pd.DataFrame,
        market: dict,
    ) -> RankingResult:

        latest = df.iloc[-1].to_dict()

        if math.isnan(
            latest.get("close", float("nan"))
        ):
            raise ValueError(
                "Latest close price invalid"
            )

        # Pass market dict — enables full regime gate (v2 scoring engine)
        result = score_stock(latest, market)

        # Handle the case where score_stock returns a failure dict
        components_data = result.get("components", {})
        component_scores = {
            name: comp.get("score", 0.0)
            for name, comp in components_data.items()
        }


        return RankingResult(
            symbol=symbol,
            score=result["final_score"],
            signal=result["signal"],
            signal_rank=SIGNAL_RANK.get(
                result["signal"],
                0,
            ),
            component_scores=component_scores,
            component_pct=result[
                "component_pct"
            ],
            latest_price=clean_val(
                latest.get("close")
            ),
            rsi=clean_val(
                latest.get("RSI")
            ),
            volume_ratio=clean_val(
                latest.get("VOLUME_RATIO")
            ),
            atr_percent=clean_val(
                latest.get("ATR_PERCENT")
            ),
            breakout=bool(
                latest.get("BREAKOUT", False)
            ),
            market_bullish=bool(
                latest.get(
                    "MARKET_BULLISH",
                    False,
                )
            ),
            trend_alignment=bool(
                latest.get(
                    "TREND_ALIGNMENT",
                    False,
                )
            ),
        )


# ============================================================
# RANKING ENGINE
# ============================================================

class RankingEngine:

    def __init__(
        self,
        db_conn_factory,
        candle_limit: int = PREFERRED_CANDLES,
        max_workers: int = DEFAULT_WORKERS,
    ):

        self._repo = CandleRepository(
            db_conn_factory
        )

        self._processor = _SymbolProcessor(
            self._repo,
            candle_limit,
        )

        self._workers = max_workers

    # ========================================================
    # MAIN RUNNER
    # ========================================================

    def run(
        self,
        symbols: Optional[list[str]] = None,
    ) -> RankingReport:

        t_start = time.perf_counter()

        # IMPORTANT FIX:
        # preload nifty once before threads
        logger.info(
            "Preloading NIFTY data..."
        )

        get_nifty_data()

        # Fetch market regime dict ONCE — reused for all stocks in the scan
        logger.info("Fetching market regime data (Nifty + VIX)...")
        market = get_market_regime_dict()
        logger.info(
            f"Market regime: {market.get('NIFTY_CLOSE', '?')} close | "
            f"VIX: {market.get('INDIAVIX', '?')}"
        )

        if symbols is None:

            logger.info(
                "Fetching active symbols..."
            )

            symbols = self._repo.get_active_symbols()

        logger.info(
            f"Ranking {len(symbols)} symbols"
        )

        ranked, errors = self._run_parallel(
            symbols, market
        )

        ranked.sort(
            key=lambda r: (
                -r.score,
                -r.signal_rank,
                r.symbol,
            )
        )

        duration = (
            time.perf_counter()
            - t_start
        )

        report = RankingReport(
            ranked=ranked,
            errors=errors,
            total_input=len(symbols),
            total_scored=len(ranked),
            total_failed=len(errors),
            duration_sec=duration,
        )

        self._log_report_summary(report)

        return report

    # ========================================================
    # TOP STOCKS
    # ========================================================

    def get_top_ranked_stocks(
        self,
        limit: int = 10,
    ) -> list[dict[str, Any]]:

        report = self.run()

        # Build dicts with the keys apply_portfolio_concentration_filter expects
        candidates = [
            {
                **r.to_dict(),
                "final_score": r.score,   # alias: RankingResult.score IS final_score
                "sector": "Unknown",       # TODO: enrich from stock metadata
            }
            for r in report.top(limit * 5)  # over-fetch significantly
        ]

        # Use a high limit for "Unknown" so we don't block everything
        filtered = apply_portfolio_concentration_filter(
            candidates, max_per_sector=10 
        )


        return filtered[:limit]

    # ========================================================
    # PARALLEL EXECUTION
    # ========================================================

    def _run_parallel(
        self,
        symbols: list[str],
        market: dict,
    ):

        ranked: list[RankingResult] = []
        errors: list[SymbolError] = []

        with ThreadPoolExecutor(
            max_workers=self._workers
        ) as pool:

            future_map = {
                pool.submit(
                    self._safe_process,
                    symbol,
                    market,           # passed to every worker thread (read-only, thread-safe)
                ): symbol
                for symbol in symbols
            }

            for future in as_completed(
                future_map
            ):

                symbol = future_map[future]

                try:

                    outcome = future.result()

                    if isinstance(
                        outcome,
                        RankingResult,
                    ):
                        ranked.append(outcome)

                    else:
                        errors.append(outcome)

                except Exception as exc:

                    errors.append(
                        SymbolError(
                            symbol=symbol,
                            stage="unknown",
                            reason=str(exc),
                            exc_type=type(exc).__name__,
                        )
                    )

                    logger.exception(
                        f"[{symbol}] Future error"
                    )

        return ranked, errors

    # ========================================================
    # SAFE PROCESSOR
    # ========================================================

    def _safe_process(
        self,
        symbol: str,
        market: dict,
    ):

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
            result = self._processor._score(symbol, df, market)

            elapsed = (
                time.perf_counter()
                - t0
            ) * 1000

            logger.debug(
                f"[{symbol}] score={result.score:.1f} ({elapsed:.0f}ms)"
            )

            return result

        except Exception as exc:

            elapsed = (
                time.perf_counter()
                - t0
            ) * 1000

            logger.warning(
                f"[{symbol}] stage={stage} error={exc} ({elapsed:.0f}ms)"
            )

            return SymbolError(
                symbol=symbol,
                stage=stage,
                reason=str(exc),
                exc_type=type(exc).__name__,
            )

    # ========================================================
    # SUMMARY LOGGING
    # ========================================================

    @staticmethod
    def _log_report_summary(
        report: RankingReport,
    ):

        summary = report.summary()

        logger.info(
            f"Ranking complete | "
            f"scored={report.total_scored}/{report.total_input} | "
            f"failed={report.total_failed} | "
            f"duration={report.duration_sec:.2f}s"
        )

        logger.info(
            f"Signals: {summary['signal_distribution']}"
        )


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================


def get_top_ranked_stocks(
    db_conn_factory,
    limit: int = 10,
    max_workers: int = DEFAULT_WORKERS,
):

    engine = RankingEngine(
        db_conn_factory,
        max_workers=max_workers,
    )

    return engine.get_top_ranked_stocks(
        limit=limit
    )



def run_full_ranking(
    db_conn_factory,
    symbols: Optional[list[str]] = None,
    max_workers: int = DEFAULT_WORKERS,
):

    engine = RankingEngine(
        db_conn_factory,
        max_workers=max_workers,
    )

    return engine.run(symbols=symbols)
