#!/usr/bin/env python3
import asyncio
from app.core.database import connect_to_mongo, get_database

async def fix_cluster_types():
    await connect_to_mongo()
    db = get_database()
    
    # Get clusters mapping
    clusters_collection = db.clusters
    clusters = {}
    async for cluster in clusters_collection.find():
        clusters[str(cluster['_id'])] = cluster.get('cluster_type', 'own')
    
    print(f"Found {len(clusters)} clusters:")
    for cluster_id, cluster_type in clusters.items():
        print(f"  {cluster_id}: {cluster_type}")
    
    # Fix posts with incorrect cluster_type
    posts_collection = db.social_posts
    
    # Find posts where cluster_type doesn't match the cluster definition
    fixed_count = 0
    total_posts = 0
    
    async for post in posts_collection.find():
        total_posts += 1
        cluster_id = str(post.get('cluster_id', ''))
        current_cluster_type = post.get('cluster_type', '')
        correct_cluster_type = clusters.get(cluster_id)
        
        if correct_cluster_type and current_cluster_type != correct_cluster_type:
            print(f"Fixing post {post['_id']}: {current_cluster_type} → {correct_cluster_type}")
            await posts_collection.update_one(
                {'_id': post['_id']},
                {'$set': {'cluster_type': correct_cluster_type}}
            )
            fixed_count += 1
    
    print(f"\nProcessed {total_posts} posts")
    print(f"Fixed {fixed_count} posts with incorrect cluster_type")
    
    # Show final stats
    print("\n=== FINAL STATS ===")
    pipeline = [
        {'$group': {
            '_id': '$cluster_type',
            'count': {'$sum': 1}
        }},
        {'$sort': {'count': -1}}
    ]
    
    async for doc in posts_collection.aggregate(pipeline):
        cluster_type = doc['_id']
        count = doc['count']
        print(f'{cluster_type}: {count} posts')

if __name__ == "__main__":
    asyncio.run(fix_cluster_types())