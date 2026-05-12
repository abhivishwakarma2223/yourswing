"""
rs_ranking.py
=============
Cross-stock Relative Strength ranking for the Nifty 200 universe.

Computes, for each stock:
  RS_PERCENTILE_RANK     — 0–100 percentile rank vs all stocks (100 = strongest)
  RS_TREND_SLOPE         — Linear slope of RS line over last 20 days (+ = improving)
  RS_NEW_HIGH            — Bool: RS line at a new 52-week high
  RS_VS_NIFTY            — Stock 3M return / Nifty 3M return

Usage:
  rankings = compute_rs_rankings(symbols, repo, nifty_close_series)
  # returns Dict[symbol → dict of RS metrics]
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# In-memory cache: {key → (timestamp, data)}
_RS_CACHE: Optional[Dict] = None
_RS_CACHE_TS: float = 0.0
_RS_CACHE_TTL = 3600  # 1 hour


def _linreg_slope(series: pd.Series) -> float:
    """Return linear regression slope of series (normalized by mean price)."""
    s = series.dropna()
    if len(s) < 5:
        return 0.0
    x = np.arange(len(s), dtype=float)
    try:
        slope = np.polyfit(x, s.values, 1)[0]
        mean_val = s.mean()
        return float(slope / mean_val) if mean_val != 0 else 0.0
    except Exception:
        return 0.0


def compute_rs_rankings(
    candles_by_symbol: Dict[str, pd.DataFrame],
    nifty_df: Optional[pd.DataFrame] = None,
) -> Dict[str, dict]:
    """
    Compute RS rankings for all symbols from preloaded candle DataFrames.

    Parameters
    ----------
    candles_by_symbol : Dict[symbol → DataFrame]
        Each DataFrame must have 'close' column and DatetimeIndex / 'time' column.
    nifty_df : pd.DataFrame, optional
        DataFrame with 'close' column for Nifty 50. Used for RS_VS_NIFTY.

    Returns
    -------
    Dict[symbol → {RS_PERCENTILE_RANK, RS_TREND_SLOPE, RS_NEW_HIGH, RS_VS_NIFTY}]
    """
    global _RS_CACHE, _RS_CACHE_TS

    now = time.time()
    if _RS_CACHE is not None and (now - _RS_CACHE_TS) < _RS_CACHE_TTL:
        logger.info("[RS] Returning cached RS rankings")
        return _RS_CACHE

    logger.info(f"[RS] Computing RS rankings for {len(candles_by_symbol)} symbols...")
    t0 = time.perf_counter()

    # ── Build aligned close matrix ────────────────────────────────────────────
    # Use last 252 days of data
    close_dict = {}
    for sym, df in candles_by_symbol.items():
        if df is None or df.empty or "close" not in df.columns:
            continue
        # Use time column or index, ensuring no duplicates
        if "time" in df.columns:
            s = df.drop_duplicates(subset=["time"]).set_index("time")["close"]
        else:
            s = df[~df.index.duplicated(keep='last')]["close"]
        s = s.tail(252)
        close_dict[sym] = s


    if not close_dict:
        logger.warning("[RS] No valid candle data for RS ranking")
        return {}

    # Align to common date index
    close_matrix = pd.DataFrame(close_dict)
    close_matrix = close_matrix.ffill().bfill().fillna(0)


    n_rows = len(close_matrix)
    if n_rows < 30:
        logger.warning("[RS] Insufficient data for RS ranking")
        return {}

    # ── ROC calculations (vectorized) ─────────────────────────────────────────
    roc_1m = close_matrix.pct_change(21).iloc[-1] * 100   # 1-month
    roc_3m = close_matrix.pct_change(63).iloc[-1] * 100   # 3-month
    roc_6m = close_matrix.pct_change(126).iloc[-1] * 100  # 6-month

    # Composite RS score: weighted sum
    rs_composite = (roc_1m * 0.2 + roc_3m * 0.4 + roc_6m * 0.4).fillna(0)

    # ── Percentile ranks ──────────────────────────────────────────────────────
    rs_pct_rank = rs_composite.rank(pct=True) * 100

    # ── Nifty RS line for each stock ─────────────────────────────────────────
    nifty_roc_3m = 0.0
    if nifty_df is not None and not nifty_df.empty and "close" in nifty_df.columns:
        nifty_close = nifty_df["close"].tail(252)
        nifty_roc_3m = float(nifty_close.pct_change(63).iloc[-1] * 100) if len(nifty_close) > 63 else 0.0

    # ── RS line = stock return / Nifty return (daily ratio series) ────────────
    # For slope computation, use 63-day return relative to Nifty
    nifty_base = 1.0  # fallback
    if nifty_df is not None and not nifty_df.empty:
        nifty_s = nifty_df["close"].tail(252)
        nifty_series = nifty_s.values
    else:
        nifty_series = None

    results: Dict[str, dict] = {}

    for sym in close_matrix.columns:
        try:
            price_series = close_matrix[sym].dropna()
            if len(price_series) < 30:
                continue

            # RS vs Nifty (3M return ratio)
            stock_roc_3m = float(roc_3m.get(sym, 0.0))
            if nifty_roc_3m != 0:
                rs_vs_nifty = (1 + stock_roc_3m / 100) / (1 + nifty_roc_3m / 100)
            else:
                rs_vs_nifty = 1.0

            # RS line (rolling 20d window for slope)
            if nifty_series is not None and len(nifty_series) >= len(price_series):
                aligned_nifty = nifty_series[-len(price_series):]
                rs_line = price_series.values / (aligned_nifty + 1e-9)
            else:
                rs_line = price_series.values / (price_series.values[0] + 1e-9)

            rs_line_series = pd.Series(rs_line, index=price_series.index)

            # RS Trend Slope (last 20 days)
            rs_slope = _linreg_slope(rs_line_series.tail(20))

            # RS New High (is RS line at 52-week high?)
            rs_52w_high = rs_line_series.tail(252).max()
            rs_current = rs_line_series.iloc[-1]
            rs_new_high = bool(rs_current >= rs_52w_high * 0.995)  # within 0.5%

            results[sym] = {
                "RS_PERCENTILE_RANK": round(float(rs_pct_rank.get(sym, 50.0)), 2),
                "RS_TREND_SLOPE":     round(rs_slope, 6),
                "RS_NEW_HIGH":        rs_new_high,
                "RS_VS_NIFTY":        round(rs_vs_nifty, 4),
            }

        except Exception as e:
            logger.warning(f"[RS] Failed for {sym}: {e}")
            results[sym] = {
                "RS_PERCENTILE_RANK": 50.0,
                "RS_TREND_SLOPE":     0.0,
                "RS_NEW_HIGH":        False,
                "RS_VS_NIFTY":        1.0,
            }

    elapsed = time.perf_counter() - t0
    logger.info(f"[RS] Rankings computed for {len(results)} symbols in {elapsed:.2f}s")

    _RS_CACHE = results
    _RS_CACHE_TS = now
    return results


def invalidate_rs_cache():
    """Force recomputation on next call."""
    global _RS_CACHE, _RS_CACHE_TS
    _RS_CACHE = None
    _RS_CACHE_TS = 0.0
