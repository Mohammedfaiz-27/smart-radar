"""
Facebook Keyword-Based Scraper Provider

Fetches Facebook posts by searching keywords using RapidAPI facebook-scraper-api4.
"""

import os
import asyncio
from typing import Tuple, List, Dict, Any
from datetime import datetime, timedelta

import requests

from core.logging_config import get_logger
from services.scraper_providers.base import BaseSocialScraperProvider
from constants.facebook_exclusions import is_facebook_account_excluded

logger = get_logger(__name__)


class FacebookKeywordProvider(BaseSocialScraperProvider):
    """
    Provider for keyword-based Facebook scraping.

    Uses RapidAPI facebook-scraper-api4 to search for posts by keyword.
    """

    def __init__(self):
        self.api_key = os.getenv('RAPIDAPI_KEY_FACEBOOK', 'd5adc2df3dmsh1ec84b4b22692aep11a79cjsn27b1ce51db9e')
        self.scraping_mode = 'keyword'

    def get_platform(self) -> str:
        return 'facebook'

    async def fetch_posts(self, **kwargs) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Fetch Facebook posts by keyword search.

        Args:
            query: Search keyword
            max_items: Maximum number of posts to fetch (default: 20)
            date_range_days: Number of days back to search (default: 7)

        Returns:
            (success: bool, posts: List[Dict])
        """
        query = kwargs.get('query')
        max_items = kwargs.get('max_items', 20)
        date_range_days = kwargs.get('date_range_days', 7)

        if not query:
            logger.error("FacebookKeywordProvider: 'query' parameter is required")
            return False, []

        try:
            logger.info(f"Fetching Facebook posts for keyword: '{query}'")

            url = "https://facebook-scraper-api4.p.rapidapi.com/fetch_search_posts"

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=date_range_days)

            querystring = {
                "query": query,
                "location_uid": "0",  # 0 = worldwide
                "start_time": start_date.strftime("%Y-%m-%d"),
                "end_time": end_date.strftime("%Y-%m-%d"),
                "recent_posts": "true"
            }

            headers = {
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": "facebook-scraper-api4.p.rapidapi.com",
            }

            # Run synchronous request in thread pool with retry logic
            loop = asyncio.get_event_loop()
            max_retries = 2
            retry_count = 0
            response = None

            while retry_count <= max_retries:
                try:
                    response = await loop.run_in_executor(
                        None,
                        lambda: requests.get(url, headers=headers, params=querystring, timeout=60)
                    )
                    break  # Success, exit retry loop
                except requests.exceptions.ReadTimeout:
                    retry_count += 1
                    if retry_count > max_retries:
                        logger.error(f"Facebook API timed out after {max_retries} retries for '{query}'")
                        return False, []
                    logger.warning(f"Facebook API timeout, retry {retry_count}/{max_retries} for '{query}'")
                    await asyncio.sleep(2 * retry_count)  # Exponential backoff

            if response is None:
                return False, []

            if response.status_code == 200:
                data = response.json()
                items = data.get('data', {}).get('items', [])

                if not items:
                    logger.warning(f"No Facebook posts found for '{query}'")
                    return False, []

                # Apply Facebook account exclusions and normalize posts
                posts = []
                excluded_count = 0

                for item in items[:max_items]:
                    basic_info = item.get('basic_info', {})
                    feedback = item.get('feedback_details', {})
                    owner = item.get('owner_info', {})

                    author_name = owner.get('owner_name')
                    author_id = owner.get('owner_id')

                    # Check if account is excluded
                    if is_facebook_account_excluded(author_name, author_id):
                        excluded_count += 1
                        logger.debug(f"⏭️ Skipping excluded Facebook account: {author_name} ({author_id})")
                        continue

                    # Create normalized post object
                    post = {
                        'id': basic_info.get('post_id'),
                        'message': basic_info.get('post_text', ''),
                        'content': basic_info.get('post_text', ''),
                        'url': basic_info.get('url', ''),
                        'post_url': basic_info.get('url', ''),
                        'hashtags': basic_info.get('post_hashtags', []),
                        'reactions': feedback.get('reaction_count', 0),
                        'shares': feedback.get('total_shares', 0),
                        'comments': feedback.get('total_comments', 0),
                        'author_id': author_id,
                        'author_name': author_name,
                        'created_time': None,  # API doesn't provide timestamp
                        '_raw_item': item,  # Store original data for debugging
                        '_scraping_mode': 'keyword',
                        '_search_query': query
                    }
                    posts.append(post)

                if excluded_count > 0:
                    logger.info(f"🚫 Excluded {excluded_count} posts from blocked Facebook accounts")

                logger.info(f"✅ Fetched {len(posts)} Facebook posts for '{query}' (after exclusions)")
                return True, posts
            else:
                logger.warning(f"Facebook API returned status {response.status_code}: {response.text}")
                return False, []

        except Exception as e:
            logger.exception(f"Error fetching Facebook posts: {e}")
            return False, []
