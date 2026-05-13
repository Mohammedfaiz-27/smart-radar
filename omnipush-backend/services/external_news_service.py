"""
External News Service
Business logic for managing external news items (NewsIt, RSS, etc.)
Handles ingestion, approval workflow, and multi-channel-group publishing
"""

import logging
import re
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
from psycopg2.extras import execute_values

from core.database import get_database
from models.external_news import (
    ExternalNewsItem,
    ExternalNewsItemCreate,
    ExternalNewsPublication,
    ExternalNewsPublicationCreate,
    ApprovalStatus,
    PublicationStatus,
    ProcessingResult
)
from services.newsit_client import get_newsit_client
from services.external_news_publishing_service import get_external_news_publishing_service
from services.llm_service import LLMService, LLMProfile
from services.s3_service import s3_service

logger = logging.getLogger(__name__)


class ExternalNewsService:
    """Service for managing external news items and publications"""

    def __init__(self):
        self.db = get_database()
        self.newsit_client = get_newsit_client()
        self.llm_service = LLMService()

    def _clean_social_content(self, content: str) -> str:
        """
        Clean scraped social media content for publishing.
        Removes: platform prefix, duplicate intro, trailing hashtags, source links.
        """
        if not content:
            return content

        cleaned = content

        # Remove platform prefix (e.g., "Twitter:", "Facebook:", etc.)
        platforms = ['twitter', 'facebook', 'instagram', 'linkedin', 'x']
        for platform in platforms:
            pattern = rf'^{platform}\s*:\s*'
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # Remove duplicate intro text (first line before "..." that repeats)
        lines = cleaned.split('\n')
        if len(lines) >= 3:
            first_line = lines[0].strip()
            if first_line.endswith('...'):
                intro_prefix = first_line.rstrip('.')
                rest_content = '\n'.join(lines[1:]).strip()
                if rest_content and intro_prefix[:20] and rest_content.startswith(intro_prefix[:20]):
                    cleaned = rest_content

        # Remove trailing hashtags
        cleaned = re.sub(r'\n\s*#\w+(\s+#\w+)*\s*$', '', cleaned)

        # Remove inline hashtags
        cleaned = re.sub(r'#\w+', '', cleaned)

        # Remove source URLs (t.co links, etc.)
        cleaned = re.sub(r'https?://t\.co/\w+', '', cleaned)
        cleaned = re.sub(r'https?://\S+$', '', cleaned)

        # Clean up extra whitespace
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        return cleaned

    async def process_newsit_message(
        self,
        message_data: Dict[str, Any],
        tenant_id: UUID,
        sqs_message_id: str
    ) -> ProcessingResult:
        """
        Process SQS message containing NewsIt news_id

        Args:
            message_data: Parsed SQS message body
            tenant_id: Tenant ID for the news item
            sqs_message_id: SQS message ID for deduplication

        Returns:
            ProcessingResult with success status and news_item_id
        """
        try:
            news_id = message_data.get('news_id')
            if not news_id:
                logger.error("Missing news_id in SQS message")
                return ProcessingResult(
                    success=False,
                    error_message="Missing news_id in message"
                )

            logger.info(f"Processing NewsIt message: {news_id} for tenant: {tenant_id}")

            # Check for duplicate by SQS message ID
            existing = self.db.client.table('external_news_items')\
                .select('id, external_id')\
                .eq('sqs_message_id', sqs_message_id)\
                .limit(1)\
                .execute()

            if existing.data:
                logger.info(f"Duplicate SQS message detected: {sqs_message_id}")
                return ProcessingResult(
                    success=True,
                    news_item_id=existing.data[0]['id'],
                    external_id=existing.data[0]['external_id'],
                    is_duplicate=True
                )

            # Check for duplicate by external_id and source
            existing = self.db.client.table('external_news_items')\
                .select('id, external_id')\
                .eq('external_source', 'newsit')\
                .eq('external_id', news_id)\
                .eq('tenant_id', str(tenant_id))\
                .limit(1)\
                .execute()

            if existing.data:
                logger.info(f"News item already exists: {news_id}")
                return ProcessingResult(
                    success=True,
                    news_item_id=existing.data[0]['id'],
                    external_id=existing.data[0]['external_id'],
                    is_duplicate=True
                )

            # Fetch and transform from NewsIt API
            generic_data = await self.newsit_client.fetch_and_transform(
                news_id,
                str(tenant_id)
            )

            if not generic_data:
                logger.info(f"News item {news_id} skipped - empty content or fetch failed")
                return ProcessingResult(
                    success=True,
                    error_message=f"News item skipped due to empty content: {news_id}",
                    external_id=news_id,
                    is_duplicate=False
                )

            # Add SQS message ID for deduplication
            generic_data['sqs_message_id'] = sqs_message_id

            # Insert into database
            result = self.db.client.table('external_news_items')\
                .insert(generic_data)\
                .execute()

            if result.data:
                news_item_id = result.data[0]['id']
                logger.info(f"Successfully stored news item: {news_item_id}")
                return ProcessingResult(
                    success=True,
                    news_item_id=news_item_id,
                    external_id=news_id,
                    is_duplicate=False
                )
            else:
                return ProcessingResult(
                    success=False,
                    error_message="Failed to insert news item into database",
                    external_id=news_id
                )

        except Exception as e:
            logger.error(f"Error processing NewsIt message: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                error_message=str(e),
                external_id=message_data.get('news_id')
            )

    async def _extract_district_with_llm(self, text: str) -> Dict[str, Any]:
        """
        Extract district/city from text using LLM

        Args:
            text: Text content to analyze

        Returns:
            Dictionary with city_data structure or default TamilNadu
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for district extraction, using default")
                return {
                    "name": "தமிழ்நாடு",
                    "multilingual_names": {
                        "ta": "தமிழ்நாடு",
                        "en": "TamilNadu"
                    }
                }

            # Use LLM to extract district
            llm_client = self.llm_service.get_client(profile=LLMProfile.PRECISE)

            if not llm_client:
                logger.warning("LLM service not available, using default")
                return {
                    "name": "தமிழ்நாடு",
                    "multilingual_names": {
                        "ta": "தமிழ்நாடு",
                        "en": "TamilNadu"
                    }
                }

            prompt = f"""Analyze the following news text and extract the district/city name mentioned in it.
The news is primarily about Tamil Nadu districts.

Text: {text}

Rules:
1. If you find a specific district or city name (like Chennai, Coimbatore, Salem, etc.), return ONLY that district name
2. If no specific district/city is mentioned, return "TamilNadu"
3. Return ONLY the district/city name in English, nothing else
4. Do not include any explanation or additional text
5. If you find multiple districts, return the most prominent one

District/City:"""

            response = await llm_client.ainvoke(prompt)
            district_en = response.content.strip()

            # Clean up the response
            district_en = district_en.replace('"', '').replace("'", '').strip()

            # If LLM returns empty or invalid response, use default
            if not district_en or len(district_en) > 50:
                logger.warning(f"Invalid LLM response: '{district_en}', using default")
                return {
                    "name": "தமிழ்நாடு",
                    "multilingual_names": {
                        "ta": "தமிழ்நாடு",
                        "en": "TamilNadu"
                    }
                }

            # Map to Tamil name (simple mapping for common districts)
            district_tamil_map = {
                "Chennai": "சென்னை",
                "Coimbatore": "கோவை",
                "Madurai": "மதுரை",
                "Salem": "சேலம்",
                "Tiruchirappalli": "திருச்சி",
                "Trichy": "திருச்சி",
                "Tirunelveli": "திருநெல்வேலி",
                "Tiruppur": "திருப்பூர்",
                "Erode": "ஈரோடு",
                "Vellore": "வேலூர்",
                "Thoothukudi": "தூத்துக்குடி",
                "Tuticorin": "தூத்துக்குடி",
                "Dindigul": "திண்டுக்கல்",
                "Thanjavur": "தஞ்சாவூர்",
                "Kancheepuram": "காஞ்சிபுரம்",
                "Karur": "கரூர்",
                "Ramanathapuram": "ராமநாதபுரம்",
                "Cuddalore": "கடலூர்",
                "Villupuram": "விழுப்புரம்",
                "Sivaganga": "சிவகங்கை",
                "Virudhunagar": "விருதுநகர்",
                "Nagapattinam": "நாகப்பட்டினம்",
                "Namakkal": "நாமக்கல்",
                "Dharmapuri": "தர்மபுரி",
                "Krishnagiri": "கிருஷ்ணகிரி",
                "Pudukkottai": "புதுக்கோட்டை",
                "Ariyalur": "அரியலூர்",
                "Perambalur": "பெரம்பலூர்",
                "Nilgiris": "நீலகிரி",
                "Ooty": "உதகை",
                "Kanyakumari": "கன்னியாகுமரி",
                "Theni": "தேனி",
                "TamilNadu": "தமிழ்நாடு"
            }

            district_ta = district_tamil_map.get(district_en, district_en)

            logger.info(f"Extracted district: {district_en} ({district_ta})")

            return {
                "name": district_ta,
                "multilingual_names": {
                    "ta": district_ta,
                    "en": district_en
                }
            }

        except Exception as e:
            logger.error(f"Error extracting district with LLM: {e}", exc_info=True)
            # Return default on error
            return {
                "name": "தமிழ்நாடு",
                "multilingual_names": {
                    "ta": "தமிழ்நாடு",
                    "en": "TamilNadu"
                }
            }

    async def process_slack_message(
        self,
        message_data: Dict[str, Any],
        tenant_id: UUID,
        sqs_message_id: str
    ) -> ProcessingResult:
        """
        Process SQS message containing Slack bot reshare post

        Args:
            message_data: Parsed SQS message body
            tenant_id: Tenant ID for the news item
            sqs_message_id: SQS message ID for deduplication

        Returns:
            ProcessingResult with success status and news_item_id
        """
        try:
            external_id = message_data.get('_id')
            if not external_id:
                logger.error("Missing _id in Slack message")
                return ProcessingResult(
                    success=False,
                    error_message="Missing _id in message"
                )

            logger.info(f"Processing Slack message: {external_id} for tenant: {tenant_id}")

            # Check for duplicate by SQS message ID
            existing = self.db.client.table('external_news_items')\
                .select('id, external_id')\
                .eq('sqs_message_id', sqs_message_id)\
                .limit(1)\
                .execute()

            if existing.data:
                logger.info(f"Duplicate SQS message detected: {sqs_message_id}")
                return ProcessingResult(
                    success=True,
                    news_item_id=existing.data[0]['id'],
                    external_id=existing.data[0]['external_id'],
                    is_duplicate=True
                )

            # Check for duplicate by external_id and source
            existing = self.db.client.table('external_news_items')\
                .select('id, external_id')\
                .eq('external_source', 'slack')\
                .eq('external_id', external_id)\
                .eq('tenant_id', str(tenant_id))\
                .limit(1)\
                .execute()

            if existing.data:
                logger.info(f"Slack post already exists: {external_id}")
                return ProcessingResult(
                    success=True,
                    news_item_id=existing.data[0]['id'],
                    external_id=existing.data[0]['external_id'],
                    is_duplicate=True
                )

            # Extract data from Slack message
            attachments = message_data.get('attachments', [])
            if not attachments:
                logger.warning(f"No attachments in Slack message: {external_id}")
                return ProcessingResult(
                    success=False,
                    error_message="No attachments in message",
                    external_id=external_id
                )

            attachment = attachments[0]

            # Check for image_url
            image_url = attachment.get('image_url')
            if not image_url:
                logger.info(f"Slack message {external_id} has no image_url, skipping")
                return ProcessingResult(
                    success=True,
                    error_message="No image_url in message, skipped",
                    external_id=external_id,
                    is_duplicate=False
                )

            # Extract content
            text_content = attachment.get('text') or attachment.get('pretext') or attachment.get('fallback') or ''
            title = attachment.get('title') or 'Reshare Post'
            original_url = attachment.get('original_url') or attachment.get('from_url') or ''

            # Extract district using LLM
            city_data = await self._extract_district_with_llm(text_content)

            # Upload image to S3
            s3_image_url = image_url  # Fallback to original URL
            s3_result = await s3_service.upload_external_news_image(
                image_url=image_url,
                tenant_id=str(tenant_id),
                external_source='slack',
                external_id=external_id
            )

            if s3_result:
                s3_image_url = s3_result['url']
                logger.info(f"Uploaded Slack image to S3: {s3_image_url}")
            else:
                logger.warning(f"Failed to upload Slack image to S3, using original URL: {image_url}")

            # Prepare news item data
            news_data = {
                'external_source': 'slack',
                'external_id': external_id,
                'tenant_id': str(tenant_id),
                'sqs_message_id': sqs_message_id,
                'title': title[:500] if title else 'Reshare Post',
                'content': text_content or 'Reshare post from Slack',
                'source_url': original_url,
                'source_name': attachment.get('service_name') or 'Slack',
                'images': {
                    'original_url': s3_image_url,
                    'thumbnail_url': s3_image_url  # Use S3 URL
                },
                'city_data': city_data,
                'approval_status': 'pending',
                'is_breaking': False,
                'fetched_at': datetime.utcnow().isoformat(),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }

            # Insert into database
            result = self.db.client.table('external_news_items')\
                .insert(news_data)\
                .execute()

            if result.data:
                news_item_id = result.data[0]['id']
                logger.info(f"Successfully stored Slack post: {news_item_id}")
                return ProcessingResult(
                    success=True,
                    news_item_id=news_item_id,
                    external_id=external_id,
                    is_duplicate=False
                )
            else:
                return ProcessingResult(
                    success=False,
                    error_message="Failed to insert Slack post into database",
                    external_id=external_id
                )

        except Exception as e:
            logger.error(f"Error processing Slack message: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                error_message=str(e),
                external_id=message_data.get('_id')
            )

    async def get_external_news(
        self,
        tenant_id: UUID,
        approval_status: Optional[str] = None,
        external_source: Optional[str] = None,
        is_breaking: Optional[bool] = None,
        district: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        List external news with filters and pagination

        Args:
            tenant_id: Tenant ID
            approval_status: Filter by approval status ('all', 'pending', 'approved', 'rejected')
            external_source: Filter by external source ('newsit', 'rss', etc.)
            is_breaking: Filter by breaking news flag
            district: Filter by district name (searches in city_data.name and multilingual_names)
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Dictionary with items and pagination metadata
        """
        try:
            # Build query
            query = self.db.client.table('external_news_items')\
                .select('*', count='exact')\
                .eq('tenant_id', str(tenant_id))

            # Apply filters
            if approval_status and approval_status != 'all':
                query = query.eq('approval_status', approval_status)

            if external_source:
                query = query.eq('external_source', external_source)

            if is_breaking is not None:
                query = query.eq('is_breaking', is_breaking)

            # District filter: Search in city_data JSONB column
            # Supports searching in name, multilingual_names.en, and multilingual_names.ta
            if district:
                # Use ilike for case-insensitive search on city_data->name
                # We'll use OR filter to check multiple fields
                query = query.or_(
                    f"city_data->>name.ilike.%{district}%,"
                    f"city_data->multilingual_names->>en.ilike.%{district}%,"
                    f"city_data->multilingual_names->>ta.ilike.%{district}%"
                )

            # Order by fetched_at descending
            query = query.order('fetched_at', desc=True)

            # Pagination
            offset = (page - 1) * limit
            query = query.range(offset, offset + limit - 1)

            # Execute
            result = query.execute()

            total_count = result.count if result.count is not None else len(result.data)
            total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

            return {
                "items": result.data,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }

        except Exception as e:
            logger.error(f"Error fetching external news: {e}", exc_info=True)
            raise

    async def get_external_news_by_id(
        self,
        news_id: UUID,
        tenant_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get single external news item by ID
        Checks external_news_items first, then falls back to news_items for Auto Pilot items

        Args:
            news_id: External news item ID
            tenant_id: Tenant ID

        Returns:
            News item dictionary or None
        """
        try:
            # First try external_news_items table
            result = self.db.client.table('external_news_items')\
                .select('*')\
                .eq('id', str(news_id))\
                .eq('tenant_id', str(tenant_id))\
                .limit(1)\
                .execute()

            if result.data:
                return result.data[0]

            # No fallback needed post-migration - all data is in external_news_items
            return None

        except Exception as e:
            logger.error(f"Error fetching news item {news_id}: {e}")
            return None

    async def approve_news(
        self,
        news_id: UUID,
        approved_by: UUID,
        tenant_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Approve external news item

        Updates both external_news_items and news_items tables to keep approval status in sync.
        This is the manual user approval step (after AI moderation).

        Args:
            news_id: External news item ID
            approved_by: User ID who approved
            tenant_id: Tenant ID

        Returns:
            Updated news item or None
        """
        try:
            approval_timestamp = datetime.utcnow().isoformat()

            # Update external_news_items table
            result = self.db.client.table('external_news_items')\
                .update({
                    'approval_status': 'approved',
                    'approved_by': str(approved_by),
                    'approved_at': approval_timestamp,
                    'updated_at': approval_timestamp
                })\
                .eq('id', str(news_id))\
                .eq('tenant_id', str(tenant_id))\
                .execute()

            if result.data:
                logger.info(f"News item {news_id} approved by {approved_by}")
                return result.data[0]
            else:
                logger.warning(f"News item {news_id} not found or not updated")
                return None

        except Exception as e:
            logger.error(f"Error approving news item {news_id}: {e}")
            raise

    async def reject_news(
        self,
        news_id: UUID,
        rejected_by: UUID,
        rejection_reason: str,
        tenant_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Reject external news item

        Updates both external_news_items and news_items tables to keep rejection status in sync.
        This is the manual user rejection step.

        Args:
            news_id: External news item ID
            rejected_by: User ID who rejected
            rejection_reason: Reason for rejection
            tenant_id: Tenant ID

        Returns:
            Updated news item or None
        """
        try:
            rejection_timestamp = datetime.utcnow().isoformat()

            # Update external_news_items table
            result = self.db.client.table('external_news_items')\
                .update({
                    'approval_status': 'rejected',
                    'rejected_by': str(rejected_by),
                    'rejected_at': rejection_timestamp,
                    'rejection_reason': rejection_reason,
                    'updated_at': rejection_timestamp
                })\
                .eq('id', str(news_id))\
                .eq('tenant_id', str(tenant_id))\
                .execute()

            if result.data:
                logger.info(f"News item {news_id} rejected by {rejected_by}")
                return result.data[0]
            else:
                logger.warning(f"News item {news_id} not found or not updated")
                return None

        except Exception as e:
            logger.error(f"Error rejecting news item {news_id}: {e}")
            raise

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

            # Get social account details
            accounts_result = self.db.client.table('social_accounts')\
                .select('id, platform, account_name, account_id, content_tone, custom_instructions')\
                .in_('id', account_ids)\
                .eq('tenant_id', str(tenant_id))\
                .execute()

            return accounts_result.data or []

        except Exception as e:
            logger.error(f"Error getting channel group accounts: {e}")
            return []

    async def publish_to_channel_groups(
        self,
        news_id: UUID,
        channel_group_ids: List[UUID],
        initiated_by: UUID,
        tenant_id: UUID,
        selected_language: str = 'en',
        customized_title: Optional[str] = None,
        customized_content: Optional[str] = None,
        create_drafts: bool = True
    ) -> Dict[str, Any]:
        """
        Publish approved news to multiple channel groups
        Creates posts, adapts content per channel tone, and publishes

        Args:
            news_id: External news item ID
            channel_group_ids: List of channel group IDs to publish to
            initiated_by: User ID who initiated publishing
            tenant_id: Tenant ID
            selected_language: Language variant to use
            customized_title: Optional customized title
            customized_content: Optional customized content
            create_drafts: If True, creates drafts for review; if False, publishes directly

        Returns:
            Dictionary with success status, publications, and errors
        """
        try:
            # Verify news item is approved
            news_item = await self.get_external_news_by_id(news_id, tenant_id)
            if not news_item:
                return {
                    "success": False,
                    "message": "News item not found",
                    "publications": [],
                    "errors": ["News item not found"]
                }

            if news_item['approval_status'] != 'approved':
                return {
                    "success": False,
                    "message": "News item must be approved before publishing",
                    "publications": [],
                    "errors": ["News item not approved"]
                }

            publications = []
            errors = []
            all_publish_results = []

            # Get publishing service
            publishing_service = get_external_news_publishing_service()

            # Publish to each channel group
            for channel_group_id in channel_group_ids:
                try:
                    # Step 1: Get social accounts from channel group
                    social_accounts = await self._get_channel_group_accounts(channel_group_id, tenant_id)

                    if not social_accounts:
                        errors.append(f"No social accounts found in channel group {channel_group_id}")
                        continue

                    # Step 2: Prepare content for post
                    final_title = customized_title or news_item.get('title', '')
                    final_content = customized_content or news_item.get('content', '')

                    # Clean social media scraped content (removes platform prefix, duplicate intro, hashtags, source links)
                    final_title = self._clean_social_content(final_title)
                    final_content = self._clean_social_content(final_content)

                    # Use multilingual content if available
                    if not customized_content and news_item.get('multilingual_data') and selected_language in news_item['multilingual_data']:
                        lang_content = news_item['multilingual_data'][selected_language]
                        if not customized_title:
                            final_title = lang_content.get('title', final_title)
                        final_content = lang_content.get('content', final_content)

                    # Step 3: Create Post record
                    post_id = str(uuid4())
                    post_content = {
                        "text": final_content,
                        "media_ids": []  # External news uses direct image URLs, not media_ids
                    }

                    # Build channels array for post
                    channels_data = [
                        {
                            "platform": account['platform'],
                            "account_id": account['id'],
                            "account_name": account.get('account_name', '')
                        }
                        for account in social_accounts
                    ]

                    post_data = {
                        'id': post_id,
                        'tenant_id': str(tenant_id),
                        'user_id': str(initiated_by),
                        'title': final_title,
                        'content': post_content,
                        'channels': channels_data,
                        'status': 'publishing',
                        'channel_group_id': str(channel_group_id),
                        'metadata': {
                            'source': 'external_news',
                            'external_source': news_item.get('external_source', 'unknown'),
                            'selected_language': selected_language,
                            'is_breaking': news_item.get('is_breaking', False),
                            'news_item_id': str(news_id),
                            'category': news_item.get('category'),
                            'topics': news_item.get('topics', [])
                        },
                        'created_by': str(initiated_by),
                        'created_at': datetime.utcnow().isoformat()
                    }

                    # Set external_news_id (all items are now in external_news_items)
                    post_data['external_news_id'] = str(news_id)

                    # Insert post
                    post_result = self.db.client.table('posts').insert(post_data).execute()

                    if not post_result.data:
                        errors.append(f"Failed to create post for channel group {channel_group_id}")
                        continue

                    logger.info(f"Created post {post_id} for channel group {channel_group_id}")

                    # Step 4: Create publication record (link to post)
                    pub_data = {
                        'external_news_id': str(news_id),
                        'tenant_id': str(tenant_id),
                        'channel_group_id': str(channel_group_id),
                        'post_id': post_id,  # Link to the post we just created
                        'status': 'publishing',
                        'initiated_by': str(initiated_by),
                        'selected_language': selected_language,
                        'customized_title': customized_title,
                        'customized_content': customized_content
                    }

                    result = self.db.client.table('external_news_publications')\
                        .insert(pub_data)\
                        .execute()

                    if not result.data:
                        errors.append(f"Failed to create publication record for channel group {channel_group_id}")
                        continue

                    publication_record = result.data[0]
                    publication_id = publication_record['id']
                    logger.info(f"Created publication record {publication_id} linked to post {post_id}")

                    # Step 5: Actually publish to social channels with content adaptation
                    publish_result = await publishing_service.publish_news_to_channels(
                        news_item=news_item,
                        channel_group_id=channel_group_id,
                        tenant_id=tenant_id,
                        initiated_by=initiated_by,
                        post_id=UUID(post_id),  # Pass post_id to publishing service
                        selected_language=selected_language,
                        customized_title=customized_title,
                        customized_content=customized_content,
                        create_drafts=create_drafts
                    )

                    # Update publication record with results (only for external_news_items)
                    update_data = {
                        'completed_at': datetime.utcnow().isoformat(),
                        'publish_results': {
                            'results': publish_result.get('results', []),
                            'total_accounts': publish_result.get('total_accounts', 0),
                            'success_count': publish_result.get('success_count', 0),
                            'failure_count': publish_result.get('failure_count', 0),
                            'tone_groups_used': publish_result.get('tone_groups_used', 0),
                            'adaptations_generated': publish_result.get('adaptations_generated', 0)
                        }
                    }

                    # Set final status
                    if publish_result['success']:
                        update_data['status'] = 'published'
                    else:
                        update_data['status'] = 'failed'
                        update_data['error_message'] = publish_result.get('error', 'Publishing failed')

                    # Update the publication record only if it exists (external_news_items)
                    if publication_id:
                        update_result = self.db.client.table('external_news_publications')\
                            .update(update_data)\
                            .eq('id', publication_id)\
                            .execute()
                    else:
                        update_result = None  # No publication record for Auto Pilot items

                    # Update the Post record with publish results
                    post_status = 'published' if publish_result['success'] else 'failed'
                    post_update_data = {
                        'status': post_status,
                        'publish_results': update_data['publish_results'],
                        'published_at': datetime.utcnow().isoformat() if publish_result['success'] else None
                    }

                    post_update_result = self.db.client.table('posts')\
                        .update(post_update_data)\
                        .eq('id', post_id)\
                        .execute()

                    if post_update_result.data:
                        if update_result and update_result.data:
                            # External news item - use actual publication record
                            publications.append(update_result.data[0])
                        else:
                            # Auto Pilot item - create synthetic publication entry from publish results
                            current_time = datetime.utcnow()
                            synthetic_publication = {
                                'id': str(uuid4()),  # Generate placeholder ID
                                'external_news_id': str(news_id),
                                'channel_group_id': channel_group_id,
                                'post_id': post_id,
                                'status': post_status,
                                'publish_results': update_data['publish_results'],
                                'published_at': current_time.isoformat() if publish_result['success'] else None,
                                'tenant_id': str(tenant_id),
                                'initiated_by': str(initiated_by),
                                'initiated_at': current_time.isoformat(),
                                'completed_at': current_time.isoformat() if post_status in ['published', 'failed'] else None,
                                'created_at': current_time.isoformat(),
                                'updated_at': current_time.isoformat(),
                                'selected_language': selected_language,
                                'customized_title': customized_title,
                                'customized_content': customized_content,
                                'error_message': None
                            }
                            publications.append(synthetic_publication)

                        all_publish_results.extend(publish_result.get('results', []))

                        logger.info(
                            f"Published to channel group {channel_group_id}: "
                            f"{publish_result.get('success_count', 0)}/{publish_result.get('total_accounts', 0)} accounts succeeded. "
                            f"Post {post_id} updated with status: {post_status}"
                        )
                    else:
                        if not update_result.data:
                            errors.append(f"Failed to update publication record for channel group {channel_group_id}")
                        if not post_update_result.data:
                            errors.append(f"Failed to update post record {post_id}")

                except Exception as e:
                    logger.error(f"Error publishing to channel group {channel_group_id}: {e}", exc_info=True)
                    errors.append(f"Channel group {channel_group_id}: {str(e)}")

                    # Try to update publication record to failed status
                    try:
                        if 'publication_id' in locals():
                            self.db.client.table('external_news_publications')\
                                .update({
                                    'status': 'failed',
                                    'error_message': str(e),
                                    'completed_at': datetime.utcnow().isoformat()
                                })\
                                .eq('id', publication_id)\
                                .execute()
                    except:
                        pass

            # Summary
            total_success = sum(1 for p in publications if p['status'] == 'published')
            total_accounts_published = sum(
                p.get('publish_results', {}).get('success_count', 0)
                for p in publications
            )

            return {
                "success": total_success > 0,
                "message": f"Published to {total_success}/{len(channel_group_ids)} channel group(s), {total_accounts_published} accounts total",
                "publications": publications,
                "errors": errors if errors else None,
                "detailed_results": all_publish_results
            }

        except Exception as e:
            logger.error(f"Error publishing news to channel groups: {e}", exc_info=True)
            raise

    async def get_publication_history(
        self,
        news_id: UUID,
        tenant_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Get publication history for a news item

        Args:
            news_id: External news item ID
            tenant_id: Tenant ID

        Returns:
            List of publication records
        """
        try:
            result = self.db.client.table('external_news_publications')\
                .select('*')\
                .eq('external_news_id', str(news_id))\
                .eq('tenant_id', str(tenant_id))\
                .order('initiated_at', desc=True)\
                .execute()

            return result.data

        except Exception as e:
            logger.error(f"Error fetching publication history for {news_id}: {e}")
            return []

    async def get_news_status_counts(
        self,
        tenant_id: UUID,
        external_source: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Get count of news items by approval status using count aggregation queries

        Args:
            tenant_id: Tenant ID
            external_source: Optional filter by external source (newsit, twitter, facebook, etc.)

        Returns:
            Dictionary with counts by status
        """
        try:
            # Get total count
            query = self.db.client.table('external_news_items')\
                .select('id', count='exact')\
                .eq('tenant_id', str(tenant_id))

            if external_source:
                query = query.eq('external_source', external_source)

            all_result = query.execute()
            all_count = all_result.count or 0

            # Get pending count
            query = self.db.client.table('external_news_items')\
                .select('id', count='exact')\
                .eq('tenant_id', str(tenant_id))\
                .eq('approval_status', 'pending')

            if external_source:
                query = query.eq('external_source', external_source)

            pending_result = query.execute()
            pending_count = pending_result.count or 0

            # Get approved count
            query = self.db.client.table('external_news_items')\
                .select('id', count='exact')\
                .eq('tenant_id', str(tenant_id))\
                .eq('approval_status', 'approved')

            if external_source:
                query = query.eq('external_source', external_source)

            approved_result = query.execute()
            approved_count = approved_result.count or 0

            # Get rejected count
            query = self.db.client.table('external_news_items')\
                .select('id', count='exact')\
                .eq('tenant_id', str(tenant_id))\
                .eq('approval_status', 'rejected')

            if external_source:
                query = query.eq('external_source', external_source)

            rejected_result = query.execute()
            rejected_count = rejected_result.count or 0

            counts = {
                'all': all_count,
                'pending': pending_count,
                'approved': approved_count,
                'rejected': rejected_count
            }

            logger.info(f"External news status counts: {counts}")
            return counts

        except Exception as e:
            logger.error(f"Error getting status counts: {e}")
            return {'all': 0, 'pending': 0, 'approved': 0, 'rejected': 0}


# Singleton instance
_external_news_service_instance: Optional[ExternalNewsService] = None


def get_external_news_service() -> ExternalNewsService:
    """Get or create external news service singleton instance"""
    global _external_news_service_instance

    if _external_news_service_instance is None:
        _external_news_service_instance = ExternalNewsService()

    return _external_news_service_instance
