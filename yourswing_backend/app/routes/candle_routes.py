from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import schemas, crud
from app.models import Stock
from app.market_api import fetch_daily_candles
from app.strategy_engine import generate_signal

router = APIRouter(tags=["candles"])

@router.get("/candles", response_model=List[schemas.Candle])
def read_candles(symbol: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_candles(db=db, symbol=symbol, skip=skip, limit=limit)

@router.post("/candles", response_model=schemas.Candle)
def create_candle(candle: schemas.CandleCreate, db: Session = Depends(get_db)):
    return crud.create_candle(db=db, candle=candle)

@router.get("/fetch/{symbol}")
def fetch_stock(symbol: str):

    data = fetch_daily_candles(symbol)

    return {
        "symbol": symbol,
        "candles": data
    }



@router.get("/fetch-save/{symbol}")
def fetch_and_save(symbol: str, db: Session = Depends(get_db)):

    stock = db.query(Stock).filter(
        Stock.symbol == symbol
    ).first()

    if not stock:

        stock = Stock(
            symbol=symbol,
            company_name=symbol,
            exchange="Yahoo"
        )

        db.add(stock)
        db.commit()
        db.refresh(stock)

    candles = fetch_daily_candles(symbol)

    count = crud.save_candles(db, stock.id, candles)

    return {
        "symbol": symbol,
        "candles_saved": count
    }




@router.get("/api/trending")
def get_trending_stocks(db: Session = Depends(get_db)):
    from concurrent.futures import ThreadPoolExecutor
    from app.market_api import get_live_price
    import math

    stocks = crud.get_all_stocks(db)
    
    # 1. Fetch historical analysis for all stocks synchronously from the local database
    analyses = {}
    symbols_to_fetch = []
    
    for s in stocks:
        analysis = crud.get_latest_analysis(db, s.id)
        if analysis:
            analyses[s.symbol] = analysis
            symbols_to_fetch.append(s.symbol)
            
    # 2. Fetch live prices concurrently without passing the DB session
    live_prices = {}
    if symbols_to_fetch:
        with ThreadPoolExecutor(max_workers=30) as executor:
            # map returns results in the exact same order as symbols_to_fetch
            results = executor.map(get_live_price, symbols_to_fetch)
            for symbol, price_info in zip(symbols_to_fetch, results):
                live_prices[symbol] = price_info
            
    # 3. Combine analysis with live price and calculate dynamic change percent
    trending = []
    for s in stocks:
        symbol = s.symbol
        if symbol not in analyses:
            continue
            
        analysis = analyses[symbol]
        price_info = live_prices.get(symbol, {"live_price": 0.0, "previous_close": 0.0})
        
        live_price = price_info["live_price"]
        previous_close = price_info["previous_close"]
        
        if math.isnan(live_price):
            live_price = 0.0
        if math.isnan(previous_close):
            previous_close = 0.0
            
        # If Yahoo didn't provide a previous close, fallback to local DB candle
        if previous_close == 0.0:
            candles = crud.get_latest_candles(db, s.id, limit=1)
            if candles:
                previous_close = candles[0].close
                
        # If Yahoo couldn't fetch live price, fallback to previous close
        if live_price == 0.0 and previous_close > 0:
            live_price = previous_close
            
        change = 0.0
        change_percent = 0.0
        if previous_close > 0:
            change = round(live_price - previous_close, 2)
            change_percent = round((change / previous_close) * 100, 2)
            
        trending.append({
            "symbol": symbol.upper(),
            "price": round(live_price, 2),
            "change": change,
            "changePercent": change_percent,
            "signal": analysis["signal"]
        })
        
    return trending
@router.get("/api/analysis/{symbol}")
def get_stock_analysis(symbol: str, db: Session = Depends(get_db)):
    symbol = symbol.upper()
    
    # 1. Check if stock exists, if not create it
    stock = crud.get_stock_by_symbol(db, symbol)
    if not stock:
        stock = Stock(symbol=symbol, company_name=symbol, exchange="Yahoo")
        db.add(stock)
        db.commit()
        db.refresh(stock)
        
    # 2. Fetch live data from Yahoo Finance
    try:
        candles_data = fetch_daily_candles(symbol)
        if candles_data:
            crud.save_candles(db, stock.id, candles_data)
    except Exception as e:
        print(f"Error fetching from Yahoo: {e}")
        
    # 3. Calculate dynamic indicators with live price overlay
    analysis = crud.analyze_stock_with_live_price(db, stock.id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Not enough data to compute analysis")
    
    # Format exactly as requested
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
        "indicators": {
            "RSI": {
                "value": analysis["rsi"] if analysis["rsi"] else "N/A"
            },
            "EMA20": {
                "value": analysis["ema20"] if analysis["ema20"] else "N/A"
            },
            "EMA50": {
                "value": analysis["ema50"] if analysis["ema50"] else "N/A"
            }
        }
    }