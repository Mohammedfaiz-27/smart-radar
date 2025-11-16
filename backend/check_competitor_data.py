#!/usr/bin/env python3
"""Check competitor cluster data"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    connection_string = "mongodb+srv://dbusr:dbusr123@smart-radar.tbapili.mongodb.net/smart_radar?retryWrites=true&w=majority&appName=smart-radar"
    client = AsyncIOMotorClient(connection_string)
    db = client.smart_radar

    print("=== CLUSTERS ===")
    clusters = await db.clusters.find({}).to_list(length=100)
    for cluster in clusters:
        print(f"\n{cluster.get('name')}:")
        print(f"  Type: {cluster.get('cluster_type')}")
        print(f"  Dashboard: {cluster.get('dashboard_type')}")
        print(f"  Active: {cluster.get('is_active')}")
        print(f"  Keywords: {cluster.get('keywords', [])[:3]}")

    print("\n=== RAW DATA BY CLUSTER ===")
    for cluster in clusters:
        count = await db.raw_data.count_documents({"cluster_id": cluster.get('_id')})
        print(f"{cluster.get('name')} ({cluster.get('cluster_type')}): {count} raw entries")

    print("\n=== POSTS TABLE BY CLUSTER ===")
    for cluster in clusters:
        count = await db.posts_table.count_documents({"cluster_id": str(cluster.get('_id'))})
        print(f"{cluster.get('name')} ({cluster.get('cluster_type')}): {count} posts")

    print("\n=== POSTS BY CLUSTER TYPE ===")
    pipeline = [
        {
            "$lookup": {
                "from": "clusters",
                "let": {"cluster_id_str": {"$toString": "$cluster_id"}},
                "pipeline": [
                    {"$addFields": {"id_str": {"$toString": "$_id"}}},
                    {"$match": {"$expr": {"$eq": ["$id_str", "$$cluster_id_str"]}}}
                ],
                "as": "cluster_info"
            }
        },
        {"$unwind": "$cluster_info"},
        {
            "$group": {
                "_id": "$cluster_info.cluster_type",
                "count": {"$sum": 1}
            }
        }
    ]

    result = await db.posts_table.aggregate(pipeline).to_list(length=100)
    for item in result:
        print(f"{item['_id']}: {item['count']} posts")

    client.close()

if __name__ == '__main__':
    asyncio.run(main())
