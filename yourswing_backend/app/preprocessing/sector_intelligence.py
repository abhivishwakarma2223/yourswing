"""
sector_intelligence.py
======================
Sector mapping + breadth analysis for all Nifty 200 stocks.

Computes, for each stock:
  SECTOR_RANK              — rank of sector by momentum (1 = strongest)
  TOTAL_SECTORS            — total sectors in universe (13)
  SECTOR_RS_SLOPE          — slope of sector RS vs Nifty (+ = improving)
  SECTOR_BREADTH_PCT       — % of sector stocks above their EMA50
  STOCK_RS_WITHIN_SECTOR   — stock's RS rank within its sector (percentile 0–100)
  sector_name              — human-readable sector label
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_SECTOR_CACHE: Optional[Dict] = None
_SECTOR_CACHE_TS: float = 0.0
_SECTOR_CACHE_TTL = 3600  # 1 hour


# ─────────────────────────────────────────────────────────────────────────────
# SECTOR MAPPING  — NSE official classification for Nifty 200
# ─────────────────────────────────────────────────────────────────────────────

NIFTY200_SECTOR_MAP: Dict[str, str] = {
    # Banking & Finance
    "360ONE.NS":    "Banking & Finance",
    "ABCAPITAL.NS": "Banking & Finance",
    "AUBANK.NS":    "Banking & Finance",
    "AXISBANK.NS":  "Banking & Finance",
    "BAJFINANCE.NS":"Banking & Finance",
    "BAJAJFINSV.NS":"Banking & Finance",
    "BAJAJHLDNG.NS":"Banking & Finance",
    "BANKBARODA.NS":"Banking & Finance",
    "BANKINDIA.NS": "Banking & Finance",
    "BSE.NS":       "Banking & Finance",
    "CANBK.NS":     "Banking & Finance",
    "CHOLAFIN.NS":  "Banking & Finance",
    "FEDERALBNK.NS":"Banking & Finance",
    "GROWW.NS":     "Banking & Finance",
    "HDFCAMC.NS":   "Banking & Finance",
    "HDFCBANK.NS":  "Banking & Finance",
    "HDFCLIFE.NS":  "Banking & Finance",
    "ICICIAMC.NS":  "Banking & Finance",
    "ICICIBANK.NS": "Banking & Finance",
    "ICICIGI.NS":   "Banking & Finance",
    "IDFCFIRSTB.NS":"Banking & Finance",
    "INDUSINDBK.NS":"Banking & Finance",
    "INDIANB.NS":   "Banking & Finance",
    "JIOFINANCIAL.NS": "Banking & Finance",
    "JIOFIN.NS":    "Banking & Finance",
    "KOTAKBANK.NS": "Banking & Finance",
    "LTF.NS":       "Banking & Finance",
    "LICIHSGFIN.NS":"Banking & Finance",
    "M&MFIN.NS":    "Banking & Finance",
    "MFSL.NS":      "Banking & Finance",
    "MOTILALOFS.NS":"Banking & Finance",
    "MUTHOOTFIN.NS":"Banking & Finance",
    "PAYTM.NS":     "Banking & Finance",
    "POLICYBZR.NS": "Banking & Finance",
    "PNB.NS":       "Banking & Finance",
    "RECLTD.NS":    "Banking & Finance",
    "SBICARD.NS":   "Banking & Finance",
    "SBILIFE.NS":   "Banking & Finance",
    "SBIN.NS":      "Banking & Finance",
    "SHRIRAMFIN.NS":"Banking & Finance",
    "TATACAP.NS":   "Banking & Finance",
    "TATAINVEST.NS":"Banking & Finance",
    "UNIONBANK.NS": "Banking & Finance",
    "YESBANK.NS":   "Banking & Finance",

    # Information Technology
    "COFORGE.NS":   "Information Technology",
    "HCLTECH.NS":   "Information Technology",
    "INFY.NS":      "Information Technology",
    "KPITTECH.NS":  "Information Technology",
    "LTM.NS":       "Information Technology",
    "MPHASIS.NS":   "Information Technology",
    "NAUKRI.NS":    "Information Technology",
    "OFSS.NS":      "Information Technology",
    "PERSISTENT.NS":"Information Technology",
    "TATAELXSI.NS": "Information Technology",
    "TATACOMM.NS":  "Information Technology",
    "TCS.NS":       "Information Technology",
    "TECHM.NS":     "Information Technology",
    "WIPRO.NS":     "Information Technology",

    # Automobile & Auto Ancillaries
    "ASHOKLEY.NS":  "Automobile",
    "BAJAJ-AUTO.NS":"Automobile",
    "BALKRISIND.NS":"Automobile",
    "BHARATFORG.NS":"Automobile",
    "BOSCHLTD.NS":  "Automobile",
    "EICHERMOT.NS": "Automobile",
    "HEROMOTOCO.NS":"Automobile",
    "HYUNDAI.NS":   "Automobile",
    "M&M.NS":       "Automobile",
    "MARUTI.NS":    "Automobile",
    "MOTHERSON.NS": "Automobile",
    "MRF.NS":       "Automobile",
    "EXIDEIND.NS":  "Automobile",
    "TVSMOTOR.NS":  "Automobile",
    "TMCV.NS":      "Automobile",
    "TMPV.NS":      "Automobile",

    # Energy & Oil/Gas
    "ADANIENSOL.NS":"Energy & Power",
    "ADANIGREEN.NS":"Energy & Power",
    "ADANIPOWER.NS":"Energy & Power",
    "ATGL.NS":      "Energy & Power",
    "BPCL.NS":      "Energy & Power",
    "COALINDIA.NS": "Energy & Power",
    "GAIL.NS":      "Energy & Power",
    "HINDPETRO.NS": "Energy & Power",
    "IOC.NS":       "Energy & Power",
    "JSWENERGY.NS": "Energy & Power",
    "NHPC.NS":      "Energy & Power",
    "NTPC.NS":      "Energy & Power",
    "OIL.NS":       "Energy & Power",
    "ONGC.NS":      "Energy & Power",
    "PFC.NS":       "Energy & Power",
    "POWERGRID.NS": "Energy & Power",
    "PRERMIERNERGY.NS": "Energy & Power",
    "PRERMIERNE.NS":"Energy & Power",
    "RELIANCE.NS":  "Energy & Power",
    "RVNL.NS":      "Energy & Power",
    "SUZLON.NS":    "Energy & Power",
    "TATAPOWER.NS": "Energy & Power",
    "WAAREENNER.NS":"Energy & Power",
    "WAAREENERGR.NS":"Energy & Power",
    "IREDA.NS":     "Energy & Power",
    "ENRIN.NS":     "Energy & Power",
    "WAAREEENER.NS":"Energy & Power",

    # FMCG & Consumer
    "BRITANNIA.NS": "FMCG",
    "COLPAL.NS":    "FMCG",
    "DABUR.NS":     "FMCG",
    "GODREJCP.NS":  "FMCG",
    "GODFRYPHLP.NS":"FMCG",
    "HINDUNILVR.NS":"FMCG",
    "ITC.NS":       "FMCG",
    "MARICO.NS":    "FMCG",
    "NESTLEIND.NS": "FMCG",
    "PATANJALI.NS": "FMCG",
    "RADICO.NS":    "FMCG",
    "TATACONSUM.NS":"FMCG",
    "UNITDDSPR.NS": "FMCG",
    "UNITDSSPR.NS": "FMCG",
    "UNITDSSPR.NS": "FMCG",
    "VBL.NS":       "FMCG",
    "ETERNAL.NS":   "FMCG",
    "SWIGGY.NS":    "FMCG",

    # Healthcare & Pharma
    "ABBOTINDIA.NS":"Healthcare",
    "ALKEM.NS":     "Healthcare",
    "APOLLOHOSP.NS":"Healthcare",
    "AUROPHARMA.NS":"Healthcare",
    "BIOCON.NS":    "Healthcare",
    "CIPLA.NS":     "Healthcare",
    "DIVISLAB.NS":  "Healthcare",
    "DRREDDY.NS":   "Healthcare",
    "FORTIS.NS":    "Healthcare",
    "GLENMARK.NS":  "Healthcare",
    "LAURUSLABS.NS":"Healthcare",
    "LUPIN.NS":     "Healthcare",
    "MANKIND.NS":   "Healthcare",
    "MAXHEALTH.NS": "Healthcare",
    "SUNPHARMA.NS": "Healthcare",
    "TORNTPHARM.NS":"Healthcare",
    "ZYDUSLIFE.NS": "Healthcare",

    # Metals & Mining
    "HINDALCO.NS":  "Metals & Mining",
    "HINDZINC.NS":  "Metals & Mining",
    "JINDALSTEL.NS":"Metals & Mining",
    "JSWSTEEL.NS":  "Metals & Mining",
    "NATIONALUM.NS":"Metals & Mining",
    "NMDC.NS":      "Metals & Mining",
    "SAIL.NS":      "Metals & Mining",
    "TATASTEEL.NS": "Metals & Mining",
    "UPL.NS":       "Metals & Mining",
    "VEDL.NS":      "Metals & Mining",
    "VMM.NS":       "Metals & Mining",

    # Capital Goods & Infrastructure
    "ABB.NS":       "Capital Goods",
    "BDL.NS":       "Capital Goods",
    "BEL.NS":       "Capital Goods",
    "BHEL.NS":      "Capital Goods",
    "CGPOWER.NS":   "Capital Goods",
    "COCHINSHIP.NS":"Capital Goods",
    "CONCOR.NS":    "Capital Goods",
    "CUMMINSIND.NS":"Capital Goods",
    "GMRAIRPORT.NS":"Capital Goods",
    "GVT&D.NS":     "Capital Goods",
    "HAL.NS":       "Capital Goods",
    "HAVELLS.NS":   "Capital Goods",
    "HUDCO.NS":     "Capital Goods",
    "IRFC.NS":      "Capital Goods",
    "IRCTC.NS":     "Capital Goods",
    "KEI.NS":       "Capital Goods",
    "LT.NS":        "Capital Goods",
    "MAZDOCK.NS":   "Capital Goods",
    "POLYCAB.NS":   "Capital Goods",
    "POWERINDIA.NS":"Capital Goods",
    "SIEMENS.NS":   "Capital Goods",
    "SOLARINDS.NS": "Capital Goods",
    "TIINDIA.NS":   "Capital Goods",

    # Real Estate
    "DLF.NS":       "Real Estate",
    "GODREJPROP.NS":"Real Estate",
    "LODHA.NS":     "Real Estate",
    "OBEROIRLTY.NS":"Real Estate",
    "PHOENIXLTD.NS":"Real Estate",
    "PRESTIGE.NS":  "Real Estate",

    # Consumer Durables & Retail
    "BLUESTARCO.NS":"Consumer Durables",
    "DIXON.NS":     "Consumer Durables",
    "DMART.NS":     "Consumer Durables",
    "KALYANKJIL.NS":"Consumer Durables",
    "LGENDIA.NS":   "Consumer Durables",
    "NYKAA.NS":     "Consumer Durables",
    "PAGEIND.NS":   "Consumer Durables",
    "TITAN.NS":     "Consumer Durables",
    "TRENT.NS":     "Consumer Durables",
    "VOLTAS.NS":    "Consumer Durables",
    "LENSKAR.NS":   "Consumer Durables",
    "LENSKAART.NS": "Consumer Durables",
    "LENSKARRT.NS": "Consumer Durables",

    # Chemicals & Specialty
    "APLAPOLLO.NS": "Chemicals",
    "ASTRAL.NS":    "Chemicals",
    "COROMANDEL.NS":"Chemicals",
    "LENSKAR.NS":   "Chemicals",
    "PIDILITIND.NS":"Chemicals",
    "PIIND.NS":     "Chemicals",
    "SRF.NS":       "Chemicals",
    "SUPREMEIND.NS":"Chemicals",
    "ASIANPAINT.NS":"Chemicals",

    # Telecom & Media
    "ADANIENT.NS":  "Telecom & Media",
    "ADANIPORTS.NS":"Telecom & Media",
    "BHARTIARTL.NS":"Telecom & Media",
    "IDEA.NS":      "Telecom & Media",
    "INDIATOWER.NS":"Telecom & Media",
    "INDUSTOWER.NS":"Telecom & Media",
    "INDHOTEL.NS":  "Telecom & Media",
    "INDIGOO.NS":   "Telecom & Media",
    "INDIGO.NS":    "Telecom & Media",
    "JUBLFOOD.NS":  "Telecom & Media",
    "MCX.NS":       "Telecom & Media",

    # Cement & Building Materials
    "AMBUJACEM.NS": "Cement",
    "GRASIM.NS":    "Cement",
    "SHREECEM.NS":  "Cement",
    "ULTRACEMC.NS": "Cement",
    "ULTRACEMCO.NS":"Cement",
}


def _get_sector(symbol: str) -> str:
    """Return sector for symbol, default 'Diversified'."""
    return NIFTY200_SECTOR_MAP.get(symbol, "Diversified")


def compute_sector_data(
    candles_by_symbol: Dict[str, "pd.DataFrame"],
    rs_rankings: Dict[str, dict],
) -> Dict[str, dict]:
    """
    Compute sector-level metrics for all symbols.

    Parameters
    ----------
    candles_by_symbol : Dict[symbol → DataFrame]
        Must have columns: close, EMA50, EMA200 (post-indicator computation).
    rs_rankings : Dict[symbol → {RS_PERCENTILE_RANK, ...}]
        Pre-computed RS rankings from rs_ranking.compute_rs_rankings().

    Returns
    -------
    Dict[symbol → {SECTOR_RANK, TOTAL_SECTORS, SECTOR_RS_SLOPE,
                   SECTOR_BREADTH_PCT, STOCK_RS_WITHIN_SECTOR, sector_name}]
    """
    global _SECTOR_CACHE, _SECTOR_CACHE_TS

    now = time.time()
    if _SECTOR_CACHE is not None and (now - _SECTOR_CACHE_TS) < _SECTOR_CACHE_TTL:
        logger.info("[SECTOR] Returning cached sector data")
        return _SECTOR_CACHE

    logger.info(f"[SECTOR] Computing sector intelligence for {len(candles_by_symbol)} symbols...")
    t0 = time.perf_counter()

    # ── Build per-sector data ─────────────────────────────────────────────────
    # Group symbols by sector
    sector_symbols: Dict[str, list] = {}
    for sym in candles_by_symbol:
        sec = _get_sector(sym)
        sector_symbols.setdefault(sec, []).append(sym)

    total_sectors = len(sector_symbols)

    # ── Per-sector breadth & RS ───────────────────────────────────────────────
    sector_metrics: Dict[str, dict] = {}

    for sector, syms in sector_symbols.items():
        above_ema50_count = 0
        above_ema200_count = 0
        rs_composite_values = []
        roc_3m_values = []

        for sym in syms:
            df = candles_by_symbol.get(sym)
            if df is None or df.empty:
                continue

            latest = df.iloc[-1]

            # Safe float conversion
            def _sf(v):
                try:
                    if v is None or (isinstance(v, float) and np.isnan(v)): return 0.0
                    return float(v)
                except: return 0.0

            # Breadth: above EMA50?
            close = _sf(latest.get("close"))
            ema50 = _sf(latest.get("EMA50"))
            ema200 = _sf(latest.get("EMA200"))

            if close > 0 and ema50 > 0:
                if close > ema50:
                    above_ema50_count += 1
                if ema200 > 0 and close > ema200:
                    above_ema200_count += 1


            # Sector RS composite
            rs_data = rs_rankings.get(sym, {})
            rs_pct = rs_data.get("RS_PERCENTILE_RANK", 50.0)
            rs_composite_values.append(rs_pct)

            # ROC 3M
            roc_3m = latest.get("ROC_3M", 0.0)
            if roc_3m is not None and not (isinstance(roc_3m, float) and np.isnan(roc_3m)):
                roc_3m_values.append(float(roc_3m))

        n = len(syms)
        breadth_pct = (above_ema50_count / n * 100) if n > 0 else 50.0
        avg_rs = np.mean(rs_composite_values) if rs_composite_values else 50.0
        avg_roc_3m = np.mean(roc_3m_values) if roc_3m_values else 0.0

        # Sector RS slope: use avg RS over time (approximated by avg of individual slopes)
        sector_slopes = [
            rs_rankings.get(sym, {}).get("RS_TREND_SLOPE", 0.0)
            for sym in syms
            if sym in rs_rankings
        ]
        sector_rs_slope = float(np.mean(sector_slopes)) if sector_slopes else 0.0

        sector_metrics[sector] = {
            "breadth_pct":    round(breadth_pct, 2),
            "avg_rs":         round(float(avg_rs), 2),
            "avg_roc_3m":     round(float(avg_roc_3m), 2),
            "sector_rs_slope":round(sector_rs_slope, 6),
            "n_stocks":       n,
        }

    # ── Rank sectors by composite momentum score ──────────────────────────────
    # Score: 0.5 × breadth_pct (normalized) + 0.3 × avg_rs + 0.2 × roc_3m
    if sector_metrics:
        sector_df = pd.DataFrame(sector_metrics).T
        sector_df["composite"] = (
            sector_df["breadth_pct"] * 0.5 +
            sector_df["avg_rs"] * 0.3 +
            sector_df["avg_roc_3m"].clip(-20, 30).apply(lambda x: (x + 20) / 50 * 100) * 0.2
        )
        sector_df["rank"] = sector_df["composite"].rank(ascending=False).astype(int)
        sector_rank_map = sector_df["rank"].to_dict()
        sector_breadth_map = sector_df["breadth_pct"].to_dict()
        sector_slope_map = sector_df["sector_rs_slope"].to_dict()
    else:
        sector_rank_map = {}
        sector_breadth_map = {}
        sector_slope_map = {}

    # ── Per-stock intra-sector RS rank ────────────────────────────────────────
    intra_sector_ranks: Dict[str, float] = {}
    for sector, syms in sector_symbols.items():
        rs_vals = {
            sym: rs_rankings.get(sym, {}).get("RS_PERCENTILE_RANK", 50.0)
            for sym in syms
        }
        if not rs_vals:
            continue
        rs_series = pd.Series(rs_vals)
        rs_pct_within = rs_series.rank(pct=True) * 100
        for sym, pct in rs_pct_within.items():
            intra_sector_ranks[sym] = round(float(pct), 2)

    # ── Assemble final per-symbol output ─────────────────────────────────────
    results: Dict[str, dict] = {}
    for sym in candles_by_symbol:
        sector = _get_sector(sym)
        sec_rank = sector_rank_map.get(sector, total_sectors // 2)
        results[sym] = {
            "SECTOR_RANK":            int(sec_rank),
            "TOTAL_SECTORS":          total_sectors,
            "SECTOR_RS_SLOPE":        sector_slope_map.get(sector, 0.0),
            "SECTOR_BREADTH_PCT":     sector_breadth_map.get(sector, 50.0),
            "STOCK_RS_WITHIN_SECTOR": intra_sector_ranks.get(sym, 50.0),
            "sector_name":            sector,
        }

    elapsed = time.perf_counter() - t0
    logger.info(f"[SECTOR] Intelligence computed for {len(results)} symbols in {elapsed:.2f}s")

    _SECTOR_CACHE = results
    _SECTOR_CACHE_TS = now
    return results


def invalidate_sector_cache():
    global _SECTOR_CACHE, _SECTOR_CACHE_TS
    _SECTOR_CACHE = None
    _SECTOR_CACHE_TS = 0.0


def get_sector_for_symbol(symbol: str) -> str:
    return _get_sector(symbol)
