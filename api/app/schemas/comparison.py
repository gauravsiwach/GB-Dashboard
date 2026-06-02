from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum


class ComparisonStatus(str, Enum):
    """Status of a flag comparison."""
    IN_SYNC = "in_sync"
    MISSING_IN_TARGET = "missing_in_target"
    MISSING_IN_SOURCE = "missing_in_source"
    DIFFERENT = "different"


class FlagComparison(BaseModel):
    """Comparison result for a single flag."""
    key: str
    growthbook_feature_id: str
    status: ComparisonStatus
    source_value: Optional[str] = None
    target_value: Optional[str] = None
    source_enabled: Optional[bool] = None
    target_enabled: Optional[bool] = None
    draft: bool = False
    source_rules: Optional[List[Dict[str, Any]]] = None
    target_rules: Optional[List[Dict[str, Any]]] = None
    rules_different: bool = False


class ComparisonRequest(BaseModel):
    """Request to compare flags between environments."""
    source_environment: str
    target_environment: str
    market_id: int


class ComparisonResponse(BaseModel):
    """Response from flag comparison."""
    success: bool
    message: str
    source_environment: str
    target_environment: str
    comparisons: List[FlagComparison]
    total_flags: int
    in_sync_count: int
    different_count: int
    missing_in_target_count: int
    missing_in_source_count: int
