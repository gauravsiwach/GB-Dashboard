from pydantic import BaseModel
from datetime import datetime


class MarketBase(BaseModel):
    name: str
    env_flow: str


class MarketCreate(MarketBase):
    pass


class MarketResponse(MarketBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
