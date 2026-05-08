"""
Swing Trading Score Engine
==========================
Each component scores on a continuous scale (not binary).
Partial credit is given based on how strongly conditions are met.

Component       Max Score
---------       ---------
Trend               25
Breakout            20
Volume              15
Momentum            15
Relative Strength   10
Structure            5
Volatility           5
Market Trend         5
---------       ---------
TOTAL              100
"""

import math
import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _safe(val, default=0.0):
    """Return val if it's a valid finite number, else default."""
    try:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _clamp(val, lo, hi):
    """Clamp val to [lo, hi]."""
    return max(lo, min(hi, val))


def _sigmoid_scale(x, center, steepness, max_score):
    """
    Smooth sigmoid scaling. Returns a value in (0, max_score).
    - center:    the x value that gives ~50% of max_score
    - steepness: how sharply the curve rises (higher = steeper)
    """
    try:
        scaled = 1 / (1 + math.exp(-steepness * (x - center)))
        return scaled * max_score
    except (OverflowError, ZeroDivisionError):
        return 0.0


def _linear_scale(x, x_min, x_max, score_min, score_max):
    """Linear interpolation between two breakpoints."""
    if x_max == x_min:
        return score_min
    ratio = _clamp((x - x_min) / (x_max - x_min), 0, 1)
    return score_min + ratio * (score_max - score_min)


# ─────────────────────────────────────────────────────────────────────────────
# 1. TREND  (max 25)
# ─────────────────────────────────────────────────────────────────────────────

def score_trend(latest: dict) -> dict:
    """
    Sub-components:
      - EMA Alignment         (0–12):  how cleanly EMAs stack bullish
      - Price vs EMAs         (0–8):   how far price sits above each EMA
      - Trend Strength        (0–5):   EMA20 vs EMA50 separation %
    """
    MAX = 25

    ema20  = _safe(latest.get("EMA20"))
    ema50  = _safe(latest.get("EMA50"))
    ema200 = _safe(latest.get("EMA200"))
    close  = _safe(latest.get("close"))
    ts     = _safe(latest.get("TREND_STRENGTH"))  # (EMA20-EMA50)/EMA50 * 100

    breakdown = {}

    # ── EMA Alignment (0–12) ─────────────────────────────────────
    # Full stack: +12,  partial stacks get proportional credit
    if ema20 > 0 and ema50 > 0 and ema200 > 0:
        alignment_score = 0.0
        if ema20 > ema50:
            # How far above? Smooth credit 0–6 based on separation
            sep_pct = ((ema20 - ema50) / ema50) * 100  # e.g. 0 to 5%
            alignment_score += _linear_scale(sep_pct, 0, 3, 2, 6)
        if ema50 > ema200:
            sep_pct = ((ema50 - ema200) / ema200) * 100
            alignment_score += _linear_scale(sep_pct, 0, 3, 1, 6)
    else:
        alignment_score = 0.0
    breakdown["ema_alignment"] = _clamp(alignment_score, 0, 12)

    # ── Price vs EMAs (0–8) ──────────────────────────────────────
    # Each EMA gives smooth credit based on how far above close is
    price_score = 0.0
    if ema20 > 0:
        pct_above = ((close - ema20) / ema20) * 100   # -inf to +inf
        price_score += _linear_scale(pct_above, -2, 4, 0, 3)   # 3pts for EMA20
    if ema50 > 0:
        pct_above = ((close - ema50) / ema50) * 100
        price_score += _linear_scale(pct_above, -3, 5, 0, 3)   # 3pts for EMA50
    if ema200 > 0:
        pct_above = ((close - ema200) / ema200) * 100
        price_score += _linear_scale(pct_above, -5, 8, 0, 2)   # 2pts for EMA200
    breakdown["price_vs_emas"] = _clamp(price_score, 0, 8)

    # ── Trend Strength (0–5) ─────────────────────────────────────
    # TREND_STRENGTH = (EMA20 - EMA50) / EMA50 * 100
    # 0% = flat, >5% = very strong
    ts_score = _linear_scale(ts, 0, 6, 0, 5)
    breakdown["trend_strength"] = _clamp(ts_score, 0, 5)

    raw   = sum(breakdown.values())
    final = _clamp(raw, 0, MAX)
    return {"score": round(final, 2), "max": MAX, "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# 2. BREAKOUT  (max 20)
# ─────────────────────────────────────────────────────────────────────────────

def score_breakout(latest: dict) -> dict:
    """
    Sub-components:
      - Breakout Magnitude    (0–8):  how far close broke above 20-day high
      - Volume Confirmation   (0–7):  volume ratio on the breakout candle
      - Candle Quality        (0–5):  body % of the breakout candle
    """
    MAX = 20

    close        = _safe(latest.get("close"))
    highest_20   = _safe(latest.get("HIGHEST_20"))
    volume_ratio = _safe(latest.get("VOLUME_RATIO"), 1.0)
    body_pct     = _safe(latest.get("CANDLE_BODY_PERCENT"))
    is_breakout  = bool(latest.get("BREAKOUT", False))

    breakdown = {}

    # ── Breakout Magnitude (0–8) ─────────────────────────────────
    if highest_20 > 0:
        breakout_pct = ((close - highest_20) / highest_20) * 100
        # Even a tiny break gets some credit; big breaks (>3%) near full
        mag_score = _sigmoid_scale(breakout_pct, 1.0, 1.5, 8)
    else:
        mag_score = 0.0
    breakdown["breakout_magnitude"] = _clamp(mag_score, 0, 8)

    # ── Volume Confirmation (0–7) ────────────────────────────────
    # volume_ratio: 1.0 = average, >2.0 = very strong
    vol_score = _linear_scale(volume_ratio, 0.8, 2.5, 0, 7)
    breakdown["volume_confirmation"] = _clamp(vol_score, 0, 7)

    # ── Candle Quality (0–5) ─────────────────────────────────────
    # body_pct 0→1: higher = more decisive bullish close
    candle_score = _linear_scale(body_pct, 0.3, 0.85, 0, 5)
    breakdown["candle_quality"] = _clamp(candle_score, 0, 5)

    # Penalty: if confirmed breakout flag is False, dampen scores
    if not is_breakout:
        for k in breakdown:
            breakdown[k] *= 0.4

    raw   = sum(breakdown.values())
    final = _clamp(raw, 0, MAX)
    return {"score": round(final, 2), "max": MAX, "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# 3. VOLUME  (max 15)
# ─────────────────────────────────────────────────────────────────────────────

def score_volume(latest: dict) -> dict:
    """
    Sub-components:
      - Volume Ratio          (0–8):  current vs 20-day average
      - Volume Trend          (0–7):  volume direction (expanding vs shrinking)
    """
    MAX = 15

    volume_ratio    = _safe(latest.get("VOLUME_RATIO"), 1.0)
    # VOLUME_TREND: pass in (vol_ratio - prev_vol_ratio) if available
    # Fallback: use volume_ratio itself as proxy for trend
    volume_trend    = _safe(latest.get("VOLUME_TREND"), 0.0)

    breakdown = {}

    # ── Volume Ratio (0–8) ───────────────────────────────────────
    # 1.0 = neutral, 2.0 = good, 3.0+ = exceptional
    ratio_score = _sigmoid_scale(volume_ratio, 1.5, 2.0, 8)
    breakdown["volume_ratio"] = _clamp(ratio_score, 0, 8)

    # ── Volume Trend (0–7) ───────────────────────────────────────
    # Positive trend = expanding volume = bullish confirmation
    # volume_trend > 0 means volume is growing vs prior candles
    trend_score = _linear_scale(volume_trend, -0.3, 0.5, 0, 7)
    breakdown["volume_trend"] = _clamp(trend_score, 0, 7)

    raw   = sum(breakdown.values())
    final = _clamp(raw, 0, MAX)
    return {"score": round(final, 2), "max": MAX, "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# 4. MOMENTUM  (max 15)
# ─────────────────────────────────────────────────────────────────────────────

def score_momentum(latest: dict) -> dict:
    """
    Sub-components:
      - RSI Zone              (0–6):  RSI in bullish but not overbought zone
      - MACD Signal           (0–5):  histogram strength + crossover
      - Close Near High       (0–4):  bullish close position in candle range
    """
    MAX = 15

    rsi          = _safe(latest.get("RSI"), 50)
    macd_hist    = _safe(latest.get("MACD_HIST"))
    macd         = _safe(latest.get("MACD"))
    macd_signal  = _safe(latest.get("MACD_SIGNAL"))
    close_near_h = _safe(latest.get("CLOSE_NEAR_HIGH"), 0.5)  # 0=at high, 1=at low

    breakdown = {}

    # ── RSI Zone (0–6) ───────────────────────────────────────────
    # Sweet spot for swing buys: RSI 50–70 (momentum without overbought)
    # Below 50: weak, Above 75: overbought risk
    if rsi < 40:
        rsi_score = _linear_scale(rsi, 20, 40, 0, 1)   # Very weak
    elif rsi <= 55:
        rsi_score = _linear_scale(rsi, 40, 55, 1, 4)   # Building momentum
    elif rsi <= 70:
        rsi_score = _linear_scale(rsi, 55, 70, 4, 6)   # Ideal zone
    else:
        rsi_score = _linear_scale(rsi, 70, 85, 6, 2)   # Overbought decay
    breakdown["rsi_zone"] = _clamp(rsi_score, 0, 6)

    # ── MACD Signal (0–5) ────────────────────────────────────────
    # Positive histogram = bullish, stronger histogram = stronger signal
    # Also reward when MACD > Signal (bullish crossover zone)
    macd_score = 0.0
    if macd_hist > 0:
        # Scale histogram strength (normalize loosely)
        macd_score += _sigmoid_scale(macd_hist, 0.05, 30, 3)
    if macd > macd_signal:
        macd_score += 2.0
    breakdown["macd_signal"] = _clamp(macd_score, 0, 5)

    # ── Close Near High (0–4) ────────────────────────────────────
    # close_near_high: 0 = closed at high (best), 1 = closed at low (worst)
    cnh_score = _linear_scale(close_near_h, 0.5, 0.0, 0, 4)  # inverted
    breakdown["close_near_high"] = _clamp(cnh_score, 0, 4)

    raw   = sum(breakdown.values())
    final = _clamp(raw, 0, MAX)
    return {"score": round(final, 2), "max": MAX, "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# 5. RELATIVE STRENGTH  (max 10)
# ─────────────────────────────────────────────────────────────────────────────

def score_relative_strength(latest: dict) -> dict:
    """
    Sub-components:
      - RS vs Nifty           (0–7):  stock return / nifty return ratio
      - Distance from EMA20   (0–3):  reward pullbacks to EMA for entries
    """
    MAX = 10

    rs             = _safe(latest.get("RELATIVE_STRENGTH"), 1.0)
    dist_ema20     = _safe(latest.get("DISTANCE_FROM_EMA20"))  # % above/below EMA20

    breakdown = {}

    # ── RS vs Nifty (0–7) ────────────────────────────────────────
    # RS > 1.0 = outperforming Nifty
    # RS 1.0   = in-line, RS < 1.0 = underperforming
    rs_score = _sigmoid_scale(rs, 1.05, 12, 7)
    breakdown["rs_vs_nifty"] = _clamp(rs_score, 0, 7)

    # ── Distance from EMA20 (0–3) ────────────────────────────────
    # Best swing entry: price pulled back near EMA20 (dist ~0 to +3%)
    # Too far above = chasing, below = weak
    if dist_ema20 < -5:
        dist_score = 0.0                                         # Below EMA20: weak
    elif dist_ema20 <= 0:
        dist_score = _linear_scale(dist_ema20, -5, 0, 0.5, 2)  # Slight pullback
    elif dist_ema20 <= 3:
        dist_score = _linear_scale(dist_ema20, 0, 3, 2, 3)     # Just above EMA20: ideal
    else:
        dist_score = _linear_scale(dist_ema20, 3, 10, 3, 0.5)  # Stretched above
    breakdown["distance_from_ema20"] = _clamp(dist_score, 0, 3)

    raw   = sum(breakdown.values())
    final = _clamp(raw, 0, MAX)
    return {"score": round(final, 2), "max": MAX, "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# 6. STRUCTURE  (max 5)
# ─────────────────────────────────────────────────────────────────────────────

def score_structure(latest: dict) -> dict:
    """
    Sub-components:
      - Bullish Structure     (0–3):  higher highs + higher lows
      - Trend Alignment       (0–2):  EMA20 > EMA50 > EMA200
    """
    MAX = 5

    bullish_structure = bool(latest.get("BULLISH_STRUCTURE", False))
    trend_alignment   = bool(latest.get("TREND_ALIGNMENT", False))

    # Use HIGHER_HIGH and HIGHER_LOW individually for partial credit
    higher_high = bool(latest.get("HIGHER_HIGH", False))
    higher_low  = bool(latest.get("HIGHER_LOW", False))

    breakdown = {}

    # ── Bullish Structure (0–3) ──────────────────────────────────
    struct_score = 0.0
    if higher_high:
        struct_score += 1.5
    if higher_low:
        struct_score += 1.5
    breakdown["bullish_structure"] = _clamp(struct_score, 0, 3)

    # ── Trend Alignment (0–2) ────────────────────────────────────
    breakdown["trend_alignment"] = 2.0 if trend_alignment else 0.0

    raw   = sum(breakdown.values())
    final = _clamp(raw, 0, MAX)
    return {"score": round(final, 2), "max": MAX, "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# 7. VOLATILITY  (max 5)
# ─────────────────────────────────────────────────────────────────────────────

def score_volatility(latest: dict) -> dict:
    """
    Swing trading wants moderate ATR — not too quiet (no movement),
    not too wild (uncontrollable risk).

    Sub-components:
      - ATR % Sweet Spot      (0–3):  ideal ATR range for swing trades
      - Range Compression     (0–2):  tight 20-day range = coiled spring
    """
    MAX = 5

    atr_pct      = _safe(latest.get("ATR_PERCENT"))    # ATR as % of price
    range_pct    = _safe(latest.get("RANGE_PERCENT"))  # 20-day H-L as % of low

    breakdown = {}

    # ── ATR % Sweet Spot (0–3) ───────────────────────────────────
    # Ideal swing ATR: 1.5% – 4% of price
    # Too low (<0.8%): dead stock, Too high (>6%): too risky
    if atr_pct < 0.8:
        atr_score = _linear_scale(atr_pct, 0, 0.8, 0, 0.5)
    elif atr_pct <= 1.5:
        atr_score = _linear_scale(atr_pct, 0.8, 1.5, 0.5, 1.5)
    elif atr_pct <= 4.0:
        atr_score = _linear_scale(atr_pct, 1.5, 4.0, 1.5, 3.0)  # Sweet spot
    else:
        atr_score = _linear_scale(atr_pct, 4.0, 8.0, 3.0, 0.5)  # Too volatile
    breakdown["atr_sweet_spot"] = _clamp(atr_score, 0, 3)

    # ── Range Compression (0–2) ──────────────────────────────────
    # Tighter 20-day range = stock is coiling = potential energy for breakout
    # range_pct < 8%: very tight (good), > 20%: wide & choppy (bad)
    compression_score = _linear_scale(range_pct, 20, 5, 0, 2)
    breakdown["range_compression"] = _clamp(compression_score, 0, 2)

    raw   = sum(breakdown.values())
    final = _clamp(raw, 0, MAX)
    return {"score": round(final, 2), "max": MAX, "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# 8. MARKET TREND  (max 5)
# ─────────────────────────────────────────────────────────────────────────────

def score_market_trend(latest: dict) -> dict:
    """
    Sub-components:
      - Market Bullish        (0–3):  Nifty above EMA20, EMA20 > EMA50
      - RS in Bull Market     (0–2):  extra credit if stock is RS > 1 in bull mkt
    """
    MAX = 5

    market_bullish = bool(latest.get("MARKET_BULLISH", False))
    rs             = _safe(latest.get("RELATIVE_STRENGTH"), 1.0)

    breakdown = {}

    # ── Market Bullish (0–3) ─────────────────────────────────────
    breakdown["market_bullish"] = 3.0 if market_bullish else 0.0

    # ── RS in Bull Market (0–2) ──────────────────────────────────
    # Only reward RS leadership when market itself is bullish
    if market_bullish and rs > 1.0:
        rs_bull_score = _linear_scale(rs, 1.0, 1.3, 0, 2)
    else:
        rs_bull_score = 0.0
    breakdown["rs_in_bull_market"] = _clamp(rs_bull_score, 0, 2)

    raw   = sum(breakdown.values())
    final = _clamp(raw, 0, MAX)
    return {"score": round(final, 2), "max": MAX, "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# MASTER SCORER
# ─────────────────────────────────────────────────────────────────────────────

SIGNAL_THRESHOLDS = {
    "STRONG BUY":  80,
    "BUY":         65,
    "WEAK BUY":    50,
    "NEUTRAL":     35,
    "AVOID":        0,
}


def get_signal(total_score: float) -> str:
    for label, threshold in SIGNAL_THRESHOLDS.items():
        if total_score >= threshold:
            return label
    return "AVOID"


def score_stock(latest: dict, df = None, market_bullish = None) -> dict:
    """
    Master function — pass in the latest row of your indicators DataFrame.
    Returns full score breakdown + signal.

    Usage:
        latest = df.iloc[-1].to_dict()
        result = score_stock(latest)
        print(result["signal"], result["total_score"])
    """
    components = {
        "trend":             score_trend(latest),
        "breakout":          score_breakout(latest),
        "volume":            score_volume(latest),
        "momentum":          score_momentum(latest),
        "relative_strength": score_relative_strength(latest),
        "structure":         score_structure(latest),
        "volatility":        score_volatility(latest),
        "market_trend":      score_market_trend(latest),
    }

    total_score = sum(c["score"] for c in components.values())
    total_max   = sum(c["max"]   for c in components.values())  # should be 100

    signal = get_signal(total_score)

    # Per-component score percentage (for UI display)
    component_pct = {
        name: round((c["score"] / c["max"]) * 100, 1) if c["max"] > 0 else 0.0
        for name, c in components.items()
    }

    result = {
        "total_score":   round(total_score, 2),
        "total_max":     total_max,
        "signal":        signal,
        "components":    components,
        "component_pct": component_pct,
    }

    logger.info(
        f"[SCORE] {signal} | Total: {total_score:.1f}/{total_max} | "
        + " | ".join(f"{k}: {v['score']:.1f}" for k, v in components.items())
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# VOLUME TREND HELPER  (call before score_stock)
# ─────────────────────────────────────────────────────────────────────────────

def add_volume_trend(df):
    """
    Compute VOLUME_TREND column = rolling change in volume ratio.
    Call this once after calculate_indicators(), before scoring.
    """
    df["VOLUME_TREND"] = df["VOLUME_RATIO"].diff(3).fillna(0)
    return df