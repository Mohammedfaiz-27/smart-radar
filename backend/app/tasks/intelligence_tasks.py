"""
Celery tasks for intelligence processing and analysis
"""
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta
from celery import Task
from app.core.celery_instance import celery_app
from app.services.intelligence_service import IntelligenceService
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
async def process_pending_intelligence(self):
    """
    Process intelligence analysis for posts that don't have it yet
    """
    try:
        post_service = SocialPostService()
        intelligence_service = IntelligenceService()
        
        # Get posts without intelligence data (posts collected but not analyzed)
        # This would require a query to find posts where intelligence is null/empty
        
        # For now, let's get recent posts and re-analyze if needed
        recent_posts = await post_service.get_posts(
            skip=0,
            limit=2000
        )
        
        processed_count = 0
        threat_count = 0
        
        for post in recent_posts:
            try:
                # Re-analyze sentiment and threat level
                intelligence = await intelligence_service.analyze_post(
                    post.content.text,
                    post.engagement.dict()
                )
                
                processed_count += 1
                
                if intelligence.is_threat:
                    threat_count += 1
                    
                    # Send real-time threat alert
                    websocket_manager = WebSocketManager()
                    await websocket_manager.broadcast_message({
                        "type": "threat_detected",
                        "data": {
                            "post_id": post.id,
                            "platform": post.platform,
                            "threat_level": intelligence.threat_level,
                            "sentiment_score": intelligence.sentiment_score,
                            "engagement": post.engagement.dict()
                        }
                    })
                
            except Exception as e:
                print(f"Error processing intelligence for post {post.id}: {e}")
                continue
        
        return {
            "status": "success",
            "processed_count": processed_count,
            "threat_count": threat_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "processed_count": 0
        }

@celery_app.task(base=AsyncTask, bind=True)
async def analyze_post_sentiment(self, post_id: str):
    """
    Analyze sentiment for a specific post
    """
    try:
        post_service = SocialPostService()
        intelligence_service = IntelligenceService()
        
        post = await post_service.get_post(post_id)
        if not post:
            return {"status": "error", "error": "Post not found"}
        
        # Perform intelligence analysis
        intelligence = await intelligence_service.analyze_post(
            post.content.text,
            post.engagement.dict()
        )
        
        return {
            "status": "success",
            "post_id": post_id,
            "sentiment_score": intelligence.sentiment_score,
            "sentiment_label": intelligence.sentiment_label,
            "is_threat": intelligence.is_threat,
            "threat_level": intelligence.threat_level
        }
        
    except Exception as e:
        return {
            "status": "error",
            "post_id": post_id,
            "error": str(e)
        }

@celery_app.task(base=AsyncTask, bind=True)
async def batch_sentiment_analysis(self, post_ids: List[str]):
    """
    Batch sentiment analysis for multiple posts
    """
    try:
        post_service = SocialPostService()
        intelligence_service = IntelligenceService()
        
        results = []
        threat_posts = []
        
        for post_id in post_ids:
            try:
                post = await post_service.get_post(post_id)
                if not post:
                    results.append({
                        "post_id": post_id,
                        "status": "error",
                        "error": "Post not found"
                    })
                    continue
                
                # Analyze sentiment
                intelligence = await intelligence_service.analyze_post(
                    post.content.text,
                    post.engagement.dict()
                )
                
                result = {
                    "post_id": post_id,
                    "status": "success",
                    "sentiment_score": intelligence.sentiment_score,
                    "sentiment_label": intelligence.sentiment_label,
                    "is_threat": intelligence.is_threat,
                    "threat_level": intelligence.threat_level
                }
                
                results.append(result)
                
                if intelligence.is_threat:
                    threat_posts.append({
                        "post_id": post_id,
                        "threat_level": intelligence.threat_level,
                        "platform": post.platform
                    })
                
            except Exception as e:
                results.append({
                    "post_id": post_id,
                    "status": "error",
                    "error": str(e)
                })
        
        # Send threat alert if any threats found
        if threat_posts:
            websocket_manager = WebSocketManager()
            await websocket_manager.broadcast_message({
                "type": "batch_threats_detected",
                "data": {
                    "threat_count": len(threat_posts),
                    "threats": threat_posts,
                    "processed_count": len(post_ids)
                }
            })
        
        return {
            "status": "success",
            "processed_count": len(post_ids),
            "successful_count": len([r for r in results if r.get("status") == "success"]),
            "threat_count": len(threat_posts),
            "results": results
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "processed_count": 0
        }

@celery_app.task(base=AsyncTask, bind=True)
async def deep_content_analysis(self, cluster_id: str, time_range_hours: int = 24):
    """
    Perform deep content analysis for a cluster over a time range
    """
    try:
        post_service = SocialPostService()
        intelligence_service = IntelligenceService()
        
        # Get posts for the cluster within time range
        posts = await post_service.get_posts(
            cluster_id=cluster_id,
            skip=0,
            limit=2000
        )
        
        # Filter by time range
        cutoff_time = datetime.utcnow() - timedelta(hours=time_range_hours)
        recent_posts = [
            post for post in posts 
            if post.collected_at >= cutoff_time
        ]
        
        # Analyze sentiment trends
        sentiment_scores = []
        threat_levels = []
        platform_breakdown = {}
        
        for post in recent_posts:
            try:
                intelligence = await intelligence_service.analyze_post(
                    post.content.text,
                    post.engagement.dict()
                )
                
                sentiment_scores.append(intelligence.sentiment_score)
                if intelligence.is_threat:
                    threat_levels.append(intelligence.threat_level)
                
                # Platform breakdown
                if post.platform not in platform_breakdown:
                    platform_breakdown[post.platform] = {
                        "total": 0,
                        "threats": 0,
                        "avg_sentiment": 0
                    }
                
                platform_breakdown[post.platform]["total"] += 1
                if intelligence.is_threat:
                    platform_breakdown[post.platform]["threats"] += 1
                
            except Exception as e:
                print(f"Error analyzing post {post.id}: {e}")
                continue
        
        # Calculate analytics
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        threat_percentage = (len(threat_levels) / len(recent_posts)) * 100 if recent_posts else 0
        
        # Calculate platform averages
        for platform_data in platform_breakdown.values():
            if platform_data["total"] > 0:
                platform_data["threat_percentage"] = (platform_data["threats"] / platform_data["total"]) * 100
        
        analysis_result = {
            "cluster_id": cluster_id,
            "time_range_hours": time_range_hours,
            "total_posts": len(recent_posts),
            "avg_sentiment_score": avg_sentiment,
            "threat_count": len(threat_levels),
            "threat_percentage": threat_percentage,
            "platform_breakdown": platform_breakdown,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send analysis results via WebSocket
        websocket_manager = WebSocketManager()
        await websocket_manager.broadcast_message({
            "type": "deep_analysis_complete",
            "data": analysis_result
        })
        
        return {
            "status": "success",
            **analysis_result
        }
        
    except Exception as e:
        return {
            "status": "error",
            "cluster_id": cluster_id,
            "error": str(e)
        }

@celery_app.task(base=AsyncTask, bind=True)
async def trend_analysis(self, keywords: List[str], days_back: int = 7):
    """
    Analyze sentiment trends for specific keywords over time
    """
    try:
        post_service = SocialPostService()
        intelligence_service = IntelligenceService()
        
        # Get posts containing the keywords
        all_posts = []
        for keyword in keywords:
            # This would ideally search posts by content containing keyword
            # For now, get recent posts and filter
            posts = await post_service.get_posts(skip=0, limit=1000)
            keyword_posts = [
                post for post in posts 
                if keyword.lower() in post.content.text.lower()
            ]
            all_posts.extend(keyword_posts)
        
        # Filter by date range
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        recent_posts = [
            post for post in all_posts 
            if post.collected_at >= cutoff_date
        ]
        
        # Analyze trends by day
        daily_trends = {}
        
        for post in recent_posts:
            day_key = post.collected_at.date().isoformat()
            
            if day_key not in daily_trends:
                daily_trends[day_key] = {
                    "post_count": 0,
                    "sentiment_scores": [],
                    "threat_count": 0,
                    "platforms": set()
                }
            
            try:
                intelligence = await intelligence_service.analyze_post(
                    post.content.text,
                    post.engagement.dict()
                )
                
                daily_trends[day_key]["post_count"] += 1
                daily_trends[day_key]["sentiment_scores"].append(intelligence.sentiment_score)
                if intelligence.is_threat:
                    daily_trends[day_key]["threat_count"] += 1
                daily_trends[day_key]["platforms"].add(post.platform)
                
            except Exception as e:
                print(f"Error analyzing post {post.id}: {e}")
                continue
        
        # Calculate daily averages
        trend_summary = {}
        for day, data in daily_trends.items():
            avg_sentiment = sum(data["sentiment_scores"]) / len(data["sentiment_scores"]) if data["sentiment_scores"] else 0
            trend_summary[day] = {
                "post_count": data["post_count"],
                "avg_sentiment": avg_sentiment,
                "threat_count": data["threat_count"],
                "threat_percentage": (data["threat_count"] / data["post_count"]) * 100 if data["post_count"] > 0 else 0,
                "platforms": list(data["platforms"])
            }
        
        return {
            "status": "success",
            "keywords": keywords,
            "days_analyzed": days_back,
            "total_posts": len(recent_posts),
            "daily_trends": trend_summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "keywords": keywords,
            "error": str(e)
        }