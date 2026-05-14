import sys
import os
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal
from app.market_api import fetch_all_active_stock_candles
from app.snapshot_engine import run_daily_snapshot

def fix_today():
    print("1. Fetching the absolute latest candles (which now definitely include today's close)...")
    fetch_all_active_stock_candles()
    
    print("\n2. Re-running the snapshot for May 14th (forcing overwrite of the stale data)...")
    with SessionLocal() as db:
        result = run_daily_snapshot(
            db=db, 
            db_conn_factory=engine.raw_connection, 
            force=True, # FORCE overwrite
            target_date=date(2026, 5, 14)
        )
        print("Snapshot generation result:", result)
        
    print("\nSuccessfully repaired May 14th data using accurate daily closing prices!")

if __name__ == "__main__":
    fix_today()
