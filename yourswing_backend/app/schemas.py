from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CandleBase(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: float
    candle_time: datetime
    timeframe: str = "1d"

class CandleCreate(CandleBase):
    pass

class Candle(CandleBase):
    id: int
    stock_id: int

    class Config:
        from_attributes = True
