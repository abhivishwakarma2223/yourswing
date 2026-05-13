"""
app/market_update.py
==========================
Runs every 60 seconds during market hours.
"""

import json
import logging
from datetime import date, datetime, timezone, time as dtime

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.live_overlay import fetch_batch_live_prices, compute_live_overlay

logger = logging.getLogger(__name__)

MARKET_OPEN_IST  = dtime(9, 15)
MARKET_CLOSE_IST = dtime(15, 35)


def is_market_open() -> bool:
    import pytz
    ist  = pytz.timezone("Asia/Kolkata")
    now  = datetime.now(ist)
    if now.weekday() >= 5: return False
    t = now.time().replace(tzinfo=None)
    return MARKET_OPEN_IST <= t <= MARKET_CLOSE_IST


def run_live_update(db: Session) -> dict:
    t_start = datetime.now(timezone.utc)
    today = date.today()

    rows  = db.execute(text("""
        SELECT symbol, final_score, signal, latest_price, atr_percent, breakout
        FROM daily_stock_candidates
        WHERE trade_date = :td
        ORDER BY final_score DESC
        LIMIT 50
    """), {"td": today}).mappings().all()

    if not rows:
        return {"status": "skipped", "reason": "no_daily_candidates"}

    symbols = [r["symbol"] for r in rows]
    live_prices = fetch_batch_live_prices(symbols)

    if not live_prices:
        return {"status": "skipped", "reason": "no_live_prices"}

    updated = 0
    for row in rows:
        sym  = row["symbol"]
        live = live_prices.get(sym)
        if not live: continue

        try:
            overlay = compute_live_overlay(
                institutional_score  = float(row["final_score"] or 0),
                snapshot_price       = float(row["latest_price"] or 0),
                live                 = live,
                institutional_signal = row["signal"] or "NEUTRAL",
                breakout_at_snapshot = bool(row["breakout"]),
                atr_percent          = float(row["atr_percent"] or 2.0),
            )

            db.execute(text("""
                INSERT INTO live_market_state (
                    symbol, live_price, prev_close, live_change, live_change_pct,
                    day_open, day_high, day_low, live_volume,
                    institutional_score, dynamic_live_score, live_delta,
                    live_status, live_signal, breakout_active,
                    adjustment_breakdown, gap_pct, trade_date, updated_at
                ) VALUES (
                    :symbol, :live_price, :prev_close, :live_change, :live_change_pct,
                    :day_open, :day_high, :day_low, :live_volume,
                    :institutional_score, :dynamic_live_score, :live_delta,
                    :live_status, :live_signal, :breakout_active,
                    :adjustment_breakdown, :gap_pct, :trade_date, NOW()
                )
                ON CONFLICT (symbol) DO UPDATE SET
                    live_price = EXCLUDED.live_price,
                    live_change = EXCLUDED.live_change,
                    live_change_pct = EXCLUDED.live_change_pct,
                    dynamic_live_score = EXCLUDED.dynamic_live_score,
                    live_status = EXCLUDED.live_status,
                    live_signal = EXCLUDED.live_signal,
                    updated_at = NOW()
            """), {
                "symbol":               sym,
                "live_price":           float(live["price"]),
                "prev_close":           float(live["prev_close"]),
                "live_change":          float(live["change"]),
                "live_change_pct":      float(live["change_pct"]),
                "day_open":             float(live["day_open"]),
                "day_high":             float(live["day_high"]),
                "day_low":              float(live["day_low"]),
                "live_volume":          int(live["volume"]),
                "institutional_score":  float(overlay["live_score"] - overlay["live_delta"]),
                "dynamic_live_score":   float(overlay["live_score"]),
                "live_delta":           float(overlay["live_delta"]),
                "live_status":          "ACTIVE", 
                "live_signal":          str(overlay["live_signal"]),
                "breakout_active":      bool(row["breakout"]),
                "adjustment_breakdown": json.dumps(overlay["adjustments"]),
                "gap_pct":              float(overlay["gap_pct"]),
                "trade_date":           today,
            })
            updated += 1
        except Exception as e:
            logger.error(f"[{sym}] live update failed: {e}", exc_info=True)
            # No rollback here to allow other symbols to update, 
            # but we could use savepoints if we wanted to be very strict.

    db.commit()
    duration = (datetime.now(timezone.utc) - t_start).total_seconds() * 1000
    return {"status": "ok", "updated": updated, "duration_ms": round(duration, 1)}
