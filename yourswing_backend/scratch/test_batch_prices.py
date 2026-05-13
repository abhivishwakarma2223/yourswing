from app.market_api import fetch_batch_prices

symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS"]
print(f"Fetching prices for: {symbols}")
results = fetch_batch_prices(symbols)
print(f"Results: {results}")
