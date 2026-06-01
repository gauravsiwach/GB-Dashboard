from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Market
import logging

logger = logging.getLogger(__name__)


async def seed_india_market(session: AsyncSession):
    result = await session.execute(select(Market).where(Market.name == "india"))
    existing = result.scalar_one_or_none()
    
    if existing:
        logger.info("India market already exists, skipping seed")
        return
    
    india_market = Market(
        name="india",
        env_flow="dev->qa->uat->production"
    )
    session.add(india_market)
    await session.commit()
    logger.info("India market seeded successfully")
