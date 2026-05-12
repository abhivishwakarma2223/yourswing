"""
breakout_engine.py
==================
Institutional breakout/base analysis engine.

Calculates:
- BASE_LENGTH_DAYS
- VOL_DURING_BASE
- RANGE_COMPRESSION_PCT
- VCP_DETECTED
- POCKET_PIVOT
- BUYABLE_GAP_UP
- STRUCTURAL_STOP
- RESISTANCE_TARGET
- RR_RATIO
- PRIOR_RESISTANCE_1
"""

from __future__ import annotations
import pandas as pd
import numpy as np

def compute_breakout_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute base and breakout metrics on the indicator DataFrame.
    """
    # 1. Base Analysis
    # We define start of base as the last time price crossed below EMA50
    # Actually, a better definition is the last local peak before a consolidation.
    # For simplicity, we'll use "days since price was last below EMA50" as a proxy for the current constructive run/base.
    # But the scoring engine specifically wants BASE_LENGTH_DAYS.
    # Let's use a rolling window to find the length of the current consolidation (price within a tight range).
    
    # Simple consolidation detection: last time price was NOT in a 15% range of the current price
    # We'll iterate backwards from the latest row.
    if len(df) < 20:
        df["BASE_LENGTH_DAYS"] = 5
        df["VOL_DURING_BASE"] = 1.0
        df["RANGE_COMPRESSION_PCT"] = 15.0
        df["VCP_DETECTED"] = False
        df["POCKET_PIVOT"] = False
        df["BUYABLE_GAP_UP"] = False
        df["STRUCTURAL_STOP"] = df["close"] * 0.95
        df["RESISTANCE_TARGET"] = df["close"] * 1.10
        df["RR_RATIO"] = 2.0
        df["PRIOR_RESISTANCE_1"] = df["close"] * 1.15
        return df

    latest_close = df["close"].iloc[-1]
    
    # 2. Range Compression (20-day high-low range as % of price)
    df["RANGE_COMPRESSION_PCT"] = (
        (df["high"].rolling(20).max() - df["low"].rolling(20).min()) / df["close"]
    ) * 100

    # 3. Base Length & Vol During Base
    # We'll define base as a period where price stays within 15% of the average.
    # Let's find how many days ago the price first entered this +/- 10% band from the current price.
    upper_band = latest_close * 1.10
    lower_band = latest_close * 0.90
    
    base_len = 0
    for i in range(len(df) - 1, -1, -1):
        if lower_band <= df["close"].iloc[i] <= upper_band:
            base_len += 1
        else:
            break
    
    df["BASE_LENGTH_DAYS"] = base_len
    
    # Volume during base
    if base_len > 0:
        vol_ratio_base = df["VOLUME_RATIO"].tail(base_len).mean()
    else:
        vol_ratio_base = 1.0
    df["VOL_DURING_BASE"] = vol_ratio_base

    # 4. VCP Detection (successive range contractions)
    # Check if 20-day range is shrinking over the last 60 days
    r20 = df["RANGE_COMPRESSION_PCT"]
    vcp = (r20.iloc[-1] < r20.iloc[-10]) and (r20.iloc[-10] < r20.iloc[-20])
    df["VCP_DETECTED"] = vcp

    # 5. Pocket Pivot
    # Up-day on above-avg vol without necessarily breaking out.
    # "volume exceeds any down-day volume in last 10 days"
    last_10 = df.tail(10)
    down_days_vol = last_10[last_10["close"] < last_10["open"]]["volume"]
    max_down_vol = down_days_vol.max() if not down_days_vol.empty else 0
    is_up_day = df["close"].iloc[-1] > df["open"].iloc[-1]
    df["POCKET_PIVOT"] = is_up_day and (df["volume"].iloc[-1] > max_down_vol)

    # 6. Buyable Gap Up
    # Gap up > 1% from previous close with volume > 2x average
    prev_close = df["close"].shift(1).iloc[-1]
    curr_open = df["open"].iloc[-1]
    gap_pct = (curr_open - prev_close) / prev_close * 100
    df["BUYABLE_GAP_UP"] = (gap_pct > 1.0) and (df["VOLUME_RATIO"].iloc[-1] > 2.0)

    # 7. Structural Stop & Resistance Target
    # Stop: lowest of last 20 days (recent swing low)
    df["STRUCTURAL_STOP"] = df["low"].rolling(20).min()
    
    # Target: highest of last 120 days (prior resistance)
    df["RESISTANCE_TARGET"] = df["high"].rolling(120).max()
    df["PRIOR_RESISTANCE_1"] = df["high"].rolling(250).max()
    
    # RR Ratio
    risk = df["close"] - df["STRUCTURAL_STOP"]
    reward = df["RESISTANCE_TARGET"] - df["close"]
    df["RR_RATIO"] = (reward / risk).replace([np.inf, -np.inf], 0).fillna(0).clip(0, 10)

    return df
