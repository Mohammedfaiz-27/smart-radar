"""
YouTube data collector implementation
Uses YouTube Data API v3 for data collection
"""
from typing import Dict, Any, Optional, AsyncGenerator, List
from datetime import datetime, timedelta
import os
import asyncio
from app.collectors.base_collector import BaseCollector
from app.models.posts_table import PostCreate, Platform
from app.models.cluster import PlatformConfig

class YouTubeCollector(BaseCollector):
    """Collector for YouTube platform"""
    
    def __init__(self):
        """Initialize YouTube collector with API credentials"""
        api_key = os.getenv("YOUTUBE_API_KEY")
        super().__init__(api_key=api_key)
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.rate_limit_delay = 0.5  # YouTube has generous quotas
        
    def get_platform(self) -> Platform:
        """Return platform identifier"""
        return Platform.YOUTUBE
    
    def get_api_endpoint(self) -> str:
        """Return API endpoint being used"""
        return f"{self.base_url}/search"
    
    async def search(
        self,
        keyword: str,
        config: PlatformConfig,
        max_results: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Search YouTube for videos matching keyword
        
        Args:
            keyword: Search term or hashtag (exact cluster keyword)
            config: Platform configuration
            max_results: Maximum number of results
            
        Yields:
            Raw video data from YouTube API
        """
        if not self.api_key:
            self.logger.error("🔑 YouTube API key not configured")
            return
        
        # Calculate date filter for recent videos (last 30 days)
        published_after = (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z'
        
        # Check if keyword contains Tamil characters
        has_tamil = any('\u0B80' <= char <= '\u0BFF' for char in keyword)
        self.logger.debug(f"🔍 YouTube search for keyword: '{keyword}' (Tamil: {has_tamil})")
        
        # Use exact keyword as provided (cluster keywords are already specific)
        params = {
            "key": self.api_key,
            "q": keyword,  # Use exact cluster keyword
            "type": "video",
            "part": "snippet",
            "maxResults": min(50, max_results),  # API max is 50 per request
            "order": "date",  # Get recent videos
            "publishedAfter": published_after,
            "regionCode": "IN",  # India region for Tamil Nadu content
        }
        
        # Add language preference for Tamil content if no specific language is set
        if config.language and config.language != "auto":
            params["relevanceLanguage"] = config.language
        elif has_tamil:
            # For Tamil keywords, prefer Tamil content but don't restrict completely
            params["relevanceLanguage"] = "ta"  # Tamil language preference
            self.logger.debug("🇮🇳 Tamil keyword detected - setting Tamil language preference")
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        next_page_token = None
        total_fetched = 0
        
        self.logger.debug(f"📄 Starting YouTube search with params: {params}")
        
        while total_fetched < max_results:
            page_start_time = datetime.utcnow()
            try:
                self.logger.debug(f"📖 YouTube search page (token: {'Yes' if next_page_token else 'None'})")
                
                # Add page token for pagination
                if next_page_token:
                    params["pageToken"] = next_page_token
                
                # Search for videos
                search_response = await self.make_request(
                    f"{self.base_url}/search",
                    params=params
                )
                
                if not search_response:
                    self.logger.warning(f"🚫 No response from YouTube search API")
                    break
                
                # Extract video IDs
                video_ids = []
                items = search_response.get("items", [])
                page_duration = (datetime.utcnow() - page_start_time).total_seconds()
                
                self.logger.debug(f"📦 YouTube search found {len(items)} videos in {page_duration:.2f}s")
                
                for item in items:
                    video_id = item.get("id", {}).get("videoId")
                    if video_id:
                        video_ids.append(video_id)
                
                if not video_ids:
                    self.logger.info(f"📭 No videos found for '{keyword}' on YouTube")
                    break
                
                # Get detailed statistics for videos
                self.logger.debug(f"📊 Getting statistics for {len(video_ids)} videos")
                video_details = await self.get_video_statistics(video_ids)
                
                # Combine search results with statistics
                for i, item in enumerate(items):
                    if i < len(video_details):
                        video_id = item.get("id", {}).get("videoId")
                        stats = video_details.get(video_id, {})
                        
                        # Check engagement threshold
                        view_count = int(stats.get("viewCount", 0))
                        like_count = int(stats.get("likeCount", 0))
                        comment_count = int(stats.get("commentCount", 0))
                        
                        total_engagement = like_count + comment_count
                        
                        self.logger.debug(f"📹 Video engagement: {total_engagement} (likes: {like_count}, comments: {comment_count}, views: {view_count}, threshold: {config.min_engagement})")
                        
                        if total_engagement >= config.min_engagement or view_count >= (config.min_engagement * 10):
                            # Combine snippet and statistics
                            combined_data = {
                                **item,
                                "statistics": stats,
                                "contentDetails": video_details.get(f"{video_id}_details", {})
                            }
                            
                            total_fetched += 1
                            yield combined_data
                            
                            if total_fetched >= max_results:
                                self.logger.debug(f"✅ Reached max_results ({max_results}), stopping")
                                return
                
                # Check for next page
                next_page_token = search_response.get("nextPageToken")
                if not next_page_token:
                    break
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
                
            except Exception as e:
                page_duration = (datetime.utcnow() - page_start_time).total_seconds()
                self.logger.error(f"❌ Error searching YouTube for '{keyword}' after {page_duration:.2f}s: {e}")
                break
    
    async def get_video_statistics(self, video_ids: List[str]) -> Dict[str, Dict]:
        """
        Get detailed statistics for videos
        
        Args:
            video_ids: List of YouTube video IDs
            
        Returns:
            Dictionary mapping video ID to statistics
        """
        if not video_ids or not self.api_key:
            return {}
        
        params = {
            "key": self.api_key,
            "id": ",".join(video_ids),
            "part": "statistics,contentDetails"
        }
        
        try:
            response = await self.make_request(
                f"{self.base_url}/videos",
                params=params
            )
            
            if not response:
                self.logger.warning(f"🚫 No response from YouTube videos API")
                return {}
            
            stats_dict = {}
            items = response.get("items", [])
            self.logger.debug(f"📊 Retrieved statistics for {len(items)} videos")
            
            for item in items:
                video_id = item.get("id")
                if video_id:
                    stats_dict[video_id] = item.get("statistics", {})
                    stats_dict[f"{video_id}_details"] = item.get("contentDetails", {})
            
            return stats_dict
            
        except Exception as e:
            self.logger.error(f"❌ Error getting video statistics: {e}")
            return {}
    
    def parse_post(self, raw_post: Dict[str, Any], cluster_id: str) -> PostCreate:
        """
        Parse YouTube API response into PostCreate model
        
        Args:
            raw_post: Raw video data from API
            cluster_id: Associated cluster ID
            
        Returns:
            PostCreate model
        """
        # Extract video ID
        video_id = raw_post.get("id", {}).get("videoId", "")
        if not video_id and isinstance(raw_post.get("id"), str):
            video_id = raw_post.get("id")
            
        self.logger.debug(f"🆔 Parsing YouTube video: {video_id}")
        
        # Extract snippet data
        snippet = raw_post.get("snippet", {})
        
        # Extract text content (title + description)
        title = snippet.get("title", "")
        description = snippet.get("description", "")
        post_text = f"{title}\n\n{description}" if description else title
        
        # Check if content contains Tamil characters
        has_tamil_text = any('\u0B80' <= char <= '\u0BFF' for char in post_text) if post_text else False
        self.logger.debug(f"📝 YouTube content length: {len(post_text)} chars (Tamil: {has_tamil_text})")
        
        # Log Tamil content for debugging
        if has_tamil_text:
            self.logger.info(f"🇮🇳 Found Tamil YouTube video: {title[:100]}{'...' if len(title) > 100 else ''}")
        
        # Extract channel info
        channel_title = snippet.get("channelTitle", "unknown")
        channel_id = snippet.get("channelId", "")
        
        # Build video URL
        post_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Parse datetime
        published_at_str = snippet.get("publishedAt", "")
        posted_at = self.parse_youtube_datetime(published_at_str)
        
        # Extract engagement metrics
        metrics = self.extract_engagement_metrics(raw_post)
        
        # Get subscriber count (not available in search API, default to 0)
        author_followers = 0
        
        return PostCreate(
            platform_post_id=video_id,
            platform=Platform.YOUTUBE,
            cluster_id=cluster_id,
            author_username=channel_title,
            author_followers=author_followers,
            post_text=self.clean_text(post_text),
            post_url=post_url,
            posted_at=posted_at,
            likes=metrics["likes"],
            comments=metrics["comments"],
            shares=metrics["shares"],
            views=metrics["views"]
        )
    
    def extract_engagement_metrics(self, raw_post: Dict[str, Any]) -> Dict[str, int]:
        """Extract engagement metrics from YouTube video"""
        statistics = raw_post.get("statistics", {})
        
        # Parse counts (they come as strings)
        views = statistics.get("viewCount", "0")
        likes = statistics.get("likeCount", "0")
        comments = statistics.get("commentCount", "0")
        
        # YouTube doesn't provide share count directly
        shares = 0
        
        return {
            "likes": int(likes) if likes.isdigit() else 0,
            "comments": int(comments) if comments.isdigit() else 0,
            "shares": shares,
            "views": int(views) if views.isdigit() else 0
        }
    
    def parse_youtube_datetime(self, date_str: str) -> datetime:
        """
        Parse YouTube datetime format (ISO 8601)
        Example: "2024-01-15T10:30:00Z"
        """
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return datetime.utcnow()
    
    async def get_channel_videos(
        self,
        channel_id: str,
        config: PlatformConfig,
        max_results: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Get videos from a specific YouTube channel
        
        Args:
            channel_id: YouTube channel ID
            config: Platform configuration
            max_results: Maximum number of results
            
        Yields:
            Raw video data from channel
        """
        if not self.api_key:
            self.logger.error("🔑 YouTube API key not configured")
            return
        
        # First, get the uploads playlist ID
        params = {
            "key": self.api_key,
            "id": channel_id,
            "part": "contentDetails"
        }
        
        try:
            response = await self.make_request(
                f"{self.base_url}/channels",
                params=params
            )
            
            if not response or not response.get("items"):
                print(f"Channel '{channel_id}' not found")
                return
            
            # Get uploads playlist ID
            uploads_playlist_id = (
                response["items"][0]
                .get("contentDetails", {})
                .get("relatedPlaylists", {})
                .get("uploads")
            )
            
            if not uploads_playlist_id:
                return
            
            # Get videos from uploads playlist
            async for video in self.get_playlist_videos(uploads_playlist_id, config, max_results):
                yield video
                
        except Exception as e:
            self.logger.error(f"❌ Error getting videos for channel '{channel_id}': {e}")
    
    async def get_playlist_videos(
        self,
        playlist_id: str,
        config: PlatformConfig,
        max_results: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Get videos from a YouTube playlist
        
        Args:
            playlist_id: YouTube playlist ID
            config: Platform configuration
            max_results: Maximum number of results
            
        Yields:
            Raw video data from playlist
        """
        if not self.api_key:
            return
        
        params = {
            "key": self.api_key,
            "playlistId": playlist_id,
            "part": "snippet",
            "maxResults": min(50, max_results)
        }
        
        next_page_token = None
        total_fetched = 0
        
        while total_fetched < max_results:
            try:
                if next_page_token:
                    params["pageToken"] = next_page_token
                
                response = await self.make_request(
                    f"{self.base_url}/playlistItems",
                    params=params
                )
                
                if not response:
                    break
                
                items = response.get("items", [])
                video_ids = []
                
                for item in items:
                    video_id = item.get("snippet", {}).get("resourceId", {}).get("videoId")
                    if video_id:
                        video_ids.append(video_id)
                
                if video_ids:
                    # Get statistics for videos
                    stats = await self.get_video_statistics(video_ids)
                    
                    for item in items:
                        video_id = item.get("snippet", {}).get("resourceId", {}).get("videoId")
                        if video_id in stats:
                            # Convert playlist item to video format
                            video_data = {
                                "id": {"videoId": video_id},
                                "snippet": item.get("snippet", {}),
                                "statistics": stats[video_id]
                            }
                            
                            total_fetched += 1
                            yield video_data
                            
                            if total_fetched >= max_results:
                                return
                
                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break
                
                await asyncio.sleep(self.rate_limit_delay)
                
            except Exception as e:
                self.logger.error(f"❌ Error getting playlist videos: {e}")
                break
    
    async def get_video_comments(
        self,
        video_id: str,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get comments for a specific video
        
        Args:
            video_id: YouTube video ID
            max_results: Maximum number of comments
            
        Returns:
            List of comment data
        """
        if not self.api_key:
            return []
        
        params = {
            "key": self.api_key,
            "videoId": video_id,
            "part": "snippet",
            "maxResults": min(100, max_results),
            "order": "relevance"
        }
        
        comments = []
        next_page_token = None
        
        while len(comments) < max_results:
            try:
                if next_page_token:
                    params["pageToken"] = next_page_token
                
                response = await self.make_request(
                    f"{self.base_url}/commentThreads",
                    params=params
                )
                
                if not response:
                    break
                
                items = response.get("items", [])
                for item in items:
                    comment_data = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                    if comment_data:
                        comments.append(comment_data)
                        
                        if len(comments) >= max_results:
                            break
                
                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break
                
                await asyncio.sleep(self.rate_limit_delay)
                
            except Exception as e:
                self.logger.error(f"❌ Error getting comments for video '{video_id}': {e}")
                break
        
        return comments[:max_results]