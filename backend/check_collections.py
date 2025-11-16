#!/usr/bin/env python3
"""Check Atlas collections and data"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_atlas():
    connection_string = "mongodb+srv://dbusr:dbusr123@smart-radar.tbapili.mongodb.net/smart_radar?retryWrites=true&w=majority&appName=smart-radar"

    try:
        client = AsyncIOMotorClient(connection_string, serverSelectionTimeoutMS=5000)
        db = client.smart_radar

        # List all collections
        collections = await db.list_collection_names()
        print(f"✓ Collections in smart_radar: {collections}")

        # Count documents in each collection
        for coll_name in collections:
            count = await db[coll_name].count_documents({})
            print(f"  - {coll_name}: {count} documents")

        # Check if raw_table exists
        if 'raw_table' in collections:
            print(f"\n✓ raw_table exists")
            sample = await db.raw_table.find_one()
            if sample:
                print(f"  Sample keys: {list(sample.keys())}")
        else:
            print(f"\n✗ raw_table does NOT exist")

        # Get cluster count
        cluster_count = await db.clusters.count_documents({})
        print(f"\n✓ Total clusters in Atlas: {cluster_count}")

        # List all clusters
        clusters = await db.clusters.find({}, {"name": 1, "cluster_type": 1}).to_list(length=100)
        print(f"✓ Clusters:")
        for c in clusters:
            print(f"  - {c.get('name')} ({c.get('cluster_type')})")

        client.close()
    except Exception as e:
        print(f'✗ Error: {e}')

if __name__ == '__main__':
    asyncio.run(check_atlas())
