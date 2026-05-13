"""
Instagram Account-Based Scraper Provider

Fetches posts from specific Instagram accounts using RapidAPI instagram-scraper-api2.
"""

import os
import asyncio
from typing import Tuple, List, Dict, Any
from datetime import datetime, timedelta, timezone

import requests

from core.logging_config import get_logger
from services.scraper_providers.base import BaseSocialScraperProvider

logger = get_logger(__name__)


class InstagramAccountProvider(BaseSocialScraperProvider):
    """
    Provider for account-based Instagram scraping.

    Fetches posts from a specific Instagram account by username.
    """

    def __init__(self):
        self.api_key = os.getenv('RAPIDAPI_KEY_INSTAGRAM', os.getenv('RAPIDAPI_KEY_FACEBOOK', ''))
        self.scraping_mode = 'account'

    def get_platform(self) -> str:
        return 'instagram'

    async def fetch_posts(self, **kwargs) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Fetch Instagram posts from a specific account.

        Args:
            account_id: Instagram username (e.g., 'username')
            account_identifier: Alternative identifier (same as account_id for Instagram)
            max_items: Maximum number of posts to fetch (default: 20)
            date_range_days: Number of days to look back (default: 7) - client-side filtering

        Returns:
            (success: bool, posts: List[Dict])
        """
        account_id = kwargs.get('account_id')
        account_identifier = kwargs.get('account_identifier', account_id)
        max_items = kwargs.get('max_items', 20)
        date_range_days = kwargs.get('date_range_days', 7)

        if not account_id and not account_identifier:
            logger.error("InstagramAccountProvider: 'account_id' or 'account_identifier' is required")
            return False, []

        # Use account_id if available, otherwise use account_identifier
        username = (account_id or account_identifier).lstrip('@')

        try:
            logger.info(f"Fetching posts from Instagram account: '@{username}'")

            # Calculate cutoff time for filtering
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=date_range_days)
            logger.debug(f"Filtering Instagram posts newer than: {cutoff_time.isoformat()}")

            # Use RapidAPI Instagram scraper to get user posts
            url = "https://instagram-scraper-api2.p.rapidapi.com/v1/posts"

            querystring = {
                "username_or_id_or_url": username
            }

            headers = {
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": "instagram-scraper-api2.p.rapidapi.com",
            }

            # Run synchronous request in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(url, headers=headers, params=querystring, timeout=30)
            )

            if response.status_code == 200:
                data = response.json()

                # Extract posts from the API response
                posts = []
                try:
                    # The API returns posts in data.items array
                    items = data.get('data', {}).get('items', [])

                    if not items:
                        logger.warning(f"No posts found for Instagram account '@{username}'")
                        return True, []

                    for item in items[:max_items]:
                        # Extract post data
                        post_id = item.get('id', item.get('pk', ''))
                        caption_obj = item.get('caption', {})
                        caption_text = caption_obj.get('text', '') if caption_obj else ''

                        # Extract timestamp
                        taken_at = item.get('taken_at')
                        post_created_at = None
                        if taken_at:
                            try:
                                post_created_at = datetime.fromtimestamp(taken_at, tz=timezone.utc)

                                # Filter by date range
                                if post_created_at < cutoff_time:
                                    logger.debug(f"Skipping old Instagram post from {post_created_at.isoformat()}")
                                    continue
                            except Exception as date_error:
                                logger.debug(f"Could not parse Instagram post date, including post: {date_error}")

                        # Extract user info
                        user = item.get('user', {})
                        author_name = user.get('username', username)
                        author_id = user.get('pk', user.get('id', ''))

                        # Extract media URL (image or video thumbnail)
                        media_url = None

                        # Check for carousel media (multiple images/videos)
                        carousel_media = item.get('carousel_media', [])
                        if carousel_media and len(carousel_media) > 0:
                            first_carousel_item = carousel_media[0]
                            image_versions = first_carousel_item.get('image_versions2', {})
                            candidates = image_versions.get('candidates', [])
                            if candidates and len(candidates) > 0:
                                # Get highest quality image (first in candidates)
                                media_url = candidates[0].get('url', '')

                        # Check for single image/video
                        if not media_url:
                            image_versions = item.get('image_versions2', {})
                            candidates = image_versions.get('candidates', [])
                            if candidates and len(candidates) > 0:
                                media_url = candidates[0].get('url', '')

                        # Fallback: check video thumbnail
                        if not media_url and item.get('media_type') == 2:  # Video
                            video_versions = item.get('video_versions', [])
                            if video_versions and len(video_versions) > 0:
                                # Use image thumbnail for videos
                                thumbnail_url = item.get('image_versions2', {}).get('candidates', [])
                                if thumbnail_url and len(thumbnail_url) > 0:
                                    media_url = thumbnail_url[0].get('url', '')

                        # Extract engagement metrics
                        like_count = item.get('like_count', 0)
                        comment_count = item.get('comment_count', 0)

                        # Extract post URL
                        code = item.get('code', '')
                        post_url = f"https://www.instagram.com/p/{code}/" if code else ''

                        # Create normalized post object
                        normalized_post = {
                            'id': str(post_id),
                            'content': caption_text,
                            'message': caption_text,
                            'url': post_url,
                            'post_url': post_url,
                            'author_id': str(author_id),
                            'author_name': author_name,
                            'created_time': post_created_at,
                            'hashtags': self._extract_hashtags(caption_text),
                            'reactions': like_count,
                            'likes': like_count,
                            'shares': 0,  # Instagram doesn't provide share count via API
                            'comments': comment_count,
                            'media_url': media_url,
                            '_raw_item': item,  # Store original data for debugging
                            '_scraping_mode': 'account',
                            '_target_account_username': username
                        }

                        posts.append(normalized_post)

                    logger.info(f"✅ Fetched {len(posts)} posts from Instagram account '@{username}'")
                    return True, posts

                except Exception as parse_error:
                    logger.exception(f"Error parsing Instagram response: {parse_error}")
                    return False, []

            elif response.status_code == 404:
                logger.warning(f"Instagram account not found or no posts: '@{username}'")
                return True, []  # Account may exist but have no posts
            elif response.status_code == 403:
                logger.warning(f"Instagram account is private or access denied: '@{username}'")
                return False, []
            else:
                logger.warning(f"Instagram API returned status {response.status_code}: {response.text}")
                return False, []

        except Exception as e:
            logger.exception(f"Error fetching posts from Instagram account: {e}")
            return False, []

    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from caption text"""
        if not text:
            return []

        import re
        hashtags = re.findall(r'#(\w+)', text)
        return hashtags
