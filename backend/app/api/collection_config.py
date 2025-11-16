"""
API endpoints for controlling automatic data collection configuration
"""
import os
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

router = APIRouter()

class CollectionConfig(BaseModel):
    """Collection configuration model"""
    enable_auto_collection: bool
    data_collection_interval_minutes: int
    intelligence_processing_interval_minutes: int
    threat_monitoring_interval_minutes: int
    daily_analytics_enabled: bool
    weekly_cleanup_enabled: bool

class CollectionConfigUpdate(BaseModel):
    """Collection configuration update model"""
    enable_auto_collection: Optional[bool] = None
    data_collection_interval_minutes: Optional[int] = None
    intelligence_processing_interval_minutes: Optional[int] = None
    threat_monitoring_interval_minutes: Optional[int] = None
    daily_analytics_enabled: Optional[bool] = None
    weekly_cleanup_enabled: Optional[bool] = None

@router.get("/config", response_model=CollectionConfig)
async def get_collection_config():
    """Get current collection configuration"""
    return CollectionConfig(
        enable_auto_collection=os.getenv("ENABLE_AUTO_COLLECTION", "true").lower() == "true",
        data_collection_interval_minutes=int(os.getenv("DATA_COLLECTION_INTERVAL_MINUTES", "30")),
        intelligence_processing_interval_minutes=int(os.getenv("INTELLIGENCE_PROCESSING_INTERVAL_MINUTES", "15")),
        threat_monitoring_interval_minutes=int(os.getenv("THREAT_MONITORING_INTERVAL_MINUTES", "5")),
        daily_analytics_enabled=os.getenv("DAILY_ANALYTICS_ENABLED", "true").lower() == "true",
        weekly_cleanup_enabled=os.getenv("WEEKLY_CLEANUP_ENABLED", "true").lower() == "true"
    )

@router.post("/config", response_model=CollectionConfig)
async def update_collection_config(config_update: CollectionConfigUpdate):
    """
    Update collection configuration
    Note: This updates environment variables in memory.
    For persistent changes, modify the .env file.
    """
    try:
        current_config = await get_collection_config()
        
        # Update configuration values
        if config_update.enable_auto_collection is not None:
            os.environ["ENABLE_AUTO_COLLECTION"] = str(config_update.enable_auto_collection).lower()
            
        if config_update.data_collection_interval_minutes is not None:
            if config_update.data_collection_interval_minutes < 1:
                raise HTTPException(status_code=400, detail="Data collection interval must be at least 1 minute")
            os.environ["DATA_COLLECTION_INTERVAL_MINUTES"] = str(config_update.data_collection_interval_minutes)
            
        if config_update.intelligence_processing_interval_minutes is not None:
            if config_update.intelligence_processing_interval_minutes < 1:
                raise HTTPException(status_code=400, detail="Intelligence processing interval must be at least 1 minute")
            os.environ["INTELLIGENCE_PROCESSING_INTERVAL_MINUTES"] = str(config_update.intelligence_processing_interval_minutes)
            
        if config_update.threat_monitoring_interval_minutes is not None:
            if config_update.threat_monitoring_interval_minutes < 1:
                raise HTTPException(status_code=400, detail="Threat monitoring interval must be at least 1 minute")
            os.environ["THREAT_MONITORING_INTERVAL_MINUTES"] = str(config_update.threat_monitoring_interval_minutes)
            
        if config_update.daily_analytics_enabled is not None:
            os.environ["DAILY_ANALYTICS_ENABLED"] = str(config_update.daily_analytics_enabled).lower()
            
        if config_update.weekly_cleanup_enabled is not None:
            os.environ["WEEKLY_CLEANUP_ENABLED"] = str(config_update.weekly_cleanup_enabled).lower()

        # Return updated configuration
        return await get_collection_config()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")

@router.post("/disable-auto-collection")
async def disable_auto_collection():
    """Quickly disable automatic data collection"""
    os.environ["ENABLE_AUTO_COLLECTION"] = "false"
    return {"message": "Automatic data collection disabled", "status": "success"}

@router.post("/enable-auto-collection")
async def enable_auto_collection():
    """Quickly enable automatic data collection"""
    os.environ["ENABLE_AUTO_COLLECTION"] = "true"
    return {"message": "Automatic data collection enabled", "status": "success"}

@router.get("/status")
async def get_collection_status():
    """Get current status of collection services"""
    # Get configuration from environment variables directly
    ENABLE_AUTO_COLLECTION = os.getenv("ENABLE_AUTO_COLLECTION", "true").lower() == "true"
    DATA_COLLECTION_INTERVAL_MINUTES = int(os.getenv("DATA_COLLECTION_INTERVAL_MINUTES", "15"))
    INTELLIGENCE_PROCESSING_INTERVAL_MINUTES = int(os.getenv("INTELLIGENCE_PROCESSING_INTERVAL_MINUTES", "5"))
    THREAT_MONITORING_INTERVAL_MINUTES = int(os.getenv("THREAT_MONITORING_INTERVAL_MINUTES", "5"))
    DAILY_ANALYTICS_ENABLED = os.getenv("DAILY_ANALYTICS_ENABLED", "true").lower() == "true"
    WEEKLY_CLEANUP_ENABLED = os.getenv("WEEKLY_CLEANUP_ENABLED", "true").lower() == "true"
    
    return {
        "automatic_collection_active": ENABLE_AUTO_COLLECTION,
        "data_collection_interval": f"{DATA_COLLECTION_INTERVAL_MINUTES} minutes",
        "intelligence_processing_interval": f"{INTELLIGENCE_PROCESSING_INTERVAL_MINUTES} minutes", 
        "threat_monitoring_interval": f"{THREAT_MONITORING_INTERVAL_MINUTES} minutes",
        "daily_analytics_enabled": DAILY_ANALYTICS_ENABLED,
        "weekly_cleanup_enabled": WEEKLY_CLEANUP_ENABLED,
        "next_collection_in": f"Check Celery Beat scheduler",
        "celery_worker_status": "Check worker health endpoint"
    }

@router.post("/restart-scheduler")
async def restart_scheduler():
    """
    Restart Celery Beat scheduler to apply new configuration
    Note: This requires manual restart of Celery Beat process
    """
    return {
        "message": "To apply new configuration, restart the Celery Beat process",
        "command": "celery -A app.core.celery_app beat --loglevel=info",
        "status": "restart_required"
    }