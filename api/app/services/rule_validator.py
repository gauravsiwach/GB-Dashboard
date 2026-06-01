import json
import logging
from typing import Dict, Any, List, Optional
from app.services.growthbook_error import GrowthBookError

logger = logging.getLogger(__name__)


class RuleValidator:
    """Service for validating feature flag rule structures and conditions."""
    
    # Valid operators for rule conditions
    VALID_OPERATORS = {
        "eq", "ne", "gt", "lt", "gte", "lte", 
        "in", "notIn", "contains", "notContains",
        "startsWith", "endsWith"
    }
    
    # Common attribute names that are typically valid
    COMMON_ATTRIBUTES = {
        "country", "email", "userId", "id", "role", 
        "plan", "version", "environment", "locale"
    }
    
    @classmethod
    def validate_rule(cls, rule_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate a rule's JSON structure and conditions.
        
        Args:
            rule_data: Dictionary containing rule configuration
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if rule_data is a dictionary
            if not isinstance(rule_data, dict):
                return False, "Rule must be a JSON object"
            
            # Validate conditions if present
            if "conditions" in rule_data:
                conditions = rule_data["conditions"]
                if not isinstance(conditions, list):
                    return False, "Conditions must be an array"
                
                for i, condition in enumerate(conditions):
                    is_valid, error = cls._validate_condition(condition)
                    if not is_valid:
                        return False, f"Condition {i}: {error}"
            
            # Validate rollout percentage if present
            if "rolloutPercentage" in rule_data:
                rollout = rule_data["rolloutPercentage"]
                if not isinstance(rollout, (int, float)):
                    return False, "rolloutPercentage must be a number"
                if not (0 <= rollout <= 100):
                    return False, "rolloutPercentage must be between 0 and 100"
            
            # Validate value if present
            if "value" in rule_data:
                # Value can be any JSON type, so we just check it's present
                pass
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating rule: {str(e)}")
            return False, f"Validation error: {str(e)}"
    
    @classmethod
    def _validate_condition(cls, condition: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate a single condition within a rule.
        
        Args:
            condition: Dictionary containing condition configuration
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        required_fields = ["attribute", "operator", "value"]
        for field in required_fields:
            if field not in condition:
                return False, f"Missing required field: {field}"
        
        # Validate attribute
        attribute = condition["attribute"]
        if not isinstance(attribute, str):
            return False, "Attribute must be a string"
        if not attribute:
            return False, "Attribute cannot be empty"
        
        # Validate operator
        operator = condition["operator"]
        if not isinstance(operator, str):
            return False, "Operator must be a string"
        if operator not in cls.VALID_OPERATORS:
            return False, f"Invalid operator: {operator}. Valid operators: {', '.join(sorted(cls.VALID_OPERATORS))}"
        
        # Validate value (can be any JSON type)
        value = condition["value"]
        if value is None:
            return False, "Value cannot be null"
        
        return True, None
    
    @classmethod
    def validate_rule_json(cls, rule_json: str) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate a rule JSON string and parse it.
        
        Args:
            rule_json: String containing rule configuration in JSON format
            
        Returns:
            Tuple of (is_valid, error_message, parsed_data)
        """
        try:
            # Parse JSON
            rule_data = json.loads(rule_json)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}", None
        
        # Validate structure
        is_valid, error = cls.validate_rule(rule_data)
        if not is_valid:
            return False, error, None
        
        return True, None, rule_data
