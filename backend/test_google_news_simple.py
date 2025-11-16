#!/usr/bin/env python3
"""
Simple test script for Google News RSS feed collection
Tests without database dependency
"""
import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.collectors.google_news_collector import GoogleNewsCollector
from app.models.cluster import PlatformConfig


async def test_google_news_simple():
    """Simple test with hardcoded keywords"""
    
    print("🔍 Testing Google News RSS Feed Collection")
    print("=" * 60)
    
    # Test keywords from our clusters
    test_keywords = [
        "DMK",
        "திராவிட மாடல்",  # Tamil keyword
        "AIADMK",
        "Palaniswami"
    ]
    
    print(f"📊 Testing with keywords: {test_keywords}")
    
    # Create Google News collector
    collector = GoogleNewsCollector()
    
    # Create platform config for Indian news
    config = PlatformConfig(
        enabled=True,
        language='ta',  # Tamil
        location='IN',  # India
        max_results=3   # Limit for testing
    )
    
    print(f"\n🌐 Platform config:")
    print(f"  Language: {config.language}")
    print(f"  Location: {config.location}")
    print(f"  Max results: {config.max_results}")
    
    total_articles = 0
    
    # Test collection for each keyword
    async with collector:
        for i, keyword in enumerate(test_keywords):
            print(f"\n--- Testing keyword {i+1}/{len(test_keywords)}: '{keyword}' ---")
            
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
                        post = collector.parse_post(article, "test_cluster_id")
                        print(f"  ✅ Successfully parsed to PostCreate model")
                        print(f"     Platform: {post.platform}")
                        print(f"     Content length: {len(post.content)} chars")
                    except Exception as parse_error:
                        print(f"  ❌ Error parsing to PostCreate: {parse_error}")
                
                print(f"\n✅ Collected {article_count} articles for keyword '{keyword}'")
                
                # Add delay between keywords to be respectful
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"\n❌ Error collecting for keyword '{keyword}': {e}")
                import traceback
                traceback.print_exc()
    
    print(f"\n🎉 Test Complete!")
    print(f"Total articles collected: {total_articles}")
    print(f"Keywords tested: {len(test_keywords)}")
    
    if total_articles > 0:
        print("\n✅ Google News RSS collection is working!")
        print("Ready to integrate into automated pipeline.")
    else:
        print("\n⚠️  No articles collected. Check:")
        print("  - Internet connection")
        print("  - RSS feed accessibility")
        print("  - Keyword relevance")


if __name__ == "__main__":
    print("Google News RSS Feed Test (Simple)")
    print("=" * 40)
    
    # Run test
    asyncio.run(test_google_news_simple())