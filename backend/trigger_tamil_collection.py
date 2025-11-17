"""
Manually trigger Tamil data collection
"""
import asyncio
import sys
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.cluster_service import ClusterService
from app.core.database import connect_to_mongo, close_mongo_connection

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

async def collect_tamil_data():
    """Collect Tamil data for all active clusters"""

    # Connect to database
    print("🔌 Connecting to MongoDB...")
    await connect_to_mongo()
    print("✅ Connected!")

    try:
        # Get clusters
        cluster_service = ClusterService()
        clusters = await cluster_service.get_clusters(is_active=True)

        if not clusters:
            print("❌ No active clusters found!")
            return

        print(f"\n📊 Found {len(clusters)} active cluster(s):")
        for cluster in clusters:
            print(f"   - {cluster.name} ({cluster.cluster_type})")
            print(f"     Keywords: {cluster.keywords}")

        # Trigger collection
        orchestrator = PipelineOrchestrator()

        print(f"\n🚀 Starting data collection for all clusters...")
        print("This will collect from: X (Twitter), Facebook, YouTube, and Google News\n")

        tasks = []
        for cluster in clusters:
            print(f"📋 Queuing: {cluster.name}")
            task = orchestrator.collect_and_process_cluster(
                cluster_id=cluster.id,
                save_to_social_posts=True,
                save_to_posts_table=True
            )
            tasks.append(task)

        # Run all collections in parallel
        print(f"\n⏳ Collecting data (this may take 1-2 minutes)...\n")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Show results
        print("\n" + "="*60)
        print("COLLECTION RESULTS")
        print("="*60)

        total_posts = 0
        for cluster, result in zip(clusters, results):
            if isinstance(result, Exception):
                print(f"❌ {cluster.name}: ERROR - {result}")
            else:
                posts_collected = result.get('total_posts_processed', 0)
                total_posts += posts_collected
                print(f"\n✅ {cluster.name}: {posts_collected} posts")

                # Show per-platform breakdown
                platforms = result.get('platforms', {})
                for platform, stats in platforms.items():
                    platform_posts = stats.get('posts_processed', 0)
                    if platform_posts > 0:
                        print(f"   - {platform}: {platform_posts} posts")

        print(f"\n{'='*60}")
        print(f"🎉 TOTAL: {total_posts} Tamil posts collected!")
        print("="*60)

    finally:
        # Close database connection
        await close_mongo_connection()
        print("\n✅ Database connection closed")

if __name__ == "__main__":
    asyncio.run(collect_tamil_data())
