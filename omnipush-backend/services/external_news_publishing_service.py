"""
External News Publishing Service
Handles publishing external news items to social channels with content adaptation
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime

from core.database import get_database
from services.content_adaptation_service import ContentAdaptationService, ChannelConfig, ContentAdaptation
from services.social_posting_service import SocialPostingService
from services.newscard_template_service import NewscardTemplateService
from services.social_template_assignment_service import SocialTemplateAssignmentService
from services.content_service import ContentService
from services.draft_service import get_draft_service
from utils.tamil_text_cleaner import safe_clean_tamil_content, safe_truncate_tamil

logger = logging.getLogger(__name__)


class ExternalNewsPublishingService:
    """Service for publishing external news to social channels with content adaptation"""

    def __init__(self):
        self.db = get_database()
        self.content_adaptation_service = ContentAdaptationService()
        self.social_posting_service = SocialPostingService()
        self.newscard_template_service = NewscardTemplateService()
        self.template_assignment_service = SocialTemplateAssignmentService(self.db.client)
        self.content_service = ContentService()

    def _remove_hashtags(self, content: str) -> str:
        """Remove hashtags, user mentions, URLs, and HTML tags from content for newscard generation"""
        if not content:
            return content
        # Remove HTML tags (e.g., <p>, </p>, <br>, etc.)
        cleaned = re.sub(r'<[^>]+>', '', content)
        # Remove hashtags (words starting with #)
        cleaned = re.sub(r'#\w+', '', cleaned)
        # Remove user mentions (@username)
        cleaned = re.sub(r'@\w+', '', cleaned)
        # Remove URLs (t.co links and others)
        cleaned = re.sub(r'https?://t\.co/\w+', '', cleaned)
        cleaned = re.sub(r'https?://\S+', '', cleaned)
        # Clean up extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        # Clean Tamil text encoding issues
        cleaned = safe_clean_tamil_content(cleaned, "newscard_content")
        return cleaned

    def _clean_caption_content(self, content: str, source_name: str = None) -> str:
        """
        Clean caption content for social media posting.
        Removes: platform prefix, duplicate intro, trailing hashtags, user mentions, source links, and HTML tags.
        """
        if not content:
            return content

        cleaned = content

        # Remove HTML tags (e.g., <p>, </p>, <br>, etc.)
        cleaned = re.sub(r'<[^>]+>', '', cleaned)

        # Remove platform prefix (e.g., "Twitter:", "Facebook:", etc.)
        platforms = ['twitter', 'facebook', 'instagram', 'linkedin', 'x']
        for platform in platforms:
            pattern = rf'^{platform}\s*:\s*'
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # Remove duplicate intro text (first line before "..." that repeats)
        # Pattern: "intro text...\n\nintro text full version"
        lines = cleaned.split('\n')
        if len(lines) >= 3:
            first_line = lines[0].strip()
            if first_line.endswith('...'):
                # Check if intro repeats in content
                intro_prefix = first_line.rstrip('.')
                # Find if this intro appears again
                rest_content = '\n'.join(lines[1:]).strip()
                # Use safe truncation for Tamil text
                intro_check = safe_truncate_tamil(intro_prefix, 20, suffix="")
                if rest_content.startswith(intro_check):
                    # Remove the truncated intro line
                    cleaned = rest_content

        # Remove ALL hashtags (both inline and trailing)
        cleaned = re.sub(r'#\w+', '', cleaned)

        # Remove ALL user mentions (@username)
        cleaned = re.sub(r'@\w+', '', cleaned)

        # Remove ALL URLs (t.co links and others, anywhere in text)
        cleaned = re.sub(r'https?://t\.co/\w+', '', cleaned)
        cleaned = re.sub(r'https?://\S+', '', cleaned)

        # Clean up extra whitespace and newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Collapse multiple spaces
        cleaned = cleaned.strip()

        # Clean Tamil text encoding issues
        cleaned = safe_clean_tamil_content(cleaned, "caption_content")

        return cleaned

    async def publish_news_to_channels(
        self,
        news_item: Dict[str, Any],
        channel_group_id: UUID,
        tenant_id: UUID,
        initiated_by: UUID,
        post_id: Optional[UUID] = None,
        selected_language: str = 'en',
        customized_title: Optional[str] = None,
        customized_content: Optional[str] = None,
        create_drafts: bool = True  # NEW: Enable Human-in-the-Loop review workflow
    ) -> Dict[str, Any]:
        """
        Publish external news to all social accounts in a channel group
        OR create drafts for human review (Human-in-the-Loop workflow)

        Args:
            news_item: External news item data
            channel_group_id: Channel group ID to publish to
            tenant_id: Tenant ID
            initiated_by: User ID who initiated publishing
            post_id: Optional Post record ID to track publishing
            selected_language: Language variant to use
            customized_title: Optional custom title
            customized_content: Optional custom content
            create_drafts: If True, creates drafts for review instead of publishing (default: True)

        Returns:
            Dictionary with publication results OR draft creation results
        """
        try:
            logger.info(f"Publishing external news {news_item['id']} to channel group {channel_group_id}")

            # Check if this is a Slack reshare post - use simplified publishing
            is_slack_reshare = news_item.get('external_source') == 'slack'

            if is_slack_reshare:
                logger.info("Detected Slack reshare post - using image-only publishing (no newscard, no content adaptation)")
                return await self._publish_slack_reshare(
                    news_item=news_item,
                    channel_group_id=channel_group_id,
                    tenant_id=tenant_id,
                    post_id=post_id
                )

            # Step 1: Get social accounts from channel group
            social_accounts = await self._get_channel_group_accounts(channel_group_id, tenant_id)

            if not social_accounts:
                return {
                    "success": False,
                    "error": "No social accounts found in channel group",
                    "results": []
                }

            logger.info(f"Found {len(social_accounts)} social accounts in channel group")

            # Step 2: Prepare base content
            base_content = await self._prepare_base_content(
                news_item,
                selected_language,
                customized_title,
                customized_content
            )

            # Check if news item has image (affects content length for newscard)
            has_image = bool(news_item.get('images'))

            # Step 3: Extract district/city from news_item (Tamil name preferred) - used for newscard template
            district = None
            if news_item.get('city_data'):
                city_data = news_item['city_data']
                district = (
                    city_data.get('multilingual_names', {}).get('ta') or
                    city_data.get('multilingual_names', {}).get('en') or
                    city_data.get('name')
                )
                if district:
                    logger.info(f"Using district from NewsIt data: {district}")

            # Step 4: Get channel configurations for content adaptation
            channel_configs = await self._get_channel_configs(social_accounts, tenant_id, has_image)

            # Step 5: Adapt content for ALL channels in a single LLM call (multi-page news)
            # This replaces the old tone-based grouping approach with a consolidated single call
            adapted_content_map, extracted_district = await self._adapt_content_multi_page_consolidated(
                base_content,
                channel_configs,
                district
            )

            # Use extracted district if we didn't have one from NewsIt
            if not district and extracted_district:
                district = extracted_district
                logger.info(f"Using LLM-extracted district: {district}")

            # Fallback to தமிழ்நாடு if no district found
            if not district:
                district = "தமிழ்நாடு"
                logger.info("No district found, using fallback: தமிழ்நாடு")

            # **NEW: Human-in-the-Loop Review Workflow**
            # Step 6: Create drafts for review (if enabled)
            if create_drafts:
                logger.info("Creating drafts for human review instead of publishing directly")
                return await self._create_drafts_for_review(
                    news_item=news_item,
                    adapted_content_map=adapted_content_map,
                    social_accounts=social_accounts,
                    channel_configs=channel_configs,
                    tenant_id=tenant_id,
                    initiated_by=initiated_by,
                    district=district
                )

            # Step 7: Publish to each social account (legacy direct publishing)
            publication_results = await self._publish_to_accounts(
                social_accounts,
                channel_configs,
                adapted_content_map,
                news_item.get('images', {}),
                tenant_id,
                news_item,
                customized_title,
                district
            )

            # Step 8: Aggregate results
            success_count = sum(1 for r in publication_results if r['success'])

            result_data = {
                "success": success_count > 0,
                "total_accounts": len(social_accounts),
                "success_count": success_count,
                "failure_count": len(social_accounts) - success_count,
                "results": publication_results,
                "multi_page_llm_call": True,  # Indicates single consolidated LLM call
                "adaptations_generated": len(adapted_content_map)
            }

            # Step 8: Update Post record if post_id provided
            if post_id:
                try:
                    post_status = 'published' if success_count > 0 else 'failed'
                    post_update_data = {
                        'status': post_status,
                        'publish_results': {
                            'results': publication_results,
                            'total_accounts': len(social_accounts),
                            'success_count': success_count,
                            'failure_count': len(social_accounts) - success_count
                        }
                    }

                    if success_count > 0:
                        post_update_data['published_at'] = datetime.utcnow().isoformat()

                    self.db.client.table('posts')\
                        .update(post_update_data)\
                        .eq('id', str(post_id))\
                        .execute()

                    logger.info(f"Updated Post {post_id} with status: {post_status}")

                except Exception as post_update_error:
                    logger.error(f"Failed to update Post {post_id}: {post_update_error}")

            return result_data

        except Exception as e:
            logger.error(f"Error publishing external news: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    async def _create_drafts_for_review(
        self,
        news_item: Dict[str, Any],
        adapted_content_map: Dict[str, Dict[str, Any]],
        social_accounts: List[Dict[str, Any]],
        channel_configs: List[ChannelConfig],
        tenant_id: UUID,
        initiated_by: UUID,
        district: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create draft records for human review (Human-in-the-Loop workflow)

        Args:
            news_item: External news item data
            adapted_content_map: Map of channel_id -> {content, headline, hashtags}
            social_accounts: List of social account data
            channel_configs: List of channel configurations
            tenant_id: Tenant ID
            initiated_by: User ID who initiated
            district: Extracted district name

        Returns:
            Dictionary with draft creation results
        """
        try:
            draft_service = get_draft_service()
            draft_service.db = self.db

            # Convert adapted_content_map to ContentAdaptation objects
            adaptations = []
            for channel_id, adaptation_data in adapted_content_map.items():
                adaptation = ContentAdaptation(
                    channel_id=channel_id,
                    adapted_content=adaptation_data.get('content', ''),
                    hashtags=adaptation_data.get('hashtags', []),
                    headline=adaptation_data.get('headline'),
                    success=True
                )
                adaptations.append(adaptation)

            # Create social_account_id_map (channel_id -> social_account_id)
            # In this case, channel_id IS the social_account_id
            social_account_id_map = {acc['id']: acc['id'] for acc in social_accounts}

            # Create drafts
            success, created_drafts, error_msg = await draft_service.create_drafts_from_adaptations(
                adaptations=adaptations,
                social_account_id_map=social_account_id_map,
                tenant_id=tenant_id,
                user_id=initiated_by,
                external_news_id=UUID(news_item['id']),
                post_id=None,
                metadata={
                    'district': district,
                    'news_title': news_item.get('title'),
                    'external_source': news_item.get('external_source')
                }
            )

            # Update district in created drafts if provided (bulk update)
            if success and district and created_drafts:
                db_client = self.db.client if hasattr(self.db, 'client') else self.db
                draft_ids = [draft['id'] for draft in created_drafts]

                # Perform bulk update for all drafts at once
                if draft_ids:
                    db_client.table('post_drafts').update({
                        'generated_district': district,
                        'final_district': district
                    }).in_('id', draft_ids).execute()

            if success:
                logger.info(f"Successfully created {len(created_drafts)} drafts for review")
                return {
                    "success": True,
                    "draft_mode": True,
                    "total_drafts": len(created_drafts),
                    "drafts": created_drafts,
                    "message": f"Created {len(created_drafts)} drafts for review. Please review and approve in the Post Review tab."
                }
            else:
                logger.error(f"Failed to create drafts: {error_msg}")
                return {
                    "success": False,
                    "draft_mode": True,
                    "error": error_msg,
                    "drafts": []
                }

        except Exception as e:
            logger.exception(f"Error creating drafts for review: {e}")
            return {
                "success": False,
                "draft_mode": True,
                "error": str(e),
                "drafts": []
            }

    async def _publish_slack_reshare(
        self,
        news_item: Dict[str, Any],
        channel_group_id: UUID,
        tenant_id: UUID,
        post_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Simplified publishing for Slack reshare posts
        Posts ONLY the image without any text, newscard generation, or content adaptation

        Args:
            news_item: External news item data (from Slack)
            channel_group_id: Channel group ID to publish to
            tenant_id: Tenant ID
            post_id: Optional Post record ID to track publishing

        Returns:
            Dictionary with publication results
        """
        try:
            logger.info(f"Publishing Slack reshare post {news_item['id']} (image-only)")

            # Step 1: Get social accounts from channel group
            social_accounts = await self._get_channel_group_accounts(channel_group_id, tenant_id)

            if not social_accounts:
                return {
                    "success": False,
                    "error": "No social accounts found in channel group",
                    "results": []
                }

            logger.info(f"Found {len(social_accounts)} social accounts in channel group")

            # Step 2: Get image URL from news item
            images = news_item.get('images', {})
            image_url = (
                images.get('original_url') or
                images.get('low_res_url') or
                images.get('thumbnail_url')
            )

            if not image_url:
                logger.error("No image URL found in Slack reshare post")
                return {
                    "success": False,
                    "error": "No image URL found in reshare post",
                    "results": []
                }

            logger.info(f"Using image URL: {image_url}")

            # Step 3: Publish to each social account (image only, no text)
            publication_results = []

            for account in social_accounts:
                account_id = account['id']

                try:
                    logger.info(f"Publishing image-only to account {account_id} ({account['platform']})")

                    # Publish using SocialPostingService - image only, empty caption
                    response = self.social_posting_service.post_to_account(
                        account_id=account_id,
                        tenant_id=account['tenant_id'],
                        content="",  # Empty content - image only as per PRD
                        media_url=image_url,
                        media_type="IMAGE"
                    )

                    result = {
                        "account_id": account_id,
                        "account_name": account.get('account_name', 'Unknown'),
                        "platform": response.platform,
                        "success": not response.error,
                        "post_id": response.post_id,
                        "message": response.message,
                        "error": response.error,
                        "published_at": datetime.utcnow().isoformat() if not response.error else None,
                        "is_slack_reshare": True,
                        "image_url": image_url
                    }

                    publication_results.append(result)

                    if not response.error:
                        logger.info(f"✓ Successfully published image to {account['platform']} ({account.get('account_name')})")
                    else:
                        logger.warning(f"✗ Failed to publish to {account['platform']}: {response.error}")

                except Exception as e:
                    logger.error(f"Error publishing to account {account_id}: {e}")
                    publication_results.append({
                        "account_id": account_id,
                        "account_name": account.get('account_name', 'Unknown'),
                        "platform": account['platform'],
                        "success": False,
                        "error": f"Exception: {str(e)}",
                        "is_slack_reshare": True
                    })

            # Step 4: Aggregate results
            success_count = sum(1 for r in publication_results if r['success'])

            result_data = {
                "success": success_count > 0,
                "total_accounts": len(social_accounts),
                "success_count": success_count,
                "failure_count": len(social_accounts) - success_count,
                "results": publication_results,
                "publishing_mode": "slack_reshare_image_only"
            }

            # Step 5: Update Post record if post_id provided
            if post_id:
                try:
                    post_status = 'published' if success_count > 0 else 'failed'
                    post_update_data = {
                        'status': post_status,
                        'publish_results': {
                            'results': publication_results,
                            'total_accounts': len(social_accounts),
                            'success_count': success_count,
                            'failure_count': len(social_accounts) - success_count,
                            'publishing_mode': 'slack_reshare_image_only'
                        }
                    }

                    if success_count > 0:
                        post_update_data['published_at'] = datetime.utcnow().isoformat()

                    self.db.client.table('posts')\
                        .update(post_update_data)\
                        .eq('id', str(post_id))\
                        .execute()

                    logger.info(f"Updated Post {post_id} with status: {post_status}")

                except Exception as post_update_error:
                    logger.error(f"Failed to update Post {post_id}: {post_update_error}")

            logger.info(
                f"Slack reshare publishing complete: {success_count}/{len(social_accounts)} successful"
            )

            return result_data

        except Exception as e:
            logger.error(f"Error publishing Slack reshare post: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    async def _get_channel_group_accounts(
        self,
        channel_group_id: UUID,
        tenant_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get all social accounts in a channel group"""
        try:
            # Get channel group with account IDs
            group_result = self.db.client.table('channel_groups')\
                .select('social_account_ids')\
                .eq('id', str(channel_group_id))\
                .eq('tenant_id', str(tenant_id))\
                .single()\
                .execute()

            if not group_result.data:
                logger.warning(f"Channel group {channel_group_id} not found")
                return []

            account_ids = group_result.data.get('social_account_ids', [])
            if not account_ids:
                logger.warning(f"Channel group {channel_group_id} has no social accounts")
                return []

            logger.info(f"Channel group has {len(account_ids)} account IDs")

            # Get social account details
            accounts_result = self.db.client.table('social_accounts')\
                .select('id, tenant_id, platform, account_name, account_id, content_tone, custom_instructions')\
                .in_('id', account_ids)\
                .eq('tenant_id', str(tenant_id))\
                .execute()

            accounts = accounts_result.data or []
            logger.info(f"Retrieved {len(accounts)} accounts from channel group")

            return accounts

        except Exception as e:
            logger.error(f"Error getting channel group accounts: {e}")
            return []

    async def _prepare_base_content(
        self,
        news_item: Dict[str, Any],
        selected_language: str,
        customized_title: Optional[str],
        customized_content: Optional[str]
    ) -> str:
        """Prepare base content from news item"""

        # Use custom content if provided
        if customized_content:
            return customized_content

        # Try to get language-specific content
        if selected_language != 'en' and news_item.get('multilingual_data'):
            lang_data = news_item['multilingual_data'].get(selected_language, {})
            if lang_data.get('content'):
                return lang_data['content']

        # Fallback to default content
        title = customized_title or news_item.get('title', '')
        content = news_item.get('content', '')

        # Combine title and content
        base_content = f"{title}\n\n{content}" if title else content

        # Clean Tamil text encoding issues
        base_content = safe_clean_tamil_content(base_content, "base_content")

        return base_content

    async def _get_channel_configs(
        self,
        social_accounts: List[Dict[str, Any]],
        tenant_id: UUID,
        has_image: bool = False
    ) -> List[ChannelConfig]:
        """Get channel configurations for content adaptation"""

        channel_configs = []

        for account in social_accounts:
            config = ChannelConfig(
                id=account['id'],
                platform=account['platform'],
                account_name=account.get('account_name', 'Unknown'),
                content_tone=account.get('content_tone', 'professional'),
                custom_instructions=account.get('custom_instructions'),
                has_image=has_image
            )
            channel_configs.append(config)

        logger.info(f"Created {len(channel_configs)} channel configurations (has_image={has_image})")
        return channel_configs

    def _group_channels_by_tone(
        self,
        channel_configs: List[ChannelConfig]
    ) -> Dict[str, List[ChannelConfig]]:
        """Group channels by content tone for efficient adaptation"""

        tone_groups = {}

        for config in channel_configs:
            # Create a key combining tone and custom instructions
            tone_key = f"{config.content_tone}::{config.custom_instructions or 'none'}"

            if tone_key not in tone_groups:
                tone_groups[tone_key] = []

            tone_groups[tone_key].append(config)

        logger.info(f"Grouped {len(channel_configs)} channels into {len(tone_groups)} tone groups")

        # Log group details
        for tone_key, configs in tone_groups.items():
            logger.info(f"  Tone group '{tone_key}': {len(configs)} channel(s)")

        return tone_groups

    async def _adapt_content_by_tone(
        self,
        base_content: str,
        tone_groups: Dict[str, List[ChannelConfig]],
        district: Optional[str] = None
    ) -> Tuple[Dict[str, str], Optional[str]]:
        """
        Adapt content for each unique tone
        Returns tuple of (mapping of channel_id -> adapted_content, extracted district)
        """

        adapted_content_map = {}
        extracted_district = None
        is_first_tone = True

        for tone_key, configs in tone_groups.items():
            try:
                # Use the first config in the group as representative
                representative_config = configs[0]

                logger.info(f"Adapting content for tone group: {tone_key}")

                # Extract district only in first tone group if not already available
                should_extract_district = is_first_tone and not district

                # Adapt content using ContentAdaptationService
                batch_results, district_from_llm = await self.content_adaptation_service.adapt_content_batch(
                    original_content=base_content,
                    channels=[representative_config],
                    max_batch_size=1,
                    extract_district=should_extract_district
                )

                # Capture district from first tone group
                if should_extract_district and district_from_llm:
                    extracted_district = district_from_llm
                    logger.info(f"District extracted in first tone group: {extracted_district}")

                is_first_tone = False

                if batch_results and batch_results[0].adaptations:
                    adaptation = batch_results[0].adaptations[0]

                    if adaptation.success:
                        adapted_text = adaptation.adapted_content
                        logger.info(f"Successfully adapted content for tone '{tone_key}'")

                        # Map the adapted content to ALL channels with this tone
                        for config in configs:
                            adapted_content_map[config.id] = adapted_text
                    else:
                        logger.warning(f"Failed to adapt content for tone '{tone_key}': {adaptation.error_message}")
                        # Use original content as fallback
                        for config in configs:
                            adapted_content_map[config.id] = base_content
                else:
                    logger.warning(f"No adaptation result for tone '{tone_key}', using original content")
                    for config in configs:
                        adapted_content_map[config.id] = base_content

            except Exception as e:
                logger.error(f"Error adapting content for tone '{tone_key}': {e}")
                # Use original content as fallback
                for config in configs:
                    adapted_content_map[config.id] = base_content

        logger.info(f"Content adaptation complete: {len(adapted_content_map)} channel(s) mapped")
        return (adapted_content_map, extracted_district)

    async def _adapt_content_multi_page_consolidated(
        self,
        base_content: str,
        channel_configs: List[ChannelConfig],
        district: Optional[str] = None,
        batch_size: int = 20
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Adapt content for ALL channels using multi-page news prompt in batches.
        This is the new consolidated approach that replaces tone-based grouping.

        Args:
            base_content: The original news content
            channel_configs: List of all channel configurations
            district: Optional pre-extracted district name
            batch_size: Number of accounts per LLM call (default: 20)

        Returns:
            Tuple of (mapping of channel_id -> adaptation data, extracted district)
        """
        adapted_content_map = {}
        extracted_district = None

        try:
            if not channel_configs:
                logger.warning("No channel configurations provided")
                return ({}, None)

            num_batches = (len(channel_configs) + batch_size - 1) // batch_size
            logger.info(f"Adapting content for {len(channel_configs)} channels using multi-page news ({num_batches} batch(es) of up to {batch_size})")

            # IMPORTANT: District extraction is CONTENT-ORIENTED, not account-oriented
            # It answers: "What district is this news about?" (e.g., பொன்னேரி, சென்னை)
            # This is extracted ONCE from the content in the first batch,
            # not separately for each account. All accounts get the same district
            # because they're all publishing the same news content.
            should_extract_district = district is None

            # Call the new multi-page news adaptation method (batched LLM calls)
            batch_results, district_from_llm = await self.content_adaptation_service.adapt_content_multi_page_news(
                original_content=base_content,
                channels=channel_configs,
                include_headline=True,  # Generate headlines for newscard
                extract_district=should_extract_district,
                batch_size=batch_size
            )

            # Capture extracted district
            if should_extract_district and district_from_llm:
                extracted_district = district_from_llm
                logger.info(f"District extracted from LLM: {extracted_district}")

            # Process adaptations from all batches
            if batch_results:
                for batch_result in batch_results:
                    if batch_result.adaptations:
                        for adaptation in batch_result.adaptations:
                            if adaptation.success:
                                # Store full adaptation data (content, headline, hashtags)
                                adapted_content_map[adaptation.channel_id] = {
                                    'content': adaptation.adapted_content,
                                    'headline': adaptation.headline,
                                    'hashtags': adaptation.hashtags
                                }
                                logger.debug(f"✓ Channel {adaptation.channel_id}: adapted successfully")
                            else:
                                # Use original content as fallback
                                adapted_content_map[adaptation.channel_id] = {
                                    'content': base_content,
                                    'headline': None,
                                    'hashtags': []
                                }
                                logger.warning(f"✗ Channel {adaptation.channel_id}: {adaptation.error_message}, using original")

            # Fallback for any channels not in results
            if len(adapted_content_map) < len(channel_configs):
                logger.warning("Some channels missing from adaptation results, using original content")
                for config in channel_configs:
                    if config.id not in adapted_content_map:
                        adapted_content_map[config.id] = {
                            'content': base_content,
                            'headline': None,
                            'hashtags': []
                        }

        except Exception as e:
            logger.error(f"Error in multi-page content adaptation: {e}", exc_info=True)
            # Fallback: use original content for all channels
            for config in channel_configs:
                adapted_content_map[config.id] = {
                    'content': base_content,
                    'headline': None,
                    'hashtags': []
                }

        logger.info(f"Multi-page content adaptation complete: {len(adapted_content_map)} channel(s) processed")
        return (adapted_content_map, extracted_district)

    async def _generate_newscard_for_account(
        self,
        account: Dict[str, Any],
        content: str,
        news_item: Dict[str, Any],
        tenant_id: UUID,
        customized_title: Optional[str] = None,
        district: Optional[str] = None,
        headline: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate newscard for a social account

        Args:
            account: Social account data
            content: Adapted content for this account (without tags)
            news_item: External news item with images, category, etc.
            tenant_id: Tenant ID
            customized_title: Optional custom title
            district: District/city name for newscard template
            headline: LLM-generated headline from multi-page news response (30-50 chars)

        Returns:
            Newscard image URL if successful, None otherwise
        """
        try:
            account_id = account['id']
            account_name = account.get('account_name', 'Channel')

            # Check if news item has image
            has_image = bool(news_item.get('images'))
            original_image_url = None

            if has_image:
                images = news_item['images']
                original_image_url = (
                    images.get('original_url') or
                    images.get('low_res_url') or
                    images.get('thumbnail_url')
                )

            logger.info(f"Generating newscard for account {account_id} (has_image={has_image})")

            # Get template assignment for this account
            template_name = None
            try:
                assignments = await self.template_assignment_service.get_template_assignments(
                    tenant_id=str(tenant_id),
                    social_account_id=account_id
                )

                if assignments:
                    assignment = assignments[0]
                    # Choose template based on image availability
                    if has_image and assignment.template_with_image:
                        template_name = assignment.template_with_image
                        logger.info(f"Using template with image: {template_name}")
                    elif not has_image and assignment.template_without_image:
                        template_name = assignment.template_without_image
                        logger.info(f"Using template without image: {template_name}")
                    else:
                        logger.warning(f"No appropriate template in assignment for has_image={has_image}")
                else:
                    logger.info(f"No template assignment for account {account_id}, will use rotation")

            except Exception as e:
                logger.warning(f"Error getting template assignment: {e}, will use rotation")

            # Determine headline priority:
            # 1. LLM-generated headline from multi-page news (HIGHEST PRIORITY - already optimized)
            # 2. Customized title from user input
            # 3. Generate with separate LLM call (FALLBACK ONLY - for backward compatibility)

            final_headline = None

            if headline and headline.strip():
                # ALWAYS prefer headline from multi-page news LLM response (already optimized for Tamil news)
                final_headline = headline.strip()
                logger.info(f"✓ Using LLM-generated headline from multi-page news: {final_headline}")
            elif customized_title and customized_title.strip():
                # Fallback to customized title from publish popup
                final_headline = customized_title.strip()
                logger.info(f"Using customized title as headline: {final_headline}")
            else:
                # Final fallback: generate headline using separate LLM call (backward compatibility)
                logger.warning("No headline from multi-page news or customized title, generating with separate LLM call")
                try:
                    logger.info("Generating headline using LLM")
                    from services.llm_service import llm_service, LLMProfile
                    from utils.tamil_text_cleaner import has_orphaned_tamil_marks

                    # Use safe truncation to avoid splitting Tamil characters
                    content_preview = safe_truncate_tamil(content, 500, suffix="...")

#                     # System message with Tamil generation rules
#                     tamil_system_msg = """You are a Tamil language expert. Follow these CRITICAL rules:

# TAMIL TEXT STRUCTURE:
# - Tamil words MUST start with consonants: க, ச, ட, த, ப, ம, ய, ர, ல, வ, ழ, ள, ற, ன, ந
# - Vowel signs (ா, ி, ீ, ு, ூ, ெ, ே, ை, ொ, ோ, ௌ) come AFTER consonants
# - NEVER start any word with a vowel sign

# ✅ CORRECT Tamil:
# - பொன்னேரி (consonant ப + vowel sign ொ)
# - மாநகராட்சி (consonant ம + vowel sign ா)
# - செயல்திறன் (consonant ச + vowel sign ெ)

# ❌ INCORRECT - NEVER generate:
# - ொன்னேரி (orphaned vowel sign)
# - ாநகராட்சி (orphaned vowel sign)
# - ெயல்திறன் (orphaned vowel sign)

# VALIDATE: Before responding, check EVERY Tamil word starts with a consonant."""

                    headline_user_prompt = f"""Generate a compelling headline for this news content in Tamil.

Content: {content_preview}

Requirements:
- Maximum 50 characters
- Attention-grabbing and concise
- Tamil language (தமிழ்)
- Captures the essence of the news

Respond with ONLY the headline text, no explanation."""

                    # Try up to 3 times to get valid Tamil
                    max_retries = 1
                    for attempt in range(max_retries):
                        final_headline = await llm_service.generate(
                            messages=[
                                # {"role": "system", "content": tamil_system_msg},
                                {"role": "user", "content": headline_user_prompt}
                            ],
                            profile=LLMProfile.DEFAULT,
                            temperature=0.7,
                            max_tokens=100,
                            service_name="newscard_headline_generation"
                        )

                        final_headline = final_headline.strip()
                        # Clean Tamil text in LLM-generated headline
                        final_headline = safe_clean_tamil_content(final_headline, "llm_generated_headline")

                        # Check if headline has corruption
                        if has_orphaned_tamil_marks(final_headline):
                            logger.warning(f"LLM generated corrupted Tamil headline (attempt {attempt + 1}/{max_retries}): {final_headline}")
                            if attempt < max_retries - 1:
                                logger.info("Retrying headline generation...")
                                continue
                            else:
                                logger.error("Max retries reached, using corrupted headline")
                        else:
                            logger.info(f"✓ Generated valid Tamil headline: {final_headline}")
                            break

                    # Truncate to 50 chars if needed (using safe truncation for Tamil)
                    if len(final_headline) > 50:
                        final_headline = safe_truncate_tamil(final_headline, 50, suffix="")

                    logger.info(f"Generated fallback headline: {final_headline}")

                except Exception as e:
                    logger.warning(f"Failed to generate headline using LLM: {e}, will skip headline")
                    final_headline = None

            # District is passed from caller (extracted from NewsIt or from LLM during content adaptation)

            # Generate newscard HTML (remove hashtags for cleaner newscard)
            try:
                newscard_content = self._remove_hashtags(content)
                newscard_html = await self.newscard_template_service.generate_newscard_html_async(
                    content=newscard_content,
                    tenant_id=str(tenant_id),
                    channel_id=account_id,
                    channel_name=account_name,
                    category=news_item.get('category', 'News'),
                    template_name=template_name,  # None will use rotation
                    image_url=original_image_url,
                    db_client=self.db.client,
                    headline=final_headline,  # Use final_headline (priority: multi-page LLM > customized > fallback LLM)
                    district=district
                )

                logger.info(f"Generated newscard HTML for account {account_id}")

            except Exception as e:
                logger.error(f"Failed to generate newscard HTML: {e}")
                return None

            # Convert HTML to image and upload to S3
            try:
                screenshot_result = await self.content_service.generate_screenshot(
                    html_content=newscard_html,
                    tenant_id=str(tenant_id)
                )

                newscard_url = screenshot_result.get('url')

                if newscard_url:
                    logger.info(f"✓ Newscard generated and uploaded for account {account_id}: {newscard_url}")
                    return newscard_url
                else:
                    logger.error(f"Screenshot generation did not return URL")
                    return None

            except Exception as e:
                logger.error(f"Failed to convert newscard HTML to image: {e}")
                return None

        except Exception as e:
            logger.error(f"Error generating newscard for account {account['id']}: {e}", exc_info=True)
            return None

    async def _publish_to_accounts(
        self,
        social_accounts: List[Dict[str, Any]],
        channel_configs: List[ChannelConfig],
        adapted_content_map: Dict[str, Any],  # Changed from Dict[str, str] to Dict[str, Any]
        images: Dict[str, Any],
        tenant_id: UUID,
        news_item: Dict[str, Any],
        customized_title: Optional[str] = None,
        district: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Publish adapted content to social accounts with newscard generation.

        The adapted_content_map now contains full adaptation data:
        {channel_id: {'content': str, 'headline': str, 'hashtags': List[str]}}

        IMPORTANT:
        - Newscard uses content WITHOUT tags (clean content only)
        - Social media caption includes content WITH tags appended
        """

        results = []

        # Determine original media URL (as fallback)
        original_media_url = None
        if images:
            original_media_url = (
                images.get('original_url') or
                images.get('low_res_url') or
                images.get('thumbnail_url')
            )

        for account in social_accounts:
            account_id = account['id']

            try:
                # Get adapted content data for this account
                adaptation_data = adapted_content_map.get(account_id)

                if not adaptation_data:
                    logger.warning(f"No adapted content found for account {account_id}, skipping")
                    results.append({
                        "account_id": account_id,
                        "account_name": account.get('account_name', 'Unknown'),
                        "platform": account['platform'],
                        "success": False,
                        "error": "No adapted content available"
                    })
                    continue

                # Extract content, headline, and hashtags
                # Handle both old format (string) and new format (dict) for backward compatibility
                if isinstance(adaptation_data, dict):
                    content = adaptation_data.get('content', '')
                    headline = adaptation_data.get('headline')
                    hashtags = adaptation_data.get('hashtags', [])
                else:
                    # Old format: just a string
                    content = adaptation_data
                    headline = None
                    hashtags = []

                if not content:
                    logger.warning(f"Empty content for account {account_id}, skipping")
                    results.append({
                        "account_id": account_id,
                        "account_name": account.get('account_name', 'Unknown'),
                        "platform": account['platform'],
                        "success": False,
                        "error": "Empty adapted content"
                    })
                    continue

                logger.info(f"Publishing to account {account_id} ({account['platform']})")

                # IMPORTANT: Generate newscard with content WITHOUT tags
                # The newscard should display clean, professional content
                newscard_content = self._remove_hashtags(content)  # Remove any inline hashtags

                newscard_url = await self._generate_newscard_for_account(
                    account=account,
                    content=newscard_content,  # Clean content without tags
                    news_item=news_item,
                    tenant_id=tenant_id,
                    customized_title=customized_title,
                    district=district,
                    headline=headline  # Pass LLM-generated headline from multi-page news (ALWAYS USE THIS)
                )

                # Determine media URL: Use newscard if generated, otherwise use original image
                media_url = newscard_url if newscard_url else original_media_url
                media_type = "IMAGE" if media_url else None

                if newscard_url:
                    logger.info(f"Using newscard for publication: {newscard_url}")
                elif original_media_url:
                    logger.info(f"Newscard generation failed/skipped, using original image")
                else:
                    logger.info(f"No newscard or original image available")

                # Build caption for social media: content + tags
                # Clean the content first (remove platform prefix, duplicate intro, source links)
                caption_content = self._clean_caption_content(content, news_item.get('source_name'))

                # Append hashtags for social media (NOT in newscard)
                if hashtags:
                    # Filter out any duplicate hashtags already in content
                    content_lower = caption_content.lower()
                    unique_tags = [tag for tag in hashtags if tag.lower() not in content_lower]

                    if unique_tags:
                        # Add tags at the end of caption
                        tags_str = ' '.join(unique_tags)
                        caption_content = f"{caption_content}\n\n{tags_str}".strip()
                        logger.info(f"Appended {len(unique_tags)} hashtags to caption")

                # Publish using SocialPostingService
                response = self.social_posting_service.post_to_account(
                    account_id=account_id,
                    tenant_id=account['tenant_id'],
                    content=caption_content,  # Caption includes tags
                    media_url=media_url,
                    media_type=media_type
                )

                # Use safe truncation for preview
                content_preview = safe_truncate_tamil(content, 100) if len(content) > 100 else content

                result = {
                    "account_id": account_id,
                    "account_name": account.get('account_name', 'Unknown'),
                    "platform": response.platform,
                    "success": not response.error,
                    "post_id": response.post_id,
                    "message": response.message,
                    "error": response.error,
                    "published_at": datetime.utcnow().isoformat() if not response.error else None,
                    "adapted_content_preview": content_preview
                }

                results.append(result)

                if not response.error:
                    logger.info(f"✓ Successfully published to {account['platform']} ({account.get('account_name')})")
                else:
                    logger.warning(f"✗ Failed to publish to {account['platform']}: {response.error}")

            except Exception as e:
                logger.error(f"Error publishing to account {account_id}: {e}")
                results.append({
                    "account_id": account_id,
                    "account_name": account.get('account_name', 'Unknown'),
                    "platform": account['platform'],
                    "success": False,
                    "error": f"Exception: {str(e)}"
                })

        success_count = sum(1 for r in results if r['success'])
        logger.info(f"Publishing complete: {success_count}/{len(results)} successful")

        return results


# Singleton instance
_external_news_publishing_service_instance: Optional[ExternalNewsPublishingService] = None


def get_external_news_publishing_service() -> ExternalNewsPublishingService:
    """Get or create external news publishing service singleton instance"""
    global _external_news_publishing_service_instance

    if _external_news_publishing_service_instance is None:
        _external_news_publishing_service_instance = ExternalNewsPublishingService()

    return _external_news_publishing_service_instance
