"""
pipeline.py
===========
Centralized preprocessing orchestrator.
"""

from __future__ import annotations
import pandas as pd
import logging
from .rs_ranking import compute_rs_rankings
from .sector_intelligence import compute_sector_data
from .breakout_engine import compute_breakout_metrics
from .weekly_data import add_weekly_indicators
from app.scoring_engine import (
    add_volume_trend, 
    add_roc_columns, 
    add_rsi_prev, 
    add_run_from_base, 
    add_52w_high, 
    add_hv_percentile
)

logger = logging.getLogger(__name__)

def run_preprocessing_pipeline(
    symbol: str,
    df: pd.DataFrame,
    rs_rankings: dict = None,
    sector_data: dict = None,
) -> pd.DataFrame:
    """
    Run all preprocessing stages and return enriched DataFrame.
    """
    try:
        # 1. Base v2 helpers (from scoring_engine)
        df = add_volume_trend(df)
        df = add_roc_columns(df)
        df = add_rsi_prev(df)
        df = add_run_from_base(df)
        df = add_52w_high(df)
        df = add_hv_percentile(df)
        
        # 2. Weekly Data
        df = add_weekly_indicators(df)
        
        # 3. Breakout Engine
        df = compute_breakout_metrics(df)
        
        # 4. Inject RS rankings
        if rs_rankings and symbol in rs_rankings:
            for k, v in rs_rankings[symbol].items():
                df[k] = v
        else:
            # Fallbacks
            df["RS_PERCENTILE_RANK"] = 50.0
            df["RS_TREND_SLOPE"] = 0.0
            df["RS_NEW_HIGH"] = False
            df["RS_VS_NIFTY"] = 1.0
            
        # 5. Inject Sector Intelligence
        if sector_data and symbol in sector_data:
            for k, v in sector_data[symbol].items():
                df[k] = v
        else:
            # Fallbacks
            df["SECTOR_RANK"] = 7
            df["TOTAL_SECTORS"] = 13
            df["SECTOR_RS_SLOPE"] = 0.0
            df["SECTOR_BREADTH_PCT"] = 50.0
            df["STOCK_RS_WITHIN_SECTOR"] = 50.0
            df["sector_name"] = "Unknown"

        # 6. Additional Flags for master scorer
        # HIGHER_HIGH, HIGHER_LOW (calculated over last 10 days)
        if len(df) >= 10:
            df["HIGHER_HIGH"] = df["high"].iloc[-1] > df["high"].iloc[-10]
            df["HIGHER_LOW"] = df["low"].iloc[-1] > df["low"].iloc[-10]
        else:
            df["HIGHER_HIGH"] = False
            df["HIGHER_LOW"] = False
        
        # SWING_RANGE_PCT (average high-low range)
        df["SWING_RANGE_PCT"] = ((df["high"] - df["low"]) / df["close"] * 100).rolling(20).mean()
        
        # CANDLE_BODY_PERCENT (body / range)
        body = (df["close"] - df["open"]).abs()
        rng = (df["high"] - df["low"]).clip(lower=0.01)
        df["CANDLE_BODY_PERCENT"] = body / rng
        
        # CLOSE_NEAR_HIGH (normalized: 0 = at high, 1 = at low)
        # Note: Master scorer says 0 = at high (best), 1 = at low (worst)
        dist_from_high = df["high"] - df["close"]
        full_range = (df["high"] - df["low"]).clip(lower=0.01)
        df["CLOSE_NEAR_HIGH"] = dist_from_high / full_range

        return df
        
    except Exception as e:
        logger.error(f"Error in preprocessing pipeline for {symbol}: {e}")
        return df
