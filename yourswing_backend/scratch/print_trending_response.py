import json
from app.database import get_db_connection
from app.ranking_engine import get_top_ranked_stocks

def print_trending():
    # get_top_ranked_stocks expects a db_conn_factory
    top_stocks = get_top_ranked_stocks(get_db_connection, limit=3)
    
    # Simulate what the route does:
    trending = []
    for stock_data in top_stocks:
        symbol = stock_data["symbol"]
        score = stock_data["score"]
        signal = stock_data["signal"]
        trending.append({
            "symbol": symbol.upper(),
            "score": score,
            "signal": signal,
            "price": stock_data.get("latest_price", 0.0),
            "change": 0.0,
            "changePercent": 0.0
        })
        
    print("--- Trending API Response (Simulated) ---")
    print(json.dumps(trending, indent=2))

if __name__ == "__main__":
    print_trending()
