"""
Raw data storage model for unprocessed API responses
Stores raw JSON data from platform APIs for backup and reprocessing
"""
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
from bson import ObjectId

class ProcessingStatus(str, Enum):
    """Processing status for raw data"""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    # Legacy uppercase values for compatibility
    PENDING_UPPER = "PENDING"
    PROCESSING_UPPER = "PROCESSING"
    COMPLETED_UPPER = "COMPLETED" 
    PROCESSED = "PROCESSED"
    FAILED_UPPER = "FAILED"
    SKIPPED_UPPER = "SKIPPED"

class RawDataPlatform(str, Enum):
    """Supported platforms for raw data collection"""
    X = "X"
    FACEBOOK = "Facebook"
    YOUTUBE = "YouTube"
    GOOGLE_NEWS = "Google News"

class RawDataBase(BaseModel):
    """Base model for raw data storage"""
    # Source information
    platform: RawDataPlatform = Field(..., description="Source platform")
    cluster_id: str = Field(..., description="Associated cluster ID")
    keyword: str = Field(..., description="Search keyword used")
    
    # Raw API response
    raw_json: Dict[str, Any] = Field(..., description="Complete raw JSON from API")
    api_endpoint: str = Field(..., description="API endpoint used")
    api_params: Dict[str, Any] = Field(default_factory=dict, description="API parameters used")
    
    # Processing metadata
    processing_status: ProcessingStatus = Field(
        default=ProcessingStatus.PENDING,
        description="Current processing status"
    )
    processed_at: Optional[datetime] = Field(None, description="When data was processed")
    processing_error: Optional[str] = Field(None, description="Error message if processing failed")
    posts_extracted: int = Field(default=0, description="Number of posts extracted from this data")
    
    # Collection metadata
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when data was fetched"
    )
    response_size_bytes: int = Field(default=0, description="Size of raw response in bytes")
    
    # Pagination info (if applicable)
    has_next_page: bool = Field(default=False, description="Whether there's more data to fetch")
    next_cursor: Optional[str] = Field(None, description="Cursor/token for next page")
    page_number: Optional[int] = Field(None, description="Page number if using numbered pagination")

class RawDataCreate(RawDataBase):
    """Model for creating new raw data entry"""
    pass

class RawDataUpdate(BaseModel):
    """Model for updating raw data entry"""
    processing_status: Optional[ProcessingStatus] = None
    processed_at: Optional[datetime] = None
    processing_error: Optional[str] = None
    posts_extracted: Optional[int] = None

class RawDataInDB(RawDataBase):
    """Raw data model as stored in database"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class RawDataResponse(RawDataBase):
    """Raw data response model for API"""
    id: str
    created_at: datetime
    updated_at: datetime

class RawDataQueryParams(BaseModel):
    """Parameters for querying raw data"""
    platform: Optional[RawDataPlatform] = None
    cluster_id: Optional[str] = None
    processing_status: Optional[ProcessingStatus] = None
    fetched_after: Optional[datetime] = None
    fetched_before: Optional[datetime] = None
    has_error: Optional[bool] = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)

class RawDataStats(BaseModel):
    """Statistics for raw data collection"""
    total_records: int
    records_by_platform: Dict[str, int]
    records_by_status: Dict[str, int]
    total_posts_extracted: int
    failed_processing_count: int
    pending_processing_count: int
    oldest_unprocessed: Optional[datetime]
    total_size_mb: float