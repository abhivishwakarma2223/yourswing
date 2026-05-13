import os
import sys
from datetime import date, timedelta

# Add the root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.snapshot_engine import run_daily_snapshot
from app.market_api import fetch_all_active_stock_candles

def backfill():
    print("Starting backfill process...")
    
    # 1. Sync candles first (to ensure historical data is in DB)
    print("Syncing candles for all active stocks...")
    fetch_all_active_stock_candles()
    
    # 2. Backfill missing snapshots
    dates_to_fill = [
        date(2026, 5, 11),
        date(2026, 5, 12),
        date(2026, 5, 13) # Re-run for today just in case
    ]
    
    db = SessionLocal()
    try:
        for target_date in dates_to_fill:
            print(f"\nProcessing snapshot for {target_date}...")
            result = run_daily_snapshot(db, engine.raw_connection, force=True, target_date=target_date)
            print(f"Result for {target_date}: {result}")
    finally:
        db.close()

if __name__ == "__main__":
    backfill()
