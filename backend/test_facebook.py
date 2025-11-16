#!/usr/bin/env python3
"""
Debug Facebook collector specifically
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / '.env')

from app.collectors.facebook_collector import FacebookCollector
from app.models.cluster import PlatformConfig

async def debug_facebook():
    """Debug Facebook collector with detailed output"""
    print("Debugging Facebook Collector...")
    
    api_key = os.getenv("FACEBOOK_RAPIDAPI_KEY")
    print(f"API Key: {api_key[:10]}...{api_key[-10:] if api_key else 'NOT SET'}")
    
    config = PlatformConfig(
        enabled=True,
        max_results=5,
        min_engagement=1,
        language="ta",
        location="Tamil Nadu"
    )
    
    collector = FacebookCollector()
    print(f"Base URL: {collector.base_url}")
    print(f"API Host: {collector.api_host}")
    print(f"Endpoint: {collector.get_api_endpoint()}")
    
    # Test manual API call
    try:
        headers = {
            "x-rapidapi-key": collector.api_key,
            "x-rapidapi-host": collector.api_host
        }
        
        params = {
            "query": "DMK",
            "recent_posts": "true",
            "location_uid": "tamilnadu"
        }
        
        print(f"\nTesting direct API call...")
        print(f"Headers: {headers}")
        print(f"Params: {params}")
        
        async with collector:
            response = await collector.make_request(
                f"{collector.base_url}/search/posts",
                headers=headers,
                params=params
            )
            print(f"Response: {response}")
            
            if response:
                posts = response.get("results", [])
                print(f"Found {len(posts)} posts in response")
                if posts:
                    print(f"First post: {posts[0]}")
            else:
                print("No response received")
                
    except Exception as e:
        print(f"API Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_facebook())