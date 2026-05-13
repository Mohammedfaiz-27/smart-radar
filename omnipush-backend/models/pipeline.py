from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum

from .base import BaseResponse, PaginatedResponse


class PipelineStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    ERROR = "error"


class ProcessingStep(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    BOTH = "both"


class NewsSource(str, Enum):
    RSS = "rss"
    API = "api"
    WEBHOOK = "webhook"


class ModerationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"


class ChannelType(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


# Request Models
class ChannelConfig(BaseModel):
    name: str
    type: ChannelType
    platform: str
    config: Dict[str, Any] = {}


class PipelineConfig(BaseModel):
    input_channels: List[ChannelConfig] = []
    output_channels: List[ChannelConfig] = []
    processing_steps: List[ProcessingStep] = []
    moderation_enabled: bool = True
    auto_publish: bool = False
    schedule_config: Optional[Dict[str, Any]] = None

    model_config = {"extra": "ignore"}


class CreatePipelineRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    config: PipelineConfig
    status: PipelineStatus = PipelineStatus.ACTIVE


class UpdatePipelineRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    config: Optional[PipelineConfig] = None
    status: Optional[PipelineStatus] = None


class FetchNewsRequest(BaseModel):
    pipeline_id: UUID
    sources: Optional[List[str]] = None


class ModerateContentRequest(BaseModel):
    content: str
    source: str
    pipeline_id: UUID


# Response Models
class Pipeline(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    config: PipelineConfig
    status: PipelineStatus
    created_by: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_run: Optional[datetime] = None
    total_processed: int = 0


class NewsItem(BaseModel):
    id: UUID
    pipeline_id: UUID
    title: str
    content: str
    source: str
    source_url: Optional[str] = None
    published_at: Optional[datetime] = None
    fetched_at: datetime
    moderation_status: ModerationStatus = ModerationStatus.PENDING
    moderation_score: Optional[float] = None
    moderation_flags: Optional[List[str]] = None
    processed_content: Optional[str] = None
    generated_image_url: Optional[str] = None
    published_channels: Optional[List[str]] = None


class PipelineRun(BaseModel):
    id: UUID
    pipeline_id: UUID
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    items_processed: int = 0
    items_published: int = 0
    errors: Optional[List[str]] = None


class ListPipelinesResponse(PaginatedResponse):
    pipelines: List[Pipeline]


class CreatePipelineResponse(BaseResponse):
    id: UUID
    name: str
    status: PipelineStatus
    created_at: datetime


class UpdatePipelineResponse(BaseResponse):
    id: UUID
    name: str
    updated_at: datetime


class DeletePipelineResponse(BaseResponse):
    message: str = "Pipeline deleted successfully"


class ListNewsItemsResponse(PaginatedResponse):
    items: List[NewsItem]


class FetchNewsResponse(BaseResponse):
    pipeline_id: UUID
    items_fetched: int
    items_moderated: int
    items_processed: int
    run_id: UUID


class ModerateContentResponse(BaseResponse):
    status: ModerationStatus
    score: float
    flags: List[str]
    approved: bool


class PipelineStatsResponse(BaseResponse):
    pipeline_id: UUID
    total_items: int
    approved_items: int
    rejected_items: int
    published_items: int
    last_run: Optional[datetime] = None
    success_rate: float