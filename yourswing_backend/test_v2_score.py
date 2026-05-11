"""
Standalone v2 scoring engine test.
Fetches RELIANCE.NS via yfinance (no DB needed) and runs the full pipeline.
"""
import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd

# ── 1. Fetch OHLCV ────────────────────────────────────────────────────────────
print("--- Fetching RELIANCE.NS from yfinance ---")
raw = yf.download("RELIANCE.NS", period="2y", interval="1d", progress=False)

# Flatten MultiIndex columns if present
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = [c[0].lower() for c in raw.columns]
else:
    raw.columns = [c.lower() for c in raw.columns]

raw = raw[["open", "high", "low", "close", "volume"]].dropna().reset_index()

# Normalize the date column name
raw.rename(columns={"date": "time", "Date": "time", "index": "time"}, inplace=True)
print(f"Rows fetched: {len(raw)}")

# ── 2. Calculate Indicators (includes v2 helpers) ─────────────────────────────
from app.indicator_engine import calculate_indicators
df = calculate_indicators(raw)
print(f"Rows after calculate_indicators: {len(df)}")

# ── 3. Market Regime Dict ─────────────────────────────────────────────────────
from app.market_api import get_market_regime_dict
print("\nFetching market regime (Nifty + VIX)...")
market = get_market_regime_dict()
print(f"  Nifty close  : {market['NIFTY_CLOSE']}")
print(f"  Nifty EMA20  : {market['NIFTY_EMA20']}")
print(f"  Nifty EMA50  : {market['NIFTY_EMA50']}")
print(f"  Nifty EMA200 : {market['NIFTY_EMA200']}")
print(f"  VIX          : {market['INDIAVIX']}")
print(f"  VIX EMA10    : {market['INDIAVIX_EMA10']}")

# ── 4. Score the latest row ───────────────────────────────────────────────────
from app.scoring_engine import score_stock
latest = df.iloc[-1].to_dict()
result = score_stock(latest, market)

print()
print("=" * 50)
print("  v2 SCORE RESULT — RELIANCE.NS")
print("=" * 50)
print(f"  Regime       : {result['regime']}  (x{result['regime_multiplier']})")
print(f"  Raw score    : {result['raw_score']} / 93")
print(f"  Normalized   : {result['normalized_score']}")
print(f"  FINAL SCORE  : {result['final_score']}")
print(f"  SIGNAL       : {result['signal']}")
print()

print("  Component breakdown:")
print(f"  {'Component':<28} {'Score':>6}  {'% of max':>9}")
print("  " + "-" * 48)
for name, comp in result["components"].items():
    pct = result["component_pct"][name]
    print(f"  {name:<28} {comp['score']:>5.1f}/{comp['max']}  ({pct}%)")

print()
print("  Flags:")
for f in result["flags"]:
    print(f"  [{f['severity']}] {f['flag']}: {f['detail']}")
if not result["flags"]:
    print("  None")

print()
print("  Regime detail:")
for k, v in result["regime_detail"]["detail"].items():
    print(f"  {k}: {v}")
