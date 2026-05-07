from datetime import datetime, time
import pytz
import yfinance as yf
from sqlalchemy import text
from app.database import engine

def is_market_closed() -> bool:
    """
    Returns True if the Indian market (IST) is currently closed.
    Market hours are considered closed after 15:30 IST.
    """
    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist)
    
    # Check if it's weekend
    if now_ist.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return True
        
    market_open = time(9, 15)
    market_close = time(15, 30)
    current_time = now_ist.time()
    
    # Market is closed if time is before 9:15 AM or after 3:30 PM
    return not (market_open <= current_time <= market_close)

def fetch_daily_candles(symbol: str):
    """
    Fetches historical daily candles.
    Strictly filters out today's candle if the market has not closed yet.
    """
    stock = yf.Ticker(symbol)
    df = stock.history(period="1y", interval="1d")
    
    if df.empty:
        return []
        
    # Drop any rows where yfinance returns NaN for critical fields (e.g., market holidays)
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])

    candles = []
    ist = pytz.timezone("Asia/Kolkata")
    today = datetime.now(ist).date()
    market_closed = is_market_closed()

    for index, row in df.iterrows():
        # Ensure the index (candle time) is properly converted to a date
        candle_date = index.tz_convert(ist).date() if index.tzinfo else index.date()
        
        # If the candle is for today and the market is still open, ignore it (it's incomplete)
        if candle_date == today and not market_closed:
            continue

        candles.append({
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"]),
            "candle_time": candle_date
        })

    return candles

def get_live_price(symbol: str) -> dict:
    """
    Fetches the latest real-time price and previous close for a given symbol.
    """
    try:
        stock = yf.Ticker(symbol)
        import math
        # fast_info is typically much faster for just getting the latest price
        info = stock.fast_info
        
        last_price = 0.0
        if 'lastPrice' in info and not math.isnan(float(info['lastPrice'])):
            last_price = float(info['lastPrice'])
            
        previous_close = 0.0
        if 'regularMarketPreviousClose' in info and not math.isnan(float(info['regularMarketPreviousClose'])):
            previous_close = float(info['regularMarketPreviousClose'])
        elif 'previousClose' in info and not math.isnan(float(info['previousClose'])):
            previous_close = float(info['previousClose'])
            
        if last_price > 0.0 and previous_close > 0.0:
            # Circuit Breaker Check: Indian stocks have max 20% limit. If Yahoo fast_info shows >20% change, it's garbage data.
            percent_change = abs((last_price - previous_close) / previous_close) * 100
            if percent_change > 20.0:
                print(f"Suspicious fast_info data for {symbol}: {last_price} vs {previous_close}. Falling back to history.")
                last_price = 0.0 # Force fallback
            else:
                return {"live_price": last_price, "previous_close": previous_close}
        elif last_price > 0.0:
            return {"live_price": last_price, "previous_close": previous_close}
            
        # Fallback to history if fast_info fails or returns garbage
        df = stock.history(period="5d", interval="1d")
        if not df.empty:
            close_val = float(df.iloc[-1]["Close"])
            if not math.isnan(close_val):
                return {"live_price": close_val, "previous_close": previous_close}
    except Exception as e:
        print(f"Error fetching live price for {symbol}: {e}")
        
    return {"live_price": 0.0, "previous_close": 0.0}


def get_active_stock_symbols():

    with engine.connect() as conn:

        result = conn.execute(text("""
            SELECT symbol
            FROM stocks
            WHERE is_active = TRUE
        """))

        symbols = [row[0] for row in result.fetchall()]

    return symbols

def fetch_all_active_stock_candles():
    from app.database import SessionLocal
    from app.crud import get_stock_by_symbol, save_candles

    symbols = get_active_stock_symbols()

    all_candles = {}
    
    with SessionLocal() as db:
        for symbol in symbols:
            try:
                candles = fetch_daily_candles(symbol)
                
                stock = get_stock_by_symbol(db, symbol)
                if stock and candles:
                    save_candles(db, stock.id, candles)
                    all_candles[symbol] = candles
                    print(f"Fetched and saved candles for {symbol}")
                elif not stock:
                    print(f"Skipping {symbol}: Not found in DB")
                else:
                    print(f"Skipping {symbol}: No candles returned")

            except Exception as e:
                print(f"Error fetching {symbol}: {e}")

    return all_candles