from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from uuid import UUID
from enum import Enum

from .base import BaseResponse, PaginatedResponse


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"


class AIImageStyle(str, Enum):
    PHOTOGRAPHIC = "photographic"
    DIGITAL_ART = "digital_art"
    COMIC_BOOK = "comic_book"
    FANTASY_ART = "fantasy_art"
    LINE_ART = "line_art"
    ANALOG_FILM = "analog_film"


class AIImageSize(str, Enum):
    SMALL = "512x512"
    MEDIUM = "1024x1024"
    LARGE = "1536x1536"


# Request Models
class UpdateMediaRequest(BaseModel):
    tags: Optional[List[str]] = None
    description: Optional[str] = None


class GenerateAIImageRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000)
    style: AIImageStyle = AIImageStyle.PHOTOGRAPHIC
    size: AIImageSize = AIImageSize.MEDIUM


# Response Models
class MediaMetadata(BaseModel):
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None  # for videos
    format: Optional[str] = None


class Media(BaseModel):
    id: UUID
    filename: str
    type: Optional[MediaType] = None
    size: Optional[int] = None  # bytes
    url: Optional[str] = None
    thumbnail_url: Optional[HttpUrl] = None
    metadata: Optional[MediaMetadata] = None
    # tags: List[str] = []
    # description: Optional[str] = None
    # uploaded_by: UUID
    created_at: datetime


class AIGeneratedMedia(Media):
    generation_prompt: str


class ListMediaResponse(PaginatedResponse):
    media: List[Media]


class UploadMediaResponse(BaseResponse):
    id: UUID
    filename: str
    type: MediaType
    size: Optional[int] = None
    url: HttpUrl
    thumbnail_url: Optional[HttpUrl] = None
    uploaded_by: UUID
    created_at: datetime


class GenerateAIImageResponse(BaseResponse):
    id: UUID
    filename: str
    type: MediaType
    url: HttpUrl
    generation_prompt: str
    created_at: datetime


class UpdateMediaResponse(BaseResponse):
    id: UUID
    tags: List[str]
    description: Optional[str]
    updated_at: datetime


class DeleteMediaResponse(BaseResponse):
    message: str = "Media deleted successfully"


# Image Search Models
class SearchImagesRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    num_results: int = Field(default=20, ge=1, le=50)


class SearchImageResult(BaseModel):
    url: str
    thumbnail_url: str
    title: str
    source: str
    width: Optional[int] = None
    height: Optional[int] = None


class SearchImagesResponse(BaseResponse):
    results: List[SearchImageResult]