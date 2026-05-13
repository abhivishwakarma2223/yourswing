from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index, Boolean, Date, BigInteger
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from datetime import datetime
from .database import Base


# STOCKS TABLE
class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    company_name = Column(String)
    exchange = Column(String)


# CANDLES TABLE
class Candle(Base):
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True, index=True)

    stock_id = Column(Integer, ForeignKey("stocks.id"))

    timeframe = Column(String)

    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

    candle_time = Column(DateTime)

    __table_args__ = (
        Index('idx_candles_stock_time', 'stock_id', 'candle_time'),
    )   


# INDICATORS TABLE
class Indicator(Base):
    __tablename__ = "indicators"

    id = Column(Integer, primary_key=True, index=True)

    stock_id = Column(Integer, ForeignKey("stocks.id"))

    indicator_name = Column(String)
    value = Column(Float)
    timeframe = Column(String)
    created_at = Column(DateTime)

    # for index
    __table_args__ = (
        Index('idx_indicators_stock_name_time', 'stock_id', 'indicator_name', 'created_at'),
    )


# SCORING SNAPSHOTS TABLE
class ScoringSnapshot(Base):
    __tablename__ = "scoring_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    scored_at = Column(DateTime, default=datetime.now)
    
    final_score = Column(Float)
    normalized_score = Column(Float)
    raw_score = Column(Float)
    
    signal = Column(String)
    regime = Column(String)
    regime_multiplier = Column(Float)
    
    components = Column(JSONB)
    missing_fields = Column(JSONB)
    data_quality_score = Column(Float)

    __table_args__ = (
        Index('idx_scoring_symbol_time', 'symbol', 'scored_at'),
    )


# SECTOR CACHE TABLE
class SectorCache(Base):
    __tablename__ = "sector_cache"

    symbol = Column(String, primary_key=True)
    sector = Column(String)
    sector_rank = Column(Integer)
    sector_breadth_pct = Column(Float)
    cached_at = Column(DateTime, default=datetime.now)


# DAILY CANDIDATES TABLE (Institutional Intelligence)
class DailyStockCandidate(Base):
    __tablename__ = "daily_stock_candidates"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False)
    trade_date = Column(Date, nullable=False, index=True)

    # Scores
    raw_score = Column(Float, nullable=False, default=0.0)
    final_score = Column(Float, nullable=False, default=0.0)
    signal = Column(String(20), nullable=False, default='NEUTRAL')

    # Setup Intelligence
    setup_type = Column(String(50))
    rr_ratio = Column(Float)
    entry_zone_low = Column(Float)
    entry_zone_high = Column(Float)
    stop_loss = Column(Float)
    target_price = Column(Float)

    # Snapshot price
    latest_price = Column(Float)

    # Market context
    regime = Column(String(30))
    regime_multiplier = Column(Float)
    sector = Column(String(50))

    # Component breakdown
    component_pct = Column(JSONB)
    flags = Column(JSONB)

    # Raw indicators at snapshot time
    rsi = Column(Float)
    volume_ratio = Column(Float)
    atr_percent = Column(Float)
    breakout = Column(Boolean, default=False)
    rs_percentile = Column(Float)
    dist_from_ema20 = Column(Float)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index('idx_dsc_symbol_date', 'symbol', 'trade_date'),
        Index('idx_dsc_score', 'trade_date', 'final_score'),
    )


# LIVE MARKET STATE TABLE (Transient Execution State)
class LiveMarketState(Base):
    __tablename__ = "live_market_state"

    symbol = Column(String(20), primary_key=True)

    # Live price data
    live_price = Column(Float)
    prev_close = Column(Float)
    live_change = Column(Float)
    live_change_pct = Column(Float)
    day_open = Column(Float)
    day_high = Column(Float)
    day_low = Column(Float)
    live_volume = Column(BigInteger)
    relative_volume = Column(Float)

    # Live score
    institutional_score = Column(Float)
    dynamic_live_score = Column(Float)
    live_delta = Column(Float)

    # Live status
    live_status = Column(String(30))
    live_signal = Column(String(20))

    # Live execution flags
    breakout_active = Column(Boolean, default=False)
    extended_from_ema20 = Column(Boolean, default=False)
    gap_up = Column(Boolean, default=False)
    gap_down = Column(Boolean, default=False)
    high_relative_volume = Column(Boolean, default=False)
    reversal_warning = Column(Boolean, default=False)

    # Live adjustment breakdown
    adjustment_breakdown = Column(JSONB)

    # Gap info
    gap_pct = Column(Float)
    intraday_range_pct = Column(Float)
    close_position = Column(Float)

    # Metadata
    trade_date = Column(Date)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)