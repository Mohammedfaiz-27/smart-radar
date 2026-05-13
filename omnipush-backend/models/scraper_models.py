from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


# Special constant for intelligent district-based channel group routing
RECOMMENDED_CHANNELS_MAGIC_VALUE = "__RECOMMENDED_CHANNELS__"


class ScraperJobStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Platform(str, Enum):
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    NEWSIT = "newsit"
    # LINKEDIN = "linkedin"
    # YOUTUBE = "youtube"
    # TELEGRAM = "telegram"


class ResolutionStatus(str, Enum):
    """Status of social account URL resolution"""
    PENDING = "pending"
    RESOLVED = "resolved"
    FAILED = "failed"


class SocialAccountInput(BaseModel):
    """Input model for adding a social account URL to a scraper job"""
    platform: Platform = Field(..., description="Social media platform")
    account_url: str = Field(..., min_length=1, description="Full URL to the social media account")

    class Config:
        json_schema_extra = {
            "example": {
                "platform": "facebook",
                "account_url": "https://facebook.com/technews"
            }
        }


class SocialAccountResolved(BaseModel):
    """Model for a resolved social media account"""
    id: UUID
    scraper_job_id: UUID
    platform: str
    account_url: str
    account_identifier: Optional[str] = Field(None, description="Resolved username/handle")
    account_id: Optional[str] = Field(None, description="Platform-specific account ID")
    account_name: Optional[str] = Field(None, description="Display name of the account")
    account_metadata: Dict[str, Any] = Field(default={}, description="Additional platform-specific data")
    resolution_status: str = Field(default="pending", description="Resolution status")
    resolution_error: Optional[str] = Field(None, description="Error message if resolution failed")
    resolved_at: Optional[datetime] = None
    last_validation_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScraperJobSettings(BaseModel):
    """Additional settings for scraper jobs"""
    max_posts_per_run: int = Field(default=10, description="Maximum posts to process per run")
    auto_publish: bool = Field(default=False, description="Automatically publish approved posts")
    generate_news_card: bool = Field(default=True, description="Generate news cards for posts")
    content_filters: List[str] = Field(default=[], description="Content filters to apply")
    min_engagement_threshold: int = Field(default=0, description="Minimum engagement for posts")
    exclude_keywords: List[str] = Field(default=[], description="Keywords to exclude from scraping")
    language_filter: Optional[str] = Field(default=None, description="Language filter (e.g., 'en', 'ta')")
    location_filter: Optional[str] = Field(default=None, description="Location filter")
    date_range_days: int = Field(default=1, description="How many days back to search")
    channel_group_ids: Optional[List[str]] = Field(default=None, description="Channel group IDs for publishing (supports multiple groups)")
    post_mode: Optional[str] = Field(default="auto", description="Post mode (auto, text, image, news_card, etc.)")
    post_approval_logic: Optional[str] = Field(default=None, description="Natural language approval/rejection logic for posts")


class ScraperJobCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Job name")
    description: Optional[str] = Field(None, description="Job description")
    keywords: List[str] = Field(default=[], description="Keywords to search for (optional if social_accounts provided)")
    platforms: List[Platform] = Field(..., min_items=1, description="Social media platforms to scrape")
    schedule_cron: str = Field(default="*/5 * * * *", description="Cron schedule expression")
    is_enabled: bool = Field(default=True, description="Whether the job is enabled")
    settings: Optional[ScraperJobSettings] = Field(default_factory=ScraperJobSettings, description="Additional job settings")
    social_accounts: Optional[List[SocialAccountInput]] = Field(default=None, description="Social media account URLs to scrape (optional)")


class ScraperJobUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    platforms: Optional[List[Platform]] = Field(None, min_items=1)
    schedule_cron: Optional[str] = None
    is_enabled: Optional[bool] = None
    settings: Optional[ScraperJobSettings] = None
    social_accounts: Optional[List[SocialAccountInput]] = Field(default=None, description="Social media account URLs to scrape (optional)")


class ScraperJob(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: Optional[str]
    keywords: List[str]
    platforms: List[str]
    schedule_cron: str
    is_enabled: bool
    settings: Dict[str, Any]
    post_approval_logic: Optional[str]
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    run_count: int
    success_count: int
    error_count: int
    last_error: Optional[str]
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    social_accounts: List[SocialAccountResolved] = Field(default=[], description="Resolved social media accounts")

    class Config:
        from_attributes = True


class ScraperJobRunCreate(BaseModel):
    scraper_job_id: UUID
    status: ScraperJobStatus = ScraperJobStatus.RUNNING


class ScraperJobRunUpdate(BaseModel):
    status: Optional[ScraperJobStatus] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    posts_found: Optional[int] = None
    posts_processed: Optional[int] = None
    posts_approved: Optional[int] = None
    posts_published: Optional[int] = None
    error_message: Optional[str] = None
    run_log: Optional[Dict[str, Any]] = None


class ScraperJobRun(BaseModel):
    id: UUID
    scraper_job_id: UUID
    tenant_id: UUID
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    posts_found: int
    posts_processed: int
    posts_approved: int
    posts_published: int
    error_message: Optional[str]
    run_log: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class ScraperJobWithStats(ScraperJob):
    """Extended scraper job model with execution statistics"""
    total_posts_found: int = 0
    total_posts_processed: int = 0
    total_posts_approved: int = 0
    total_posts_published: int = 0
    avg_posts_per_run: float = 0.0
    success_rate: float = 0.0
    last_run_duration: Optional[int] = None


class ScraperJobList(BaseModel):
    """Response model for listing scraper jobs"""
    jobs: List[ScraperJobWithStats]
    total: int
    page: int
    size: int
    has_next: bool