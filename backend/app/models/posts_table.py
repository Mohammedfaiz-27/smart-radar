"""
Posts table model for structured social media data
Stores processed and LLM-enriched social media posts from all platforms
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from bson import ObjectId

class Platform(str, Enum):
    """Supported social media platforms"""
    X = "X"
    FACEBOOK = "Facebook"
    YOUTUBE = "YouTube"
    PRINT_MAGAZINE = "Print Magazine"
    GOOGLE_NEWS = "Google News"

class SentimentLabel(str, Enum):
    """Sentiment classification labels"""
    POSITIVE = "Positive"
    NEGATIVE = "Negative"
    NEUTRAL = "Neutral"

class PostBase(BaseModel):
    """Base model for posts table"""
    # Platform identification
    platform_post_id: str = Field(..., description="Original ID from the platform")
    platform: Platform = Field(..., description="Source platform")
    cluster_id: str = Field(..., description="Foreign key referencing clusters table")
    
    # Author information
    author_username: Optional[str] = Field(default="Unknown", description="Username of the post's author")
    author_followers: int = Field(default=0, description="Follower count at time of fetch")
    
    # Post content
    post_text: str = Field(..., description="Full text content of the post")
    post_url: str = Field(..., description="Direct URL to the post")
    posted_at: datetime = Field(..., description="Original timestamp of the post")
    
    # Engagement metrics
    likes: int = Field(default=0, description="Number of likes/reactions")
    comments: int = Field(default=0, description="Number of comments")
    shares: int = Field(default=0, description="Number of shares/retweets")
    views: int = Field(default=0, description="Number of views/impressions")
    
    # LLM-generated intelligence
    sentiment_score: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="LLM-generated sentiment score (-1.0 to 1.0)"
    )
    sentiment_label: SentimentLabel = Field(
        default=SentimentLabel.NEUTRAL,
        description="LLM-generated sentiment label"
    )
    is_threat: bool = Field(
        default=False,
        description="LLM-generated flag for potential threats"
    )
    threat_level: str = Field(
        default="None",
        description="Threat severity: None, Low, Medium, High, Critical"
    )
    threat_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Threat assessment score (0.0 to 1.0)"
    )
    key_narratives: List[str] = Field(
        default_factory=list,
        description="LLM-identified main topics or narratives"
    )
    language: str = Field(
        default="English",
        description="LLM-detected language"
    )
    has_been_responded_to: bool = Field(
        default=False,
        description="Whether this post has been responded to"
    )
    # Full LLM analysis (stored for future reference)
    llm_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Complete LLM analysis including threat assessment details"
    )

    # Multi-entity aspect-based sentiment analysis (NEW v26.0)
    entity_sentiments: Optional[Dict[str, Dict[str, Any]]] = Field(
        default_factory=dict,
        description="""Entity-specific sentiment analysis. Key=entity_name (DMK/ADMK/BJP/TVK), Value=sentiment_data
        Structure: {
            "DMK": {
                "label": "Positive|Negative|Neutral",
                "score": 0.75,  # -1.0 to 1.0
                "confidence": 0.85,  # 0.0 to 1.0
                "mentioned_count": 3,
                "context_relevance": 0.9,
                "text_sentiment": {"score": 0.8, "segments": ["text mentioning DMK"]},
                "emoji_sentiment": {"score": 0.7, "emojis": ["😊", "👍"]},
                "hashtag_sentiment": {"score": 0.6, "hashtags": ["#SupportDMK"]},
                "threat_level": 0.0,
                "threat_reasoning": "No threats detected"
            }
        }"""
    )

    comparative_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="""Analysis of entity relationships when multiple entities mentioned
        Structure: {
            "has_comparison": true,
            "comparison_type": "Direct Contrast|Implicit|Neutral Coexistence",
            "entities_compared": ["DMK", "BJP"],
            "relationship": "DMK praised while BJP criticized",
            "context_segments": ["relevant text showing comparison"]
        }"""
    )

    # System metadata
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when data was fetched"
    )

class PostCreate(PostBase):
    """Model for creating a new post"""
    pass

class PostUpdate(BaseModel):
    """Model for updating post fields"""
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[SentimentLabel] = None
    is_threat: Optional[bool] = None
    threat_level: Optional[str] = None
    threat_score: Optional[float] = None
    key_narratives: Optional[List[str]] = None
    language: Optional[str] = None
    llm_analysis: Optional[Dict[str, Any]] = None
    entity_sentiments: Optional[Dict[str, Dict[str, Any]]] = None  # NEW v26.0
    comparative_analysis: Optional[Dict[str, Any]] = None  # NEW v26.0
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    views: Optional[int] = None

class PostInDB(PostBase):
    """Post model as stored in database"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class PostResponse(PostBase):
    """Post response model for API"""
    id: str
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    # Additional computed fields
    engagement_rate: Optional[float] = Field(None, description="Calculated engagement rate")
    
    def calculate_engagement_rate(self) -> float:
        """Calculate engagement rate based on metrics"""
        if self.views > 0:
            total_engagement = self.likes + self.comments + self.shares
            return (total_engagement / self.views) * 100
        return 0.0

class PostsQueryParams(BaseModel):
    """Parameters for querying posts"""
    cluster_id: Optional[str] = None
    platform: Optional[Platform] = None
    sentiment_label: Optional[SentimentLabel] = None
    is_threat: Optional[bool] = None
    language: Optional[str] = None
    posted_after: Optional[datetime] = None
    posted_before: Optional[datetime] = None
    min_engagement: Optional[int] = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=5000)

class PostsAggregateResponse(BaseModel):
    """Aggregated statistics for posts"""
    total_posts: int
    posts_by_platform: Dict[str, int]
    posts_by_sentiment: Dict[str, int]
    threat_posts: int
    languages: List[str]
    total_engagement: Dict[str, int]  # likes, comments, shares, views
    average_sentiment_score: float
    most_common_narratives: List[Dict[str, Any]]  # narrative text and count