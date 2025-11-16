"""
API endpoints for managing Celery tasks
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.core.celery_instance import celery_app
from app.tasks.data_collection_tasks import (
    scheduled_data_collection,
    collect_cluster_data,
    platform_specific_collection,
    emergency_data_collection,
    bulk_historical_collection
)
from app.tasks.intelligence_tasks import (
    process_pending_intelligence,
    analyze_post_sentiment,
    batch_sentiment_analysis,
    deep_content_analysis,
    trend_analysis
)
from app.tasks.monitoring_tasks import (
    monitor_threat_posts,
    aggregate_daily_analytics,
    cleanup_old_data,
    system_health_check
)

router = APIRouter()

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class EmergencyCollectionRequest(BaseModel):
    keywords: List[str]
    priority: str = "high"

class HistoricalCollectionRequest(BaseModel):
    cluster_ids: List[str]
    start_date: str
    end_date: str

class PlatformCollectionRequest(BaseModel):
    platform: str
    keywords: List[str]
    cluster_id: Optional[str] = None

class BatchAnalysisRequest(BaseModel):
    post_ids: List[str]

class TrendAnalysisRequest(BaseModel):
    keywords: List[str]
    days_back: int = 7

# Data Collection Task Endpoints

@router.post("/data-collection/scheduled", response_model=TaskResponse)
async def trigger_scheduled_collection():
    """Trigger immediate data collection for all active clusters"""
    try:
        task = scheduled_data_collection.delay()
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message="Scheduled data collection task started"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

@router.post("/data-collection/cluster/{cluster_id}", response_model=TaskResponse)
async def trigger_cluster_collection(cluster_id: str, platforms: Optional[List[str]] = None):
    """Trigger data collection for a specific cluster"""
    try:
        task = collect_cluster_data.delay(cluster_id, platforms)
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message=f"Data collection started for cluster {cluster_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

@router.post("/data-collection/platform", response_model=TaskResponse)
async def trigger_platform_collection(request: PlatformCollectionRequest):
    """Trigger data collection for a specific platform"""
    try:
        task = platform_specific_collection.delay(
            request.platform,
            request.keywords,
            request.cluster_id
        )
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message=f"Data collection started for platform {request.platform}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

@router.post("/data-collection/emergency", response_model=TaskResponse)
async def trigger_emergency_collection(request: EmergencyCollectionRequest):
    """Trigger emergency data collection for crisis situations"""
    try:
        task = emergency_data_collection.delay(request.keywords, request.priority)
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message=f"Emergency data collection started for keywords: {', '.join(request.keywords)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

@router.post("/data-collection/historical", response_model=TaskResponse)
async def trigger_historical_collection(request: HistoricalCollectionRequest):
    """Trigger bulk historical data collection"""
    try:
        date_range = {
            "start": request.start_date,
            "end": request.end_date
        }
        task = bulk_historical_collection.delay(request.cluster_ids, date_range)
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message=f"Historical data collection started for {len(request.cluster_ids)} clusters"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

# Intelligence Task Endpoints

@router.post("/intelligence/process-pending", response_model=TaskResponse)
async def trigger_intelligence_processing():
    """Process intelligence analysis for pending posts"""
    try:
        task = process_pending_intelligence.delay()
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message="Intelligence processing task started"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

@router.post("/intelligence/analyze/{post_id}", response_model=TaskResponse)
async def trigger_post_analysis(post_id: str):
    """Analyze sentiment for a specific post"""
    try:
        task = analyze_post_sentiment.delay(post_id)
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message=f"Sentiment analysis started for post {post_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

@router.post("/intelligence/batch-analysis", response_model=TaskResponse)
async def trigger_batch_analysis(request: BatchAnalysisRequest):
    """Batch sentiment analysis for multiple posts"""
    try:
        task = batch_sentiment_analysis.delay(request.post_ids)
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message=f"Batch analysis started for {len(request.post_ids)} posts"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

@router.post("/intelligence/deep-analysis/{cluster_id}", response_model=TaskResponse)
async def trigger_deep_analysis(cluster_id: str, time_range_hours: int = 24):
    """Perform deep content analysis for a cluster"""
    try:
        task = deep_content_analysis.delay(cluster_id, time_range_hours)
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message=f"Deep analysis started for cluster {cluster_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

@router.post("/intelligence/trend-analysis", response_model=TaskResponse)
async def trigger_trend_analysis(request: TrendAnalysisRequest):
    """Analyze sentiment trends for keywords"""
    try:
        task = trend_analysis.delay(request.keywords, request.days_back)
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message=f"Trend analysis started for keywords: {', '.join(request.keywords)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

# Monitoring Task Endpoints

@router.post("/monitoring/threat-monitor", response_model=TaskResponse)
async def trigger_threat_monitoring():
    """Trigger immediate threat monitoring check"""
    try:
        task = monitor_threat_posts.delay()
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message="Threat monitoring task started"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

@router.post("/monitoring/daily-analytics", response_model=TaskResponse)
async def trigger_daily_analytics():
    """Trigger daily analytics aggregation"""
    try:
        task = aggregate_daily_analytics.delay()
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message="Daily analytics aggregation started"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

@router.post("/monitoring/cleanup", response_model=TaskResponse)
async def trigger_data_cleanup():
    """Trigger data cleanup task"""
    try:
        task = cleanup_old_data.delay()
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message="Data cleanup task started"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

@router.post("/monitoring/health-check", response_model=TaskResponse)
async def trigger_health_check():
    """Trigger system health check"""
    try:
        task = system_health_check.delay()
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message="System health check started"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

# Task Management Endpoints

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a specific task"""
    try:
        task_result = celery_app.AsyncResult(task_id)
        
        return {
            "task_id": task_id,
            "status": task_result.status,
            "result": task_result.result if task_result.ready() else None,
            "info": task_result.info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")

@router.get("/active")
async def get_active_tasks():
    """Get list of currently active tasks"""
    try:
        # Get active tasks from Celery
        active_tasks = celery_app.control.inspect().active()
        
        if not active_tasks:
            return {"active_tasks": [], "count": 0}
        
        # Flatten the tasks from all workers
        all_tasks = []
        for worker, tasks in active_tasks.items():
            for task in tasks:
                task["worker"] = worker
                all_tasks.append(task)
        
        return {
            "active_tasks": all_tasks,
            "count": len(all_tasks),
            "workers": list(active_tasks.keys())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active tasks: {str(e)}")

@router.get("/stats")
async def get_task_stats():
    """Get task execution statistics"""
    try:
        stats = celery_app.control.inspect().stats()
        
        return {
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task stats: {str(e)}")

@router.post("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a running task"""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        
        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": f"Task {task_id} has been cancelled"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")

@router.get("/queues")
async def get_queue_lengths():
    """Get the length of task queues"""
    try:
        # This would require connecting to Redis to get queue lengths
        # For now, return a placeholder
        return {
            "queues": {
                "data_collection": 0,
                "intelligence": 0,
                "monitoring": 0,
                "default": 0
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue lengths: {str(e)}")