"""
Unified monitored content model for SMART RADAR v25.0
Consolidates social_posts and news_articles into single collection
"""
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum

class ContentType(str, Enum):
    SOCIAL_POST = "social_post"
    NEWS_ARTICLE = "news_article"

class Platform(str, Enum):
    X = "X"
    FACEBOOK = "Facebook"
    YOUTUBE = "YouTube"
    NEWS_SITE = "news_site"

class EntitySentiment(BaseModel):
    """Entity-specific sentiment analysis"""
    label: str = Field(..., description="Sentiment label: Positive, Negative, Neutral")
    score: float = Field(..., ge=-1.0, le=1.0, description="Sentiment score between -1 and 1")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in sentiment analysis")
    mentioned_count: int = Field(default=1, description="Number of times entity is mentioned")
    context_relevance: float = Field(..., ge=0.0, le=1.0, description="How relevant the mention is to the entity")

class IntelligenceV24(BaseModel):
    """Master Intelligence Prompt v24.0 - Entity-Centric Scoring"""
    relational_summary: str = Field(..., description="Comprehensive content summary with entity relationships")
    entity_sentiments: Dict[str, EntitySentiment] = Field(default_factory=dict, description="Entity-specific sentiment analysis")
    threat_level: str = Field(..., pattern="^(low|medium|high|critical)$", description="Threat assessment level")
    threat_reasoning: str = Field(..., description="Explanation for threat level assignment")
    narrative_alignment: Dict[str, float] = Field(default_factory=dict, description="Alignment with known narratives (0-1 scale)")
    response_urgency: str = Field(..., pattern="^(low|medium|high|immediate)$", description="Response urgency level")
    key_themes: List[str] = Field(default_factory=list, description="Main themes identified in content")
    geopolitical_context: str = Field(default="", description="Relevant geopolitical context")
    misinformation_risk: float = Field(default=0.0, ge=0.0, le=1.0, description="Risk of misinformation (0-1 scale)")
    virality_potential: float = Field(default=0.0, ge=0.0, le=1.0, description="Potential for viral spread (0-1 scale)")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SocialMetrics(BaseModel):
    """Social media specific metrics"""
    likes: int = Field(default=0)
    shares: int = Field(default=0)
    comments: int = Field(default=0)
    views: int = Field(default=0)
    engagement_rate: float = Field(default=0.0, ge=0.0, description="Calculated engagement rate")
    follower_count: int = Field(default=0, description="Author's follower count")

class NewsMetrics(BaseModel):
    """News article specific metrics"""
    word_count: int = Field(default=0)
    reading_time_minutes: int = Field(default=0)
    source_credibility: float = Field(default=0.5, ge=0.0, le=1.0, description="Source credibility score")
    article_category: str = Field(default="", description="News category")
    journalist_name: Optional[str] = Field(None, description="Author/journalist name")

class MonitoredContentBase(BaseModel):
    """Base model for unified monitored content"""
    # Core identification
    content_type: ContentType = Field(..., description="Type of content")
    platform: Platform = Field(..., description="Source platform")
    platform_content_id: str = Field(..., description="Unique ID from source platform")
    
    # Content data
    title: str = Field(..., description="Content title or first line")
    content: str = Field(..., description="Full content text")
    author: str = Field(..., description="Content author/creator")
    url: Optional[str] = Field(None, description="Source URL")
    
    # Temporal data
    published_at: datetime = Field(..., description="When content was published")
    collected_at: datetime = Field(default_factory=datetime.utcnow, description="When content was collected")
    
    # Intelligence analysis (v24.0)
    intelligence: Optional[IntelligenceV24] = Field(None, description="AI-generated intelligence analysis")
    
    # Cluster associations
    matched_clusters: List[Dict[str, Any]] = Field(default_factory=list, description="Matching cluster information")
    
    # Platform-specific metrics
    social_metrics: Optional[SocialMetrics] = Field(None, description="Social media metrics (if applicable)")
    news_metrics: Optional[NewsMetrics] = Field(None, description="News article metrics (if applicable)")
    
    # Processing metadata
    processing_status: str = Field(default="pending", pattern="^(pending|processing|completed|failed)$")
    processing_errors: List[str] = Field(default_factory=list, description="Any processing errors encountered")
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class MonitoredContent(MonitoredContentBase):
    """Complete monitored content model with database fields"""
    id: Optional[str] = Field(None, alias="_id", description="MongoDB ObjectId")
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "content_type": "social_post",
                "platform": "X",
                "platform_content_id": "1234567890",
                "title": "Important political announcement",
                "content": "Today we announce new policy changes...",
                "author": "@politician_handle",
                "url": "https://x.com/politician_handle/status/1234567890",
                "published_at": "2024-01-01T12:00:00Z",
                "intelligence": {
                    "relational_summary": "Political announcement about policy changes with mention of DMK and opposition parties",
                    "entity_sentiments": {
                        "DMK": {
                            "label": "Positive",
                            "score": 0.7,
                            "confidence": 0.85,
                            "mentioned_count": 2,
                            "context_relevance": 0.9
                        }
                    },
                    "threat_level": "low",
                    "threat_reasoning": "Standard policy announcement without inflammatory language",
                    "response_urgency": "low",
                    "key_themes": ["policy", "governance", "announcement"],
                    "misinformation_risk": 0.1,
                    "virality_potential": 0.3
                },
                "matched_clusters": [
                    {
                        "cluster_name": "DMK",
                        "cluster_type": "own",
                        "match_score": 0.95,
                        "matched_keywords": ["DMK", "policy"]
                    }
                ],
                "social_metrics": {
                    "likes": 150,
                    "shares": 25,
                    "comments": 30,
                    "views": 5000,
                    "engagement_rate": 0.041,
                    "follower_count": 50000
                }
            }
        }

class MonitoredContentResponse(MonitoredContentBase):
    """Response model for API endpoints"""
    id: str = Field(..., description="Content ID")
    
class MonitoredContentCreate(BaseModel):
    """Model for creating new monitored content"""
    content_type: ContentType
    platform: Platform
    platform_content_id: str
    title: str
    content: str
    author: str
    url: Optional[str] = None
    published_at: datetime
    
    # Optional pre-computed metrics
    social_metrics: Optional[SocialMetrics] = None
    news_metrics: Optional[NewsMetrics] = None

class MonitoredContentUpdate(BaseModel):
    """Model for updating existing monitored content"""
    intelligence: Optional[IntelligenceV24] = None
    matched_clusters: Optional[List[Dict[str, Any]]] = None
    processing_status: Optional[str] = None
    processing_errors: Optional[List[str]] = None
    social_metrics: Optional[SocialMetrics] = None
    news_metrics: Optional[NewsMetrics] = None

# Query models for filtering
class ContentQueryParams(BaseModel):
    """Query parameters for content filtering"""
    content_type: Optional[ContentType] = None
    platform: Optional[Platform] = None
    cluster_type: Optional[str] = None  # "own", "competitor"
    cluster_name: Optional[str] = None
    threat_level: Optional[str] = None
    response_urgency: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    
class ContentAggregation(BaseModel):
    """Model for aggregated content analytics"""
    total_content: int
    content_by_type: Dict[str, int]
    content_by_platform: Dict[str, int]
    threat_distribution: Dict[str, int]
    sentiment_distribution: Dict[str, Dict[str, int]]  # entity -> sentiment counts
    top_entities: List[Dict[str, Any]]
    trending_themes: List[str]
    time_range: Dict[str, datetime]