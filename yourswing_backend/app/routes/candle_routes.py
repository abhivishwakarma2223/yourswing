from typing import List, Optional
import time
import logging
import math
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app import schemas, crud
from app.models import Stock
from app.market_api import fetch_daily_candles, fetch_batch_prices, is_market_closed

logger = logging.getLogger(__name__)

router = APIRouter(tags=["candles"])

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "2.1.0",
        "engine": "Hybrid Institutional v1",
        "timestamp": time.time()
    }

@router.get("/trending")
def get_trending_stocks(
    db:     Session = Depends(get_db),
    limit:  int     = Query(default=10, ge=1, le=50),
):
    """
    Returns the top trending stocks combining:
      - Institutional intelligence (daily_stock_candidates)
      - Live execution state       (live_market_state)
    """
    # 1. Load daily institutional data
    daily_rows = db.execute(text("""
        SELECT * FROM daily_stock_candidates
        WHERE trade_date = CURRENT_DATE
        ORDER BY final_score DESC
        LIMIT :limit
    """), {"limit": limit * 3}).mappings().all()

    # Fallback to last available snapshot
    if not daily_rows:
        daily_rows = db.execute(text("""
            SELECT * FROM daily_stock_candidates
            WHERE trade_date = (SELECT MAX(trade_date) FROM daily_stock_candidates)
            ORDER BY final_score DESC
            LIMIT :limit
        """), {"limit": limit * 3}).mappings().all()

    if not daily_rows:
        raise HTTPException(status_code=404, detail="No daily snapshot found.")

    symbols = [r["symbol"] for r in daily_rows]

    # 2. Load live state
    live_rows = db.execute(text("""
        SELECT * FROM live_market_state
        WHERE symbol = ANY(:symbols)
    """), {"symbols": symbols}).mappings().all()

    live_by_symbol = {r["symbol"]: dict(r) for r in live_rows}

    # 3. Merge
    merged = []
    for row in daily_rows:
        sym  = row["symbol"]
        live = live_by_symbol.get(sym)

        is_closed = is_market_closed()

        if live:
            # During market hours, use the dynamic live data
            # After market close, use the solid institutional data from the daily snapshot
            if not is_closed:
                price = live["live_price"]
                change_pct = live["live_change_pct"]
                score = live["dynamic_live_score"]
                signal = live["live_signal"]
            else:
                price = row["latest_price"]
                # For change pct after close, we could calculate it or just use 0.0 
                # but live["live_change_pct"] is usually the day's final change %
                change_pct = live["live_change_pct"] 
                score = row["final_score"]
                signal = row["signal"]
        else:
            price = row["latest_price"]
            change_pct = 0.0
            score = row["final_score"]
            signal = row["signal"]

        merged.append({
            "symbol": sym,
            "price": price,
            "changePercent": change_pct,
            "score": score,
            "signal": signal,
            "sector": row["sector"],
            "setupType": row["setup_type"],
            "rrRatio": row["rr_ratio"],
            "stopLoss": row["stop_loss"],
            "targetPrice": row["target_price"],
            "tradeDate": str(row["trade_date"])
        })

    # 4. Filter & Limit
    merged.sort(key=lambda x: x["score"], reverse=True)
    
    # Final safety check for NaN/None in scores
    for item in merged:
        if item["score"] is None or (isinstance(item["score"], float) and math.isnan(item["score"])):
            item["score"] = 0.0

    return merged[:limit]


@router.post("/admin/snapshot")
def trigger_snapshot(
    background_tasks: BackgroundTasks,
    force:   bool    = False,
    db:      Session = Depends(get_db),
):
    from app.snapshot_engine import run_daily_snapshot
    from app.database import engine as db_engine

    def _run():
        from app.database import SessionLocal
        _db = SessionLocal()
        try:
            run_daily_snapshot(_db, db_engine.raw_connection, force=force)
        except Exception as e:
            logger.error(f"Background snapshot failed: {e}", exc_info=True)
        finally:
            _db.close()

    background_tasks.add_task(_run)
    return {"status": "started"}


@router.post("/admin/live-update")
def trigger_live_update(db: Session = Depends(get_db)):
    from app.market_update import run_live_update
    return run_live_update(db)


@router.get("/analysis/{symbol}")
def get_stock_analysis(symbol: str, db: Session = Depends(get_db)):
    # Keep existing analysis logic for deep-dive
    stock = crud.get_stock_by_symbol(db, symbol)
    if not stock:
        stock = Stock(symbol=symbol, company_name=symbol, exchange="Yahoo")
        db.add(stock)
        db.commit()
        db.refresh(stock)
    
    fetch_daily_candles(symbol) # Ensure fresh data
    analysis = crud.analyze_stock_with_live_price(db, stock.id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Not enough data")
    return analysis

@router.post("/prices/batch")
def get_batch_prices(symbols: List[str]):
    return fetch_batch_prices(symbols)

@router.get("/candles", response_model=List[schemas.Candle])
def read_candles(symbol: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_candles(db=db, symbol=symbol, skip=skip, limit=limit)
