"""
debug_stock_score.py
====================
Deep diagnostic scoring breakdown tool for a single stock.
Inspects component-level and indicator-level contributions to the final score.

Target: NATIONALUM.NS (or any symbol passed via CLI)

Usage:
  PYTHONPATH=. python scratch/debug_stock_score.py NATIONALUM.NS
"""

import sys
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Optional

# App Imports
from app.database import SessionLocal
from app.models import Stock, Candle
from app.indicator_engine import calculate_indicators, get_nifty_data
from app.scoring_engine import score_stock, classify_market_regime
from app.market_api import get_market_regime_dict, compute_market_breadth
from app.preprocessing.pipeline import run_preprocessing_pipeline
from app.preprocessing.rs_ranking import compute_rs_rankings
from app.preprocessing.sector_intelligence import compute_sector_data

# Configure Logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("ScoreDebugger")

def debug_symbol(symbol: str):
    db = SessionLocal()
    try:
        print(f"\n[DEBUG] Fetching data for {symbol} and Nifty universe...")
        
        # 1. Fetch Target Stock
        stock = db.query(Stock).filter(Stock.symbol == symbol).first()
        if not stock:
            print(f"Error: Stock {symbol} not found in database.")
            return

        # 2. Fetch a sample universe for RS/Sector computation (Nifty 50 or similar)
        # To get accurate RS ranks, we ideally need the full universe.
        # Let's take top 100 stocks as a proxy if we don't want to wait for 200.
        universe_stocks = db.query(Stock).limit(100).all()
        universe_symbols = [s.symbol for s in universe_stocks]
        if symbol not in universe_symbols:
            universe_symbols.append(symbol)

        candles_by_symbol = {}
        for s in universe_symbols:
            s_id = db.query(Stock.id).filter(Stock.symbol == s).scalar()
            cdf = db.query(Candle).filter(Candle.stock_id == s_id).order_by(Candle.candle_time.desc()).limit(300).all()
            if cdf:
                df = pd.DataFrame([{"time": c.candle_time, "open": c.open, "high": c.high, "low": c.low, "close": c.close, "volume": c.volume} for c in cdf]).sort_values("time")
                candles_by_symbol[s] = calculate_indicators(df)

        # 3. Precompute Batch Data
        nifty_df = get_nifty_data()
        rs_rankings = compute_rs_rankings(candles_by_symbol, nifty_df=nifty_df)
        sector_data = compute_sector_data(candles_by_symbol, rs_rankings)
        breadth = compute_market_breadth(candles_by_symbol)
        market = get_market_regime_dict(breadth_data=breadth)
        regime_info = classify_market_regime(market)

        # 4. Process Target Stock
        target_df = candles_by_symbol[symbol]
        target_df = run_preprocessing_pipeline(symbol, target_df, rs_rankings, sector_data)
        latest_row = target_df.iloc[-1].to_dict()

        # 5. Score with Debugging
        res = score_stock(latest_row, market)

        # ─────────────────────────────────────────────────────────────────────────────
        # OUTPUT: FULL SCORE BREAKDOWN
        # ─────────────────────────────────────────────────────────────────────────────
        print("\n" + "="*80)
        print(f"DEEP DIAGNOSTIC: {symbol}")
        print("="*80)
        
        print(f"Signal      : {res['signal']}")
        print(f"Final Score : {res['final_score']} / 100")
        print(f"Raw Score   : {res['raw_score']} / 93 (approx max)")
        print(f"Regime      : {res['regime']} (Multiplier: x{res['regime_multiplier']})")
        print(f"Sector      : {latest_row.get('sector_name', 'Unknown')}")

        print("\n[1] COMPONENT BREAKDOWN")
        print("-" * 30)
        for comp_name, data in res["components"].items():
            score = data["score"]
            max_s = data["max"]
            pct = (score / max_s * 100) if max_s > 0 else 0
            print(f"{comp_name.replace('_', ' ').title():20}: {score:5.2f} / {max_s:2} ({pct:4.1f}%)")

        print("\n[2] SUB-COMPONENT BREAKDOWN")
        print("-" * 30)
        for comp_name, data in res["components"].items():
            print(f"\n{comp_name.replace('_', ' ').title()}:")
            breakdown = data.get("breakdown", {})
            for sub, val in breakdown.items():
                print(f"  - {sub:25}: {val:5.2f}")

        print("\n[3] RAW INDICATOR VALUES")
        print("-" * 30)
        # Group indicators for readability
        indicators = [
            "RS_PERCENTILE_RANK", "RS_TREND_SLOPE", "RS_NEW_HIGH", "RS_VS_NIFTY",
            "SECTOR_RANK", "SECTOR_BREADTH_PCT", "STOCK_RS_WITHIN_SECTOR",
            "EMA20", "EMA50", "EMA200", "close",
            "ROC_1M", "ROC_3M", "ROC_6M", "RSI", "RSI_PREV10",
            "ATR", "ATR_PERCENT", "BASE_LENGTH_DAYS", "VOL_DURING_BASE", "BREAKOUT", "VCP_DETECTED",
            "RR_RATIO", "STRUCTURAL_STOP", "RESISTANCE_TARGET",
            "WEEKLY_TREND_BULLISH", "WEEKLY_EMA20_ABOVE_50"
        ]
        for ind in indicators:
            val = latest_row.get(ind)
            if isinstance(val, (float, np.float64)):
                print(f"{ind:25}: {val:10.4f}")
            else:
                print(f"{ind:25}: {val}")

        print("\n[4] MARKET REGIME IMPACT")
        print("-" * 30)
        raw = res["normalized_score"]
        mult = res["regime_multiplier"]
        final = res["final_score"]
        print(f"Score before regime gate : {raw:5.2f}")
        print(f"Regime Multiplier        : x{mult:.2f} ({res['regime']})")
        print(f"Score after regime gate  : {final:5.2f}")
        
        if mult < 1.0:
            reduction = (1 - mult) * 100
            print(f"Impact: Score reduced by {reduction:.0f}% due to market conditions.")

        print("\n[5] SCORING EXPLANATION")
        print("-" * 30)
        expl = []
        # RS
        rs_pct = latest_row.get("RS_PERCENTILE_RANK", 0)
        if rs_pct > 80: expl.append(f"• RS percentile is very strong ({rs_pct:.0f}th percentile)")
        elif rs_pct < 40: expl.append(f"• RS percentile is weak ({rs_pct:.0f}th percentile)")
        
        # Breakout
        if not latest_row.get("BREAKOUT"):
            expl.append("• Breakout quality weak because breakout flag is False")
        else:
            expl.append("• Active breakout detected; boosting breakout quality")
            
        # RR
        rr = latest_row.get("RR_RATIO", 0)
        if rr > 3: expl.append(f"• Risk reward excellent due to RR ratio above 3 ({rr:.1f})")
        elif rr < 1.5: expl.append(f"• Risk reward poor due to RR ratio below 1.5 ({rr:.1f})")
        
        # VCP
        if latest_row.get("VCP_DETECTED"):
            expl.append("• Coiled price action detected (VCP); reducing volatility risk")
            
        # Trend
        if not latest_row.get("WEEKLY_TREND_BULLISH"):
            expl.append("• WARNING: Daily setup not confirmed by Weekly trend")
            
        # Regime
        if mult <= 0.6:
            expl.append(f"• Final score heavily suppressed because market regime is {res['regime']}")

        for e in expl: print(e)

        print("\n[6] MISSING/FALLBACK DETECTION")
        print("-" * 30)
        missing = [i for i in indicators if latest_row.get(i) is None]
        print(f"Missing field count : {len(missing)}")
        if missing: print(f"Fields: {', '.join(missing)}")
        
        fallbacks = 0
        if latest_row.get("RS_PERCENTILE_RANK") == 50.0: fallbacks += 1
        if latest_row.get("SECTOR_BREADTH_PCT") == 50.0: fallbacks += 1
        print(f"Fallback usage count: {fallbacks} (approx)")

        # ─────────────────────────────────────────────────────────────────────────────
        # VISUALS
        # ─────────────────────────────────────────────────────────────────────────────
        print(f"\n[7] Generating charts in scratch/diagnostic_{symbol}.png...")
        
        plt.figure(figsize=(12, 6))
        
        # Horizontal Bar Chart
        plt.subplot(1, 2, 1)
        comps = list(res["components"].keys())
        scores = [res["components"][c]["score"] for c in comps]
        max_scores = [res["components"][c]["max"] for c in comps]
        
        y_pos = np.arange(len(comps))
        plt.barh(y_pos, max_scores, color='gray', alpha=0.2, label='Max Possible')
        plt.barh(y_pos, scores, color='teal', label='Actual Score')
        plt.yticks(y_pos, [c.replace('_', ' ').title() for c in comps])
        plt.xlabel('Points')
        plt.title('Component Contributions')
        plt.legend()

        # Pie Chart
        plt.subplot(1, 2, 2)
        valid_comps = {k: v["score"] for k, v in res["components"].items() if v["score"] > 0}
        if valid_comps:
            plt.pie(valid_comps.values(), labels=[k.replace('_', ' ').title() for k in valid_comps.keys()], autopct='%1.1f%%')
            plt.title('Score Composition (Raw)')
        
        plt.tight_layout()
        plt.savefig(f"scratch/diagnostic_{symbol}.png")

        print("\n[8] FINAL DIAGNOSTIC SUMMARY")
        print("-" * 30)
        sorted_comps = sorted(res["components"].items(), key=lambda x: x[1]["score"], reverse=True)
        print(f"Strongest Component : {sorted_comps[0][0].replace('_', ' ').title()}")
        print(f"Weakest Component   : {sorted_comps[-1][0].replace('_', ' ').title()}")
        
        if res["final_score"] > 60:
            print("Verdict: This stock shows strong institutional characteristics.")
        elif res["normalized_score"] > 60 and mult < 0.7:
            print("Verdict: High-quality stock being suppressed by broad market weakness.")
        else:
            print("Verdict: Lacks sufficient conviction/setup for institutional entry.")

    finally:
        db.close()

if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "NATIONALUM.NS"
    debug_symbol(sym)
