"""
YouTube data collector implementation
Uses YouTube138 RapidAPI for data collection (same key as X/Facebook)
"""
from typing import Dict, Any, AsyncGenerator
from datetime import datetime
import os
import asyncio
from app.collectors.base_collector import BaseCollector
from app.models.posts_table import PostCreate, Platform
from app.models.cluster import PlatformConfig


class YouTubeCollector(BaseCollector):
    """Collector for YouTube platform using RapidAPI YouTube138"""

    def __init__(self):
        api_key = os.getenv("X_RAPIDAPI_KEY")  # Same RapidAPI key used for X and Facebook
        api_host = "youtube138.p.rapidapi.com"
        super().__init__(api_key=api_key, api_host=api_host)
        self.base_url = f"https://{api_host}"
        self.rate_limit_delay = 1.0

    def get_platform(self) -> Platform:
        return Platform.YOUTUBE

    def get_api_endpoint(self) -> str:
        return f"{self.base_url}/search/"

    async def search(
        self,
        keyword: str,
        config: PlatformConfig,
        max_results: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.api_key:
            self.logger.error("🔑 YouTube (RapidAPI) key not configured")
            return

        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host
        }

        has_tamil = any('஀' <= char <= '௿' for char in keyword)
        self.logger.debug(f"🔍 YouTube138 search for: '{keyword}' (Tamil: {has_tamil})")

        params = {
            "q": keyword,
            "hl": "ta" if has_tamil else "en",
            "gl": "IN"
        }

        total_fetched = 0

        try:
            response = await self.make_request(
                f"{self.base_url}/search/",
                headers=headers,
                params=params
            )

            if not response:
                self.logger.warning("🚫 No response from YouTube138 search API")
                return

            contents = response.get("contents", [])
            self.logger.debug(f"📦 YouTube138 search returned {len(contents)} items")

            for item in contents:
                if total_fetched >= max_results:
                    return

                video = item.get("video")
                if not video:
                    continue

                video_id = video.get("videoId")
                if not video_id:
                    continue

                # Use only search result data — no extra detail API call to avoid rate limits
                stats = video.get("stats", {})
                views = int(stats.get("views", 0) or 0)

                # Filter by views only (likes/comments not available from search results)
                if views < max(config.min_engagement * 5, 100):
                    continue

                combined = {
                    "videoId": video_id,
                    "title": video.get("title", ""),
                    "description": "",
                    "channelName": video.get("channelName", "Unknown"),
                    "channelId": video.get("channelId", ""),
                    "publishDate": "",
                    "stats": {
                        "views": views,
                        "likes": 0,
                        "comments": 0
                    }
                }

                total_fetched += 1
                yield combined

        except Exception as e:
            self.logger.error(f"❌ Error searching YouTube for '{keyword}': {e}")

    def parse_post(self, raw_post: Dict[str, Any], cluster_id: str) -> PostCreate:
        video_id = raw_post.get("videoId", "")
        title = raw_post.get("title", "")
        description = raw_post.get("description", "")
        post_text = f"{title}\n\n{description}".strip() if description else title

        channel_name = raw_post.get("channelName", "Unknown")
        post_url = f"https://www.youtube.com/watch?v={video_id}"

        publish_date = raw_post.get("publishDate", "") or raw_post.get("uploadDate", "")
        posted_at = self._parse_date(publish_date)

        stats = raw_post.get("stats", {})
        views = int(stats.get("views", 0) or 0)
        likes = int(stats.get("likes", 0) or 0)
        comments = int(stats.get("comments", 0) or 0)

        if any('஀' <= char <= '௿' for char in post_text):
            self.logger.info(f"🇮🇳 Found Tamil YouTube video: {title[:100]}")

        return PostCreate(
            platform_post_id=video_id,
            platform=Platform.YOUTUBE,
            cluster_id=cluster_id,
            author_username=channel_name,
            author_followers=0,
            post_text=self.clean_text(post_text),
            post_url=post_url,
            posted_at=posted_at,
            likes=likes,
            comments=comments,
            shares=0,
            views=views
        )

    def extract_engagement_metrics(self, raw_post: Dict[str, Any]) -> Dict[str, int]:
        stats = raw_post.get("stats", {})
        return {
            "likes": int(stats.get("likes", 0) or 0),
            "comments": int(stats.get("comments", 0) or 0),
            "shares": 0,
            "views": int(stats.get("views", 0) or 0)
        }

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date from YouTube138 response (YYYY-MM-DD or ISO format)"""
        if not date_str:
            return datetime.utcnow()
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except Exception:
                return datetime.utcnow()
