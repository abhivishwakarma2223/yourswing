from sqlalchemy.orm import Session
from typing import List, Optional
from app.models import Candle
from app.schemas import CandleCreate
from .models import Candle
import pandas as pd
from .models import Candle, Indicator
from sqlalchemy import desc
from .models import Stock



def save_candles(db, stock_id, candles):
    # Fetch all existing dates for this stock in ONE query and convert to pure dates
    existing_dates = set(
        c[0].date() for c in db.query(Candle.candle_time).filter(Candle.stock_id == stock_id).all() if c[0]
    )

    new_candles = []
    for candle in candles:
        # Convert Pandas Timestamp to standard date to avoid timezone/type mismatch
        candle_date = candle["candle_time"].date()
        
        if candle_date in existing_dates:
            continue

        new_candles.append(
            Candle(
                stock_id=stock_id,
                timeframe="1d",
                open=candle["open"],
                high=candle["high"],
                low=candle["low"],
                close=candle["close"],
                volume=candle["volume"],
                candle_time=candle["candle_time"]
            )
        )

    if new_candles:
        db.add_all(new_candles)
        db.commit()

    return len(new_candles)



def get_candles_dataframe(db, stock_id):

    candles = db.query(Candle).filter(
        Candle.stock_id == stock_id
    ).order_by(Candle.candle_time).all()

    data = []

    for c in candles:

        data.append({
            "time": c.candle_time,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume
        })

    return pd.DataFrame(data)




import math

def get_latest_analysis(db, stock_id):
    from app.indicator_engine import calculate_indicators
    from app.strategy_engine import generate_signal

    df = get_candles_dataframe(db, stock_id)
    if df.empty:
        return None

    df = calculate_indicators(df)
    latest_row = df.iloc[-1]

    def clean_val(v):
        if pd.isna(v) or math.isnan(v):
            return 0.0
        return float(v)

    indicators_dict = {
        "RSI": clean_val(latest_row.get("RSI", 0)),
        "EMA20": clean_val(latest_row.get("EMA20", 0)),
        "EMA50": clean_val(latest_row.get("EMA50", 0)),
        "MACD": clean_val(latest_row.get("MACD", 0)),
        "MACD_SIGNAL": clean_val(latest_row.get("MACD_SIGNAL", 0)),
        "ATR": clean_val(latest_row.get("ATR", 0)),
        "VOLUME_RATIO": clean_val(latest_row.get("VOLUME_RATIO", 0)),
        "RELATIVE_STRENGTH": clean_val(latest_row.get("RELATIVE_STRENGTH", 0)),
        "BREAKOUT": bool(latest_row.get("BREAKOUT", False))
    }

    signal = generate_signal(indicators_dict)

    return {
        "rsi": round(indicators_dict["RSI"], 2),
        "ema20": round(indicators_dict["EMA20"], 2),
        "ema50": round(indicators_dict["EMA50"], 2),
        "macd": round(indicators_dict["MACD"], 2),
        "atr": round(indicators_dict["ATR"], 2),
        "volume_ratio": round(indicators_dict["VOLUME_RATIO"], 2),
        "relative_strength": round(indicators_dict["RELATIVE_STRENGTH"], 2),
        "breakout": indicators_dict["BREAKOUT"],
        "signal": signal
    }

def analyze_stock_with_live_price(db: Session, stock_id: int):
    from app.market_api import get_live_price
    
    analysis = get_latest_analysis(db, stock_id)
    if not analysis:
        return None
        
    stock = db.query(Stock).filter(Stock.id == stock_id).first()
    if not stock:
        return None
        
    import math
    live_price = get_live_price(stock.symbol)
    if math.isnan(live_price):
        live_price = 0.0
    
    # Get the latest historical candle (which is yesterday's if market is open)
    candles = get_latest_candles(db, stock_id, limit=1)
    previous_close = candles[0].close if candles else live_price
    if math.isnan(previous_close):
        previous_close = 0.0
    
    # If live_price couldn't be fetched, fallback to previous_close
    if live_price == 0.0 and previous_close > 0:
        live_price = previous_close
    
    change = 0.0
    change_percent = 0.0
    if previous_close > 0:
        change = round(live_price - previous_close, 2)
        change_percent = round((change / previous_close) * 100, 2)
        
    return {
        "symbol": stock.symbol.upper(),
        "live_price": round(live_price, 2),
        "previous_close": round(previous_close, 2),
        "change": change,
        "changePercent": change_percent,
        **analysis
    }





def get_candle(db: Session, candle_id: int) -> Optional[Candle]:
    pass

def get_candles(db: Session, symbol: str, skip: int = 0, limit: int = 100) -> List[Candle]:
    pass

def create_candle(db: Session, candle: CandleCreate) -> Candle:
    pass

def delete_candle(db: Session, candle_id: int) -> bool:
    pass

def get_stock_by_symbol(db: Session, symbol: str) -> Optional[Stock]:
    return db.query(Stock).filter(Stock.symbol == symbol).first()

def get_all_stocks(db: Session) -> List[Stock]:
    return db.query(Stock).all()

def get_latest_candles(db: Session, stock_id: int, limit: int = 2) -> List[Candle]:
    return db.query(Candle).filter(
        Candle.stock_id == stock_id
    ).order_by(desc(Candle.candle_time)).limit(limit).all()
