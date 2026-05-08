import pandas as pd
import pandas_ta as ta
import logging
import yfinance as yf
import time
import numpy as np

logger = logging.getLogger(__name__)

NIFTY_CACHE = None
LAST_FETCH_TIME = None


def get_nifty_data():
    global NIFTY_CACHE, LAST_FETCH_TIME

    if (
        NIFTY_CACHE is not None
        and LAST_FETCH_TIME
        and (time.time() - LAST_FETCH_TIME < 3600)
    ):
        return NIFTY_CACHE

    try:
        nifty_raw = yf.download("^NSEI", period="2y", progress=False)
        if nifty_raw.empty:
            return None

        close_series = nifty_raw['Close'].squeeze()
        nifty_df = pd.DataFrame(index=close_series.index)
        nifty_df["close"] = close_series.values

        # Normalize index timezone
        if hasattr(nifty_df.index, 'tz') and nifty_df.index.tz is not None:
            nifty_df.index = nifty_df.index.tz_localize(None)
        
        # Ensure the index is purely dates for easier mapping
        nifty_df.index = nifty_df.index.date

        # Use pandas_ta instead of talib
        nifty_df["EMA20"] = ta.ema(nifty_df["close"], length=20)
        nifty_df["EMA50"] = ta.ema(nifty_df["close"], length=50)

        nifty_df["MARKET_BULLISH"] = (
            (nifty_df["close"] > nifty_df["EMA20"]) &
            (nifty_df["EMA20"] > nifty_df["EMA50"])
        )

        NIFTY_CACHE = nifty_df
        LAST_FETCH_TIME = time.time()
        return nifty_df

    except Exception as e:
        logger.error(f"Failed to fetch Nifty data: {e}")
        return None


def calculate_indicators(df):
    logger.info(f"Calculating indicators for {len(df)} candles")

    if df.empty:
        return df

    # Ensure column names are what pandas_ta expects or map them
    # pandas_ta works best with columns named 'open', 'high', 'low', 'close', 'volume'
    
    # ── Core Indicators (using pandas_ta) ────────────────────────
    df["RSI"]    = ta.rsi(df["close"], length=14)
    df["EMA20"]  = ta.ema(df["close"], length=20)
    df["EMA50"]  = ta.ema(df["close"], length=50)
    df["EMA200"] = ta.ema(df["close"], length=200)

    # MACD
    macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
    if macd_df is not None:
        df["MACD"]        = macd_df["MACD_12_26_9"]
        df["MACD_SIGNAL"] = macd_df["MACDs_12_26_9"]
        df["MACD_HIST"]   = macd_df["MACDh_12_26_9"]

    # ATR
    df["ATR"]         = ta.atr(df["high"], df["low"], df["close"], length=14)
    df["ATR_PERCENT"] = (df["ATR"] / df["close"].replace(0, np.nan)) * 100

    # ── Volume ───────────────────────────────────────────────────
    df["AVG_VOLUME_20"] = df["volume"].rolling(20).mean()
    df["VOLUME_RATIO"]  = df["volume"] / df["AVG_VOLUME_20"].replace(0, np.nan)

    # ── Swing Structure ──────────────────────────────────────────
    df["PREV_SWING_HIGH"] = df["high"].shift(1).rolling(5).max()
    df["PREV_SWING_LOW"]  = df["low"].shift(1).rolling(5).min()
    df["HIGHER_HIGH"]     = df["high"] > df["PREV_SWING_HIGH"]
    df["HIGHER_LOW"]      = df["low"]  > df["PREV_SWING_LOW"]

    # ── Candle Metrics ───────────────────────────────────────────
    df["CANDLE_BODY"]         = abs(df["close"] - df["open"])
    df["CANDLE_RANGE"]        = df["high"] - df["low"]
    df["CANDLE_BODY_PERCENT"] = (
        df["CANDLE_BODY"] / df["CANDLE_RANGE"].replace(0, np.nan)
    )
    df["CLOSE_NEAR_HIGH"] = (
        (df["high"] - df["close"]) / df["CANDLE_RANGE"].replace(0, np.nan)
    )

    # ── Distance & Trend ─────────────────────────────────────────
    df["DISTANCE_FROM_EMA20"] = ((df["close"] - df["EMA20"]) / df["EMA20"]) * 100
    df["TREND_STRENGTH"]      = ((df["EMA20"] - df["EMA50"]) / df["EMA50"]) * 100

    # ── 20-Day Range ─────────────────────────────────────────────
    df["RANGE_HIGH_20"] = df["high"].rolling(20).max()
    df["RANGE_LOW_20"]  = df["low"].rolling(20).min()
    df["RANGE_PERCENT"] = (
        (df["RANGE_HIGH_20"] - df["RANGE_LOW_20"])
        / df["RANGE_LOW_20"].replace(0, np.nan)
    ) * 100

    # ── Relative Strength vs Nifty ──
    nifty_df = get_nifty_data()
    if nifty_df is not None and not nifty_df.empty:
        stock_return = df["close"] / df["close"].shift(20)
        df_dates = df["time"].apply(lambda d: d.date() if hasattr(d, 'date') else d)
        
        nifty_aligned = df_dates.map(nifty_df["close"])
        nifty_aligned = nifty_aligned.ffill()
        
        nifty_return = nifty_aligned / nifty_aligned.shift(20)
        df["RELATIVE_STRENGTH"] = stock_return / nifty_return.replace(0, np.nan)
        df["MARKET_BULLISH"] = df_dates.map(nifty_df["MARKET_BULLISH"]).ffill().fillna(False)
    else:
        df["RELATIVE_STRENGTH"] = 1.0
        df["MARKET_BULLISH"]    = False

    # ── Breakout ─────────────────────────────────────────────────
    df["HIGHEST_20"] = df["high"].shift(1).rolling(20).max()
    df["BREAKOUT"]   = (
        (df["close"] > df["HIGHEST_20"]) &
        (df["VOLUME_RATIO"] > 1.5) &
        (df["CANDLE_BODY_PERCENT"] > 0.6)
    )

    # ── Structure & Alignment ────────────────────────────────────
    df["BULLISH_STRUCTURE"] = df["HIGHER_HIGH"] & df["HIGHER_LOW"]
    df["TREND_ALIGNMENT"]   = (
        (df["EMA20"] > df["EMA50"]) &
        (df["EMA50"] > df["EMA200"])
    )

    return df
