from datetime import datetime, time
import pytz
import yfinance as yf
import pandas as pd
import time as time_module
from sqlalchemy import text
from app.database import engine
from typing import List, Dict, Optional

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
    SMART BATCH FETCH: 
    1. Checks live_market_state (hybrid cache) for data.
    2. Fetches remaining from yfinance.
    """
    if not symbols: return {}
    
    results = {}
    remaining_symbols = []
    
    # 1. Try to get from our hybrid cache first
    try:
        from app.database import engine
        with engine.connect() as conn:
            # Normalize to uppercase for DB lookup
            upper_symbols = [s.upper() for s in symbols]
            query = text("SELECT symbol, live_price, live_change, live_change_pct FROM live_market_state WHERE symbol = ANY(:symbols)")
            cache_rows = conn.execute(query, {"symbols": upper_symbols}).mappings().all()
            
            cache_map = {r["symbol"]: r for r in cache_rows}
            
            for orig in symbols:
                s_upper = orig.upper()
                if s_upper in cache_map:
                    row = cache_map[s_upper]
                    results[orig] = {
                        "price": float(row["live_price"]),
                        "change": float(row["live_change"] or 0.0),
                        "changePercent": float(row["live_change_pct"] or 0.0)
                    }
                else:
                    remaining_symbols.append(orig)
    except Exception as e:
        print(f"Cache lookup failed: {e}")
        remaining_symbols = symbols

    if not remaining_symbols:
        return results

    # 2. Fetch remaining from yfinance
    try:
        data = yf.download(remaining_symbols, period="7d", interval="1d", progress=False, group_by='ticker')
        
        for orig in remaining_symbols:
            try:
                s_upper = orig.upper()
                
                # Robust extraction: handle both MultiIndex and single level index
                if isinstance(data.columns, pd.MultiIndex):
                    if s_upper in data.columns.levels[0]:
                        stock_data = data[s_upper]
                    else:
                        # Sometimes it might not be in levels but still accessible
                        try:
                            stock_data = data[s_upper]
                        except:
                            results[orig] = {"price": 0.0, "change": 0.0, "changePercent": 0.0}
                            continue
                else:
                    # Single symbol might return flat columns if yfinance decides so
                    stock_data = data

                if stock_data is None or stock_data.empty:
                    results[orig] = {"price": 0.0, "change": 0.0, "changePercent": 0.0}
                    continue
                
                # Use 'Close' or 'Adj Close'
                col = 'Close' if 'Close' in stock_data.columns else 'Adj Close'
                if col not in stock_data.columns:
                    results[orig] = {"price": 0.0, "change": 0.0, "changePercent": 0.0}
                    continue

                close_series = stock_data[col].dropna()
                if close_series.empty:
                    results[orig] = {"price": 0.0, "change": 0.0, "changePercent": 0.0}
                    continue
                
                price = float(close_series.iloc[-1])
                prev_close = float(close_series.iloc[-2]) if len(close_series) > 1 else price
                
                results[orig] = {
                    "price": round(price, 2),
                    "change": round(price - prev_close, 2),
                    "changePercent": round(((price - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0
                }
            except Exception as e:
                print(f"Error processing {orig}: {e}")
                results[orig] = {"price": 0.0, "change": 0.0, "changePercent": 0.0}
    except Exception as e:
        print(f"Bulk Fetch Error: {e}")
        for s in remaining_symbols:
            if s not in results:
                results[s] = {"price": 0.0, "change": 0.0, "changePercent": 0.0}
                
    return results


# ─────────────────────────────────────────────────────────────────────────────
# VIX DATA  (mirrors Nifty cache pattern from indicator_engine.py)
# ─────────────────────────────────────────────────────────────────────────────

_VIX_CACHE: Optional[pd.DataFrame] = None
_VIX_LAST_FETCH: Optional[float] = None
_VIX_CACHE_TTL = 3600   # 1 hour


def get_vix_data() -> Optional[pd.DataFrame]:
    """
    Fetch India VIX (^INDIAVIX) daily data with a 1-hour in-memory cache.
    Returns a DataFrame with columns: close, EMA10.
    Returns None on failure.
    """
    global _VIX_CACHE, _VIX_LAST_FETCH

    now = time_module.time()
    if _VIX_CACHE is not None and _VIX_LAST_FETCH and (now - _VIX_LAST_FETCH < _VIX_CACHE_TTL):
        return _VIX_CACHE

    try:
        raw = yf.download("^INDIAVIX", period="1y", progress=False)
        if raw.empty:
            return None

        close_series = raw["Close"].squeeze()
        vix_df = pd.DataFrame({"close": close_series.values}, index=close_series.index)

        # Normalize index
        if hasattr(vix_df.index, "tz") and vix_df.index.tz is not None:
            vix_df.index = vix_df.index.tz_localize(None)
        vix_df.index = vix_df.index.date

        # EMA10 for rising-VIX detection
        vix_df["EMA10"] = vix_df["close"].ewm(span=10, adjust=False).mean()

        _VIX_CACHE = vix_df
        _VIX_LAST_FETCH = now
        return vix_df

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to fetch VIX data: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# MARKET REGIME DICT  (pass directly to classify_market_regime())
# ─────────────────────────────────────────────────────────────────────────────

def _safe_float(v, default=0.0):
    try:
        import numpy as np
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return default
        return float(v)
    except:
        return default

def compute_market_breadth(candles_by_symbol: Dict[str, pd.DataFrame]) -> dict:
    """
    Compute market-wide breadth metrics from a batch of candle DataFrames.
    """
    if not candles_by_symbol:
        return {
            "PCT_ABOVE_EMA50": 50.0,
            "ADV_DECLINE_RATIO": 1.0,
            "NEW_HIGHS_52W": 0,
            "NEW_LOWS_52W": 0
        }

    above_ema50 = 0
    advances = 0
    declines = 0
    new_highs = 0
    new_lows = 0
    total = 0

    for sym, df in candles_by_symbol.items():
        if df.empty: continue
        latest = df.iloc[-1]
        
        total += 1
        # Above EMA50
        close = _safe_float(latest.get("close"))
        ema50 = _safe_float(latest.get("EMA50"))
        if close > ema50 and ema50 > 0:
            above_ema50 += 1
            
        # Adv/Dec
        if len(df) > 1:
            prev_close = _safe_float(df["close"].iloc[-2])
            curr_close = _safe_float(df["close"].iloc[-1])
            if curr_close > prev_close:
                advances += 1
            elif curr_close < prev_close:
                declines += 1
        
        # 52W High/Low
        high_52w = _safe_float(latest.get("HIGH_52W"))
        if high_52w > 0:
            if close >= high_52w * 0.995:
                new_highs += 1
        # New low (approx)
        if len(df) >= 252:
            low_52w = df["low"].tail(252).min()
            low_52w = _safe_float(low_52w)
            if low_52w > 0 and close <= low_52w * 1.005:
                new_lows += 1

    res = {
        "PCT_ABOVE_EMA50": (above_ema50 / total * 100) if total > 0 else 50.0,
        "ADV_DECLINE_RATIO": (advances / max(declines, 1)) if total > 0 else 1.0,
        "NEW_HIGHS_52W": new_highs,
        "NEW_LOWS_52W": new_lows
    }
    
    # NEW: Persist to DB for cross-process consistency
    try:
        import json
        from sqlalchemy import text
        from app.database import engine
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO market_stats (key, value, updated_at) VALUES ('latest_breadth', :val, CURRENT_TIMESTAMP) "
                     "ON CONFLICT (key) DO UPDATE SET value = :val, updated_at = CURRENT_TIMESTAMP"),
                {"val": json.dumps(res)}
            )
            conn.commit()
    except Exception as e:
        print(f"Failed to persist market stats: {e}")

    return res


# ─────────────────────────────────────────────────────────────────────────────
# MARKET REGIME DICT  (pass directly to classify_market_regime())
# ─────────────────────────────────────────────────────────────────────────────

_REGIME_CACHE: dict = {}
_REGIME_CACHE_TS: float = 0.0

def get_market_regime_dict(breadth_data: Optional[dict] = None) -> dict:
    """
    Build the market dict required by classify_market_regime() in scoring_engine.
    """
    global _REGIME_CACHE, _REGIME_CACHE_TS
    
    now = time_module.time()
    # Cache regime for 5 minutes (to allow breadth updates within same scan but prevent spamming YF)
    if not breadth_data and _REGIME_CACHE and (now - _REGIME_CACHE_TS < 300):
        return _REGIME_CACHE

    from app.indicator_engine import get_nifty_data
    import pandas_ta as ta

    # ── Nifty ─────────────────────────────────────────────────────
    nifty_df = get_nifty_data()
    if nifty_df is None or nifty_df.empty:
        return {
            "NIFTY_CLOSE":       0.0,
            "NIFTY_EMA20":       0.0,
            "NIFTY_EMA50":       0.0,
            "NIFTY_EMA200":      0.0,
            "INDIAVIX":          15.0,
            "INDIAVIX_EMA10":    15.0,
            "PCT_ABOVE_EMA50":   50.0,
            "ADV_DECLINE_RATIO": 1.0,
            "NEW_HIGHS_52W":     0,
            "NEW_LOWS_52W":      0,
        }

    # EMA200 on Nifty
    nifty_ema200 = float(
        ta.ema(nifty_df["close"], length=200).iloc[-1]
    ) if len(nifty_df) >= 200 else float(nifty_df["close"].iloc[-1])

    nifty_latest = nifty_df.iloc[-1]

    # ── VIX ───────────────────────────────────────────────────────
    vix_df = get_vix_data()
    if vix_df is not None and not vix_df.empty:
        vix_close  = float(vix_df["close"].iloc[-1])
        vix_ema10  = float(vix_df["EMA10"].iloc[-1])
    else:
        vix_close  = 15.0
        vix_ema10  = 15.0

    # ── Breadth ───────────────────────────────────────────────────
    if not breadth_data:
        # NEW: Try to load from DB first
        try:
            import json
            from sqlalchemy import text
            from app.database import engine
            with engine.connect() as conn:
                row = conn.execute(text("SELECT value FROM market_stats WHERE key = 'latest_breadth'")).fetchone()
                if row:
                    breadth_data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        except Exception as e:
            print(f"Failed to load cached market stats: {e}")

    if not breadth_data:
        breadth_data = {
            "PCT_ABOVE_EMA50":   50.0,
            "ADV_DECLINE_RATIO": 1.0,
            "NEW_HIGHS_52W":     0,
            "NEW_LOWS_52W":      0,
        }

    res = {
        "NIFTY_CLOSE":       float(nifty_latest["close"]),
        "NIFTY_EMA20":       float(nifty_latest["EMA20"]),
        "NIFTY_EMA50":       float(nifty_latest["EMA50"]),
        "NIFTY_EMA200":      nifty_ema200,
        "INDIAVIX":          vix_close,
        "INDIAVIX_EMA10":    vix_ema10,
        **breadth_data
    }
    
    _REGIME_CACHE = res
    _REGIME_CACHE_TS = now
    return res

