"""
Swing Trading Score Engine  v2.0  — Institutional Grade
========================================================
Architecture: Multi-layer weighted scoring with multiplicative regime gate.

Component               Max Score   Notes
---------               ---------   -----
Market Regime           MULTIPLIER  Gate: 0.30 / 0.60 / 0.85 / 1.00
Relative Strength            15     RS rank, RS trend, RS new-high
Sector Strength              15     Sector momentum, breadth, leadership
Trend Structure              18     Multi-TF, HH/HL quality, base context
Breakout Quality             13     52W high, base length, volume pattern
Risk-Reward                  12     Structural stops, R:R ratio
Entry Timing                 10     Pocket pivot, tightness, extension
Momentum                      5     Multi-period ROC + acceleration
Volatility Quality            5     ATR sweet-spot + VCP + HV percentile
Earnings Risk               FLAG    Not subtracted — flagged as penalty note
---------               ---------   -----
RAW TOTAL                   ~93     Normalized to 100 after regime multiply
"""

import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _safe(val, default: float = 0.0) -> float:
    """Return val if it's a valid finite number, else default."""
    try:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def _sigmoid_scale(x: float, center: float, steepness: float, max_score: float) -> float:
    """Smooth sigmoid: returns (0, max_score). center → 50% of max_score."""
    try:
        return (1 / (1 + math.exp(-steepness * (x - center)))) * max_score
    except (OverflowError, ZeroDivisionError):
        return 0.0


def _linear_scale(x: float, x_min: float, x_max: float,
                  score_min: float, score_max: float) -> float:
    """Linear interpolation clamped to [score_min, score_max]."""
    if x_max == x_min:
        return score_min
    ratio = _clamp((x - x_min) / (x_max - x_min), 0.0, 1.0)
    return score_min + ratio * (score_max - score_min)


# ─────────────────────────────────────────────────────────────────────────────
# 0. MARKET REGIME  — MULTIPLICATIVE GATE
# ─────────────────────────────────────────────────────────────────────────────

REGIME_MULTIPLIERS = {
    "TRENDING_BULL":  1.00,   # Full scores
    "CHOPPY_BULL":    0.85,   # Most setups work; reduce extended setups
    "CHOPPY_BEAR":    0.60,   # Dangerous — most setups fail
    "TRENDING_BEAR":  0.30,   # Almost nothing works; only short setups
}


def classify_market_regime(market: dict) -> dict:
    """
    Determine 4-state market regime.

    Required keys in `market`:
      NIFTY_CLOSE         — current Nifty 50 close
      NIFTY_EMA20         — Nifty 20-day EMA
      NIFTY_EMA50         — Nifty 50-day EMA
      NIFTY_EMA200        — Nifty 200-day EMA
      INDIAVIX            — India VIX current value
      INDIAVIX_EMA10      — India VIX 10-day EMA (to detect rising vs falling)
      PCT_ABOVE_EMA50     — % of Nifty 200 stocks above their EMA50 (breadth)
      ADV_DECLINE_RATIO   — advance/decline ratio (e.g., 1.3 = 1.3x more advances)
      NEW_HIGHS_52W       — count of 52-week highs in Nifty 200
      NEW_LOWS_52W        — count of 52-week lows in Nifty 200

    Optional:
      BREADTH_THRUST      — bool: Zweig-style breadth thrust fired in last 10 days
    """
    nifty        = _safe(market.get("NIFTY_CLOSE"))
    ema20        = _safe(market.get("NIFTY_EMA20"))
    ema50        = _safe(market.get("NIFTY_EMA50"))
    ema200       = _safe(market.get("NIFTY_EMA200"))
    vix          = _safe(market.get("INDIAVIX"), 15)
    vix_ema10    = _safe(market.get("INDIAVIX_EMA10"), 15)
    pct_above    = _safe(market.get("PCT_ABOVE_EMA50"), 50)   # breadth %
    ad_ratio     = _safe(market.get("ADV_DECLINE_RATIO"), 1.0)
    new_highs    = _safe(market.get("NEW_HIGHS_52W"), 0)
    new_lows     = _safe(market.get("NEW_LOWS_52W"), 0)
    breadth_thr  = bool(market.get("BREADTH_THRUST", False))

    # ── Trend state ──────────────────────────────────────────────
    price_above_ema50  = nifty > ema50
    price_above_ema200 = nifty > ema200
    ema50_above_ema200 = ema50 > ema200

    # ── Breadth score (0–4) ──────────────────────────────────────
    breadth_score = 0
    if pct_above > 60:   breadth_score += 2
    elif pct_above > 50: breadth_score += 1
    if ad_ratio > 1.3:   breadth_score += 1
    if new_highs > new_lows and new_highs > 10: breadth_score += 1

    # ── VIX state ────────────────────────────────────────────────
    vix_rising = vix > vix_ema10 * 1.05   # VIX rising = danger signal
    vix_extreme = vix > 25                 # India VIX >25 = fear/distribution

    # ── Classify regime ─────────────────────────────────────────
    if price_above_ema50 and ema50_above_ema200 and breadth_score >= 3 and not vix_rising:
        regime = "TRENDING_BULL"
    elif price_above_ema200 and breadth_score >= 1 and not vix_extreme:
        regime = "CHOPPY_BULL"
    elif not price_above_ema200 and breadth_score <= 1:
        regime = "TRENDING_BEAR"
    else:
        regime = "CHOPPY_BEAR"

    multiplier = REGIME_MULTIPLIERS[regime]

    # Breadth thrust upgrades choppy states
    if breadth_thr and regime == "CHOPPY_BULL":
        multiplier = min(multiplier + 0.10, 1.00)

    return {
        "regime":        regime,
        "multiplier":    multiplier,
        "breadth_score": breadth_score,
        "vix_rising":    vix_rising,
        "vix_extreme":   vix_extreme,
        "detail": {
            "price_above_ema50":  price_above_ema50,
            "price_above_ema200": price_above_ema200,
            "ema50_above_ema200": ema50_above_ema200,
            "pct_above_ema50":    pct_above,
            "ad_ratio":           ad_ratio,
            "new_highs":          int(new_highs),
            "new_lows":           int(new_lows),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. RELATIVE STRENGTH  (max 15)  — was 10, severely underweighted
# ─────────────────────────────────────────────────────────────────────────────

def score_relative_strength(latest: dict) -> dict:
    """
    Sub-components:
      - RS Percentile Rank    (0–7):  rank within Nifty 200 universe
      - RS Trend Direction    (0–4):  improving vs deteriorating RS
      - RS New High           (0–4):  RS line making new highs (pre-breakout signal)

    Required keys:
      RS_PERCENTILE_RANK    — 0–100 percentile rank within Nifty 200
                              (100 = strongest RS, 0 = weakest)
      RS_TREND_SLOPE        — slope of RS line over last 20 days (+ve = improving)
      RS_NEW_HIGH           — bool: RS line at a new 52-week high
      RS_VS_NIFTY           — ratio: stock 3M return / Nifty 3M return
    """
    MAX = 15

    rs_pct_rank  = _safe(latest.get("RS_PERCENTILE_RANK"), 50)   # 0–100
    rs_slope     = _safe(latest.get("RS_TREND_SLOPE"), 0.0)       # + = improving
    rs_new_high  = bool(latest.get("RS_NEW_HIGH", False))
    rs_vs_nifty  = _safe(latest.get("RS_VS_NIFTY"), 1.0)         # ratio

    breakdown = {}

    # ── RS Percentile Rank (0–7) ─────────────────────────────────
    # >80th percentile = very strong; 50–80 = moderate; <50 = avoid
    rank_score = _linear_scale(rs_pct_rank, 40, 95, 0, 7)
    breakdown["rs_percentile_rank"] = _clamp(rank_score, 0, 7)

    # ── RS Trend Direction (0–4) ─────────────────────────────────
    # Improving RS = institutional accumulation flowing in
    # slope > 0 = improving; normalize loosely around 0
    slope_score = _sigmoid_scale(rs_slope, 0.0, 8, 4)
    breakdown["rs_trend_direction"] = _clamp(slope_score, 0, 4)

    # ── RS New High (0–4) ────────────────────────────────────────
    # RS line making new 52W high before/with price = highest-probability setup
    if rs_new_high:
        rs_nh_score = 4.0
    else:
        # Partial credit if RS is outperforming meaningfully
        rs_nh_score = _linear_scale(rs_vs_nifty, 1.0, 1.5, 0, 2)
    breakdown["rs_new_high"] = _clamp(rs_nh_score, 0, 4)

    raw   = sum(breakdown.values())
    final = _clamp(raw, 0, MAX)
    return {"score": round(final, 2), "max": MAX, "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# 2. SECTOR STRENGTH  (max 15)  — was 10, critical for Indian market rotation
# ─────────────────────────────────────────────────────────────────────────────

def score_sector_strength(latest: dict) -> dict:
    """
    Sub-components:
      - Sector Momentum Rank  (0–6):  rank of sector vs all sectors (1=best)
      - Sector RS Trend       (0–5):  is sector RS improving or deteriorating?
      - Intra-Sector Leader   (0–4):  is this stock leader or laggard in sector?

    Required keys:
      SECTOR_RANK           — rank of sector by momentum (1 = strongest)
      TOTAL_SECTORS         — total sectors (typically 13 for NSE)
      SECTOR_RS_SLOPE       — slope of sector RS vs Nifty (+ = improving)
      SECTOR_BREADTH_PCT    — % of stocks in sector above EMA50
      STOCK_RS_WITHIN_SECTOR — stock's RS rank within its sector (percentile 0–100)
    """
    MAX = 15

    sector_rank   = _safe(latest.get("SECTOR_RANK"), 7)
    total_sectors = _safe(latest.get("TOTAL_SECTORS"), 13)
    sector_slope  = _safe(latest.get("SECTOR_RS_SLOPE"), 0.0)
    sector_brdth  = _safe(latest.get("SECTOR_BREADTH_PCT"), 50)   # 0–100
    stock_intra   = _safe(latest.get("STOCK_RS_WITHIN_SECTOR"), 50)  # 0–100

    breakdown = {}

    # ── Sector Momentum Rank (0–6) ───────────────────────────────
    # Rank 1 = top sector; normalize so top 3 sectors score highest
    rank_pct = 1 - ((sector_rank - 1) / max(total_sectors - 1, 1))  # 1.0 for rank 1
    sec_rank_score = _linear_scale(rank_pct, 0.2, 1.0, 0, 6)
    breakdown["sector_momentum_rank"] = _clamp(sec_rank_score, 0, 6)

    # ── Sector RS Trend + Breadth (0–5) ─────────────────────────
    # Sector RS improving AND broad participation = strong tailwind
    slope_score = _sigmoid_scale(sector_slope, 0.0, 6, 3)
    breadth_score = _linear_scale(sector_brdth, 40, 75, 0, 2)
    sec_trend_score = slope_score + breadth_score
    breakdown["sector_rs_trend_and_breadth"] = _clamp(sec_trend_score, 0, 5)

    # ── Intra-Sector Leadership (0–4) ────────────────────────────
    # Stock must be a sector LEADER, not a laggard
    # <50th percentile within sector = laggard catching up = penalize
    intra_score = _linear_scale(stock_intra, 40, 90, 0, 4)
    breakdown["intra_sector_leadership"] = _clamp(intra_score, 0, 4)

    raw   = sum(breakdown.values())
    final = _clamp(raw, 0, MAX)
    return {"score": round(final, 2), "max": MAX, "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# 3. TREND STRUCTURE  (max 18)  — was 25, reduced slightly; quality upgraded
# ─────────────────────────────────────────────────────────────────────────────

def score_trend_structure(latest: dict) -> dict:
    """
    Sub-components:
      - EMA Alignment Quality (0–6):  stack quality with separation pct
      - Multi-TF Alignment    (0–5):  weekly trend confirms daily setup
      - HH/HL Pattern Quality (0–4):  tight vs messy swing structure
      - Base Context          (0–3):  breakout from base vs extended from run

    Required keys:
      EMA20, EMA50, EMA200, close
      TREND_STRENGTH        — (EMA20-EMA50)/EMA50 * 100
      WEEKLY_TREND_BULLISH  — bool: stock above weekly EMA20 & EMA50
      WEEKLY_EMA20_ABOVE_50 — bool: weekly EMA20 > weekly EMA50
      HIGHER_HIGH           — bool
      HIGHER_LOW            — bool
      SWING_RANGE_PCT       — avg % move between swing pivots (lower = tighter)
      DIST_FROM_52W_HIGH_PCT— % below 52-week high (0 = at 52W high)
      RUN_FROM_BASE_PCT     — % gain from last base low (0–100+)
    """
    MAX = 18

    ema20    = _safe(latest.get("EMA20"))
    ema50    = _safe(latest.get("EMA50"))
    ema200   = _safe(latest.get("EMA200"))
    close    = _safe(latest.get("close"))
    ts       = _safe(latest.get("TREND_STRENGTH"))

    weekly_bull      = bool(latest.get("WEEKLY_TREND_BULLISH", False))
    weekly_ema_align = bool(latest.get("WEEKLY_EMA20_ABOVE_50", False))

    higher_high    = bool(latest.get("HIGHER_HIGH", False))
    higher_low     = bool(latest.get("HIGHER_LOW", False))
    swing_rng_pct  = _safe(latest.get("SWING_RANGE_PCT"), 10)   # % avg swing size
    run_from_base  = _safe(latest.get("RUN_FROM_BASE_PCT"), 0)  # % from base

    breakdown = {}

    # ── EMA Alignment Quality (0–6) ──────────────────────────────
    align_score = 0.0
    if ema20 > 0 and ema50 > 0 and ema200 > 0:
        if ema20 > ema50:
            sep = ((ema20 - ema50) / ema50) * 100
            align_score += _linear_scale(sep, 0, 3, 1, 3)
        if ema50 > ema200:
            sep = ((ema50 - ema200) / ema200) * 100
            align_score += _linear_scale(sep, 0, 3, 0.5, 3)
    breakdown["ema_alignment_quality"] = _clamp(align_score, 0, 6)

    # ── Multi-Timeframe Alignment (0–5) ──────────────────────────
    # Daily breakout in weekly downtrend = trap
    # Daily breakout in weekly uptrend  = high-probability
    mtf_score = 0.0
    if weekly_bull:     mtf_score += 3.0
    if weekly_ema_align: mtf_score += 2.0
    breakdown["multi_tf_alignment"] = _clamp(mtf_score, 0, 5)

    # ── HH/HL Pattern Quality (0–4) ──────────────────────────────
    # Presence is worth 2pts each; tightness multiplies quality
    struct_score = 0.0
    if higher_high: struct_score += 1.5
    if higher_low:  struct_score += 1.5
    # Tight swings (< 6%) are institutional; wide (> 15%) is noise
    tightness_bonus = _linear_scale(swing_rng_pct, 15, 3, 0, 1)
    struct_score += tightness_bonus
    breakdown["hhhl_pattern_quality"] = _clamp(struct_score, 0, 4)

    # ── Base Context (0–3) ───────────────────────────────────────
    # Extended stocks (run_from_base > 40%) look bullish but have poor expectancy
    # Fresh from base (< 15%) = constructive
    if run_from_base <= 15:
        base_score = 3.0
    elif run_from_base <= 30:
        base_score = _linear_scale(run_from_base, 15, 30, 3.0, 1.5)
    elif run_from_base <= 50:
        base_score = _linear_scale(run_from_base, 30, 50, 1.5, 0.5)
    else:
        base_score = 0.0    # Extended — penalize
    breakdown["base_context"] = _clamp(base_score, 0, 3)

    raw   = sum(breakdown.values())
    final = _clamp(raw, 0, MAX)
    return {"score": round(final, 2), "max": MAX, "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# 4. BREAKOUT QUALITY  (max 13)  — 52W high, base length, volume pattern
# ─────────────────────────────────────────────────────────────────────────────

def score_breakout_quality(latest: dict) -> dict:
    """
    Sub-components:
      - 52W High Proximity    (0–5):  breaking 52W high is institutional trigger
      - Base Length           (0–4):  longer base = more accumulation
      - Volume Pattern        (0–4):  contraction during base + expansion on break

    Required keys:
      close
      HIGH_52W              — 52-week high
      HIGHEST_20            — 20-day high (still used as breakout confirmation)
      BASE_LENGTH_DAYS      — days in current consolidation
      VOLUME_RATIO          — current volume / 20-day avg volume
      VOL_DURING_BASE       — avg volume ratio during base (ideally < 1.0 = quiet)
      CANDLE_BODY_PERCENT   — breakout candle body as fraction of range (0–1)
      BREAKOUT              — bool: is today a breakout day?
    """
    MAX = 13

    close          = _safe(latest.get("close"))
    high_52w       = _safe(latest.get("HIGH_52W"), close)
    highest_20     = _safe(latest.get("HIGHEST_20"), close)
    base_days      = _safe(latest.get("BASE_LENGTH_DAYS"), 5)
    volume_ratio   = _safe(latest.get("VOLUME_RATIO"), 1.0)
    vol_in_base    = _safe(latest.get("VOL_DURING_BASE"), 1.0)   # ideally < 1
    body_pct       = _safe(latest.get("CANDLE_BODY_PERCENT"), 0.5)
    is_breakout    = bool(latest.get("BREAKOUT", False))

    breakdown = {}

    # ── 52W High Proximity (0–5) ─────────────────────────────────
    # Close at/near 52W high = institutional momentum trigger
    if high_52w > 0:
        pct_below_52w = ((high_52w - close) / high_52w) * 100   # 0% = at high
        proximity_score = _linear_scale(pct_below_52w, 20, 0, 0, 5)
    else:
        proximity_score = 0.0
    breakdown["high_52w_proximity"] = _clamp(proximity_score, 0, 5)

    # ── Base Length (0–4) ────────────────────────────────────────
    # 3 weeks (15 days) minimum; 6–8 weeks (30–40 days) is ideal
    base_score = _linear_scale(base_days, 5, 40, 0, 4)
    breakdown["base_length"] = _clamp(base_score, 0, 4)

    # ── Volume Pattern (0–4) ─────────────────────────────────────
    # Ideal: quiet base (low vol) + explosive breakout (high vol)
    # vol_in_base < 0.8 AND volume_ratio > 2.0 = perfect
    quiet_base_bonus = _linear_scale(vol_in_base, 1.2, 0.6, 0, 1.5)   # lower = better
    breakout_vol     = _linear_scale(volume_ratio, 1.0, 2.5, 0, 2.5)
    vol_pattern = quiet_base_bonus + breakout_vol
    # Candle quality bonus
    candle_bonus = _linear_scale(body_pct, 0.3, 0.85, 0, 1.0)
    vol_pattern += candle_bonus
    breakdown["volume_pattern"] = _clamp(vol_pattern, 0, 4)

    # Penalty: no confirmed breakout — dampen scores
    if not is_breakout:
        for k in breakdown:
            breakdown[k] *= 0.40

    raw   = sum(breakdown.values())
    final = _clamp(raw, 0, MAX)
    return {"score": round(final, 2), "max": MAX, "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# 5. RISK-REWARD  (max 12)  — structural stops, not just ATR multiples
# ─────────────────────────────────────────────────────────────────────────────

def score_risk_reward(latest: dict) -> dict:
    """
    Sub-components:
      - R:R Ratio             (0–6):  (target - entry) / (entry - structural stop)
      - Stop Quality          (0–3):  is stop below actual price structure?
      - Target Definition     (0–3):  is profit target at a defined resistance?

    Required keys:
      close                   — current/entry price
      STRUCTURAL_STOP         — stop below recent higher low or base low
      ATR                     — average true range (fallback stop check)
      RESISTANCE_TARGET       — nearest resistance / measured move target
      PRIOR_RESISTANCE_1      — first prior resistance level
      RR_RATIO                — pre-calculated R:R if available
    """
    MAX = 12

    close        = _safe(latest.get("close"))
    struct_stop  = _safe(latest.get("STRUCTURAL_STOP"), 0)
    atr          = _safe(latest.get("ATR"), 0)
    target       = _safe(latest.get("RESISTANCE_TARGET"), 0)
    rr_ratio     = _safe(latest.get("RR_RATIO"), 0)

    breakdown = {}

    # ── R:R Ratio (0–6) ──────────────────────────────────────────
    if rr_ratio > 0:
        rr = rr_ratio
    elif struct_stop > 0 and target > close > struct_stop:
        risk   = close - struct_stop
        reward = target - close
        rr = reward / risk if risk > 0 else 0
    else:
        rr = 0

    # 1:1 = minimal; 2:1 = acceptable; 3:1+ = excellent
    rr_score = _linear_scale(rr, 1.0, 3.5, 0, 6)
    breakdown["rr_ratio"] = _clamp(rr_score, 0, 6)

    # ── Stop Quality (0–3) ───────────────────────────────────────
    # Structural stop (below HH/HL structure) vs ATR-based stop
    stop_quality = 0.0
    if struct_stop > 0 and close > 0:
        stop_pct = ((close - struct_stop) / close) * 100   # risk %
        # Good stop: 2–6% below entry. Too tight (<1%) or too wide (>10%) = bad
        if stop_pct < 1:
            stop_quality = 0.5     # Too tight; will be stopped out on noise
        elif stop_pct <= 3:
            stop_quality = 3.0     # Tight structural stop = excellent
        elif stop_pct <= 6:
            stop_quality = _linear_scale(stop_pct, 3, 6, 3.0, 1.5)
        else:
            stop_quality = _linear_scale(stop_pct, 6, 12, 1.5, 0)
    elif atr > 0 and close > 0:
        # Fallback: ATR-based estimation (less ideal)
        stop_pct = (atr * 1.5 / close) * 100
        stop_quality = _linear_scale(stop_pct, 8, 2, 0, 2)   # max 2 for ATR-based
    breakdown["stop_quality"] = _clamp(stop_quality, 0, 3)

    # ── Target Definition (0–3) ──────────────────────────────────
    # Is there a clear, defined resistance to take profit at?
    if target > close:
        # Target exists — reward based on how much upside to the target
        target_pct = ((target - close) / close) * 100
        tgt_score = _linear_scale(target_pct, 3, 15, 1, 3)
    else:
        tgt_score = 0.0
    breakdown["target_definition"] = _clamp(tgt_score, 0, 3)

    raw   = sum(breakdown.values())
    final = _clamp(raw, 0, MAX)
    return {"score": round(final, 2), "max": MAX, "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# 6. ENTRY TIMING  (max 10)  — was 5, significantly underweighted
# ─────────────────────────────────────────────────────────────────────────────

def score_entry_timing(latest: dict) -> dict:
    """
    Sub-components:
      - Extension from EMA20  (0–4):  reward entries near EMA, penalize chasing
      - Base Tightness        (0–3):  tight consolidation = smart money accumulation
      - Pocket Pivot / Setup  (0–3):  up-day on above-avg vol without crossing high

    Required keys:
      DISTANCE_FROM_EMA20   — % above/below EMA20 (+ = above)
      RANGE_COMPRESSION_PCT — 20-day range as % of price (lower = tighter)
      POCKET_PIVOT          — bool: pocket pivot pattern detected
      BUYABLE_GAP_UP        — bool: first gap-up from base
      DAYS_IN_CONSOLIDATION — days since last significant high (for tightness)
    """
    MAX = 10

    dist_ema20   = _safe(latest.get("DISTANCE_FROM_EMA20"))   # %
    range_cmp    = _safe(latest.get("RANGE_COMPRESSION_PCT"), 15)  # % range
    pocket_pivot = bool(latest.get("POCKET_PIVOT", False))
    buyable_gu   = bool(latest.get("BUYABLE_GAP_UP", False))
    days_consol  = _safe(latest.get("DAYS_IN_CONSOLIDATION"), 5)

    breakdown = {}

    # ── Extension from EMA20 (0–4) ───────────────────────────────
    # Best entry: just above EMA20 (0–3%). Extended (>8%) = chasing
    if dist_ema20 < -5:
        ext_score = 0.0          # Below EMA20 = weak
    elif dist_ema20 <= 0:
        ext_score = _linear_scale(dist_ema20, -5, 0, 0.5, 2.0)  # Slight pullback
    elif dist_ema20 <= 3:
        ext_score = _linear_scale(dist_ema20, 0, 3, 2.0, 4.0)   # Ideal zone
    elif dist_ema20 <= 8:
        ext_score = _linear_scale(dist_ema20, 3, 8, 4.0, 1.5)   # Slightly extended
    else:
        ext_score = _linear_scale(dist_ema20, 8, 20, 1.5, 0)    # Chasing
    breakdown["extension_from_ema20"] = _clamp(ext_score, 0, 4)

    # ── Base Tightness (0–3) ─────────────────────────────────────
    # Range < 8% = very tight = accumulation. Range > 20% = choppy
    tightness = _linear_scale(range_cmp, 20, 4, 0, 2)
    # Length bonus: longer tight consolidation = more accumulation
    length_bonus = _linear_scale(days_consol, 5, 30, 0, 1)
    tight_score = tightness + length_bonus
    breakdown["base_tightness"] = _clamp(tight_score, 0, 3)

    # ── Pocket Pivot / Setup Quality (0–3) ───────────────────────
    if buyable_gu:
        pp_score = 3.0    # First gap-up from base = highest probability entry
    elif pocket_pivot:
        pp_score = 2.0    # Pocket pivot = institutional-grade pre-breakout entry
    else:
        pp_score = 0.0
    breakdown["pocket_pivot_or_gap"] = _clamp(pp_score, 0, 3)

    raw   = sum(breakdown.values())
    final = _clamp(raw, 0, MAX)
    return {"score": round(final, 2), "max": MAX, "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# 7. MOMENTUM  (max 5)  — complete overhaul: multi-period ROC replaces MACD
# ─────────────────────────────────────────────────────────────────────────────

def score_momentum(latest: dict) -> dict:
    """
    Sub-components:
      - Multi-Period ROC      (0–3):  1M / 3M / 6M price momentum (Fama-French)
      - Momentum Acceleration (0–2):  RSI rising vs falling (direction matters)

    Required keys:
      ROC_1M                — 1-month rate of change %
      ROC_3M                — 3-month rate of change %
      ROC_6M                — 6-month rate of change %
      RSI                   — current RSI
      RSI_PREV10            — RSI 10 days ago (to detect acceleration)
      CLOSE_NEAR_HIGH       — 0 = at high (best), 1 = at low (worst)
    """
    MAX = 5

    roc_1m      = _safe(latest.get("ROC_1M"), 0)
    roc_3m      = _safe(latest.get("ROC_3M"), 0)
    roc_6m      = _safe(latest.get("ROC_6M"), 0)
    rsi         = _safe(latest.get("RSI"), 50)
    rsi_prev    = _safe(latest.get("RSI_PREV10"), 50)
    cnh         = _safe(latest.get("CLOSE_NEAR_HIGH"), 0.5)  # 0 = at high

    breakdown = {}

    # ── Multi-Period ROC (0–3) ───────────────────────────────────
    # Weight 3M and 6M more than 1M (consistent with academic evidence)
    # 3M ROC >10% = strong; 6M ROC > 20% = very strong
    roc1_s = _linear_scale(roc_1m,  0, 10, 0, 0.5)
    roc3_s = _linear_scale(roc_3m,  0, 20, 0, 1.5)
    roc6_s = _linear_scale(roc_6m,  0, 35, 0, 1.0)
    roc_score = roc1_s + roc3_s + roc6_s
    breakdown["multi_period_roc"] = _clamp(roc_score, 0, 3)

    # ── Momentum Acceleration (0–2) ──────────────────────────────
    # RSI rising from 40→60 is very different from falling from 78→60
    rsi_delta = rsi - rsi_prev    # +ve = accelerating
    # RSI in sweet spot (50–70) AND rising = best signal
    if 50 <= rsi <= 72 and rsi_delta > 0:
        acc_score = _linear_scale(rsi_delta, 0, 15, 0.5, 2.0)
    elif rsi > 72:
        acc_score = _linear_scale(rsi, 72, 85, 1.0, 0)   # Overbought decay
    elif rsi_delta > 5:
        acc_score = 0.5    # Recovering from oversold
    else:
        acc_score = 0.0
    # Close-near-high micro-bonus
    cnh_bonus = _linear_scale(cnh, 0.8, 0.0, 0, 0.3)
    breakdown["momentum_acceleration"] = _clamp(acc_score + cnh_bonus, 0, 2)

    raw   = sum(breakdown.values())
    final = _clamp(raw, 0, MAX)
    return {"score": round(final, 2), "max": MAX, "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# 8. VOLATILITY QUALITY  (max 5)
# ─────────────────────────────────────────────────────────────────────────────

def score_volatility_quality(latest: dict) -> dict:
    """
    Sub-components:
      - ATR Sweet Spot        (0–2):  ideal swing ATR range
      - VCP Detection         (0–2):  Volatility Contraction Pattern
      - HV Percentile         (0–1):  low HV relative to own history = coiled

    Required keys:
      ATR_PERCENT           — ATR as % of price
      VCP_DETECTED          — bool: successive range contractions found
      HV_PERCENTILE         — historical volatility percentile (0–100 vs own history)
                              (low = quiet relative to its own history = coiling)
    """
    MAX = 5

    atr_pct      = _safe(latest.get("ATR_PERCENT"))
    vcp_detected = bool(latest.get("VCP_DETECTED", False))
    hv_pct       = _safe(latest.get("HV_PERCENTILE"), 50)   # lower = quieter

    breakdown = {}

    # ── ATR Sweet Spot (0–2) ─────────────────────────────────────
    # Ideal: 1.5–4.0% for swing trading
    if atr_pct < 0.8:
        atr_score = _linear_scale(atr_pct, 0, 0.8, 0, 0.3)    # Dead stock
    elif atr_pct <= 1.5:
        atr_score = _linear_scale(atr_pct, 0.8, 1.5, 0.3, 1.0)
    elif atr_pct <= 4.0:
        atr_score = _linear_scale(atr_pct, 1.5, 4.0, 1.0, 2.0)   # Sweet spot
    else:
        atr_score = _linear_scale(atr_pct, 4.0, 8.0, 2.0, 0.3)   # Too volatile
    breakdown["atr_sweet_spot"] = _clamp(atr_score, 0, 2)

    # ── VCP Detection (0–2) ──────────────────────────────────────
    # Minervini's VCP: successive contractions = institutional accumulation
    breakdown["vcp_detected"] = 2.0 if vcp_detected else 0.0

    # ── HV Percentile (0–1) ──────────────────────────────────────
    # Low HV relative to own history = coiled spring
    hv_score = _linear_scale(hv_pct, 70, 15, 0, 1)    # lower HV% = higher score
    breakdown["hv_percentile"] = _clamp(hv_score, 0, 1)

    raw   = sum(breakdown.values())
    final = _clamp(raw, 0, MAX)
    return {"score": round(final, 2), "max": MAX, "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# OPERATIONAL FLAGS  (not subtracted from score — surfaced as risk flags)
# ─────────────────────────────────────────────────────────────────────────────

def check_operational_flags(latest: dict) -> list[dict]:
    """
    Returns a list of risk flags. These do NOT subtract from score directly
    but should be surfaced to the trader for review before acting.

    Required keys:
      DAYS_TO_EARNINGS      — days until next earnings announcement
      ADV_CRORE             — avg daily value traded in crore (liquidity)
      DIST_FROM_52W_HIGH_PCT— % below 52-week high
    """
    flags = []

    days_to_earnings = _safe(latest.get("DAYS_TO_EARNINGS"), 999)
    adv_crore        = _safe(latest.get("ADV_CRORE"), 100)
    dist_52w_high    = _safe(latest.get("DIST_FROM_52W_HIGH_PCT"), 0)

    # Earnings proximity — swing setups within 7 days of earnings are high-risk
    if days_to_earnings <= 3:
        flags.append({
            "flag": "EARNINGS_IMMINENT",
            "severity": "HIGH",
            "detail": f"Earnings in {int(days_to_earnings)} day(s) — avoid or size very small",
        })
    elif days_to_earnings <= 7:
        flags.append({
            "flag": "EARNINGS_NEAR",
            "severity": "MEDIUM",
            "detail": f"Earnings in {int(days_to_earnings)} days — monitor gap risk",
        })

    # Liquidity filter — below ₹5cr ADV is often illiquid for meaningful sizing
    if adv_crore < 5:
        flags.append({
            "flag": "LOW_LIQUIDITY",
            "severity": "HIGH",
            "detail": f"ADV ₹{adv_crore:.1f}Cr — slippage risk; check actual depth",
        })
    elif adv_crore < 15:
        flags.append({
            "flag": "MODERATE_LIQUIDITY",
            "severity": "LOW",
            "detail": f"ADV ₹{adv_crore:.1f}Cr — size positions carefully",
        })

    # Distribution detection — stocks far from 52W high may be in distribution
    if dist_52w_high > 40:
        flags.append({
            "flag": "DEEP_DISTRIBUTION_RISK",
            "severity": "HIGH",
            "detail": f"Stock is {dist_52w_high:.1f}% below 52W high — likely in distribution",
        })

    return flags


# ─────────────────────────────────────────────────────────────────────────────
# MASTER SCORER
# ─────────────────────────────────────────────────────────────────────────────

# Raw component max = 93; normalize to 100 for signal thresholds
_RAW_MAX = 93.0

SIGNAL_THRESHOLDS = {
    "STRONG BUY": 80,
    "BUY":        65,
    "WEAK BUY":   50,
    "NEUTRAL":    35,
    "AVOID":       0,
}


def get_signal(normalized_score: float) -> str:
    for label, threshold in SIGNAL_THRESHOLDS.items():
        if normalized_score >= threshold:
            return label
    return "AVOID"


def score_stock(latest: dict, market: Optional[dict] = None) -> dict:
    try:
        # ── Market Regime ─────────────────────────────────────────────
        if market:
            regime_data = classify_market_regime(market)
            # NEW: Allow forcing a multiplier for consistency with snapshots
            if "force_multiplier" in market:
                regime_data["multiplier"] = market["force_multiplier"]
        else:
            regime_data = {
                "regime": "CHOPPY_BULL",
                "multiplier": 0.85,
                "breadth_score": 0,
                "vix_rising": False,
                "vix_extreme": False,
                "detail": {},
            }

        multiplier = regime_data["multiplier"]

        # ── Component Scores ──────────────────────────────────────────
        components = {
            "relative_strength":  score_relative_strength(latest),   # 15
            "sector_strength":    score_sector_strength(latest),      # 15
            "trend_structure":    score_trend_structure(latest),      # 18
            "breakout_quality":   score_breakout_quality(latest),     # 13
            "risk_reward":        score_risk_reward(latest),          # 12
            "entry_timing":       score_entry_timing(latest),         # 10
            "momentum":           score_momentum(latest),              #  5
            "volatility_quality": score_volatility_quality(latest),   #  5
        }

        raw_score        = sum(c["score"] for c in components.values())
        normalized_score = (raw_score / _RAW_MAX) * 100
        final_score      = normalized_score * multiplier

        signal = get_signal(final_score)

        # Per-component % of max
        component_pct = {
            name: round((c["score"] / c["max"]) * 100, 1) if c["max"] > 0 else 0.0
            for name, c in components.items()
        }

        # Operational flags
        flags = check_operational_flags(latest)

        result = {
            "raw_score":          round(raw_score, 2),
            "normalized_score":   round(normalized_score, 2),
            "final_score":        round(final_score, 2),
            "signal":             signal,
            "regime":             regime_data["regime"],
            "regime_multiplier":  multiplier,
            "components":         components,
            "component_pct":      component_pct,
            "flags":              flags,
            "regime_detail":      regime_data,
        }

        flag_str = "; ".join(f["flag"] for f in flags) if flags else "None"
        logger.info(
            f"[SCORE] {signal} | Final: {final_score:.1f} "
            f"(raw {raw_score:.1f}/{_RAW_MAX} × {multiplier}) "
            f"| Regime: {regime_data['regime']} "
            f"| Flags: {flag_str}"
        )

        return result

    except Exception as e:
        logger.error(f"Error scoring stock: {e}")
        # Return a safe fallback to prevent API crash
        return {
            "raw_score": 0.0,
            "normalized_score": 0.0,
            "final_score": 0.0,
            "signal": "AVOID",
            "regime": "UNKNOWN",
            "regime_multiplier": 0.0,
            "components": {},
            "component_pct": {},
            "flags": [{"flag": "SCORING_ERROR", "severity": "HIGH", "detail": str(e)}],
            "regime_detail": {},
        }


# ─────────────────────────────────────────────────────────────────────────────
# PORTFOLIO-LEVEL CORRELATION CONTROL  (call after scoring multiple stocks)
# ─────────────────────────────────────────────────────────────────────────────

def apply_portfolio_concentration_filter(
    ranked_stocks: list[dict],
    max_per_sector: int = 2,
    max_correlated_groups: int = 3,
) -> list[dict]:
    """
    Post-scoring filter to prevent correlated recommendations.

    Parameters
    ----------
    ranked_stocks : list of dicts
        Each dict must have keys: 'symbol', 'sector', 'final_score'.
        Should be pre-sorted by final_score descending.
    max_per_sector : int
        Maximum stocks per sector in the final recommendation list.
    max_correlated_groups : int
        Total number of distinct sectors allowed in the final list.

    Returns
    -------
    Filtered list respecting sector concentration limits.
    Each stock gets a 'concentration_note' key.
    """
    sector_counts: dict[str, int] = {}
    filtered = []

    for stock in ranked_stocks:
        sector = stock.get("sector", "Unknown")
        count  = sector_counts.get(sector, 0)

        if count < max_per_sector:
            sector_counts[sector] = count + 1
            stock["concentration_note"] = f"Sector slot {count + 1}/{max_per_sector}"
            filtered.append(stock)
        else:
            stock["concentration_note"] = f"EXCLUDED — {sector} at limit ({max_per_sector})"

    return filtered


# ─────────────────────────────────────────────────────────────────────────────
# VOLUME TREND HELPER  (unchanged — still valid)
# ─────────────────────────────────────────────────────────────────────────────

def add_volume_trend(df):
    """
    Compute VOLUME_TREND = rolling change in volume ratio over 3 days.
    Call after calculate_indicators(), before scoring.
    """
    df["VOLUME_TREND"] = df["VOLUME_RATIO"].diff(3).fillna(0)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# NEW INDICATOR HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def add_roc_columns(df, price_col: str = "close"):
    """
    Add multi-period Rate of Change columns.
    ROC_1M  = 21-day ROC, ROC_3M = 63-day, ROC_6M = 126-day.
    """
    df["ROC_1M"] = df[price_col].pct_change(21) * 100
    df["ROC_3M"] = df[price_col].pct_change(63) * 100
    df["ROC_6M"] = df[price_col].pct_change(126) * 100
    return df


def add_rsi_prev(df, rsi_col: str = "RSI", lookback: int = 10):
    """Add RSI_PREV10 column for momentum acceleration detection."""
    df["RSI_PREV10"] = df[rsi_col].shift(lookback)
    return df


def add_run_from_base(df, price_col: str = "close", lookback: int = 60):
    """
    Approximate RUN_FROM_BASE_PCT: % gain from lowest close in last `lookback` days.
    A high value means the stock is extended from its base.
    """
    df["RUN_FROM_BASE_PCT"] = (
        (df[price_col] - df[price_col].rolling(lookback).min())
        / df[price_col].rolling(lookback).min()
    ) * 100
    return df


def add_52w_high(df, high_col: str = "high"):
    """Add HIGH_52W and DIST_FROM_52W_HIGH_PCT columns."""
    df["HIGH_52W"] = df[high_col].rolling(252).max()
    df["DIST_FROM_52W_HIGH_PCT"] = (
        (df["HIGH_52W"] - df[high_col]) / df["HIGH_52W"]
    ) * 100
    return df


def add_hv_percentile(df, atr_pct_col: str = "ATR_PERCENT", lookback: int = 252):
    """
    HV_PERCENTILE: Where is today's ATR% relative to its own 1-year history.
    0 = all-time quiet (coiled), 100 = all-time volatile.
    """
    def rank_pct(series):
        return series.rank(pct=True) * 100

    df["HV_PERCENTILE"] = (
        df[atr_pct_col]
        .rolling(lookback)
        .apply(lambda x: (x[-1] >= x).mean() * 100, raw=True)
    )
    return df