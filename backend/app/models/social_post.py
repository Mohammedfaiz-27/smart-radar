"""
Social Post data model for Entity-Centric Sentiment Process v19.0
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import the new models from common
from app.models.common import ClusterMatch, IntelligenceV19

class SocialPostBase(BaseModel):
    """Base social post model - v19.0 Entity-Centric for multi-platform (X, Facebook, YouTube)"""
    # Platform identifiers
    platform: str = Field(..., pattern="^(X|Facebook|YouTube)$", description="Social media platform")
    platform_post_id: Optional[str] = Field(None, description="Original post ID from the platform")
    
    # Content data
    content: str = Field(..., description="Post text/caption")
    author: str = Field(..., description="Username, handle, or page name")
    post_url: str = Field(..., description="Direct link to the post")
    posted_at: datetime = Field(..., description="When post was originally published")
    
    # Platform-specific engagement metrics
    engagement_metrics: Dict[str, Any] = Field(default_factory=dict, description="Likes, shares, comments, views, etc.")
    
    # Entity-Centric Intelligence v19.0
    intelligence: IntelligenceV19 = Field(..., description="Entity-centric sentiment analysis")
    matched_clusters: List[ClusterMatch] = Field(default_factory=list, description="All clusters that matched this post")
    perspective_type: str = Field(default="multi", description="Analysis type: single or multi-perspective")
    
    # Response tracking
    has_been_responded_to: bool = Field(default=False, description="Whether a response has been generated")
    threat_campaign_id: Optional[str] = Field(None, description="ID of related threat campaign if applicable")
    
    # Additional metadata
    media_urls: List[str] = Field(default_factory=list, description="URLs to images, videos, etc.")
    hashtags: List[str] = Field(default_factory=list, description="Extracted hashtags")
    mentions: List[str] = Field(default_factory=list, description="Extracted @mentions")

class SocialPostCreate(SocialPostBase):
    """Social post creation model"""
    pass

class SocialPostInDB(SocialPostBase):
    """Social post model stored in database"""
    id: str = Field(alias="_id")
    collected_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class SocialPostResponse(SocialPostBase):
    """Social post response model"""
    id: str
    collected_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Platform-specific helper functions for creating posts
def create_x_post(content: str, author: str, post_url: str, platform_post_id: str, 
                  posted_at: datetime, likes: int = 0, retweets: int = 0, 
                  replies: int = 0, hashtags: List[str] = None, 
                  mentions: List[str] = None) -> SocialPostCreate:
    """Helper to create X (Twitter) post"""
    return SocialPostCreate(
        platform="X",
        platform_post_id=platform_post_id,
        content=content,
        author=author,
        post_url=post_url,
        posted_at=posted_at,
        engagement_metrics={
            "likes": likes,
            "retweets": retweets,
            "replies": replies,
            "impressions": 0  # Can be added later
        },
        hashtags=hashtags or [],
        mentions=mentions or [],
        intelligence=IntelligenceV19(
            relational_summary="Pending analysis",
            entity_sentiments={},
            threat_level="low"
        )
    )


def create_facebook_post(content: str, author: str, post_url: str, platform_post_id: str,
                        posted_at: datetime, likes: int = 0, shares: int = 0,
                        comments: int = 0, reactions: Dict[str, int] = None) -> SocialPostCreate:
    """Helper to create Facebook post"""
    engagement = {
        "likes": likes,
        "shares": shares,
        "comments": comments
    }
    if reactions:
        engagement["reactions"] = reactions
        
    return SocialPostCreate(
        platform="Facebook",
        platform_post_id=platform_post_id,
        content=content,
        author=author,
        post_url=post_url,
        posted_at=posted_at,
        engagement_metrics=engagement,
        intelligence=IntelligenceV19(
            relational_summary="Pending analysis",
            entity_sentiments={},
            threat_level="low"
        )
    )


def create_youtube_post(content: str, author: str, post_url: str, platform_post_id: str,
                       posted_at: datetime, views: int = 0, likes: int = 0,
                       dislikes: int = 0, comments: int = 0, duration: str = None) -> SocialPostCreate:
    """Helper to create YouTube video post"""
    engagement = {
        "views": views,
        "likes": likes,
        "dislikes": dislikes,
        "comments": comments
    }
    if duration:
        engagement["duration"] = duration
        
    return SocialPostCreate(
        platform="YouTube",
        platform_post_id=platform_post_id,
        content=content,
        author=author,
        post_url=post_url,
        posted_at=posted_at,
        engagement_metrics=engagement,
        intelligence=IntelligenceV19(
            relational_summary="Pending analysis",
            entity_sentiments={},
            threat_level="low"
        )
    )