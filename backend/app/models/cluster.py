"""
Cluster data model for MongoDB
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Optional
from datetime import datetime
from bson import ObjectId
from enum import Enum

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, _source_type, _handler):
        return {"type": "string"}

class DashboardType(str, Enum):
    """Dashboard type for cluster display"""
    OWN = "Own"
    COMPETITOR = "Competitor"

class PlatformConfig(BaseModel):
    """Platform-specific configuration"""
    enabled: bool = Field(default=True, description="Whether to collect from this platform")
    language: Optional[str] = Field(default=None, description="Language filter (e.g., 'en', 'ta')")
    location: Optional[str] = Field(default=None, description="Geographic location (e.g., 'Tamilnadu')")
    min_engagement: int = Field(default=0, description="Minimum engagement threshold")
    max_results: int = Field(default=30, description="Maximum results per fetch (reduced from 100 for speed)")
    
class ClusterPlatformConfig(BaseModel):
    """Configuration for all platforms"""
    x: PlatformConfig = Field(default_factory=PlatformConfig)
    facebook: PlatformConfig = Field(default_factory=PlatformConfig)
    youtube: PlatformConfig = Field(default_factory=PlatformConfig)

class ClusterThresholds(BaseModel):
    """Platform-specific thresholds for engagement"""
    twitter: Dict[str, int] = Field(default_factory=dict)
    facebook: Dict[str, int] = Field(default_factory=dict)
    instagram: Dict[str, int] = Field(default_factory=dict)

class ClusterBase(BaseModel):
    """Base cluster model"""
    name: str = Field(..., min_length=1, max_length=200)
    cluster_type: Literal["own", "competitor"]
    dashboard_type: DashboardType = Field(default=DashboardType.OWN, description="Dashboard to display data on")
    keywords: List[str] = Field(..., min_items=1)
    thresholds: ClusterThresholds = Field(default_factory=ClusterThresholds)
    platform_config: ClusterPlatformConfig = Field(default_factory=ClusterPlatformConfig, description="Platform-specific settings")
    fetch_frequency_minutes: int = Field(default=30, ge=5, le=1440, description="How often to fetch data (5-1440 minutes)")
    is_active: bool = True

class ClusterCreate(ClusterBase):
    """Cluster creation model"""
    pass

class ClusterUpdate(BaseModel):
    """Cluster update model"""
    name: Optional[str] = None
    cluster_type: Optional[Literal["own", "competitor"]] = None
    dashboard_type: Optional[DashboardType] = None
    keywords: Optional[List[str]] = None
    thresholds: Optional[ClusterThresholds] = None
    platform_config: Optional[ClusterPlatformConfig] = None
    fetch_frequency_minutes: Optional[int] = None
    is_active: Optional[bool] = None

class ClusterInDB(ClusterBase):
    """Cluster model stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class ClusterResponse(ClusterBase):
    """Cluster response model"""
    id: str
    created_at: datetime
    updated_at: datetime