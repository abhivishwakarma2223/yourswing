import yfinance as yf
import pandas as pd
import pandas_ta as ta

nifty_raw = yf.download("^NSEI", period="2y", progress=False)
print("Columns:", nifty_raw.columns)
close_series = nifty_raw['Close'].squeeze()
print("Squeeze type:", type(close_series))

nifty_df = pd.DataFrame(index=close_series.index)
nifty_df["close"] = close_series.values
nifty_df["EMA20"] = ta.ema(nifty_df["close"], length=20)
print("Latest EMA20:", nifty_df["EMA20"].iloc[-1])
print("Is None check:", nifty_df["EMA20"].iloc[-1] is None)
