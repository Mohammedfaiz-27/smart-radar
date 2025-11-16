"""
API endpoints for data collection
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.services.data_collection_service import DataCollectionService
from app.services.cluster_service import ClusterService

router = APIRouter()

class CollectionRequest(BaseModel):
    cluster_id: str
    platforms: Optional[List[str]] = ["x", "facebook", "youtube"]

class BatchCollectionRequest(BaseModel):
    cluster_ids: List[str]
    platforms: Optional[List[str]] = ["x", "facebook", "youtube"]

class CollectionResponse(BaseModel):
    cluster_id: str
    collected_posts: int
    post_ids: List[str]
    status: str

@router.post("/collect/{cluster_id}", response_model=CollectionResponse)
async def collect_posts_for_cluster(
    cluster_id: str,
    request: CollectionRequest,
    background_tasks: BackgroundTasks
):
    """Collect posts for a specific cluster"""
    try:
        # Get cluster information
        cluster_service = ClusterService()
        cluster = await cluster_service.get_cluster(cluster_id)
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        
        # Start collection
        async with DataCollectionService() as collection_service:
            post_ids = await collection_service.collect_posts_for_cluster(
                cluster_id=cluster_id,
                keywords=cluster.keywords,
                platforms=request.platforms
            )
        
        return CollectionResponse(
            cluster_id=cluster_id,
            collected_posts=len(post_ids),
            post_ids=post_ids,
            status="completed"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Collection failed: {str(e)}")

@router.post("/collect/batch", response_model=List[CollectionResponse])
async def collect_posts_batch(
    request: BatchCollectionRequest,
    background_tasks: BackgroundTasks
):
    """Collect posts for multiple clusters"""
    try:
        cluster_service = ClusterService()
        collection_service = DataCollectionService()
        
        # Get cluster data
        clusters = []
        for cluster_id in request.cluster_ids:
            cluster = await cluster_service.get_cluster(cluster_id)
            if cluster:
                clusters.append({
                    "id": cluster_id,
                    "keywords": cluster.keywords,
                    "platforms": request.platforms
                })
        
        if not clusters:
            raise HTTPException(status_code=404, detail="No valid clusters found")
        
        # Collect posts
        async with collection_service:
            results = await collection_service.collect_posts_batch(clusters)
        
        # Format response
        responses = []
        for cluster_id, post_ids in results.items():
            responses.append(CollectionResponse(
                cluster_id=cluster_id,
                collected_posts=len(post_ids),
                post_ids=post_ids,
                status="completed" if post_ids else "failed"
            ))
        
        return responses
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch collection failed: {str(e)}")

@router.post("/collect/start-background/{cluster_id}")
async def start_background_collection(
    cluster_id: str,
    request: CollectionRequest,
    background_tasks: BackgroundTasks
):
    """Start background collection for a cluster"""
    try:
        # Get cluster information
        cluster_service = ClusterService()
        cluster = await cluster_service.get_cluster(cluster_id)
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        
        # Add background task
        background_tasks.add_task(
            _background_collection_task,
            cluster_id,
            cluster.keywords,
            request.platforms
        )
        
        return {"message": f"Background collection started for cluster {cluster_id}"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start background collection: {str(e)}")

async def _background_collection_task(
    cluster_id: str,
    keywords: List[str],
    platforms: List[str]
):
    """Background task for post collection"""
    try:
        async with DataCollectionService() as collection_service:
            post_ids = await collection_service.collect_posts_for_cluster(
                cluster_id=cluster_id,
                keywords=keywords,
                platforms=platforms
            )
            print(f"Background collection completed for cluster {cluster_id}: {len(post_ids)} posts")
    except Exception as e:
        print(f"Background collection failed for cluster {cluster_id}: {e}")

@router.get("/status")
async def get_collection_status():
    """Get status of data collection services"""
    try:
        collection_service = DataCollectionService()
        
        status = {
            "x_configured": bool(collection_service.x_rapidapi_key),
            "facebook_configured": bool(collection_service.facebook_rapidapi_key),
            "youtube_configured": bool(collection_service.youtube_api_key),
            "available_platforms": []
        }
        
        if status["x_configured"]:
            status["available_platforms"].append("x")
        if status["facebook_configured"]:
            status["available_platforms"].append("facebook")
        if status["youtube_configured"]:
            status["available_platforms"].append("youtube")
        
        return status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")