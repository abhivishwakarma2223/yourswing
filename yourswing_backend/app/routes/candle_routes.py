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
    stocks = crud.get_all_stocks(db)
    trending = []
    for s in stocks:
        analysis = crud.analyze_stock_with_live_price(db, s.id)
        if not analysis:
            continue
            
        trending.append({
            "symbol": analysis["symbol"],
            "price": analysis["live_price"],
            "change": analysis["change"],
            "changePercent": analysis["changePercent"],
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