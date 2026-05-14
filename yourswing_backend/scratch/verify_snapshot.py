import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal
from app.ranking_engine import run_full_ranking
from sqlalchemy import text

def verify_score():
    print("Verifying TATASTEEL score...")
    
    # Check what's in the candles table
    df = pd.read_sql("SELECT * FROM candles WHERE stock_id = (SELECT id FROM stocks WHERE symbol = 'TATASTEEL.NS') ORDER BY candle_time DESC LIMIT 2", engine)
    print("Latest candles in DB:")
    print(df[['candle_time', 'open', 'high', 'low', 'close', 'volume']])

    # Get the score from the database (what the UI shows)
    with SessionLocal() as db:
        db_score_row = db.execute(text("""
            SELECT final_score, trade_date 
            FROM daily_stock_candidates 
            WHERE symbol = 'TATASTEEL.NS' AND trade_date = '2026-05-14'
        """)).fetchone()
        
        if not db_score_row:
            print("No database score found for TATASTEEL on May 14.")
            return
            
        db_score = float(db_score_row[0])
        print(f"[DB SCORE] TATASTEEL score in database for May 14th: {db_score}")

    # Recalculate the score using the RankingEngine
    report = run_full_ranking(
        db_conn_factory=lambda: engine.raw_connection(),
        symbols=['TATASTEEL.NS']
    )
    
    if not report.ranked:
        print("RankingEngine returned no results.")
        return
        
    engine_score = float(report.ranked[0].score)
    print(f"[ENGINE SCORE] TATASTEEL freshly calculated score: {engine_score}")
    
    if round(db_score, 2) == round(engine_score, 2):
        print("SUCCESS: The database score EXACTLY matches the live calculation!")
    else:
        print("MISMATCH: The scores do not match!")

if __name__ == "__main__":
    verify_score()
