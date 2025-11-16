#!/usr/bin/env python3
"""Check raw_data status"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    connection_string = "mongodb+srv://dbusr:dbusr123@smart-radar.tbapili.mongodb.net/smart_radar?retryWrites=true&w=majority&appName=smart-radar"
    client = AsyncIOMotorClient(connection_string)
    db = client.smart_radar

    # Count raw_data by status
    total = await db.raw_data.count_documents({})
    pending = await db.raw_data.count_documents({"processing_status": "pending"})
    processed = await db.raw_data.count_documents({"processing_status": "processed"})
    failed = await db.raw_data.count_documents({"processing_status": "failed"})

    print(f"Raw Data Status:")
    print(f"  Total: {total}")
    print(f"  Pending: {pending}")
    print(f"  Processed: {processed}")
    print(f"  Failed: {failed}")

    # Check posts_table
    posts_count = await db.posts_table.count_documents({})
    print(f"\nPosts Table: {posts_count} documents")

    # Sample a pending entry
    sample = await db.raw_data.find_one({"processing_status": "pending"})
    if sample:
        print(f"\nSample pending entry:")
        print(f"  ID: {sample.get('_id')}")
        print(f"  Platform: {sample.get('platform')}")
        print(f"  Has content: {bool(sample.get('raw_content'))}")

    client.close()

if __name__ == '__main__':
    asyncio.run(main())
