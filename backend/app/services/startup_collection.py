"""
Startup Data Collection Service
Triggers data collection for all active clusters when the server starts
"""
import logging
import asyncio
from typing import List
from app.services.cluster_service import ClusterService
from app.services.pipeline_orchestrator import PipelineOrchestrator

logger = logging.getLogger(__name__)


async def trigger_startup_collection():
    """
    Trigger data collection for all active clusters on server startup.
    This runs in the background so it doesn't block server startup.
    """
    # Add a small delay before starting collection to ensure server is fully up
    async def delayed_collection():
        await asyncio.sleep(5)  # Wait 5 seconds after startup
        await _collect_all_clusters()

    # Run collection in background task
    asyncio.create_task(delayed_collection())


async def _collect_all_clusters():
    """
    Internal function to collect data from all active clusters.
    Runs asynchronously in the background.
    Collects from ALL platforms: X, Facebook, YouTube, and Google News
    """
    try:
        cluster_service = ClusterService()
        orchestrator = PipelineOrchestrator()

        # Get all active clusters
        clusters = await cluster_service.get_clusters(is_active=True)

        if not clusters:
            logger.warning("⚠️ No active clusters found for startup collection")
            return

        # Separate own and competitor clusters
        own_clusters = [c for c in clusters if c.cluster_type == "own"]
        competitor_clusters = [c for c in clusters if c.cluster_type == "competitor"]

        logger.info(f"📊 Found {len(own_clusters)} own clusters and {len(competitor_clusters)} competitor clusters")

        # Collect data for all clusters in parallel
        tasks = []

        for cluster in clusters:
            logger.info(f"📋 Scheduling collection for: {cluster.name} ({cluster.cluster_type})")
            logger.info(f"   Keywords: {cluster.keywords}")
            logger.info(f"   Platforms: X, Facebook, YouTube, Google News")
            task = orchestrator.collect_and_process_cluster(
                cluster_id=cluster.id,
                save_to_social_posts=True,  # Save to both collections for compatibility
                save_to_posts_table=True
            )
            tasks.append(task)

        # Run all collections in parallel
        logger.info(f"🚀 Starting parallel collection for {len(tasks)} clusters across all platforms...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log results
        success_count = 0
        error_count = 0
        total_posts = 0

        for i, (cluster, result) in enumerate(zip(clusters, results)):
            if isinstance(result, Exception):
                logger.error(f"❌ Error collecting {cluster.name}: {result}")
                error_count += 1
            else:
                posts_collected = result.get('total_posts_processed', 0)
                total_posts += posts_collected
                success_count += 1
                logger.info(f"✅ {cluster.name}: {posts_collected} posts collected")

                # Log per-platform stats
                platforms = result.get('platforms', {})
                for platform, stats in platforms.items():
                    platform_posts = stats.get('posts_processed', 0)
                    if platform_posts > 0:
                        logger.info(f"   - {platform}: {platform_posts} posts")

        logger.info(f"🎉 Startup collection complete: {success_count} succeeded, {error_count} failed, {total_posts} total posts")

    except Exception as e:
        logger.error(f"❌ Fatal error in startup collection: {e}")
        import traceback
        logger.error(traceback.format_exc())
