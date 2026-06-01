import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.schemas.promotion import PromotionRequest, PromotionResponse
from app.services.promotion_service import PromotionService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/promote", response_model=PromotionResponse)
async def promote_flags(request: PromotionRequest, db: AsyncSession = Depends(get_db)):
    """
    Promote flags from source to target environment.
    Creates missing flags in target environment and updates existing flags.
    """
    try:
        # Initialize promotion service
        promotion_service = PromotionService()
        
        # Promote flags
        logger.info(
            f"Promoting flags from {request.source_environment} to {request.target_environment} "
            f"for market_id={request.market_id}"
        )
        results = await promotion_service.promote_flags(
            source_environment=request.source_environment,
            target_environment=request.target_environment,
            market_id=request.market_id,
            flag_keys=request.flag_keys
        )
        
        # Calculate statistics
        total_flags = len(results)
        successful_count = sum(1 for r in results if r.status == "success")
        failed_count = sum(1 for r in results if r.status == "failed")
        skipped_count = sum(1 for r in results if r.status == "skipped")
        
        logger.info(
            f"Promotion completed: {successful_count} successful, "
            f"{failed_count} failed, {skipped_count} skipped"
        )
        
        return PromotionResponse(
            success=True,
            message=f"Promotion completed: {successful_count} successful, {failed_count} failed, {skipped_count} skipped",
            total_flags=total_flags,
            successful_count=successful_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            results=results
        )
        
    except Exception as e:
        logger.error(f"Error promoting flags: {e}")
        raise HTTPException(status_code=500, detail=str(e))
