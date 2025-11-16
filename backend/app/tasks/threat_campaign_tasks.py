"""
Celery tasks for threat campaign detection and management
"""
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta
from celery import Task

from app.core.celery_instance import celery_app
from app.services.threat_clustering_service import ThreatClusteringService
from app.services.websocket_manager import WebSocketManager


class AsyncTask(Task):
    """Base task class for async operations"""
    def __call__(self, *args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.run_async(*args, **kwargs))
        finally:
            loop.close()


@celery_app.task(base=AsyncTask, bind=True)
async def detect_threat_campaigns(self):
    """
    Detect new threat campaigns from recent threats
    Runs every 15 minutes
    """
    try:
        clustering_service = ThreatClusteringService()
        
        # Detect new campaigns
        new_campaign_ids = await clustering_service.detect_threat_campaigns()
        
        # Update existing campaigns with new threats
        updated_campaigns = await clustering_service.update_existing_campaigns()
        
        result = {
            "status": "success",
            "new_campaigns": len(new_campaign_ids),
            "updated_campaigns": updated_campaigns,
            "campaign_ids": new_campaign_ids,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send WebSocket notifications for new campaigns
        if new_campaign_ids:
            await _notify_new_campaigns(new_campaign_ids)
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "new_campaigns": 0,
            "updated_campaigns": 0,
            "timestamp": datetime.utcnow().isoformat()
        }


@celery_app.task(base=AsyncTask, bind=True)
async def update_campaign_metrics(self, campaign_id: str):
    """
    Update metrics for a specific campaign
    """
    try:
        clustering_service = ThreatClusteringService()
        
        # Get campaign
        campaign = await clustering_service.campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            return {"status": "error", "error": "Campaign not found"}
        
        # Get all posts for this campaign
        post_ids = campaign.get("post_ids", [])
        posts = await clustering_service.posts_collection.find({
            "_id": {"$in": [ObjectId(pid) for pid in post_ids]}
        }).to_list(length=None)
        
        # Calculate updated metrics
        updated_metrics = await clustering_service._calculate_updated_metrics(posts)
        
        # Update campaign
        await clustering_service.campaigns_collection.update_one(
            {"_id": ObjectId(campaign_id)},
            {
                "$set": {
                    "last_updated_at": datetime.utcnow(),
                    **updated_metrics
                }
            }
        )
        
        return {
            "status": "success",
            "campaign_id": campaign_id,
            "updated_metrics": updated_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "campaign_id": campaign_id,
            "error": str(e)
        }


@celery_app.task(base=AsyncTask, bind=True)
async def calculate_campaign_velocity(self, campaign_id: str):
    """
    Calculate and update campaign velocity
    """
    try:
        clustering_service = ThreatClusteringService()
        
        # Get campaign posts from last 24 hours
        campaign = await clustering_service.campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            return {"status": "error", "error": "Campaign not found"}
        
        # Get recent posts (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        recent_posts = await clustering_service.posts_collection.find({
            "threat_campaign_id": campaign_id,
            "collected_at": {"$gte": cutoff_time}
        }).to_list(length=None)
        
        # Calculate velocity (posts per hour)
        post_count = len(recent_posts)
        velocity = post_count / 24  # Posts per hour over 24 hours
        
        # Update campaign velocity
        await clustering_service.campaigns_collection.update_one(
            {"_id": ObjectId(campaign_id)},
            {
                "$set": {
                    "campaign_velocity": velocity,
                    "last_updated_at": datetime.utcnow()
                }
            }
        )
        
        # Check if velocity indicates escalation
        escalation_threshold = 5.0  # 5 posts per hour
        if velocity > escalation_threshold:
            await _notify_campaign_escalation(campaign_id, velocity)
        
        return {
            "status": "success",
            "campaign_id": campaign_id,
            "velocity": velocity,
            "recent_posts": post_count,
            "escalated": velocity > escalation_threshold
        }
        
    except Exception as e:
        return {
            "status": "error",
            "campaign_id": campaign_id,
            "error": str(e)
        }


@celery_app.task(base=AsyncTask, bind=True)
async def monitor_campaign_activity(self):
    """
    Monitor all active campaigns for activity changes
    Runs every hour
    """
    try:
        clustering_service = ThreatClusteringService()
        
        # Get all active campaigns
        active_campaigns = await clustering_service.campaigns_collection.find({
            "status": "active"
        }).to_list(length=None)
        
        results = []
        escalated_campaigns = []
        
        for campaign in active_campaigns:
            campaign_id = str(campaign["_id"])
            
            # Calculate velocity for each campaign
            velocity_result = await calculate_campaign_velocity.delay(campaign_id)
            
            # Check for escalation
            if velocity_result.get("escalated", False):
                escalated_campaigns.append({
                    "campaign_id": campaign_id,
                    "name": campaign.get("name", "Unknown Campaign"),
                    "velocity": velocity_result.get("velocity", 0)
                })
            
            results.append(velocity_result)
        
        # Send batch notification if there are escalated campaigns
        if escalated_campaigns:
            await _notify_batch_escalations(escalated_campaigns)
        
        return {
            "status": "success",
            "monitored_campaigns": len(active_campaigns),
            "escalated_campaigns": len(escalated_campaigns),
            "escalations": escalated_campaigns,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "monitored_campaigns": 0,
            "escalated_campaigns": 0
        }


@celery_app.task(base=AsyncTask, bind=True)
async def cleanup_inactive_campaigns(self):
    """
    Clean up campaigns that haven't had activity for a while
    Runs daily
    """
    try:
        clustering_service = ThreatClusteringService()
        
        # Mark campaigns as inactive if no activity for 7 days
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        
        result = await clustering_service.campaigns_collection.update_many(
            {
                "status": "active",
                "last_updated_at": {"$lt": cutoff_time}
            },
            {
                "$set": {
                    "status": "monitoring",
                    "last_updated_at": datetime.utcnow()
                }
            }
        )
        
        # Mark campaigns as resolved if no activity for 30 days
        resolved_cutoff = datetime.utcnow() - timedelta(days=30)
        
        resolved_result = await clustering_service.campaigns_collection.update_many(
            {
                "status": {"$in": ["active", "monitoring"]},
                "last_updated_at": {"$lt": resolved_cutoff}
            },
            {
                "$set": {
                    "status": "resolved",
                    "last_updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "status": "success",
            "moved_to_monitoring": result.modified_count,
            "resolved_campaigns": resolved_result.modified_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "moved_to_monitoring": 0,
            "resolved_campaigns": 0
        }


@celery_app.task(base=AsyncTask, bind=True)
async def generate_campaign_report(self, campaign_id: str):
    """
    Generate a detailed report for a specific campaign
    """
    try:
        clustering_service = ThreatClusteringService()
        
        # Get campaign details
        campaign = await clustering_service.campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            return {"status": "error", "error": "Campaign not found"}
        
        # Get all campaign posts
        post_ids = campaign.get("post_ids", [])
        posts = await clustering_service.posts_collection.find({
            "_id": {"$in": [ObjectId(pid) for pid in post_ids]}
        }).to_list(length=None)
        
        # Generate report data
        report = {
            "campaign_id": campaign_id,
            "campaign_name": campaign.get("name", "Unknown"),
            "description": campaign.get("description", ""),
            "threat_level": campaign.get("threat_level", "low"),
            "status": campaign.get("status", "active"),
            "created_at": campaign.get("created_at"),
            "first_detected_at": campaign.get("first_detected_at"),
            "last_updated_at": campaign.get("last_updated_at"),
            
            # Statistics
            "total_posts": len(posts),
            "total_engagement": campaign.get("total_engagement", 0),
            "average_sentiment": campaign.get("average_sentiment", 0),
            "campaign_velocity": campaign.get("campaign_velocity", 0),
            "reach_estimate": campaign.get("reach_estimate", 0),
            
            # Key elements
            "keywords": campaign.get("keywords", []),
            "hashtags": campaign.get("hashtags", []),
            "participating_accounts": campaign.get("participating_accounts", []),
            
            # Platform breakdown
            "platform_breakdown": _calculate_platform_breakdown(posts),
            
            # Timeline
            "timeline": _generate_campaign_timeline(posts),
            
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return {
            "status": "success",
            "report": report
        }
        
    except Exception as e:
        return {
            "status": "error",
            "campaign_id": campaign_id,
            "error": str(e)
        }


# Helper functions for WebSocket notifications
async def _notify_new_campaigns(campaign_ids: List[str]):
    """Send WebSocket notification for new campaigns"""
    try:
        websocket_manager = WebSocketManager()
        
        for campaign_id in campaign_ids:
            await websocket_manager.broadcast_message({
                "type": "campaign_detected",
                "data": {
                    "campaign_id": campaign_id,
                    "message": "New threat campaign detected",
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
    except Exception as e:
        print(f"Error sending campaign notifications: {e}")


async def _notify_campaign_escalation(campaign_id: str, velocity: float):
    """Send WebSocket notification for campaign escalation"""
    try:
        websocket_manager = WebSocketManager()
        await websocket_manager.broadcast_message({
            "type": "campaign_escalation",
            "data": {
                "campaign_id": campaign_id,
                "velocity": velocity,
                "message": f"Campaign escalation detected: {velocity:.1f} posts/hour",
                "timestamp": datetime.utcnow().isoformat()
            }
        })
    except Exception as e:
        print(f"Error sending escalation notification: {e}")


async def _notify_batch_escalations(escalated_campaigns: List[Dict[str, Any]]):
    """Send batch notification for multiple escalated campaigns"""
    try:
        websocket_manager = WebSocketManager()
        await websocket_manager.broadcast_message({
            "type": "batch_campaign_escalations",
            "data": {
                "escalated_count": len(escalated_campaigns),
                "campaigns": escalated_campaigns,
                "message": f"{len(escalated_campaigns)} campaigns showing increased activity",
                "timestamp": datetime.utcnow().isoformat()
            }
        })
    except Exception as e:
        print(f"Error sending batch escalation notification: {e}")


def _calculate_platform_breakdown(posts: List[Dict[str, Any]]) -> Dict[str, int]:
    """Calculate breakdown of posts by platform"""
    platform_counts = {}
    for post in posts:
        platform = post.get("platform", "unknown")
        platform_counts[platform] = platform_counts.get(platform, 0) + 1
    return platform_counts


def _generate_campaign_timeline(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate timeline of campaign activity"""
    timeline = []
    
    # Sort posts by time
    sorted_posts = sorted(posts, key=lambda x: x.get("posted_at", datetime.min))
    
    # Group by hour
    current_hour = None
    hour_count = 0
    
    for post in sorted_posts:
        posted_at = post.get("posted_at")
        if isinstance(posted_at, str):
            posted_at = datetime.fromisoformat(posted_at.replace('Z', '+00:00'))
        
        post_hour = posted_at.replace(minute=0, second=0, microsecond=0)
        
        if current_hour != post_hour:
            if current_hour is not None:
                timeline.append({
                    "timestamp": current_hour.isoformat(),
                    "post_count": hour_count
                })
            current_hour = post_hour
            hour_count = 1
        else:
            hour_count += 1
    
    # Add final hour
    if current_hour is not None:
        timeline.append({
            "timestamp": current_hour.isoformat(),
            "post_count": hour_count
        })
    
    return timeline


# Import ObjectId at the top level to avoid issues
from bson import ObjectId