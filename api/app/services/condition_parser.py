"""
Condition Parser Service for parsing rule conditions from GrowthBook feature data.
This service enables filtering flags by rule attributes and values.
"""

import logging
import json
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ConditionParser:
    """Parse and extract conditions from GrowthBook rule data."""

    @staticmethod
    def parse_condition_string(condition: str) -> Dict[str, Any]:
        """
        Parse a condition string in format 'attribute=value' or 'attribute:operator:value'.
        
        Examples:
            'userId=123' -> {'attribute': 'userId', 'operator': '=', 'value': '123'}
            'country:IN' -> {'attribute': 'country', 'operator': ':', 'value': 'IN'}
            'age>18' -> {'attribute': 'age', 'operator': '>', 'value': '18'}
        
        Args:
            condition: Condition string to parse
            
        Returns:
            Dictionary with attribute, operator, and value
        """
        if not condition:
            return {}
        
        # Try different operators in order of precedence
        operators = ['>=', '<=', '!=', '>', '<', '=', ':']
        
        for op in operators:
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) == 2:
                    return {
                        'attribute': parts[0].strip(),
                        'operator': op,
                        'value': parts[1].strip()
                    }
        
        # If no operator found, treat as simple attribute match
        return {
            'attribute': condition.strip(),
            'operator': '=',
            'value': ''
        }

    @staticmethod
    def extract_conditions_from_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract conditions from GrowthBook rule data.
        
        GrowthBook rules can have conditions in various formats:
        - Simple conditions: {'condition': {'userId': '123'}}
        - Complex conditions: {'conditions': [{'attribute': 'userId', 'operator': '=', 'value': '123'}]}
        - Inline conditions: {'userId': '123'}
        
        Args:
            rules: List of rule dictionaries from GrowthBook
            
        Returns:
            List of extracted condition dictionaries
        """
        conditions = []
        
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            
            # logger.info(f"Processing rule: {json.dumps(rule, indent=2)}")
            
            # Try to extract conditions from different possible locations
            condition_data = rule.get('condition') or rule.get('conditions')
            
            if condition_data:
                # logger.info(f"Found condition_data: {json.dumps(condition_data, indent=2)}")
                
                # Handle case where condition_data is a JSON string
                if isinstance(condition_data, str):
                    try:
                        condition_data = json.loads(condition_data)
                        # logger.info(f"Parsed condition_data from JSON string: {json.dumps(condition_data, indent=2)}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse condition_data as JSON: {e}")
                        continue
                
                if isinstance(condition_data, dict):
                    # Simple condition format like {'id': '1230'}
                    for attr, value in condition_data.items():
                        conditions.append({
                            'attribute': attr,
                            'operator': '=',
                            'value': str(value),
                            'rule_id': rule.get('id')
                        })
                        # logger.info(f"Extracted condition: {attr}={value}")
                elif isinstance(condition_data, list):
                    # Array of condition objects
                    for cond in condition_data:
                        if isinstance(cond, dict):
                            conditions.append({
                                'attribute': cond.get('attribute', ''),
                                'operator': cond.get('operator', '='),
                                'value': str(cond.get('value', '')),
                                'rule_id': rule.get('id')
                            })
                            # logger.info(f"Extracted condition from array: {cond}")
            
            # Also check for inline conditions in the rule itself
            # Handle case where condition might be nested deeper
            for key, value in rule.items():
                if key not in ['id', 'description', 'environments', 'allEnvironments', 'condition', 'conditions']:
                    # Treat other keys as potential condition attributes
                    conditions.append({
                        'attribute': key,
                        'operator': '=',
                        'value': str(value),
                        'rule_id': rule.get('id')
                    })
                    # logger.info(f"Extracted inline condition: {key}={value}")
        
        # logger.info(f"Total extracted conditions: {len(conditions)}")
        return conditions

    @staticmethod
    def matches_condition(condition: Dict[str, Any], rule_conditions: List[Dict[str, Any]]) -> bool:
        """
        Check if a parsed condition matches any of the rule conditions.
        
        Args:
            condition: Parsed condition dictionary (attribute, operator, value)
            rule_conditions: List of extracted rule conditions
            
        Returns:
            True if condition matches, False otherwise
        """
        attr = condition.get('attribute', '').lower()
        op = condition.get('operator', '=')
        value = condition.get('value', '').lower()
        
        for rule_cond in rule_conditions:
            rule_attr = rule_cond.get('attribute', '').lower()
            rule_op = rule_cond.get('operator', '=')
            rule_value = rule_cond.get('value', '').lower()
            
            # Match attribute and operator
            if attr == rule_attr and op == rule_op:
                # For equality, check if values match (case-insensitive)
                if op in ['=', ':']:
                    if value == rule_value:
                        return True
                # For other operators, do simple string comparison
                else:
                    if value == rule_value:
                        return True
        
        return False

    @staticmethod
    def filter_flags_by_condition(flags: List[Dict[str, Any]], condition_string: str) -> List[Dict[str, Any]]:
        """
        Filter flags based on a condition string.
        
        Args:
            flags: List of flag dictionaries with rules data
            condition_string: Condition string (e.g., 'userId=123')
            
        Returns:
            Filtered list of flags that match the condition
        """
        if not condition_string or not flags:
            return flags
        
        parsed_condition = ConditionParser.parse_condition_string(condition_string)
        
        if not parsed_condition or not parsed_condition.get('attribute'):
            return flags
        
        filtered_flags = []
        
        for flag in flags:
            rules = flag.get('rules', [])
            if not rules:
                continue
            
            # Extract conditions from rules
            rule_conditions = ConditionParser.extract_conditions_from_rules(rules)
            
            # Check if any rule condition matches
            if ConditionParser.matches_condition(parsed_condition, rule_conditions):
                filtered_flags.append(flag)
        
        return filtered_flags
