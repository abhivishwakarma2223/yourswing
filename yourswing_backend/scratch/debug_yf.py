import yfinance as yf

symbols = ["AAPL"]
data = yf.download(symbols, period="2d", group_by='ticker')
print(f"Columns for {symbols}: {data.columns}")
print(f"Data head:\n{data.head()}")

symbols2 = ["AAPL", "MSFT"]
data2 = yf.download(symbols2, period="2d", group_by='ticker')
print(f"\nColumns for {symbols2}: {data2.columns}")
print(f"Data head:\n{data2.head()}")
