#!/usr/bin/env python3
"""Trigger collection for competitor clusters"""
import asyncio
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.cluster_service import ClusterService

async def main():
    print("Collecting data for COMPETITOR clusters...\n")

    cluster_service = ClusterService()
    orchestrator = PipelineOrchestrator()

    # Get all active clusters
    clusters = await cluster_service.get_clusters(is_active=True)

    # Filter competitor clusters
    competitor_clusters = [c for c in clusters if c.cluster_type == "competitor"]

    print(f"Found {len(competitor_clusters)} competitor clusters:")
    for c in competitor_clusters:
        print(f"  - {c.name}")

    print("\nStarting collection...\n")

    for cluster in competitor_clusters:
        print(f"{'='*60}")
        print(f"Collecting for: {cluster.name}")
        print(f"{'='*60}")

        result = await orchestrator.collect_and_process_cluster(
            cluster_id=cluster.id,
            save_to_social_posts=False,
            save_to_posts_table=True
        )

        print(f"\n{cluster.name} Results:")
        print(f"  Total collected: {result.get('total_posts_collected', 0)}")
        print(f"  Total processed: {result.get('total_posts_processed', 0)}")

        for platform, stats in result.get('platforms', {}).items():
            if 'error' not in stats:
                print(f"  {platform}: {stats.get('posts_saved', 0)} posts")

        print()

if __name__ == '__main__':
    asyncio.run(main())
