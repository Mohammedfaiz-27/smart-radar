from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum

from .base import BaseResponse
from .content import Platform


class DateRange(str, Enum):
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"


class InsightType(str, Enum):
    BEST_POSTING_TIME = "best_posting_time"
    CONTENT_TYPE = "content_type"
    AUDIENCE_GROWTH = "audience_growth"
    ENGAGEMENT_PATTERN = "engagement_pattern"


# Response Models
class PostMetrics(BaseModel):
    total_reach: int
    total_engagement: int
    engagement_rate: float
    clicks: int


class PlatformMetrics(BaseModel):
    platform: Platform
    reach: int
    engagement: int
    likes: int
    shares: Optional[int] = None
    comments: int
    clicks: int


class PostAnalytics(BaseModel):
    post_id: UUID
    overall_metrics: PostMetrics
    platform_breakdown: List[PlatformMetrics]


class GetPostAnalyticsResponse(BaseResponse):
    post_id: UUID
    overall_metrics: PostMetrics
    platform_breakdown: List[PlatformMetrics]


class DashboardOverview(BaseModel):
    total_posts: int
    total_reach: int
    total_engagement: int
    avg_engagement_rate: float


class PlatformPerformance(BaseModel):
    platform: Platform
    posts: int
    reach: int
    engagement: int
    engagement_rate: float


class TopPerformingPost(BaseModel):
    post_id: UUID
    title: str
    engagement: int
    reach: int


class EngagementTrend(BaseModel):
    date: date
    engagement: int


class GetDashboardResponse(BaseResponse):
    overview: DashboardOverview
    platform_performance: List[PlatformPerformance]
    top_performing_posts: List[TopPerformingPost]
    engagement_trends: List[EngagementTrend]


class Insight(BaseModel):
    type: InsightType
    platform: Optional[Platform] = None
    recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)


class Demographics(BaseModel):
    age_groups: Dict[str, float]
    top_locations: List[str]


class EngagementPatterns(BaseModel):
    best_days: List[str]
    best_hours: List[int]


class AudienceInsights(BaseModel):
    demographics: Demographics
    engagement_patterns: EngagementPatterns


class GetInsightsResponse(BaseResponse):
    insights: List[Insight]
    audience_insights: AudienceInsights