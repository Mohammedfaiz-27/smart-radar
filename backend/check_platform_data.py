#!/usr/bin/env python3
"""Check what platforms have data"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    connection_string = "mongodb+srv://dbusr:dbusr123@smart-radar.tbapili.mongodb.net/smart_radar?retryWrites=true&w=majority&appName=smart-radar"
    client = AsyncIOMotorClient(connection_string)
    db = client.smart_radar

    print("Raw Data by Platform:")
    platforms = await db.raw_data.distinct("platform")
    for platform in platforms:
        count = await db.raw_data.count_documents({"platform": platform})
        pending = await db.raw_data.count_documents({"platform": platform, "processing_status": "pending"})
        print(f"  {platform}: {count} total ({pending} pending)")

    print("\nPosts Table by Platform:")
    post_platforms = await db.posts_table.distinct("platform")
    for platform in post_platforms:
        count = await db.posts_table.count_documents({"platform": platform})
        print(f"  {platform}: {count} posts")

    print(f"\n Total raw_data: {await db.raw_data.count_documents({})}")
    print(f"Total posts_table: {await db.posts_table.count_documents({})}")

    client.close()

if __name__ == '__main__':
    asyncio.run(main())
