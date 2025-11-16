#!/usr/bin/env python3
"""
Script to fetch news articles from Google News RSS feeds
"""
import asyncio
import aiohttp
import sys
import os

async def trigger_news_collection():
    """Trigger news collection via API"""
    print("🚀 Starting Google News RSS Collection")
    print("=" * 60)
    
    api_base = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        try:
            # Trigger collection for all clusters
            print("📡 Triggering news collection for all clusters...")
            
            async with session.post(f"{api_base}/api/v1/news/collect") as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Collection triggered successfully!")
                    print(f"Result: {result}")
                    return result
                else:
                    text = await resp.text()
                    print(f"❌ API returned status {resp.status}: {text}")
                    return {"error": f"Status {resp.status}"}
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"error": str(e)}


if __name__ == "__main__":
    print("Google News RSS Feed Collector")
    print("-" * 40)
    print("Collecting news articles for:")
    print("  - DMK")
    print("  - AIADMK")
    print("  - All configured clusters")
    print("-" * 40)
    
    # Run the collection
    result = asyncio.run(trigger_news_collection())
    
    if 'error' not in result:
        print("\n✅ RSS feed collection triggered successfully!")
    else:
        print(f"\n⚠️ Collection failed: {result['error']}")