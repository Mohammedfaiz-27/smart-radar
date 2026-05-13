from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum

from models.base import BaseResponse, PaginatedResponse


class ModerationStatus(str, Enum):
    """Moderation status enum"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"


class NewsItem(BaseModel):
    """News item model"""
    id: UUID
    pipeline_id: Optional[UUID] = None  # Optional for non-pipeline sources
    title: str = Field(max_length=500)
    content: str
    source_name: Optional[str] = None  # Display name for the source
    external_source: Optional[str] = None  # Normalized identifier (newsit, pipeline, slack, etc.)
    source_url: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    is_approved: Optional[bool] = False
    tenant_id: Optional[str] = None
    published_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    moderation_status: ModerationStatus = ModerationStatus.PENDING
    moderation_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    moderation_flags: Optional[List[str]] = []
    moderation_reason: Optional[str] = None
    processed_content: Optional[str] = None
    generated_image_url: Optional[str] = None
    images: Optional[Dict[str, Any]] = None
    published_channels: Optional[List[str]] = []
    moderated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class CreateNewsItemRequest(BaseModel):
    """Request model for creating a news item"""
    pipeline_id: Optional[str] = Field(None, description="Pipeline ID this news item belongs to (optional)")
    title: str = Field(max_length=500, description="News item title")
    content: str = Field(description="News item content")
    source_name: Optional[str] = Field(None, description="Source display name")
    external_source: Optional[str] = Field(None, description="Source identifier (newsit, pipeline, slack, etc.)")
    source_url: Optional[str] = Field(None, description="URL of the source")
    category: Optional[str] = Field(None, description="News category")
    published_at: Optional[datetime] = Field(None, description="When the news was originally published")
    tenant_id: Optional[str] = Field(None, description="Tenant ID")
    moderation_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Initial moderation score")
    generated_image_url: Optional[str] = Field(None, description="Generated image URL")


class UpdateNewsItemRequest(BaseModel):
    """Request model for updating a news item"""
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    source_name: Optional[str] = None
    external_source: Optional[str] = None
    source_url: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    processed_content: Optional[str] = None
    generated_image_url: Optional[str] = None


class UpdateModerationRequest(BaseModel):
    """Request model for updating moderation status"""
    moderation_status: ModerationStatus
    moderation_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    moderation_flags: Optional[List[str]] = []
    moderation_reason: Optional[str] = Field(None, description="Reason for rejection or flagging")
    processed_content: Optional[str] = None
    is_approved: Optional[bool] = None


class UpdatePublishedChannelsRequest(BaseModel):
    """Request model for updating published channels"""
    channels: List[str] = Field(description="List of channels where item was published")


class BulkModerationRequest(BaseModel):
    """Request model for bulk moderation updates"""
    news_item_ids: List[str] = Field(description="List of news item IDs to update")
    moderation_status: ModerationStatus
    is_approved: Optional[bool] = None


class NewsItemsStatsResponse(BaseResponse):
    """Response model for news items statistics"""
    stats: Dict[str, int] = Field(description="Statistics including total, pending, approved, rejected, published counts")


class CreateNewsItemResponse(BaseResponse):
    """Response model for creating a news item"""
    news_item: NewsItem


class UpdateNewsItemResponse(BaseResponse):
    """Response model for updating a news item"""
    news_item: NewsItem


class DeleteNewsItemResponse(BaseResponse):
    """Response model for deleting a news item"""
    success: bool
    deleted_id: str


class ListNewsItemsResponse(PaginatedResponse):
    """Response model for listing news items"""
    items: List[NewsItem]


class SearchNewsItemsResponse(BaseResponse):
    """Response model for searching news items"""
    items: List[NewsItem]
    total_results: int


class BulkModerationResponse(BaseResponse):
    """Response model for bulk moderation updates"""
    updated_count: int
    total_requested: int
    updated_ids: List[str]


class NewsItemsFilters(BaseModel):
    """Filters for news items queries"""
    pipeline_id: Optional[str] = None
    status: Optional[str] = None
    moderation_status: Optional[ModerationStatus] = None
    category: Optional[str] = None
    is_approved: Optional[bool] = None
    unpublished_only: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None