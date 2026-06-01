from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class FlagBase(BaseModel):
    key: str
    market_id: int


class FlagCreate(FlagBase):
    description: Optional[str] = None
    default_value: Optional[str] = None


class FlagUpdate(BaseModel):
    key: Optional[str] = None
    growthbook_feature_id: Optional[str] = None


class FlagResponse(BaseModel):
    id: int
    key: str
    market_id: int
    growthbook_feature_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FlagImportRequest(BaseModel):
    growthbook_feature_id: str
    market_id: int
    key: Optional[str] = None  # If not provided, use growthbook_feature_id


class FlagImportResponse(BaseModel):
    success: bool
    message: str
    flag: Optional[FlagResponse] = None
    error: Optional[str] = None


class FeatureData(BaseModel):
    """Schema for GrowthBook feature data."""
    id: str
    key: str
    description: Optional[str] = None
    defaultValue: Optional[dict] = None


class ImportAllFlagsRequest(BaseModel):
    """Request to import all flags from GrowthBook for a market."""
    market_id: int
    dry_run: bool = False


class ImportAllFlagsResponse(BaseModel):
    """Response for importing all flags."""
    success: bool
    message: str
    imported_count: int = 0
    updated_count: int = 0
    deleted_count: int = 0
    failed_count: int = 0
    flags: list[FlagResponse] = []
    errors: list[str] = []
    to_add: list[dict] = []
    to_update: list[dict] = []
    to_delete: list[dict] = []
    dry_run: bool = False


class UpdateFlagValueRequest(BaseModel):
    """Request to update a flag's value in GrowthBook for a specific environment."""
    environment: str
    enabled: bool
    default_value: str = "false"


class UpdateFlagValueResponse(BaseModel):
    """Response for updating a flag's value in GrowthBook."""
    success: bool
    message: str
    error: Optional[str] = None
