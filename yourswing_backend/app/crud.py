from sqlalchemy.orm import Session
from typing import List, Optional
from app.schemas import CandleCreate
import pandas as pd
from sqlalchemy import desc
from .models import *



def save_candles(db, stock_id, candles):
    # Fetch all existing dates for this stock in ONE query and convert to pure dates
    existing_dates = set(
        c[0].date() for c in db.query(Candle.candle_time).filter(Candle.stock_id == stock_id).all() if c[0]
    )

    new_candles = []
    for candle in candles:
        # Convert Pandas Timestamp to standard date to avoid timezone/type mismatch
        ct = candle["candle_time"]
        candle_date = ct.date() if hasattr(ct, "date") else ct
        
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

def get_latest_analysis(db, stock_id, live_price=None):
    from app.indicator_engine import calculate_indicators
    from app.scoring_engine import score_stock
    from app.preprocessing.pipeline import run_preprocessing_pipeline
    from app.market_api import get_market_regime_dict
    from app.preprocessing.rs_ranking import compute_rs_rankings
    from app.preprocessing.sector_intelligence import compute_sector_data

    df = get_candles_dataframe(db, stock_id)
    if df.empty:
        return None

    # Core indicators
    df = calculate_indicators(df)
    symbol = db.query(Stock.symbol).filter(Stock.id == stock_id).scalar()
    
    # For single-stock analysis, we might not have batch RS/Sector data pre-computed.
    # We'll compute it on the fly for just this symbol if needed, though RS ranking usually needs the whole universe.
    # For simplicity, we'll pass None and the pipeline will use defaults/cached data if available.
    market = get_market_regime_dict()
    
    # Run full institutional pipeline
    df = run_preprocessing_pipeline(symbol, df)
    
    latest_row = df.iloc[-1].to_dict()
    
    # NEW: If live price is provided, update the latest row before scoring
    if live_price is not None and live_price > 0:
        latest_row['close'] = live_price
        # Optional: update other price-dependent indicators if necessary, 
        # but most scoring logic uses 'close' or 'price'
        latest_row['price'] = live_price

    def clean_val(v):
        try:
            f = float(v)
            if pd.isna(f) or math.isnan(f):
                return 0.0
            return f
        except (TypeError, ValueError):
            return 0.0

    score_result = score_stock(latest_row, market=market)
    score = score_result["final_score"]
    signal = score_result["signal"]

    indicators_dict = {
        "RSI": clean_val(latest_row.get("RSI", 0)),
        "EMA20": clean_val(latest_row.get("EMA20", 0)),
        "EMA50": clean_val(latest_row.get("EMA50", 0)),
        "MACD": clean_val(latest_row.get("MACD", 0)),
        "ATR": clean_val(latest_row.get("ATR", 0)),
        "VOLUME_RATIO": clean_val(latest_row.get("VOLUME_RATIO", 0)),
        "RELATIVE_STRENGTH": clean_val(latest_row.get("RS_PERCENTILE_RANK", 0)), # Using the new RS rank
        "BREAKOUT": bool(latest_row.get("BREAKOUT", False))
    }

    return {
        "rsi": round(indicators_dict["RSI"], 2),
        "ema20": round(indicators_dict["EMA20"], 2),
        "ema50": round(indicators_dict["EMA50"], 2),
        "macd": round(indicators_dict["MACD"], 2),
        "atr": round(indicators_dict["ATR"], 2),
        "volume_ratio": round(indicators_dict["VOLUME_RATIO"], 2),
        "relative_strength": round(indicators_dict["RELATIVE_STRENGTH"], 2),
        "breakout": indicators_dict["BREAKOUT"],
        "signal": signal,
        "score": score,
        "components": score_result.get("components", {}),
        "regime": score_result.get("regime", "UNKNOWN"),
        "regime_multiplier": score_result.get("regime_multiplier", 1.0)
    }

def analyze_stock_with_live_price(db: Session, stock_id: int):
    from app.market_api import get_live_price
    
    stock = db.query(Stock).filter(Stock.id == stock_id).first()
    if not stock:
        return None
        
    price_info = get_live_price(stock.symbol)
    live_price = price_info["live_price"]
    previous_close = price_info["previous_close"]

    # Re-calculate analysis with the LIVE price
    analysis = get_latest_analysis(db, stock_id, live_price=live_price)
    if not analysis:
        return None
    
    if math.isnan(live_price):
        live_price = 0.0
    if math.isnan(previous_close):
        previous_close = 0.0
        
    # If previous_close is 0 from fast_info, fallback to the latest historical candle
    if previous_close == 0.0:
        candles = get_latest_candles(db, stock_id, limit=1)
        if candles:
            previous_close = candles[0].close
        
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
    return db.query(Candle).filter(Candle.id == candle_id).first()

def get_candles(db: Session, symbol: str, skip: int = 0, limit: int = 100) -> List[Candle]:
    stock = get_stock_by_symbol(db, symbol)
    if not stock:
        return []
    return db.query(Candle).filter(
        Candle.stock_id == stock.id
    ).order_by(desc(Candle.candle_time)).offset(skip).limit(limit).all()

def create_candle(db: Session, candle: CandleCreate) -> Candle:
    db_candle = Candle(**candle.model_dump())
    db.add(db_candle)
    db.commit()
    db.refresh(db_candle)
    return db_candle

def delete_candle(db: Session, candle_id: int) -> bool:
    db_candle = get_candle(db, candle_id)
    if db_candle:
        db.delete(db_candle)
        db.commit()
        return True
    return False

def get_stock_by_symbol(db: Session, symbol: str) -> Optional[Stock]:
    return db.query(Stock).filter(Stock.symbol == symbol).first()

def get_all_stocks(db: Session) -> List[Stock]:
    return db.query(Stock).all()

def get_latest_candles(db: Session, stock_id: int, limit: int = 2) -> List[Candle]:
    return db.query(Candle).filter(
        Candle.stock_id == stock_id
    ).order_by(desc(Candle.candle_time)).limit(limit).all()
