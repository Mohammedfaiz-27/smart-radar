"""
Celery configuration for background tasks
"""
import os
import logging
from celery import Celery
from celery.signals import setup_logging
from dotenv import load_dotenv

load_dotenv()

# Import our logging configuration
from app.core.logging_config import setup_logging as setup_app_logging
# Import the celery instance
from app.core.celery_instance import celery_app

# MongoDB URL for Celery broker and result backend
mongodb_url = os.getenv("MONGODB_URL", "mongodb+srv://smart_radar_db_user:<db_password>@smart-radar.exjrbpk.mongodb.net/smart_radar?retryWrites=true&w=majority&appName=smart-radar")

# Automatic collection configuration from environment variables
ENABLE_AUTO_COLLECTION = os.getenv("ENABLE_AUTO_COLLECTION", "true").lower() == "true"
DATA_COLLECTION_INTERVAL_MINUTES = int(os.getenv("DATA_COLLECTION_INTERVAL_MINUTES", "15"))
INTELLIGENCE_PROCESSING_INTERVAL_MINUTES = int(os.getenv("INTELLIGENCE_PROCESSING_INTERVAL_MINUTES", "5"))
THREAT_MONITORING_INTERVAL_MINUTES = int(os.getenv("THREAT_MONITORING_INTERVAL_MINUTES", "5"))
NEWS_COLLECTION_INTERVAL_MINUTES = int(os.getenv("NEWS_COLLECTION_INTERVAL_MINUTES", "60"))
ENABLE_NEWS_COLLECTION = os.getenv("ENABLE_NEWS_COLLECTION", "true").lower() == "true"
DAILY_ANALYTICS_ENABLED = os.getenv("DAILY_ANALYTICS_ENABLED", "true").lower() == "true"
WEEKLY_CLEANUP_ENABLED = os.getenv("WEEKLY_CLEANUP_ENABLED", "true").lower() == "true"

def get_beat_schedule():
    """
    Generate beat schedule based on environment configuration
    """
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

# Add beat schedule to the imported celery instance
celery_app.conf.beat_schedule = get_beat_schedule()

def main():
    """
    Main method to enable debug mode and start Celery worker
    """
    from celery.utils.log import get_task_logger
    
    # Set debug logging level
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    
    # Initialize our logging system
    log_level = "DEBUG" if debug_mode else "INFO"
    setup_app_logging("celery_main", log_level)
    
    logger = get_task_logger(__name__)
    
    # Initialize database connection
    from app.core.database import connect_to_mongo
    import asyncio
    
    logger.info("🔗 Initializing database connection...")
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Connect to database
        loop.run_until_complete(connect_to_mongo())
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
    
    if debug_mode:
        # Enable Celery debug logging
        celery_app.conf.update(
            worker_log_level="DEBUG",
            worker_hijack_root_logger=False,
            worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
            worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"
        )
        
        print("🔧 Celery Debug Mode Enabled")
        print(f"📊 Auto Collection: {ENABLE_AUTO_COLLECTION}")
        print(f"⏰ Data Collection Interval: {DATA_COLLECTION_INTERVAL_MINUTES} minutes")
        print(f"🧠 Intelligence Processing Interval: {INTELLIGENCE_PROCESSING_INTERVAL_MINUTES} minutes")
        print(f"⚠️  Threat Monitoring Interval: {THREAT_MONITORING_INTERVAL_MINUTES} minutes")
        print(f"📰 News Collection: {ENABLE_NEWS_COLLECTION} (every {NEWS_COLLECTION_INTERVAL_MINUTES} minutes)")
        print(f"📈 Daily Analytics: {DAILY_ANALYTICS_ENABLED}")
        print(f"🧹 Weekly Cleanup: {WEEKLY_CLEANUP_ENABLED}")
        print(f"🔗 MongoDB URL: {mongodb_url}")
        
        # Print active beat schedule
        schedule = get_beat_schedule()
        print(f"📅 Active Scheduled Tasks: {len(schedule)}")
        for task_name, task_config in schedule.items():
            interval = task_config['schedule']
            if interval >= 3600:
                interval_str = f"{interval/3600:.1f} hours"
            elif interval >= 60:
                interval_str = f"{interval/60:.1f} minutes"
            else:
                interval_str = f"{interval} seconds"
            print(f"  - {task_name}: every {interval_str}")
    
    # Start Celery worker
    print("🚀 Starting Celery Worker...")
    celery_app.start(argv=[
        'worker',
        '--loglevel=debug' if debug_mode else '--loglevel=info',
        '--concurrency=4',
        '--queues=default,data_collection,intelligence,monitoring',
        '--pool=solo' if os.name == 'nt' else '--pool=prefork'  # Use solo pool on Windows
    ])
    
    return celery_app

if __name__ == "__main__":
    # Start Celery worker when run directly
    main()