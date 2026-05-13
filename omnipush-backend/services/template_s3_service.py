"""
Template S3 Service
==================

Service for fetching template content from S3 with local fallback.
Integrates with the existing newscard template service to provide
cloud-based template storage and retrieval.
"""

import requests
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import asyncio
from datetime import datetime, timedelta

from core.database import get_database

logger = logging.getLogger(__name__)

class TemplateS3Service:
    """Service for managing template content retrieval from S3"""

    def __init__(self):
        self.db = get_database()
        self.cache = {}  # In-memory cache for template content
        self.cache_ttl = 3600  # 1 hour cache TTL
        self.aws_region = self._get_aws_region()

    def _get_aws_region(self) -> str:
        """Get AWS region from environment"""
        import os
        return os.getenv("AWS_REGION", "ap-south-2")

    async def get_template_content_by_name(self, template_name: str) -> Optional[str]:
        """
        Get template content by name, trying S3 first, then local fallback.
        Includes caching for performance.
        """
        # Check cache first
        cache_key = f"template_content_{template_name}"
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            if datetime.now() < cached_item['expires_at']:
                logger.debug(f"Using cached template content for {template_name}")
                return cached_item['content']

        try:
            # Get template metadata from database
            template_data = await self._get_template_from_db(template_name)
            if not template_data:
                logger.warning(f"Template not found in database: {template_name}")
                return None

            # Try S3 first
            if template_data.get('s3_url'):
                content = await self._fetch_from_s3(template_data['s3_url'])
                if content:
                    # Cache the content
                    self._cache_content(cache_key, content)
                    logger.info(f"Retrieved template {template_name} from S3")
                    return content

            # Fallback to local file
            if template_data.get('template_path'):
                content = await self._fetch_from_local(template_data['template_path'])
                if content:
                    # Cache the content
                    self._cache_content(cache_key, content)
                    logger.info(f"Retrieved template {template_name} from local file")
                    return content

            logger.error(f"No valid content source found for template: {template_name}")
            return None

        except Exception as e:
            logger.error(f"Failed to get template content for {template_name}: {str(e)}")
            return None

    async def get_template_content_by_id(self, template_id: str) -> Optional[str]:
        """Get template content by ID"""
        try:
            # Get template metadata from database
            template_data = await self._get_template_from_db_by_id(template_id)
            if not template_data:
                logger.warning(f"Template not found in database: {template_id}")
                return None

            return await self.get_template_content_by_name(template_data['template_name'])

        except Exception as e:
            logger.error(f"Failed to get template content for ID {template_id}: {str(e)}")
            return None

    async def _get_template_from_db(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get template metadata from database by name"""
        try:
            result = self.db.client.table('newscard_templates')\
                .select('id, template_name, template_path, s3_url, s3_bucket, s3_key, is_active')\
                .eq('template_name', template_name)\
                .eq('is_active', True)\
                .execute()

            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(f"Database error fetching template {template_name}: {str(e)}")
            return None

    async def _get_template_from_db_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template metadata from database by ID"""
        try:
            result = self.db.client.table('newscard_templates')\
                .select('id, template_name, template_path, s3_url, s3_bucket, s3_key, is_active')\
                .eq('id', template_id)\
                .eq('is_active', True)\
                .execute()

            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(f"Database error fetching template by ID {template_id}: {str(e)}")
            return None

    def _fix_s3_url_region(self, s3_url: str) -> str:
        """
        Fix S3 URLs missing region specification.
        Converts: https://bucket.s3.amazonaws.com/key
        To: https://bucket.s3.{region}.amazonaws.com/key
        """
        import re
        # Pattern to detect URLs missing region: bucket.s3.amazonaws.com (not bucket.s3.region.amazonaws.com)
        pattern = r'(https://[^/]+\.s3)\.amazonaws\.com(/.*)'

        if '.s3.' in s3_url and not re.search(r'\.s3\.[a-z0-9-]+\.amazonaws\.com', s3_url):
            # URL is missing region, add it
            fixed_url = re.sub(pattern, rf'\1.{self.aws_region}.amazonaws.com\2', s3_url)
            if fixed_url != s3_url:
                logger.info(f"Fixed region-less S3 URL: {s3_url} -> {fixed_url}")
                return fixed_url

        return s3_url

    async def _fetch_from_s3(self, s3_url: str) -> Optional[str]:
        """Fetch template content from S3"""
        try:
            # Fix URL if missing region
            s3_url = self._fix_s3_url_region(s3_url)

            # Use asyncio to make HTTP request non-blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(s3_url, timeout=10)
            )

            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"S3 fetch failed with status {response.status_code}: {s3_url}.error while trying to access the s3 public url:{response.text}")
                return None

        except Exception as e:
            logger.error(f"Error fetching from S3 {s3_url}: {str(e)}")
            return None

    async def _fetch_from_local(self, template_path: str) -> Optional[str]:
        """Fetch template content from local file"""
        try:
            # Construct full path relative to project root
            if template_path.startswith('/'):
                template_path = template_path[1:]  # Remove leading slash

            base_dir = Path(__file__).parent.parent
            full_path = base_dir / template_path

            if full_path.exists():
                # Use asyncio to read file non-blocking
                loop = asyncio.get_event_loop()
                content = await loop.run_in_executor(
                    None,
                    lambda: full_path.read_text(encoding='utf-8')
                )
                return content
            else:
                logger.warning(f"Local template file not found: {full_path}")
                return None

        except Exception as e:
            logger.error(f"Error reading local template {template_path}: {str(e)}")
            return None

    def _cache_content(self, cache_key: str, content: str):
        """Cache template content with TTL"""
        self.cache[cache_key] = {
            'content': content,
            'expires_at': datetime.now() + timedelta(seconds=self.cache_ttl)
        }

        # Simple cache cleanup - remove expired entries
        self._cleanup_expired_cache()

    def _cleanup_expired_cache(self):
        """Remove expired cache entries"""
        now = datetime.now()
        expired_keys = [
            key for key, value in self.cache.items()
            if now >= value['expires_at']
        ]

        for key in expired_keys:
            del self.cache[key]

    async def preload_templates(self, template_names: list = None) -> Dict[str, bool]:
        """
        Preload templates into cache for better performance.
        If template_names is None, preloads all active templates.
        """
        results = {}

        try:
            if template_names is None:
                # Get all active templates
                result = self.db.client.table('newscard_templates')\
                    .select('template_name')\
                    .eq('is_active', True)\
                    .execute()

                template_names = [t['template_name'] for t in result.data]

            # Preload each template
            for template_name in template_names:
                try:
                    content = await self.get_template_content_by_name(template_name)
                    results[template_name] = content is not None
                    if content:
                        logger.info(f"Preloaded template: {template_name}")
                    else:
                        logger.warning(f"Failed to preload template: {template_name}")

                except Exception as e:
                    logger.error(f"Error preloading template {template_name}: {str(e)}")
                    results[template_name] = False

            successful = sum(1 for success in results.values() if success)
            logger.info(f"Preloaded {successful}/{len(template_names)} templates")

            return results

        except Exception as e:
            logger.error(f"Error in preload_templates: {str(e)}")
            return {}

    async def get_all_available_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get metadata for all available templates"""
        try:
            result = self.db.client.table('newscard_templates')\
                .select('*')\
                .eq('is_active', True)\
                .order('template_display_name')\
                .execute()

            templates = {}
            for template_data in result.data:
                templates[template_data['template_name']] = {
                    'id': template_data['id'],
                    'display_name': template_data['template_display_name'],
                    'supports_images': template_data['supports_images'],
                    'description': template_data.get('description'),
                    'has_s3_url': bool(template_data.get('s3_url')),
                    'has_local_path': bool(template_data.get('template_path'))
                }

            return templates

        except Exception as e:
            logger.error(f"Error getting available templates: {str(e)}")
            return {}

    def clear_cache(self):
        """Clear all cached template content"""
        self.cache.clear()
        logger.info("Template cache cleared")

# Global instance for use in other services
template_s3_service = TemplateS3Service()