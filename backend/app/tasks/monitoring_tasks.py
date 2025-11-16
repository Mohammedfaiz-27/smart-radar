"""
Celery tasks for monitoring, alerting, and system maintenance
"""
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta
from celery import Task
from app.core.celery_instance import celery_app
from app.services.social_post_service import SocialPostService
from app.services.websocket_manager import WebSocketManager

class AsyncTask(Task):
    """Base task class for async operations"""
    def __call__(self, *args, **kwargs):
        # Try to use existing event loop if available
        try:
            loop = asyncio.get_running_loop()
            # If we're already in an event loop, we can't use run_until_complete
            # This shouldn't happen in Celery, but let's be safe
            return asyncio.create_task(self.run(*args, **kwargs))
        except RuntimeError:
            # No running loop, create a new one (normal Celery case)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.run(*args, **kwargs))
            finally:
                # Don't close the loop immediately - give Motor time to clean up
                try:
                    # Wait for any pending tasks to complete
                    pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
                    if pending:
                        loop.run_until_complete(asyncio.sleep(0.1))  # Brief wait
                        # Check again for remaining tasks
                        pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
                        for task in pending:
                            task.cancel()
                        if pending:
                            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass  # Ignore cleanup errors
                finally:
                    loop.close()

@celery_app.task(base=AsyncTask, bind=True)
async def monitor_threat_posts(self):
    """
    Monitor for new threat posts and send real-time alerts
    """
    try:
        post_service = SocialPostService()
        
        # Get threat posts from the last 10 minutes
        recent_time = datetime.utcnow() - timedelta(minutes=10)
        threat_posts = await post_service.get_threat_posts()
        
        # Filter for very recent threats
        new_threats = [
            post for post in threat_posts 
            if post.collected_at >= recent_time
        ]
        
        if not new_threats:
            return {
                "status": "success",
                "new_threats": 0,
                "message": "No new threats detected"
            }
        
        # Categorize threats by severity
        critical_threats = [p for p in new_threats if p.intelligence.threat_level == "critical"]
        high_threats = [p for p in new_threats if p.intelligence.threat_level == "high"]
        medium_threats = [p for p in new_threats if p.intelligence.threat_level == "medium"]
        
        # Send real-time alerts
        websocket_manager = WebSocketManager()
        
        for threat in critical_threats:
            await websocket_manager.broadcast_message({
                "type": "critical_threat_alert",
                "data": {
                    "post_id": threat.id,
                    "platform": threat.platform,
                    "author": threat.author.display_name,
                    "content_preview": threat.content.text[:200],
                    "sentiment_score": threat.intelligence.sentiment_score,
                    "engagement": threat.engagement.dict(),
                    "timestamp": threat.collected_at.isoformat(),
                    "alert_level": "CRITICAL"
                }
            })
        
        # Send summary alert for all new threats
        await websocket_manager.broadcast_message({
            "type": "threat_monitoring_update",
            "data": {
                "total_new_threats": len(new_threats),
                "critical_count": len(critical_threats),
                "high_count": len(high_threats),
                "medium_count": len(medium_threats),
                "monitoring_period": "10 minutes",
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        return {
            "status": "success",
            "new_threats": len(new_threats),
            "critical_threats": len(critical_threats),
            "high_threats": len(high_threats),
            "medium_threats": len(medium_threats),
            "monitoring_period": "10 minutes"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "new_threats": 0
        }

@celery_app.task(base=AsyncTask, bind=True)
async def aggregate_daily_analytics(self):
    """
    Generate daily analytics aggregation
    """
    try:
        post_service = SocialPostService()
        
        # Get posts from the last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_posts = await post_service.get_posts(skip=0, limit=10000)
        
        # Filter posts from last 24 hours
        daily_posts = [
            post for post in recent_posts 
            if post.collected_at >= yesterday
        ]
        
        # Calculate analytics
        total_posts = len(daily_posts)
        threat_posts = [p for p in daily_posts if p.intelligence.is_threat]
        
        # Platform breakdown
        platform_stats = {}
        for post in daily_posts:
            if post.platform not in platform_stats:
                platform_stats[post.platform] = {
                    "total": 0,
                    "threats": 0,
                    "positive_sentiment": 0,
                    "negative_sentiment": 0,
                    "total_engagement": 0
                }
            
            stats = platform_stats[post.platform]
            stats["total"] += 1
            
            if post.intelligence.is_threat:
                stats["threats"] += 1
            
            if post.intelligence.sentiment_score > 0:
                stats["positive_sentiment"] += 1
            elif post.intelligence.sentiment_score < 0:
                stats["negative_sentiment"] += 1
            
            # Total engagement
            engagement = post.engagement
            stats["total_engagement"] += (engagement.likes + engagement.shares + 
                                        engagement.comments + engagement.retweets)
        
        # Sentiment distribution
        sentiment_scores = [p.intelligence.sentiment_score for p in daily_posts]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        # Threat level distribution
        threat_levels = {}
        for post in threat_posts:
            level = post.intelligence.threat_level
            threat_levels[level] = threat_levels.get(level, 0) + 1
        
        analytics_summary = {
            "date": yesterday.date().isoformat(),
            "total_posts": total_posts,
            "threat_posts": len(threat_posts),
            "threat_percentage": (len(threat_posts) / total_posts) * 100 if total_posts > 0 else 0,
            "avg_sentiment_score": avg_sentiment,
            "platform_breakdown": platform_stats,
            "threat_level_distribution": threat_levels,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Store analytics (would save to database in real implementation)
        
        # Send analytics update
        websocket_manager = WebSocketManager()
        await websocket_manager.broadcast_message({
            "type": "daily_analytics_ready",
            "data": analytics_summary
        })
        
        return {
            "status": "success",
            **analytics_summary
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "total_posts": 0
        }

@celery_app.task(base=AsyncTask, bind=True)
async def cleanup_old_data(self):
    """
    Clean up old data to manage database size
    """
    try:
        from app.core.database import get_database
        db = get_database()
        
        # Define retention periods
        retention_periods = {
            "social_posts": 30,  # Keep posts for 30 days
            "response_logs": 90,  # Keep response logs for 90 days
        }
        
        cleanup_results = {}
        
        for collection_name, days in retention_periods.items():
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            collection = db[collection_name]
            
            # Count documents to be deleted
            count_to_delete = await collection.count_documents({
                "collected_at": {"$lt": cutoff_date}
            })
            
            if count_to_delete > 0:
                # Delete old documents
                result = await collection.delete_many({
                    "collected_at": {"$lt": cutoff_date}
                })
                
                cleanup_results[collection_name] = {
                    "deleted_count": result.deleted_count,
                    "retention_days": days
                }
            else:
                cleanup_results[collection_name] = {
                    "deleted_count": 0,
                    "retention_days": days
                }
        
        total_deleted = sum(r["deleted_count"] for r in cleanup_results.values())
        
        # Log cleanup results
        print(f"Cleanup completed: {total_deleted} documents deleted")
        
        return {
            "status": "success",
            "total_deleted": total_deleted,
            "cleanup_results": cleanup_results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "total_deleted": 0
        }

@celery_app.task(base=AsyncTask, bind=True)
async def system_health_check(self):
    """
    Perform system health checks and send alerts if issues detected
    """
    try:
        from app.core.database import get_database
        
        health_status = {
            "database": "unknown",
            "api_keys": "unknown",
            "data_collection": "unknown",
            "overall": "unknown"
        }
        
        issues = []
        
        # Check database connectivity
        try:
            db = get_database()
            await db.admin.command('ping')
            health_status["database"] = "healthy"
        except Exception as e:
            health_status["database"] = "error"
            issues.append(f"Database connection failed: {str(e)}")
        
        # Check API key configuration
        import os
        api_keys = {
            "X_RAPIDAPI_KEY": os.getenv("X_RAPIDAPI_KEY"),
            "FACEBOOK_RAPIDAPI_KEY": os.getenv("FACEBOOK_RAPIDAPI_KEY"),
            "YOUTUBE_API_KEY": os.getenv("YOUTUBE_API_KEY"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY")
        }
        
        missing_keys = [key for key, value in api_keys.items() if not value or value.startswith("your_")]
        
        if missing_keys:
            health_status["api_keys"] = "warning"
            issues.append(f"Missing or placeholder API keys: {', '.join(missing_keys)}")
        else:
            health_status["api_keys"] = "healthy"
        
        # Check recent data collection
        try:
            post_service = SocialPostService()
            recent_posts = await post_service.get_posts(skip=0, limit=10)
            
            if recent_posts:
                latest_post_age = datetime.utcnow() - recent_posts[0].collected_at
                if latest_post_age.total_seconds() > 3600:  # 1 hour
                    health_status["data_collection"] = "warning"
                    issues.append("No data collected in the last hour")
                else:
                    health_status["data_collection"] = "healthy"
            else:
                health_status["data_collection"] = "warning"
                issues.append("No posts found in database")
                
        except Exception as e:
            health_status["data_collection"] = "error"
            issues.append(f"Data collection check failed: {str(e)}")
        
        # Determine overall health
        if any(status == "error" for status in health_status.values()):
            health_status["overall"] = "error"
        elif any(status == "warning" for status in health_status.values()):
            health_status["overall"] = "warning"
        else:
            health_status["overall"] = "healthy"
        
        # Send health update
        websocket_manager = WebSocketManager()
        await websocket_manager.broadcast_message({
            "type": "system_health_update",
            "data": {
                "health_status": health_status,
                "issues": issues,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        return {
            "status": "success",
            "health_status": health_status,
            "issues": issues,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "health_status": {"overall": "error"}
        }