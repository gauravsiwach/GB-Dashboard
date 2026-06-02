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
                
                # Extract rules for source and target environments
                all_rules = feature.get("rules", [])
                source_rules = self._filter_rules_by_environment(all_rules, source_environment)
                target_rules = self._filter_rules_by_environment(all_rules, target_environment)
                
                # Determine comparison status
                comparison = self._compare_flag(
                    feature_key,
                    feature_id,
                    source_env_config,
                    target_env_config,
                    source_environment,
                    target_environment,
                    draft,
                    source_rules,
                    target_rules
                )
                
                comparisons.append(comparison)
            
            logger.info(f"Comparison complete: {len(comparisons)} flags compared")
            return comparisons
            
        except Exception as e:
            logger.error(f"Error comparing environments: {e}")
            raise
    
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
    
    def _compare_flag(
        self,
        key: str,
        feature_id: str,
        source_config: Dict[str, Any],
        target_config: Dict[str, Any],
        source_env_name: str,
        target_env_name: str,
        draft: bool = False,
        source_rules: List[Dict[str, Any]] = None,
        target_rules: List[Dict[str, Any]] = None
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
            source_rules: Rules for source environment
            target_rules: Rules for target environment
            
        Returns:
            FlagComparison with comparison result
        """
        source_enabled = source_config.get("enabled", False) if source_config else False
        target_enabled = target_config.get("enabled", False) if target_config else False
        source_value = source_config.get("defaultValue") if source_config else None
        target_value = target_config.get("defaultValue") if target_config else None
        
        # Compare rules
        rules_different = self._compare_rules(source_rules, target_rules, source_env_name, target_env_name)
        
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
        elif source_enabled == target_enabled and source_value == target_value and not rules_different:
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
            draft=draft,
            source_rules=source_rules,
            target_rules=target_rules,
            rules_different=rules_different
        )
    
    def _compare_rules(
        self,
        source_rules: List[Dict[str, Any]],
        target_rules: List[Dict[str, Any]],
        source_env_name: str,
        target_env_name: str
    ) -> bool:
        """
        Compare rules between source and target environments.
        
        Args:
            source_rules: Rules for source environment
            target_rules: Rules for target environment
            source_env_name: Source environment name
            target_env_name: Target environment name
            
        Returns:
            True if rules are different, False otherwise
        """
        if not source_rules and not target_rules:
            return False  # Both have no rules - same
        
        if not source_rules or not target_rules:
            return True  # One has rules, other doesn't - different
        
        if len(source_rules) != len(target_rules):
            return True  # Different number of rules - different
        
        # Compare each rule
        for i, (source_rule, target_rule) in enumerate(zip(source_rules, target_rules)):
            # Filter rules by environment before comparing
            source_rule_envs = source_rule.get("environments", [])
            target_rule_envs = target_rule.get("environments", [])
            
            # Check if rules apply to their respective environments
            source_applies = not source_rule_envs or source_env_name in source_rule_envs or source_rule.get("allEnvironments", False)
            target_applies = not target_rule_envs or target_env_name in target_rule_envs or target_rule.get("allEnvironments", False)
            
            # Compare key rule fields
            if (source_rule.get("type") != target_rule.get("type") or
                source_rule.get("condition") != target_rule.get("condition") or
                source_rule.get("value") != target_rule.get("value") or
                source_rule.get("enabled") != target_rule.get("enabled")):
                return True
        
        return False
