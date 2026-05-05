from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CandleBase(BaseModel):
    symbol: str
    timeframe: str
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float

class CandleCreate(CandleBase):
    pass

class Candle(CandleBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
