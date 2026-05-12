import json
import logging
import pandas as pd
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Stock, Candle
from app.indicator_engine import calculate_indicators
from app.scoring_engine import score_stock, classify_market_regime
from app.market_api import get_market_regime_dict, compute_market_breadth
from app.preprocessing.pipeline import run_preprocessing_pipeline
from app.preprocessing.rs_ranking import compute_rs_rankings
from app.preprocessing.sector_intelligence import compute_sector_data

# Configure logging to capture defaults
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("audit_logger")

def audit_stock(symbol: str, db: Session, rs_rankings=None, sector_data=None, market=None):
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        return {"symbol": symbol, "error": f"Stock {symbol} not found"}

    # Fetch candles
    candles_query = db.query(Candle).filter(Candle.stock_id == stock.id).order_by(Candle.candle_time.desc()).limit(300).all()
    if not candles_query:
        return {"symbol": symbol, "error": f"No candles found for {symbol}"}

    # Convert to DataFrame
    df = pd.DataFrame([{
        "time": c.candle_time,
        "open": c.open,
        "high": c.high,
        "low": c.low,
        "close": c.close,
        "volume": c.volume
    } for c in candles_query])
    df = df.sort_values("time")

    # Audit Preprocessing Pipeline
    logger.info(f"--- Auditing Preprocessing Pipeline for {symbol} ---")
    
    # 1. Base Indicators
    df = calculate_indicators(df)
    
    # 2. Institutional Pipeline
    df = run_preprocessing_pipeline(symbol, df, rs_rankings, sector_data)
    
    # Check if helper columns exist
    helpers = {
        "RS_RANK": "RS_PERCENTILE_RANK" in df.columns,
        "SECTOR": "SECTOR_BREADTH_PCT" in df.columns,
        "WEEKLY": "WEEKLY_TREND_BULLISH" in df.columns,
        "VCP": "VCP_DETECTED" in df.columns,
        "RR": "RR_RATIO" in df.columns,
        "HV_PCT": "HV_PERCENTILE" in df.columns
    }
    
    latest_row = df.iloc[-1].to_dict()
    if market is None:
        market = get_market_regime_dict()
    
    # Audit Scoring
    logger.info(f"--- Auditing Scoring Engine for {symbol} ---")
    
    # Required keys based on scoring_engine.py
    required_keys = [
        "RS_PERCENTILE_RANK", "RS_TREND_SLOPE", "RS_NEW_HIGH", "RS_VS_NIFTY",
        "SECTOR_RANK", "TOTAL_SECTORS", "SECTOR_RS_SLOPE", "SECTOR_BREADTH_PCT", "STOCK_RS_WITHIN_SECTOR",
        "EMA20", "EMA50", "EMA200", "close", "TREND_STRENGTH", "WEEKLY_TREND_BULLISH", "WEEKLY_EMA20_ABOVE_50",
        "HIGHER_HIGH", "HIGHER_LOW", "SWING_RANGE_PCT", "RUN_FROM_BASE_PCT",
        "HIGH_52W", "HIGHEST_20", "BASE_LENGTH_DAYS", "VOLUME_RATIO", "VOL_DURING_BASE", "CANDLE_BODY_PERCENT", "BREAKOUT",
        "RR_RATIO", "STRUCTURAL_STOP", "ATR", "RESISTANCE_TARGET", "DISTANCE_FROM_EMA20", "RANGE_COMPRESSION_PCT", "POCKET_PIVOT",
        "ROC_1M", "ROC_3M", "ROC_6M", "RSI", "RSI_PREV10", "CLOSE_NEAR_HIGH", "ATR_PERCENT", "VCP_DETECTED", "HV_PERCENTILE"
    ]
    
    missing_fields = [k for k in required_keys if k not in latest_row or latest_row[k] is None]
    
    result = score_stock(latest_row, market)
    
    regime_data = classify_market_regime(market)
    regime_name = regime_data["regime"]
    multiplier = regime_data["multiplier"]

    audit_data = {
        "symbol": symbol,
        "scores": {
            "raw_score": result["raw_score"],
            "normalized_score": result["normalized_score"],
            "final_score": result["final_score"],
            "regime": regime_name,
            "multiplier": multiplier,
            "signal": result["signal"]
        },
        "components": result["components"],
        "helpers_status": helpers,
        "missing_fields": list(set(missing_fields)),
        "breakout_flag": latest_row.get("BREAKOUT", False),
        "rr_ratio": round(latest_row.get("RR_RATIO", 0.0), 2),
        "rs_rank": latest_row.get("RS_PERCENTILE_RANK", 0.0),
        "sector_rs": latest_row.get("STOCK_RS_WITHIN_SECTOR", None),
        "regime_dict": market
    }
    
    return audit_data

def run_full_audit():
    with SessionLocal() as db:
        # Get symbols
        stocks = db.query(Stock).limit(10).all()
        symbols = [s.symbol for s in stocks]
        
        logger.info("Fetching all candles for batch processing...")
        candles_by_symbol = {}
        for s in symbols:
            cdf = db.query(Candle).filter(Candle.stock_id == db.query(Stock.id).filter(Stock.symbol == s).scalar()).order_by(Candle.candle_time.desc()).limit(300).all()
            if cdf:
                df = pd.DataFrame([{"time": c.candle_time, "open": c.open, "high": c.high, "low": c.low, "close": c.close, "volume": c.volume} for c in cdf]).sort_values("time")
                candles_by_symbol[s] = calculate_indicators(df)
        
        logger.info("Computing batch rankings...")
        rs_rankings = compute_rs_rankings(candles_by_symbol, nifty_df=None)
        sector_data = compute_sector_data(candles_by_symbol, rs_rankings)
        
        logger.info("Computing market breadth...")
        breadth = compute_market_breadth(candles_by_symbol)
        market = get_market_regime_dict(breadth_data=breadth)
        
        results = []
        for s in symbols:
            logger.info(f"Auditing {s}...")
            res = audit_stock(s, db, rs_rankings, sector_data, market)
            results.append(res)
            
        print("\n" + "="*80)
        print("INSTITUTIONAL SCORING ENGINE AUDIT REPORT (v2)")
        print("="*80)
        
        print(f"\nMARKET CONTEXT:")
        print(f"  Regime: {results[0]['scores']['regime']} (x{results[0]['scores']['multiplier']})")
        print(f"  Breadth: {market.get('PCT_ABOVE_EMA50')}% Above EMA50, Adv/Dec: {market.get('ADV_DECLINE_RATIO')}")
        print(f"  VIX: {market.get('INDIAVIX')}")
        
        for res in results:
            if "error" in res:
                print(f"\n[{res['symbol']}] Error: {res['error']}")
                continue
                
            s = res["scores"]
            print(f"\n[{res['symbol']}]")
            print(f"  Scores: Raw={s['raw_score']}, Norm={s['normalized_score']}, Final={s['final_score']}")
            print(f"  Signal: {s['signal']}")
            print(f"  Breakdown:")
            for comp, data in res["components"].items():
                print(f"    - {comp:20}: {data['score']}/{data['max']} ({round(data['score']/data['max']*100 if data['max']>0 else 0, 1)}%)")
            
            print(f"  New Indicators Status:")
            for h, status in res["helpers_status"].items():
                print(f"    - {h:20}: {'OK' if status else 'MISSING'}")
            
            print(f"  Missing Fields: {', '.join(res['missing_fields']) if res['missing_fields'] else 'None'}")
            print(f"  Key Values: RS_Rank={res['rs_rank']}, Sector_RS={res['sector_rs']}, RR_Ratio={res['rr_ratio']}, Breakout={res['breakout_flag']}")

if __name__ == "__main__":
    run_full_audit()

