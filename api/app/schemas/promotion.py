from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum


class PromotionStatus(str, Enum):
    """Status of a flag promotion."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class FlagPromotionResult(BaseModel):
    """Result of promoting a single flag."""
    key: str
    growthbook_feature_id: str
    status: PromotionStatus
    message: str
    error: Optional[str] = None


class PromotionRequest(BaseModel):
    """Request to promote flags between environments."""
    source_environment: str
    target_environment: str
    market_id: int
    flag_keys: Optional[List[str]] = None  # If None, promote all flags from comparison


class PromotionResponse(BaseModel):
    """Response for flag promotion."""
    success: bool
    message: str
    total_flags: int
    successful_count: int
    failed_count: int
    skipped_count: int
    results: List[FlagPromotionResult]
