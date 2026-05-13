"""
Create both institutional intelligence tables.

Run ONCE:
    python -m app.create_tables
"""

from app.database import get_db
from sqlalchemy import text

DAILY_CANDIDATES_TABLE = """
CREATE TABLE IF NOT EXISTS daily_stock_candidates (
    id                  SERIAL          PRIMARY KEY,
    symbol              VARCHAR(20)     NOT NULL,
    trade_date          DATE            NOT NULL,

    -- Scores
    raw_score           FLOAT           NOT NULL DEFAULT 0,
    final_score         FLOAT           NOT NULL DEFAULT 0,
    signal              VARCHAR(20)     NOT NULL DEFAULT 'NEUTRAL',

    -- Setup intelligence
    setup_type          VARCHAR(50),        -- BREAKOUT / PULLBACK / VCP / CUP_HANDLE
    rr_ratio            FLOAT,              -- Risk:Reward ratio
    entry_zone_low      FLOAT,              -- Optimal entry zone low
    entry_zone_high     FLOAT,              -- Optimal entry zone high
    stop_loss           FLOAT,              -- Structural stop level
    target_price        FLOAT,              -- Resistance / measured move target

    -- Snapshot price
    latest_price        FLOAT,

    -- Market context
    regime              VARCHAR(30),        -- TRENDING_BULL / CHOPPY_BULL / etc
    regime_multiplier   FLOAT,
    sector              VARCHAR(50),

    -- Component breakdown (for frontend drill-down)
    component_pct       JSONB,
    flags               JSONB,

    -- Raw indicators at snapshot time
    rsi                 FLOAT,
    volume_ratio        FLOAT,
    atr_percent         FLOAT,
    breakout            BOOLEAN         DEFAULT FALSE,
    rs_percentile       FLOAT,          -- RS rank at snapshot
    dist_from_ema20     FLOAT,          -- % distance from EMA20 at snapshot

    -- Metadata
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW(),

    UNIQUE(symbol, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_dsc_trade_date
    ON daily_stock_candidates(trade_date DESC);

CREATE INDEX IF NOT EXISTS idx_dsc_score
    ON daily_stock_candidates(trade_date, final_score DESC);

CREATE INDEX IF NOT EXISTS idx_dsc_symbol_date
    ON daily_stock_candidates(symbol, trade_date);
"""

LIVE_MARKET_STATE_TABLE = """
CREATE TABLE IF NOT EXISTS live_market_state (
    -- PRIMARY KEY = symbol (one row per stock, updated in-place)
    symbol                  VARCHAR(20)     PRIMARY KEY,

    -- Live price data
    live_price              FLOAT,
    prev_close              FLOAT,
    live_change             FLOAT,              -- absolute change
    live_change_pct         FLOAT,              -- % change
    day_open                FLOAT,
    day_high                FLOAT,
    day_low                 FLOAT,
    live_volume             BIGINT,
    relative_volume         FLOAT,              -- live_volume / avg_volume

    -- Live score (institutional score + live adjustments)
    institutional_score     FLOAT,              -- from daily_stock_candidates
    dynamic_live_score      FLOAT,              -- after live adjustments
    live_delta              FLOAT,              -- difference (live - institutional)

    -- Live status
    live_status             VARCHAR(30),        -- BREAKOUT_CONFIRMED / EXTENDED / etc
    live_signal             VARCHAR(20),        -- STRONG BUY / BUY / WEAK BUY etc

    -- Live execution flags (boolean per condition)
    breakout_active         BOOLEAN         DEFAULT FALSE,
    extended_from_ema20     BOOLEAN         DEFAULT FALSE,
    gap_up                  BOOLEAN         DEFAULT FALSE,
    gap_down                BOOLEAN         DEFAULT FALSE,
    high_relative_volume    BOOLEAN         DEFAULT FALSE,
    reversal_warning        BOOLEAN         DEFAULT FALSE,

    -- Live adjustment breakdown (for frontend transparency)
    adjustment_breakdown    JSONB,              -- list of {reason, delta}

    -- Gap info
    gap_pct                 FLOAT,
    intraday_range_pct      FLOAT,              -- (high-low)/prev_close * 100
    close_position          FLOAT,              -- 0=at low, 1=at high

    -- Metadata
    trade_date              DATE,               -- which daily snapshot this is from
    updated_at              TIMESTAMPTZ     DEFAULT NOW()
);
"""


def create_tables():
    db = next(get_db())
    try:
        db.execute(text(DAILY_CANDIDATES_TABLE))
        db.execute(text(LIVE_MARKET_STATE_TABLE))
        db.commit()
        print("Tables created successfully.")
        print("   - daily_stock_candidates")
        print("   - live_market_state")
    except Exception as e:
        db.rollback()
        print(f"Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_tables()
