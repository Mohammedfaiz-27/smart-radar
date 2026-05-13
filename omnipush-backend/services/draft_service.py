#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Draft Service for Post Approval Workflow
Handles creation, retrieval, approval, and rejection of LLM-generated content drafts
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from core.database import get_database, SupabaseClient
from core.logging_config import get_logger
from services.content_adaptation_service import ContentAdaptation, BatchAdaptationResult
from services.social_posting_service import SocialPostingService

logger = get_logger(__name__)


class DraftService:
    """Service for managing post drafts in the approval workflow"""

    def __init__(self, db_client: SupabaseClient = None):
        self.db = db_client or get_database()
        self.social_posting_service = SocialPostingService()

    def _get_db_client(self):
        """Get the appropriate database client (service_client if wrapper, or raw client)"""
        if hasattr(self.db, 'service_client'):
            return self.db.service_client
        elif hasattr(self.db, 'client'):
            return self.db.client
        return self.db

    async def create_drafts_from_adaptations(
        self,
        adaptations: List[ContentAdaptation],
        social_account_id_map: Dict[str, str],  # Maps channel_id to actual social_account_id
        tenant_id: UUID,
        user_id: UUID,
        external_news_id: Optional[UUID] = None,
        post_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
        """
        Create draft records from LLM content adaptations

        Args:
            adaptations: List of ContentAdaptation objects from LLM
            social_account_id_map: Maps channel_id to social_account_id
            tenant_id: Tenant ID
            user_id: User who initiated the generation
            external_news_id: Optional link to external_news_items
            post_id: Optional link to posts table
            metadata: Additional metadata to store

        Returns:
            Tuple of (success, created_drafts, error_message)
        """
        try:
            if not adaptations:
                return (False, [], "No adaptations provided")

            if not external_news_id and not post_id:
                return (False, [], "Either external_news_id or post_id must be provided")

            db_client = self._get_db_client()
            created_drafts = []

            for adaptation in adaptations:
                # Skip failed adaptations
                if not adaptation.success:
                    logger.warning(f"Skipping failed adaptation for channel {adaptation.channel_id}: {adaptation.error_message}")
                    continue

                # Get social account ID (use mapping if available, otherwise use channel_id directly)
                social_account_id = social_account_id_map.get(adaptation.channel_id, adaptation.channel_id)

                # Prepare draft data
                draft_data = {
                    'tenant_id': str(tenant_id),
                    'user_id': str(user_id),
                    'social_account_id': str(social_account_id),
                    'external_news_id': str(external_news_id) if external_news_id else None,
                    'post_id': str(post_id) if post_id else None,
                    # LLM-generated content (immutable)
                    'generated_content': adaptation.adapted_content,
                    'generated_headline': adaptation.headline,
                    'generated_district': None,  # Set by caller if needed
                    'generated_hashtags': adaptation.hashtags or [],
                    # User-editable content (defaults to generated)
                    'final_content': adaptation.adapted_content,
                    'final_headline': adaptation.headline,
                    'final_district': None,  # Set by caller if needed
                    'final_hashtags': adaptation.hashtags or [],
                    'status': 'PENDING_REVIEW',
                    'metadata': metadata or {}
                }

                # Insert into database
                result = db_client.table('post_drafts').insert(draft_data).execute()

                if result.data:
                    created_drafts.append(result.data[0])
                    logger.info(f"Created draft {result.data[0]['id']} for social account {social_account_id}")
                else:
                    logger.error(f"Failed to create draft for channel {adaptation.channel_id}")

            if created_drafts:
                logger.info(f"Successfully created {len(created_drafts)} drafts for review")
                return (True, created_drafts, None)
            else:
                return (False, [], "Failed to create any drafts")

        except Exception as e:
            logger.exception(f"Error creating drafts from adaptations: {e}")
            return (False, [], str(e))

    async def get_pending_drafts(
        self,
        tenant_id: UUID,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
        external_news_id: Optional[UUID] = None,
        post_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Fetch pending drafts with pagination

        Args:
            tenant_id: Tenant ID
            page: Page number (1-indexed)
            limit: Items per page
            status: Filter by status (defaults to PENDING_REVIEW)
            external_news_id: Filter by external news
            post_id: Filter by post

        Returns:
            Dictionary with items and pagination info
        """
        try:
            db_client = self._get_db_client()

            # Build query
            query = db_client.table('post_drafts').select(
                '''
                *,
                social_accounts:social_account_id (
                    id, platform, account_name, content_tone
                ),
                external_news_items:external_news_id (
                    id, title, external_source, images
                ),
                posts:post_id (
                    id, title, content
                ),
                users:user_id (
                    id, first_name, last_name, email
                )
                ''',
                count='exact'
            ).eq('tenant_id', str(tenant_id))

            # Apply filters
            if status:
                query = query.eq('status', status)
            else:
                query = query.eq('status', 'PENDING_REVIEW')

            if external_news_id:
                query = query.eq('external_news_id', str(external_news_id))

            if post_id:
                query = query.eq('post_id', str(post_id))

            # Pagination
            offset = (page - 1) * limit
            query = query.order('created_at', desc=True).range(offset, offset + limit - 1)

            # Execute query
            result = query.execute()

            total_count = result.count if hasattr(result, 'count') else 0
            total_pages = (total_count + limit - 1) // limit if total_count else 0

            return {
                'items': result.data or [],
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total_count': total_count,
                    'total_pages': total_pages
                }
            }

        except Exception as e:
            logger.exception(f"Error fetching pending drafts: {e}")
            return {
                'items': [],
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total_count': 0,
                    'total_pages': 0
                }
            }

    async def get_draft_by_id(
        self,
        draft_id: UUID,
        tenant_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single draft by ID

        Args:
            draft_id: Draft ID
            tenant_id: Tenant ID (for security)

        Returns:
            Draft data or None
        """
        try:
            db_client = self._get_db_client()

            result = db_client.table('post_drafts').select(
                '''
                *,
                social_accounts:social_account_id (
                    id, platform, account_name, content_tone
                ),
                external_news_items:external_news_id (
                    id, title, content, external_source, images
                ),
                posts:post_id (
                    id, title, content
                ),
                users:user_id (
                    id, first_name, last_name, email
                )
                '''
            ).eq('id', str(draft_id)).eq('tenant_id', str(tenant_id)).maybe_single().execute()

            return result.data if result.data else None

        except Exception as e:
            logger.exception(f"Error fetching draft {draft_id}: {e}")
            return None

    async def approve_draft(
        self,
        draft_id: UUID,
        tenant_id: UUID,
        approved_by: UUID,
        final_content: Optional[str] = None,
        final_headline: Optional[str] = None,
        final_district: Optional[str] = None,
        final_hashtags: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Approve a draft and update final_* fields

        Args:
            draft_id: Draft ID
            tenant_id: Tenant ID (for security)
            approved_by: User ID who approved
            final_content: Optional edited content
            final_headline: Optional edited headline
            final_district: Optional edited district
            final_hashtags: Optional edited hashtags

        Returns:
            Tuple of (success, updated_draft, error_message)
        """
        try:
            db_client = self._get_db_client()

            # Fetch current draft
            current_draft = await self.get_draft_by_id(draft_id, tenant_id)
            if not current_draft:
                return (False, None, "Draft not found")

            # Check if already approved or rejected
            if current_draft['status'] != 'PENDING_REVIEW':
                return (False, None, f"Draft already {current_draft['status']}")

            # Prepare update data
            update_data = {
                'status': 'APPROVED',
                'approved_by': str(approved_by),
                'approved_at': datetime.utcnow().isoformat()
            }

            # Update final_* fields if provided
            if final_content is not None:
                update_data['final_content'] = final_content
            if final_headline is not None:
                update_data['final_headline'] = final_headline
            if final_district is not None:
                update_data['final_district'] = final_district
            if final_hashtags is not None:
                update_data['final_hashtags'] = final_hashtags

            # Update in database
            result = db_client.table('post_drafts').update(update_data).eq('id', str(draft_id)).eq('tenant_id', str(tenant_id)).execute()

            if result.data:
                logger.info(f"Draft {draft_id} approved by user {approved_by}")
                return (True, result.data[0], None)
            else:
                return (False, None, "Failed to update draft")

        except Exception as e:
            logger.exception(f"Error approving draft {draft_id}: {e}")
            return (False, None, str(e))

    async def update_draft(
        self,
        draft_id: UUID,
        tenant_id: UUID,
        final_content: Optional[str] = None,
        final_headline: Optional[str] = None,
        final_district: Optional[str] = None,
        final_hashtags: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Update draft content without changing status

        Args:
            draft_id: Draft ID
            tenant_id: Tenant ID
            final_content: Updated content (optional)
            final_headline: Updated headline (optional)
            final_district: Updated district (optional)
            final_hashtags: Updated hashtags (optional)

        Returns:
            Tuple of (success, updated_draft, error_message)
        """
        try:
            db_client = self._get_db_client()

            # Fetch current draft
            current_draft = await self.get_draft_by_id(draft_id, tenant_id)
            if not current_draft:
                return (False, None, "Draft not found")

            # Prepare update data (only update fields, don't change status)
            update_data = {}

            # Update final_* fields if provided
            if final_content is not None:
                update_data['final_content'] = final_content
            if final_headline is not None:
                update_data['final_headline'] = final_headline
            if final_district is not None:
                update_data['final_district'] = final_district
            if final_hashtags is not None:
                update_data['final_hashtags'] = final_hashtags

            # Update in database
            result = db_client.table('post_drafts').update(update_data).eq('id', str(draft_id)).eq('tenant_id', str(tenant_id)).execute()

            if result.data:
                logger.info(f"Draft {draft_id} updated successfully")
                return (True, result.data[0], None)
            else:
                return (False, None, "Failed to update draft")

        except Exception as e:
            logger.exception(f"Error updating draft {draft_id}: {e}")
            return (False, None, str(e))

    async def _generate_newscard_for_draft(
        self,
        draft: Dict[str, Any],
        tenant_id: UUID
    ) -> Optional[str]:
        """
        Generate newscard for a draft from its original news item or post

        Args:
            draft: Draft data (must include external_news_items or posts)
            tenant_id: Tenant ID

        Returns:
            Newscard URL or None if generation failed
        """
        try:
            # Import newscard and content services
            from services.newscard_template_service import newscard_template_service
            from services.content_service import ContentService

            # Get original content from external_news_items or posts
            news_item = draft.get('external_news_items')
            post = draft.get('posts')

            if not news_item and not post:
                logger.warning(f"No source content found for draft {draft['id']} - cannot generate newscard")
                return None

            # Determine source data
            # IMPORTANT: Prioritize final_headline from draft (Tamil) over original title (English)
            if news_item:
                title = draft.get('final_headline') or news_item.get('title', 'News Update')
                content = draft.get('final_content', news_item.get('content', ''))
                images = news_item.get('images', [])
                source_url = news_item.get('url')
            else:
                title = draft.get('final_headline') or post.get('title', 'Post')
                content = draft.get('final_content', post.get('content', ''))
                images = post.get('content', {}).get('images', []) if isinstance(post.get('content'), dict) else []
                source_url = None

            # Get image URL from source
            image_url = None
            if images:
                if isinstance(images, list) and len(images) > 0:
                    image_url = images[0] if isinstance(images[0], str) else images[0].get('url')
                elif isinstance(images, dict):
                    # Try to get original_url first, then thumbnail_url, then url
                    image_url = images.get('original_url') or images.get('thumbnail_url') or images.get('url')

            # Get social account for template selection
            social_account = draft.get('social_accounts', {})
            account_id = social_account.get('id')
            platform = social_account.get('platform', 'facebook').lower()

            # Get district for newscard
            district = draft.get('final_district', '')

            # Get database client for template assignment lookup
            db_client = self._get_db_client()

            # Generate newscard HTML
            newscard_html = await newscard_template_service.generate_newscard_html_async(
                content=content,
                tenant_id=str(tenant_id),
                channel_id=account_id,
                channel_name=social_account.get('account_name', 'News Channel'),
                image_url=image_url,
                headline=title,
                district=district,
                db_client=db_client
            )

            if not newscard_html:
                logger.error("Failed to generate newscard HTML")
                return None

            # Convert HTML to image and upload to S3
            content_service = ContentService()
            screenshot_result = await content_service.generate_screenshot(
                html_content=newscard_html,
                tenant_id=str(tenant_id)
            )

            newscard_url = screenshot_result.get('url')

            if newscard_url:
                logger.info(f"Newscard generated and uploaded to S3 for draft {draft['id']}: {newscard_url}")
                return newscard_url
            else:
                logger.error("Screenshot generation did not return URL")
                return None

        except Exception as e:
            logger.exception(f"Error generating newscard for draft: {e}")
            return None

    async def reject_draft(
        self,
        draft_id: UUID,
        tenant_id: UUID,
        rejected_by: UUID,
        rejection_reason: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Reject a draft

        Args:
            draft_id: Draft ID
            tenant_id: Tenant ID (for security)
            rejected_by: User ID who rejected
            rejection_reason: Optional reason for rejection

        Returns:
            Tuple of (success, updated_draft, error_message)
        """
        try:
            db_client = self._get_db_client()

            # Fetch current draft
            current_draft = await self.get_draft_by_id(draft_id, tenant_id)
            if not current_draft:
                return (False, None, "Draft not found")

            # Check if already approved or rejected
            if current_draft['status'] != 'PENDING_REVIEW':
                return (False, None, f"Draft already {current_draft['status']}")

            # Prepare update data
            update_data = {
                'status': 'REJECTED',
                'rejected_by': str(rejected_by),
                'rejected_at': datetime.utcnow().isoformat(),
                'rejection_reason': rejection_reason
            }

            # Update in database
            result = db_client.table('post_drafts').update(update_data).eq('id', str(draft_id)).eq('tenant_id', str(tenant_id)).execute()

            if result.data:
                logger.info(f"Draft {draft_id} rejected by user {rejected_by}")
                return (True, result.data[0], None)
            else:
                return (False, None, "Failed to update draft")

        except Exception as e:
            logger.exception(f"Error rejecting draft {draft_id}: {e}")
            return (False, None, str(e))

    async def publish_approved_draft(
        self,
        draft_id: UUID,
        tenant_id: UUID,
        newscard_url: Optional[str] = None,
        auto_approve: bool = True
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Publish an approved draft to social media

        This function handles the complete publishing workflow:
        1. Auto-approve if needed (PENDING_REVIEW -> APPROVED)
        2. Generate newscard from original news item/post
        3. Publish to social media platform
        4. Update draft status to PUBLISHED/FAILED

        Args:
            draft_id: Draft ID
            tenant_id: Tenant ID
            newscard_url: Optional newscard image URL (if not provided, will generate)
            auto_approve: Auto-approve PENDING_REVIEW drafts (default: True)

        Returns:
            Tuple of (success, publish_result, error_message)
        """
        try:
            # Fetch draft
            draft = await self.get_draft_by_id(draft_id, tenant_id)
            if not draft:
                return (False, None, "Draft not found")

            # Auto-approve if PENDING_REVIEW
            if draft['status'] == 'PENDING_REVIEW' and auto_approve:
                logger.info(f"Auto-approving draft {draft_id} for publishing")
                db_client = self._get_db_client()
                db_client.table('post_drafts').update({
                    'status': 'APPROVED',
                    'approved_at': datetime.utcnow().isoformat()
                }).eq('id', str(draft_id)).execute()
                draft['status'] = 'APPROVED'
            elif draft['status'] not in ['PENDING_REVIEW', 'APPROVED']:
                return (False, None, f"Draft cannot be published (current status: {draft['status']})")

            # Get social account info
            social_account = draft.get('social_accounts')
            if not social_account:
                return (False, None, "Social account not found for draft")

            # Generate newscard if not provided
            if not newscard_url:
                newscard_url = await self._generate_newscard_for_draft(draft, tenant_id)
                if newscard_url:
                    logger.info(f"Generated newscard for draft {draft_id}: {newscard_url}")

            # Prepare content for publishing
            content = draft['final_content']

            # Add headline if present
            if draft.get('final_headline'):
                content = f"{draft['final_headline']}\n\n{content}"

            # Add hashtags if present
            if draft.get('final_hashtags'):
                hashtags_str = ' '.join(draft['final_hashtags'])
                content = f"{content}\n\n{hashtags_str}"

            # Determine media type if newscard_url provided
            media_type = "IMAGE" if newscard_url else None

            # Publish using social posting service
            try:
                response = self.social_posting_service.post_to_account(
                    account_id=social_account['id'],
                    tenant_id=str(tenant_id),
                    content=content,
                    media_url=newscard_url,
                    media_type=media_type
                )

                # Update draft with publish results
                db_client = self._get_db_client()
                update_data = {
                    'status': 'PUBLISHED' if not response.error else 'FAILED',
                    'published_at': datetime.utcnow().isoformat() if not response.error else None,
                    'publish_result': {
                        'platform': response.platform,
                        'post_id': response.post_id,
                        'message': response.message,
                        'error': response.error
                    },
                    'error_message': response.error
                }

                db_client.table('post_drafts').update(update_data).eq('id', str(draft_id)).execute()

                if response.error:
                    logger.error(f"Failed to publish draft {draft_id}: {response.error}")
                    return (False, update_data['publish_result'], response.error)
                else:
                    logger.info(f"Successfully published draft {draft_id} to {response.platform}")

                    # Update posts table for tracking in Posts module
                    await self._update_posts_table_from_draft(draft, update_data['publish_result'], tenant_id)

                    return (True, update_data['publish_result'], None)

            except Exception as publish_error:
                logger.exception(f"Error during social media publishing: {publish_error}")

                # Mark as FAILED
                db_client = self._get_db_client()
                db_client.table('post_drafts').update({
                    'status': 'FAILED',
                    'error_message': str(publish_error)
                }).eq('id', str(draft_id)).execute()

                return (False, None, str(publish_error))

        except Exception as e:
            logger.exception(f"Error publishing approved draft {draft_id}: {e}")
            return (False, None, str(e))

    async def _update_posts_table_from_draft(
        self,
        draft: Dict[str, Any],
        publish_result: Dict[str, Any],
        tenant_id: UUID
    ) -> None:
        """
        Create or update posts table entry after draft publishing

        Groups all drafts by external_news_id or post_id and aggregates
        publish results to show in Posts module

        Args:
            draft: Draft data with source info
            publish_result: Publishing result for this specific account
            tenant_id: Tenant ID
        """
        try:
            db_client = self._get_db_client()

            # Determine source ID
            external_news_id = draft.get('external_news_id')
            post_id = draft.get('post_id')

            if not external_news_id and not post_id:
                logger.warning("Draft has no external_news_id or post_id - cannot update posts table")
                return

            # Find existing post record for this source
            if external_news_id:
                # Check if post exists for this news item
                existing_post = db_client.table('posts')\
                    .select('id, publish_results')\
                    .eq('tenant_id', str(tenant_id))\
                    .eq('metadata->>external_news_id', str(external_news_id))\
                    .execute()
            else:
                # Post_id is the actual post record
                existing_post = db_client.table('posts')\
                    .select('id, publish_results')\
                    .eq('id', str(post_id))\
                    .eq('tenant_id', str(tenant_id))\
                    .execute()

            # Prepare publish result entry for this account
            account_result = {
                'account_id': draft.get('social_account_id'),
                'platform': publish_result.get('platform'),
                'post_id': publish_result.get('post_id'),
                'message': publish_result.get('message'),
                'error': publish_result.get('error'),
                'published_at': datetime.utcnow().isoformat()
            }

            if existing_post.data and len(existing_post.data) > 0:
                # Update existing post record
                post_record = existing_post.data[0]
                existing_results = post_record.get('publish_results', {})

                # Get existing results array or create new one
                results_array = existing_results.get('results', [])
                results_array.append(account_result)

                # Calculate stats
                success_count = sum(1 for r in results_array if not r.get('error'))
                total_count = len(results_array)

                updated_publish_results = {
                    'results': results_array,
                    'total_accounts': total_count,
                    'success_count': success_count,
                    'failure_count': total_count - success_count
                }

                # Update post record
                update_data = {
                    'publish_results': updated_publish_results,
                    'status': 'published' if success_count > 0 else 'failed',
                    'published_at': datetime.utcnow().isoformat() if success_count > 0 else None
                }

                db_client.table('posts')\
                    .update(update_data)\
                    .eq('id', post_record['id'])\
                    .execute()

                logger.info(f"Updated existing post record {post_record['id']} with draft publish result")

            else:
                # Create new post record for news item
                news_item = draft.get('external_news_items')

                if not news_item and not post_id:
                    logger.warning("Cannot create post record - no source data")
                    return

                post_data = {
                    'tenant_id': str(tenant_id),
                    'user_id': draft.get('user_id'),
                    'created_by': draft.get('user_id'),
                    'title': draft.get('final_headline') or (news_item.get('title') if news_item else 'Published Post'),
                    'content': {
                        'text': draft.get('final_content'),
                        'headline': draft.get('final_headline'),
                        'district': draft.get('final_district'),
                        'hashtags': draft.get('final_hashtags', []),
                        'generated_by_ai': True
                    },
                    'metadata': {
                        'external_news_id': str(external_news_id) if external_news_id else None,
                        'published_from_draft': True,
                        'draft_id': draft.get('id')
                    },
                    'publish_results': {
                        'results': [account_result],
                        'total_accounts': 1,
                        'success_count': 1 if not publish_result.get('error') else 0,
                        'failure_count': 1 if publish_result.get('error') else 0
                    },
                    'status': 'published' if not publish_result.get('error') else 'failed',
                    'published_at': datetime.utcnow().isoformat() if not publish_result.get('error') else None
                }

                result = db_client.table('posts').insert(post_data).execute()

                if result.data:
                    logger.info(f"Created new post record for external_news_id {external_news_id}")
                else:
                    logger.error("Failed to create post record")

        except Exception as e:
            logger.exception(f"Error updating posts table from draft: {e}")
            # Don't fail the publish operation if posts table update fails

    async def get_draft_stats(
        self,
        tenant_id: UUID,
        external_news_id: Optional[UUID] = None,
        post_id: Optional[UUID] = None
    ) -> Dict[str, int]:
        """
        Get count of drafts by status

        Args:
            tenant_id: Tenant ID
            external_news_id: Optional filter by external news
            post_id: Optional filter by post

        Returns:
            Dictionary with counts by status
        """
        try:
            db_client = self._get_db_client()

            # Build base query
            query = db_client.table('post_drafts').select('status', count='exact').eq('tenant_id', str(tenant_id))

            if external_news_id:
                query = query.eq('external_news_id', str(external_news_id))

            if post_id:
                query = query.eq('post_id', str(post_id))

            # Get all drafts
            result = query.execute()

            # Count by status
            stats = {
                'all': 0,
                'PENDING_REVIEW': 0,
                'APPROVED': 0,
                'REJECTED': 0,
                'PUBLISHED': 0,
                'FAILED': 0
            }

            if result.data:
                stats['all'] = len(result.data)
                for item in result.data:
                    status = item.get('status')
                    if status in stats:
                        stats[status] += 1

            return stats

        except Exception as e:
            logger.exception(f"Error fetching draft stats: {e}")
            return {
                'all': 0,
                'PENDING_REVIEW': 0,
                'APPROVED': 0,
                'REJECTED': 0,
                'PUBLISHED': 0,
                'FAILED': 0
            }


# Singleton instance
_draft_service_instance = None


def get_draft_service() -> DraftService:
    """Get the singleton draft service instance"""
    global _draft_service_instance
    if _draft_service_instance is None:
        _draft_service_instance = DraftService()
    return _draft_service_instance
