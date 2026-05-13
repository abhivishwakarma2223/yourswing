import json
from datetime import date
from sqlalchemy import text
from app.database import SessionLocal

db = SessionLocal()
try:
    today = date.today()
    sql = """
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
    """
    params = {
        "symbol":               "TEST_SYM",
        "live_price":           100.0,
        "prev_close":           95.0,
        "live_change":          5.0,
        "live_change_pct":      5.26,
        "day_open":             96.0,
        "day_high":             105.0,
        "day_low":              94.0,
        "live_volume":          1000000,
        "institutional_score":  80.0,
        "dynamic_live_score":   82.0,
        "live_delta":           2.0,
        "live_status":          "ACTIVE",
        "live_signal":          "BUY",
        "breakout_active":      False,
        "adjustment_breakdown": json.dumps([{"reason": "test", "delta": 2.0}]),
        "gap_pct":              1.0,
        "trade_date":           today,
    }
    db.execute(text(sql), params)
    db.commit()
    print("Success")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
