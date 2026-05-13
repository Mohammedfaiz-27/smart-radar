from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID


class BaseResponse(BaseModel):
    """Base response model for all API responses"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class ErrorDetail(BaseModel):
    """Error detail structure"""
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseResponse):
    """Standard error response format"""
    error: ErrorDetail


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int = Field(ge=1)
    limit: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class PaginatedResponse(BaseResponse):
    """Base paginated response"""
    pagination: PaginationMeta


class UsageLimits(BaseModel):
    """Usage limits for different subscription tiers"""
    users: int
    posts_per_month: int
    ai_generations_per_month: int
    storage_gb: int


class CurrentUsage(BaseModel):
    """Current usage metrics"""
    users: int
    posts_this_month: int
    ai_generations_this_month: int
    storage_used_gb: float