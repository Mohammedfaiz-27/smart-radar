"""
News Article data models for Entity-Centric Sentiment Process v19.0
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId

from app.models.common import ClusterMatch, IntelligenceV19

class NewsArticleIntelligence(IntelligenceV19):
    """Intelligence analysis for news articles - v19.0 Entity-Centric"""
    impact_level: str = Field(default="medium", pattern="^(low|medium|high)$", description="Assessed impact level")
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in analysis")


class NewsArticleBase(BaseModel):
    """Base news article model - v19.0 Entity-Centric"""
    # Platform and source information
    platform: str = Field(default="web_news", pattern="^(web_news|print_daily|print_magazine)$", description="Source platform type")
    title: str = Field(..., min_length=1, max_length=500, description="Article headline")
    summary: Optional[str] = Field(None, max_length=2000, description="Article summary/excerpt")
    content: Optional[str] = Field(None, description="Full article content")
    source: str = Field(..., min_length=1, max_length=200, description="Publication name")
    author: Optional[str] = Field(None, max_length=200, description="Article author")
    url: str = Field(..., description="Original article URL")
    published_at: datetime = Field(..., description="Article publication date")
    
    # Entity-Centric Intelligence v19.0
    matched_clusters: List[ClusterMatch] = Field(default_factory=list, description="All clusters that matched this article")
    intelligence: NewsArticleIntelligence = Field(..., description="Entity-centric sentiment analysis")
    perspective_type: str = Field(default="multi", description="Analysis type: single or multi-perspective")
    
    # Metadata
    category: Optional[str] = Field(None, max_length=100, description="Article category")
    tags: List[str] = Field(default_factory=list, description="Article tags/keywords")
    readers_count: Optional[int] = Field(None, ge=0, description="Estimated reader count")


class NewsArticleCreate(NewsArticleBase):
    """Schema for creating news articles - v19.0 Entity-Centric"""
    pass


class NewsArticleInDB(NewsArticleBase):
    """News article model stored in database"""
    id: str = Field(alias="_id", description="MongoDB document ID")
    collected_at: datetime = Field(default_factory=datetime.utcnow, description="When article was collected")
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }


class NewsArticleResponse(NewsArticleBase):
    """Schema for news article responses - v19.0 Entity-Centric"""
    id: str = Field(..., description="Article ID")
    collected_at: datetime = Field(..., description="Collection timestamp")
    
    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }


class NewsArticleUpdate(BaseModel):
    """Schema for updating news articles"""
    platform: Optional[str] = Field(None, pattern="^(web_news|print_daily|print_magazine)$", description="Source platform type")
    summary: Optional[str] = Field(None, max_length=2000)
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    readers_count: Optional[int] = Field(None, ge=0)
    intelligence: Optional[NewsArticleIntelligence] = None
    perspective_type: Optional[str] = Field(None, pattern="^(single|multi)$")


# Helper functions for creating news articles
def create_web_news_article(title: str, summary: str, source: str, url: str, 
                           published_at: datetime, author: str = None,
                           category: str = None, readers_count: int = None) -> NewsArticleCreate:
    """Helper to create web news article"""
    return NewsArticleCreate(
        platform="web_news",
        title=title,
        summary=summary,
        source=source,
        author=author,
        url=url,
        published_at=published_at,
        category=category,
        readers_count=readers_count,
        intelligence=NewsArticleIntelligence(
            relational_summary="Pending analysis",
            entity_sentiments={},
            threat_level="low",
            impact_level="medium",
            confidence_score=0.8
        )
    )


def create_print_news_article(title: str, summary: str, source: str, url: str,
                             published_at: datetime, author: str = None,
                             platform_type: str = "print_daily") -> NewsArticleCreate:
    """Helper to create print news article (daily/magazine)"""
    return NewsArticleCreate(
        platform=platform_type,  # print_daily or print_magazine
        title=title,
        summary=summary,
        source=source,
        author=author,
        url=url,
        published_at=published_at,
        intelligence=NewsArticleIntelligence(
            relational_summary="Pending analysis",
            entity_sentiments={},
            threat_level="low",
            impact_level="medium",
            confidence_score=0.8
        )
    )