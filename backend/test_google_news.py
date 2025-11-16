#!/usr/bin/env python3
"""
Test script for Google News RSS feed collection
Tests the new GoogleNewsCollector with actual cluster keywords
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from app.collectors.google_news_collector import GoogleNewsCollector
from app.models.cluster import PlatformConfig
from app.core.database import get_database
from bson import ObjectId


async def test_google_news_collection():
    """Test Google News RSS feed collection with real cluster keywords"""
    
    print("🔍 Testing Google News RSS Feed Collection")
    print("=" * 60)
    
    # Get cluster keywords from database
    db = get_database()
    clusters = await db.clusters.find({}).to_list(length=None)
    
    if not clusters:
        print("❌ No clusters found in database")
        return
    
    print(f"📊 Found {len(clusters)} clusters:")
    for cluster in clusters:
        print(f"  - {cluster['name']} ({cluster['cluster_type']}): {cluster['keywords']}")
    
    # Test with the first cluster (DMK)
    test_cluster = clusters[0]
    cluster_id = str(test_cluster['_id'])
    keywords = test_cluster['keywords']
    
    print(f"\n🧪 Testing with cluster: {test_cluster['name']}")
    print(f"Keywords: {keywords}")
    
    # Create Google News collector
    collector = GoogleNewsCollector()
    
    # Create platform config for Tamil news
    config = PlatformConfig(
        enabled=True,
        language='ta',  # Tamil
        location='IN',  # India
        max_results=5   # Limit for testing
    )
    
    print(f"\n🌐 Platform config:")
    print(f"  Language: {config.language}")
    print(f"  Location: {config.location}")
    print(f"  Max results: {config.max_results}")
    
    total_articles = 0
    
    # Test collection for each keyword
    async with collector:
        for i, keyword in enumerate(keywords):
            print(f"\n--- Testing keyword {i+1}/{len(keywords)}: '{keyword}' ---")
            
            try:
                article_count = 0
                async for article in collector.search(keyword, config, max_results=config.max_results):
                    article_count += 1
                    total_articles += 1
                    
                    print(f"\n📰 Article {article_count}:")
                    print(f"  Title: {article.get('title', 'N/A')[:100]}...")
                    print(f"  Source: {article.get('source', 'N/A')}")
                    print(f"  Language: {article.get('language', 'N/A')}")
                    print(f"  URL: {article.get('url', 'N/A')[:80]}...")
                    print(f"  Published: {article.get('published_at', 'N/A')}")
                    
                    # Test parsing to PostCreate model
                    try:
                        post = collector.parse_post(article, cluster_id)
                        print(f"  ✅ Successfully parsed to PostCreate model")
                        print(f"     Platform: {post.platform}")
                        print(f"     Content length: {len(post.content)} chars")
                    except Exception as parse_error:
                        print(f"  ❌ Error parsing to PostCreate: {parse_error}")
                
                print(f"\n✅ Collected {article_count} articles for keyword '{keyword}'")
                
            except Exception as e:
                print(f"\n❌ Error collecting for keyword '{keyword}': {e}")
                import traceback
                traceback.print_exc()
    
    print(f"\n🎉 Test Complete!")
    print(f"Total articles collected: {total_articles}")
    print(f"Keywords tested: {len(keywords)}")
    
    if total_articles > 0:
        print("\n✅ Google News RSS collection is working!")
        print("Ready to integrate into automated pipeline.")
    else:
        print("\n⚠️  No articles collected. Check:")
        print("  - Internet connection")
        print("  - RSS feed accessibility")
        print("  - Keyword relevance")


async def test_specific_keyword():
    """Test with a specific keyword for debugging"""
    
    print("\n🔍 Testing specific keyword for debugging")
    print("=" * 50)
    
    # Test with a simple English keyword
    test_keyword = "DMK"
    
    collector = GoogleNewsCollector()
    config = PlatformConfig(
        enabled=True,
        language='en',  # English for broader results
        location='IN',  # India
        max_results=3
    )
    
    print(f"Testing keyword: '{test_keyword}'")
    print(f"Language: {config.language}, Location: {config.location}")
    
    async with collector:
        try:
            articles = []
            async for article in collector.search(test_keyword, config, max_results=3):
                articles.append(article)
                print(f"\n📰 Found article:")
                print(f"  Title: {article.get('title', 'N/A')}")
                print(f"  Source: {article.get('source', 'N/A')}")
                print(f"  URL: {article.get('url', 'N/A')}")
            
            print(f"\n✅ Collected {len(articles)} articles for '{test_keyword}'")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("Google News RSS Feed Test")
    print("=" * 30)
    
    # Run both tests
    asyncio.run(test_google_news_collection())
    asyncio.run(test_specific_keyword())