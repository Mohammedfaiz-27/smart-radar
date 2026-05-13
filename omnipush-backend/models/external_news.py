"""
Pydantic models for External News System
Supports generic external news sources (NewsIt, RSS, etc.)
"""

from pydantic import BaseModel, Field, UUID4
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ApprovalStatus(str, Enum):
    """Approval status for external news items"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PublicationStatus(str, Enum):
    """Publication status for external news publications"""
    PENDING = "pending"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


# =====================================================
# NewsIt API Response Models
# =====================================================

class NewsItContent(BaseModel):
    """Content for a single language"""
    web_content: Optional[str] = None
    title: Optional[str] = None
    headlines: Optional[str] = None
    images: Optional[Any] = None
    ai_summary: Optional[str] = None


class NewsItCategory(BaseModel):
    """Category information with multilingual support"""
    name: Optional[str] = None
    multilingual_names: Optional[Dict[str, str]] = None
    multilingual_descriptions: Optional[Dict[str, str]] = None


class NewsItTopic(BaseModel):
    """Topic information with multilingual support"""
    name: Optional[str] = None
    description: Optional[str] = None
    multilingual_names: Optional[Dict[str, str]] = None
    multilingual_descriptions: Optional[Dict[str, str]] = None
    image: Optional[str] = None


class NewsItCity(BaseModel):
    """City information with multilingual support"""
    name: Optional[str] = None
    multilingual_names: Optional[Dict[str, str]] = None


class NewsItImages(BaseModel):
    """Image URLs from NewsIt"""
    original_key: Optional[str] = None
    original_url: Optional[str] = None
    thumbnail_key: Optional[str] = None
    thumbnail_url: Optional[str] = None
    low_res_key: Optional[str] = None
    low_res_url: Optional[str] = None


class NewsItAPIData(BaseModel):
    """NewsIt API response data structure"""
    id: str
    category: Optional[NewsItCategory] = None
    city: Optional[NewsItCity] = None
    content: Optional[Dict[str, NewsItContent]] = None  # { "en": {...}, "ta": {...} }
    topics: Optional[List[NewsItTopic]] = None
    is_breaking: bool = False
    images: Optional[NewsItImages] = None
    tags: Optional[Any] = None


class NewsItAPIResponse(BaseModel):
    """Complete NewsIt API response"""
    status: int
    message: str
    data: NewsItAPIData


# =====================================================
# SQS Message Models
# =====================================================

class NewsItSQSMessage(BaseModel):
    """SQS message payload for NewsIt"""
    news_id: str
    tenant_id: Optional[UUID4] = "813bb51b-be36-4bdc-ba77-b6530cb741ca"  # Optional tenant routing
    source: str = "newsit"
    metadata: Optional[Dict[str, Any]] = None


class SlackAttachment(BaseModel):
    """Slack message attachment"""
    from_url: Optional[str] = None
    image_url: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    image_bytes: Optional[int] = None
    service_icon: Optional[str] = None
    id: Optional[int] = None
    original_url: Optional[str] = None
    fallback: Optional[str] = None
    text: Optional[str] = None
    pretext: Optional[str] = None
    title: Optional[str] = None
    title_link: Optional[str] = None
    service_name: Optional[str] = None
    mrkdwn_in: Optional[List[str]] = None
    scraped_content: Optional[str] = None
    s3_image_key: Optional[str] = None
    s3_image_url: Optional[str] = None


class SlackSQSMessage(BaseModel):
    """SQS message payload for Slack bot messages"""
    subtype: Optional[str] = None
    text: Optional[str] = None
    username: Optional[str] = None
    icons: Optional[Dict[str, str]] = None
    attachments: Optional[List[SlackAttachment]] = None
    type: Optional[str] = None
    ts: Optional[str] = None
    bot_id: Optional[str] = None
    channel_id: Optional[str] = None
    channel_name: Optional[str] = None
    _id: str  # MongoDB ID from the message
    tenant_id: Optional[UUID4] = "813bb51b-be36-4bdc-ba77-b6530cb741ca"  # Optional tenant routing


# =====================================================
# Database Models
# =====================================================

class ExternalNewsItemBase(BaseModel):
    """Base model for external news item"""
    external_source: str
    external_id: str
    title: str
    content: str
    multilingual_data: Optional[Dict[str, Any]] = None
    category: Optional[str] = None
    category_data: Optional[Dict[str, Any]] = None
    city_data: Optional[Dict[str, Any]] = None
    topics: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    images: Optional[Dict[str, Any]] = None
    media_urls: Optional[List[str]] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    is_breaking: bool = False


class ExternalNewsItemCreate(ExternalNewsItemBase):
    """Model for creating external news item"""
    tenant_id: UUID4
    sqs_message_id: Optional[str] = None


class ExternalNewsItem(ExternalNewsItemBase):
    """Complete external news item model"""
    id: UUID4
    tenant_id: UUID4
    sqs_message_id: Optional[str] = None
    approval_status: ApprovalStatus
    approved_by: Optional[UUID4] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[UUID4] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    fetched_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ExternalNewsPublicationBase(BaseModel):
    """Base model for external news publication"""
    channel_group_id: UUID4
    selected_language: Optional[str] = "en"
    customized_title: Optional[str] = None
    customized_content: Optional[str] = None


class ExternalNewsPublicationCreate(ExternalNewsPublicationBase):
    """Model for creating external news publication"""
    external_news_id: UUID4
    tenant_id: UUID4
    initiated_by: UUID4


class ExternalNewsPublication(ExternalNewsPublicationBase):
    """Complete external news publication model"""
    id: UUID4
    external_news_id: UUID4
    tenant_id: UUID4
    post_id: Optional[UUID4] = None
    status: PublicationStatus
    initiated_by: UUID4
    initiated_at: datetime
    completed_at: Optional[datetime] = None
    publish_results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# =====================================================
# API Request/Response Models
# =====================================================

class ListExternalNewsResponse(BaseModel):
    """Response for listing external news items"""
    items: List[ExternalNewsItem]
    pagination: Dict[str, Any]


class ExternalNewsDetailResponse(BaseModel):
    """Detailed response for single external news item"""
    news_item: ExternalNewsItem
    publications: List[ExternalNewsPublication] = []


class RejectNewsRequest(BaseModel):
    """Request model for rejecting news"""
    rejection_reason: str = Field(..., min_length=1, max_length=500)


class PublishToChannelGroupsRequest(BaseModel):
    """Request model for publishing to channel groups"""
    channel_group_ids: List[UUID4] = Field(..., min_items=1)
    selected_language: str = "en"
    customized_title: Optional[str] = None
    customized_content: Optional[str] = None
    create_drafts: bool = True  # If True, creates drafts for review; if False, publishes directly


class PublishNewsResponse(BaseModel):
    """Response model for publish request"""
    success: bool
    message: str
    publications: List[ExternalNewsPublication]
    errors: Optional[List[str]] = None


class ProcessingResult(BaseModel):
    """Result of processing a news item from SQS"""
    success: bool
    news_item_id: Optional[UUID4] = None
    error_message: Optional[str] = None
    external_id: Optional[str] = None
    is_duplicate: bool = False
