from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # API Configuration
    app_name: str = "SmartPost"
    app_version: str = "1.0.0"
    api_v1_prefix: str = "/v1"
    debug: bool = False

    # Supabase Configuration
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    supabase_service_key: Optional[str] = None
    supabase_db_password: Optional[str] = None  # Direct database password for RLS
    use_rls: bool = False  # Enable RLS by default

    # JWT Configuration
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 525600  # 1 year
    jwt_refresh_token_expire_days: int = 365

    # CORS Configuration
    cors_origins: list[str] = [
        "https://app.smartpost.live",
        "https://smartpost.live",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://40.192.3.94:5173",
        "http://ec2-40-192-3-94.ap-south-2.compute.amazonaws.com",
    ]

    # Stripe Configuration
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None

    # OpenAI Configuration
    openai_api_key: Optional[str] = None

    # Google Gemini Configuration
    google_api_key: Optional[str] = None

    # News API Configuration
    news_api_key: Optional[str] = None

    # Perplexity Configuration
    perplexity_api_key: Optional[str] = None

    # SerpAPI Configuration
    serpapi_key: Optional[str] = None

    # Google Custom Search Configuration
    google_custom_search_api_key: Optional[str] = None
    google_custom_search_engine_id: Optional[str] = None
    # Image search provider: 'serpapi' or 'google_custom_search'
    image_search_provider: str = "google_custom_search"

    # Facebook Configuration
    fb_app_id: Optional[str] = None
    fb_app_secret: Optional[str] = None
    fb_long_lived_token: Optional[str] = None

    # Periskope Configuration
    periskope_api_key: Optional[str] = None

    # WhatsApp Configuration
    whatsapp_sender_phone: Optional[str] = None

    # RapidAPI Configuration
    rapidapi_key_facebook: Optional[str] = None
    rapidapi_key_twitter: Optional[str] = None

    # Redis Configuration (for Celery)
    redis_url: str = "redis://localhost:6379/0"

    # AWS Configuration
    aws_access_key: Optional[str] = None
    aws_secret: Optional[str] = None
    aws_s3_bucket: str = "omnipush-media"
    aws_region: str = "us-east-1"

    # AWS SQS Configuration (for NewsIt integration)
    aws_sqs_queue_url: Optional[str] = None
    aws_sqs_region: str = "ap-south-1"
    aws_sqs_max_messages: int = 10
    aws_sqs_wait_time: int = 20  # Long polling in seconds
    aws_sqs_access_key: Optional[str] = None
    aws_sqs_secret: Optional[str] = None

    # AWS SQS Configuration for Slack Consumer (Reshare Post)
    aws_slack_consumer_sqs_queue_url: Optional[str] = None

    # NewsIt API Configuration
    newsit_api_base_url: str = "https://api.newsit.media/news-svc/api/v1"
    newsit_api_timeout: int = 30

    # File Storage
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_file_types: list[str] = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "video/mp4",
        "video/quicktime",
        "application/pdf",
    ]

    # Rate Limiting
    rate_limit_per_minute: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields without validation errors


settings = Settings()
