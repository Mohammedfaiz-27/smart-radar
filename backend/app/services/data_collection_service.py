"""
Data collection service for social media platforms
"""
import os
import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.models.social_post import SocialPostCreate
from app.services.social_post_service import SocialPostService
from app.services.intelligence_service import IntelligenceService
from app.services.cluster_service import ClusterService
from app.core.database import connect_to_mongo, close_mongo_connection

class DataCollectionService:
    def __init__(self):
        self.post_service = SocialPostService()
        self.intelligence_service = IntelligenceService()
        self.cluster_service = ClusterService()
        
        # API Configuration
        self.twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.x_rapidapi_key = os.getenv("X_RAPIDAPI_KEY")
        self.facebook_rapidapi_key = os.getenv("FACEBOOK_RAPIDAPI_KEY")
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        
        
        # Session for HTTP requests
        self.session = None
        
        # API Endpoints - Updated to correct RapidAPI hosts
        self.x_api_host = "twitter241.p.rapidapi.com"
        self.facebook_api_host = "facebook-scraper3.p.rapidapi.com"
        self.youtube_base_url = "https://www.googleapis.com/youtube/v3"
    
    async def __aenter__(self):
        # Initialize database connection
        await connect_to_mongo()
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        await close_mongo_connection()
    
    async def collect_posts_for_cluster(self, cluster_id: str, keywords: List[str], 
                                      platforms: List[str] = None) -> List[str]:
        """Collect posts for a specific cluster across platforms with multi-perspective analysis"""
        if platforms is None:
            platforms = ["x", "facebook", "youtube", "instagram"]
        
        # Get cluster info to determine cluster_type
        cluster = await self.cluster_service.get_cluster(cluster_id)
        if not cluster:
            print(f"Cluster {cluster_id} not found")
            return []
        
        cluster_type = cluster.cluster_type
        
        # Get ALL clusters for multi-perspective analysis
        all_clusters = await self.cluster_service.get_clusters()
        all_clusters_dict = [
            {
                "id": c.id,
                "name": c.name,
                "cluster_type": c.cluster_type,
                "keywords": c.keywords
            }
            for c in all_clusters
        ]
        
        # Process keywords - split if they are combined in a single string
        processed_keywords = []
        for keyword in keywords:
            if isinstance(keyword, str) and ' ' in keyword:
                # Split keywords that are combined with spaces
                split_keywords = [k.strip() for k in keyword.split() if k.strip().startswith('#')]
                processed_keywords.extend(split_keywords)
            else:
                processed_keywords.append(keyword)
        
        print(f"Cluster {cluster_id} ({cluster_type}): Processing keywords: {processed_keywords}")
        
        collected_post_ids = []
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            for platform in platforms:
                try:
                    if platform == "x" and self.x_rapidapi_key:
                        post_ids = await self._collect_x_posts(cluster_id, processed_keywords, cluster_type, all_clusters_dict)
                        collected_post_ids.extend(post_ids)
                    
                    elif platform == "facebook" and self.facebook_rapidapi_key:
                        post_ids = await self._collect_facebook_posts(cluster_id, processed_keywords, cluster_type, all_clusters_dict)
                        collected_post_ids.extend(post_ids)
                    
                    elif platform == "youtube" and self.youtube_api_key:
                        post_ids = await self._collect_youtube_posts(cluster_id, processed_keywords, cluster_type, all_clusters_dict)
                        collected_post_ids.extend(post_ids)
                    
                    else:
                        print(f"Skipping {platform} - no API token configured")
                
                except Exception as e:
                    print(f"Error collecting from {platform}: {e}")
                    continue
        
        return collected_post_ids
    
    async def _collect_x_posts(self, cluster_id: str, keywords: List[str], cluster_type: str, all_clusters: List[Dict]) -> List[str]:
        """Collect posts from X (Twitter) using RapidAPI"""
        post_ids = []
        
        url = f"https://{self.x_api_host}/search-v2"
        headers = {
            "X-RapidAPI-Key": self.x_rapidapi_key,
            "X-RapidAPI-Host": self.x_api_host
        }
        
        for keyword in keywords:
            print(f"X API: Searching for keyword: '{keyword}'")
            params = {
                "query": keyword,
                "type": "Latest",
                "count": "100"
            }
            
            try:
                async with self.session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Process tweets from RapidAPI response
                        result = data.get("result", {})
                        timeline = result.get("timeline", {})
                        instructions = timeline.get("instructions", [])
                        
                        for instruction in instructions:
                            if instruction.get("type") == "TimelineAddEntries":
                                entries = instruction.get("entries", [])
                                for entry in entries:
                                    if "tweet" in entry.get("entryId", ""):
                                        try:
                                            content = entry.get("content", {})
                                            item_content = content.get("itemContent", {})
                                            tweet_results = item_content.get("tweet_results", {})
                                            
                                            if "result" in tweet_results:
                                                tweet = tweet_results["result"]
                                                
                                                # Create post data with multi-perspective analysis
                                                post_data = await self._create_post_from_x(tweet, cluster_id, cluster_type, all_clusters)
                                                
                                                # Save post with intelligence analysis
                                                post_response = await self.post_service.create_post(post_data)
                                                post_ids.append(post_response.id)
                                        except Exception as e:
                                            print(f"Error processing tweet: {e}")
                                            continue
                    
                    else:
                        print(f"X API error for '{keyword}': {response.status}")
                        
            except Exception as e:
                print(f"X collection error for '{keyword}': {e}")
        
        return post_ids
    
    async def _collect_facebook_posts(self, cluster_id: str, keywords: List[str], cluster_type: str) -> List[str]:
        """Collect posts from Facebook using RapidAPI with pagination"""
        post_ids = []
        
        url = f"https://{self.facebook_api_host}/search/posts"
        
        # Ensure no None values in headers
        if not self.facebook_rapidapi_key:
            print("WARNING: Facebook RapidAPI key is not set")
            return []
        
        headers = {
            "X-RapidAPI-Key": self.facebook_rapidapi_key,
            "X-RapidAPI-Host": self.facebook_api_host
        }
        
        print(f"Using headers: X-RapidAPI-Key: {self.facebook_rapidapi_key[:10]}..., Host: {self.facebook_api_host}")
        
        for keyword in keywords:
            print(f"Facebook API: Searching for keyword: '{keyword}'")
            cursor = None
            page_count = 0
            max_pages = 5  # Limit to 5 pages to avoid rate limits
            
            while page_count < max_pages:
                # Use today's date for recent posts
                today = datetime.utcnow().strftime("%Y-%m-%d")
                params = {
                    "query": keyword,
                    "recent_posts": "true",
                    "location_uid": "tamilnadu",
                    "start_date": today
                }
                
                # Add cursor for pagination - ensure it's not None
                if cursor and cursor.strip():
                    params["cursor"] = cursor
                
                try:
                    print(f"Making API call with params: {params}")
                    async with self.session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            print(f"\n=== Facebook API Response for '{keyword}' (Page {page_count + 1}) ===")
                            posts = data.get("results", [])
                            print(f"Posts found: {len(posts)}")
                            
                            # Process posts
                            page_post_count = 0
                            for i, post in enumerate(posts):
                                try:
                                    # Debug: Print post details to identify None fields
                                    print(f"Processing post {i+1}:")
                                    print(f"  Author: {post.get('author')}")
                                    print(f"  Message: {post.get('message', post.get('text', 'No content'))}")
                                    print(f"  URL: {post.get('url')}")
                                    print(f"  Timestamp: {post.get('timestamp')}")
                                    
                                    # Create post data
                                    post_data = await self._create_post_from_facebook(post, cluster_id, cluster_type)
                                    print(f"  Created post data successfully")
                                    
                                    # Save post with intelligence analysis
                                    post_response = await self.post_service.create_post(post_data)
                                    post_ids.append(post_response.id)
                                    page_post_count += 1
                                    print(f"✓ Saved Facebook post {page_post_count}: {post_response.id}")
                                except Exception as e:
                                    print(f"Error processing Facebook post {i+1}: {e}")
                                    import traceback
                                    traceback.print_exc()
                                    continue
                            
                            # Check for next page
                            cursor = data.get("cursor")
                            if not cursor or len(posts) == 0:
                                print(f"No more pages available for '{keyword}'")
                                break
                            
                            page_count += 1
                            print(f"Found cursor for next page: {cursor[:50]}...")
                        
                        else:
                            print(f"Facebook API error for '{keyword}': {response.status}")
                            break
                            
                except Exception as e:
                    print(f"Facebook collection error for '{keyword}' page {page_count + 1}: {e}")
                    break
        
        return post_ids
    
    async def _collect_youtube_posts(self, cluster_id: str, keywords: List[str], cluster_type: str) -> List[str]:
        """Collect posts from YouTube Data API v3"""
        post_ids = []
        
        # Get date for filtering recent videos (last 30 days)
        published_after = (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z'
        
        for keyword in keywords:
            print(f"YouTube API: Searching for keyword: '{keyword}'")
            # YouTube search endpoint
            url = f"{self.youtube_base_url}/search"
            params = {
                "key": self.youtube_api_key,
                "q": keyword,
                "type": "video",
                "part": "snippet",
                "maxResults": 50,  # Increased from 20 to 50
                "order": "date",   # Changed from "relevance" to "date"
                "publishedAfter": published_after,  # Only videos from last 30 days
                "regionCode": "IN"  # Focus on Indian content
            }
            
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        videos = data.get("items", [])
                        video_ids = [video["id"]["videoId"] for video in videos if video.get("id", {}).get("videoId")]
                        
                        if video_ids:
                            # Get detailed video statistics
                            details_url = f"{self.youtube_base_url}/videos"
                            details_params = {
                                "key": self.youtube_api_key,
                                "id": ",".join(video_ids),
                                "part": "snippet,statistics,contentDetails"
                            }
                            
                            async with self.session.get(details_url, params=details_params) as details_response:
                                if details_response.status == 200:
                                    details_data = await details_response.json()
                                    detailed_videos = details_data.get("items", [])
                                    
                                    for video in detailed_videos:
                                        # Create post data
                                        post_data = await self._create_post_from_youtube(video, cluster_id, cluster_type)
                                        
                                        # Save post with intelligence analysis
                                        post_response = await self.post_service.create_post(post_data)
                                        post_ids.append(post_response.id)
                    
                    else:
                        print(f"YouTube API error for '{keyword}': {response.status}")
                        
            except Exception as e:
                print(f"YouTube collection error for '{keyword}': {e}")
        
        return post_ids
    
    async def _create_post_from_x(self, tweet: Dict[str, Any], cluster_id: str, cluster_type: str, all_clusters: List[Dict]) -> SocialPostCreate:
        """Convert X (Twitter) RapidAPI response to SocialPostCreate"""
        
        # Extract tweet legacy data
        legacy = tweet.get("legacy", {})
        
        # Extract engagement metrics
        engagement_metrics = {
            "likes": legacy.get("favorite_count", 0),
            "shares": legacy.get("retweet_count", 0),
            "comments": legacy.get("reply_count", 0),
            "retweets": legacy.get("retweet_count", 0)
        }
        
        # Extract user data
        user_results = tweet.get("core", {}).get("user_results", {})
        user_result = user_results.get("result", {})
        user_legacy = user_result.get("legacy", {})
        
        # Create author string
        author = user_legacy.get("screen_name", "unknown")
        
        # Get content text
        content = legacy.get("full_text", "")
        
        # Analyze content against ALL clusters for multi-perspective analysis
        matched_clusters = await self.intelligence_service.detect_matched_clusters(
            content, 
            all_clusters
        )
        
        # Determine perspective type
        own_clusters = [c for c in matched_clusters if c.cluster_type == "own"]
        competitor_clusters = [c for c in matched_clusters if c.cluster_type == "competitor"]
        
        if len(own_clusters) > 0 and len(competitor_clusters) > 0:
            perspective_type = "multi-perspective"
        elif len(own_clusters) > 0:
            perspective_type = "own"
        elif len(competitor_clusters) > 0:
            perspective_type = "competitor"
        else:
            perspective_type = "single"
        
        # Perform appropriate intelligence analysis
        if len(matched_clusters) > 1:
            # Multi-perspective analysis
            intelligence = await self.intelligence_service.analyze_multi_perspective_content(
                content,
                "social_post",
                matched_clusters
            )
        else:
            # Single perspective analysis (existing logic)
            intelligence = await self.intelligence_service.analyze_post(
                content, 
                engagement_metrics
            )
        
        return SocialPostCreate(
            platform="x",
            author=author,
            content=content,
            post_url=f"https://x.com/{author}/status/{legacy.get('id_str', '')}",
            posted_at=datetime.utcnow(),
            engagement_metrics=engagement_metrics,
            intelligence=intelligence,
            # Legacy fields for backward compatibility
            cluster_id=cluster_id,
            cluster_type=cluster_type,
            # New multi-perspective fields
            matched_clusters=[
                {
                    "cluster_id": mc.cluster_id,
                    "cluster_name": mc.cluster_name,
                    "cluster_type": mc.cluster_type,
                    "keywords_matched": mc.keywords_matched
                }
                for mc in matched_clusters
            ],
            perspective_type=perspective_type
        )
    
    async def _create_post_from_facebook(self, post: Dict[str, Any], cluster_id: str, cluster_type: str) -> SocialPostCreate:
        """Convert Facebook RapidAPI response to SocialPostCreate"""
        
        # Extract engagement metrics from RapidAPI format - ensure no None values
        reactions = post.get("reactions_count", 0) or 0
        engagement_metrics = {
            "likes": reactions,
            "shares": post.get("reshare_count", 0) or 0, 
            "comments": post.get("comments_count", 0) or 0,
            "retweets": 0  # Facebook doesn't have retweets
        }
        
        # Create author string from nested author object - handle None case
        author_obj = post.get("author", {})
        if author_obj is None:
            author = "Facebook User"
        elif isinstance(author_obj, dict):
            author = author_obj.get("name", "Facebook User") or "Facebook User"
        else:
            author = str(author_obj) if author_obj else "Facebook User"
        
        # Get content text - ensure not None
        content = post.get("message", post.get("text", "")) or "No content available"
        
        # Get intelligence analysis
        intelligence = await self.intelligence_service.analyze_post(
            content, 
            engagement_metrics
        )
        
        # Parse timestamp from Facebook post
        timestamp = post.get("timestamp", 0)
        if timestamp:
            posted_at = datetime.fromtimestamp(timestamp)
        else:
            posted_at = datetime.utcnow()
        
        return SocialPostCreate(
            platform="facebook",
            cluster_id=cluster_id,
            cluster_type=cluster_type,
            author=author,
            content=content,
            post_url=post.get("url") or post.get("post_url") or "https://facebook.com",
            posted_at=posted_at,
            engagement_metrics=engagement_metrics,
            intelligence=intelligence
        )
    
    async def _create_post_from_youtube(self, video: Dict[str, Any], cluster_id: str, cluster_type: str) -> SocialPostCreate:
        """Convert YouTube API response to SocialPostCreate"""
        
        # Extract engagement metrics
        statistics = video.get("statistics", {})
        engagement_metrics = {
            "likes": int(statistics.get("likeCount", 0)),
            "shares": 0,  # YouTube API doesn't provide direct share count
            "comments": int(statistics.get("commentCount", 0)),
            "retweets": 0
        }
        
        # Create author from channel info
        snippet = video.get("snippet", {})
        author = snippet.get("channelTitle", "Unknown Channel")
        
        # Create content text
        title = snippet.get("title", "")
        description = snippet.get("description", "")
        content = f"{title}\n\n{description}"
        
        # Parse actual video publish date
        published_at_str = snippet.get("publishedAt", "")
        if published_at_str:
            # YouTube API returns ISO format: "2024-09-19T10:30:00Z"
            try:
                posted_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00')).replace(tzinfo=None)
            except:
                posted_at = datetime.utcnow()
        else:
            posted_at = datetime.utcnow()
        
        # Get intelligence analysis
        intelligence = await self.intelligence_service.analyze_post(
            content, 
            engagement_metrics
        )
        
        return SocialPostCreate(
            platform="youtube",
            cluster_id=cluster_id,
            cluster_type=cluster_type,
            author=author,
            content=content,
            post_url=f"https://www.youtube.com/watch?v={video['id']}",
            posted_at=posted_at,  # Use actual video upload date
            engagement_metrics=engagement_metrics,
            intelligence=intelligence
        )
    
    async def collect_posts_batch(self, clusters: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Collect posts for multiple clusters in batch"""
        results = {}
        
        # Collect from all clusters concurrently
        tasks = []
        for cluster in clusters:
            task = self.collect_posts_for_cluster(
                cluster["id"], 
                cluster["keywords"], 
                cluster.get("platforms", ["x", "facebook", "youtube"])
            )
            tasks.append((cluster["id"], task))
        
        # Execute all collection tasks
        for cluster_id, task in tasks:
            try:
                post_ids = await task
                results[cluster_id] = post_ids
                print(f"Collected {len(post_ids)} posts for cluster {cluster_id}")
            except Exception as e:
                print(f"Failed to collect posts for cluster {cluster_id}: {e}")
                results[cluster_id] = []
        
        return results