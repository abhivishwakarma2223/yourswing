from datetime import datetime, time
import pytz
import yfinance as yf
from sqlalchemy import text
from app.database import engine
from typing import List, Dict

def is_market_closed() -> bool:
    """
    Returns True if the Indian market (IST) is currently closed.
    """
    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist)
    if now_ist.weekday() >= 5: return True
    market_open = time(9, 15)
    market_close = time(15, 30)
    current_time = now_ist.time()
    return not (market_open <= current_time <= market_close)

def fetch_daily_candles(symbol: str):
    stock = yf.Ticker(symbol)
    df = stock.history(period="1y", interval="1d")
    if df.empty: return []
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    candles = []
    ist = pytz.timezone("Asia/Kolkata")
    today = datetime.now(ist).date()
    market_closed = is_market_closed()

    for index, row in df.iterrows():
        candle_date = index.tz_convert(ist).date() if index.tzinfo else index.date()
        if candle_date == today and not market_closed: continue
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
    try:
        stock = yf.Ticker(symbol)
        info = stock.fast_info
        last_price = info.get('lastPrice', 0.0)
        previous_close = info.get('regularMarketPreviousClose', 0.0)
        return {"live_price": float(last_price), "previous_close": float(previous_close)}
    except:
        return {"live_price": 0.0, "previous_close": 0.0}

def get_active_stock_symbols() -> List[str]:
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
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
    return all_candles

def fetch_batch_prices(symbols: List[str]) -> Dict:
    """
    ULTRA-FAST BATCH FETCH: Uses one single network request for all symbols.
    Handles MultiIndex format for both single and multiple tickers.
    """
    if not symbols: return {}
    original_symbols = symbols
    normalized_symbols = [s.upper() for s in original_symbols]
    
    try:
        # group_by='ticker' ALWAYS returns MultiIndex, even for 1 symbol
        data = yf.download(normalized_symbols, period="7d", interval="1d", progress=False, group_by='ticker')
        results = {}
        
        for i, s in enumerate(normalized_symbols):
            orig = original_symbols[i]
            try:
                # IMPORTANT: In group_by='ticker' mode, ticker is always the top level key
                stock_data = data[s]
                
                if stock_data is None or stock_data.empty:
                    results[orig] = {"price": 0.0, "changePercent": 0.0}
                    continue
                    
                close_series = stock_data['Close'].dropna()
                if close_series.empty:
                    results[orig] = {"price": 0.0, "changePercent": 0.0}
                    continue
                
                price = float(close_series.iloc[-1])
                prev_close = float(close_series.iloc[-2]) if len(close_series) > 1 else price
                
                results[orig] = {
                    "price": round(price, 2),
                    "changePercent": round(((price - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0
                }
            except Exception as e:
                print(f"Error processing {orig}: {e}")
                results[orig] = {"price": 0.0, "changePercent": 0.0}
        return results
    except Exception as e:
        print(f"Bulk Fetch Error: {e}")
        return {s: {"price": 0.0, "changePercent": 0.0} for s in original_symbols}
