import logging
from typing import List, Dict, Any
from app.services.growthbook_client import GrowthBookClient
from app.services.comparison_service import ComparisonService
from app.schemas.promotion import PromotionStatus, FlagPromotionResult

logger = logging.getLogger(__name__)


class PromotionService:
    """Service for promoting flags between environments."""
    
    def __init__(self):
        self.gb_client = GrowthBookClient()
        self.comparison_service = ComparisonService()
    
    async def promote_flags(
        self,
        source_environment: str,
        target_environment: str,
        market_id: int,
        flag_keys: List[str] = None
    ) -> List[FlagPromotionResult]:
        """
        Promote flags from source to target environment.
        
        Args:
            source_environment: Source environment name (e.g., "dev")
            target_environment: Target environment name (e.g., "production")
            market_id: Market ID
            flag_keys: Optional list of specific flag keys to promote. If None, promotes all flags.
            
        Returns:
            List of FlagPromotionResult with promotion results
        """
        try:
            # Get comparison results to identify flags to promote
            logger.info(f"Getting comparison for {source_environment} -> {target_environment}")
            comparisons = await self.comparison_service.compare_environments(
                source_environment,
                target_environment
            )
            
            # Filter flags based on flag_keys if provided
            if flag_keys:
                comparisons = [c for c in comparisons if c.key in flag_keys]
            
            results = []
            
            for comparison in comparisons:
                # Only promote flags that need promotion (different or missing in target)
                if comparison.status in ["different", "missing_in_target"]:
                    # Skip draft flags - they may not have environment configs
                    if comparison.draft:
                        results.append(FlagPromotionResult(
                            key=comparison.key,
                            growthbook_feature_id=comparison.growthbook_feature_id,
                            status=PromotionStatus.SKIPPED,
                            message="Flag is in draft status, skipping promotion"
                        ))
                        continue
                    
                    result = await self._promote_single_flag(
                        comparison.key,
                        comparison.growthbook_feature_id,
                        source_environment,
                        target_environment
                    )
                    results.append(result)
                else:
                    # Skip flags that are in sync or missing in source
                    results.append(FlagPromotionResult(
                        key=comparison.key,
                        growthbook_feature_id=comparison.growthbook_feature_id,
                        status=PromotionStatus.SKIPPED,
                        message=f"Flag is {comparison.status}, skipping promotion"
                    ))
            
            logger.info(f"Promotion complete: {len(results)} flags processed")
            return results
            
        except Exception as e:
            logger.error(f"Error promoting flags: {e}")
            raise
    
    async def _promote_single_flag(
        self,
        key: str,
        feature_id: str,
        source_environment: str,
        target_environment: str
    ) -> FlagPromotionResult:
        """
        Promote a single flag from source to target environment.
        
        Args:
            key: Flag key
            feature_id: GrowthBook feature ID
            source_environment: Source environment name
            target_environment: Target environment name
            
        Returns:
            FlagPromotionResult with promotion result
        """
        try:
            # Fetch the feature from GrowthBook
            logger.info(f"Fetching feature {feature_id} from GrowthBook")
            response = await self.gb_client.get_feature(feature_id)
            
            logger.info(f"Full feature data response: {response}")
            
            # Unwrap feature from response
            feature_data = response.get("feature", {})
            
            # Get source environment config
            environments = feature_data.get("environments", {})
            source_config = environments.get(source_environment)
            
            logger.info(f"Feature {feature_id} environments: {list(environments.keys())}")
            logger.info(f"Source environment: {source_environment}, config exists: {source_config is not None}")
            
            if not source_config:
                logger.info(f"Flag {key} not configured in source environment {source_environment}, skipping promotion")
                return FlagPromotionResult(
                    key=key,
                    growthbook_feature_id=feature_id,
                    status=PromotionStatus.SKIPPED,
                    message=f"Flag not configured in source environment {source_environment}, skipping promotion"
                )
            
            # Extract rules for source environment
            all_rules = feature_data.get("rules", [])
            source_rules = self._filter_rules_by_environment(all_rules, source_environment)
            
            # Copy rules to target environment
            if source_rules:
                logger.info(f"Copying {len(source_rules)} rules from {source_environment} to {target_environment}")
                await self._copy_rules_to_environment(feature_id, source_rules, target_environment)
            
            # Enable the feature in target environment (copy from source)
            logger.info(f"Enabling feature {feature_id} in target environment {target_environment}")
            
            # Use toggle endpoint to enable the feature in target environment
            await self.gb_client.toggle_feature(
                feature_id,
                {target_environment: source_config.get("enabled", True)},
                f"Promoted from {source_environment}"
            )
            
            return FlagPromotionResult(
                key=key,
                growthbook_feature_id=feature_id,
                status=PromotionStatus.SUCCESS,
                message=f"Successfully promoted {key} from {source_environment} to {target_environment}"
            )
            
        except Exception as e:
            logger.error(f"Error promoting flag {key}: {e}")
            return FlagPromotionResult(
                key=key,
                growthbook_feature_id=feature_id,
                status=PromotionStatus.FAILED,
                message=f"Failed to promote {key}",
                error=str(e)
            )
    
    def _filter_rules_by_environment(self, all_rules: List[Dict[str, Any]], environment: str) -> List[Dict[str, Any]]:
        """
        Filter rules to only include those that apply to the specified environment.
        
        Args:
            all_rules: All rules from the feature
            environment: Target environment name
            
        Returns:
            Filtered list of rules that apply to the environment
        """
        filtered_rules = []
        for rule in all_rules:
            rule_envs = rule.get("environments", [])
            # Include rule if it has no environment restriction or applies to target environment
            if not rule_envs or environment in rule_envs or rule.get("allEnvironments", False):
                filtered_rules.append(rule)
        return filtered_rules
    
    async def _copy_rules_to_environment(
        self,
        feature_id: str,
        rules: List[Dict[str, Any]],
        target_environment: str
    ):
        """
        Copy rules to target environment, preserving order and structure.
        
        Args:
            feature_id: GrowthBook feature ID
            rules: Rules to copy
            target_environment: Target environment name
        """
        for rule in rules:
            # Update rule to apply to target environment
            updated_rule = rule.copy()
            updated_rule["environments"] = [target_environment]
            
            # Add the rule to the target environment
            await self.gb_client.add_rule(feature_id, target_environment, updated_rule)
