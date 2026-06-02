from fastapi import APIRouter, Depends, HTTPException
import logging
from app.schemas import ComparisonRequest, ComparisonResponse, FlagComparison
from app.services.comparison_service import ComparisonService
from app.services.growthbook_error import GrowthBookError
from app.services.condition_parser import ConditionParser

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
        if request.condition_filter:
            logger.info(f"Filtering by condition: {request.condition_filter}")
        
        # Initialize comparison service
        comparison_service = ComparisonService()
        
        # Perform comparison
        comparisons = await comparison_service.compare_environments(
            source_environment=request.source_environment,
            target_environment=request.target_environment
        )
        
        # Apply condition filter if provided
        if request.condition_filter:
            # Convert FlagComparison objects to dictionaries for ConditionParser
            comparisons_dict = [comp.model_dump() for comp in comparisons]
            # For comparison objects, check both source_rules and target_rules
            parsed_condition = ConditionParser.parse_condition_string(request.condition_filter)
            
            if parsed_condition and parsed_condition.get('attribute'):
                filtered_comparisons = []
                for comp in comparisons_dict:
                    # Check source rules
                    source_rules = comp.get('source_rules', [])
                    source_conditions = ConditionParser.extract_conditions_from_rules(source_rules)
                    source_match = ConditionParser.matches_condition(parsed_condition, source_conditions)
                    
                    # Check target rules
                    target_rules = comp.get('target_rules', [])
                    target_conditions = ConditionParser.extract_conditions_from_rules(target_rules)
                    target_match = ConditionParser.matches_condition(parsed_condition, target_conditions)
                    
                    # Include if condition matches in either source or target
                    if source_match or target_match:
                        filtered_comparisons.append(comp)
                
                comparisons_dict = filtered_comparisons
            
            # Convert back to FlagComparison objects
            comparisons = [FlagComparison(**comp) for comp in comparisons_dict]
        
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
