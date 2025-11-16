"""
X (Twitter) data collector implementation
Uses RapidAPI Twitter endpoint for data collection
"""
from typing import Dict, Any, Optional, AsyncGenerator, List
from datetime import datetime, timedelta
import os
import asyncio
from app.collectors.base_collector import BaseCollector
from app.models.posts_table import PostCreate, Platform
from app.models.cluster import PlatformConfig

class XCollector(BaseCollector):
    """Collector for X (Twitter) platform"""
    
    def __init__(self):
        """Initialize X collector with RapidAPI credentials"""
        api_key = os.getenv("X_RAPIDAPI_KEY")
        api_host = "twitter241.p.rapidapi.com"
        super().__init__(api_key=api_key, api_host=api_host)
        self.base_url = f"https://{api_host}"
        
    def get_platform(self) -> Platform:
        """Return platform identifier"""
        return Platform.X
    
    def get_api_endpoint(self) -> str:
        """Return API endpoint being used"""
        return f"{self.base_url}/search-v2"
    
    async def search(
        self,
        keyword: str,
        config: PlatformConfig,
        max_results: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Search X for posts matching keyword
        
        Args:
            keyword: Search term or hashtag
            config: Platform configuration
            max_results: Maximum number of results
            
        Yields:
            Raw post data from X API
        """
        if not self.api_key:
            self.logger.error("🔑 X API key not configured")
            return
        
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host
        }
        
        # Use exact keyword as provided (cluster keywords are already specific)
        search_query = keyword
        
        # Check if keyword contains Tamil characters
        has_tamil = any('\u0B80' <= char <= '\u0BFF' for char in keyword)
        self.logger.debug(f"🔍 X search for keyword: '{keyword}' (Tamil: {has_tamil})")
        
        # Build query with filters - improved Tamil handling
        if config.language and config.language != "auto":
            search_query += f" lang:{config.language}"
        elif has_tamil:
            # For Tamil keywords, prefer Tamil content but don't restrict completely
            # This allows mixed language posts to be found
            self.logger.debug("🇮🇳 Tamil keyword detected - optimizing for Tamil content")
        else:
            # For English keywords, don't add language filter to get broader results
            pass
        
        # Add location if specified (for X, this might be in bio or tweet text)
        if config.location and "Tamil" in config.location:
            # Use location terms that work well with Tamil content
            search_query += f" (Tamil Nadu OR TamilNadu OR TN)"
        
        params = {
            "query": search_query,
            "type": "Latest",  # Get latest tweets
            "count": str(min(max_results, 100))  # Updated to match your requirement
        }
        
        cursor = None
        total_fetched = 0
        page_count = 0
        max_pages = (max_results // 40) + 1
        
        self.logger.debug(f"📄 Starting X pagination (max_pages: {max_pages}, max_results: {max_results})")
        self.logger.debug(f"   Search query: '{search_query}'")
        
        while total_fetched < max_results and page_count < max_pages:
            page_start_time = datetime.utcnow()
            try:
                self.logger.debug(f"📖 X page {page_count + 1}/{max_pages} (cursor: {'Yes' if cursor else 'None'})")
                
                # Add cursor for pagination
                if cursor:
                    params["cursor"] = cursor
                
                # Make API request
                response = await self.make_request(
                    f"{self.base_url}/search-v2",
                    headers=headers,
                    params=params
                )
                
                if not response:
                    self.logger.warning(f"🚫 No response from X API for page {page_count + 1}")
                    break
                
                # Extract tweets from response
                result = response.get("result", {})
                timeline = result.get("timeline", {})
                instructions = timeline.get("instructions", [])
                page_duration = (datetime.utcnow() - page_start_time).total_seconds()
                
                self.logger.debug(f"📦 X response structure - result: {bool(result)}, timeline: {bool(timeline)}, instructions: {len(instructions)} items")
                
                tweets_found = False
                tweets_on_page = 0
                for instruction in instructions:
                    if instruction.get("type") == "TimelineAddEntries":
                        entries = instruction.get("entries", [])
                        self.logger.debug(f"   📝 Processing {len(entries)} timeline entries")
                        
                        for entry in entries:
                            # Skip non-tweet entries
                            if not entry.get("entryId", "").startswith("tweet-"):
                                # Check for cursor
                                if "cursor-bottom" in entry.get("entryId", ""):
                                    content = entry.get("content", {})
                                    cursor_content = content.get("value")
                                    if cursor_content:
                                        cursor = cursor_content
                                continue
                            
                            # Extract tweet data
                            tweet_content = entry.get("content", {})
                            tweet_result = tweet_content.get("itemContent", {}).get("tweet_results", {}).get("result", {})
                            
                            if tweet_result and tweet_result.get("__typename") == "Tweet":
                                tweets_found = True
                                tweets_on_page += 1
                                total_fetched += 1
                                
                                # Check engagement threshold
                                legacy = tweet_result.get("legacy", {})
                                engagement = (
                                    legacy.get("favorite_count", 0) +
                                    legacy.get("retweet_count", 0) +
                                    legacy.get("reply_count", 0)
                                )
                                
                                self.logger.debug(f"🐦 Tweet engagement: {engagement} (likes: {legacy.get('favorite_count', 0)}, retweets: {legacy.get('retweet_count', 0)}, replies: {legacy.get('reply_count', 0)}, threshold: {config.min_engagement})")
                                
                                if engagement >= config.min_engagement:
                                    yield tweet_result
                                
                                if total_fetched >= max_results:
                                    self.logger.debug(f"✅ Reached max_results ({max_results}), stopping")
                                    return
                
                page_duration = (datetime.utcnow() - page_start_time).total_seconds()
                self.logger.debug(f"📈 Page {page_count + 1} found {tweets_on_page} tweets in {page_duration:.2f}s (total: {total_fetched})")
                
                if not tweets_found or not cursor:
                    self.logger.debug(f"🔚 No more tweets available for '{keyword}' (tweets_found: {tweets_found}, cursor: {bool(cursor)})")
                    break
                
                page_count += 1
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
                
            except Exception as e:
                page_duration = (datetime.utcnow() - page_start_time).total_seconds()
                self.logger.error(f"❌ Error searching X for '{keyword}' on page {page_count + 1} after {page_duration:.2f}s: {e}")
                break
    
    def parse_post(self, raw_post: Dict[str, Any], cluster_id: str) -> PostCreate:
        """
        Parse X API response into PostCreate model
        
        Args:
            raw_post: Raw tweet data from API
            cluster_id: Associated cluster ID
            
        Returns:
            PostCreate model
        """
        # Extract legacy data
        legacy = raw_post.get("legacy", {})
        
        # Extract user data
        user_results = raw_post.get("core", {}).get("user_results", {}).get("result", {})
        user_legacy = user_results.get("legacy", {})
        
        # Parse tweet ID
        tweet_id = raw_post.get("rest_id", "")
        self.logger.debug(f"🆔 Parsing X tweet: {tweet_id}")
        
        # Parse text content - ensure Unicode preservation
        full_text = legacy.get("full_text", "")
        
        # Check if text contains Tamil characters
        has_tamil_text = any('\u0B80' <= char <= '\u0BFF' for char in full_text) if full_text else False
        self.logger.debug(f"📝 Tweet text length: {len(full_text) if full_text else 0} chars (Tamil: {has_tamil_text})")
        
        # Log Tamil content for debugging
        if has_tamil_text:
            self.logger.info(f"🇮🇳 Found Tamil tweet: {full_text[:100]}{'...' if len(full_text) > 100 else ''}")
        
        # Parse author info
        author_username = user_legacy.get("screen_name", "unknown")
        author_followers = user_legacy.get("followers_count", 0)
        
        # Build tweet URL
        post_url = f"https://twitter.com/{author_username}/status/{tweet_id}"
        
        # Parse datetime
        created_at_str = legacy.get("created_at", "")
        posted_at = self.parse_x_datetime(created_at_str)
        
        # Extract engagement metrics
        metrics = self.extract_engagement_metrics(raw_post)
        
        return PostCreate(
            platform_post_id=tweet_id,
            platform=Platform.X,
            cluster_id=cluster_id,
            author_username=author_username,
            author_followers=author_followers,
            post_text=self.clean_text(full_text),
            post_url=post_url,
            posted_at=posted_at,
            likes=metrics["likes"],
            comments=metrics["comments"],
            shares=metrics["shares"],
            views=metrics["views"]
        )
    
    def extract_engagement_metrics(self, raw_post: Dict[str, Any]) -> Dict[str, int]:
        """Extract engagement metrics from X post"""
        legacy = raw_post.get("legacy", {})
        
        # Get view count from different possible locations
        views = raw_post.get("views", {}).get("count")
        if isinstance(views, str):
            views = int(views) if views.isdigit() else 0
        elif not views:
            views = 0
        
        return {
            "likes": legacy.get("favorite_count", 0),
            "comments": legacy.get("reply_count", 0),
            "shares": legacy.get("retweet_count", 0),
            "views": views
        }
    
    def parse_x_datetime(self, date_str: str) -> datetime:
        """
        Parse X datetime format
        Example: "Mon Jan 15 14:23:01 +0000 2024"
        """
        try:
            return datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
        except:
            return datetime.utcnow()
    
    async def get_user_posts(
        self,
        username: str,
        config: PlatformConfig,
        max_results: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Get posts from a specific user
        
        Args:
            username: X username (without @)
            config: Platform configuration
            max_results: Maximum number of results
            
        Yields:
            Raw post data from user timeline
        """
        if not self.api_key:
            self.logger.error("🔑 X API key not configured")
            return
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }
        
        params = {
            "username": username.replace("@", ""),
            "include_replies": "false",
            "include_retweets": "false"
        }
        
        try:
            # Get user timeline
            response = await self.make_request(
                f"{self.base_url}/user-tweets",
                headers=headers,
                params=params
            )
            
            if not response:
                return
            
            # Extract tweets
            result = response.get("result", {})
            timeline = result.get("timeline_v2", {}).get("timeline", {})
            instructions = timeline.get("instructions", [])
            
            total_fetched = 0
            for instruction in instructions:
                if instruction.get("type") == "TimelineAddEntries":
                    entries = instruction.get("entries", [])
                    
                    for entry in entries:
                        if not entry.get("entryId", "").startswith("tweet-"):
                            continue
                        
                        tweet_content = entry.get("content", {})
                        tweet_result = tweet_content.get("itemContent", {}).get("tweet_results", {}).get("result", {})
                        
                        if tweet_result:
                            total_fetched += 1
                            yield tweet_result
                            
                            if total_fetched >= max_results:
                                return
                                
        except Exception as e:
            self.logger.error(f"❌ Error getting posts for user '{username}': {e}")