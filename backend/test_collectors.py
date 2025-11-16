#!/usr/bin/env python3
"""
Test script to verify individual collectors are working
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / '.env')

from app.collectors.facebook_collector import FacebookCollector
from app.collectors.youtube_collector import YouTubeCollector
from app.collectors.x_collector import XCollector
from app.models.cluster import PlatformConfig

async def test_facebook_collector():
    """Test Facebook collector"""
    print("Testing Facebook Collector...")
    api_key = os.getenv("FACEBOOK_RAPIDAPI_KEY")
    print(f"Facebook API Key: {'*' * 20 if api_key else 'NOT SET'}")
    
    config = PlatformConfig(
        enabled=True,
        max_results=5,
        min_engagement=1,
        language="ta",
        location="Tamil Nadu"
    )
    
    try:
        collector = FacebookCollector()
        async with collector:
            posts = []
            async for post in collector.search("DMK", config, max_results=3):
                posts.append(post)
                print(f"Found Facebook post: {post.get('message', 'No message')[:50]}...")
                if len(posts) >= 3:
                    break
        print(f"Facebook: Found {len(posts)} posts")
        return len(posts) > 0
    except Exception as e:
        print(f"Facebook error: {e}")
        return False

async def test_youtube_collector():
    """Test YouTube collector"""
    print("\nTesting YouTube Collector...")
    api_key = os.getenv("YOUTUBE_API_KEY")
    print(f"YouTube API Key: {'*' * 20 if api_key else 'NOT SET'}")
    
    config = PlatformConfig(
        enabled=True,
        max_results=5,
        min_engagement=1,
        language="ta",
        location="Tamil Nadu"
    )
    
    try:
        collector = YouTubeCollector()
        async with collector:
            posts = []
            async for post in collector.search("DMK", config, max_results=3):
                posts.append(post)
                snippet = post.get('snippet', {})
                title = snippet.get('title', 'No title')
                print(f"Found YouTube video: {title[:50]}...")
                if len(posts) >= 3:
                    break
        print(f"YouTube: Found {len(posts)} posts")
        return len(posts) > 0
    except Exception as e:
        print(f"YouTube error: {e}")
        return False

async def test_x_collector():
    """Test X collector"""
    print("\nTesting X Collector...")
    api_key = os.getenv("X_RAPIDAPI_KEY")
    print(f"X API Key: {'*' * 20 if api_key else 'NOT SET'}")
    
    config = PlatformConfig(
        enabled=True,
        max_results=5,
        min_engagement=1,
        language="ta",
        location="Tamil Nadu"
    )
    
    try:
        collector = XCollector()
        async with collector:
            posts = []
            async for post in collector.search("DMK", config, max_results=3):
                posts.append(post)
                legacy = post.get('legacy', {})
                text = legacy.get('full_text', 'No text')
                print(f"Found X post: {text[:50]}...")
                if len(posts) >= 3:
                    break
        print(f"X: Found {len(posts)} posts")
        return len(posts) > 0
    except Exception as e:
        print(f"X error: {e}")
        return False

async def main():
    """Test all collectors"""
    print("Testing all collectors individually...")
    
    results = {}
    results['facebook'] = await test_facebook_collector()
    results['youtube'] = await test_youtube_collector()
    results['x'] = await test_x_collector()
    
    print("\n" + "="*50)
    print("COLLECTOR TEST RESULTS")
    print("="*50)
    for platform, working in results.items():
        status = "✓ WORKING" if working else "✗ FAILED"
        print(f"{platform.upper()}: {status}")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())