"""
Redis cache manager for SMART RADAR
Handles post deduplication and caching
"""
import redis
import json
import hashlib
import os
from typing import Optional, List, Set
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class RedisCache:
    """Redis cache manager for post deduplication and caching"""

    def __init__(self):
        """Initialize Redis connection"""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = redis.from_url(redis_url, decode_responses=True)

        # Cache TTL settings (in seconds)
        self.POST_ID_TTL = 7 * 24 * 60 * 60  # 7 days
        self.RATE_LIMIT_TTL = 15 * 60  # 15 minutes

    def get_post_cache_key(self, platform: str, platform_content_id: str) -> str:
        """Generate cache key for a post"""
        return f"post:{platform.lower()}:{platform_content_id}"

    def get_rate_limit_key(self, platform: str) -> str:
        """Generate rate limit key for a platform"""
        return f"rate_limit:{platform.lower()}"

    def is_post_cached(self, platform: str, platform_content_id: str) -> bool:
        """
        Check if a post has been cached (already collected)

        Args:
            platform: Platform name (X, YouTube, Facebook, etc.)
            platform_content_id: Unique ID from the platform

        Returns:
            True if post is already cached, False otherwise
        """
        cache_key = self.get_post_cache_key(platform, platform_content_id)
        return self.redis_client.exists(cache_key) > 0

    def cache_post(self, platform: str, platform_content_id: str, metadata: dict = None) -> bool:
        """
        Cache a post ID to prevent duplicate collection

        Args:
            platform: Platform name
            platform_content_id: Unique ID from the platform
            metadata: Optional metadata to store with the post

        Returns:
            True if cached successfully
        """
        cache_key = self.get_post_cache_key(platform, platform_content_id)
        data = {
            "platform": platform,
            "platform_content_id": platform_content_id,
            "cached_at": self._get_timestamp()
        }
        if metadata:
            data.update(metadata)

        return self.redis_client.setex(
            cache_key,
            self.POST_ID_TTL,
            json.dumps(data)
        )

    def filter_cached_posts(self, platform: str, post_ids: List[str]) -> List[str]:
        """
        Filter out posts that are already cached

        Args:
            platform: Platform name
            post_ids: List of platform content IDs

        Returns:
            List of post IDs that are NOT cached (new posts)
        """
        new_posts = []
        for post_id in post_ids:
            if not self.is_post_cached(platform, post_id):
                new_posts.append(post_id)
        return new_posts

    def batch_cache_posts(self, platform: str, post_ids: List[str]) -> int:
        """
        Cache multiple posts at once

        Args:
            platform: Platform name
            post_ids: List of platform content IDs to cache

        Returns:
            Number of posts cached
        """
        cached_count = 0
        for post_id in post_ids:
            if self.cache_post(platform, post_id):
                cached_count += 1
        return cached_count

    def get_cached_post(self, platform: str, platform_content_id: str) -> Optional[dict]:
        """
        Get cached post data

        Args:
            platform: Platform name
            platform_content_id: Unique ID from the platform

        Returns:
            Cached post data or None if not found
        """
        cache_key = self.get_post_cache_key(platform, platform_content_id)
        data = self.redis_client.get(cache_key)
        if data:
            return json.loads(data)
        return None

    def increment_rate_limit(self, platform: str) -> int:
        """
        Increment rate limit counter for a platform

        Args:
            platform: Platform name

        Returns:
            Current count for this time window
        """
        rate_key = self.get_rate_limit_key(platform)
        count = self.redis_client.incr(rate_key)

        # Set expiry on first increment
        if count == 1:
            self.redis_client.expire(rate_key, self.RATE_LIMIT_TTL)

        return count

    def get_rate_limit_count(self, platform: str) -> int:
        """
        Get current rate limit count for a platform

        Args:
            platform: Platform name

        Returns:
            Current count in this time window
        """
        rate_key = self.get_rate_limit_key(platform)
        count = self.redis_client.get(rate_key)
        return int(count) if count else 0

    def reset_rate_limit(self, platform: str) -> bool:
        """
        Reset rate limit counter for a platform

        Args:
            platform: Platform name

        Returns:
            True if reset successfully
        """
        rate_key = self.get_rate_limit_key(platform)
        return self.redis_client.delete(rate_key) > 0

    def cache_collection_result(self, cluster_id: str, result: dict, ttl: int = 900) -> bool:
        """
        Cache collection results for quick retrieval

        Args:
            cluster_id: Cluster ID
            result: Collection result dictionary
            ttl: Time to live in seconds (default: 15 minutes)

        Returns:
            True if cached successfully
        """
        cache_key = f"collection_result:{cluster_id}"
        return self.redis_client.setex(
            cache_key,
            ttl,
            json.dumps(result)
        )

    def get_collection_result(self, cluster_id: str) -> Optional[dict]:
        """
        Get cached collection result

        Args:
            cluster_id: Cluster ID

        Returns:
            Cached result or None
        """
        cache_key = f"collection_result:{cluster_id}"
        data = self.redis_client.get(cache_key)
        if data:
            return json.loads(data)
        return None

    def clear_cluster_cache(self, cluster_id: str) -> int:
        """
        Clear all cache entries for a cluster

        Args:
            cluster_id: Cluster ID

        Returns:
            Number of keys deleted
        """
        pattern = f"*:{cluster_id}:*"
        keys = self.redis_client.keys(pattern)
        if keys:
            return self.redis_client.delete(*keys)
        return 0

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        info = self.redis_client.info()
        return {
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "0B"),
            "total_keys": self.redis_client.dbsize(),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": self._calculate_hit_rate(
                info.get("keyspace_hits", 0),
                info.get("keyspace_misses", 0)
            )
        }

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate"""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)

    def _get_timestamp(self) -> float:
        """Get current timestamp"""
        import time
        return time.time()

    def health_check(self) -> bool:
        """
        Check if Redis connection is healthy

        Returns:
            True if connection is healthy
        """
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False


# Singleton instance
_redis_cache_instance = None


def get_redis_cache() -> RedisCache:
    """
    Get singleton Redis cache instance

    Returns:
        RedisCache instance
    """
    global _redis_cache_instance
    if _redis_cache_instance is None:
        _redis_cache_instance = RedisCache()
    return _redis_cache_instance
