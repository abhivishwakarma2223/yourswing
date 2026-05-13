"""
app/snapshot_engine.py
======================
Runs the FULL institutional scoring engine ONCE after market close.
Stores top 50 candidates in daily_stock_candidates.
"""

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

SNAPSHOT_TOP_N    = 50
CLEANUP_DAYS      = 90


def _detect_setup_type(latest: dict) -> str:
    breakout      = bool(latest.get("BREAKOUT", False))
    vcp           = bool(latest.get("VCP_DETECTED", False))
    run_from_base = float(latest.get("RUN_FROM_BASE_PCT") or 0)
    rsi           = float(latest.get("RSI") or 50)

    if vcp and breakout: return "VCP_BREAKOUT"
    if vcp: return "VCP_COILING"
    if breakout and run_from_base < 15: return "BASE_BREAKOUT"
    if breakout: return "BREAKOUT"
    if rsi >= 60 and run_from_base < 20: return "MOMENTUM_CONTINUATION"
    return "WATCHLIST"


def _compute_entry_zones(latest: dict) -> dict:
    close         = float(latest.get("close") or 0)
    atr           = float(latest.get("ATR") or 0)
    struct_stop   = float(latest.get("STRUCTURAL_STOP") or 0)
    target        = float(latest.get("RESISTANCE_TARGET") or 0)
    rr_ratio      = float(latest.get("RR_RATIO") or 0)

    entry_low  = round(close - atr * 0.3, 2) if atr > 0 else None
    entry_high = round(close + atr * 0.3, 2) if atr > 0 else None

    stop = None
    if struct_stop > 0 and struct_stop < close:
        stop = round(struct_stop, 2)
    elif atr > 0:
        stop = round(close - atr * 1.5, 2)

    tgt = None
    if target > close:
        tgt = round(target, 2)
    elif stop and close > stop:
        risk   = close - stop
        tgt    = round(close + risk * 2.5, 2)

    return {
        "entry_zone_low":  entry_low,
        "entry_zone_high": entry_high,
        "stop_loss":       stop,
        "target_price":    tgt,
        "rr_ratio":        rr_ratio or (round((tgt - close)/(close - stop), 2) if (stop and tgt and close > stop) else None),
    }


def run_daily_snapshot(
    db:              Session,
    db_conn_factory,
    force:           bool = False,
    target_date:     Optional[date] = None,
) -> dict:
    today = target_date or date.today()

    if not force:
        existing = db.execute(text("SELECT COUNT(*) FROM daily_stock_candidates WHERE trade_date = :td"), {"td": today}).scalar() or 0
        if existing > 0:
            return {"status": "skipped", "reason": "already_exists", "date": str(today)}

    logger.info(f"═══ Starting daily snapshot for {today} ═══")
    t_start = datetime.now(timezone.utc)

    from app.ranking_engine import RankingEngine
    from app.preprocessing.sector_intelligence import get_sector_for_symbol

    engine  = RankingEngine(db_conn_factory, max_workers=10)
    report  = engine.run()

    if not report.ranked:
        return {"status": "error", "reason": "no_results", "date": str(today)}

    top_candidates = report.ranked[:SNAPSHOT_TOP_N]

    saved  = 0
    errors = 0

    for r in top_candidates:
        try:
            latest_row = _get_latest_indicators(r.symbol, db_conn_factory)
            setup_type = _detect_setup_type(latest_row)
            zones      = _compute_entry_zones(latest_row)

            db.execute(text("""
                INSERT INTO daily_stock_candidates (
                    symbol, trade_date, raw_score, final_score, signal,
                    setup_type, rr_ratio,
                    entry_zone_low, entry_zone_high, stop_loss, target_price,
                    latest_price, regime, regime_multiplier, sector,
                    component_pct, flags,
                    rsi, volume_ratio, atr_percent, breakout,
                    rs_percentile, dist_from_ema20,
                    created_at, updated_at
                ) VALUES (
                    :symbol, :trade_date, :raw_score, :final_score, :signal,
                    :setup_type, :rr_ratio,
                    :entry_zone_low, :entry_zone_high, :stop_loss, :target_price,
                    :latest_price, :regime, :regime_multiplier, :sector,
                    :component_pct, :flags,
                    :rsi, :volume_ratio, :atr_percent, :breakout,
                    :rs_percentile, :dist_from_ema20,
                    NOW(), NOW()
                )
                ON CONFLICT (symbol, trade_date) DO UPDATE SET
                    final_score = EXCLUDED.final_score,
                    signal = EXCLUDED.signal,
                    latest_price = EXCLUDED.latest_price,
                    setup_type = EXCLUDED.setup_type,
                    rr_ratio = EXCLUDED.rr_ratio,
                    entry_zone_low = EXCLUDED.entry_zone_low,
                    entry_zone_high = EXCLUDED.entry_zone_high,
                    stop_loss = EXCLUDED.stop_loss,
                    target_price = EXCLUDED.target_price,
                    updated_at = NOW()
            """), {
                "symbol":           str(r.symbol),
                "trade_date":       today,
                "raw_score":        float(r.score),
                "final_score":      float(r.score),
                "signal":           str(r.signal),
                "setup_type":       str(setup_type),
                "rr_ratio":         float(zones["rr_ratio"]) if zones["rr_ratio"] else None,
                "entry_zone_low":   float(zones["entry_zone_low"]) if zones["entry_zone_low"] else None,
                "entry_zone_high":  float(zones["entry_zone_high"]) if zones["entry_zone_high"] else None,
                "stop_loss":        float(zones["stop_loss"]) if zones["stop_loss"] else None,
                "target_price":     float(zones["target_price"]) if zones["target_price"] else None,
                "latest_price":     float(r.latest_price),
                "regime":           str(getattr(r, "regime", "")) if getattr(r, "regime", None) else None,
                "regime_multiplier": float(getattr(r, "regime_multiplier", 1.0)) if getattr(r, "regime_multiplier", None) else None,
                "sector":           str(get_sector_for_symbol(r.symbol)),
                "component_pct":    json.dumps(r.component_pct or {}),
                "flags":            json.dumps([]),
                "rsi":              float(r.rsi),
                "volume_ratio":     float(r.volume_ratio),
                "atr_percent":      float(r.atr_percent),
                "breakout":         bool(r.breakout),
                "rs_percentile":    float(latest_row.get("RS_PERCENTILE_RANK") or 0),
                "dist_from_ema20":  float(latest_row.get("DISTANCE_FROM_EMA20") or 0),
            })
            saved += 1
        except Exception as e:
            errors += 1
            logger.error(f"[{r.symbol}] Snapshot insert failed: {e}", exc_info=True)
            db.rollback()

    db.commit()
    _cleanup_old_snapshots(db)
    duration = (datetime.now(timezone.utc) - t_start).total_seconds()

    return {
        "status":        "ok",
        "date":          str(today),
        "saved":         saved,
        "errors":        errors,
        "duration_sec":  round(duration, 1),
    }


def _get_latest_indicators(symbol: str, db_conn_factory) -> dict:
    try:
        from app.ranking_engine import CandleRepository, PREFERRED_CANDLES
        from app.indicator_engine import calculate_indicators
        from app.scoring_engine import (
            add_roc_columns, add_rsi_prev, add_run_from_base,
            add_52w_high, add_hv_percentile, add_volume_trend,
        )

        repo = CandleRepository(db_conn_factory)
        df   = repo.get_candles(symbol, PREFERRED_CANDLES)
        if df is None or df.empty: return {}

        df = calculate_indicators(df)
        df = add_volume_trend(df)
        df = add_roc_columns(df)
        df = add_rsi_prev(df)
        df = add_run_from_base(df)
        df = add_52w_high(df)
        df = add_hv_percentile(df)
        return df.iloc[-1].to_dict()
    except Exception as e:
        logger.debug(f"[{symbol}] indicator calc failed: {e}")
        return {}


def _cleanup_old_snapshots(db: Session):
    cutoff  = date.today() - timedelta(days=CLEANUP_DAYS)
    db.execute(text("DELETE FROM daily_stock_candidates WHERE trade_date < :cutoff"), {"cutoff": cutoff})
    db.commit()


if __name__ == "__main__":
    from app.database import SessionLocal, engine
    db = SessionLocal()
    try:
        print("Running daily snapshot...")
        result = run_daily_snapshot(db, engine.raw_connection, force=True)
        print(f"Result: {result}")
    finally:
        db.close()
