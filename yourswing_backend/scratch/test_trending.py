from app.database import SessionLocal
from app.routes.candle_routes import get_trending_stocks

db = SessionLocal()
try:
    print("Testing get_trending_stocks...")
    stocks = get_trending_stocks(db, limit=10)
    print(f"Returned {len(stocks)} stocks.")
    for s in stocks:
        print(f"  {s['symbol']}: Score={s['score']}, Price={s['price']}")
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
finally:
    db.close()
