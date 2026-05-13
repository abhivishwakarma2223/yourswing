from app.database import SessionLocal
from app.models import Stock

def test_db():
    db = SessionLocal()
    try:
        stocks = db.query(Stock).limit(5).all()
        print(f"Success! Found {len(stocks)} stocks.")
        for s in stocks:
            print(f"- {s.symbol}")
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_db()
