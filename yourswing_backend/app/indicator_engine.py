import talib
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def calculate_indicators(df):
    logger.info(f"Calculating indicators for {len(df)} candles")

    if df.empty:
        return df

    # Extract series for TA-Lib
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    volume = df["volume"] # keep as series for rolling functions

    df["RSI"] = talib.RSI(close, timeperiod=14)
    df["EMA20"] = talib.EMA(close, timeperiod=20)
    df["EMA50"] = talib.EMA(close, timeperiod=50)

    # MACD
    macd, macd_signal, macd_hist = talib.MACD(
        close, fastperiod=12, slowperiod=26, signalperiod=9
    )
    df["MACD"] = macd
    df["MACD_SIGNAL"] = macd_signal
    df["MACD_HIST"] = macd_hist

    # ATR
    df["ATR"] = talib.ATR(high, low, close, timeperiod=14)

    # Volume Ratio
    df["AVG_VOLUME_20"] = volume.rolling(20).mean()
    df["VOLUME_RATIO"] = volume / df["AVG_VOLUME_20"]

    # Relative Strength
    df["RELATIVE_STRENGTH"] = df["close"] / df["EMA50"]

    # Breakout Detection
    df["HIGHEST_20"] = df["high"].rolling(20).max()
    df["BREAKOUT"] = df["close"] > df["HIGHEST_20"].shift(1)

    return df