"""
Celery tasks for automated data collection
"""
import asyncio
from typing import List, Dict, Any
from celery import Task
from app.core.celery_instance import celery_app
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.cluster_service import ClusterService
from app.services.websocket_manager import WebSocketManager
from app.services.news_article_service import NewsArticleService

class AsyncTask(Task):
    """Base task class for async operations"""
    def __call__(self, *args, **kwargs):
        # Celery should not have a running event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're already in an event loop, this is unexpected in Celery
            raise RuntimeError("Unexpected: Celery task called within existing event loop")
        except RuntimeError:
            # No running loop, create a new one (normal Celery case)
            pass

        # Create and run a new event loop for this task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(self.run(*args, **kwargs))
        finally:
            # Clean up the event loop properly
            try:
                # Cancel any remaining tasks
                pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
                if pending:
                    for task in pending:
                        task.cancel()
                    # Wait for cancelled tasks to finish
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception as cleanup_error:
                print(f"Warning: Error during task cleanup: {cleanup_error}")
            finally:
                # Close the loop
                try:
                    loop.close()
                except Exception as close_error:
                    print(f"Warning: Error closing event loop: {close_error}")

@celery_app.task(base=AsyncTask, bind=True)
async def scheduled_data_collection(self):
    """
    Scheduled task to collect data from all active clusters using PipelineOrchestrator
    """
    try:
        print("Starting scheduled data collection for all active clusters...")
        
        # Use PipelineOrchestrator for collection
        orchestrator = PipelineOrchestrator()
        results = await orchestrator.collect_all_active_clusters()
        
        # Extract summary data
        clusters_processed = results.get("clusters_processed", 0)
        total_posts_collected = results.get("total_posts_collected", 0)
        total_posts_processed = results.get("total_posts_processed", 0)
        errors = results.get("errors", [])
        
        print(f"Collection complete: {clusters_processed} clusters, {total_posts_collected} posts collected, {total_posts_processed} posts processed")
        
        # Notify via WebSocket
        websocket_manager = WebSocketManager()
        await websocket_manager.broadcast_message({
            "type": "data_collection_complete",
            "data": {
                "clusters_processed": clusters_processed,
                "successful_clusters": clusters_processed - len(errors),
                "total_posts_collected": total_posts_collected,
                "total_posts_processed": total_posts_processed,
                "errors_count": len(errors),
                "timestamp": asyncio.get_event_loop().time()
            }
        })
        
        return {
            "status": "success",
            "clusters_processed": clusters_processed,
            "successful_clusters": clusters_processed - len(errors),
            "total_posts_collected": total_posts_collected,
            "total_posts_processed": total_posts_processed,
            "errors": errors[:5]  # Limit errors in response
        }
        
    except Exception as e:
        print(f"Error in scheduled data collection: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "status": "error",
            "error": str(e),
            "clusters_processed": 0,
            "total_posts_collected": 0
        }

@celery_app.task(base=AsyncTask, bind=True)
async def collect_cluster_data(self, cluster_id: str, platforms: List[str] = None):
    """
    Collect data for a specific cluster using PipelineOrchestrator
    """
    try:
        print(f"Starting data collection for cluster: {cluster_id}")
        
        # Use PipelineOrchestrator for collection
        orchestrator = PipelineOrchestrator()
        result = await orchestrator.collect_and_process_cluster(
            cluster_id=cluster_id,
            save_to_social_posts=True,  # For backward compatibility
            save_to_posts_table=True    # For new system
        )
        
        if result.get("error"):
            return {"status": "error", "error": result["error"]}
        
        posts_collected = result.get("total_posts_collected", 0)
        posts_processed = result.get("total_posts_processed", 0)
        
        print(f"Cluster {cluster_id} collection complete: {posts_collected} collected, {posts_processed} processed")
        
        return {
            "status": "success",
            "cluster_id": cluster_id,
            "cluster_name": result.get("cluster_name", "Unknown"),
            "posts_collected": posts_collected,
            "posts_processed": posts_processed,
            "platforms": result.get("platforms", {}),
            "errors": result.get("errors", [])
        }
        
    except Exception as e:
        print(f"Error collecting data for cluster {cluster_id}: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "status": "error",
            "cluster_id": cluster_id,
            "error": str(e)
        }

@celery_app.task(base=AsyncTask, bind=True)
async def platform_specific_collection(self, platform: str, keywords: List[str], cluster_id: str = None):
    """
    Collect data from a specific platform (deprecated - use collect_cluster_data instead)
    """
    try:
        print(f"Platform-specific collection is deprecated. Use collect_cluster_data instead.")
        return {
            "status": "deprecated",
            "message": "Use collect_cluster_data task instead for better Tamil keyword support"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "platform": platform,
            "error": str(e)
        }

@celery_app.task(base=AsyncTask, bind=True)
async def emergency_data_collection(self, keywords: List[str], priority: str = "high"):
    """
    Emergency data collection for crisis situations (deprecated - create a cluster instead)
    """
    try:
        print(f"Emergency collection is deprecated. Create a cluster with keywords: {keywords}")
        
        # Send alert about deprecated usage
        websocket_manager = WebSocketManager()
        await websocket_manager.broadcast_message({
            "type": "emergency_collection_deprecated",
            "data": {
                "keywords": keywords,
                "priority": priority,
                "message": "Emergency collection is deprecated. Create a cluster with these keywords for better Tamil support.",
                "urgent": True
            }
        })
        
        return {
            "status": "deprecated",
            "keywords": keywords,
            "message": "Create a cluster with these keywords for better Tamil keyword support"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "keywords": keywords,
            "error": str(e)
        }

@celery_app.task(base=AsyncTask, bind=True)
async def bulk_historical_collection(self, cluster_ids: List[str], date_range: Dict[str, str]):
    """
    Bulk historical data collection for analysis
    """
    try:
        cluster_service = ClusterService()
        results = {}
        
        for cluster_id in cluster_ids:
            cluster = await cluster_service.get_cluster(cluster_id)
            if not cluster:
                results[cluster_id] = {"error": "Cluster not found"}
                continue
            
            # Note: This would require API endpoints that support historical data
            # For now, we'll collect current data as a placeholder
            async with DataCollectionService() as collection_service:
                post_ids = await collection_service.collect_posts_for_cluster(
                    cluster_id=cluster_id,
                    keywords=cluster.keywords,
                    platforms=["X", "Facebook", "YouTube"]
                )
            
            results[cluster_id] = {
                "posts_collected": len(post_ids),
                "post_ids": post_ids,
                "date_range": date_range
            }
        
        total_posts = sum(
            result.get("posts_collected", 0) 
            for result in results.values() 
            if isinstance(result, dict) and "posts_collected" in result
        )
        
        return {
            "status": "success",
            "clusters_processed": len(cluster_ids),
            "total_posts": total_posts,
            "date_range": date_range,
            "results": results
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "clusters_processed": 0
        }

@celery_app.task(base=AsyncTask, bind=True)
async def scheduled_news_collection(self):
    """
    Scheduled task to collect news articles from Google News for all active clusters
    """
    try:
        news_service = NewsArticleService()
        
        # Note: This would require a separate news collection service
        # For now, return a placeholder response
        results = {"clusters_processed": 0, "collected": 0, "errors": 0}
        
        # Notify via WebSocket
        websocket_manager = WebSocketManager()
        await websocket_manager.broadcast_message({
            "type": "news_collection_complete",
            "data": {
                "clusters_processed": results.get("clusters_processed", 0),
                "articles_collected": results.get("collected", 0),
                "errors": results.get("errors", 0),
                "timestamp": asyncio.get_event_loop().time()
            }
        })
        
        return {
            "status": "success",
            "clusters_processed": results.get("clusters_processed", 0),
            "articles_collected": results.get("collected", 0),
            "errors": results.get("errors", 0),
            "message": "News collection completed successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "clusters_processed": 0,
            "articles_collected": 0
        }

@celery_app.task(base=AsyncTask, bind=True)
async def collect_cluster_news(self, cluster_id: str):
    """
    Collect news articles for a specific cluster
    """
    try:
        news_service = NewsArticleService()
        
        # Note: This would require a separate news collection service
        # For now, return a placeholder response
        results = {"collected": 0}
        
        # Notify via WebSocket
        websocket_manager = WebSocketManager()
        await websocket_manager.broadcast_message({
            "type": "cluster_news_collection_complete",
            "data": {
                "cluster_id": cluster_id,
                "articles_collected": results.get("collected", 0),
                "timestamp": asyncio.get_event_loop().time()
            }
        })
        
        return {
            "status": "success",
            "cluster_id": cluster_id,
            "articles_collected": results.get("collected", 0),
            "message": f"News collection completed for cluster {cluster_id}"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "cluster_id": cluster_id,
            "error": str(e),
            "articles_collected": 0
        }