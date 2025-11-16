#!/usr/bin/env python3
"""
Simple script to check if data is stored in MongoDB
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_database():
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://admin:password@localhost:27017/?authSource=admin")
    db = client.smart_radar
    
    # Check monitored_content collection
    monitored_content_count = await db.monitored_content.count_documents({})
    print(f"📊 monitored_content collection: {monitored_content_count} documents")
    
    # Check legacy collections
    social_posts_count = await db.social_posts.count_documents({})
    news_count = await db.news_articles.count_documents({})
    clusters_count = await db.clusters.count_documents({})
    
    print(f"📊 social_posts collection: {social_posts_count} documents")
    print(f"📊 news_articles collection: {news_count} documents") 
    print(f"📊 clusters collection: {clusters_count} documents")
    
    # Show sample from monitored_content if it exists
    if monitored_content_count > 0:
        print("\n📄 Sample monitored_content document:")
        sample_doc = await db.monitored_content.find_one({})
        if sample_doc:
            print(f"  - Title: {sample_doc.get('title', 'N/A')}")
            print(f"  - Platform: {sample_doc.get('platform', 'N/A')}")
            print(f"  - Content Type: {sample_doc.get('content_type', 'N/A')}")
            print(f"  - Has Intelligence: {'intelligence' in sample_doc}")
            print(f"  - Created At: {sample_doc.get('created_at', 'N/A')}")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(check_database())