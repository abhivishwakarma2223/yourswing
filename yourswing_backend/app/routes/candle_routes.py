from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import time
from app.database import get_db
from app import schemas, crud
from app.models import Stock
from app.market_api import fetch_daily_candles, fetch_batch_prices

router = APIRouter(tags=["candles"])

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "2.0.2",
        "engine": "Swing Score v2",
        "timestamp": time.time()
    }

@router.get("/sync")
def trigger_sync():
    """Manual sync trigger to update DB from cloud environment"""
    from app.market_api import fetch_all_active_stock_candles
    print("Starting manual remote sync...")
    results = fetch_all_active_stock_candles()
    return {
        "message": f"Sync complete for {len(results)} stocks",
        "timestamp": time.time()
    }

@router.get("/diag")
def database_diagnostics(db: Session = Depends(get_db)):
    """Check how many candles each stock has"""
    from app.models import Candle, Stock
    from sqlalchemy import func
    
    stats = db.query(
        Stock.symbol, 
        func.count(Candle.id).label("count")
    ).join(Candle).group_by(Stock.symbol).all()
    
    return {
        "total_stocks_with_data": len(stats),
        "requirement": "Minimum 200 candles for v2 scoring",
        "details": {s: c for s, c in stats}
    }




# ── SIMPLE MEMORY CACHE FOR TRENDING STOCKS ──────────────────────
TRENDING_CACHE = {
    "data": None,
    "expiry": 0
}
CACHE_DURATION = 600  # 10 Minutes in seconds

@router.get("/trending")
def get_trending_stocks(refresh: bool = False, db: Session = Depends(get_db)):
    global TRENDING_CACHE
    
    # Check if cache is still valid
    current_time = time.time()
    if not refresh and TRENDING_CACHE["data"] and current_time < TRENDING_CACHE["expiry"]:
        print("Serving Trending Stocks from Cache...")
        return TRENDING_CACHE["data"]

    from app.ranking_engine import get_top_ranked_stocks
    from app.database import get_db_connection
    import math

    print("Cache expired. Recalculating Trending Stocks (this takes a few seconds)...")
    
    # 1. Rank Stocks using the Ranking Engine
    try:
        top_stocks = get_top_ranked_stocks(get_db_connection, limit=10)
    except Exception as e:
        print(f"CRITICAL ERROR in ranking engine: {e}")
        raise HTTPException(status_code=500, detail=f"Ranking engine error: {str(e)}")

    symbols_to_fetch = [s["symbol"] for s in top_stocks]


    # 2. Fetch live prices in one bulk request (Hyper-speed)
    live_data = fetch_batch_prices(symbols_to_fetch)

    # 3. Combine ranking analysis with live data
    trending = []
    for stock_data in top_stocks:
        symbol = stock_data["symbol"]
        score = stock_data["score"]
        signal = stock_data["signal"]
        
        price_info = live_data.get(symbol, {"price": 0.0, "changePercent": 0.0})
        live_price = price_info["price"]
        
        # We need previous close for the backend logic (optional fallback)
        previous_close = stock_data.get("latest_price") or live_price
            
        change = round(live_price - previous_close, 2)
        change_percent = price_info["changePercent"]
            
        trending.append({
            "symbol": symbol.upper(),
            "price": round(live_price, 2),
            "change": change,
            "changePercent": change_percent,
            "signal": signal,
            "score": score
        })
    
    # Update cache
    TRENDING_CACHE["data"] = trending
    TRENDING_CACHE["expiry"] = current_time + CACHE_DURATION
    
    return trending

@router.get("/analysis/{symbol}")
def get_stock_analysis(symbol: str, db: Session = Depends(get_db)):
    symbol = symbol.upper()
    if "." not in symbol: symbol = f"{symbol}.NS"
    
    stock = crud.get_stock_by_symbol(db, symbol)
    if not stock:
        stock = Stock(symbol=symbol, company_name=symbol, exchange="Yahoo")
        db.add(stock)
        db.commit()
        db.refresh(stock)
        
    try:
        candles_data = fetch_daily_candles(symbol)
        if candles_data:
            crud.save_candles(db, stock.id, candles_data)
    except Exception as e:
        print(f"Error fetching from Yahoo: {e}")
        
    analysis = crud.analyze_stock_with_live_price(db, stock.id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Not enough data to compute analysis")
    
    return {
        "symbol": analysis["symbol"],
        "price": analysis["live_price"],
        "previous_close": analysis["previous_close"],
        "change": analysis["change"],
        "changePercent": analysis["changePercent"],
        "rsi": analysis["rsi"],
        "ema20": analysis["ema20"],
        "ema50": analysis["ema50"],
        "macd": analysis["macd"],
        "atr": analysis["atr"],
        "volume_ratio": analysis["volume_ratio"],
        "relative_strength": analysis["relative_strength"],
        "breakout": analysis["breakout"],
        "signal": analysis["signal"],
        "score": analysis.get("score", 0.0),
        "indicators": {
            "RSI": {"value": analysis["rsi"] if analysis["rsi"] else "N/A"},
            "EMA20": {"value": analysis["ema20"] if analysis["ema20"] else "N/A"},
            "EMA50": {"value": analysis["ema50"] if analysis["ema50"] else "N/A"}
        }
    }

@router.post("/prices/batch")
def get_batch_prices(symbols: List[str]):
    return fetch_batch_prices(symbols)

@router.get("/candles", response_model=List[schemas.Candle])
def read_candles(symbol: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_candles(db=db, symbol=symbol, skip=skip, limit=limit)

@router.post("/candles", response_model=schemas.Candle)
def create_candle(candle: schemas.CandleCreate, db: Session = Depends(get_db)):
    return crud.create_candle(db=db, candle=candle)
