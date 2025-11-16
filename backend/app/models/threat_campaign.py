"""
Threat Campaign data model for MongoDB
"""
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Literal, Optional, List
from datetime import datetime
from bson import ObjectId


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
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")
        return field_schema


class ThreatCampaignBase(BaseModel):
    """Base threat campaign model"""
    name: str
    description: str
    cluster_type: Literal["own", "competitor"]
    threat_level: Literal["low", "medium", "high", "critical"]
    status: Literal["active", "monitoring", "resolved", "acknowledged"] = "active"
    keywords: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    participating_accounts: List[str] = Field(default_factory=list)
    post_ids: List[str] = Field(default_factory=list)
    
    # Campaign analytics
    total_posts: int = 0
    total_engagement: int = 0
    average_sentiment: float = 0.0
    campaign_velocity: float = 0.0  # Posts per hour
    reach_estimate: int = 0
    
    # Time tracking
    first_detected_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


class ThreatCampaignCreate(ThreatCampaignBase):
    """Threat campaign creation model"""
    pass


class ThreatCampaignInDB(ThreatCampaignBase):
    """Threat campaign model stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ThreatCampaignResponse(ThreatCampaignBase):
    """Threat campaign response model"""
    id: str
    created_at: datetime


class ThreatCampaignUpdate(BaseModel):
    """Threat campaign update model"""
    name: Optional[str] = None
    description: Optional[str] = None
    threat_level: Optional[Literal["low", "medium", "high", "critical"]] = None
    status: Optional[Literal["active", "monitoring", "resolved", "acknowledged"]] = None
    keywords: Optional[List[str]] = None
    hashtags: Optional[List[str]] = None
    participating_accounts: Optional[List[str]] = None
    post_ids: Optional[List[str]] = None
    
    # Analytics updates
    total_posts: Optional[int] = None
    total_engagement: Optional[int] = None
    average_sentiment: Optional[float] = None
    campaign_velocity: Optional[float] = None
    reach_estimate: Optional[int] = None
    
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)


class CampaignStats(BaseModel):
    """Campaign statistics for dashboard"""
    total_campaigns: int = 0
    active_campaigns: int = 0
    critical_campaigns: int = 0
    high_threat_campaigns: int = 0
    campaigns_today: int = 0
    average_velocity: float = 0.0