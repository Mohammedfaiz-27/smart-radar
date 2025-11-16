#!/usr/bin/env python3
"""Test collection from all platforms"""
import asyncio
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.cluster_service import ClusterService

async def main():
    print("Testing collection from ALL platforms...")

    cluster_service = ClusterService()
    clusters = await cluster_service.get_clusters(is_active=True)

    if not clusters:
        print("No active clusters found")
        return

    # Use first cluster for testing
    cluster = clusters[0]
    print(f"\nUsing cluster: {cluster.name} ({cluster.id})")

    orchestrator = PipelineOrchestrator()
    result = await orchestrator.collect_and_process_cluster(
        cluster_id=cluster.id,
        save_to_social_posts=False,
        save_to_posts_table=True
    )

    print(f"\n{'='*60}")
    print(f"Collection Results:")
    print(f"{'='*60}")

    for platform, stats in result.get('platforms', {}).items():
        print(f"\n{platform.upper()}:")
        if 'error' in stats:
            print(f"  ✗ Error: {stats['error']}")
        else:
            print(f"  ✓ Raw collected: {stats.get('raw_collected', 0)}")
            print(f"  ✓ Posts saved: {stats.get('posts_saved', 0)}")
            print(f"  ✓ Posts processed: {stats.get('posts_processed', 0)}")

    print(f"\nTotal:")
    print(f"  Collected: {result.get('total_posts_collected', 0)}")
    print(f"  Processed: {result.get('total_posts_processed', 0)}")

    if result.get('errors'):
        print(f"\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")

if __name__ == '__main__':
    asyncio.run(main())
