from datetime import datetime, time
import pytz
import yfinance as yf

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
            "candle_time": index
        })

    return candles

def get_live_price(symbol: str) -> float:
    """
    Fetches the latest real-time price for a given symbol.
    """
    try:
        stock = yf.Ticker(symbol)
        import math
        # fast_info is typically much faster for just getting the latest price
        info = stock.fast_info
        if 'lastPrice' in info and not math.isnan(float(info['lastPrice'])):
            return float(info['lastPrice'])
            
        # Fallback to 1m interval if fast_info fails
        df = stock.history(period="1d", interval="1m")
        if not df.empty:
            close_val = float(df.iloc[-1]["Close"])
            if not math.isnan(close_val):
                return close_val
    except Exception as e:
        print(f"Error fetching live price for {symbol}: {e}")
        
    return 0.0