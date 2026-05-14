"""
Base collector class for platform-specific data collection
Provides common functionality for all social media collectors
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
import aiohttp
import asyncio
import json
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from app.models.raw_data import RawDataCreate, ProcessingStatus, RawDataPlatform
from app.models.posts_table import PostCreate, Platform
from app.models.cluster import ClusterPlatformConfig, PlatformConfig

class BaseCollector(ABC):
    """Abstract base class for platform collectors"""

    def __init__(self, api_key: str = None, api_host: str = None):
        self.api_key = api_key
        self.api_host = api_host
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_delay = 1.0  # delay between keywords (seconds)
        self.max_retries = 3
        self.retry_delay = 5.0

        self.logger = logging.getLogger(f"collector.{self.__class__.__name__.lower()}")
        self.logger.setLevel(logging.DEBUG)

        self.logger.debug(f"Initializing {self.__class__.__name__}")
        self.logger.debug(f"  API Key: {'*' * (len(api_key) - 4) + api_key[-4:] if api_key and len(api_key) > 4 else 'Not provided'}")
        self.logger.debug(f"  API Host: {api_host}")
        self.logger.debug(f"  Rate limit delay: {self.rate_limit_delay}s")

        # Redis cache for deduplication (optional)
        try:
            from app.core.redis_cache import get_redis_cache
            self.cache = get_redis_cache()
            if not self.cache.health_check():
                self.logger.warning("Redis is not available - caching disabled")
                self.cache = None
        except Exception as e:
            self.logger.warning(f"Redis cache unavailable: {e} - caching disabled")
            self.cache = None

    @abstractmethod
    def get_platform(self) -> Platform:
        """Return the platform this collector handles"""
        pass

    @abstractmethod
    async def search(
        self,
        keyword: str,
        config: PlatformConfig,
        max_results: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Search for posts based on keyword and configuration"""
        pass

    @abstractmethod
    def parse_post(self, raw_post: Dict[str, Any], cluster_id: str) -> PostCreate:
        """Parse raw API response into PostCreate model"""
        pass

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def collect_for_cluster(
        self,
        cluster_id: str,
        keywords: List[str],
        platform_config: PlatformConfig,
        save_raw: bool = True
    ) -> List[RawDataCreate]:
        """
        Collect posts for a cluster with given keywords.
        Fetches in batches of batch_size posts, pausing batch_delay seconds between batches.
        """
        raw_data_entries = []

        if not platform_config.enabled:
            self.logger.debug(f"Platform collection disabled for {self.get_platform().value}")
            return raw_data_entries

        # Batch configuration — defaults match PlatformConfig model defaults
        batch_size  = getattr(platform_config, 'batch_size',  200)
        batch_delay = getattr(platform_config, 'batch_delay', 5.0)

        platform = self.get_platform().value
        self.logger.info(
            f"[{platform}] Starting collection: {len(keywords)} keywords, "
            f"max {platform_config.max_results} posts/keyword, "
            f"batch {batch_size} posts / {batch_delay}s pause"
        )

        start_time = datetime.utcnow()
        total_collected = 0  # tracks posts across ALL keywords for batch pacing

        for i, keyword in enumerate(keywords):
            keyword_start = datetime.utcnow()
            try:
                self.logger.info(f"[{platform}] Keyword {i+1}/{len(keywords)}: '{keyword}'")

                post_count  = 0
                batch_count = 0  # posts in the current batch window

                async for raw_post in self.search(
                    keyword,
                    platform_config,
                    max_results=platform_config.max_results
                ):
                    post_id = self._extract_post_id(raw_post)
                    if post_id and self.cache and self.cache.is_post_cached(platform, post_id):
                        continue

                    post_count      += 1
                    total_collected += 1
                    batch_count     += 1

                    if post_count % 50 == 0:
                        self.logger.info(f"  [{platform}] '{keyword}': {post_count} posts so far")

                    if save_raw:
                        raw_entry = RawDataCreate(
                            platform=RawDataPlatform(platform),
                            cluster_id=cluster_id,
                            keyword=keyword,
                            raw_json=raw_post,
                            api_endpoint=self.get_api_endpoint(),
                            api_params={
                                "keyword": keyword,
                                "language": platform_config.language,
                                "location": platform_config.location,
                                "max_results": platform_config.max_results
                            },
                            processing_status=ProcessingStatus.PENDING,
                            response_size_bytes=len(json.dumps(raw_post)),
                            posts_extracted=1
                        )
                        raw_data_entries.append(raw_entry)

                        if post_id and self.cache:
                            self.cache.cache_post(platform, post_id)

                    # ── Batch pause ──────────────────────────────────────
                    # After every batch_size posts, rest batch_delay seconds
                    if batch_count >= batch_size:
                        self.logger.info(
                            f"  [{platform}] Batch of {batch_size} done "
                            f"(total: {total_collected}) — pausing {batch_delay}s before next batch"
                        )
                        await asyncio.sleep(batch_delay)
                        batch_count = 0  # reset window

                elapsed = (datetime.utcnow() - keyword_start).total_seconds()
                self.logger.info(f"  [{platform}] '{keyword}' complete: {post_count} posts in {elapsed:.1f}s")

                # Short pause between keywords (not between batches)
                if i < len(keywords) - 1:
                    await asyncio.sleep(self.rate_limit_delay)

            except Exception as e:
                self.logger.error(f"  [{platform}] Error for keyword '{keyword}': {e}")
                import traceback
                self.logger.debug(traceback.format_exc())
                continue

        total_elapsed = (datetime.utcnow() - start_time).total_seconds()
        self.logger.info(
            f"[{platform}] Collection complete: {len(raw_data_entries)} posts "
            f"from {len(keywords)} keywords in {total_elapsed:.1f}s"
        )
        return raw_data_entries

    def _extract_post_id(self, raw_post: dict) -> Optional[str]:
        """Extract unique post ID from raw post data"""
        for field in ['id', 'post_id', 'tweet_id', 'video_id', 'article_id']:
            if field in raw_post:
                return str(raw_post[field])
        return None

    @abstractmethod
    def get_api_endpoint(self) -> str:
        """Return the API endpoint being used"""
        pass

    async def make_request(
        self,
        url: str,
        headers: Dict[str, str] = None,
        params: Dict[str, Any] = None,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        platform_name = self.get_platform().value
        request_id = hash(f"{url}{method}{params}") % 10000

        self.logger.debug(f"[{platform_name}][{request_id}] {method} {url}")

        for attempt in range(self.max_retries):
            attempt_start = datetime.utcnow()

            if attempt > 0:
                backoff = min(2 ** attempt, 30)
                self.logger.warning(f"[{platform_name}][{request_id}] Retry {attempt+1}/{self.max_retries} — waiting {backoff}s")
                await asyncio.sleep(backoff)

            try:
                timeout = aiohttp.ClientTimeout(total=60)
                async with self.session.request(
                    method, url, headers=headers, params=params, timeout=timeout
                ) as response:
                    response_text = await response.text()
                    elapsed = (datetime.utcnow() - attempt_start).total_seconds()

                    if response.status == 200:
                        try:
                            response_data = await response.json()
                            self.logger.info(f"[{platform_name}][{request_id}] OK in {elapsed:.2f}s")
                            return response_data
                        except Exception as json_error:
                            self.logger.error(f"[{platform_name}][{request_id}] JSON parse error: {json_error}")
                            return {}
                    elif response.status == 429:
                        wait_time = self.retry_delay * (attempt + 1)
                        self.logger.warning(f"[{platform_name}][{request_id}] Rate limited (attempt {attempt+1}). Waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        self.logger.error(f"[{platform_name}][{request_id}] HTTP {response.status} after {elapsed:.2f}s: {response_text[:300]}")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay)
            except Exception as e:
                elapsed = (datetime.utcnow() - attempt_start).total_seconds()
                self.logger.error(f"[{platform_name}][{request_id}] Request error (attempt {attempt+1}) after {elapsed:.2f}s: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise

        raise Exception(f"[{platform_name}] Failed after {self.max_retries} attempts")

    def extract_engagement_metrics(self, raw_post: Dict[str, Any]) -> Dict[str, int]:
        return {"likes": 0, "comments": 0, "shares": 0, "views": 0}

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = " ".join(text.split())
        if len(text) > 10000:
            text = text[:9997] + "..."
        return text

    def parse_datetime(self, date_str: str) -> datetime:
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return datetime.utcnow()
