import json
from app.database import get_db_connection
from app.crud import analyze_stock_with_live_price
from sqlalchemy.orm import Session
from app.database import SessionLocal

def print_analysis(symbol):
    with SessionLocal() as db:
        # Get stock id
        from app.models import Stock
        stock = db.query(Stock).filter(Stock.symbol == symbol).first()
        if not stock:
            print(f"Stock {symbol} not found")
            return
        
        analysis = analyze_stock_with_live_price(db, stock.id)
        print("--- API Response Dictionary ---")
        print(json.dumps(analysis, indent=2))

if __name__ == "__main__":
    import sys
    symbol = "RELIANCE.NS"
    print_analysis(symbol)
