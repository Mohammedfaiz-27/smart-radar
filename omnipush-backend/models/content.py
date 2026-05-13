from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum

from .base import BaseResponse, PaginatedResponse


class NewsItem(BaseModel):
    """Simplified NewsItem model for post relationships"""
    id: UUID
    title: str
    content: str
    source: str
    source_url: Optional[str] = None
    url: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    is_approved: bool = False
    published_at: Optional[datetime] = None
    fetched_at: datetime
    moderation_status: Optional[str] = None
    processed_content: Optional[str] = None
    generated_image_url: Optional[str] = None
    published_channels: Optional[List[str]] = None
    created_at: datetime


class PostStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    REJECTED = "rejected"


class Platform(str, Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    PINTEREST = "pinterest"
    WHATSAPP = "whatsapp"


class ApprovalAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


# Request Models
class PostContent(BaseModel):
    text: Optional[str] = ""
    media_ids: Optional[List[str]] = []
    mode: Optional[str] = None  # "text", "image", "text_with_images", "link"
    link: Optional[str] = None  # Link URL for link mode


class ChannelCustomization(BaseModel):
    platform: Platform
    account_id: UUID
    customizations: Dict[str, Any] = {}


class CreatePostRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: PostContent
    channels: List[ChannelCustomization]
    scheduled_at: Optional[datetime] = None
    enhance_with_ai: Optional[bool] = False
    channel_group_id: Optional[str] = None  # Deprecated: use channel_group_ids
    channel_group_ids: Optional[List[str]] = None  # Support multiple channel groups
    headline: Optional[str] = None  # User-provided headline (30-50 chars) for newscard modes


class UpdatePostRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[PostContent] = None
    channels: Optional[List[ChannelCustomization]] = None
    scheduled_at: Optional[datetime] = None
    enhance_with_ai: Optional[bool] = False


class SubmitApprovalRequest(BaseModel):
    message: Optional[str] = None


class ReviewPostRequest(BaseModel):
    action: ApprovalAction
    feedback: Optional[str] = None


# Response Models
class PostChannel(BaseModel):
    platform: Platform
    account_id: UUID
    customizations: Dict[str, Any] = {}


class Post(BaseModel):
    id: UUID
    title: str
    content: PostContent
    channels: List[PostChannel]
    status: PostStatus
    created_by: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    preview_html: Optional[str] = None
    news_card_url: Optional[str] = None
    news_item_id: Optional[UUID] = None
    news_item: Optional[NewsItem] = None
    keywords: Optional[List[str]] = []
    image_search_caption: Optional[str] = None
    publish_results: Optional[dict] = None


class ListPostsResponse(PaginatedResponse):
    posts: List[Post]


class CreatePostResponse(BaseResponse):
    id: UUID
    title: str
    status: PostStatus
    created_by: UUID
    created_at: datetime
    keywords: Optional[List[str]] = []
    image_search_caption: Optional[str] = None


class UpdatePostResponse(BaseResponse):
    id: UUID
    title: str
    updated_at: datetime


class DeletePostResponse(BaseResponse):
    message: str = "Post deleted successfully"


class SubmitApprovalResponse(BaseResponse):
    status: PostStatus
    submitted_at: datetime
    approvers: List[UUID]


class ReviewPostResponse(BaseResponse):
    status: PostStatus
    reviewed_by: UUID
    reviewed_at: datetime


class EnhancePostRequest(BaseModel):
    text: str = Field(min_length=1)
    

class EnhancePostResponse(BaseResponse):
    enhanced_text: str
    

class PreviewPostRequest(BaseModel):
    title: str
    content: str
    

class PreviewPostResponse(BaseResponse):
    html: str
    

class NewsCardRequest(BaseModel):
    html: str
    

class NewsCardResponse(BaseResponse):
    image_url: str
    filename: str
    

class PublishPostRequest(BaseModel):
    post_id: UUID
    channels: Optional[List[str]] = None
    account_ids: Optional[List[str]] = None
    

class PublishPostResponse(BaseResponse):
    published_channels: List[Dict[str, Any]]
    

class SchedulePostRequest(BaseModel):
    post_id: UUID
    scheduled_at: datetime
    

class SchedulePostResponse(BaseResponse):
    scheduled_at: datetime