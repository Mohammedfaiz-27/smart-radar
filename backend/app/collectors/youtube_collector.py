"""
YouTube data collector implementation
Uses YouTube Data API v3 (YOUTUBE_API_KEY)
"""
from typing import Dict, Any, AsyncGenerator
from datetime import datetime, timedelta, timezone
import os
from app.collectors.base_collector import BaseCollector
from app.models.posts_table import PostCreate, Platform
from app.models.cluster import PlatformConfig


class YouTubeCollector(BaseCollector):
    """Collector for YouTube platform using YouTube Data API v3"""

    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self):
        api_key = os.getenv("YOUTUBE_API_KEY")
        super().__init__(api_key=api_key, api_host="www.googleapis.com")
        self.rate_limit_delay = 0.5

    async def _youtube_request(self, url: str, params: dict) -> dict:
        """Single-attempt request — no retries on 403 to avoid slow timeouts."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                body = await resp.json(content_type=None)
                if resp.status == 403:
                    reason = body.get("error", {}).get("message", "forbidden")
                    raise Exception(f"403 {reason}")
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}")
                return body

    def get_platform(self) -> Platform:
        return Platform.YOUTUBE

    def get_api_endpoint(self) -> str:
        return f"{self.BASE_URL}/search"

    async def search(
        self,
        keyword: str,
        config: PlatformConfig,
        max_results: int = 100,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.api_key:
            self.logger.error("🔑 YOUTUBE_API_KEY not configured")
            return

        has_tamil = any('஀' <= char <= '௿' for char in keyword)
        self.logger.debug(f"🔍 YouTube Data API v3 search for: '{keyword}' (Tamil: {has_tamil})")

        published_after = (
            datetime.now(timezone.utc) - timedelta(days=30)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            search_data = await self._youtube_request(
                f"{self.BASE_URL}/search",
                params={
                    "key": self.api_key,
                    "q": keyword,
                    "type": "video",
                    "part": "snippet",
                    "maxResults": min(max_results, 50),
                    "order": "date",
                    "publishedAfter": published_after,
                    "regionCode": "IN",
                    "relevanceLanguage": "ta" if has_tamil else "en",
                },
            )
        except Exception as e:
            self.logger.error(f"❌ YouTube search failed for '{keyword}': {e}")
            return

        if not search_data:
            return

        items = search_data.get("items", [])
        video_ids = [
            item["id"]["videoId"]
            for item in items
            if item.get("id", {}).get("videoId")
        ]

        if not video_ids:
            self.logger.warning(f"🚫 No videos found for '{keyword}'")
            return

        # Batch-fetch statistics for all videos in one request
        try:
            stats_data = await self._youtube_request(
                f"{self.BASE_URL}/videos",
                params={
                    "key": self.api_key,
                    "id": ",".join(video_ids),
                    "part": "statistics",
                },
            )
        except Exception as e:
            self.logger.warning(f"⚠️ Could not fetch video stats for '{keyword}': {e}")
            stats_data = {}

        stat_map: Dict[str, Dict] = {
            v["id"]: v.get("statistics", {})
            for v in (stats_data or {}).get("items", [])
        }

        for item in items:
            video_id = item.get("id", {}).get("videoId")
            if not video_id:
                continue

            snippet = item.get("snippet", {})
            stats = stat_map.get(video_id, {})
            views = int(stats.get("viewCount", 0) or 0)

            if views < max(config.min_engagement * 5, 100):
                continue

            yield {
                "videoId": video_id,
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "channelName": snippet.get("channelTitle", "Unknown"),
                "channelId": snippet.get("channelId", ""),
                "publishDate": snippet.get("publishedAt", ""),
                "stats": {
                    "views": views,
                    "likes": int(stats.get("likeCount", 0) or 0),
                    "comments": int(stats.get("commentCount", 0) or 0),
                },
            }

    def parse_post(self, raw_post: Dict[str, Any], cluster_id: str) -> PostCreate:
        video_id = raw_post.get("videoId", "")
        title = raw_post.get("title", "")
        description = raw_post.get("description", "")
        post_text = f"{title}\n\n{description}".strip() if description else title

        stats = raw_post.get("stats", {})

        if any('஀' <= char <= '௿' for char in post_text):
            self.logger.info(f"🇮🇳 Found Tamil YouTube video: {title[:100]}")

        return PostCreate(
            platform_post_id=video_id,
            platform=Platform.YOUTUBE,
            cluster_id=cluster_id,
            author_username=raw_post.get("channelName", "Unknown"),
            author_followers=0,
            post_text=self.clean_text(post_text),
            post_url=f"https://www.youtube.com/watch?v={video_id}",
            posted_at=self._parse_date(raw_post.get("publishDate", "")),
            likes=int(stats.get("likes", 0) or 0),
            comments=int(stats.get("comments", 0) or 0),
            shares=0,
            views=int(stats.get("views", 0) or 0),
        )

    def extract_engagement_metrics(self, raw_post: Dict[str, Any]) -> Dict[str, int]:
        stats = raw_post.get("stats", {})
        return {
            "likes": int(stats.get("likes", 0) or 0),
            "comments": int(stats.get("comments", 0) or 0),
            "shares": 0,
            "views": int(stats.get("views", 0) or 0),
        }

    def _parse_date(self, date_str: str) -> datetime:
        if not date_str:
            return datetime.utcnow()
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return datetime.utcnow()
