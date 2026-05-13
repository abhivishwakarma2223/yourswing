import yfinance as yf

symbols = ["AAPL"]
data = yf.download(symbols, period="2d", group_by='ticker')
print(f"Columns for {symbols}: {data.columns}")
print(f"Index names: {data.columns.names}")
print(f"Is MultiIndex: {isinstance(data.columns, yf.utils.pd.MultiIndex)}")
