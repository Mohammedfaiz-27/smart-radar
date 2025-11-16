#!/usr/bin/env python3
"""
Collect data for ALL active clusters (both own and competitor)
"""
import asyncio
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.cluster_service import ClusterService


async def main():
    print("=" * 60)
    print("COLLECTING DATA FOR ALL ACTIVE CLUSTERS")
    print("=" * 60)

    cluster_service = ClusterService()
    orchestrator = PipelineOrchestrator()

    # Get all active clusters
    clusters = await cluster_service.get_clusters(is_active=True)

    if not clusters:
        print("⚠️  No active clusters found!")
        return

    # Separate by type for logging
    own_clusters = [c for c in clusters if c.cluster_type == "own"]
    competitor_clusters = [c for c in clusters if c.cluster_type == "competitor"]

    print(f"\n📊 Found {len(clusters)} active clusters:")
    print(f"   • Own: {len(own_clusters)}")
    for c in own_clusters:
        print(f"     - {c.name}")
    print(f"   • Competitor: {len(competitor_clusters)}")
    for c in competitor_clusters:
        print(f"     - {c.name}")

    print("\n🚀 Starting collection for all clusters in parallel...\n")

    # Collect all clusters in parallel
    tasks = []
    for cluster in clusters:
        task = orchestrator.collect_and_process_cluster(
            cluster_id=cluster.id,
            save_to_social_posts=False,
            save_to_posts_table=True
        )
        tasks.append((cluster, task))

    # Execute all tasks
    results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

    # Print results
    print("\n" + "=" * 60)
    print("COLLECTION RESULTS")
    print("=" * 60)

    total_posts = 0
    success_count = 0
    error_count = 0

    for (cluster, _), result in zip(tasks, results):
        print(f"\n{cluster.name} ({cluster.cluster_type}):")

        if isinstance(result, Exception):
            print(f"  ❌ ERROR: {result}")
            error_count += 1
        else:
            posts_collected = result.get('total_posts_processed', 0)
            posts_raw = result.get('total_posts_collected', 0)
            total_posts += posts_collected
            success_count += 1

            print(f"  ✅ Raw collected: {posts_raw}")
            print(f"  ✅ Processed: {posts_collected}")

            # Show platform breakdown
            for platform, stats in result.get('platforms', {}).items():
                if 'error' not in stats:
                    print(f"     • {platform}: {stats.get('posts_saved', 0)} posts")

    print("\n" + "=" * 60)
    print(f"SUMMARY: {success_count} succeeded, {error_count} failed")
    print(f"TOTAL POSTS PROCESSED: {total_posts}")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
