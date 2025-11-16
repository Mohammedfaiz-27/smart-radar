#!/usr/bin/env python3
"""
Test API connections for all platforms
"""
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_x_api():
    """Test X (Twitter) API connection"""
    api_key = os.getenv("X_RAPIDAPI_KEY")
    if not api_key:
        print("❌ X_RAPIDAPI_KEY not found in .env")
        return False
    
    print(f"✓ X API Key found: {api_key[:10]}...")
    
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "twitter241.p.rapidapi.com"
    }
    
    url = "https://twitter241.p.rapidapi.com/search-v2"
    params = {
        "query": "test",
        "type": "Latest",
        "count": "1"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✓ X API connection successful")
                    return True
                else:
                    print(f"❌ X API error: {response.status}")
                    text = await response.text()
                    print(f"   Response: {text[:200]}")
                    return False
    except Exception as e:
        print(f"❌ X API connection failed: {e}")
        return False

async def test_facebook_api():
    """Test Facebook API connection"""
    api_key = os.getenv("FACEBOOK_RAPIDAPI_KEY")
    if not api_key:
        print("❌ FACEBOOK_RAPIDAPI_KEY not found in .env")
        return False
    
    print(f"✓ Facebook API Key found: {api_key[:10]}...")
    
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "facebook-scraper3.p.rapidapi.com"
    }
    
    url = "https://facebook-scraper3.p.rapidapi.com/search"
    params = {
        "query": "test",
        "recent_posts": "true"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✓ Facebook API connection successful")
                    return True
                else:
                    print(f"❌ Facebook API error: {response.status}")
                    text = await response.text()
                    print(f"   Response: {text[:200]}")
                    return False
    except Exception as e:
        print(f"❌ Facebook API connection failed: {e}")
        return False

async def test_youtube_api():
    """Test YouTube API connection"""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("❌ YOUTUBE_API_KEY not found in .env")
        return False
    
    print(f"✓ YouTube API Key found: {api_key[:10]}...")
    
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": api_key,
        "q": "test",
        "part": "snippet",
        "maxResults": 1,
        "type": "video"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✓ YouTube API connection successful")
                    return True
                else:
                    print(f"❌ YouTube API error: {response.status}")
                    text = await response.text()
                    print(f"   Response: {text[:200]}")
                    return False
    except Exception as e:
        print(f"❌ YouTube API connection failed: {e}")
        return False

async def test_gemini_api():
    """Test Gemini API connection"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env")
        return False
    
    print(f"✓ Gemini API Key found: {api_key[:10]}...")
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Say 'test successful' in 3 words")
        print("✓ Gemini API connection successful")
        return True
    except Exception as e:
        print(f"❌ Gemini API connection failed: {e}")
        return False

async def main():
    """Test all API connections"""
    print("="*60)
    print("TESTING API CONNECTIONS")
    print("="*60)
    print()
    
    print("1. Testing X (Twitter) API...")
    x_ok = await test_x_api()
    print()
    
    print("2. Testing Facebook API...")
    fb_ok = await test_facebook_api()
    print()
    
    print("3. Testing YouTube API...")
    yt_ok = await test_youtube_api()
    print()
    
    print("4. Testing Gemini API...")
    gemini_ok = await test_gemini_api()
    print()
    
    print("="*60)
    print("SUMMARY")
    print("="*60)
    print(f"X (Twitter): {'✓ Working' if x_ok else '❌ Failed'}")
    print(f"Facebook: {'✓ Working' if fb_ok else '❌ Failed'}")
    print(f"YouTube: {'✓ Working' if yt_ok else '❌ Failed'}")
    print(f"Gemini: {'✓ Working' if gemini_ok else '❌ Failed'}")
    print()
    
    if all([x_ok, fb_ok, yt_ok, gemini_ok]):
        print("✅ All API connections working! Ready to fetch data.")
    else:
        print("⚠️ Some APIs are not working. Check your API keys in .env file.")

if __name__ == "__main__":
    asyncio.run(main())