from app.database import SessionLocal
from app.market_update import run_live_update

db = SessionLocal()
try:
    result = run_live_update(db)
    print(f"Live update result: {result}")
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
finally:
    db.close()
