"""
Facebook Account-Based Scraper Provider

Fetches posts from specific Facebook pages/accounts using RapidAPI facebook-scraper-api4.
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


class FacebookAccountProvider(BaseSocialScraperProvider):
    """
    Provider for account-based Facebook scraping.

    Fetches posts from a specific Facebook page/account by account ID or username.
    """

    def __init__(self):
        self.api_key = os.getenv('RAPIDAPI_KEY_FACEBOOK', 'd5adc2df3dmsh1ec84b4b22692aep11a79cjsn27b1ce51db9e')
        self.scraping_mode = 'account'

    def get_platform(self) -> str:
        return 'facebook'

    async def fetch_posts(self, **kwargs) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Fetch Facebook posts from a specific account.

        Args:
            account_id: Facebook account ID or username
            account_identifier: Alternative identifier (username/page name)
            max_items: Maximum number of posts to fetch (default: 20)
            date_range_days: Number of days back to search (default: 7)

        Returns:
            (success: bool, posts: List[Dict])
        """
        account_id = kwargs.get('account_id')
        account_identifier = kwargs.get('account_identifier', account_id)
        max_items = kwargs.get('max_items', 20)
        date_range_days = kwargs.get('date_range_days', 7)

        if not account_id and not account_identifier:
            logger.error("FacebookAccountProvider: 'account_id' or 'account_identifier' is required")
            return False, []

        # Use account_id if available, otherwise use account_identifier
        search_identifier = account_id or account_identifier

        # Check if account is excluded before making API call
        if is_facebook_account_excluded(search_identifier, account_id):
            logger.info(f"⏭️ Skipping excluded Facebook account: {search_identifier}")
            return True, []  # Return success but empty list

        try:
            logger.info(f"Fetching posts from Facebook account: '{search_identifier}'")

            # Use the search API with the account name/ID to get posts from that account
            # The facebook-scraper-api4 doesn't have a direct "get posts by page ID" endpoint,
            # so we use search with the page name and filter results to that specific account
            url = "https://facebook-scraper-api4.p.rapidapi.com/fetch_search_posts"

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=date_range_days)

            querystring = {
                "query": search_identifier,
                "location_uid": "0",
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
                        logger.error(f"Facebook API timed out after {max_retries} retries for account '{search_identifier}'")
                        return False, []
                    logger.warning(f"Facebook API timeout, retry {retry_count}/{max_retries} for account '{search_identifier}'")
                    await asyncio.sleep(2 * retry_count)  # Exponential backoff

            if response is None:
                return False, []

            if response.status_code == 200:
                data = response.json()
                items = data.get('data', {}).get('items', [])

                if not items:
                    logger.warning(f"No posts found for Facebook account '{search_identifier}'")
                    return True, []  # Success but no posts

                # Filter posts to only include those from the target account
                # Normalize posts
                posts = []
                filtered_out_count = 0

                for item in items[:max_items * 2]:  # Fetch extra to account for filtering
                    basic_info = item.get('basic_info', {})
                    feedback = item.get('feedback_details', {})
                    owner = item.get('owner_info', {})

                    author_name = owner.get('owner_name', '')
                    author_id = owner.get('owner_id', '')

                    # Filter: Only include posts from the target account
                    # Match by account_id (exact) or account_identifier (fuzzy)
                    is_from_target_account = False
                    if account_id and str(author_id) == str(account_id):
                        is_from_target_account = True
                    elif account_identifier and (
                        account_identifier.lower() in author_name.lower() or
                        author_name.lower() in account_identifier.lower()
                    ):
                        is_from_target_account = True

                    if not is_from_target_account:
                        filtered_out_count += 1
                        continue

                    # Additional exclusion check (in case account was added after resolution)
                    if is_facebook_account_excluded(author_name, author_id):
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
                        '_scraping_mode': 'account',
                        '_target_account_id': account_id,
                        '_target_account_identifier': account_identifier
                    }
                    posts.append(post)

                    # Stop if we have enough posts
                    if len(posts) >= max_items:
                        break

                if filtered_out_count > 0:
                    logger.debug(f"Filtered out {filtered_out_count} posts from other accounts")

                logger.info(f"✅ Fetched {len(posts)} posts from Facebook account '{search_identifier}'")
                return True, posts

            elif response.status_code == 404:
                logger.warning(f"Facebook account not found or no posts: '{search_identifier}'")
                return True, []  # Account may exist but have no posts
            elif response.status_code == 403:
                logger.warning(f"Facebook account is private or access denied: '{search_identifier}'")
                return False, []
            else:
                logger.warning(f"Facebook API returned status {response.status_code}: {response.text}")
                return False, []

        except Exception as e:
            logger.exception(f"Error fetching posts from Facebook account: {e}")
            return False, []
