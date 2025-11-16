"""
API endpoints for threat campaign management
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from bson import ObjectId
from pydantic import BaseModel

from app.core.database import get_database
from app.services.threat_clustering_service import ThreatClusteringService
from app.models.threat_campaign import (
    ThreatCampaignResponse, 
    ThreatCampaignUpdate, 
    CampaignStats
)
from app.tasks.threat_campaign_tasks import (
    detect_threat_campaigns,
    update_campaign_metrics,
    generate_campaign_report
)

router = APIRouter()

# Request/Response models
class CampaignAcknowledgeRequest(BaseModel):
    acknowledged_by: str
    notes: Optional[str] = None

class CampaignPostsResponse(BaseModel):
    campaign_id: str
    posts: List[Dict[str, Any]]
    total_posts: int

class CampaignReportResponse(BaseModel):
    campaign_id: str
    report: Dict[str, Any]
    generated_at: datetime


@router.get("/", response_model=List[ThreatCampaignResponse])
async def get_threat_campaigns(
    status: Optional[str] = Query(None, description="Filter by campaign status"),
    threat_level: Optional[str] = Query(None, description="Filter by threat level"),
    cluster_type: Optional[str] = Query(None, description="Filter by cluster type"),
    limit: int = Query(50, ge=1, le=1000),
    skip: int = Query(0, ge=0)
):
    """Get list of threat campaigns with optional filters"""
    try:
        clustering_service = ThreatClusteringService()
        
        # Build query
        query = {}
        if status:
            query["status"] = status
        if threat_level:
            query["threat_level"] = threat_level
        if cluster_type:
            query["cluster_type"] = cluster_type
        
        # Get campaigns
        cursor = clustering_service.campaigns_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        campaigns = await cursor.to_list(length=limit)
        
        # Format response
        response = []
        for campaign in campaigns:
            campaign_data = campaign.copy()
            campaign_data["id"] = str(campaign_data.pop("_id"))
            response.append(ThreatCampaignResponse(**campaign_data))
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get campaigns: {str(e)}")


@router.get("/active", response_model=List[ThreatCampaignResponse])
async def get_active_campaigns():
    """Get only active threat campaigns"""
    return await get_threat_campaigns(status="active")


@router.get("/stats", response_model=CampaignStats)
async def get_campaign_stats():
    """Get overall campaign statistics"""
    try:
        clustering_service = ThreatClusteringService()
        stats = await clustering_service.get_campaign_stats()
        return CampaignStats(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get campaign stats: {str(e)}")


@router.get("/{campaign_id}", response_model=ThreatCampaignResponse)
async def get_campaign(campaign_id: str):
    """Get specific campaign details"""
    try:
        if not ObjectId.is_valid(campaign_id):
            raise HTTPException(status_code=400, detail="Invalid campaign ID")
        
        clustering_service = ThreatClusteringService()
        campaign = await clustering_service.campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        campaign["id"] = str(campaign.pop("_id"))
        return ThreatCampaignResponse(**campaign)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get campaign: {str(e)}")


@router.put("/{campaign_id}", response_model=ThreatCampaignResponse)
async def update_campaign(campaign_id: str, update_data: ThreatCampaignUpdate):
    """Update campaign details"""
    try:
        if not ObjectId.is_valid(campaign_id):
            raise HTTPException(status_code=400, detail="Invalid campaign ID")
        
        clustering_service = ThreatClusteringService()
        
        # Check if campaign exists
        existing_campaign = await clustering_service.campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
        if not existing_campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Prepare update data
        update_dict = update_data.dict(exclude_unset=True)
        update_dict["last_updated_at"] = datetime.utcnow()
        
        # Update campaign
        result = await clustering_service.campaigns_collection.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": update_dict}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes made to campaign")
        
        # Get updated campaign
        updated_campaign = await clustering_service.campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
        updated_campaign["id"] = str(updated_campaign.pop("_id"))
        
        return ThreatCampaignResponse(**updated_campaign)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update campaign: {str(e)}")


@router.post("/{campaign_id}/acknowledge")
async def acknowledge_campaign(campaign_id: str, request: CampaignAcknowledgeRequest):
    """Mark campaign as acknowledged"""
    try:
        if not ObjectId.is_valid(campaign_id):
            raise HTTPException(status_code=400, detail="Invalid campaign ID")
        
        clustering_service = ThreatClusteringService()
        
        # Check if campaign exists
        campaign = await clustering_service.campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Update campaign status
        update_data = {
            "status": "acknowledged",
            "acknowledged_at": datetime.utcnow(),
            "acknowledged_by": request.acknowledged_by,
            "last_updated_at": datetime.utcnow()
        }
        
        if request.notes:
            update_data["acknowledgment_notes"] = request.notes
        
        await clustering_service.campaigns_collection.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": update_data}
        )
        
        return {
            "message": "Campaign acknowledged successfully",
            "campaign_id": campaign_id,
            "acknowledged_by": request.acknowledged_by,
            "acknowledged_at": update_data["acknowledged_at"].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge campaign: {str(e)}")


@router.get("/{campaign_id}/posts", response_model=CampaignPostsResponse)
async def get_campaign_posts(
    campaign_id: str,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0)
):
    """Get posts associated with a campaign"""
    try:
        if not ObjectId.is_valid(campaign_id):
            raise HTTPException(status_code=400, detail="Invalid campaign ID")
        
        clustering_service = ThreatClusteringService()
        
        # Check if campaign exists
        campaign = await clustering_service.campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get campaign posts
        cursor = clustering_service.posts_collection.find({
            "threat_campaign_id": campaign_id
        }).sort("collected_at", -1).skip(skip).limit(limit)
        
        posts = await cursor.to_list(length=limit)
        
        # Get total count
        total_posts = await clustering_service.posts_collection.count_documents({
            "threat_campaign_id": campaign_id
        })
        
        # Format posts
        formatted_posts = []
        for post in posts:
            post_data = post.copy()
            post_data["id"] = str(post_data.pop("_id"))
            post_data["cluster_id"] = str(post_data["cluster_id"])
            formatted_posts.append(post_data)
        
        return CampaignPostsResponse(
            campaign_id=campaign_id,
            posts=formatted_posts,
            total_posts=total_posts
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get campaign posts: {str(e)}")


@router.post("/{campaign_id}/report", response_model=CampaignReportResponse)
async def generate_campaign_report_endpoint(campaign_id: str, background_tasks: BackgroundTasks):
    """Generate detailed report for a campaign"""
    try:
        if not ObjectId.is_valid(campaign_id):
            raise HTTPException(status_code=400, detail="Invalid campaign ID")
        
        # Check if campaign exists
        db = get_database()
        campaign = await db.threat_campaigns.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Generate report (this could be done in background for large campaigns)
        report_result = await generate_campaign_report.delay(campaign_id)
        
        if report_result["status"] == "error":
            raise HTTPException(status_code=500, detail=report_result["error"])
        
        return CampaignReportResponse(
            campaign_id=campaign_id,
            report=report_result["report"],
            generated_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.post("/detect")
async def trigger_campaign_detection(background_tasks: BackgroundTasks):
    """Manually trigger threat campaign detection"""
    try:
        # Run detection in background
        background_tasks.add_task(detect_threat_campaigns.delay)
        
        return {
            "message": "Threat campaign detection triggered",
            "status": "processing",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger detection: {str(e)}")


@router.post("/{campaign_id}/update-metrics")
async def trigger_metrics_update(campaign_id: str, background_tasks: BackgroundTasks):
    """Manually trigger metrics update for a campaign"""
    try:
        if not ObjectId.is_valid(campaign_id):
            raise HTTPException(status_code=400, detail="Invalid campaign ID")
        
        # Check if campaign exists
        db = get_database()
        campaign = await db.threat_campaigns.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Update metrics in background
        background_tasks.add_task(update_campaign_metrics.delay, campaign_id)
        
        return {
            "message": f"Metrics update triggered for campaign {campaign_id}",
            "status": "processing",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger metrics update: {str(e)}")


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: str):
    """Delete a campaign (admin only - use with caution)"""
    try:
        if not ObjectId.is_valid(campaign_id):
            raise HTTPException(status_code=400, detail="Invalid campaign ID")
        
        clustering_service = ThreatClusteringService()
        
        # Check if campaign exists
        campaign = await clustering_service.campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Remove campaign_id from associated posts
        await clustering_service.posts_collection.update_many(
            {"threat_campaign_id": campaign_id},
            {"$unset": {"threat_campaign_id": ""}}
        )
        
        # Delete campaign
        result = await clustering_service.campaigns_collection.delete_one({"_id": ObjectId(campaign_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=500, detail="Failed to delete campaign")
        
        return {
            "message": f"Campaign {campaign_id} deleted successfully",
            "posts_updated": "Associated posts unlinked from campaign"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete campaign: {str(e)}")


@router.get("/{campaign_id}/timeline")
async def get_campaign_timeline(campaign_id: str):
    """Get campaign activity timeline"""
    try:
        if not ObjectId.is_valid(campaign_id):
            raise HTTPException(status_code=400, detail="Invalid campaign ID")
        
        clustering_service = ThreatClusteringService()
        
        # Get campaign posts
        posts = await clustering_service.posts_collection.find({
            "threat_campaign_id": campaign_id
        }).sort("posted_at", 1).to_list(length=None)
        
        if not posts:
            return {"timeline": [], "campaign_id": campaign_id}
        
        # Generate timeline
        from app.tasks.threat_campaign_tasks import _generate_campaign_timeline
        timeline = _generate_campaign_timeline(posts)
        
        return {
            "campaign_id": campaign_id,
            "timeline": timeline,
            "total_posts": len(posts),
            "time_span_hours": (
                posts[-1].get("posted_at", datetime.min) - 
                posts[0].get("posted_at", datetime.min)
            ).total_seconds() / 3600 if len(posts) > 1 else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get timeline: {str(e)}")