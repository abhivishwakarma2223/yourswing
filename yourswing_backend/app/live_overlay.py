"""
app/live_overlay.py
===================
Lightweight live market overlay applied ON TOP of the stored
institutional snapshot score.

Rules:
  - NEVER re-runs the full scoring engine
  - NEVER writes to the database
  - Only reads live prices and applies structured adjustments in memory
  - All adjustments are bounded and documented
"""

import logging
import math
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# LIVE PRICE FETCHER
# ─────────────────────────────────────────────────────────────────────────────

def fetch_batch_live_prices(symbols: list[str]) -> dict[str, dict]:
    """
    Fetch live prices for a list of symbols in a single batch call.
    Returns dict keyed by symbol.
    """
    import yfinance as yf

    tickers = [s if s.endswith(".NS") else f"{s}.NS" for s in symbols]
    result  = {}

    try:
        data = yf.download(
            tickers,
            period="2d",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )

        for sym in symbols:
            ticker = sym if sym.endswith(".NS") else f"{sym}.NS"
            try:
                if len(tickers) == 1:
                    df = data
                else:
                    df = data[ticker]

                if df is None or df.empty or len(df) < 2:
                    continue

                prev_close = float(df["Close"].iloc[-2]) if len(df) >= 2 else float(df["Close"].iloc[-1])
                curr_close = float(df["Close"].iloc[-1])
                change     = curr_close - prev_close
                change_pct = (change / prev_close * 100) if prev_close > 0 else 0.0

                result[sym] = {
                    "price":      round(curr_close, 2) if not math.isnan(curr_close) else 0.0,
                    "prev_close": round(prev_close, 2) if not math.isnan(prev_close) else 0.0,
                    "change":     round(change, 2) if not math.isnan(change) else 0.0,
                    "change_pct": round(change_pct, 2) if not math.isnan(change_pct) else 0.0,
                    "volume":     int(df["Volume"].iloc[-1]) if not math.isnan(df["Volume"].iloc[-1]) else 0,
                    "day_high":   round(float(df["High"].iloc[-1]), 2) if not math.isnan(df["High"].iloc[-1]) else 0.0,
                    "day_low":    round(float(df["Low"].iloc[-1]), 2) if not math.isnan(df["Low"].iloc[-1]) else 0.0,
                    "day_open":   round(float(df["Open"].iloc[-1]), 2) if not math.isnan(df["Open"].iloc[-1]) else 0.0,
                }
            except Exception as e:
                logger.debug(f"[{sym}] live price fetch failed: {e}")
                continue

    except Exception as e:
        logger.error(f"Batch live fetch failed: {e}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# LIVE OVERLAY CALCULATION
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LiveAdjustment:
    """Tracks each individual live adjustment for transparency."""
    reason:     str
    delta:      float   # +ve = boost, -ve = penalize


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def _score_to_signal(score: float) -> str:
    if score >= 80: return "STRONG BUY"
    if score >= 65: return "BUY"
    if score >= 50: return "WEAK BUY"
    if score >= 35: return "NEUTRAL"
    return "AVOID"


def compute_live_overlay(
    institutional_score: float,
    snapshot_price:      float,
    live:                dict,
    institutional_signal: str,
    breakout_at_snapshot: bool,
    atr_percent:         Optional[float],
) -> dict:
    """
    Compute a live-adjusted score on top of the institutional snapshot.
    """
    adjustments: list[LiveAdjustment] = []

    price      = live.get("price", snapshot_price)
    change_pct = live.get("change_pct", 0.0)
    day_open   = live.get("day_open", price)
    day_high   = live.get("day_high", price)
    day_low    = live.get("day_low", price)
    volume     = live.get("volume", 0)

    atr_pct    = atr_percent or 2.0   # fallback 2% ATR
    live_score = institutional_score

    # ── 1. Gap Analysis ──────────────────────────────────────────
    if snapshot_price > 0:
        gap_pct = ((day_open - snapshot_price) / snapshot_price) * 100
    else:
        gap_pct = 0.0

    if gap_pct > atr_pct:
        delta = _clamp(gap_pct / atr_pct * 1.5, 0, 4.0)
        adjustments.append(LiveAdjustment("gap_up_vs_atr", delta))
    elif gap_pct < -atr_pct:
        delta = _clamp(gap_pct / atr_pct * 1.5, -4.0, 0)
        adjustments.append(LiveAdjustment("gap_down_vs_atr", delta))

    # ── 2. Intraday Momentum ─────────────────────────────────────
    day_range = day_high - day_low
    if day_range > 0:
        close_position = (price - day_low) / day_range   # 0=at low, 1=at high
        if close_position >= 0.75:
            adjustments.append(LiveAdjustment("close_near_day_high", 1.5))
        elif close_position <= 0.25:
            adjustments.append(LiveAdjustment("close_near_day_low", -1.5))

    # ── 3. Breakout Activation ───────────────────────────────────
    if breakout_at_snapshot and change_pct > 1.5:
        adjustments.append(LiveAdjustment("breakout_confirmation", 2.0))
    elif breakout_at_snapshot and change_pct < -2.0:
        adjustments.append(LiveAdjustment("breakout_failure", -3.0))

    # ── 4. Reversal Warning ──────────────────────────────────────
    if institutional_signal == "STRONG BUY" and change_pct < -1.5:
        adjustments.append(LiveAdjustment("strong_buy_reversal_warning", -2.0))

    # ── Apply all adjustments ────────────────────────────────────
    total_delta = sum(a.delta for a in adjustments)
    total_delta = _clamp(total_delta, -8.0, 8.0)
    live_score  = _clamp(institutional_score + total_delta, 0.0, 100.0)
    live_score  = round(live_score, 2)

    return {
        "live_score":          live_score,
        "live_signal":         _score_to_signal(live_score),
        "live_delta":          round(total_delta, 2),
        "adjustments":         [{"reason": a.reason, "delta": a.delta} for a in adjustments],
        "gap_pct":             round(gap_pct, 2),
        "intraday_change_pct": round(change_pct, 2),
        "day_open":            day_open,
        "day_high":            day_high,
        "day_low":             day_low,
        "live_volume":         volume
    }
