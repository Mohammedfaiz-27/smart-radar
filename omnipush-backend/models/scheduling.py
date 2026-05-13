from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from uuid import UUID
from enum import Enum

from .base import BaseResponse
from .content import Platform, PostStatus


class CalendarView(str, Enum):
    MONTH = "month"
    WEEK = "week"
    DAY = "day"


class PublishStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


# Request Models
class BulkScheduleRequest(BaseModel):
    # This would typically be handled as multipart/form-data
    # but we define the expected CSV structure here
    pass


class PublishPostRequest(BaseModel):
    platforms: Optional[List[Platform]] = None


class RevokePostRequest(BaseModel):
    platforms: List[Platform]


# Response Models
class CalendarEvent(BaseModel):
    post_id: UUID
    title: str
    content: str
    scheduled_at: datetime
    platforms: List[Platform]
    status: PostStatus
    created_by: UUID


class CalendarSummary(BaseModel):
    total_posts: int
    published: int
    scheduled: int
    failed: int


class GetCalendarResponse(BaseResponse):
    events: List[CalendarEvent]
    summary: CalendarSummary


class BulkImportError(BaseModel):
    row: int
    error: str


class BulkScheduleResponse(BaseResponse):
    imported: int
    failed: int
    errors: List[BulkImportError]
    job_id: UUID


class PlatformPublishResult(BaseModel):
    platform: Platform
    status: PublishStatus
    platform_post_id: Optional[str] = None
    published_at: Optional[datetime] = None
    error: Optional[str] = None


class PublishPostResponse(BaseResponse):
    post_id: UUID
    status: str  # "publishing"
    platforms: List[PlatformPublishResult]


class PlatformRevokeResult(BaseModel):
    platform: Platform
    status: PublishStatus
    deleted_at: Optional[datetime] = None
    error: Optional[str] = None


class RevokePostResponse(BaseResponse):
    post_id: UUID
    revocation_results: List[PlatformRevokeResult]