"""
Celery instance creation - separated to avoid circular imports
"""
import os
import asyncio
from celery import Celery
from celery.signals import setup_logging, worker_ready
from dotenv import load_dotenv

load_dotenv()

# Import our logging configuration
from app.core.logging_config import setup_logging as setup_app_logging

# MongoDB URL for Celery broker and result backend
mongodb_url = os.getenv("MONGODB_URL", "mongodb+srv://smart_radar_db_user:<db_password>@smart-radar.exjrbpk.mongodb.net/smart_radar?retryWrites=true&w=majority&appName=smart-radar")

# Setup logging before creating Celery instance
@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Configure logging when Celery worker starts"""
    setup_app_logging("celery_worker", "DEBUG")

# Setup database connection when worker starts
@worker_ready.connect
def setup_database_connection(*args, **kwargs):
    """Initialize database connection when Celery worker is ready"""
    from app.core.database import connect_to_mongo
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("🔗 Initializing database connection for Celery worker")
    
    # Create event loop if one doesn't exist
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Connect to database
    try:
        loop.run_until_complete(connect_to_mongo())
        logger.info("✅ Database connection established for Celery worker")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")

# Create Celery instance with MongoDB broker and backend
# For MongoDB Atlas SRV URLs, we need to append the database name
if mongodb_url.startswith("mongodb+srv://"):
    # Extract base URL and add database name for Celery
    celery_broker = f"{mongodb_url.split('?')[0].rstrip('/')}/smart_radar"
    if '?' in mongodb_url:
        celery_broker += '?' + mongodb_url.split('?')[1]
else:
    celery_broker = mongodb_url

celery_app = Celery(
    "smart_radar",
    broker=celery_broker,
    backend=celery_broker,
    include=[
        "app.tasks.data_collection_tasks",
        "app.tasks.intelligence_tasks",
        "app.tasks.monitoring_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "app.tasks.data_collection_tasks.*": {"queue": "data_collection"},
        "app.tasks.intelligence_tasks.*": {"queue": "intelligence"},
        "app.tasks.monitoring_tasks.*": {"queue": "monitoring"},
    },
    
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone configuration
    timezone="UTC",
    enable_utc=True,
    
    # Task result configuration
    result_expires=3600,  # Results expire after 1 hour
    
    # Task execution configuration
    task_time_limit=900,  # 15 minutes max per task (increased for multi-platform collection)
    task_soft_time_limit=840,  # 14 minutes soft limit
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Configure queues
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_create_missing_queues = True

# Import tasks to register them
try:
    import app.tasks.data_collection_tasks
    import app.tasks.intelligence_tasks
    import app.tasks.monitoring_tasks
    import app.tasks.threat_campaign_tasks
except ImportError as e:
    print(f"Warning: Could not import tasks: {e}")

# Configure beat schedule
def get_beat_schedule():
    """
    Generate beat schedule based on environment configuration
    """
    import os
    
    # Automatic collection configuration from environment variables
    ENABLE_AUTO_COLLECTION = os.getenv("ENABLE_AUTO_COLLECTION", "true").lower() == "true"
    DATA_COLLECTION_INTERVAL_MINUTES = int(os.getenv("DATA_COLLECTION_INTERVAL_MINUTES", "15"))
    INTELLIGENCE_PROCESSING_INTERVAL_MINUTES = int(os.getenv("INTELLIGENCE_PROCESSING_INTERVAL_MINUTES", "5"))
    THREAT_MONITORING_INTERVAL_MINUTES = int(os.getenv("THREAT_MONITORING_INTERVAL_MINUTES", "5"))
    NEWS_COLLECTION_INTERVAL_MINUTES = int(os.getenv("NEWS_COLLECTION_INTERVAL_MINUTES", "60"))
    ENABLE_NEWS_COLLECTION = os.getenv("ENABLE_NEWS_COLLECTION", "true").lower() == "true"
    DAILY_ANALYTICS_ENABLED = os.getenv("DAILY_ANALYTICS_ENABLED", "true").lower() == "true"
    WEEKLY_CLEANUP_ENABLED = os.getenv("WEEKLY_CLEANUP_ENABLED", "true").lower() == "true"
    
    schedule = {}
    
    # Data collection tasks (conditional)
    if ENABLE_AUTO_COLLECTION:
        schedule["collect-posts-automatic"] = {
            "task": "app.tasks.data_collection_tasks.scheduled_data_collection",
            "schedule": DATA_COLLECTION_INTERVAL_MINUTES * 60,
        }
    
    # Intelligence processing for new posts
    schedule["process-intelligence-automatic"] = {
        "task": "app.tasks.intelligence_tasks.process_pending_intelligence",
        "schedule": INTELLIGENCE_PROCESSING_INTERVAL_MINUTES * 60,
    }
    
    # Threat monitoring
    schedule["monitor-threats-automatic"] = {
        "task": "app.tasks.monitoring_tasks.monitor_threat_posts",
        "schedule": THREAT_MONITORING_INTERVAL_MINUTES * 60,
    }
    
    # News collection (conditional)
    if ENABLE_NEWS_COLLECTION:
        schedule["collect-news-automatic"] = {
            "task": "app.tasks.data_collection_tasks.scheduled_news_collection",
            "schedule": NEWS_COLLECTION_INTERVAL_MINUTES * 60,
        }
    
    # Daily analytics aggregation (conditional)
    if DAILY_ANALYTICS_ENABLED:
        schedule["daily-analytics-aggregation"] = {
            "task": "app.tasks.monitoring_tasks.aggregate_daily_analytics",
            "schedule": 24.0 * 60 * 60,  # Every 24 hours
        }
    
    # Weekly cleanup (conditional)
    if WEEKLY_CLEANUP_ENABLED:
        schedule["cleanup-old-data-weekly"] = {
            "task": "app.tasks.monitoring_tasks.cleanup_old_data",
            "schedule": 7.0 * 24 * 60 * 60,  # Every 7 days
        }
    
    return schedule

# Set beat schedule on the celery instance
celery_app.conf.beat_schedule = get_beat_schedule()