from app.market_api import fetch_batch_prices

# BIOCON.NS should be in cache (top 50)
# RELIANCE.NS might be in cache or not (depending on if it was in top 50)
# APPLE (US stock) should NOT be in cache and should fall back to yfinance
symbols = ["BIOCON.NS", "AAPL"]
print(f"Fetching prices for: {symbols}")
results = fetch_batch_prices(symbols)
print(f"Results: {results}")
