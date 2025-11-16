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
        """
        Initialize collector with API credentials
        
        Args:
            api_key: API key or token for the platform
            api_host: API host URL (for RapidAPI endpoints)
        """
        self.api_key = api_key
        self.api_host = api_host
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_delay = 1.0  # Default delay between requests (seconds)
        self.max_retries = 3
        self.retry_delay = 5.0
        
        # Setup logging for this collector
        self.logger = logging.getLogger(f"collector.{self.__class__.__name__.lower()}")
        self.logger.setLevel(logging.DEBUG)
        
        # Debug initialization
        self.logger.debug(f"🔧 Initializing {self.__class__.__name__}")
        self.logger.debug(f"   API Key: {'*' * (len(api_key) - 4) + api_key[-4:] if api_key and len(api_key) > 4 else 'Not provided'}")
        self.logger.debug(f"   API Host: {api_host}")
        self.logger.debug(f"   Rate limit delay: {self.rate_limit_delay}s")
        self.logger.debug(f"   Max retries: {self.max_retries}")

        # Redis cache for deduplication (optional - gracefully handle if Redis is not available)
        try:
            from app.core.redis_cache import get_redis_cache
            self.cache = get_redis_cache()
            if not self.cache.health_check():
                self.logger.warning("⚠️  Redis is not available - caching disabled")
                self.cache = None
        except Exception as e:
            self.logger.warning(f"⚠️  Redis cache unavailable: {e} - caching disabled")
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
        """
        Search for posts based on keyword and configuration
        
        Args:
            keyword: Search term or hashtag
            config: Platform-specific configuration
            max_results: Maximum number of results to fetch
            
        Yields:
            Raw post data from the platform API
        """
        pass
    
    @abstractmethod
    def parse_post(self, raw_post: Dict[str, Any], cluster_id: str) -> PostCreate:
        """
        Parse raw API response into PostCreate model
        
        Args:
            raw_post: Raw post data from API
            cluster_id: Associated cluster ID
            
        Returns:
            PostCreate model ready for database insertion
        """
        pass
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
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
        Collect posts for a cluster with given keywords
        
        Args:
            cluster_id: ID of the cluster
            keywords: List of keywords to search
            platform_config: Platform-specific configuration
            save_raw: Whether to save raw API responses
            
        Returns:
            List of raw data entries created
        """
        raw_data_entries = []
        
        if not platform_config.enabled:
            self.logger.debug(f"🚫 Platform collection disabled for {self.get_platform().value}")
            return raw_data_entries
        
        self.logger.info(f"🚀 Starting collection for {len(keywords)} keywords on {self.get_platform().value}")
        self.logger.debug(f"   Keywords: {keywords}")
        self.logger.debug(f"   Platform config: enabled={platform_config.enabled}, max_results={platform_config.max_results}, min_engagement={platform_config.min_engagement}")
        self.logger.debug(f"   Language: {platform_config.language}, Location: {platform_config.location}")
        
        start_time = datetime.utcnow()
        
        for i, keyword in enumerate(keywords):
            keyword_start_time = datetime.utcnow()
            try:
                self.logger.info(f"📝 Processing keyword {i+1}/{len(keywords)}: '{keyword}'")
                
                # Check if keyword contains Tamil characters
                has_tamil = any('\u0B80' <= char <= '\u0BFF' for char in keyword)
                self.logger.debug(f"   Tamil characters detected: {has_tamil}")
                if has_tamil:
                    tamil_chars = [char for char in keyword if '\u0B80' <= char <= '\u0BFF']
                    self.logger.debug(f"   Tamil characters found: {tamil_chars}")
                
                # Search for posts
                post_count = 0
                search_start_time = datetime.utcnow()
                self.logger.debug(f"   🔍 Starting search for keyword '{keyword}' (max_results={platform_config.max_results})")
                
                async for raw_post in self.search(
                    keyword,
                    platform_config,
                    max_results=platform_config.max_results
                ):
                    # Check if post is already cached (deduplication)
                    post_id = self._extract_post_id(raw_post)
                    if post_id and self.cache and self.cache.is_post_cached(self.get_platform().value, post_id):
                        self.logger.debug(f"   ⏭️  Skipping cached post: {post_id}")
                        continue

                    post_count += 1

                    if post_count % 10 == 0:
                        self.logger.debug(f"   📊 Collected {post_count} posts so far for '{keyword}'")
                    
                    if save_raw:
                        # Create raw data entry
                        raw_entry = RawDataCreate(
                            platform=RawDataPlatform(self.get_platform().value),
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

                        # Cache the post ID to prevent future duplicates
                        if post_id and self.cache:
                            self.cache.cache_post(self.get_platform().value, post_id)
                
                search_duration = (datetime.utcnow() - search_start_time).total_seconds()
                keyword_duration = (datetime.utcnow() - keyword_start_time).total_seconds()
                
                self.logger.info(f"  ✅ Collected {post_count} posts for keyword '{keyword}' in {search_duration:.2f}s")
                self.logger.debug(f"     Total keyword processing time: {keyword_duration:.2f}s")
                
                # Rate limiting between keywords
                if i < len(keywords) - 1:  # Don't sleep after last keyword
                    self.logger.debug(f"   ⏳ Rate limiting: sleeping {self.rate_limit_delay}s")
                    await asyncio.sleep(self.rate_limit_delay)
                
            except Exception as e:
                keyword_duration = (datetime.utcnow() - keyword_start_time).total_seconds()
                self.logger.error(f"  ❌ Error collecting for keyword '{keyword}' after {keyword_duration:.2f}s: {e}")
                self.logger.debug(f"     Exception type: {type(e).__name__}")
                import traceback
                self.logger.debug(f"     Traceback: {traceback.format_exc()}")
                continue
        
        total_duration = (datetime.utcnow() - start_time).total_seconds()
        self.logger.info(f"🏁 Completed collection: {len(raw_data_entries)} total raw entries in {total_duration:.2f}s")
        self.logger.debug(f"   Average time per keyword: {total_duration / len(keywords):.2f}s")
        self.logger.debug(f"   Posts per keyword breakdown: {[len([e for e in raw_data_entries if e.keyword == kw]) for kw in keywords]}")

        return raw_data_entries

    def _extract_post_id(self, raw_post: dict) -> Optional[str]:
        """
        Extract unique post ID from raw post data
        Override this in platform-specific collectors

        Args:
            raw_post: Raw post data from API

        Returns:
            Unique post ID or None
        """
        # Default implementation - look for common ID fields
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
        """
        Make HTTP request with retry logic
        
        Args:
            url: Request URL
            headers: Request headers
            params: Query parameters
            method: HTTP method
            
        Returns:
            JSON response from API
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Debug logging
        platform_name = self.get_platform().value
        request_id = hash(f"{url}{method}{params}") % 10000
        
        self.logger.debug(f"🌐 [{platform_name}][{request_id}] API Request:")
        self.logger.debug(f"   URL: {url}")
        self.logger.debug(f"   Method: {method}")
        if params:
            # Log params with sensitive data masked
            safe_params = {k: ('***MASKED***' if 'key' in k.lower() or 'token' in k.lower() else v) for k, v in params.items()}
            self.logger.debug(f"   Params: {safe_params}")
        if headers:
            safe_headers = {k: (v[:10] + '...' if len(str(v)) > 10 and 'key' not in k.lower() else '***MASKED***' if 'key' in k.lower() else v) for k, v in headers.items()}
            self.logger.debug(f"   Headers: {safe_headers}")
        
        for attempt in range(self.max_retries):
            attempt_start_time = datetime.utcnow()
            self.logger.debug(f"🔄 [{platform_name}][{request_id}] Attempt {attempt + 1}/{self.max_retries}")

            # Exponential backoff delay (only on retries, not first attempt)
            if attempt > 0:
                backoff_delay = min(2 ** attempt, 30)  # Max 30 seconds
                self.logger.warning(f"⏳ [{platform_name}][{request_id}] Waiting {backoff_delay}s before retry (exponential backoff)")
                await asyncio.sleep(backoff_delay)

            try:
                # Increase timeout to 60 seconds for slow RapidAPI responses (especially Facebook)
                timeout = aiohttp.ClientTimeout(total=60)
                async with self.session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    timeout=timeout
                ) as response:
                    response_text = await response.text()
                    
                    attempt_duration = (datetime.utcnow() - attempt_start_time).total_seconds()
                    
                    if response.status == 200:
                        try:
                            response_data = await response.json()
                            response_size = len(response_text)
                            
                            self.logger.info(f"✅ [{platform_name}][{request_id}] API Success in {attempt_duration:.2f}s")
                            self.logger.debug(f"   Status: {response.status}")
                            self.logger.debug(f"   Response size: {response_size} bytes")
                            self.logger.debug(f"   Response type: {type(response_data).__name__}")
                            
                            if isinstance(response_data, dict):
                                self.logger.debug(f"   Response keys: {list(response_data.keys())}")
                                for key, value in response_data.items():
                                    if isinstance(value, list):
                                        self.logger.debug(f"   {key}: list with {len(value)} items")
                                    elif isinstance(value, dict):
                                        self.logger.debug(f"   {key}: dict with {len(value)} keys")
                                    else:
                                        self.logger.debug(f"   {key}: {type(value).__name__}")
                            elif isinstance(response_data, list):
                                self.logger.debug(f"   Response: list with {len(response_data)} items")
                            
                            return response_data
                        except Exception as json_error:
                            self.logger.error(f"❌ [{platform_name}][{request_id}] JSON Parse Error: {json_error}")
                            self.logger.debug(f"   Response content type: {response.headers.get('content-type', 'unknown')}")
                            self.logger.debug(f"   Raw response (first 500 chars): {response_text[:500]}...")
                            return {}
                    elif response.status == 429:  # Rate limit
                        wait_time = self.retry_delay * (attempt + 1)
                        self.logger.warning(f"⏳ [{platform_name}][{request_id}] Rate limited (attempt {attempt + 1}). Waiting {wait_time}s...")
                        self.logger.debug(f"   Rate limit headers: {dict(response.headers)}")
                        await asyncio.sleep(wait_time)
                    else:
                        self.logger.error(f"❌ [{platform_name}][{request_id}] API error: {response.status} after {attempt_duration:.2f}s")
                        self.logger.debug(f"   Response headers: {dict(response.headers)}")
                        self.logger.debug(f"   Response body (first 500 chars): {response_text[:500]}...")
                        if attempt < self.max_retries - 1:
                            self.logger.debug(f"   Retrying in {self.retry_delay}s...")
                            await asyncio.sleep(self.retry_delay)
            except Exception as e:
                attempt_duration = (datetime.utcnow() - attempt_start_time).total_seconds()
                self.logger.error(f"❌ [{platform_name}][{request_id}] Request error (attempt {attempt + 1}) after {attempt_duration:.2f}s: {e}")
                self.logger.debug(f"   Exception type: {type(e).__name__}")
                if attempt < self.max_retries - 1:
                    self.logger.debug(f"   Retrying in {self.retry_delay}s...")
                    await asyncio.sleep(self.retry_delay)
                else:
                    self.logger.error(f"   All {self.max_retries} attempts failed, raising exception")
                    raise
        
        self.logger.error(f"❌ [{platform_name}][{request_id}] Failed after {self.max_retries} attempts")
        raise Exception(f"Failed after {self.max_retries} attempts")
    
    def extract_engagement_metrics(self, raw_post: Dict[str, Any]) -> Dict[str, int]:
        """
        Extract engagement metrics from raw post data
        Override in subclasses for platform-specific extraction
        
        Args:
            raw_post: Raw post data from API
            
        Returns:
            Dictionary with likes, comments, shares, views
        """
        return {
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "views": 0
        }
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text content
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = " ".join(text.split())
        
        # Truncate if too long (for database limits)
        if len(text) > 10000:
            text = text[:9997] + "..."
        
        return text
    
    def parse_datetime(self, date_str: str) -> datetime:
        """
        Parse datetime string to datetime object
        Override in subclasses for platform-specific formats
        
        Args:
            date_str: Date string from API
            
        Returns:
            Parsed datetime object
        """
        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            # Fallback to current time
            return datetime.utcnow()