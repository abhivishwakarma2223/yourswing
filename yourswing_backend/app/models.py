from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
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