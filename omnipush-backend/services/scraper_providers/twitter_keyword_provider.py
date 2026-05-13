"""
Twitter Keyword-Based Scraper Provider

Fetches Twitter/X posts by searching keywords using RapidAPI twitter241.
"""

import os
import asyncio
from typing import Tuple, List, Dict, Any

import requests

from core.logging_config import get_logger
from services.scraper_providers.base import BaseSocialScraperProvider

logger = get_logger(__name__)


class TwitterKeywordProvider(BaseSocialScraperProvider):
    """
    Provider for keyword-based Twitter/X scraping.

    Uses RapidAPI twitter241 to search for posts by keyword.
    """

    def __init__(self):
        self.api_key = os.getenv('RAPIDAPI_KEY_TWITTER', '')
        self.scraping_mode = 'keyword'

    def get_platform(self) -> str:
        return 'twitter'

    async def fetch_posts(self, **kwargs) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Fetch Twitter posts by keyword search.

        Args:
            query: Search keyword
            max_items: Maximum number of posts to fetch (default: 20)

        Returns:
            (success: bool, posts: List[Dict])
        """
        query = kwargs.get('query')
        max_items = kwargs.get('max_items', 20)

        if not query:
            logger.error("TwitterKeywordProvider: 'query' parameter is required")
            return False, []

        try:
            logger.info(f"Fetching Twitter posts for keyword: '{query}'")

            url = "https://twitter241.p.rapidapi.com/search-v2"

            querystring = {
                "type": "Latest",
                "count": str(max_items),
                "query": query
            }

            headers = {
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": "twitter241.p.rapidapi.com",
            }

            # Run synchronous request in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(url, headers=headers, params=querystring, timeout=30)
            )

            if response.status_code == 200:
                data = response.json()

                # Extract tweets from the complex Twitter API structure
                tweets = []
                try:
                    timeline_instructions = data.get('result', {}).get('timeline', {}).get('instructions', [])
                    for instruction in timeline_instructions:
                        if instruction.get('type') == 'TimelineAddEntries':
                            entries = instruction.get('entries', [])
                            for entry in entries:
                                if entry.get('entryId', '').startswith('tweet-'):
                                    tweet_result = entry.get('content', {}).get('itemContent', {}).get('tweet_results', {}).get('result', {})
                                    if tweet_result.get('__typename') == 'Tweet':
                                        # Add metadata for tracking
                                        tweet_result['_scraping_mode'] = 'keyword'
                                        tweet_result['_search_query'] = query
                                        tweets.append(tweet_result)

                    logger.info(f"✅ Fetched {len(tweets)} Twitter posts for '{query}'")
                    return True, tweets

                except Exception as parse_error:
                    logger.exception(f"Error parsing Twitter response: {parse_error}")
                    return False, []
            else:
                logger.warning(f"Twitter API returned status {response.status_code}: {response.text}")
                return False, []

        except Exception as e:
            logger.exception(f"Error fetching Twitter posts: {e}")
            return False, []
