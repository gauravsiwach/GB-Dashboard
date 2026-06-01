import logging
from typing import List, Dict, Any
from app.services.growthbook_client import GrowthBookClient
from app.schemas.comparison import ComparisonStatus, FlagComparison

logger = logging.getLogger(__name__)


class ComparisonService:
    """Service for comparing flags between environments."""
    
    def __init__(self):
        self.gb_client = GrowthBookClient()
    
    async def compare_environments(
        self, 
        source_environment: str, 
        target_environment: str
    ) -> List[FlagComparison]:
        """
        Compare flags between source and target environments.
        
        Args:
            source_environment: Source environment name (e.g., "dev")
            target_environment: Target environment name (e.g., "production")
            
        Returns:
            List of FlagComparison objects with comparison results
        """
        try:
            # Fetch all features from GrowthBook
            logger.info(f"Fetching features from GrowthBook for comparison")
            response = await self.gb_client.get_all_features()
            
            # Extract features from response
            features = response.get("features", []) if isinstance(response, dict) else []
            if not features and isinstance(response, list):
                features = response
            
            comparisons = []
            
            for feature in features:
                feature_id = feature.get("id")
                feature_key = feature.get("key", feature_id)
                environments = feature.get("environments", {})
                archived = feature.get("archived", False)
                draft = feature.get("draft", False)
                
                if not feature_id:
                    continue
                
                # Skip archived flags
                if archived:
                    logger.info(f"Skipping archived feature: {feature_id}")
                    continue
                
                # Skip draft flags (optional - uncomment if you want to skip drafts)
                # if draft:
                #     logger.info(f"Skipping draft feature: {feature_id}")
                #     continue
                
                # Get source and target environment configs
                source_env_config = environments.get(source_environment)
                target_env_config = environments.get(target_environment)
                
                # Determine comparison status
                comparison = self._compare_flag(
                    feature_key,
                    feature_id,
                    source_env_config,
                    target_env_config,
                    source_environment,
                    target_environment,
                    draft
                )
                
                comparisons.append(comparison)
            
            logger.info(f"Comparison complete: {len(comparisons)} flags compared")
            return comparisons
            
        except Exception as e:
            logger.error(f"Error comparing environments: {e}")
            raise
    
    def _compare_flag(
        self,
        key: str,
        feature_id: str,
        source_config: Dict[str, Any],
        target_config: Dict[str, Any],
        source_env_name: str,
        target_env_name: str,
        draft: bool = False
    ) -> FlagComparison:
        """
        Compare a single flag between source and target environments.
        
        Args:
            key: Flag key
            feature_id: GrowthBook feature ID
            source_config: Source environment configuration
            target_config: Target environment configuration
            source_env_name: Source environment name
            target_env_name: Target environment name
            draft: Whether the flag is in draft status
            
        Returns:
            FlagComparison with comparison result
        """
        source_enabled = source_config.get("enabled", False) if source_config else False
        target_enabled = target_config.get("enabled", False) if target_config else False
        source_value = source_config.get("defaultValue") if source_config else None
        target_value = target_config.get("defaultValue") if target_config else None
        
        # Determine status
        if not source_config and not target_config:
            # Flag not configured in either environment
            status = ComparisonStatus.MISSING_IN_SOURCE
        elif not source_config:
            # Flag not in source but in target
            status = ComparisonStatus.MISSING_IN_SOURCE
        elif not target_config:
            # Flag in source but not in target
            status = ComparisonStatus.MISSING_IN_TARGET
        elif draft:
            # Flag is in draft - treat as different regardless of values
            status = ComparisonStatus.DIFFERENT
        elif source_enabled == target_enabled and source_value == target_value:
            # Flags are in sync
            status = ComparisonStatus.IN_SYNC
        else:
            # Flags are different
            status = ComparisonStatus.DIFFERENT
        
        return FlagComparison(
            key=key,
            growthbook_feature_id=feature_id,
            status=status,
            source_value=source_value,
            target_value=target_value,
            source_enabled=source_enabled,
            target_enabled=target_enabled,
            draft=draft
        )
