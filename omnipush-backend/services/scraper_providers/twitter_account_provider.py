"""
Twitter Account-Based Scraper Provider

Fetches posts from specific Twitter/X accounts using RapidAPI twitter241.
"""

import os
import asyncio
from typing import Tuple, List, Dict, Any
from datetime import datetime, timedelta, timezone

import requests

from core.logging_config import get_logger
from services.scraper_providers.base import BaseSocialScraperProvider

logger = get_logger(__name__)


class TwitterAccountProvider(BaseSocialScraperProvider):
    """
    Provider for account-based Twitter/X scraping.

    Fetches posts from a specific Twitter account by handle.
    """

    def __init__(self):
        self.api_key = os.getenv('RAPIDAPI_KEY_TWITTER', '')
        self.scraping_mode = 'account'

    def get_platform(self) -> str:
        return 'twitter'

    async def fetch_posts(self, **kwargs) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Fetch Twitter posts from a specific account.

        Args:
            account_id: Twitter account handle/screen_name (e.g., 'username')
            account_identifier: Alternative identifier (same as account_id for Twitter)
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
            logger.error("TwitterAccountProvider: 'account_id' or 'account_identifier' is required")
            return False, []

        # Use account_id if available, otherwise use account_identifier
        handle = (account_id or account_identifier).lstrip('@')

        try:
            logger.info(f"Fetching posts from Twitter account: '@{handle}'")

            # Calculate cutoff time for filtering
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=date_range_days)
            logger.debug(f"Filtering tweets newer than: {cutoff_time.isoformat()}")

            # Use search API with "from:username" query to get posts from that user
            url = "https://twitter241.p.rapidapi.com/search-v2"

            # Twitter search syntax: "from:username" fetches tweets from that user
            search_query = f"from:{handle}"

            querystring = {
                "type": "Latest",
                "count": str(max_items),
                "query": search_query
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
                                        # Verify the tweet is from the target account
                                        # Extract screen_name from tweet author
                                        author_screen_name = None
                                        try:
                                            if 'core' in tweet_result and 'user_results' in tweet_result['core']:
                                                user_result = tweet_result['core']['user_results'].get('result', {})
                                                user_legacy = user_result.get('legacy', {})
                                                author_screen_name = user_legacy.get('screen_name', '').lower()
                                        except Exception:
                                            pass

                                        # Filter: Only include tweets from target account
                                        if author_screen_name and author_screen_name != handle.lower():
                                            continue

                                        # Filter by time: Check if tweet is within date range
                                        try:
                                            tweet_created_at_str = tweet_result.get('legacy', {}).get('created_at')
                                            if tweet_created_at_str:
                                                # Twitter timestamp format: "Wed Mar 06 20:15:00 +0000 2024"
                                                tweet_created_at = datetime.strptime(tweet_created_at_str, "%a %b %d %H:%M:%S %z %Y")

                                                # Skip tweets older than cutoff time
                                                if tweet_created_at < cutoff_time:
                                                    logger.debug(f"Skipping old tweet from {tweet_created_at.isoformat()}")
                                                    continue
                                        except Exception as date_error:
                                            # If we can't parse the date, include the tweet to be safe
                                            logger.debug(f"Could not parse tweet date, including tweet: {date_error}")

                                        # Add metadata for tracking
                                        tweet_result['_scraping_mode'] = 'account'
                                        tweet_result['_target_account_handle'] = handle
                                        tweets.append(tweet_result)

                    logger.info(f"✅ Fetched {len(tweets)} posts from Twitter account '@{handle}'")
                    return True, tweets

                except Exception as parse_error:
                    logger.exception(f"Error parsing Twitter response: {parse_error}")
                    return False, []

            elif response.status_code == 404:
                logger.warning(f"Twitter account not found or no posts: '@{handle}'")
                return True, []  # Account may exist but have no posts
            elif response.status_code == 403:
                logger.warning(f"Twitter account is private or suspended: '@{handle}'")
                return False, []
            else:
                logger.warning(f"Twitter API returned status {response.status_code}: {response.text}")
                return False, []

        except Exception as e:
            logger.exception(f"Error fetching posts from Twitter account: {e}")
            return False, []
