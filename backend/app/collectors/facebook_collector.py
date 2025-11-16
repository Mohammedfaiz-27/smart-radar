"""
Facebook data collector implementation
Uses RapidAPI Facebook Scraper endpoint for data collection
"""
from typing import Dict, Any, Optional, AsyncGenerator, List
from datetime import datetime, timedelta
import os
import asyncio
from app.collectors.base_collector import BaseCollector
from app.models.posts_table import PostCreate, Platform
from app.models.cluster import PlatformConfig

class FacebookCollector(BaseCollector):
    """Collector for Facebook platform"""
    
    def __init__(self):
        """Initialize Facebook collector with RapidAPI credentials"""
        api_key = os.getenv("FACEBOOK_RAPIDAPI_KEY")
        api_host = "facebook-scraper3.p.rapidapi.com"
        super().__init__(api_key=api_key, api_host=api_host)
        self.base_url = f"https://{api_host}"
        # Reduce rate limit delay for Facebook (from default 1.0s to 0.5s)
        self.rate_limit_delay = 0.5
        
    def get_platform(self) -> Platform:
        """Return platform identifier"""
        return Platform.FACEBOOK
    
    def get_api_endpoint(self) -> str:
        """Return API endpoint being used"""
        return f"{self.base_url}/search/posts"
    
    async def search(
        self,
        keyword: str,
        config: PlatformConfig,
        max_results: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Search Facebook for posts matching keyword
        
        Args:
            keyword: Search term or hashtag
            config: Platform configuration
            max_results: Maximum number of results
            
        Yields:
            Raw post data from Facebook API
        """
        if not self.api_key:
            self.logger.error("🔑 Facebook API key not configured")
            return
        
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host
        }
        
        # Use exact keyword as provided (cluster keywords are specific)
        query = keyword
        
        # Check if keyword contains Tamil characters for better targeting
        has_tamil = any('\u0B80' <= char <= '\u0BFF' for char in keyword)
        self.logger.debug(f"🔍 Facebook search for keyword: '{keyword}' (Tamil: {has_tamil})")
        
        params = {
            "query": query,
            "recent_posts": "true",  # Get recent posts
            "start_date": datetime.utcnow().strftime("%Y-%m-%d")  # Today's date
        }
        
        # Add location filter based on configuration
        if config.location:
            if "Tamil" in config.location:
                params["location_uid"] = "tamilnadu"  # Focus on Tamil Nadu region
        elif has_tamil:
            # For Tamil keywords, default to Tamil Nadu region
            params["location_uid"] = "tamilnadu"
        
        cursor = None
        total_fetched = 0
        page_count = 0
        max_pages = 2  # Reduced from 5 to 2 for faster collection (60-70% speed boost)
        
        self.logger.debug(f"📄 Starting Facebook pagination (max_pages: {max_pages}, max_results: {max_results})")
        
        while total_fetched < max_results and page_count < max_pages:
            page_start_time = datetime.utcnow()
            try:
                self.logger.debug(f"📖 Facebook page {page_count + 1}/{max_pages} (cursor: {'Yes' if cursor else 'None'})")
                
                # Add cursor for pagination
                if cursor:
                    params["cursor"] = cursor
                
                # Make API request
                response = await self.make_request(
                    f"{self.base_url}/search/posts",  # Use correct endpoint
                    headers=headers,
                    params=params
                )
                
                if not response:
                    self.logger.warning(f"🚫 No response from Facebook API for page {page_count + 1}")
                    break
                
                # Extract posts from response
                posts = response.get("results", [])
                page_duration = (datetime.utcnow() - page_start_time).total_seconds()
                
                if not posts:
                    self.logger.info(f"📭 No posts found for '{keyword}' on Facebook page {page_count + 1}")
                    break
                
                self.logger.debug(f"📦 Found {len(posts)} posts on page {page_count + 1} in {page_duration:.2f}s")
                
                posts_yielded_this_page = 0
                for post in posts:
                    # Check engagement threshold - use direct fields from API response
                    reactions = post.get("reactions_count", 0)
                    comments = post.get("comments_count", 0)
                    shares = post.get("reshare_count", 0)
                    total_engagement = reactions + comments + shares
                    
                    self.logger.debug(f"📊 Post engagement: {total_engagement} (reactions: {reactions}, comments: {comments}, shares: {shares}, threshold: {config.min_engagement})")
                    
                    if total_engagement >= config.min_engagement:
                        total_fetched += 1
                        posts_yielded_this_page += 1
                        yield post
                        
                        if total_fetched >= max_results:
                            self.logger.debug(f"✅ Reached max_results ({max_results}), stopping")
                            return
                
                self.logger.debug(f"📈 Page {page_count + 1} yielded {posts_yielded_this_page} posts (total: {total_fetched})")
                
                # Check for next page
                cursor = response.get("cursor")
                if not cursor:
                    self.logger.debug(f"🔚 No more pages available for '{keyword}' on Facebook")
                    break
                
                page_count += 1
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
                
            except Exception as e:
                page_duration = (datetime.utcnow() - page_start_time).total_seconds()
                self.logger.error(f"❌ Error searching Facebook for '{keyword}' on page {page_count + 1} after {page_duration:.2f}s: {e}")
                break
    
    def parse_post(self, raw_post: Dict[str, Any], cluster_id: str) -> PostCreate:
        """
        Parse Facebook API response into PostCreate model
        
        Args:
            raw_post: Raw post data from API
            cluster_id: Associated cluster ID
            
        Returns:
            PostCreate model
        """
        # Extract post ID 
        post_id = raw_post.get("post_id", raw_post.get("id", ""))
        self.logger.debug(f"🆔 Parsing Facebook post: {post_id}")
        
        # Extract text content
        message = raw_post.get("message", raw_post.get("text", ""))
        self.logger.debug(f"📝 Post text length: {len(message) if message else 0} chars")
        
        # Extract author info
        author = raw_post.get("author", {})
        if isinstance(author, dict):
            author_username = author.get("name", "unknown")
            author_id = author.get("id", "")
        else:
            author_username = str(author) if author else "unknown"
            author_id = ""
        
        # Get follower count (may not be available)
        author_followers = raw_post.get("author_followers", 0)
        
        # Build post URL
        post_url = raw_post.get("url", "")
        if not post_url and post_id:
            post_url = f"https://www.facebook.com/{post_id}"
        
        # Parse datetime
        timestamp = raw_post.get("timestamp")
        if timestamp:
            posted_at = self.parse_facebook_datetime(timestamp)
        else:
            posted_at = datetime.utcnow()
        
        # Extract engagement metrics
        metrics = self.extract_engagement_metrics(raw_post)
        
        return PostCreate(
            platform_post_id=post_id,
            platform=Platform.FACEBOOK,
            cluster_id=cluster_id,
            author_username=author_username,
            author_followers=author_followers,
            post_text=self.clean_text(message),
            post_url=post_url,
            posted_at=posted_at,
            likes=metrics["likes"],
            comments=metrics["comments"],
            shares=metrics["shares"],
            views=metrics["views"]
        )
    
    def extract_engagement_metrics(self, raw_post: Dict[str, Any]) -> Dict[str, int]:
        """Extract engagement metrics from Facebook post"""
        # Use direct fields from API response
        likes = raw_post.get("reactions_count", 0)
        comments = raw_post.get("comments_count", 0) 
        shares = raw_post.get("reshare_count", 0)
        views = raw_post.get("view_count", 0)
        
        # Ensure all values are integers
        try:
            likes = int(likes) if likes else 0
            comments = int(comments) if comments else 0
            shares = int(shares) if shares else 0
            views = int(views) if views else 0
        except (ValueError, TypeError):
            # Fallback to 0 if conversion fails
            likes = comments = shares = views = 0
        
        return {
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "views": views
        }
    
    def parse_facebook_datetime(self, timestamp: Any) -> datetime:
        """
        Parse Facebook datetime format
        Can be Unix timestamp or ISO format
        """
        try:
            if isinstance(timestamp, (int, float)):
                # Unix timestamp
                return datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, str):
                # Try ISO format
                if "T" in timestamp:
                    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                else:
                    # Try other common formats
                    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        except:
            pass
        
        return datetime.utcnow()
    
    async def get_page_posts(
        self,
        page_id: str,
        config: PlatformConfig,
        max_results: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Get posts from a specific Facebook page
        
        Args:
            page_id: Facebook page ID or username
            config: Platform configuration  
            max_results: Maximum number of results
            
        Yields:
            Raw post data from page
        """
        if not self.api_key:
            self.logger.error("🔑 Facebook API key not configured")
            return
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }
        
        params = {
            "page_id": page_id,
            "limit": str(min(max_results, 50))  # API limit
        }
        
        try:
            # Get page posts
            response = await self.make_request(
                f"{self.base_url}/page-posts",
                headers=headers,
                params=params
            )
            
            if not response:
                return
            
            # Extract posts
            posts = response.get("data", [])
            
            total_fetched = 0
            for post in posts:
                # Check engagement threshold - use direct fields from API response
                reactions = post.get("reactions_count", 0)
                comments = post.get("comments_count", 0)
                shares = post.get("reshare_count", 0)
                total_engagement = reactions + comments + shares
                
                if total_engagement >= config.min_engagement:
                    total_fetched += 1
                    yield post
                    
                    if total_fetched >= max_results:
                        return
                        
        except Exception as e:
            self.logger.error(f"❌ Error getting posts for page '{page_id}': {e}")
    
    async def get_group_posts(
        self,
        group_id: str,
        config: PlatformConfig,
        max_results: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Get posts from a specific Facebook group
        
        Args:
            group_id: Facebook group ID
            config: Platform configuration
            max_results: Maximum number of results
            
        Yields:
            Raw post data from group
        """
        if not self.api_key:
            self.logger.error("🔑 Facebook API key not configured")
            return
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }
        
        params = {
            "group_id": group_id,
            "limit": str(min(max_results, 50))
        }
        
        try:
            # Get group posts
            response = await self.make_request(
                f"{self.base_url}/group-posts",
                headers=headers,
                params=params
            )
            
            if not response:
                return
            
            # Extract posts
            posts = response.get("data", [])
            
            total_fetched = 0
            for post in posts:
                total_fetched += 1
                yield post
                
                if total_fetched >= max_results:
                    return
                    
        except Exception as e:
            self.logger.error(f"❌ Error getting posts for group '{group_id}': {e}")