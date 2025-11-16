#!/usr/bin/env python3
"""
Script to collect news from Google News RSS feeds for all clusters
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from app.services.news_service import NewsService


async def collect_news_for_clusters():
    """Collect news from RSS feeds for all active clusters"""
    print("🚀 Starting Google News RSS Collection")
    print("=" * 60)
    
    news_service = NewsService()
    
    try:
        # Collect news for all clusters
        print("📡 Fetching news for all clusters...")
        result = await news_service.collect_news_for_all_clusters()
        
        print("\n✅ Collection Complete!")
        print(f"Results: {result}")
        
        # Get summary of collected articles
        if 'collected' in result:
            print(f"\n📊 Summary:")
            print(f"  Total articles collected: {result['collected']}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error during collection: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


if __name__ == "__main__":
    print("Google News RSS Feed Collector")
    print("-" * 40)
    print("This will collect news articles for:")
    print("  - DMK")
    print("  - AIADMK")
    print("  - All configured clusters")
    print("-" * 40)
    
    # Run the collection
    result = asyncio.run(collect_news_for_clusters())
    
    if 'error' not in result:
        print("\n✅ RSS feed collection completed successfully!")
    else:
        print(f"\n⚠️ Collection completed with errors: {result['error']}")