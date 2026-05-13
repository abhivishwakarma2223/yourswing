import yfinance as yf
from datetime import datetime

symbol = "RELIANCE.NS"
print(f"Checking yfinance data for {symbol}")

# Fetch data for the last month
ticker = yf.Ticker(symbol)
hist = ticker.history(period="1mo")

print("\nLast 10 rows of history data:")
print(hist.tail(10))

print(f"\nCurrent Date: {datetime.now()}")
