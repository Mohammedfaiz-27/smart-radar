#!/usr/bin/env python3
"""
Clear old data from database before re-collecting with new LLM analysis
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    connection_string = "mongodb+srv://dbusr:dbusr123@smart-radar.tbapili.mongodb.net/smart_radar?retryWrites=true&w=majority&appName=smart-radar"
    client = AsyncIOMotorClient(connection_string)
    db = client.smart_radar

    print("=" * 60)
    print("CLEARING OLD DATA")
    print("=" * 60)

    # Show current counts
    print("\n📊 Current Data Counts:")
    posts_count = await db.posts_table.count_documents({})
    raw_count = await db.raw_data.count_documents({})
    print(f"  Posts Table: {posts_count} documents")
    print(f"  Raw Data: {raw_count} documents")

    # Confirm deletion
    print("\n⚠️  This will DELETE all posts and raw data!")
    print("   Clusters and narratives will be preserved.")

    # Clear posts_table
    print("\n🗑️  Deleting posts_table...")
    result = await db.posts_table.delete_many({})
    print(f"   ✅ Deleted {result.deleted_count} posts")

    # Clear raw_data
    print("\n🗑️  Deleting raw_data...")
    result = await db.raw_data.delete_many({})
    print(f"   ✅ Deleted {result.deleted_count} raw data entries")

    # Verify deletion
    print("\n📊 Final Data Counts:")
    posts_count = await db.posts_table.count_documents({})
    raw_count = await db.raw_data.count_documents({})
    print(f"  Posts Table: {posts_count} documents")
    print(f"  Raw Data: {raw_count} documents")

    # Show preserved data
    print("\n✅ Preserved Data:")
    clusters_count = await db.clusters.count_documents({})
    narratives_count = await db.narratives.count_documents({})
    print(f"  Clusters: {clusters_count} documents")
    print(f"  Narratives: {narratives_count} documents")

    print("\n" + "=" * 60)
    print("DATA CLEARED SUCCESSFULLY")
    print("Ready for fresh collection with new LLM analysis!")
    print("=" * 60)

    client.close()

if __name__ == '__main__':
    asyncio.run(main())
