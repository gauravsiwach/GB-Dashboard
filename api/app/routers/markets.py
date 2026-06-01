from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
from app.db import get_db
from app.models import Market
from app.schemas import MarketCreate, MarketResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("", response_model=list[MarketResponse])
async def get_markets(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Market))
        markets = result.scalars().all()
        logger.info(f"Retrieved {len(markets)} markets")
        return markets
    except Exception as e:
        logger.error(f"Error retrieving markets: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{market_id}", response_model=MarketResponse)
async def get_market(market_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Market).where(Market.id == market_id))
        market = result.scalar_one_or_none()
        
        if not market:
            logger.warning(f"Market not found: {market_id}")
            raise HTTPException(status_code=404, detail="Market not found")
        
        logger.info(f"Retrieved market: {market_id}")
        return market
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving market {market_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("", response_model=MarketResponse, status_code=201)
async def create_market(market: MarketCreate, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Market).where(Market.name == market.name))
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.warning(f"Market already exists: {market.name}")
            raise HTTPException(status_code=400, detail="Market with this name already exists")
        
        db_market = Market(**market.model_dump())
        db.add(db_market)
        await db.commit()
        await db.refresh(db_market)
        
        logger.info(f"Created market: {market.name}")
        return db_market
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating market {market.name}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
