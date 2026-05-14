#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Publish Service for OmniPush Platform

Handles publishing posts to various social media channels with configurable options.
Supports news card generation, text-only publishing, and image publishing.
Now supports channel group-based publishing with multiple social accounts.
"""

import asyncio
import os
import mimetypes
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from uuid import UUID

from core.logging_config import get_logger
from services.content_service import generate_news_card_from_text
from services.social_posting_service import SocialPostingService
from services.token_cache_service import TokenCacheService
from services.content_adaptation_service import ContentAdaptationService, ChannelConfig
from services.image_search_service import image_search_service
from models.content import PostStatus, Platform

logger = get_logger(__name__)


class PublishConfig:
    """Configuration for publishing posts"""
    
    def __init__(
        self,
        channels: List[str] = None,
        publish_text: bool = True,
        publish_image: bool = True,
        generate_news_card: bool = True,
        facebook_page_id: str = "61579232464240",
        whatsapp_group_id: str = "120363422585569875@g.us",
        facebook_access_token: str = None,
        periskope_api_key: str = None,
        whatsapp_sender_phone: str = "+918189900456",
        # New channel group support
        channel_group_id: str = None,
        social_accounts: List[Dict[str, Any]] = None,
        template_name: str = None
    ):
        self.channels = channels or ["facebook", "instagram", "whatsapp"]
        self.publish_text = publish_text
        self.publish_image = publish_image
        self.generate_news_card = generate_news_card
        self.facebook_page_id = facebook_page_id
        self.whatsapp_group_id = whatsapp_group_id
        self.facebook_access_token = os.getenv("FB_LONG_LIVED_TOKEN") or os.getenv("FACEBOOK_ACCESS_TOKEN") or facebook_access_token
        self.periskope_api_key =  os.getenv("PERISKOPE_API_KEY") or periskope_api_key
        self.whatsapp_sender_phone = os.getenv("WHATSAPP_SENDER_PHONE") or whatsapp_sender_phone

        # Channel group support
        self.channel_group_id = channel_group_id
        self.social_accounts = social_accounts or []
        self.template_name = template_name


class PublishResult:
    """Result of publishing to a specific channel"""
    
    def __init__(self, platform: str, success: bool, message: str = "", error: str = None, post_id: str = None, account_name: str = None):
        self.platform = platform
        self.success = success
        self.message = message
        self.error = error
        self.post_id = post_id
        self.account_name = account_name
        self.published_at = datetime.utcnow() if success else None


class PublishService:
    """Service for publishing posts to social media platforms"""

    def __init__(self, config: PublishConfig = None):
        self.config = config or PublishConfig()
        self.db_client = None
        self.token_cache = TokenCacheService()
        self.content_adaptation_service = ContentAdaptationService()
        self.social_posting_service = SocialPostingService()  # Initialize unified social posting service
        
    def set_db_client(self, db_client):
        """Set database client for updating post status"""
        self.db_client = db_client

    def _get_db_client(self):
        """Get the appropriate database client (service_client if wrapper, or raw client)"""
        if hasattr(self.db_client, 'service_client'):
            return self.db_client.service_client
        return self.db_client
    
    def set_social_accounts(self, social_accounts: List[Dict[str, Any]]):
        """Set social accounts for channel group publishing"""
        self.config.social_accounts = social_accounts
        logger.info(f"Set {len(social_accounts)} social accounts for publishing")

    def _detect_media_type(self, file_path_or_url: str) -> str:
        """
        Detect media type (IMAGE or VIDEO) from file path or URL

        Args:
            file_path_or_url: Local file path or URL to media

        Returns:
            'VIDEO' for video files, 'IMAGE' for image files or unknown types
        """
        if not file_path_or_url:
            return "IMAGE"

        # Clean URL - remove query parameters for extension detection
        clean_path = file_path_or_url.split('?')[0].lower()

        # Check for video extensions
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.3gp', '.flv', '.wmv']
        if any(clean_path.endswith(ext) for ext in video_extensions):
            return "VIDEO"

        # Try using mimetypes for more accurate detection
        try:
            mimetype, _ = mimetypes.guess_type(file_path_or_url)
            if mimetype and mimetype.startswith('video/'):
                return "VIDEO"
        except:
            pass

        # Default to IMAGE for images and unknown types
        return "IMAGE"

    async def publish_to_tenant_accounts(
        self,
        tenant_id: str,
        content: str,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None,
        platforms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Publish content to all connected social accounts for a tenant using database credentials

        Args:
            tenant_id: Tenant ID
            content: Content to post
            media_url: Optional media URL
            media_type: Media type ('IMAGE' or 'VIDEO')
            platforms: Optional list of platforms to post to

        Returns:
            Dictionary with platform results
        """
        logger.info(f"Publishing to tenant {tenant_id} accounts - platforms: {platforms}")

        try:
            # Use the unified social posting service with database credentials
            results = self.social_posting_service.post_to_all_accounts(
                tenant_id=tenant_id,
                content=content,
                media_url=media_url,
                media_type=media_type,
                platforms=platforms
            )

            # Convert to expected format for consistency
            formatted_results = {}
            for platform, responses in results.items():
                platform_results = []
                for response in responses:
                    result = {
                        "success": not response.error,
                        "platform": response.platform,
                        "post_id": response.post_id,
                        "message": response.message or response.error,
                        "error": response.error
                    }
                    platform_results.append(result)
                formatted_results[platform] = platform_results

            logger.info(f"Completed publishing to tenant {tenant_id} - {len(formatted_results)} platforms")
            return formatted_results

        except Exception as e:
            logger.error(f"Error publishing to tenant {tenant_id} accounts: {e}")
            return {
                "error": [{
                    "success": False,
                    "platform": "all",
                    "error": f"Failed to publish: {str(e)}"
                }]
            }

    async def publish_to_specific_accounts(
        self,
        tenant_id: str,
        account_ids: List[str],
        content: str,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Publish content to specific social accounts by their IDs

        Args:
            tenant_id: Tenant ID for security
            account_ids: List of social account IDs
            content: Content to post
            media_url: Optional media URL
            media_type: Media type ('IMAGE' or 'VIDEO')

        Returns:
            List of results for each account
        """
        logger.info(f"Publishing to specific accounts: {account_ids}")

        results = []
        for account_id in account_ids:
            try:
                response = self.social_posting_service.post_to_account(
                    account_id=account_id,
                    tenant_id=tenant_id,
                    content=content,
                    media_url=media_url,
                    media_type=media_type
                )

                result = {
                    "account_id": account_id,
                    "success": not response.error,
                    "platform": response.platform,
                    "post_id": response.post_id,
                    "message": response.message or response.error,
                    "error": response.error
                }
                results.append(result)

            except Exception as e:
                logger.error(f"Error posting to account {account_id}: {e}")
                results.append({
                    "account_id": account_id,
                    "success": False,
                    "platform": "unknown",
                    "error": f"Failed to post: {str(e)}"
                })

        logger.info(f"Completed publishing to {len(results)} specific accounts")
        return results
    
    async def _preview_configured_channels(self, content: str, image_url: str = None, tenant_id: str = None) -> Dict[str, Any]:
        """Preview mode for traditional channels - generate news cards but don't publish"""
        results = {}
        
        for channel in self.config.channels:
            channel_lower = channel.lower()
            logger.info(f"Previewing for {channel_lower}...")
            
            # Generate preview without actually publishing
            results[channel_lower] = {
                "success": True,
                "platform": channel_lower,
                "ready_for_publishing": True,
                "message": f"Ready to publish to {channel_lower}",
                "preview_mode": True,
                "published_at": None  # No actual publishing in preview
            }
        
        return results

    async def _preview_channel_group_accounts(self, content: str, image_url: str = None, tenant_id: str = None, post_id: str = None, source_image_url: str = None) -> Dict[str, Any]:
        """Preview mode for channel group accounts - generate news cards and adapt content but don't publish"""
        results = {}
        
        if not self.config.social_accounts:
            logger.warning("No social accounts configured for channel group preview")
            return results
        
        logger.info(f"Previewing for {len(self.config.social_accounts)} social accounts from channel group with content adaptation")
        
        try:
            # Step 1: Get channel configurations for content adaptation
            social_account_ids = [account['id'] for account in self.config.social_accounts]
            channel_configs = await self.content_adaptation_service.get_channel_configs(
                self.db_client, social_account_ids, tenant_id
            )
            
            if not channel_configs:
                logger.warning("No channel configurations found, using original content")
                channel_configs = [
                    ChannelConfig(
                        id=account['id'],
                        platform=account['platform'], 
                        account_name=account['account_name'],
                        content_tone='professional'
                    )
                    for account in self.config.social_accounts
                ]
            
            # Step 2: Adapt content for ALL channels using multi-page news in batches
            # This replaces the old batch approach with consolidated multi-page generation
            # Processes in batches of 20 accounts per LLM call for optimal performance
            # IMPORTANT: Enable district extraction for proper newscard generation with district/scope
            should_generate_headline = getattr(self, '_should_include_headline', False)
            batch_results, extracted_district = await self.content_adaptation_service.adapt_content_multi_page_news(
                original_content=content,
                channels=channel_configs,
                include_headline=should_generate_headline,
                extract_district=True,  # Enable district extraction and scope determination (national/state/district)
                batch_size=20,  # Default batch size
                source_image_url=source_image_url  # Pass source image for LLM vision
            )

            # Log extracted district for debugging
            if extracted_district:
                logger.info(f"📍 District/Scope extracted from content: {extracted_district}")
            else:
                logger.warning("⚠️ No district/scope extracted from content")

            # Step 3: Create a mapping of channel_id -> adapted content
            adapted_content_map = {}
            for batch_result in batch_results:
                for adaptation in batch_result.adaptations:
                    adapted_content_map[adaptation.channel_id] = adaptation

                    # Track adaptation results in database
                    if post_id and self.db_client:
                        try:
                            await self.content_adaptation_service.track_adaptation_result(
                                self.db_client, post_id, adaptation.channel_id, adaptation, tenant_id
                            )
                        except Exception as track_error:
                            logger.warning(f"Failed to track adaptation result: {track_error}")

            # Step 4: Preview each account and generate channel-specific newscards
            for account in self.config.social_accounts:
                try:
                    platform = account['platform'].lower()
                    account_name = account['account_name']
                    account_id = account['id']
                    
                    # Get adapted content or fall back to original
                    adaptation = adapted_content_map.get(account_id)
                    if adaptation and adaptation.success:
                        final_content = adaptation.adapted_content
                        logger.info(f"Using adapted content for {platform}: {account_name}")
                    else:
                        final_content = content
                        logger.warning(f"Using original content for {platform}: {account_name} (adaptation failed: {adaptation.error_message if adaptation else 'No adaptation found'})")

                    # Determine headline: use provided headline or LLM-generated headline
                    provided_headline = getattr(self, '_provided_headline', None)
                    final_headline = (
                        provided_headline or  # From user input
                        (adaptation.headline if adaptation and adaptation.success and adaptation.headline else None)  # From LLM
                    )

                    # Generate channel-specific newscard if needed
                    channel_image_url = image_url
                    
                    # Generate newscard when:
                    # 1. No image provided and newscard generation is enabled (text → card)
                    # 2. Mode is newscard_with_image (explicit)
                    # 3. Mode is news_card with a user-selected template (image becomes background)
                    _mode = getattr(self, '_post_mode', None)
                    should_generate_channel_newscard = self.config.generate_news_card and (
                        image_url is None or
                        _mode in ("newscard_with_image", "news_card")
                    )

                    if should_generate_channel_newscard:
                        logger.info(f"Generating channel-specific newscard for {platform}: {account_name}")
                        try:
                            from services.content_service import generate_news_card_from_text

                            # Create channel-specific content adaptation for newscard
                            channel_adaptation = {
                                'channel_name': account_name,
                                'channel_id': account_id,
                                'platform': platform,
                            }

                            # Pass image_url as template background when in news_card/newscard_with_image mode
                            if _mode in ("newscard_with_image", "news_card"):
                                newscard_image_url = image_url
                            else:
                                newscard_image_url = None
                            
                            news_card_result = await generate_news_card_from_text(
                                title="",
                                content=final_content,
                                tenant_id=tenant_id,
                                content_adaptation=channel_adaptation,
                                channel_id=account_id,
                                image_url=newscard_image_url,
                                headline=final_headline,
                                district=extracted_district,
                                template_name=self.config.template_name
                            )

                            if news_card_result.get('url'):
                                channel_image_url = news_card_result['url']
                                logger.info(f"Channel-specific newscard generated for {account_name}: {channel_image_url}")
                            else:
                                logger.warning(f"Failed to generate newscard for {account_name}")
                        except Exception as newscard_error:
                            logger.error(f"Error generating newscard for {account_name}: {newscard_error}")

                    logger.info(f"Previewing for {platform}: {account_name}")
                    
                    # Use account-specific key for results
                    result_key = f"{platform}_{account_id}"
                    results[result_key] = {
                        "success": True,
                        "message": f"Ready to publish to {account_name}",
                        "error": None,
                        "post_id": None,  # No actual publishing in preview
                        "account_name": account_name,
                        "platform": platform,
                        "account_id": account_id,
                        "published_at": None,  # No actual publishing in preview
                        "content_adapted": adaptation.success if adaptation else False,
                        "original_content_length": len(content),
                        "adapted_content_length": len(final_content),
                        "preview_mode": True,
                        "ready_for_publishing": True,
                        "news_card_url": channel_image_url
                    }
                    
                    logger.info(f"Preview ready for {platform} ({account_name})")
                        
                except Exception as e:
                    logger.exception(f"Error previewing account {account.get('account_name', account.get('id'))}: {e}")
                    result_key = f"{account['platform'].lower()}_{account['id']}"
                    results[result_key] = {
                        "success": False,
                        "error": str(e),
                        "account_name": account.get('account_name', 'Unknown'),
                        "platform": account['platform'].lower(),
                        "account_id": account['id'],
                        "published_at": None,
                        "content_adapted": False,
                        "preview_mode": True
                    }
                    
        except Exception as e:
            logger.exception(f"Content adaptation failed in preview: {e}")
            # Fallback to original content without adaptation
            for account in self.config.social_accounts:
                try:
                    platform = account['platform'].lower()
                    account_name = account['account_name']
                    account_id = account['id']
                    
                    logger.info(f"Previewing for {platform}: {account_name} (without adaptation)")
                    
                    result_key = f"{platform}_{account_id}"
                    results[result_key] = {
                        "success": True,
                        "message": f"Ready to publish to {account_name}",
                        "error": None,
                        "post_id": None,
                        "account_name": account_name,
                        "platform": platform,
                        "account_id": account_id,
                        "published_at": None,
                        "content_adapted": False,
                        "preview_mode": True,
                        "ready_for_publishing": True
                    }
                    
                except Exception as account_error:
                    logger.exception(f"Error previewing account {account.get('account_name')}: {account_error}")
                    continue
        
        return results

    async def _simulate_publishing_results(self, content: str, image_url: str = None, tenant_id: str = None) -> Dict[str, Any]:
        """Legacy simulate publishing results method - kept for backward compatibility"""
        results = {}
        
        if self.config.social_accounts:
            # Simulate results for channel group accounts
            for account in self.config.social_accounts:
                platform = account.get('platform', 'unknown').lower()
                account_name = account.get('account_name', f"{platform}_account")
                account_id = account['id']
                
                results[account_id] = {
                    "success": True,
                    "platform": platform,
                    "account_name": account_name,
                    "ready_for_publishing": True,
                    "message": f"Ready to publish to {account_name}",
                    "preview_mode": True
                }
        else:
            # Simulate results for traditional channels
            for channel in self.config.channels:
                channel_lower = channel.lower()
                results[channel_lower] = {
                    "success": True,
                    "platform": channel_lower,
                    "ready_for_publishing": True,
                    "message": f"Ready to publish to {channel_lower}",
                    "preview_mode": True
                }
        
        return results
    
    async def publish_post(
        self,
        post_id: str,
        title: str,
        content: str,
        tenant_id: str = None,
        user_id: str = None,
        image_url: str = None,
        post_mode: str = None,
        preview_mode: bool = False,
        source_image_url: str = None
    ) -> Dict[str, Any]:
        """
        Publish a post to configured channels

        Args:
            post_id: ID of the post to publish
            title: Post title
            content: Post content text
            tenant_id: Tenant ID for context
            user_id: User ID who initiated the publish
            image_url: Optional image URL to use
            post_mode: Post mode ("text", "image", "text_with_images")
            preview_mode: If True, performs all steps except actual publishing
            source_image_url: Optional source image for LLM vision (repost flow only)

        Returns:
            Dictionary with publish results for each channel
        """
        logger.info(f"Starting publish for post {post_id}: {title[:50]}...")
        logger.info(f"Publish params - tenant_id: {tenant_id}, user_id: {user_id}, image_url: {image_url}, post_mode: {post_mode}, source_image_url: {source_image_url}")

        # Store post mode for channel-specific processing
        self._post_mode = post_mode

        # Special handling for link mode - skip all processing and post link directly
        if post_mode == "link":
            logger.info("🔗 Link mode detected - skipping content generation and newscard creation")
            try:
                # Step 1: Update post status to publishing (skip in preview mode)
                if self.db_client and not preview_mode:
                    await self._update_post_status(post_id, PostStatus.PUBLISHING, tenant_id)

                # Step 2: Publish link directly to channels
                if preview_mode:
                    logger.info("Preview mode - generating preview for link post")
                    if self.config.social_accounts:
                        results = await self._preview_channel_group_accounts(content, None, tenant_id, post_id, source_image_url)
                    else:
                        results = await self._preview_configured_channels(content, None, tenant_id)
                    all_success = True
                else:
                    # Actual publishing
                    if self.config.social_accounts:
                        results = await self._publish_to_channel_group_accounts(content, None, tenant_id, post_id, source_image_url)
                    else:
                        results = await self._publish_to_configured_channels(content, None, tenant_id)
                    all_success = all(result.get("success", False) for result in results.values())

                # Step 3: Update post status based on results (skip in preview mode)
                if self.db_client and not preview_mode:
                    if all_success:
                        await self._update_post_status(post_id, PostStatus.PUBLISHED, tenant_id)
                    else:
                        await self._update_post_status(post_id, PostStatus.FAILED, tenant_id)

                logger.info(f"✅ Link post publishing completed - Success: {all_success}")

                return {
                    "post_id": post_id,
                    "success": all_success,
                    "channels": results,
                    "published_at": datetime.utcnow().isoformat() if all_success and not preview_mode else None
                }
            except Exception as e:
                logger.exception(f"Failed to publish link post: {e}")
                if self.db_client and not preview_mode:
                    await self._update_post_status(post_id, PostStatus.FAILED, tenant_id)
                return {
                    "post_id": post_id,
                    "success": False,
                    "error": str(e)
                }

        try:
            # Step 0: Check if any social accounts have auto_image_search enabled
            logger.info(f"🔍 Checking auto image search settings for {len(self.config.social_accounts)} social accounts")

            for i, account in enumerate(self.config.social_accounts):
                auto_search_enabled = account.get('auto_image_search', False)
                logger.info(f"  Account {i+1}: {account.get('account_name', 'Unknown')} ({account.get('platform', 'Unknown')}) - auto_image_search: {auto_search_enabled}")

            auto_enabled_accounts = [
                account for account in self.config.social_accounts
                if account.get('auto_image_search', False)
            ]
            auto_image_search_enabled = len(auto_enabled_accounts) > 0

            logger.info(f"🎯 Auto image search summary: {len(auto_enabled_accounts)} out of {len(self.config.social_accounts)} accounts have auto_image_search enabled")

            if not auto_image_search_enabled:
                logger.info("⚠️ No accounts have auto_image_search enabled - skipping auto image search")

            # Handle automatic image search if enabled and no image is provided
            if auto_image_search_enabled and not image_url and tenant_id:
                logger.info("Auto image search enabled for at least one account")

                # Get post details to check for image_search_caption
                try:
                    db_client = self._get_db_client()
                    if db_client:
                        post_response = db_client.table('posts').select(
                            'image_search_caption'
                        ).eq('id', post_id).eq('tenant_id', tenant_id).maybe_single().execute()

                        if post_response.data and post_response.data.get('image_search_caption'):
                            search_term = post_response.data['image_search_caption']
                            logger.info(f"Found image search caption: '{search_term}'")

                            # Search and download image
                            search_result = await image_search_service.search_image(search_term, tenant_id)

                            if search_result:
                                # Store the auto-downloaded image in media table
                                media_data = {
                                    'id': search_result['media_id'],
                                    'tenant_id': tenant_id,
                                    'file_name': search_result['filename'],
                                    'content_type': search_result['content_type'],
                                    'mime_type': search_result['content_type'],
                                    'media_type': 'image',
                                    'file_size': search_result['file_size'],
                                    'file_path': search_result['url'],
                                    's3_key': search_result.get('s3_key'),
                                    's3_bucket': os.getenv('AWS_S3_BUCKET') if search_result.get('s3_key') else None,
                                    'size': search_result['file_size'],
                                    'created_at': datetime.utcnow().isoformat(),
                                    'metadata': {
                                        'auto_generated': True,
                                        'search_term': search_term,
                                        'attribution': search_result.get('attribution', {})
                                    }
                                }

                                # Insert into media table
                                try:
                                    db_client.table('media').insert(media_data).execute()
                                    logger.info(f"Stored auto-downloaded image in media table: {search_result['media_id']}")
                                except Exception:
                                    # Try media_assets as fallback
                                    try:
                                        db_client.table('media_assets').insert(media_data).execute()
                                        logger.info(f"Stored auto-downloaded image in media_assets table: {search_result['media_id']}")
                                    except Exception as e:
                                        logger.warning(f"Failed to store auto-downloaded image metadata: {e}")

                                # Use the auto-downloaded image
                                image_url = search_result['url']

                                # Override post mode based on auto image search
                                if post_mode == "text":
                                    self._post_mode = "text_with_images"
                                    logger.info("Auto image search: Changed post mode from 'text' to 'text_with_images'")
                                elif post_mode == "news_card":
                                    self._post_mode = "newscard_with_image"
                                    logger.info("Auto image search: Changed post mode from 'news_card' to 'newscard_with_image'")

                                logger.info(f"Auto image search successful: {image_url}")
                            else:
                                logger.warning(f"Auto image search failed for term: '{search_term}'")
                        else:
                            logger.info("No image_search_caption found for auto image search")
                    else:
                        logger.warning("No database client available for auto image search")

                except Exception as search_error:
                    logger.error(f"Auto image search failed: {search_error}")
                    # Continue with publishing even if auto image search fails

            # Step 1: Determine if we should generate a news card based on post mode
            news_card_url = image_url  # Use provided image first
            should_generate_newscard = False
            
            # Generate news card based on post mode and conditions
            if self.config.generate_news_card and self.config.publish_image:
                if post_mode == "news_card" and not news_card_url:
                    # Explicit news card mode - always generate newscard
                    should_generate_newscard = True
                    logger.info("Explicit news card mode - will generate news card")
                elif post_mode == "newscard_with_image":
                    # Newscard with image mode - generate newscard using provided image
                    should_generate_newscard = True
                    logger.info("Newscard with image mode - will generate news card with image")
                elif post_mode == "image" and not news_card_url:
                    # Image-only post mode without image - generate newscard
                    should_generate_newscard = True
                    logger.info("Image-only post without image - will generate news card")
                elif post_mode == "text":
                    # Text-only post mode - do not generate newscard
                    should_generate_newscard = False
                    logger.info("Text-only post - skipping news card generation")
                elif post_mode == "text_with_images":
                    # Text with images mode - should have images already, no newscard needed
                    should_generate_newscard = False
                    logger.info("Text with images post - no news card generation needed")
                elif not post_mode and not news_card_url:
                    # Backwards compatibility: if no mode specified, generate newscard as before
                    should_generate_newscard = True
                    logger.info("No post mode specified - generating news card for backwards compatibility")
            
            # Generate global newscard only when NOT using channel groups
            # For channel groups, newscard will be generated per-channel with fallback logic
            if should_generate_newscard and not self.config.social_accounts:
                logger.info(f"Generating news card (mode: {post_mode}, no channel groups)...")

                # Get content adaptation settings from social channel configs if available
                content_adaptation = await self._get_content_adaptation_from_channels(tenant_id)

                if not content or not content.strip():
                    logger.warning("Content is empty - skipping news card generation")
                    # return {
                    #     "post_id": post_id,
                    #     "success": False,
                    #     "error": "Content is empty",
                    #     "channels": {},
                    #     "published_at": None
                    # }
                else:
                    # Note: For global newscard, district extraction is not needed here
                    # as it's handled per-channel in _publish_to_channel_group_accounts
                    news_card_result = await generate_news_card_from_text(
                        title, content, tenant_id, content_adaptation, channel_id=None, image_url=image_url,
                        template_name=self.config.template_name
                    )
                    if news_card_result.get('url'):
                        news_card_url = news_card_result['url']
                        logger.info(f"News card generated: {news_card_url} (LLM: {news_card_result.get('llm_generated', False)}, Adapted: {news_card_result.get('content_adapted', False)})")
                    else:
                        logger.warning("Failed to generate news card")
            elif should_generate_newscard and self.config.social_accounts:
                logger.info("Skipping global newscard generation - will generate channel-specific newscards with fallback")
            elif image_url:
                logger.info(f"Using provided image: {image_url}")
            
            # Step 2: Update post status to publishing (skip in preview mode)
            if self.db_client and not preview_mode:
                await self._update_post_status(post_id, PostStatus.PUBLISHING, tenant_id)
            
            # Step 3: Determine publishing targets and execute (or simulate in preview mode)
            if preview_mode:
                # Preview mode: Generate actual news cards and adapt content but skip publishing to platforms
                logger.info("Preview mode - generating news cards without publishing")
                if self.config.social_accounts:
                    # For newscard_with_image mode, use the global newscard; otherwise use per-channel generation
                    preview_image_url = news_card_url if (post_mode == "newscard_with_image" and news_card_url) else None
                    results = await self._preview_channel_group_accounts(content, preview_image_url, tenant_id, post_id, source_image_url)
                else:
                    # Generate global newscard but skip publishing to platforms
                    results = await self._preview_configured_channels(content, news_card_url, tenant_id)
                all_success = True  # Preview is always "successful"
            else:
                # Actual publishing
                if self.config.social_accounts:
                    # Use channel group accounts with content adaptation
                    # For newscard_with_image mode, use the global newscard; otherwise use per-channel generation
                    final_image_url = news_card_url if (post_mode == "newscard_with_image" and news_card_url) else image_url
                    results = await self._publish_to_channel_group_accounts(content, image_url, tenant_id, post_id, source_image_url)
                else:
                    # Use traditional channel-based publishing with global newscard
                    results = await self._publish_to_configured_channels(content, news_card_url, tenant_id)

                # Step 4: Determine overall success
                all_success = all(result.get("success", False) for result in results.values())

            # Extract first channel-specific newscard URL if no global newscard exists
            final_newscard_url = news_card_url
            if not final_newscard_url and results:
                # Check if any channel generated a newscard
                for result in results.values():
                    if result.get("newscard_url"):
                        final_newscard_url = result["newscard_url"]
                        logger.info(f"Using channel-specific newscard URL for post: {final_newscard_url}")
                        break

            # Step 5: Update post status based on results (skip status update in preview mode)
            if self.db_client and not preview_mode:
                final_status = PostStatus.PUBLISHED if all_success else PostStatus.FAILED
                # Store publish results in the publish_results column
                await self._update_post_status(post_id, final_status, tenant_id, {
                    "published_at": datetime.utcnow().isoformat() if all_success else None,
                    "news_card_url": final_newscard_url,
                    "publish_results": results
                })
            elif self.db_client and preview_mode:
                # In preview mode, only update news_card_url if generated
                if final_newscard_url:
                    await self._update_post_status(post_id, PostStatus.DRAFT, tenant_id, {
                        "news_card_url": final_newscard_url
                    })
            
            # Step 6: Return comprehensive results
            return {
                "post_id": post_id,
                "success": all_success,
                "news_card_url": final_newscard_url,
                "channels": results,
                "published_at": datetime.utcnow().isoformat() if all_success else None,
                "summary": {
                    "total_channels": len(results),
                    "successful": len([r for r in results.values() if r.get("success")]),
                    "failed": len([r for r in results.values() if not r.get("success")])
                }
            }
            
        except Exception as e:
            logger.exception(f"Publish failed for post {post_id}: {e}")
            
            # Update post status to failed
            if self.db_client:
                await self._update_post_status(post_id, PostStatus.FAILED, tenant_id)
            
            return {
                "post_id": post_id,
                "success": False,
                "error": str(e),
                "channels": {},
                "published_at": None
            }
    
    async def _publish_to_configured_channels(self, content: str, image_url: str = None, tenant_id: str = None) -> Dict[str, Any]:
        """Publish to traditionally configured channels"""
        results = {}
        
        for channel in self.config.channels:
            channel_lower = channel.lower()
            logger.info(f"Publishing to {channel_lower}...")
            
            try:
                if channel_lower == "facebook":
                    result = await self._publish_to_facebook(content, image_url, tenant_id)
                elif channel_lower == "instagram":
                    result = await self._publish_to_instagram(content, image_url, tenant_id)
                elif channel_lower == "whatsapp":
                    result = await self._publish_to_whatsapp(content, image_url)
                else:
                    result = PublishResult(
                        platform=channel_lower,
                        success=False,
                        error=f"Unsupported platform: {channel_lower}"
                    )
                
                results[channel_lower] = {
                    "success": result.success,
                    "message": result.message,
                    "error": result.error,
                    "post_id": result.post_id,
                    "account_name": result.account_name,
                    "published_at": result.published_at.isoformat() if result.published_at else None
                }
                
                if not result.success:
                    logger.exception(f"Failed to publish to {channel_lower}: {result.error}")
                else:
                    logger.info(f"Successfully published to {channel_lower}")
                    
            except Exception as e:
                logger.exception(f"Error publishing to {channel_lower}: {e}")
                results[channel_lower] = {
                    "success": False,
                    "error": str(e),
                    "published_at": None
                }
        
        return results
    
    async def _publish_to_channel_group_accounts(self, content: str, image_url: str = None, tenant_id: str = None, post_id: str = None, source_image_url: str = None) -> Dict[str, Any]:
        """Publish to social accounts from channel group with content adaptation"""
        results = {}

        if not self.config.social_accounts:
            logger.warning("No social accounts configured for channel group publishing")
            return results

        # Check if link mode - skip content adaptation
        is_link_mode = hasattr(self, '_post_mode') and self._post_mode == "link"

        if is_link_mode:
            logger.info("🔗 Link mode: Skipping content adaptation and LLM calls")
            # For link mode, publish directly without adaptation
            for account in self.config.social_accounts:
                account_id = account['id']
                platform = account['platform']
                account_name = account.get('account_name', 'Unknown')

                logger.info(f"Publishing link to {platform}: {account_name}")

                try:
                    # For link mode, just send the URL as-is
                    # Ensure it's a clean URL without extra formatting
                    link_content = content.strip()

                    # Log the exact content being sent
                    logger.info(f"📤 Sending to {account_name}: '{link_content}'")

                    # Publish to the platform using post_to_account
                    response = self.social_posting_service.post_to_account(
                        account_id=account_id,
                        tenant_id=tenant_id,
                        content=link_content,
                        media_url=None,
                        media_type=None
                    )

                    if not response.error:
                        logger.info(f"Successfully published link to {platform} ({account_name})")
                        results[account_id] = {
                            "success": True,
                            "platform": platform,
                            "account_name": account_name,
                            "message": f"Link posted to {account_name}"
                        }
                    else:
                        logger.error(f"Failed to publish link to {platform} ({account_name}): {response.error}")
                        results[account_id] = {
                            "success": False,
                            "platform": platform,
                            "account_name": account_name,
                            "error": response.error
                        }

                except Exception as e:
                    logger.exception(f"Error publishing link to {platform} ({account_name}): {e}")
                    results[account_id] = {
                        "success": False,
                        "platform": platform,
                        "account_name": account_name,
                        "error": str(e)
                    }

            return results

        logger.info(f"Publishing to {len(self.config.social_accounts)} social accounts from channel group with content adaptation")

        try:
            # Step 1: Get channel configurations for content adaptation
            social_account_ids = [account['id'] for account in self.config.social_accounts]
            channel_configs = await self.content_adaptation_service.get_channel_configs(
                self.db_client, social_account_ids, tenant_id
            )

            # Step 2: Adapt content — skip AI entirely when no custom channel configs exist
            adapted_content_map = {}
            extracted_district = None

            if not channel_configs:
                logger.info("No channel configurations found — publishing original content without AI adaptation")
                # Build a pass-through map so the rest of the pipeline works unchanged
                for account in self.config.social_accounts:
                    class _PassThrough:
                        def __init__(self, acct_id, orig):
                            self.channel_id = acct_id
                            self.adapted_content = orig
                            self.success = True
                            self.error_message = None
                            self.headline = None
                            self.news_card_url = None
                            self.district = None
                            self.scope = None
                    adapted_content_map[account['id']] = _PassThrough(account['id'], content)
            else:
                should_generate_headline = getattr(self, '_should_include_headline', False)
                batch_results, extracted_district = await self.content_adaptation_service.adapt_content_multi_page_news(
                    original_content=content,
                    channels=channel_configs,
                    include_headline=should_generate_headline,
                    extract_district=True,
                    batch_size=20,
                    source_image_url=source_image_url
                )

                if extracted_district:
                    logger.info(f"📍 District/Scope extracted from content: {extracted_district}")

                for batch_result in batch_results:
                    for adaptation in batch_result.adaptations:
                        adapted_content_map[adaptation.channel_id] = adaptation

                        if post_id and self.db_client:
                            try:
                                await self.content_adaptation_service.track_adaptation_result(
                                    self.db_client, post_id, adaptation.channel_id, adaptation, tenant_id
                                )
                            except Exception as track_error:
                                logger.warning(f"Failed to track adaptation result: {track_error}")
            
            # Step 4: Publish to each account using adapted content and channel-specific newscards
            for account in self.config.social_accounts:
                try:
                    platform = account['platform'].lower()
                    account_name = account['account_name']
                    account_id = account['id']
                    
                    # Get adapted content or fall back to original
                    adaptation = adapted_content_map.get(account_id)
                    if adaptation and adaptation.success:
                        final_content = adaptation.adapted_content
                        logger.info(f"Using adapted content for {platform}: {account_name}")
                    else:
                        final_content = content
                        logger.warning(f"Using original content for {platform}: {account_name} (adaptation failed: {adaptation.error_message if adaptation else 'No adaptation found'})")

                    # Determine headline: use provided headline or LLM-generated headline
                    provided_headline = getattr(self, '_provided_headline', None)
                    final_headline = (
                        provided_headline or  # From user input
                        (adaptation.headline if adaptation and adaptation.success and adaptation.headline else None)  # From LLM
                    )

                    # Generate channel-specific newscard if needed
                    channel_image_url = image_url  # Start with provided image (if any)

                    # Generate newscard when:
                    # 1. No image provided and newscard generation is enabled (text → card)
                    # 2. Mode is newscard_with_image (explicit)
                    # 3. Mode is news_card with a user-selected template (image becomes background)
                    _mode = getattr(self, '_post_mode', None)
                    should_generate_channel_newscard = self.config.generate_news_card and (
                        image_url is None or
                        _mode in ("newscard_with_image", "news_card")
                    )

                    if should_generate_channel_newscard:
                        logger.info(f"Generating channel-specific newscard for {platform}: {account_name}")
                        channel_newscard_generated = False

                        try:
                            from services.content_service import generate_news_card_from_text

                            # Create channel-specific content adaptation for newscard
                            channel_adaptation = {
                                'channel_name': account_name,
                                'channel_id': account_id,
                                'platform': platform,
                            }

                            # Pass image_url as template background when in news_card/newscard_with_image mode
                            if _mode in ("newscard_with_image", "news_card"):
                                newscard_image_url = image_url
                            else:
                                newscard_image_url = None

                            news_card_result = await generate_news_card_from_text(
                                title="",
                                content=final_content,
                                tenant_id=tenant_id,
                                content_adaptation=channel_adaptation,
                                channel_id=account_id,
                                image_url=newscard_image_url,
                                headline=final_headline,
                                district=extracted_district,
                                template_name=self.config.template_name
                            )

                            if news_card_result.get('url'):
                                channel_image_url = news_card_result['url']
                                channel_newscard_generated = True
                                logger.info(f"✓ Channel-specific newscard generated for {account_name}: {channel_image_url}")
                            else:
                                logger.warning(f"Channel-specific newscard generation returned no URL for {account_name}")

                        except Exception as newscard_error:
                            logger.error(f"Error generating channel-specific newscard for {account_name}: {newscard_error}")

                        # Generate preview/default newscard as fallback if channel-specific generation failed
                        if not channel_newscard_generated:
                            logger.info(f"Generating preview/default newscard as fallback for {account_name}")
                            try:
                                from services.content_service import generate_news_card_from_text

                                # Generate default newscard without channel-specific template
                                fallback_result = await generate_news_card_from_text(
                                    title="",
                                    content=final_content,
                                    tenant_id=tenant_id,
                                    content_adaptation=None,  # No channel-specific adaptation
                                    channel_id=None,  # No specific channel
                                    image_url=newscard_image_url,
                                    headline=final_headline,
                                    district=extracted_district
                                )

                                if fallback_result.get('url'):
                                    channel_image_url = fallback_result['url']
                                    logger.info(f"✓ Preview/default newscard generated as fallback for {account_name}: {channel_image_url}")
                                else:
                                    logger.error(f"Failed to generate fallback newscard for {account_name}")

                            except Exception as fallback_error:
                                logger.error(f"Error generating fallback newscard for {account_name}: {fallback_error}")
                    
                    logger.info(f"Publishing to {platform}: {account_name}")
                    
                    if platform == 'facebook':
                        result = await self._publish_to_facebook_account(account, final_content, channel_image_url, tenant_id)
                    elif platform == 'whatsapp':
                        result = await self._publish_to_whatsapp_account(account, final_content, channel_image_url)
                    elif platform == 'instagram':
                        result = await self._publish_to_instagram_account(account, final_content, channel_image_url)
                    elif platform == 'twitter':
                        result = await self._publish_to_twitter_account(account, final_content, channel_image_url)
                    else:
                        result = PublishResult(
                            platform=platform,
                            success=False,
                            error=f"Unsupported platform: {platform}",
                            account_name=account_name
                        )
                    
                    # Use account-specific key for results
                    result_key = f"{platform}_{account_id}"
                    results[result_key] = {
                        "success": result.success,
                        "message": result.message,
                        "error": result.error,
                        "post_id": result.post_id,
                        "newscard_url": channel_image_url if channel_image_url != image_url else None,  # Save generated newscard URL
                        "account_name": result.account_name,
                        "platform": platform,
                        "account_id": account_id,
                        "published_at": result.published_at.isoformat() if result.published_at else None,
                        "content_adapted": adaptation.success if adaptation else False,
                        "original_content_length": len(content),
                        "adapted_content_length": len(final_content)
                    }
                    
                    if not result.success:
                        logger.exception(f"Failed to publish to {platform} ({account_name}): {result.error}")
                    else:
                        logger.info(f"Successfully published to {platform} ({account_name})")
                        
                except Exception as e:
                    logger.exception(f"Error publishing to account {account.get('account_name', account.get('id'))}: {e}")
                    result_key = f"{account['platform'].lower()}_{account['id']}"
                    results[result_key] = {
                        "success": False,
                        "error": str(e),
                        "account_name": account.get('account_name', 'Unknown'),
                        "platform": account['platform'].lower(),
                        "account_id": account['id'],
                        "published_at": None,
                        "content_adapted": False
                    }
                    
        except Exception as e:
            logger.exception(f"Content adaptation failed: {e}")
            # Fallback to original content without adaptation
            for account in self.config.social_accounts:
                try:
                    platform = account['platform'].lower()
                    account_name = account['account_name']
                    account_id = account['id']
                    
                    logger.info(f"Publishing to {platform}: {account_name} (without adaptation)")
                    
                    if platform == 'facebook':
                        result = await self._publish_to_facebook_account(account, content, image_url, tenant_id)
                    elif platform == 'whatsapp':
                        result = await self._publish_to_whatsapp_account(account, content, image_url)
                    elif platform == 'instagram':
                        result = await self._publish_to_instagram_account(account, content, image_url)
                    elif platform == 'twitter':
                        result = await self._publish_to_twitter_account(account, content, image_url)
                    else:
                        result = PublishResult(
                            platform=platform,
                            success=False,
                            error=f"Unsupported platform: {platform}",
                            account_name=account_name
                        )
                    
                    result_key = f"{platform}_{account_id}"
                    results[result_key] = {
                        "success": result.success,
                        "message": result.message,
                        "error": result.error,
                        "post_id": result.post_id,
                        "account_name": result.account_name,
                        "platform": platform,
                        "account_id": account_id,
                        "published_at": result.published_at.isoformat() if result.published_at else None,
                        "content_adapted": False
                    }
                    
                except Exception as account_error:
                    logger.exception(f"Error publishing to account {account.get('account_name')}: {account_error}")
                    continue
                results[result_key] = {
                    "success": False,
                    "error": str(e),
                    "account_name": account.get('account_name', 'Unknown'),
                    "platform": account.get('platform', 'unknown'),
                    "account_id": account.get('id', 'unknown'),
                    "published_at": None
                }
        
        return results
    
    async def _get_content_adaptation_from_channels(self, tenant_id: str = None) -> Dict[str, Any]:
        """Get content adaptation settings from social channel configs"""
        try:
            # If social accounts are configured, use their settings
            if self.config.social_accounts and self.db_client:
                social_account_ids = [account['id'] for account in self.config.social_accounts]
                channel_configs = await self.content_adaptation_service.get_channel_configs(
                    self.db_client, social_account_ids, tenant_id
                )
                
                if channel_configs:
                    # Use settings from the first channel config as base for news card
                    first_config = channel_configs[0]
                    content_adaptation = {
                        'tone': first_config.content_tone or 'professional',
                        'style': 'modern',  # Default style
                        'color_scheme': 'default',  # Default color scheme
                        'custom_instructions': first_config.custom_instructions,
                        # Note: Do NOT include channel_name here as it may be used incorrectly as channel_id
                    }
                    logger.info(f"Using content adaptation from channel {first_config.account_name}: tone={first_config.content_tone}")
                    return content_adaptation
            
            # Fallback to default settings
            logger.info("Using default content adaptation settings")
            return {
                'tone': 'professional',
                'style': 'modern', 
                'color_scheme': 'default'
            }
            
        except Exception as e:
            logger.warning(f"Failed to get content adaptation from channels: {e}")
            # Fallback to default settings
            return {
                'tone': 'professional',
                'style': 'modern', 
                'color_scheme': 'default'
            }
    

    async def _publish_to_facebook_account(self, account: Dict[str, Any], content: str, image_url: str = None, tenant_id: str = None) -> PublishResult:
        """Publish to a specific Facebook account using SocialPostingService"""
        # DISABLING FACEBOOK - Temporarily disabled due to posting issues
        # return PublishResult(
        #     platform="facebook",
        #     success=False,
        #     error="Facebook posting is temporarily disabled",
        #     account_name=account.get('account_name', 'Facebook Account')
        # )

        try:
            # Get access token from account
            page_access_token = account.get('access_token')
            if not page_access_token:
                return PublishResult(
                    platform="facebook",
                    success=False,
                    error="Facebook access token not configured",
                    account_name=account['account_name']
                )

            # Get page ID from account
            page_id = account.get('page_id') or account.get('account_id')
            if not page_id:
                return PublishResult(
                    platform="facebook",
                    success=False,
                    error="Facebook page ID not configured",
                    account_name=account['account_name']
                )

            # Prepare content for posting
            message = content if self.config.publish_text else ""
            media_type = self._detect_media_type(image_url) if image_url else "IMAGE"

            # Use SocialPostingService for posting
            response = self.social_posting_service.post_to_facebook(
                user_id=page_id,
                token=page_access_token,
                media_url=image_url or "",
                caption=message,
                media_type=media_type or "IMAGE"
            )

            if not response.error:
                return PublishResult(
                    platform="facebook",
                    success=True,
                    message=response.message or "Posted successfully to Facebook",
                    post_id=response.post_id,
                    account_name=account['account_name']
                )
            else:
                return PublishResult(
                    platform="facebook",
                    success=False,
                    error=response.error or "Unknown Facebook error",
                    account_name=account['account_name']
                )

        except Exception as e:
            return PublishResult(
                platform="facebook",
                success=False,
                error=f"Facebook publish error: {str(e)}",
                account_name=account['account_name']
            )
    
    async def _publish_to_whatsapp_account(self, account: Dict[str, Any], content: str, image_url: str = None) -> PublishResult:
        """Publish to a specific WhatsApp account"""
        try:
            if not self.config.periskope_api_key:
                return PublishResult(
                    platform="whatsapp",
                    success=False,
                    error="Periskope API key not configured",
                    account_name=account['account_name']
                )
            
            # Get Periskope ID
            periskope_id = account.get('periskope_id')
            if not periskope_id:
                return PublishResult(
                    platform="whatsapp",
                    success=False,
                    error="WhatsApp Periskope ID not configured",
                    account_name=account['account_name']
                )
            
            # Prepare message
            message = content if self.config.publish_text else ""
            image_url_to_use = image_url if image_url and self.config.publish_image else None
            
            # Publish to WhatsApp using new social posting service
            response = self.social_posting_service.post_to_whatsapp(
                group_id=periskope_id,
                message=message,
                media_url=image_url_to_use,
                api_key=self.config.periskope_api_key,
                sender_phone=self.config.whatsapp_sender_phone
            )

            if not response.error:
                return PublishResult(
                    platform="whatsapp",
                    success=True,
                    message=response.message or "Posted successfully to WhatsApp",
                    post_id=response.post_id,
                    account_name=account['account_name']
                )
            else:
                return PublishResult(
                    platform="whatsapp",
                    success=False,
                    error=response.error or "Unknown WhatsApp error",
                    account_name=account['account_name']
                )
                
        except Exception as e:
            return PublishResult(
                platform="whatsapp",
                success=False,
                error=f"WhatsApp publish error: {str(e)}",
                account_name=account['account_name']
            )
    
    async def _publish_to_instagram_account(self, account: Dict[str, Any], content: str, image_url: str = None) -> PublishResult:
        """Publish to a specific Instagram account using SocialPostingService"""
        try:
            # Get access token from account
            access_token = account.get('access_token')
            if not access_token:
                return PublishResult(
                    platform="instagram",
                    success=False,
                    error="Instagram access token not configured",
                    account_name=account['account_name']
                )

            # Get Instagram account ID
            account_id = account.get('account_id')
            if not account_id:
                return PublishResult(
                    platform="instagram",
                    success=False,
                    error="Instagram account ID not configured",
                    account_name=account['account_name']
                )

            # Instagram requires media for posting
            if not image_url:
                return PublishResult(
                    platform="instagram",
                    success=False,
                    error="Instagram posts require media (image or video)",
                    account_name=account['account_name']
                )

            # Prepare content for posting
            caption = content if self.config.publish_text else ""

            # Determine media type using robust detection
            media_type = self._detect_media_type(image_url)

            # Use SocialPostingService for posting
            response = self.social_posting_service.post_to_instagram(
                user_id=account_id,
                token=access_token,
                media_url=image_url,
                caption=caption,
                media_type=media_type
            )

            if not response.error:
                return PublishResult(
                    platform="instagram",
                    success=True,
                    message=response.message or "Posted successfully to Instagram",
                    post_id=response.post_id,
                    account_name=account['account_name']
                )
            else:
                return PublishResult(
                    platform="instagram",
                    success=False,
                    error=response.error or "Unknown Instagram error",
                    account_name=account['account_name']
                )

        except Exception as e:
            return PublishResult(
                platform="instagram",
                success=False,
                error=f"Instagram publish error: {str(e)}",
                account_name=account['account_name']
            )
    
    async def _publish_to_twitter_account(self, account: Dict[str, Any], content: str, image_url: str = None) -> PublishResult:
        """Publish to a specific Twitter account (placeholder for future implementation)"""
        return PublishResult(
            platform="twitter",
            success=False,
            error="Twitter publishing not yet implemented",
            account_name=account['account_name']
        )

    async def _publish_to_facebook(self, content: str, image_url: str = None, tenant_id: str = None) -> PublishResult:
        """Publish to Facebook page (legacy method using SocialPostingService)"""
        # DISABLING FACEBOOK - Temporarily disabled due to posting issues
        # return PublishResult(
        #     platform="facebook",
        #     success=False,
        #     error="Facebook posting is temporarily disabled"
        # )

        try:
            if not self.config.facebook_access_token:
                return PublishResult(
                    platform="facebook",
                    success=False,
                    error="Facebook access token not configured"
                )

            # Prepare content for posting
            message = content if self.config.publish_text else ""
            media_type = self._detect_media_type(image_url) if image_url else "IMAGE"

            # Use SocialPostingService for posting
            response = self.social_posting_service.post_to_facebook(
                user_id=self.config.facebook_page_id,
                token=self.config.facebook_access_token,
                media_url=image_url or "",
                caption=message,
                media_type=media_type or "IMAGE"
            )

            if not response.error:
                return PublishResult(
                    platform="facebook",
                    success=True,
                    message=response.message or "Posted successfully to Facebook",
                    post_id=response.post_id
                )
            else:
                return PublishResult(
                    platform="facebook",
                    success=False,
                    error=response.error or "Unknown Facebook error"
                )

        except Exception as e:
            return PublishResult(
                platform="facebook",
                success=False,
                error=f"Facebook publish error: {str(e)}"
            )

    async def _publish_to_instagram(self, content: str, image_url: str = None, tenant_id: str = None) -> PublishResult:
        """Publish to Instagram (legacy method - requires configuration via social accounts)"""
        return PublishResult(
            platform="instagram",
            success=False,
            error="Instagram posting requires social account configuration. Use channel group publishing instead."
        )

    async def _publish_to_whatsapp(self, content: str, image_url: str = None) -> PublishResult:
        """Publish to WhatsApp group (legacy method)"""
        try:
            if not self.config.periskope_api_key:
                return PublishResult(
                    platform="whatsapp",
                    success=False,
                    error="Periskope API key not configured"
                )
            
            # Prepare message
            message = content if self.config.publish_text else ""
            image_url_to_use = image_url if image_url and self.config.publish_image else None
            
            # Publish to WhatsApp using new social posting service
            response = self.social_posting_service.post_to_whatsapp(
                group_id=self.config.whatsapp_group_id,
                message=message,
                media_url=image_url_to_use,
                api_key=self.config.periskope_api_key,
                sender_phone=self.config.whatsapp_sender_phone
            )

            if not response.error:
                return PublishResult(
                    platform="whatsapp",
                    success=True,
                    message=response.message or "Posted successfully to WhatsApp",
                    post_id=response.post_id
                )
            else:
                return PublishResult(
                    platform="whatsapp",
                    success=False,
                    error=response.error or "Unknown WhatsApp error"
                )
                
        except Exception as e:
            return PublishResult(
                platform="whatsapp",
                success=False,
                error=f"WhatsApp publish error: {str(e)}"
            )
    
    async def _update_post_status(
        self,
        post_id: str,
        status: PostStatus,
        tenant_id: str = None,
        additional_data: Dict[str, Any] = None
    ):
        """Update post status in database"""
        try:
            if not self.db_client:
                return

            # Skip database update for preview posts (non-UUID post_id like "preview")
            try:
                UUID(post_id)
            except (ValueError, AttributeError):
                logger.debug(f"Skipping database update for non-UUID post_id: {post_id}")
                return

            update_data = {
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat()
            }

            if additional_data:
                update_data.update(additional_data)

            # Build query
            query = self._get_db_client().table('posts').update(update_data).eq('id', post_id)

            if tenant_id:
                query = query.eq('tenant_id', tenant_id)

            result = query.execute()

            if result.data:
                logger.info(f"Updated post {post_id} status to {status.value}")
            else:
                logger.warning(f"Failed to update post {post_id} status")

        except Exception as e:
            logger.exception(f"Error updating post status: {e}")
    
    async def publish_approved_posts(
        self, 
        tenant_id: str,
        user_id: str = None,
        max_posts: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Publish all approved posts for a tenant
        
        Args:
            tenant_id: Tenant ID to publish posts for
            user_id: User ID who initiated the publish
            max_posts: Maximum number of posts to publish in one batch
            
        Returns:
            List of publish results
        """
        try:
            if not self.db_client:
                logger.exception("Database client not set")
                return []
            
            # Get approved posts
            posts_response = self._get_db_client().table('posts').select('*').eq(
                'tenant_id', tenant_id
            ).eq('status', PostStatus.APPROVED.value).limit(max_posts).execute()
            
            if not posts_response.data:
                logger.info("No approved posts found to publish")
                return []
            
            posts = posts_response.data
            logger.info(f"Found {len(posts)} approved posts to publish")
            
            results = []
            for post in posts:
                try:
                    # Determine post mode for backwards compatibility
                    post_content = post.get('content', {})
                    has_text = bool(post_content.get('text', '').strip()) if isinstance(post_content, dict) else bool(str(post_content).strip())
                    has_media = bool(post_content.get('media_ids')) if isinstance(post_content, dict) else False
                    
                    if has_text and has_media:
                        post_mode = "text_with_images"
                    elif has_text and not has_media:
                        post_mode = "text"
                    elif not has_text and has_media:
                        post_mode = "image"
                    else:
                        post_mode = None
                    
                    result = await self.publish_post(
                        post_id=post['id'],
                        title=post['title'],
                        content=post['content']['text'] if isinstance(post['content'], dict) else str(post['content']),
                        tenant_id=tenant_id,
                        user_id=user_id,
                        post_mode=post_mode
                    )
                    results.append(result)
                    
                    # Add small delay between publishes
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.exception(f"Failed to publish post {post['id']}: {e}")
                    results.append({
                        "post_id": post['id'],
                        "success": False,
                        "error": str(e)
                    })
            
            return results
            
        except Exception as e:
            logger.exception(f"Error publishing approved posts: {e}")
            return []


# Convenience function for quick publishing
async def publish_post_simple(
    post_id: str,
    title: str,
    content: str,
    channels: List[str] = None,
    publish_text: bool = True,
    publish_image: bool = True,
    db_client = None
) -> Dict[str, Any]:
    """
    Simple function to publish a post with basic configuration
    
    Args:
        post_id: Post ID to publish
        title: Post title
        content: Post content
        channels: List of channels to publish to (default: facebook, whatsapp)
        publish_text: Whether to publish text content
        publish_image: Whether to publish image content
        db_client: Database client for status updates
        
    Returns:
        Publish results
    """
    config = PublishConfig(
        channels=channels,
        publish_text=publish_text,
        publish_image=publish_image
    )
    
    service = PublishService(config)
    if db_client:
        service.set_db_client(db_client)
    
    return await service.publish_post(post_id, title, content)
