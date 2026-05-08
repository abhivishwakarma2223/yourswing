import os
import sys

# Add the root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.market_api import fetch_all_active_stock_candles

if __name__ == "__main__":
    print("Starting initial candle sync for all active stocks...")
    print("This may take a few minutes for 200 stocks. Please wait...")
    
    try:
        results = fetch_all_active_stock_candles()
        print(f"\nSuccess! Fetched data for {len(results)} stocks.")
        print("Your dashboard should now show live data.")
    except Exception as e:
        print(f"Error during candle sync: {e}")
