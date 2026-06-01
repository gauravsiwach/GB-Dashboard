from fastapi import APIRouter, Depends, HTTPException
import logging
from app.schemas import ComparisonRequest, ComparisonResponse
from app.services.comparison_service import ComparisonService
from app.services.growthbook_error import GrowthBookError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/compare", tags=["comparison"])


@router.post("", response_model=ComparisonResponse)
async def compare_environments(request: ComparisonRequest):
    """
    Compare flags between source and target environments.
    
    Args:
        request: Comparison request with source_environment, target_environment, and market_id
        
    Returns:
        ComparisonResponse with comparison results
    """
    try:
        logger.info(f"Comparing environments: {request.source_environment} -> {request.target_environment}")
        
        # Initialize comparison service
        comparison_service = ComparisonService()
        
        # Perform comparison
        comparisons = await comparison_service.compare_environments(
            source_environment=request.source_environment,
            target_environment=request.target_environment
        )
        
        # Calculate statistics
        total_flags = len(comparisons)
        in_sync_count = sum(1 for c in comparisons if c.status == "in_sync")
        different_count = sum(1 for c in comparisons if c.status == "different")
        missing_in_target_count = sum(1 for c in comparisons if c.status == "missing_in_target")
        missing_in_source_count = sum(1 for c in comparisons if c.status == "missing_in_source")
        
        logger.info(
            f"Comparison results: {total_flags} total, "
            f"{in_sync_count} in sync, "
            f"{different_count} different, "
            f"{missing_in_target_count} missing in target, "
            f"{missing_in_source_count} missing in source"
        )
        
        return ComparisonResponse(
            success=True,
            message="Comparison completed successfully",
            source_environment=request.source_environment,
            target_environment=request.target_environment,
            comparisons=comparisons,
            total_flags=total_flags,
            in_sync_count=in_sync_count,
            different_count=different_count,
            missing_in_target_count=missing_in_target_count,
            missing_in_source_count=missing_in_source_count
        )
        
    except GrowthBookError as e:
        logger.error(f"GrowthBook API error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch features from GrowthBook: {e.message}")
    except Exception as e:
        logger.error(f"Error comparing environments: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
