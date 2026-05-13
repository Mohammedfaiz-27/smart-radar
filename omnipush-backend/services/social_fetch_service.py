import asyncio
import logging
import requests
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4

from models.content import Platform
from core.config import settings

logger = logging.getLogger(__name__)


class SocialFetchService:
    """Service for fetching social media content with cursor tracking and deduplication"""
    
    def __init__(self, db_client):
        self.db_client = db_client
        self.rapidapi_configs = {
            Platform.FACEBOOK: {
                "url": "https://facebook-scraper-api4.p.rapidapi.com/fetch_search_posts",
                "headers": {
                    "x-rapidapi-key": settings.rapidapi_key_facebook,
                    "x-rapidapi-host": "facebook-scraper-api4.p.rapidapi.com",
                }
            },
            Platform.TWITTER: {
                "url": "https://twitter241.p.rapidapi.com/search-v2",
                "headers": {
                    "x-rapidapi-key": settings.rapidapi_key_twitter,
                    "x-rapidapi-host": "twitter241.p.rapidapi.com",
                }
            }
        }

    def _get_db_client(self):
        """Get the appropriate database client (service_client if wrapper, or raw client)"""
        if hasattr(self.db_client, 'service_client'):
            return self.db_client.service_client
        return self.db_client

    async def get_sync_state(self, social_account_id: str, sync_type: str = "posts") -> Optional[Dict[str, Any]]:
        """Get the current sync state for a social account"""
        try:
            response = self._get_db_client().table('social_sync_states').select('*').eq(
                'social_account_id', social_account_id
            ).eq('sync_type', sync_type).maybe_single().execute()
            
            return response.data if response.data else None
        except Exception as e:
            logger.exception(f"Failed to get sync state: {e}")
            return None
    
    async def update_sync_state(
        self, 
        social_account_id: str, 
        sync_type: str, 
        last_cursor: str = None,
        last_item_id: str = None,
        status: str = "success",
        error_message: str = None
    ) -> bool:
        """Update the sync state for a social account"""
        try:
            update_data = {
                'last_sync_timestamp': datetime.now(timezone.utc).isoformat(),
                'status': status,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            if last_cursor:
                update_data['last_cursor'] = last_cursor
            if last_item_id:
                update_data['last_item_id'] = last_item_id
            if error_message:
                update_data['error_message'] = error_message
            
            # Try to update existing record
            result = self._get_db_client().table('social_sync_states').update(update_data).eq(
                'social_account_id', social_account_id
            ).eq('sync_type', sync_type).execute()
            
            if not result.data:
                # Create new record if it doesn't exist
                account_response = self._get_db_client().table('social_accounts').select(
                    'tenant_id, platform'
                ).eq('id', social_account_id).maybe_single().execute()
                
                if account_response.data:
                    account = account_response.data
                    insert_data = {
                        'id': str(uuid4()),
                        'social_account_id': social_account_id,
                        'tenant_id': account['tenant_id'],
                        'platform': account['platform'],
                        'sync_type': sync_type,
                        **update_data
                    }
                    
                    self._get_db_client().table('social_sync_states').insert(insert_data).execute()
            
            return True
        except Exception as e:
            logger.exception(f"Failed to update sync state: {e}")
            return False
    
    async def store_content(
        self, 
        social_account_id: str, 
        platform: Platform, 
        content_type: str,
        content_data: Dict[str, Any]
    ) -> bool:
        """Store fetched content with deduplication"""
        try:
            # Extract platform-specific content ID
            platform_content_id = self._extract_content_id(platform, content_data)
            if not platform_content_id:
                logger.warning(f"Could not extract content ID for platform {platform}")
                return False
            
            # Check if content already exists
            existing = self._get_db_client().table('social_media_content').select('id').eq(
                'platform', platform.value
            ).eq('platform_content_id', platform_content_id).execute()
            
            if existing.data:
                logger.info(f"Content {platform_content_id} already exists, skipping")
                return True
            
            # Extract content details
            content_details = self._extract_content_details(platform, content_data)
            
            # Get account details
            account_response = self._get_db_client().table('social_accounts').select(
                'tenant_id'
            ).eq('id', social_account_id).maybe_single().execute()
            
            if not account_response.data:
                logger.exception(f"Social account {social_account_id} not found")
                return False
            
            # Store content
            content_record = {
                'id': str(uuid4()),
                'social_account_id': social_account_id,
                'tenant_id': account_response.data['tenant_id'],
                'platform': platform.value,
                'content_type': content_type,
                'platform_content_id': platform_content_id,
                'content_data': content_data,
                **content_details
            }
            
            result = self._get_db_client().table('social_media_content').insert(content_record).execute()
            return bool(result.data)
            
        except Exception as e:
            logger.exception(f"Failed to store content: {e}")
            return False
    
    def _extract_content_id(self, platform: Platform, content_data: Dict[str, Any]) -> Optional[str]:
        """Extract platform-specific content ID"""
        try:
            if platform == Platform.FACEBOOK:
                return content_data.get('post_id')
            elif platform == Platform.TWITTER:
                # Twitter content ID is nested in the result structure
                if 'result' in content_data and 'rest_id' in content_data['result']:
                    return content_data['result']['rest_id']
                return None
            elif platform == Platform.INSTAGRAM:
                return content_data.get('id')
            else:
                return content_data.get('id')
        except Exception as e:
            logger.exception(f"Failed to extract content ID: {e}")
            return None
    
    def _extract_content_details(self, platform: Platform, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract standardized content details from platform-specific data"""
        details = {
            'author_id': None,
            'author_name': None,
            'content_text': None,
            'media_urls': [],
            'engagement_metrics': {},
            'published_at': None
        }
        
        try:
            if platform == Platform.FACEBOOK:
                details.update({
                    'author_id': content_data.get('author', {}).get('id'),
                    'author_name': content_data.get('author', {}).get('name'),
                    'content_text': content_data.get('message'),
                    'media_urls': self._extract_facebook_media_urls(content_data),
                    'engagement_metrics': {
                        'likes': content_data.get('reactions_count', 0),
                        'comments': content_data.get('comments_count', 0),
                        'shares': content_data.get('reshare_count', 0),
                        'reactions': content_data.get('reactions', {})
                    },
                    'published_at': datetime.fromtimestamp(
                        content_data.get('timestamp', 0), tz=timezone.utc
                    ).isoformat() if content_data.get('timestamp') else None
                })
            
            elif platform == Platform.TWITTER:
                # Twitter data is nested differently
                tweet_data = content_data.get('result', {})
                user_data = tweet_data.get('core', {}).get('user_results', {}).get('result', {})
                legacy_data = tweet_data.get('legacy', {})
                
                details.update({
                    'author_id': user_data.get('rest_id'),
                    'author_name': user_data.get('legacy', {}).get('name'),
                    'content_text': legacy_data.get('full_text'),
                    'media_urls': self._extract_twitter_media_urls(tweet_data),
                    'engagement_metrics': {
                        'likes': legacy_data.get('favorite_count', 0),
                        'retweets': legacy_data.get('retweet_count', 0),
                        'replies': legacy_data.get('reply_count', 0)
                    },
                    'published_at': self._parse_twitter_timestamp(legacy_data.get('created_at'))
                })
            
            return details
            
        except Exception as e:
            logger.exception(f"Failed to extract content details: {e}")
            return details
    
    def _extract_facebook_media_urls(self, content_data: Dict[str, Any]) -> List[str]:
        """Extract media URLs from Facebook content"""
        urls = []
        
        # Ensure content_data is not None
        if not content_data:
            return urls
        
        # Check for image
        image_data = content_data.get('image')
        if image_data and isinstance(image_data, dict) and image_data.get('uri'):
            urls.append(image_data['uri'])
        
        # Check for video
        if content_data.get('video'):
            urls.append(content_data['video'])
        
        # Check for video files
        video_files = content_data.get('video_files')
        if video_files and isinstance(video_files, dict):
            if video_files.get('video_hd_file'):
                urls.append(video_files['video_hd_file'])
            elif video_files.get('video_sd_file'):
                urls.append(video_files['video_sd_file'])
        
        return urls
    
    def _extract_twitter_media_urls(self, tweet_data: Dict[str, Any]) -> List[str]:
        """Extract media URLs from Twitter content"""
        urls = []
        
        # Check for extended entities (media)
        if 'extended_entities' in tweet_data:
            media = tweet_data['extended_entities'].get('media', [])
            for item in media:
                if item.get('media_url_https'):
                    urls.append(item['media_url_https'])
        
        return urls
    
    def _parse_twitter_timestamp(self, timestamp_str: str) -> Optional[str]:
        """Parse Twitter timestamp string to ISO format"""
        if not timestamp_str:
            return None
        
        try:
            # Twitter format: "Wed Jun 05 01:09:43 +0000 2024"
            from datetime import datetime
            dt = datetime.strptime(timestamp_str, "%a %b %d %H:%M:%S %z %Y")
            return dt.isoformat()
        except Exception as e:
            logger.exception(f"Failed to parse Twitter timestamp: {e}")
            return None
    
    async def fetch_facebook_posts(
        self, 
        social_account_id: str, 
        query: str, 
        max_posts: int = 20
    ) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
        """Fetch Facebook posts with cursor tracking"""
        try:
            # Get current sync state
            sync_state = await self.get_sync_state(social_account_id, "posts")
            last_cursor = sync_state.get('last_cursor') if sync_state else None
            
            config = self.rapidapi_configs[Platform.FACEBOOK]
            params = {"query": query}
            
            if last_cursor:
                params["cursor"] = last_cursor
            
            response = requests.get(
                config["url"], 
                headers=config["headers"], 
                params=params
            )
            
            if response.status_code != 200:
                await self.update_sync_state(
                    social_account_id, "posts", 
                    status="error", 
                    error_message=f"API request failed: {response.status_code}"
                )
                return False, [], None
            
            data = response.json()

            # Handle both API response formats
            # Old API: {'results': [...]}
            # New API: {'data': {'items': [...]}}
            if 'data' in data and 'items' in data['data']:
                raw_posts = data['data']['items']
            else:
                raw_posts = data.get('results', [])

            if not raw_posts:
                logger.info(f"No new Facebook posts found for query: {query}")
                return True, [], None

            # Apply Facebook account exclusions
            from constants.facebook_exclusions import is_facebook_account_excluded

            posts = []
            excluded_count = 0

            for post in raw_posts[:max_posts]:
                # Extract author info based on API format
                author_name = None
                author_id = None

                # New API format
                if 'owner_info' in post:
                    author_name = post['owner_info'].get('owner_name')
                    author_id = post['owner_info'].get('owner_id')
                # Old API format
                elif 'author' in post:
                    author_name = post['author'].get('name')
                    author_id = post['author'].get('id')

                # Check if account is excluded
                if is_facebook_account_excluded(author_name, author_id):
                    excluded_count += 1
                    logger.debug(f"⏭️ Skipping excluded Facebook account: {author_name} ({author_id})")
                    continue

                posts.append(post)

            if excluded_count > 0:
                logger.info(f"🚫 Excluded {excluded_count} posts from blocked Facebook accounts")

            # Store posts and track the last one
            stored_count = 0
            last_post_id = None

            for post in posts:
                if await self.store_content(social_account_id, Platform.FACEBOOK, "post", post):
                    stored_count += 1
                    # Handle both API formats for post_id
                    if 'basic_info' in post:
                        last_post_id = post['basic_info'].get('post_id')
                    else:
                        last_post_id = post.get('post_id')
            
            # Update sync state with new cursor
            new_cursor = data.get('cursor')
            await self.update_sync_state(
                social_account_id, "posts",
                last_cursor=new_cursor,
                last_item_id=last_post_id
            )
            
            logger.info(f"Stored {stored_count} Facebook posts for account {social_account_id}")
            return True, posts[:stored_count], new_cursor
            
        except Exception as e:
            logger.exception(f"Failed to fetch Facebook posts: {e}")
            await self.update_sync_state(
                social_account_id, "posts",
                status="error",
                error_message=str(e)
            )
            return False, [], None
    
    async def fetch_twitter_posts(
        self, 
        social_account_id: str, 
        query: str, 
        max_posts: int = 20
    ) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
        """Fetch Twitter posts with cursor tracking"""
        try:
            # Get current sync state
            sync_state = await self.get_sync_state(social_account_id, "posts")
            last_cursor = sync_state.get('last_cursor') if sync_state else None
            
            config = self.rapidapi_configs[Platform.TWITTER]
            params = {
                "type": "Latest",
                "count": str(max_posts),
                "query": query
            }
            
            if last_cursor:
                params["cursor"] = last_cursor
            
            response = requests.get(
                config["url"], 
                headers=config["headers"], 
                params=params
            )
            
            if response.status_code != 200:
                await self.update_sync_state(
                    social_account_id, "posts",
                    status="error",
                    error_message=f"API request failed: {response.status_code}"
                )
                return False, [], None
            
            data = response.json()
            
            # Extract tweets from Twitter response
            tweets = []
            if 'result' in data and 'timeline' in data['result']:
                timeline = data['result']['timeline']
                if 'instructions' in timeline:
                    for instruction in timeline['instructions']:
                        if instruction.get('type') == 'TimelineAddEntries':
                            for entry in instruction.get('entries', []):
                                if entry.get('content', {}).get('itemContent', {}).get('itemType') == 'TimelineTweet':
                                    tweet_data = entry['content']['itemContent'].get('tweet_results', {}).get('result')
                                    if tweet_data:
                                        tweets.append(tweet_data)
            
            if not tweets:
                logger.info(f"No new Twitter posts found for query: {query}")
                return True, [], None
            
            # Store tweets and track the last one
            stored_count = 0
            last_tweet_id = None
            
            for tweet in tweets[:max_posts]:
                if await self.store_content(social_account_id, Platform.TWITTER, "post", tweet):
                    stored_count += 1
                    last_tweet_id = tweet.get('rest_id')
            
            # Update sync state with new cursor
            new_cursor = data.get('cursor', {}).get('bottom') if data.get('cursor') else None
            await self.update_sync_state(
                social_account_id, "posts",
                last_cursor=new_cursor,
                last_item_id=last_tweet_id
            )
            
            logger.info(f"Stored {stored_count} Twitter posts for account {social_account_id}")
            return True, tweets[:stored_count], new_cursor
            
        except Exception as e:
            logger.exception(f"Failed to fetch Twitter posts: {e}")
            await self.update_sync_state(
                social_account_id, "posts",
                status="error",
                error_message=str(e)
            )
            return False, [], None
    
    async def fetch_social_content(
        self, 
        social_account_id: str, 
        platform: Platform, 
        query: str = None,
        max_items: int = 20
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Generic method to fetch social content based on platform"""
        try:
            if platform == Platform.FACEBOOK:
                success, posts, cursor = await self.fetch_facebook_posts(
                    social_account_id, query or "news", max_items
                )
                return success, posts
            
            elif platform == Platform.TWITTER:
                success, posts, cursor = await self.fetch_twitter_posts(
                    social_account_id, query or "news", max_items
                )
                return success, posts
            
            else:
                logger.warning(f"Platform {platform} not supported for fetching")
                return False, []
                
        except Exception as e:
            logger.exception(f"Failed to fetch social content: {e}")
            return False, []
    
    async def get_unprocessed_content(
        self, 
        tenant_id: str, 
        platform: Platform = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get unprocessed social media content for moderation/analysis"""
        try:
            query = self._get_db_client().table('social_media_content').select('*').eq(
                'tenant_id', tenant_id
            ).eq('processed', False)
            
            if platform:
                query = query.eq('platform', platform.value)
            
            response = query.order('fetched_at', desc=True).limit(limit).execute()
            return response.data or []
            
        except Exception as e:
            logger.exception(f"Failed to get unprocessed content: {e}")
            return []
    
    async def mark_content_processed(self, content_ids: List[str]) -> bool:
        """Mark content as processed"""
        try:
            result = self._get_db_client().table('social_media_content').update({
                'processed': True,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).in_('id', content_ids).execute()
            
            return bool(result.data)
        except Exception as e:
            logger.exception(f"Failed to mark content as processed: {e}")
            return False
