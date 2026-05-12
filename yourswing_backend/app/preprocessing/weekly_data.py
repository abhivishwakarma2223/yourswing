"""
weekly_data.py
==============
Weekly timeframe aggregation and indicators.
"""

from __future__ import annotations
import pandas as pd

def add_weekly_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate daily data to weekly and compute weekly indicators.
    Then map them back to the daily DataFrame.
    """
    if len(df) < 50:
        df["WEEKLY_TREND_BULLISH"] = False
        df["WEEKLY_EMA20_ABOVE_50"] = False
        return df

    # 1. Resample to weekly
    # Ensure 'time' is index for resample
    temp_df = df.copy()
    if "time" in temp_df.columns:
        temp_df["time"] = pd.to_datetime(temp_df["time"])
        temp_df.set_index("time", inplace=True)
    
    weekly = temp_df.resample('W').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    
    # 2. Weekly Indicators
    weekly["W_EMA20"] = weekly["close"].ewm(span=20, adjust=False).mean()
    weekly["W_EMA50"] = weekly["close"].ewm(span=50, adjust=False).mean()
    
    weekly["WEEKLY_TREND_BULLISH"] = (weekly["close"] > weekly["W_EMA20"]) & (weekly["W_EMA20"] > weekly["W_EMA50"])
    weekly["WEEKLY_EMA20_ABOVE_50"] = weekly["W_EMA20"] > weekly["W_EMA50"]
    
    # 3. Map back to daily (forward fill weekly values)
    # Reindex weekly to daily dates
    weekly_reindexed = weekly[["WEEKLY_TREND_BULLISH", "WEEKLY_EMA20_ABOVE_50"]].reindex(temp_df.index, method='ffill').fillna(False)
    
    df["WEEKLY_TREND_BULLISH"] = weekly_reindexed["WEEKLY_TREND_BULLISH"].values
    df["WEEKLY_EMA20_ABOVE_50"] = weekly_reindexed["WEEKLY_EMA20_ABOVE_50"].values
    
    return df
