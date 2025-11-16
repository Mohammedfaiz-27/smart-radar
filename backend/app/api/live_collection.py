"""
Live Data Collection API for SMART RADAR v25.0
Real-time data collection from all platforms
"""
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Dict, Any

from app.services.live_data_collection_service import LiveDataCollectionService

router = APIRouter()

# Global service instance
collection_service = LiveDataCollectionService()

@router.post("/start")
async def start_live_collection(
    background_tasks: BackgroundTasks,
    duration_minutes: int = Query(60, ge=1, le=1440, description="Collection duration in minutes")
) -> Dict[str, Any]:
    """Start live data collection from all platforms"""
    try:
        # Start collection in background
        task = asyncio.create_task(collection_service.start_live_collection(duration_minutes))
        
        return {
            "status": "started",
            "message": f"Live data collection started for {duration_minutes} minutes",
            "duration_minutes": duration_minutes,
            "platforms": ["X", "Facebook", "YouTube", "News Sites"],
            "collection_interval": "30 seconds"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_live_collection() -> Dict[str, str]:
    """Stop ongoing live collection"""
    try:
        return await collection_service.stop_collection()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_collection_status() -> Dict[str, Any]:
    """Get current collection status"""
    try:
        return collection_service.get_collection_status()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/collect-batch")
async def collect_single_batch() -> Dict[str, Any]:
    """Collect a single batch of data immediately"""
    try:
        stats = await collection_service.collect_single_batch()
        
        return {
            "status": "completed",
            "message": "Single batch collection completed",
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))