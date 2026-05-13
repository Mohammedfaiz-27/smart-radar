"""
Social Account URL Resolution Service

Parses social media URLs and resolves account details using platform APIs.
Validates accounts and extracts platform-specific identifiers.
"""

import re
import os
import asyncio
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone

import requests

from core.logging_config import get_logger

logger = get_logger(__name__)


class SocialAccountResolver:
    """
    Service for resolving social media account URLs to platform-specific identifiers.

    Supports:
    - Facebook: Extracts page ID or username, validates account exists
    - Twitter/X: Extracts handle, validates account exists
    - Instagram: Extracts username, validates account exists
    """

    def __init__(self):
        # Get API keys from environment
        self.facebook_api_key = os.getenv('RAPIDAPI_KEY_FACEBOOK', '')
        self.twitter_api_key = os.getenv('RAPIDAPI_KEY_TWITTER', '')
        self.instagram_api_key = os.getenv('RAPIDAPI_KEY_INSTAGRAM', os.getenv('RAPIDAPI_KEY_FACEBOOK', ''))

    async def resolve_account(self, platform: str, account_url: str) -> Dict[str, Any]:
        """
        Parse and resolve a social media account URL.

        Args:
            platform: Platform name ('facebook', 'twitter', 'instagram')
            account_url: Full URL to the social media account

        Returns:
            Dict with resolution results:
            {
                'platform': str,
                'account_url': str,
                'account_identifier': str,  # Username/handle
                'account_id': str,          # Platform-specific ID
                'account_name': str,        # Display name
                'account_metadata': dict,   # Additional platform data
                'status': 'resolved'|'failed',
                'error': str (if failed)
            }
        """
        try:
            logger.info(f"Resolving {platform} account URL: {account_url}")

            # Step 1: Parse URL to extract identifier
            parse_result = self._parse_url(platform, account_url)
            if not parse_result['success']:
                return self._failed_result(
                    platform=platform,
                    account_url=account_url,
                    error=parse_result['error']
                )

            account_identifier = parse_result['identifier']
            logger.debug(f"Extracted identifier: {account_identifier}")

            # Step 2: Validate and resolve account using platform API
            if platform.lower() == 'facebook':
                resolve_result = await self._resolve_facebook_account(account_identifier)
            elif platform.lower() == 'twitter':
                resolve_result = await self._resolve_twitter_account(account_identifier)
            elif platform.lower() == 'instagram':
                resolve_result = await self._resolve_instagram_account(account_identifier)
            else:
                return self._failed_result(
                    platform=platform,
                    account_url=account_url,
                    error=f"Platform '{platform}' not supported for account resolution"
                )

            if not resolve_result['success']:
                return self._failed_result(
                    platform=platform,
                    account_url=account_url,
                    error=resolve_result['error']
                )

            # Step 3: Return resolved account data
            return {
                'platform': platform,
                'account_url': account_url,
                'account_identifier': account_identifier,
                'account_id': resolve_result['account_id'],
                'account_name': resolve_result['account_name'],
                'account_metadata': resolve_result.get('metadata', {}),
                'status': 'resolved',
                'error': None
            }

        except Exception as e:
            logger.exception(f"Unexpected error resolving {platform} account: {e}")
            return self._failed_result(
                platform=platform,
                account_url=account_url,
                error=f"Unexpected error: {str(e)}"
            )

    def _parse_url(self, platform: str, url: str) -> Dict[str, Any]:
        """
        Parse social media URL to extract account identifier.

        Returns:
            {'success': bool, 'identifier': str, 'error': str}
        """
        try:
            if platform.lower() == 'facebook':
                return self._parse_facebook_url(url)
            elif platform.lower() == 'twitter':
                return self._parse_twitter_url(url)
            elif platform.lower() == 'instagram':
                return self._parse_instagram_url(url)
            else:
                return {'success': False, 'error': f"Platform '{platform}' not supported"}
        except Exception as e:
            return {'success': False, 'error': f"URL parsing error: {str(e)}"}

    def _parse_facebook_url(self, url: str) -> Dict[str, Any]:
        """
        Parse Facebook URL to extract page name or profile ID.

        Supported formats:
        - https://facebook.com/pagename
        - https://www.facebook.com/pagename
        - https://m.facebook.com/pagename
        - https://facebook.com/profile.php?id=123456
        - https://facebook.com/pages/pagename/123456
        """
        try:
            parsed = urlparse(url)

            # Normalize domain
            if not any(domain in parsed.netloc.lower() for domain in ['facebook.com', 'fb.com']):
                return {'success': False, 'error': 'Invalid Facebook URL: domain must be facebook.com or fb.com'}

            path = parsed.path.strip('/')

            # Case 1: profile.php?id=123456
            if 'profile.php' in path:
                query_params = parse_qs(parsed.query)
                profile_id = query_params.get('id', [None])[0]
                if profile_id:
                    return {'success': True, 'identifier': profile_id}
                else:
                    return {'success': False, 'error': 'Facebook profile URL missing id parameter'}

            # Case 2: /pages/pagename/123456
            if path.startswith('pages/'):
                parts = path.split('/')
                if len(parts) >= 3:
                    # Use the numeric ID if available, otherwise use page name
                    page_id = parts[-1] if parts[-1].isdigit() else parts[-2]
                    return {'success': True, 'identifier': page_id}

            # Case 3: /pagename (most common)
            if path:
                # Remove query parameters and fragments
                identifier = path.split('?')[0].split('#')[0]
                if identifier:
                    return {'success': True, 'identifier': identifier}

            return {'success': False, 'error': 'Could not extract Facebook page name or ID from URL'}

        except Exception as e:
            return {'success': False, 'error': f"Error parsing Facebook URL: {str(e)}"}

    def _parse_twitter_url(self, url: str) -> Dict[str, Any]:
        """
        Parse Twitter/X URL to extract handle.

        Supported formats:
        - https://twitter.com/username
        - https://www.twitter.com/username
        - https://x.com/username
        - https://mobile.twitter.com/username
        """
        try:
            parsed = urlparse(url)

            # Normalize domain
            if not any(domain in parsed.netloc.lower() for domain in ['twitter.com', 'x.com']):
                return {'success': False, 'error': 'Invalid Twitter URL: domain must be twitter.com or x.com'}

            path = parsed.path.strip('/')

            # Extract username (handle)
            # Path format: username or username/status/12345...
            if path:
                # Remove query parameters and fragments
                clean_path = path.split('?')[0].split('#')[0]

                # Get first path segment (the username)
                username = clean_path.split('/')[0]

                # Validate username (alphanumeric + underscore, 1-15 chars)
                if re.match(r'^[A-Za-z0-9_]{1,15}$', username):
                    # Remove @ if present
                    username = username.lstrip('@')
                    return {'success': True, 'identifier': username}

            return {'success': False, 'error': 'Could not extract Twitter handle from URL'}

        except Exception as e:
            return {'success': False, 'error': f"Error parsing Twitter URL: {str(e)}"}

    def _parse_instagram_url(self, url: str) -> Dict[str, Any]:
        """
        Parse Instagram URL to extract username.

        Supported formats:
        - https://instagram.com/username
        - https://www.instagram.com/username
        - https://www.instagram.com/username/
        """
        try:
            parsed = urlparse(url)

            # Normalize domain
            if 'instagram.com' not in parsed.netloc.lower():
                return {'success': False, 'error': 'Invalid Instagram URL: domain must be instagram.com'}

            path = parsed.path.strip('/')

            # Extract username
            # Path format: username or username/p/postid...
            if path:
                # Remove query parameters and fragments
                clean_path = path.split('?')[0].split('#')[0]

                # Get first path segment (the username)
                username = clean_path.split('/')[0]

                # Validate username (alphanumeric + underscore + period, max 30 chars)
                if re.match(r'^[A-Za-z0-9_.]{1,30}$', username):
                    # Remove @ if present
                    username = username.lstrip('@')
                    return {'success': True, 'identifier': username}

            return {'success': False, 'error': 'Could not extract Instagram username from URL'}

        except Exception as e:
            return {'success': False, 'error': f"Error parsing Instagram URL: {str(e)}"}

    async def _resolve_facebook_account(self, identifier: str) -> Dict[str, Any]:
        """
        Validate Facebook account exists using RapidAPI.

        Returns:
            {'success': bool, 'account_id': str, 'account_name': str, 'error': str}
        """
        try:
            if not self.facebook_api_key:
                logger.warning("Facebook API key not configured, skipping validation")
                return {
                    'success': True,
                    'account_id': identifier,
                    'account_name': identifier,
                    'metadata': {'validation_skipped': True}
                }

            # We can use a simple search to verify the account exists
            # Use the facebook-scraper-api4 search endpoint
            url = "https://facebook-scraper-api4.p.rapidapi.com/fetch_search_posts"

            querystring = {
                "query": identifier,
                "location_uid": "0",
                "recent_posts": "true"
            }

            headers = {
                "x-rapidapi-key": self.facebook_api_key,
                "x-rapidapi-host": "facebook-scraper-api4.p.rapidapi.com",
            }

            # Run synchronous request in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(url, headers=headers, params=querystring, timeout=30)
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get('data', {}).get('items', [])

                if items and len(items) > 0:
                    # Extract account info from first post
                    first_item = items[0]
                    owner_info = first_item.get('owner_info', {})

                    account_id = owner_info.get('owner_id', identifier)
                    account_name = owner_info.get('owner_name', identifier)

                    logger.info(f"✅ Facebook account resolved: {account_name} (ID: {account_id})")

                    return {
                        'success': True,
                        'account_id': account_id,
                        'account_name': account_name,
                        'metadata': {
                            'owner_info': owner_info,
                            'validation_method': 'search_posts'
                        }
                    }
                else:
                    logger.warning(f"No posts found for Facebook account: {identifier}")
                    # Account might be private or have no posts, but URL is valid
                    return {
                        'success': True,
                        'account_id': identifier,
                        'account_name': identifier,
                        'metadata': {'validation_warning': 'No posts found, account may be private or empty'}
                    }
            elif response.status_code == 404:
                return {
                    'success': False,
                    'error': f"Facebook account not found: {identifier}"
                }
            elif response.status_code == 403:
                return {
                    'success': False,
                    'error': f"Facebook account is private or access denied: {identifier}"
                }
            else:
                logger.warning(f"Facebook API returned status {response.status_code}")
                # Don't fail - just use identifier as fallback
                return {
                    'success': True,
                    'account_id': identifier,
                    'account_name': identifier,
                    'metadata': {'validation_error': f'API returned {response.status_code}'}
                }

        except requests.exceptions.Timeout:
            logger.warning(f"Facebook API timeout for {identifier}, using identifier as fallback")
            return {
                'success': True,
                'account_id': identifier,
                'account_name': identifier,
                'metadata': {'validation_timeout': True}
            }
        except Exception as e:
            logger.exception(f"Error resolving Facebook account {identifier}: {e}")
            # Don't fail the resolution - use identifier as fallback
            return {
                'success': True,
                'account_id': identifier,
                'account_name': identifier,
                'metadata': {'validation_error': str(e)}
            }

    async def _resolve_twitter_account(self, handle: str) -> Dict[str, Any]:
        """
        Validate Twitter account exists using RapidAPI.

        Returns:
            {'success': bool, 'account_id': str, 'account_name': str, 'error': str}
        """
        try:
            if not self.twitter_api_key:
                logger.warning("Twitter API key not configured, skipping validation")
                return {
                    'success': True,
                    'account_id': handle,
                    'account_name': handle,
                    'metadata': {'validation_skipped': True}
                }

            # Use twitter241 API to search for user
            url = "https://twitter241.p.rapidapi.com/search-v2"

            querystring = {
                "type": "People",
                "count": "1",
                "query": handle
            }

            headers = {
                "x-rapidapi-key": self.twitter_api_key,
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

                # Parse user data from response
                users = []
                try:
                    timeline_instructions = data.get('result', {}).get('timeline', {}).get('instructions', [])
                    for instruction in timeline_instructions:
                        if instruction.get('type') == 'TimelineAddEntries':
                            entries = instruction.get('entries', [])
                            for entry in entries:
                                if entry.get('entryId', '').startswith('user-'):
                                    user_result = entry.get('content', {}).get('itemContent', {}).get('user_results', {}).get('result', {})
                                    if user_result.get('__typename') == 'User':
                                        users.append(user_result)
                except Exception as parse_error:
                    logger.warning(f"Error parsing Twitter user response: {parse_error}")

                if users:
                    user = users[0]
                    legacy = user.get('legacy', {})

                    account_id = user.get('rest_id', handle)
                    account_name = legacy.get('name', handle)
                    screen_name = legacy.get('screen_name', handle)

                    logger.info(f"✅ Twitter account resolved: {account_name} (@{screen_name})")

                    return {
                        'success': True,
                        'account_id': screen_name,  # Use screen_name as identifier
                        'account_name': account_name,
                        'metadata': {
                            'rest_id': account_id,
                            'screen_name': screen_name,
                            'followers_count': legacy.get('followers_count', 0),
                            'validation_method': 'people_search'
                        }
                    }
                else:
                    logger.warning(f"Twitter account not found: @{handle}")
                    return {
                        'success': False,
                        'error': f"Twitter account not found: @{handle}"
                    }
            elif response.status_code == 404:
                return {
                    'success': False,
                    'error': f"Twitter account not found: @{handle}"
                }
            elif response.status_code == 403:
                return {
                    'success': False,
                    'error': f"Twitter account is private or suspended: @{handle}"
                }
            else:
                logger.warning(f"Twitter API returned status {response.status_code}")
                # Don't fail - just use handle as fallback
                return {
                    'success': True,
                    'account_id': handle,
                    'account_name': handle,
                    'metadata': {'validation_error': f'API returned {response.status_code}'}
                }

        except requests.exceptions.Timeout:
            logger.warning(f"Twitter API timeout for @{handle}, using handle as fallback")
            return {
                'success': True,
                'account_id': handle,
                'account_name': handle,
                'metadata': {'validation_timeout': True}
            }
        except Exception as e:
            logger.exception(f"Error resolving Twitter account @{handle}: {e}")
            # Don't fail the resolution - use handle as fallback
            return {
                'success': True,
                'account_id': handle,
                'account_name': handle,
                'metadata': {'validation_error': str(e)}
            }

    async def _resolve_instagram_account(self, username: str) -> Dict[str, Any]:
        """
        Validate Instagram account exists using RapidAPI.

        Returns:
            {'success': bool, 'account_id': str, 'account_name': str, 'error': str}
        """
        try:
            if not self.instagram_api_key:
                logger.warning("Instagram API key not configured, skipping validation")
                return {
                    'success': True,
                    'account_id': username,
                    'account_name': username,
                    'metadata': {'validation_skipped': True}
                }

            # Use instagram-scraper-api2 to get user info
            url = "https://instagram-scraper-api2.p.rapidapi.com/v1/info"

            querystring = {
                "username_or_id_or_url": username
            }

            headers = {
                "x-rapidapi-key": self.instagram_api_key,
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

                # Extract user info from response
                user_data = data.get('data', {})

                if user_data:
                    account_id = user_data.get('pk', username)
                    account_name = user_data.get('full_name', username)
                    ig_username = user_data.get('username', username)

                    logger.info(f"✅ Instagram account resolved: {account_name} (@{ig_username})")

                    return {
                        'success': True,
                        'account_id': ig_username,  # Use username as identifier
                        'account_name': account_name,
                        'metadata': {
                            'pk': str(account_id),
                            'username': ig_username,
                            'follower_count': user_data.get('follower_count', 0),
                            'following_count': user_data.get('following_count', 0),
                            'is_private': user_data.get('is_private', False),
                            'validation_method': 'user_info'
                        }
                    }
                else:
                    logger.warning(f"No data found for Instagram account: @{username}")
                    return {
                        'success': False,
                        'error': f"Instagram account not found: @{username}"
                    }
            elif response.status_code == 404:
                return {
                    'success': False,
                    'error': f"Instagram account not found: @{username}"
                }
            elif response.status_code == 403:
                return {
                    'success': False,
                    'error': f"Instagram account is private or access denied: @{username}"
                }
            else:
                logger.warning(f"Instagram API returned status {response.status_code}")
                # Don't fail - just use username as fallback
                return {
                    'success': True,
                    'account_id': username,
                    'account_name': username,
                    'metadata': {'validation_error': f'API returned {response.status_code}'}
                }

        except requests.exceptions.Timeout:
            logger.warning(f"Instagram API timeout for @{username}, using username as fallback")
            return {
                'success': True,
                'account_id': username,
                'account_name': username,
                'metadata': {'validation_timeout': True}
            }
        except Exception as e:
            logger.exception(f"Error resolving Instagram account @{username}: {e}")
            # Don't fail the resolution - use username as fallback
            return {
                'success': True,
                'account_id': username,
                'account_name': username,
                'metadata': {'validation_error': str(e)}
            }

    def _failed_result(self, platform: str, account_url: str, error: str) -> Dict[str, Any]:
        """Helper to create a failed resolution result"""
        return {
            'platform': platform,
            'account_url': account_url,
            'account_identifier': None,
            'account_id': None,
            'account_name': None,
            'account_metadata': {},
            'status': 'failed',
            'error': error
        }


# Singleton instance
_resolver_instance = None

def get_social_account_resolver() -> SocialAccountResolver:
    """Get singleton instance of SocialAccountResolver"""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = SocialAccountResolver()
    return _resolver_instance
