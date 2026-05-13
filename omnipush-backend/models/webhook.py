from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel, HttpUrl
from uuid import UUID
from enum import Enum

from .base import BaseResponse
from .content import Platform


class WebhookEvent(str, Enum):
    POST_PUBLISHED = "post.published"
    POST_FAILED = "post.failed"
    APPROVAL_REQUIRED = "approval.required"
    USER_INVITED = "user.invited"
    SUBSCRIPTION_CHANGED = "subscription.changed"


# Request Models
class RegisterWebhookRequest(BaseModel):
    url: HttpUrl
    events: List[WebhookEvent]
    secret: str


# Response Models
class Webhook(BaseModel):
    id: UUID
    url: HttpUrl
    events: List[WebhookEvent]
    created_at: datetime


class RegisterWebhookResponse(BaseResponse):
    id: UUID
    url: HttpUrl
    events: List[WebhookEvent]
    created_at: datetime


# Webhook Event Payloads
class PlatformPublishInfo(BaseModel):
    platform: Platform
    platform_post_id: str
    published_at: datetime


class PostPublishedEventData(BaseModel):
    post_id: UUID
    tenant_id: UUID
    platforms: List[PlatformPublishInfo]


class WebhookEventPayload(BaseModel):
    event: WebhookEvent
    data: Dict[str, Any]
    timestamp: datetime