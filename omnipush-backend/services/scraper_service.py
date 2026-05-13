import asyncio
import re
from datetime import datetime, timezone, timedelta
import os
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from core.database import SupabaseClient
from core.logging_config import get_logger
from croniter import croniter

from models.scraper_models import (
    ScraperJob, ScraperJobCreate, ScraperJobUpdate,
    ScraperJobRun, ScraperJobRunCreate, ScraperJobRunUpdate,
    ScraperJobWithStats, ScraperJobStatus, SocialAccountResolved
)
from models.content import Platform
from services.news_service import NewsService
from services.publish_service import PublishService, PublishConfig
from services.channel_groups_service import ChannelGroupsService
from services.s3_service import s3_service
from services.social_account_resolver import get_social_account_resolver
from services.scraper_providers import (
    FacebookKeywordProvider,
    FacebookAccountProvider,
    TwitterKeywordProvider,
    TwitterAccountProvider,
    InstagramAccountProvider
)

logger = get_logger(__name__)


class ScraperJobService:
    """Service for managing social media scraper jobs"""
    
    def __init__(self, db_client: SupabaseClient):
        self.db_client = db_client
        self.news_service = NewsService()
        
    async def create_job(self, job_data: ScraperJobCreate, tenant_id: UUID, user_id: UUID) -> ScraperJob:
        """Create a new scraper job"""
        try:
            job_id = str(uuid4())
            
            # Calculate next run time
            next_run_at = self._calculate_next_run(job_data.schedule_cron)
            
            # Extract post_approval_logic from settings if present
            settings_dict = job_data.settings.dict() if job_data.settings else {}
            post_approval_logic = settings_dict.pop('post_approval_logic', None)

            job_dict = {
                'id': job_id,
                'tenant_id': str(tenant_id),
                'name': job_data.name,
                'description': job_data.description,
                'keywords': job_data.keywords,
                'platforms': [p.value for p in job_data.platforms],
                'schedule_cron': job_data.schedule_cron,
                'is_enabled': job_data.is_enabled,
                'settings': settings_dict,
                'post_approval_logic': post_approval_logic,
                'next_run_at': next_run_at.isoformat() if next_run_at else None,
                'created_by': str(user_id),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            response = self.db_client.service_client.table('scraper_jobs').insert(job_dict).execute()

            if not response.data:
                raise Exception("Failed to create scraper job")

            created_job = response.data[0]
            logger.info(f"Created scraper job: {created_job['id']} - {created_job['name']}")

            # Resolve and insert social accounts if provided
            social_accounts = []
            if job_data.social_accounts:
                logger.info(f"Resolving {len(job_data.social_accounts)} social account URLs...")
                social_accounts = await self._resolve_and_insert_social_accounts(
                    job_id=job_id,
                    social_account_inputs=job_data.social_accounts
                )

            # Add social accounts to the job object
            created_job['social_accounts'] = social_accounts

            return ScraperJob(**created_job)
            
        except Exception as e:
            logger.exception(f"Failed to create scraper job: {e}")
            raise
    
    async def update_job(self, job_id: UUID, job_data: ScraperJobUpdate, tenant_id: UUID) -> Optional[ScraperJob]:
        """Update an existing scraper job"""
        try:
            update_dict = {}

            if job_data.name is not None:
                update_dict['name'] = job_data.name
            if job_data.description is not None:
                update_dict['description'] = job_data.description
            if job_data.keywords is not None:
                update_dict['keywords'] = job_data.keywords
            if job_data.platforms is not None:
                update_dict['platforms'] = [p.value for p in job_data.platforms]
            if job_data.schedule_cron is not None:
                update_dict['schedule_cron'] = job_data.schedule_cron
                # Recalculate next run time if schedule changes
                update_dict['next_run_at'] = self._calculate_next_run(job_data.schedule_cron).isoformat()
            if job_data.is_enabled is not None:
                update_dict['is_enabled'] = job_data.is_enabled
                if not job_data.is_enabled:
                    update_dict['next_run_at'] = None  # Clear next run if disabled
                    logger.info(f"Job {job_id} disabled - clearing next_run_at")
                else:
                    # Recalculate next run time when enabling job
                    # Get current job to get its schedule
                    current_job_response = self.db_client.service_client.table('scraper_jobs').select('schedule_cron').eq('id', str(job_id)).execute()
                    if current_job_response.data:
                        schedule_cron = current_job_response.data[0].get('schedule_cron')
                        if schedule_cron:
                            update_dict['next_run_at'] = self._calculate_next_run(schedule_cron).isoformat()
                            logger.info(f"Job {job_id} enabled - next run scheduled at: {update_dict['next_run_at']}")
            if job_data.settings is not None:
                settings_dict = job_data.settings.dict()
                # Extract post_approval_logic from settings if present
                post_approval_logic = settings_dict.pop('post_approval_logic', None)

                update_dict['settings'] = settings_dict
                if post_approval_logic is not None:
                    update_dict['post_approval_logic'] = post_approval_logic

            update_dict['updated_at'] = datetime.now(timezone.utc).isoformat()

            logger.info(f"Updating job {job_id} with data: {update_dict}")

            response = self.db_client.service_client.table('scraper_jobs').update(update_dict).eq('id', str(job_id)).eq('tenant_id', str(tenant_id)).execute()

            if not response.data:
                logger.warning(f"No data returned when updating job {job_id} - job may not exist or tenant mismatch")
                return None

            updated_job = response.data[0]
            logger.info(f"Updated scraper job: {updated_job['id']} - {updated_job['name']} - is_enabled: {updated_job.get('is_enabled')} - next_run_at: {updated_job.get('next_run_at')}")

            # Handle social account updates if provided
            if job_data.social_accounts is not None:
                # Delete existing social accounts
                self.db_client.service_client.table('scraper_job_social_accounts').delete().eq(
                    'scraper_job_id', str(job_id)
                ).execute()

                # Resolve and insert new social accounts
                if job_data.social_accounts:
                    logger.info(f"Updating social accounts: resolving {len(job_data.social_accounts)} account URLs...")
                    social_accounts = await self._resolve_and_insert_social_accounts(
                        job_id=str(job_id),
                        social_account_inputs=job_data.social_accounts
                    )
                    updated_job['social_accounts'] = social_accounts
                else:
                    updated_job['social_accounts'] = []
            else:
                # Load existing social accounts
                updated_job['social_accounts'] = await self._load_social_accounts(str(job_id))

            return ScraperJob(**updated_job)

        except Exception as e:
            logger.exception(f"Failed to update scraper job {job_id}: {e}")
            raise
    
    async def delete_job(self, job_id: UUID, tenant_id: UUID) -> bool:
        """Delete a scraper job"""
        try:
            response = self.db_client.service_client.table('scraper_jobs').delete().eq('id', str(job_id)).eq('tenant_id', str(tenant_id)).execute()
            
            success = bool(response.data)
            if success:
                logger.info(f"Deleted scraper job: {job_id}")
            
            return success
            
        except Exception as e:
            logger.exception(f"Failed to delete scraper job {job_id}: {e}")
            raise
    
    async def get_job(self, job_id: UUID, tenant_id: UUID) -> Optional[ScraperJob]:
        """Get a specific scraper job"""
        try:
            response = self.db_client.service_client.table('scraper_jobs').select('*').eq('id', str(job_id)).eq('tenant_id', str(tenant_id)).execute()

            if not response.data:
                return None

            job_data = response.data[0]

            # Load social accounts for this job
            job_data['social_accounts'] = await self._load_social_accounts(str(job_id))

            return ScraperJob(**job_data)
            
        except Exception as e:
            logger.exception(f"Failed to get scraper job {job_id}: {e}")
            raise
    
    async def list_jobs(self, tenant_id: UUID, page: int = 1, size: int = 20, enabled_only: bool = False) -> Dict[str, Any]:
        """List scraper jobs with statistics"""
        try:
            # Use service client to bypass RLS and manually filter by tenant
            query = self.db_client.service_client.table('scraper_jobs').select('*').eq('tenant_id', str(tenant_id))

            if enabled_only:
                query = query.eq('is_enabled', True)

            # Get total count
            count_response = query.execute()
            total = len(count_response.data)

            # Get paginated results
            offset = (page - 1) * size
            response = query.order('created_at', desc=True).range(offset, offset + size - 1).execute()

            # Get all job IDs for the page to fetch statistics in batch
            job_ids = [job_data['id'] for job_data in response.data]

            # Fetch statistics for all jobs in a single query
            stats_map = await self._get_job_statistics_batch(job_ids) if job_ids else {}

            jobs_with_stats = []
            for job_data in response.data:
                # Load social accounts for this job
                job_data['social_accounts'] = await self._load_social_accounts(job_data['id'])

                job = ScraperJob(**job_data)

                # Get statistics from the batch result
                stats = stats_map.get(str(job.id), {
                    'total_posts_found': 0,
                    'total_posts_processed': 0,
                    'total_posts_approved': 0,
                    'total_posts_published': 0,
                    'avg_posts_per_run': 0.0,
                    'success_rate': 0.0,
                    'last_run_duration': None
                })

                job_with_stats = ScraperJobWithStats(
                    **job.dict(),
                    **stats
                )
                jobs_with_stats.append(job_with_stats)

            return {
                'jobs': jobs_with_stats,
                'total': total,
                'page': page,
                'size': size,
                'has_next': offset + size < total
            }

        except Exception as e:
            logger.exception(f"Failed to list scraper jobs: {e}")
            raise
    
    async def get_jobs_ready_to_run(self) -> List[ScraperJob]:
        """Get all jobs that are ready to run"""
        try:
            now = datetime.now(timezone.utc).isoformat()

            response = self.db_client.service_client.table('scraper_jobs').select('*').eq('is_enabled', True).lte('next_run_at', now).execute()

            jobs = [ScraperJob(**job_data) for job_data in response.data]

            logger.debug(f"Found {len(jobs)} jobs ready to run")
            return jobs

        except Exception as e:
            logger.exception(f"Failed to get jobs ready to run: {e}")
            return []

    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get current status of a specific job (for checking is_enabled)"""
        try:
            response = self.db_client.service_client.table('scraper_jobs').select('id, is_enabled').eq('id', job_id).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]

            return None

        except Exception as e:
            logger.debug(f"Failed to get job status for {job_id}: {e}")
            return None

    async def start_job_run(self, job: ScraperJob) -> ScraperJobRun:
        """Start a new job run"""
        try:
            run_id = str(uuid4())
            
            run_dict = {
                'id': run_id,
                'scraper_job_id': str(job.id),
                'tenant_id': str(job.tenant_id),
                'status': ScraperJobStatus.RUNNING.value,
                'started_at': datetime.now(timezone.utc).isoformat(),
                'posts_found': 0,
                'posts_processed': 0,
                'posts_approved': 0,
                'posts_published': 0,
                'run_log': {},
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            response = self.db_client.service_client.table('scraper_job_runs').insert(run_dict).execute()
            
            if not response.data:
                raise Exception("Failed to create job run")
            
            run_data = response.data[0]
            logger.info(f"Started job run: {run_id} for job {job.name}")
            
            return ScraperJobRun(**run_data)
            
        except Exception as e:
            logger.exception(f"Failed to start job run for {job.id}: {e}")
            raise
    
    async def complete_job_run(self, run: ScraperJobRun, update_data: ScraperJobRunUpdate) -> ScraperJobRun:
        """Complete a job run with results"""
        try:
            update_dict = update_data.dict(exclude_unset=True)
            update_dict['completed_at'] = datetime.now(timezone.utc).isoformat()
            
            if 'duration_seconds' not in update_dict and run.started_at:
                now = datetime.now(timezone.utc)
                if isinstance(run.started_at, str):
                    started_at = datetime.fromisoformat(run.started_at.replace('Z', '+00:00'))
                else:
                    started_at = run.started_at
                    if started_at.tzinfo is None:
                        started_at = started_at.replace(tzinfo=timezone.utc)
                duration = (now - started_at).total_seconds()
                update_dict['duration_seconds'] = int(duration)
            
            response = self.db_client.service_client.table('scraper_job_runs').update(update_dict).eq('id', str(run.id)).execute()
            
            if not response.data:
                raise Exception("Failed to update job run")
            
            updated_run = ScraperJobRun(**response.data[0])
            
            # Update job statistics
            await self._update_job_after_run(run.scraper_job_id, updated_run)
            
            logger.info(f"Completed job run: {run.id} with status {update_data.status}")
            
            return updated_run
            
        except Exception as e:
            logger.exception(f"Failed to complete job run {run.id}: {e}")
            raise
    
    async def execute_scraper_job(self, job: ScraperJob) -> ScraperJobRun:
        """Execute a single scraper job"""
        run = await self.start_job_run(job)

        try:
            logger.info(f"Executing scraper job: {job.name} (ID: {job.id})")
            logger.info(f"Job settings: {job.settings}")
            logger.info(f"Auto-publish setting: {job.settings.get('auto_publish', False)}")
            
            total_posts_found = 0
            total_posts_processed = 0
            total_posts_approved = 0
            total_posts_published = 0
            run_log = {'keywords': job.keywords, 'platforms': job.platforms, 'results': []}

            # Calculate appropriate time range for scraping based on job schedule
            date_range_days = self._calculate_scrape_time_range(job)
            logger.info(f"🕐 Using time range of {date_range_days:.3f} days for this scrape")

            # No need for social_fetch_service - we use direct API calls

            # Process each keyword and platform combination
            # Special handling: Process Newsit platform separately (once, not per keyword)
            newsit_processed = False

            for keyword in job.keywords:
                for platform in job.platforms:
                    try:
                        # Special handling for Newsit platform
                        if platform.lower() == "newsit":
                            # Process Newsit only once (not per keyword)
                            if newsit_processed:
                                logger.info(f"Newsit already processed, skipping for keyword: {keyword}")
                                continue

                            newsit_processed = True
                            logger.info(f"Processing Newsit platform with keywords: {job.keywords}")

                            # Fetch pending Newsit items from external_news_items
                            success, posts = await self._fetch_newsit_posts(
                                keywords=job.keywords,
                                tenant_id=job.tenant_id,
                                max_items=job.settings.get('max_posts_per_run', 10)
                            )
                        else:
                            logger.info(f"Scraping {platform} for keyword: {keyword}")

                            # Fetch social content using direct API calls by keyword
                            success, posts = await self._fetch_platform_content(
                                platform=platform,
                                query=keyword,
                                max_items=job.settings.get('max_posts_per_run', 10),
                                date_range_days=date_range_days
                            )
                        
                        if success:
                            posts_found = len(posts)
                            total_posts_found += posts_found

                            # Convert posts to articles
                            articles = []
                            for post in posts:
                                try:
                                    if platform.lower() == "newsit":
                                        # Convert Newsit items to articles
                                        article = await self._convert_newsit_to_article(post, keyword)
                                    else:
                                        # Convert social media posts to articles
                                        article = await self._convert_post_to_article(post, platform, keyword)
                                    articles.append(article)
                                except Exception as post_error:
                                    logger.exception(f"Error converting post to article: {post_error}")
                                    continue
                            
                            if not articles:
                                logger.warning(f"No articles created from {len(posts)} posts")
                                continue

                            # For Newsit: Skip saving (already in external_news_items)
                            # For other platforms: Save to external_news_items with duplicate checking
                            if platform.lower() == "newsit":
                                logger.info(f"Processing {len(articles)} Newsit items (already in external_news_items)...")
                                new_articles = articles  # All Newsit items are "new" for moderation
                                existing_articles = []
                            else:
                                logger.info(f"Saving {len(articles)} articles to external_news_items...")
                                save_result = await self._save_news_items(articles, job.tenant_id)
                                new_articles = save_result['new_articles']
                                existing_articles = save_result['existing_articles']

                            # Process and moderate articles
                            processed_posts = []
                            if new_articles:
                                for i, article in enumerate(new_articles, 1):
                                    try:
                                        logger.info(f"Moderating article {i}/{len(new_articles)}: {article.title[:50]}...")
                                        # Pass custom approval logic if defined (it's a direct field on the job now)
                                        custom_logic = getattr(job, 'post_approval_logic', None)
                                        processed = await self.news_service.moderate_news_content(article, custom_logic)
                                        processed_posts.append(processed)
                                        
                                        total_posts_processed += 1
                                        status = "✅ Approved" if processed.is_approved else "❌ Rejected"
                                        reason = f" ({processed.moderation_reason})" if processed.moderation_reason else ""
                                        logger.info(f"  {status}{reason}")
                                        
                                        if processed.is_approved:
                                            total_posts_approved += 1
                                        
                                        # Add delay between moderation calls
                                        await asyncio.sleep(1)
                                        
                                    except Exception as post_error:
                                        logger.exception(f"Error moderating article: {post_error}")
                                        continue

                            # Update moderation results and handle platform-specific logic
                            if processed_posts:
                                if platform.lower() == "newsit":
                                    # For Newsit: Update external_news_items approval status and auto-publish
                                    logger.info(f"Updating Newsit approval status for {len(processed_posts)} items...")
                                    for processed in processed_posts:
                                        article = processed.article
                                        external_news_item_id = getattr(article, 'external_news_item_id', None)

                                        if external_news_item_id:
                                            # Check auto_publish setting to determine approval status update strategy
                                            if job.settings.get('auto_publish', False):
                                                # Auto-publish enabled: Update approval status based on AI result
                                                await self._update_newsit_approval_status(
                                                    external_news_item_id,
                                                    processed.is_approved,
                                                    processed.moderation_reason
                                                )

                                                # Auto-publish approved items
                                                if processed.is_approved:
                                                    logger.info(f"📤 Auto-publishing approved Newsit item: {article.title[:50]}...")
                                                    publish_result = await self._auto_publish_newsit_item(processed, job)

                                                    if publish_result.get('success'):
                                                        total_posts_published += 1
                                                        logger.info(f"✅ Successfully auto-published Newsit item")
                                                    else:
                                                        logger.error(f"❌ Failed to auto-publish Newsit item: {publish_result.get('error')}")
                                                else:
                                                    # Rejected by AI - marked as rejected, won't appear in pending list
                                                    logger.info(f"❌ Newsit item rejected by AI: {article.title[:50]}")
                                            else:
                                                # Auto-publish disabled: Manual approval workflow
                                                if processed.is_approved:
                                                    # Keep approval_status='pending' for manual approval in UI
                                                    # But update moderation_reason to store AI feedback
                                                    try:
                                                        moderation_data = {
                                                            'moderation_reason': f"AI Approved: {processed.moderation_reason}" if processed.moderation_reason else "AI Approved",
                                                            'moderated_at': datetime.now(timezone.utc).isoformat()
                                                        }
                                                        self.db_client.service_client.table('external_news_items').update(
                                                            moderation_data
                                                        ).eq('id', external_news_item_id).execute()
                                                    except Exception as e:
                                                        logger.warning(f"Failed to update moderation data: {e}")

                                                    logger.info(f"💾 Newsit item approved by AI, awaiting manual approval: {article.title[:50]}...")
                                                    logger.info(f"   Item remains in 'pending' status for manual review in News Post tab")
                                                    # Item stays with approval_status='pending' and will appear in News Post tab
                                                else:
                                                    # Rejected by AI - update approval_status so it doesn't keep appearing
                                                    await self._update_newsit_approval_status(
                                                        external_news_item_id,
                                                        False,  # rejected
                                                        processed.moderation_reason
                                                    )
                                                    logger.info(f"❌ Newsit item rejected by AI, marked as rejected: {article.title[:50]}")
                                else:
                                    # For other platforms: Update external_news_items with moderation results
                                    logger.info(f"Updating moderation results for {len(processed_posts)} articles...")
                                    await self._update_news_moderation(processed_posts)

                                    # Auto-publish approved social media posts with image validation
                                    published_count = await self._auto_publish_social_posts(processed_posts, job, platform)
                                    total_posts_published += published_count

                            # Log existing articles that were skipped
                            if existing_articles:
                                logger.info(f"⏭️  Skipped processing {len(existing_articles)} duplicate articles")

                            run_log['results'].append({
                                'keyword': keyword,
                                'platform': platform,
                                'posts_found': posts_found,
                                'posts_processed': len(processed_posts),
                                'posts_approved': len([p for p in processed_posts if p.is_approved])
                            })
                            
                        else:
                            logger.warning(f"Failed to fetch content from {platform} for keyword: {keyword}")
                            
                        # Add delay between platform requests
                        await asyncio.sleep(2)
                        
                    except Exception as platform_error:
                        logger.exception(f"Error processing {platform} for {keyword}: {platform_error}")
                        continue

            # ====================================================================================
            # ACCOUNT-BASED SCRAPING (NEW FEATURE)
            # ====================================================================================
            # Load and process social media accounts if configured
            social_accounts = await self._load_social_accounts(str(job.id))
            resolved_accounts = [acc for acc in social_accounts if acc.resolution_status == 'resolved']

            if resolved_accounts:
                logger.info(f"🎯 Starting account-based scraping for {len(resolved_accounts)} social accounts...")

                # Track post IDs to avoid duplicates (between keyword and account scraping)
                seen_post_ids = set()

                for account in resolved_accounts:
                    try:
                        platform = account.platform
                        logger.info(f"Scraping {platform} account: {account.account_name} ({account.account_id})")

                        # Fetch posts from this account
                        success, posts = await self._fetch_account_content(
                            platform=platform,
                            account_id=account.account_id,
                            account_identifier=account.account_identifier,
                            max_items=job.settings.get('max_posts_per_run', 10),
                            date_range_days=date_range_days
                        )

                        if not success or not posts:
                            logger.warning(f"No posts found for {platform} account: {account.account_name}")
                            continue

                        # Filter out duplicates (posts already seen from keyword scraping)
                        original_count = len(posts)
                        posts = [p for p in posts if p.get('id') not in seen_post_ids]
                        duplicates_filtered = original_count - len(posts)

                        if duplicates_filtered > 0:
                            logger.info(f"⏭️ Filtered {duplicates_filtered} duplicate posts (already scraped via keywords)")

                        if not posts:
                            logger.info(f"All posts from {account.account_name} were duplicates, skipping")
                            continue

                        # Add new post IDs to seen set
                        for post in posts:
                            seen_post_ids.add(post.get('id'))

                        posts_found = len(posts)
                        total_posts_found += posts_found

                        # Convert posts to articles (same flow as keyword scraping)
                        articles = []
                        for post in posts:
                            try:
                                article = await self._convert_post_to_article(post, platform, f"account:{account.account_identifier}")
                                articles.append(article)
                            except Exception as post_error:
                                logger.exception(f"Error converting post to article: {post_error}")
                                continue

                        if not articles:
                            logger.warning(f"No articles created from {len(posts)} posts")
                            continue

                        # Save to external_news_items with duplicate checking (same as keyword flow)
                        logger.info(f"Saving {len(articles)} articles from account {account.account_name}...")
                        save_result = await self._save_news_items(articles, job.tenant_id)
                        new_articles = save_result['new_articles']
                        existing_articles = save_result['existing_articles']

                        # Moderate new articles (same flow)
                        processed_posts = []
                        if new_articles:
                            for i, article in enumerate(new_articles, 1):
                                try:
                                    logger.info(f"Moderating article {i}/{len(new_articles)}: {article.title[:50]}...")
                                    custom_logic = getattr(job, 'post_approval_logic', None)
                                    processed = await self.news_service.moderate_news_content(article, custom_logic)
                                    processed_posts.append(processed)

                                    total_posts_processed += 1
                                    status = "✅ Approved" if processed.is_approved else "❌ Rejected"
                                    reason = f" ({processed.moderation_reason})" if processed.moderation_reason else ""
                                    logger.info(f"  {status}{reason}")

                                    if processed.is_approved:
                                        total_posts_approved += 1

                                    await asyncio.sleep(1)  # Delay between moderation calls

                                except Exception as post_error:
                                    logger.exception(f"Error moderating article: {post_error}")
                                    continue

                        # Update moderation results and auto-publish (same flow as keyword scraping)
                        if processed_posts:
                            logger.info(f"Updating moderation results for {len(processed_posts)} articles from account...")
                            await self._update_news_moderation(processed_posts)

                            # Auto-publish approved social media posts with image validation
                            published_count = await self._auto_publish_social_posts(processed_posts, job, platform)
                            total_posts_published += published_count

                        # Log existing articles that were skipped
                        if existing_articles:
                            logger.info(f"⏭️  Skipped processing {len(existing_articles)} duplicate articles")

                        # Add to run log
                        run_log['results'].append({
                            'scraping_mode': 'account',
                            'account': account.account_name or account.account_identifier,
                            'platform': platform,
                            'posts_found': posts_found,
                            'posts_processed': len(processed_posts),
                            'posts_approved': len([p for p in processed_posts if p.is_approved])
                        })

                        # Add delay between account requests
                        await asyncio.sleep(2)

                    except Exception as account_error:
                        logger.exception(f"Error processing account {account.account_identifier}: {account_error}")
                        continue

                logger.info(f"✅ Account-based scraping completed for {len(resolved_accounts)} accounts")
            else:
                logger.debug("No social accounts configured for this job")

            # ====================================================================================
            # END OF ACCOUNT-BASED SCRAPING
            # ====================================================================================

            # Complete the job run successfully
            update_data = ScraperJobRunUpdate(
                status=ScraperJobStatus.COMPLETED,
                posts_found=total_posts_found,
                posts_processed=total_posts_processed,
                posts_approved=total_posts_approved,
                posts_published=total_posts_published,
                run_log=run_log
            )
            
            completed_run = await self.complete_job_run(run, update_data)
            
            logger.info(f"Scraper job completed: {job.name} - Found: {total_posts_found}, "
                       f"Processed: {total_posts_processed}, Approved: {total_posts_approved}, "
                       f"Published: {total_posts_published}")
            
            return completed_run
            
        except Exception as e:
            logger.exception(f"Scraper job failed: {job.name} - {e}")
            
            # Mark job run as failed
            update_data = ScraperJobRunUpdate(
                status=ScraperJobStatus.FAILED,
                error_message=str(e),
                posts_found=total_posts_found,
                posts_processed=total_posts_processed,
                posts_approved=total_posts_approved,
                posts_published=total_posts_published
            )
            
            return await self.complete_job_run(run, update_data)
    
    def _calculate_next_run(self, cron_expression: str) -> datetime:
        """Calculate next run time based on cron expression"""
        try:
            cron = croniter(cron_expression, datetime.now(timezone.utc))
            return cron.get_next(datetime)
        except Exception as e:
            logger.warning(f"Invalid cron expression {cron_expression}: {e}, using 5 minutes")
            return datetime.now(timezone.utc) + timedelta(minutes=5)

    def _calculate_scrape_time_range(self, job: ScraperJob) -> float:
        """
        Calculate appropriate time range for scraping based on job schedule.

        Returns number of days to look back when scraping posts.
        Uses last_run_at if available, otherwise estimates from cron schedule.
        Adds 20% buffer to avoid missing posts due to timing issues.

        Args:
            job: ScraperJob instance

        Returns:
            float: Number of days to look back (can be fractional, e.g., 0.08 for ~2 hours)
        """
        try:
            if job.last_run_at:
                # Calculate time since last run
                time_since_last_run = datetime.now(timezone.utc) - job.last_run_at
                days_since_last_run = time_since_last_run.total_seconds() / 86400  # Convert to days

                # Add 20% buffer
                date_range_days = days_since_last_run * 1.2

                logger.info(f"Calculated scrape range from last_run_at: {date_range_days:.3f} days ({time_since_last_run})")
            else:
                # First run - estimate interval from cron schedule
                try:
                    cron = croniter(job.schedule_cron, datetime.now(timezone.utc))
                    next_run_1 = cron.get_next(datetime)
                    next_run_2 = cron.get_next(datetime)

                    interval_seconds = (next_run_2 - next_run_1).total_seconds()
                    interval_days = interval_seconds / 86400

                    # Add 20% buffer
                    date_range_days = interval_days * 1.2

                    logger.info(f"Calculated scrape range from cron schedule: {date_range_days:.3f} days (interval: {interval_seconds/60:.1f} minutes)")
                except Exception as e:
                    logger.warning(f"Could not parse cron schedule, using default 7 days: {e}")
                    date_range_days = 7.0

            # Ensure minimum range (at least 1 hour = 0.042 days)
            # and maximum range (cap at 30 days to avoid excessive API calls)
            date_range_days = max(0.042, min(date_range_days, 30.0))

            return date_range_days

        except Exception as e:
            logger.exception(f"Error calculating scrape time range: {e}")
            return 7.0  # Default fallback

    async def _fetch_platform_content(self, platform: str, query: str, max_items: int = 20, date_range_days: float = 7.0) -> tuple[bool, list]:
        """Fetch content from platform APIs using keyword search (via providers)"""
        try:
            logger.info(f"Fetching {platform} posts for keyword: '{query}'")

            # Use provider pattern for clean abstraction
            provider = None
            if platform.lower() == 'facebook':
                provider = FacebookKeywordProvider()
            elif platform.lower() == 'twitter':
                provider = TwitterKeywordProvider()
            else:
                logger.warning(f"Platform {platform} not supported, using mock data")
                return await self._fetch_mock_content(platform, query, max_items)

            # Fetch posts using provider
            success, posts = await provider.fetch_posts(query=query, max_items=max_items, date_range_days=date_range_days)
            return success, posts

        except Exception as e:
            logger.exception(f"Error fetching content from {platform}: {e}")
            logger.info(f"Falling back to mock data for {platform}")
            return await self._fetch_mock_content(platform, query, max_items)

    async def _fetch_account_content(
        self,
        platform: str,
        account_id: str,
        account_identifier: str,
        max_items: int = 20,
        date_range_days: float = 7.0
    ) -> tuple[bool, list]:
        """Fetch content from a specific social media account (via providers)"""
        try:
            logger.info(f"Fetching {platform} posts from account: '{account_id}' / '{account_identifier}'")

            # Use provider pattern for account-based scraping
            provider = None
            if platform.lower() == 'facebook':
                provider = FacebookAccountProvider()
            elif platform.lower() == 'twitter':
                provider = TwitterAccountProvider()
            elif platform.lower() == 'instagram':
                provider = InstagramAccountProvider()
            else:
                logger.warning(f"Platform {platform} not supported for account scraping")
                return False, []

            # Fetch posts using provider
            success, posts = await provider.fetch_posts(
                account_id=account_id,
                account_identifier=account_identifier,
                max_items=max_items,
                date_range_days=date_range_days
            )
            return success, posts

        except Exception as e:
            logger.exception(f"Error fetching content from {platform} account {account_id}: {e}")
            return False, []

    async def _fetch_facebook_posts(self, query: str, max_items: int = 20) -> tuple[bool, list]:
        """Fetch Facebook posts using RapidAPI facebook-scraper-api4"""
        try:
            import requests
            import asyncio
            from datetime import datetime, timedelta

            url = "https://facebook-scraper-api4.p.rapidapi.com/fetch_search_posts"

            # Calculate date range (last 7 days for better results)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            querystring = {
                "query": query,
                "location_uid": "0",  # 0 = worldwide
                "start_time": start_date.strftime("%Y-%m-%d"),
                "end_time": end_date.strftime("%Y-%m-%d"),
                "recent_posts": "true"
            }

            # Use environment variables for API keys
            facebook_api_key = os.getenv('RAPIDAPI_KEY_FACEBOOK', 'd5adc2df3dmsh1ec84b4b22692aep11a79cjsn27b1ce51db9e')

            headers = {
                "x-rapidapi-key": facebook_api_key,
                "x-rapidapi-host": "facebook-scraper-api4.p.rapidapi.com",
            }

            # Run the synchronous request in a thread pool to make it async
            # Increased timeout to 60s and added retry logic for slow API
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

                # facebook-scraper-api4 returns structure: {"data": {"items": [...]}}
                items = data.get('data', {}).get('items', [])

                if not items:
                    logger.warning(f"No Facebook posts found for '{query}'")
                    return False, []

                # Transform API response to match expected format
                # Apply Facebook account exclusions
                from constants.facebook_exclusions import is_facebook_account_excluded

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
                        # Store original data for debugging
                        '_raw_item': item
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

    async def _fetch_twitter_posts(self, query: str, max_items: int = 20) -> tuple[bool, list]:
        """Fetch Twitter posts using RapidAPI (like social_test.py)"""
        try:
            import requests
            import asyncio

            url = "https://twitter241.p.rapidapi.com/search-v2"

            querystring = {"type": "Latest", "count": str(max_items), "query": query}

            # Use environment variables for API keys
            twitter_api_key = os.getenv('RAPIDAPI_KEY_TWITTER', '')

            headers = {
                "x-rapidapi-key": twitter_api_key,
                "x-rapidapi-host": "twitter241.p.rapidapi.com",
            }

            # Run the synchronous request in a thread pool to make it async
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

    async def _fetch_mock_content(self, platform: str, query: str, max_items: int = 20) -> tuple[bool, list]:
        """Fetch mock content as fallback"""
        try:
            mock_posts = [
                {
                    'post_id': f'mock_post_{i}',
                    'content': f'Mock {platform} post about {query} - post {i}',
                    'author': f'Mock Author {i}',
                    'url': f'https://{platform}.com/post_{i}',
                    'published_at': datetime.now(timezone.utc).isoformat(),
                    'engagement': {
                        'likes': i * 10,
                        'comments': i * 2,
                        'shares': i
                    }
                }
                for i in range(1, min(max_items, 3) + 1)  # Return 1-3 mock posts
            ]

            logger.info(f"Using {len(mock_posts)} mock posts from {platform} for '{query}'")
            return True, mock_posts

        except Exception as e:
            logger.exception(f"Failed to generate mock content for {platform}: {e}")
            return False, []

    async def _fetch_newsit_posts(self, keywords: List[str], tenant_id: UUID, max_items: int = 20) -> tuple[bool, list]:
        """Fetch pending Newsit posts from external_news_items table"""
        try:
            logger.info(f"Fetching Newsit posts for keywords: {keywords}")

            # Query external_news_items for pending items
            # Filter by: external_source='newsit', approval_status='pending', tenant_id
            query = self.db_client.service_client.table('external_news_items').select('*').eq(
                'external_source', 'newsit'
            ).eq(
                'approval_status', 'pending'
            ).eq(
                'tenant_id', str(tenant_id)
            ).order('created_at', desc=True)

            response = query.execute()

            if not response.data:
                logger.info("No pending Newsit posts found")
                return True, []

            # Filter by keywords (case-insensitive match in title, content, or category)
            matched_posts = []
            for item in response.data:
                title = (item.get('title') or '').lower()
                content = (item.get('content') or '').lower()
                category = (item.get('category') or '').lower()

                # Check if any keyword matches
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if keyword_lower in title or keyword_lower in content or keyword_lower in category:
                        matched_posts.append(item)
                        break  # Don't add same post multiple times

            # Limit to max_items
            matched_posts = matched_posts[:max_items]

            logger.info(f"✅ Found {len(matched_posts)} matching Newsit posts for keywords: {keywords}")
            return True, matched_posts

        except Exception as e:
            logger.exception(f"Error fetching Newsit posts: {e}")
            return False, []
    
    async def _convert_post_to_article(self, post: Dict[str, Any], platform: str, keyword: str):
        """Convert social media post to NewsArticle format"""
        from services.news_service import NewsArticle

        # Extract content using platform-specific logic (same as demo_job.py)
        content = self._extract_content_text(post, platform)

        if not content:
            logger.warning(f"No content extracted from {platform} post: {post}")
            content = f"Social media post from {platform}"

        # Clean content at scrape time (removes hashtags, links, etc.)
        content = self._clean_scraped_content(content)

        # Extract URL using platform-specific logic
        url = self._extract_post_url(post, platform)

        # Extract media URL (photo/image) using platform-specific logic
        media_url = self._extract_media_url(post, platform)

        # Create meaningful title from cleaned content
        title = f"Post about {keyword}"
        if len(content) > 50:
            title = content[:47] + "..."

        article = NewsArticle(
            title=title,
            content=content,
            url=url,
            source=f"{platform.title()}",
            published_at=datetime.now(timezone.utc),
            category=keyword
        )

        # Set media URL on article if found
        if media_url:
            article.media_url = media_url
            logger.info(f"Added media URL to article: {media_url}")

        return article

    async def _convert_newsit_to_article(self, newsit_item: Dict[str, Any], keyword: str):
        """Convert external_news_items (Newsit) to NewsArticle format"""
        from services.news_service import NewsArticle

        # Extract data from external_news_items
        title = newsit_item.get('title', 'Untitled')
        content = newsit_item.get('content', '')
        source_url = newsit_item.get('source_url') or ''
        source_name = newsit_item.get('source_name', 'NewsIt')
        category = newsit_item.get('category') or keyword

        # Parse timestamps
        created_at = newsit_item.get('created_at')
        if isinstance(created_at, str):
            try:
                published_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                published_at = datetime.now(timezone.utc)
        else:
            published_at = created_at if created_at else datetime.now(timezone.utc)

        # Create NewsArticle with external_news_item_id for tracking
        article = NewsArticle(
            title=title,
            content=content,
            url=source_url,
            source=source_name,
            published_at=published_at,
            category=category
        )

        # Store external_news_item_id for later updates
        article.external_news_item_id = newsit_item.get('id')
        article.external_news_item_data = newsit_item  # Store full item for publishing

        return article

    def _clean_scraped_content(self, content: str) -> str:
        """
        Clean scraped social media content at scrape time.
        Removes: HTML tags, hashtags, user mentions (@username), source links (t.co), extra whitespace.
        """
        if not content:
            return content

        cleaned = content

        # Remove HTML tags
        cleaned = re.sub(r'<[^>]+>', '', cleaned)

        # Remove hashtags
        cleaned = re.sub(r'#\w+', '', cleaned)

        # Remove user mentions (@username)
        cleaned = re.sub(r'@\w+', '', cleaned)

        # Remove t.co links and other URLs
        cleaned = re.sub(r'https?://t\.co/\w+', '', cleaned)
        cleaned = re.sub(r'https?://\S+', '', cleaned)

        # Clean up extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        return cleaned

    def _extract_content_text(self, post: dict, platform: str) -> str:
        """Extract content text from social media post (same logic as demo_job.py)"""
        try:
            if platform.lower() == 'facebook':
                return post.get('message', '') or post.get('content', '')
            elif platform.lower() == 'twitter':
                # Twitter content is nested differently
                if 'result' in post and 'legacy' in post['result']:
                    return post['result']['legacy'].get('full_text', '')
                elif 'legacy' in post:
                    return post['legacy'].get('full_text', '')
                return post.get('content', '')
            else:
                return post.get('content', '') or post.get('text', '')
        except Exception as e:
            logger.exception(f"Error extracting content text from {platform}: {e}")
            return ""

    def _extract_post_url(self, post: dict, platform: str) -> str:
        """Extract URL from social media post based on platform"""
        try:
            if platform.lower() == 'facebook':
                # Facebook API returns 'link' or 'url' field
                return post.get('link', '') or post.get('url', '') or post.get('post_url', '')
            elif platform.lower() == 'twitter':
                # Twitter API structure for tweet URL
                # Twitter URL format: https://twitter.com/{username}/status/{tweet_id}
                if 'legacy' in post:
                    # Extract user screen_name and tweet id_str from legacy structure
                    legacy = post.get('legacy', {})
                    tweet_id = legacy.get('id_str', '')

                    # Try to get username from core or legacy user_results
                    username = None
                    if 'core' in post and 'user_results' in post['core']:
                        user_legacy = post['core']['user_results'].get('result', {}).get('legacy', {})
                        username = user_legacy.get('screen_name', '')

                    if username and tweet_id:
                        return f"https://twitter.com/{username}/status/{tweet_id}"
                    elif tweet_id:
                        # Fallback: use tweet ID only
                        return f"https://twitter.com/i/status/{tweet_id}"

                # Fallback to direct url field
                return post.get('url', '') or post.get('link', '')
            else:
                # Generic extraction
                return post.get('url', '') or post.get('link', '') or post.get('post_url', '')
        except Exception as e:
            logger.exception(f"Error extracting URL from {platform} post: {e}")
            return ""

    def _extract_media_url(self, post: dict, platform: str) -> Optional[str]:
        """Extract media URL from social media post based on platform"""
        try:
            if platform.lower() == 'twitter':
                # Twitter media is in extended_entities.media array
                # Check legacy structure first (from RapidAPI response)
                if 'legacy' in post:
                    legacy = post.get('legacy', {})
                    extended_entities = legacy.get('extended_entities', {})
                    media_list = extended_entities.get('media', [])

                    if media_list and len(media_list) > 0:
                        # Get first media item (usually the main photo)
                        first_media = media_list[0]
                        media_type = first_media.get('type', '')

                        # Extract photo URL
                        if media_type == 'photo':
                            media_url = first_media.get('media_url_https', '')
                            if media_url:
                                logger.debug(f"Extracted Twitter photo URL: {media_url}")
                                return media_url

                # Fallback: check direct extended_entities (for different API structures)
                extended_entities = post.get('extended_entities', {})
                media_list = extended_entities.get('media', [])

                if media_list and len(media_list) > 0:
                    first_media = media_list[0]
                    media_url = first_media.get('media_url_https', '')
                    if media_url:
                        logger.debug(f"Extracted Twitter photo URL (fallback): {media_url}")
                        return media_url

            elif platform.lower() == 'facebook':
                # Facebook API returns media in various fields
                # Try different field names based on API version
                media_url = (
                    post.get('full_picture', '') or
                    post.get('picture', '') or
                    post.get('image', '')
                )

                # Check attachments for media
                if not media_url:
                    attachments = post.get('attachments', {})
                    if isinstance(attachments, dict):
                        data = attachments.get('data', [])
                        if data and len(data) > 0:
                            media = data[0].get('media', {})
                            media_url = media.get('image', {}).get('src', '')

                if media_url:
                    logger.debug(f"Extracted Facebook photo URL: {media_url}")
                    return media_url

            elif platform.lower() == 'instagram':
                # Instagram media extraction
                # First check if media_url is already in the post (from InstagramAccountProvider)
                media_url = post.get('media_url', '')
                if media_url:
                    logger.debug(f"Extracted Instagram media URL: {media_url}")
                    return media_url

                # Fallback: extract from image_versions2 structure
                image_versions = post.get('image_versions2', {})
                candidates = image_versions.get('candidates', [])
                if candidates and len(candidates) > 0:
                    # Get highest quality image (first in candidates)
                    media_url = candidates[0].get('url', '')
                    if media_url:
                        logger.debug(f"Extracted Instagram photo URL: {media_url}")
                        return media_url

                # Check carousel media (multiple images/videos)
                carousel_media = post.get('carousel_media', [])
                if carousel_media and len(carousel_media) > 0:
                    first_carousel_item = carousel_media[0]
                    image_versions = first_carousel_item.get('image_versions2', {})
                    candidates = image_versions.get('candidates', [])
                    if candidates and len(candidates) > 0:
                        media_url = candidates[0].get('url', '')
                        if media_url:
                            logger.debug(f"Extracted Instagram carousel photo URL: {media_url}")
                            return media_url

            # No media found
            return None

        except Exception as e:
            logger.exception(f"Error extracting media URL from {platform} post: {e}")
            return None
    
    async def _save_news_items(self, articles: list, tenant_id: UUID) -> dict:
        """Save articles to external_news_items table with duplicate checking

        Note: Function name preserved for backward compatibility, but now saves to external_news_items
        """
        try:
            from uuid import uuid4
            new_articles = []
            existing_articles = []

            if not articles:
                return {
                    'new_articles': [],
                    'existing_articles': [],
                    'all_articles': []
                }

            # Batch check for existing articles by URL and title for better performance
            article_urls = [article.url for article in articles if article.url]
            article_titles = [article.title for article in articles if article.title]

            existing_by_url = {}
            existing_by_title = {}

            if article_urls:
                url_response = self.db_client.service_client.table('external_news_items').select('id, source_url, title').eq(
                    'tenant_id', str(tenant_id)
                ).in_('source_url', article_urls).execute()

                for item in url_response.data or []:
                    url_key = item.get('source_url')
                    if url_key:
                        existing_by_url[url_key] = item

            if article_titles:
                title_response = self.db_client.service_client.table('external_news_items').select('id, source_url, title').eq(
                    'tenant_id', str(tenant_id)
                ).in_('title', article_titles).execute()

                for item in title_response.data or []:
                    existing_by_title[item['title']] = item

            # Get or create a default pipeline for this tenant (once, not per article)
            default_pipeline_id = await self._get_default_pipeline_id(tenant_id)

            # Prepare bulk insert data for external_news_items (unified table)
            external_news_items_bulk = []

            for article in articles:
                # Check if article already exists by URL or title
                existing_item = None
                duplicate_type = None

                if article.url and article.url in existing_by_url:
                    existing_item = existing_by_url[article.url]
                    duplicate_type = "URL"
                elif article.title and article.title in existing_by_title:
                    existing_item = existing_by_title[article.title]
                    duplicate_type = "Title"

                if existing_item:
                    # Article already exists, skip it
                    article.news_item_id = existing_item['id']
                    existing_articles.append(article)
                    logger.info(f"⏭️  Skipped duplicate article ({duplicate_type}): {article.title[:50]}...")
                    continue

                # Article doesn't exist, prepare for bulk insert
                news_item_id = str(uuid4())

                # Extract image URL if available
                image_url = getattr(article, 'image_url', None) or getattr(article, 'media_url', None)

                # Upload image to S3 if available
                s3_image_url = None
                if image_url:
                    # Determine external source from article source
                    external_source = article.source.lower() if article.source else 'social_media'

                    s3_result = await s3_service.upload_external_news_image(
                        image_url=image_url,
                        tenant_id=str(tenant_id),
                        external_source=external_source,
                        external_id=news_item_id
                    )

                    if s3_result:
                        s3_image_url = s3_result['url']
                        logger.info(f"Uploaded {external_source} image to S3: {s3_image_url}")
                    else:
                        logger.warning(f"Failed to upload {external_source} image to S3, using original URL")
                        s3_image_url = image_url  # Fallback to original URL

                # Prepare data for external_news_items (unified table post-migration)
                try:
                    # Clean title and content to remove HTML tags
                    cleaned_title = self._clean_scraped_content(article.title) if article.title else article.title
                    cleaned_content = self._clean_scraped_content(article.content) if article.content else article.content

                    external_news_data = {
                        'id': news_item_id,
                        'tenant_id': str(tenant_id),
                        'pipeline_id': default_pipeline_id,  # Link to pipeline
                        'external_source': article.source.lower() if article.source else 'social_media',
                        'external_id': article.url or str(uuid4()),  # Use URL for deduplication
                        'title': cleaned_title,
                        'content': cleaned_content,
                        'category': getattr(article, 'category', 'social_media'),
                        'source_url': article.url,
                        'source_name': article.source,
                        'images': {
                            'original_url': s3_image_url,
                            'thumbnail_url': s3_image_url,
                            'low_res_url': s3_image_url
                        } if s3_image_url else None,
                        # Approval workflow fields
                        'approval_status': 'pending',
                        'is_approved': False,
                        'status': 'pending_moderation',
                        # Timestamps
                        'published_at': article.published_at.isoformat() if hasattr(article, 'published_at') and article.published_at else None,
                        'fetched_at': datetime.now(timezone.utc).isoformat(),
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }

                    external_news_items_bulk.append(external_news_data)

                except Exception as e:
                    # Don't fail the whole operation if data preparation fails
                    logger.error(f"Failed to prepare external_news_item: {e}")
                    continue  # Skip this article

                # Add the ID to the article object for later reference
                article.news_item_id = news_item_id
                new_articles.append(article)

                logger.info(f"📰 Prepared social media article: {article.title[:50]}...")

            # Bulk insert to external_news_items table (unified table post-migration)
            if external_news_items_bulk:
                logger.info(f"Performing bulk insert of {len(external_news_items_bulk)} items to external_news_items table")
                self.db_client.service_client.table('external_news_items').insert(external_news_items_bulk).execute()
                logger.info(f"✓ Successfully bulk inserted {len(external_news_items_bulk)} items to external_news_items")

            if existing_articles:
                logger.info(f"⏭️  Skipped {len(existing_articles)} duplicate articles")
            logger.info(f"Successfully saved {len(new_articles)} new social media articles to database")

            return {
                'new_articles': new_articles,
                'existing_articles': existing_articles,
                'all_articles': new_articles + existing_articles
            }

        except Exception as e:
            logger.exception(f"Failed to save news items: {e}")
            raise
    
    async def _update_news_moderation(self, processed_news: list):
        """Update news items with moderation results (like demo_job.py)"""
        try:
            for processed in processed_news:
                article = processed.article
                if hasattr(article, 'news_item_id'):
                    # IMPORTANT: Do NOT set is_approved=True here - that's for manual user approval
                    # Only update moderation_status to track AI moderation result
                    moderation_data = {
                        'moderation_reason': processed.moderation_reason,
                        'moderation_score': getattr(processed, 'moderation_score', None),
                        'moderation_status': 'approved' if processed.is_approved else 'rejected',
                        'moderated_at': datetime.now(timezone.utc).isoformat()
                    }

                    # Update external_news_items table (unified table post-migration)
                    self.db_client.service_client.table('external_news_items').update(moderation_data).eq(
                        'id', article.news_item_id
                    ).execute()

            approved_count = len([p for p in processed_news if p.is_approved])
            logger.info(f"✅ Updated moderation status for {len(processed_news)} news items ({approved_count} passed moderation)")

        except Exception as e:
            logger.exception(f"Failed to update news moderation: {e}")
            raise
    
    async def _create_and_publish_posts(self, approved_content: list, job):
        """Create posts from approved content and publish them (like demo_job.py)"""
        try:
            # Create posts from approved content
            logger.info(f"Creating posts from {len(approved_content)} approved articles...")
            created_posts = await self.news_service.create_posts_from_news(
                processed_news=approved_content,
                tenant_id=str(job.tenant_id),  # Convert UUID to string
                user_id=str(job.created_by)   # Convert UUID to string
            )

            if not created_posts:
                logger.warning("No posts created from approved content")
                return

            logger.info(f"Created {len(created_posts)} post drafts")

            # Save posts to database FIRST (required for auto image search to read metadata)
            await self._save_posts(created_posts, approved_content, job.tenant_id, job.created_by)

            # Publish posts if auto-publish is enabled (after posts are saved to DB)
            await self._publish_approved_posts(created_posts, job)

        except Exception as e:
            logger.exception(f"Failed to create and publish posts: {e}")
            raise
    
    async def _save_posts(self, posts: list, processed_news: list, tenant_id: UUID, user_id: UUID):
        """Save posts to database with links to source news items (like demo_job.py)"""
        try:
            from uuid import uuid4

            # Create a mapping of article URLs to news item IDs
            news_item_map = {}
            for processed in processed_news:
                if hasattr(processed.article, 'news_item_id'):
                    news_item_map[processed.article.url] = processed.article.news_item_id
                    logger.debug(f"Added to news_item_map: {processed.article.url} -> {processed.article.news_item_id}")

            logger.info(f"Created news_item_map with {len(news_item_map)} entries")

            saved_count = 0
            for post_data in posts:
                post_data['id'] = str(uuid4())
                post_data['created_at'] = datetime.now(timezone.utc).isoformat()
                post_data['status'] = 'draft'
                post_data['created_by'] = str(user_id)
                post_data['tenant_id'] = str(tenant_id)

                # Add image_search_caption as a direct field for auto image search
                if 'metadata' not in post_data:
                    post_data['metadata'] = {}

                # Use post title as the image search term
                post_title = post_data.get('title', '')
                if post_title:
                    post_data['image_search_caption'] = post_title
                    logger.debug(f"Added image_search_caption: {post_title}")

                # Link to source news item if available
                # Check for both 'source_url' and 'original_article_url' keys
                source_url = post_data.get('metadata', {}).get('source_url') or \
                           post_data.get('metadata', {}).get('original_article_url')

                if source_url and source_url in news_item_map:
                    post_data['news_item_id'] = news_item_map[source_url]
                    logger.info(f"🔗 Linked post to news item: {news_item_map[source_url]} (source: {source_url})")
                else:
                    if source_url:
                        logger.warning(f"⚠️ Could not find news_item for URL: {source_url}")
                        logger.debug(f"Available URLs in map: {list(news_item_map.keys())}")
                    else:
                        logger.warning(f"⚠️ No source URL found in post metadata: {post_data.get('metadata', {})}")

                self.db_client.service_client.table('posts').insert(post_data).execute()
                saved_count += 1
                logger.info(f"💾 Saved post: {post_data['title']}")

            logger.info(f"Successfully saved {saved_count} posts to database")

        except Exception as e:
            logger.exception(f"Failed to save posts: {e}")
            raise
    
    async def _publish_approved_posts(self, posts: list, job):
        """Publish posts using the publish service (supports multiple channel groups)"""
        if not posts:
            return

        logger.info(f"🚀 Publishing {len(posts)} posts...")

        try:
            # Get channel_group_ids from job settings (supports multiple groups)
            channel_group_ids = job.settings.get('channel_group_ids', [])

            # Backwards compatibility: check for old singular field
            if not channel_group_ids:
                old_channel_group_id = job.settings.get('channel_group_id')
                if old_channel_group_id:
                    channel_group_ids = [old_channel_group_id]

            if not channel_group_ids:
                logger.warning("No channel_group_ids configured for auto-publish")
                return

            post_mode = job.settings.get('post_mode', 'auto')
            logger.info(f"Using {len(channel_group_ids)} channel group(s), post mode: {post_mode}")

            # Initialize services
            channel_groups_service = ChannelGroupsService()
            all_social_accounts = []
            seen_account_ids = set()  # To avoid duplicates across groups

            # Collect social accounts from all channel groups
            for channel_group_id in channel_group_ids:
                try:
                    logger.info(f"Fetching social accounts from channel group: {channel_group_id}")
                    channel_group = await channel_groups_service.get_channel_group(
                        group_id=channel_group_id,
                        tenant_id=job.tenant_id
                    )

                    if channel_group and channel_group.get('social_account_ids'):
                        accounts_response = self.db_client.service_client.table('social_accounts').select(
                            'id, platform, account_name, account_id, status, page_id, periskope_id, auto_image_search, access_token'
                        ).in_('id', channel_group["social_account_ids"]).eq('tenant_id', job.tenant_id).execute()

                        accounts = accounts_response.data or []
                        # Add only unique accounts (avoid duplicates)
                        for account in accounts:
                            if account['id'] not in seen_account_ids:
                                all_social_accounts.append(account)
                                seen_account_ids.add(account['id'])

                        logger.info(f"Found {len(accounts)} social accounts in channel group {channel_group_id}")
                    else:
                        logger.warning(f"Channel group {channel_group_id} not found or has no accounts")

                except Exception as e:
                    logger.exception(f"Error getting channel group {channel_group_id}: {e}")
                    continue  # Continue with next group

            social_accounts = all_social_accounts
            logger.info(f"Collected {len(social_accounts)} unique social accounts from {len(channel_group_ids)} channel group(s)")

            if not social_accounts:
                # Fallback: Get all connected social accounts for this tenant
                accounts_response = self.db_client.service_client.table('social_accounts').select(
                    'id, platform, account_name, account_id, status, page_id, periskope_id, auto_image_search, access_token'
                ).eq('tenant_id', str(job.tenant_id)).eq('status', 'connected').execute()

                social_accounts = accounts_response.data or []
                logger.info(f"Fallback: Using {len(social_accounts)} connected social accounts for tenant")

            if not social_accounts:
                logger.warning("No connected social accounts found for publishing")
                return

            # Set up publish service with channel group support
            # Note: Using first channel_group_id for config (legacy field)
            publish_config = PublishConfig(
                channels=[],  # Will be determined by social accounts
                publish_text=True,
                publish_image=True,
                generate_news_card=job.settings.get('generate_news_card', True),
                channel_group_id=channel_group_ids[0] if channel_group_ids else None,
                social_accounts=social_accounts
            )

            publish_service = PublishService(publish_config)
            publish_service.set_db_client(self.db_client)

            # Log auto image search configuration for debugging
            auto_enabled_accounts = [acc for acc in social_accounts if acc.get('auto_image_search', False)]
            logger.info(f"🖼️ Auto image search enabled for {len(auto_enabled_accounts)} out of {len(social_accounts)} social accounts")
            for acc in auto_enabled_accounts:
                logger.info(f"  - {acc.get('platform', 'Unknown')} ({acc.get('account_name', 'Unknown')})")
            
            published_count = 0
            for post_data in posts:
                try:
                    # Use post mode from job settings, with fallback to auto-detection
                    effective_post_mode = post_mode
                    if post_mode == 'auto':
                        # Auto-determine post mode based on content
                        post_content = post_data.get('content', {})
                        has_text = bool(post_content.get('text', '').strip()) if isinstance(post_content, dict) else bool(str(post_content).strip())
                        has_media = bool(post_content.get('media_ids')) if isinstance(post_content, dict) else False

                        if has_text and has_media:
                            effective_post_mode = "text_with_images"
                        elif has_text and not has_media:
                            effective_post_mode = "text"
                        elif not has_text and has_media:
                            effective_post_mode = "image"
                        else:
                            effective_post_mode = "text"  # Default to text

                    logger.info(f"Publishing post with mode: {effective_post_mode} (configured: {post_mode})")

                    # Log image_search_caption for debugging auto image search
                    image_search_caption = post_data.get('image_search_caption')
                    if image_search_caption:
                        logger.info(f"🔍 Post has image_search_caption: '{image_search_caption}'")
                    else:
                        logger.warning("⚠️ Post missing image_search_caption for auto image search")

                    # Publish the post
                    result = await publish_service.publish_post(
                        post_id=post_data['id'],
                        title=post_data['title'],
                        content=post_data['content']['text'] if isinstance(post_data['content'], dict) else str(post_data['content']),
                        tenant_id=str(job.tenant_id),
                        user_id=job.created_by,
                        post_mode=effective_post_mode
                    )

                    if result['success']:
                        published_count += 1
                        logger.info(f"✅ Published post: {post_data['title'][:50]}...")

                        # Log channel results
                        for channel, channel_result in result['channels'].items():
                            if channel_result['success']:
                                logger.info(f"  📱 {channel}: ✅ Success")
                            else:
                                logger.warning(f"  📱 {channel}: ❌ {channel_result.get('error', 'Unknown error')}")
                    else:
                        logger.error(f"❌ Failed to publish post: {post_data['title'][:50]}... - {result.get('error', 'Unknown error')}")

                    # Add small delay between publishes
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.exception(f"❌ Error publishing post {post_data['id']}: {e}")
                    continue

            logger.info(f"🎉 Publishing complete: {published_count}/{len(posts)} posts published successfully")

        except Exception as e:
            logger.exception(f"Failed to publish posts: {e}")
            raise
    
    async def _get_default_pipeline_id(self, tenant_id: UUID) -> str:
        """Get or create a default pipeline for scraper jobs"""
        try:
            # First try to find an existing pipeline for this tenant
            pipelines_response = self.db_client.service_client.table('pipelines').select('id').eq(
                'tenant_id', str(tenant_id)
            ).limit(1).execute()
            
            if pipelines_response.data:
                pipeline_id = pipelines_response.data[0]['id']
                logger.debug(f"Using existing pipeline: {pipeline_id}")
                return pipeline_id
            
            # If no pipeline exists, create a default one for scraper jobs
            from uuid import uuid4
            default_pipeline_id = str(uuid4())
            
            # Get a system user ID for created_by (required field)
            # Try to get the first admin user for this tenant
            users_response = self.db_client.service_client.table('users').select('id').eq(
                'tenant_id', str(tenant_id)
            ).limit(1).execute()

            if not users_response.data:
                logger.error(f"No users found for tenant {tenant_id}, cannot create pipeline")
                raise ValueError(f"Cannot create pipeline: no users found for tenant {tenant_id}")

            created_by_user_id = users_response.data[0]['id']

            pipeline_data = {
                'id': default_pipeline_id,
                'tenant_id': str(tenant_id),
                'name': 'Scraper Jobs Default Pipeline',
                'description': 'Default pipeline for social media scraper jobs',
                'config': {'type': 'scraper', 'source': 'social_media'},
                'status': 'active',
                'created_by': created_by_user_id,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            self.db_client.service_client.table('pipelines').insert(pipeline_data).execute()
            logger.info(f"Created default pipeline for scraper jobs: {default_pipeline_id}")
            
            return default_pipeline_id
            
        except Exception as e:
            logger.exception(f"Failed to get/create default pipeline: {e}")
            # Fallback to known pipeline ID if creation fails
            return "1a7b052a-70ef-4823-9623-72b66f747ad9"

    async def _update_newsit_approval_status(
        self,
        external_news_item_id: str,
        is_approved: bool,
        moderation_reason: Optional[str] = None
    ) -> bool:
        """Update approval status of external_news_items (Newsit)"""
        try:
            update_data = {
                'approval_status': 'approved' if is_approved else 'rejected',
                'moderation_reason': moderation_reason,
                'moderated_at': datetime.now(timezone.utc).isoformat()
            }

            response = self.db_client.service_client.table('external_news_items').update(
                update_data
            ).eq('id', external_news_item_id).execute()

            if response.data:
                status = "approved" if is_approved else "rejected"
                logger.info(f"✅ Updated Newsit item {external_news_item_id} approval status to: {status}")
                return True
            else:
                logger.warning(f"Failed to update Newsit item {external_news_item_id} approval status")
                return False

        except Exception as e:
            logger.exception(f"Error updating Newsit approval status: {e}")
            return False

    async def _auto_publish_newsit_item(
        self,
        processed_news,
        job: ScraperJob
    ) -> Dict[str, Any]:
        """Auto-publish approved Newsit item to configured channel groups (supports multiple groups)"""
        try:
            from services.external_news_publishing_service import get_external_news_publishing_service
            from services.channel_group_resolution_service import get_channel_group_resolution_service

            article = processed_news.article
            external_news_item_id = getattr(article, 'external_news_item_id', None)
            external_news_item_data = getattr(article, 'external_news_item_data', None)

            if not external_news_item_id or not external_news_item_data:
                logger.warning("Missing external_news_item_id or data for Newsit publishing")
                return {'success': False, 'error': 'Missing external news item data'}

            # Get channel_group_ids from job settings (supports multiple groups)
            channel_group_ids = job.settings.get('channel_group_ids', [])

            # Backwards compatibility: check for old singular field
            if not channel_group_ids:
                old_channel_group_id = job.settings.get('channel_group_id')
                if old_channel_group_id:
                    channel_group_ids = [old_channel_group_id]

            if not channel_group_ids:
                logger.warning("No channel_group_ids configured for Newsit auto-publish")
                return {'success': False, 'error': 'No channel groups configured'}

            logger.info(f"📤 Auto-publishing Newsit item {external_news_item_id} to {len(channel_group_ids)} channel group(s)")

            # Extract district from news item for intelligent routing
            district = None
            if external_news_item_data.get('city_data'):
                city_data = external_news_item_data['city_data']
                district = (
                    city_data.get('multilingual_names', {}).get('ta') or
                    city_data.get('multilingual_names', {}).get('en') or
                    city_data.get('name')
                )
                if district:
                    logger.info(f"Extracted district from news item: {district}")

            # Resolve channel group IDs (handles RECOMMENDED magic value)
            resolution_service = get_channel_group_resolution_service()
            resolved_group_ids = await resolution_service.resolve_channel_group_ids(
                channel_group_ids=channel_group_ids,
                district=district,
                tenant_id=job.tenant_id
            )

            if not resolved_group_ids:
                logger.error("No channel groups resolved after resolution (RECOMMENDED might have no matches)")
                return {'success': False, 'error': 'No channel groups could be resolved'}

            logger.info(f"Resolved to {len(resolved_group_ids)} actual channel group(s)")

            # Get publishing service
            publishing_service = get_external_news_publishing_service()

            # Publish to each channel group
            all_results = []
            success_count = 0
            failure_count = 0

            for group_id in resolved_group_ids:
                try:
                    logger.info(f"Publishing to channel group: {group_id}")

                    result = await publishing_service.publish_news_to_channels(
                        news_item=external_news_item_data,
                        channel_group_id=UUID(group_id),
                        tenant_id=job.tenant_id,
                        initiated_by=job.created_by,
                        selected_language='en'  # Default to English, can be made configurable
                    )

                    all_results.append({
                        'channel_group_id': group_id,
                        'success': result.get('success'),
                        'error': result.get('error'),
                        'results': result.get('results', [])
                    })

                    if result.get('success'):
                        success_count += 1
                        logger.info(f"✅ Successfully published to channel group {group_id}")
                    else:
                        failure_count += 1
                        logger.error(f"❌ Failed to publish to channel group {group_id}: {result.get('error')}")

                except Exception as e:
                    logger.exception(f"Error publishing to channel group {group_id}: {e}")
                    all_results.append({
                        'channel_group_id': group_id,
                        'success': False,
                        'error': str(e)
                    })
                    failure_count += 1

            # Return aggregated results
            overall_success = success_count > 0
            logger.info(
                f"Multi-channel publishing complete for {external_news_item_id}: "
                f"{success_count} succeeded, {failure_count} failed"
            )

            return {
                'success': overall_success,
                'total_groups': len(resolved_group_ids),
                'success_count': success_count,
                'failure_count': failure_count,
                'results': all_results,
                'error': None if overall_success else f"{failure_count} out of {len(resolved_group_ids)} groups failed"
            }

        except Exception as e:
            logger.exception(f"Error auto-publishing Newsit item: {e}")
            return {'success': False, 'error': str(e)}

    async def _auto_publish_social_posts(
        self,
        processed_posts: list,
        job: ScraperJob,
        platform: str
    ) -> int:
        """
        Auto-publish approved social media posts (Twitter/Facebook) with image validation.
        Only publishes if ALL conditions are met:
        1. AI moderation approved
        2. Image exists in post
        3. Image successfully uploaded to S3
        4. S3 URL stored in Supabase
        5. Auto-publish enabled in job settings

        Returns: Number of posts successfully published
        """
        # Check if auto-publish is enabled
        auto_publish_enabled = job.settings.get('auto_publish', False)
        logger.info(f"🔍 Auto-publish check for {platform}: settings={job.settings}, auto_publish={auto_publish_enabled}")

        if not auto_publish_enabled:
            logger.info(f"⏸️  Auto-publish disabled for {platform} scraper job '{job.name}', skipping auto-publish")
            return 0

        logger.info(f"✅ Auto-publish enabled for {platform} scraper job '{job.name}'")

        # Filter eligible posts (approved + has S3 image)
        eligible_posts = []

        for processed in processed_posts:
            if not processed.is_approved:
                logger.debug(f"Post not approved by AI, skipping: {processed.article.title[:50]}")
                continue

            article = processed.article
            news_item_id = getattr(article, 'news_item_id', None)

            if not news_item_id:
                logger.warning("Post missing news_item_id, skipping auto-publish")
                continue

            # Query external_news_items to check for S3 image
            try:
                news_item_response = self.db_client.service_client.table('external_news_items')\
                    .select('images')\
                    .eq('id', news_item_id)\
                    .execute()

                if not news_item_response.data or len(news_item_response.data) == 0:
                    logger.warning(f"News item {news_item_id} not found in database")
                    continue

                news_item = news_item_response.data[0]
                images = news_item.get('images')

                # Validate S3 image exists
                if not images or not images.get('original_url'):
                    logger.warning(
                        f"❌ Post '{article.title[:50]}' has NO S3 image, skipping auto-publish. "
                        f"Auto-publish requires scraped posts to have images."
                    )
                    continue

                # Verify S3 URL format
                s3_url = images['original_url']
                if not (s3_url.startswith('s3://') or s3_url.startswith('https://')):
                    logger.warning(f"Invalid S3 URL format: {s3_url}, skipping auto-publish")
                    continue

                logger.info(
                    f"✅ Post eligible for auto-publish: '{article.title[:50]}' "
                    f"(Approved + has S3 image: {s3_url[:50]}...)"
                )
                eligible_posts.append(processed)

            except Exception as e:
                logger.exception(f"Error checking image for post {news_item_id}: {e}")
                continue

        if not eligible_posts:
            logger.info(
                f"ℹ️  No {platform} posts eligible for auto-publish. "
                f"Requirements: AI approval + scraped image uploaded to S3"
            )
            return 0

        logger.info(
            f"📤 Auto-publishing {len(eligible_posts)} approved {platform} posts "
            f"(out of {len(processed_posts)} total moderated)"
        )

        # Publish using existing multi-channel logic
        try:
            await self._create_and_publish_posts(eligible_posts, job)
            logger.info(f"✅ Successfully auto-published {len(eligible_posts)} {platform} posts")
            return len(eligible_posts)

        except Exception as e:
            logger.exception(f"Error in auto-publish for {platform}: {e}")
            return 0

    async def _update_job_after_run(self, job_id: UUID, run: ScraperJobRun):
        """Update job statistics after a run"""
        try:
            # Calculate next run time
            job_response = self.db_client.service_client.table('scraper_jobs').select('schedule_cron').eq('id', str(job_id)).execute()
            if not job_response.data:
                return
            
            cron_expression = job_response.data[0]['schedule_cron']
            next_run_at = self._calculate_next_run(cron_expression)
            
            update_dict = {
                'last_run_at': run.started_at.isoformat(),
                'next_run_at': next_run_at.isoformat(),
                'run_count': 1,  # Will be incremented by SQL
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            if run.status == ScraperJobStatus.COMPLETED.value:
                update_dict['success_count'] = 1
                update_dict['last_error'] = None
            else:
                update_dict['error_count'] = 1
                update_dict['last_error'] = run.error_message
            
            # Use SQL to increment counters
            self.db_client.service_client.rpc('increment_scraper_job_counters', {
                'job_id': str(job_id),
                'success': run.status == ScraperJobStatus.COMPLETED.value,
                'last_run': run.started_at.isoformat(),
                'next_run': next_run_at.isoformat(),
                'error_msg': run.error_message
            }).execute()
            
        except Exception as e:
            logger.exception(f"Failed to update job after run: {e}")
    
    async def _get_job_statistics_batch(self, job_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get statistics for multiple jobs in a single query"""
        try:
            if not job_ids:
                return {}

            # Get all run statistics for all jobs in one query
            response = self.db_client.service_client.table('scraper_job_runs').select(
                'scraper_job_id, posts_found, posts_processed, posts_approved, posts_published, duration_seconds, status, created_at'
            ).in_('scraper_job_id', job_ids).execute()

            runs_by_job = {}
            for run in (response.data or []):
                job_id = run.get('scraper_job_id')
                if job_id not in runs_by_job:
                    runs_by_job[job_id] = []
                runs_by_job[job_id].append(run)

            # Calculate statistics for each job
            stats_map = {}
            for job_id in job_ids:
                runs = runs_by_job.get(job_id, [])

                if not runs:
                    stats_map[job_id] = {
                        'total_posts_found': 0,
                        'total_posts_processed': 0,
                        'total_posts_approved': 0,
                        'total_posts_published': 0,
                        'avg_posts_per_run': 0.0,
                        'success_rate': 0.0,
                        'last_run_duration': None
                    }
                    continue

                total_posts_found = sum(run.get('posts_found', 0) for run in runs)
                total_posts_processed = sum(run.get('posts_processed', 0) for run in runs)
                total_posts_approved = sum(run.get('posts_approved', 0) for run in runs)
                total_posts_published = sum(run.get('posts_published', 0) for run in runs)

                successful_runs = len([run for run in runs if run.get('status') == 'completed'])
                success_rate = (successful_runs / len(runs)) * 100 if runs else 0

                avg_posts_per_run = total_posts_found / len(runs) if runs else 0

                # Get last run duration
                last_run_duration = None
                if runs:
                    last_run = sorted(runs, key=lambda r: r.get('created_at', ''), reverse=True)[0]
                    last_run_duration = last_run.get('duration_seconds')

                stats_map[job_id] = {
                    'total_posts_found': total_posts_found,
                    'total_posts_processed': total_posts_processed,
                    'total_posts_approved': total_posts_approved,
                    'total_posts_published': total_posts_published,
                    'avg_posts_per_run': round(avg_posts_per_run, 2),
                    'success_rate': round(success_rate, 2),
                    'last_run_duration': last_run_duration
                }

            return stats_map

        except Exception as e:
            logger.exception(f"Failed to get job statistics batch: {e}")
            # Return empty stats for all jobs on error
            return {job_id: {
                'total_posts_found': 0,
                'total_posts_processed': 0,
                'total_posts_approved': 0,
                'total_posts_published': 0,
                'avg_posts_per_run': 0.0,
                'success_rate': 0.0,
                'last_run_duration': None
            } for job_id in job_ids}

    async def _get_job_statistics(self, job_id: UUID) -> Dict[str, Any]:
        """Get statistics for a job from its runs (single job wrapper for backward compatibility)"""
        try:
            stats_map = await self._get_job_statistics_batch([str(job_id)])
            return stats_map.get(str(job_id), {
                'total_posts_found': 0,
                'total_posts_processed': 0,
                'total_posts_approved': 0,
                'total_posts_published': 0,
                'avg_posts_per_run': 0.0,
                'success_rate': 0.0,
                'last_run_duration': None
            })
        except Exception as e:
            logger.exception(f"Failed to get job statistics: {e}")
            return {
                'total_posts_found': 0,
                'total_posts_processed': 0,
                'total_posts_approved': 0,
                'total_posts_published': 0,
                'avg_posts_per_run': 0.0,
                'success_rate': 0.0,
                'last_run_duration': None
            }

    async def _resolve_and_insert_social_accounts(
        self,
        job_id: str,
        social_account_inputs: list
    ) -> List[SocialAccountResolved]:
        """
        Resolve social account URLs and insert them into the database.

        Args:
            job_id: ID of the scraper job
            social_account_inputs: List of SocialAccountInput objects

        Returns:
            List of SocialAccountResolved objects
        """
        resolver = get_social_account_resolver()
        resolved_accounts = []

        for account_input in social_account_inputs:
            try:
                # Resolve the account URL
                resolution_result = await resolver.resolve_account(
                    platform=account_input.platform.value,
                    account_url=account_input.account_url
                )

                # Prepare data for database insertion
                account_data = {
                    'id': str(uuid4()),
                    'scraper_job_id': job_id,
                    'platform': resolution_result['platform'],
                    'account_url': resolution_result['account_url'],
                    'account_identifier': resolution_result.get('account_identifier'),
                    'account_id': resolution_result.get('account_id'),
                    'account_name': resolution_result.get('account_name'),
                    'account_metadata': resolution_result.get('account_metadata', {}),
                    'resolution_status': resolution_result['status'],
                    'resolution_error': resolution_result.get('error'),
                    'resolved_at': datetime.now(timezone.utc).isoformat() if resolution_result['status'] == 'resolved' else None,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }

                # Insert into database
                response = self.db_client.service_client.table('scraper_job_social_accounts').insert(account_data).execute()

                if response.data:
                    inserted_account = response.data[0]
                    resolved_account = SocialAccountResolved(**inserted_account)
                    resolved_accounts.append(resolved_account)

                    # Log result
                    if resolution_result['status'] == 'resolved':
                        logger.info(f"✅ Resolved {resolution_result['platform']} account: {resolution_result.get('account_name', 'Unknown')} ({resolution_result.get('account_id', 'Unknown')})")
                    else:
                        logger.warning(f"❌ Failed to resolve {resolution_result['platform']} account: {resolution_result.get('error', 'Unknown error')}")

            except Exception as e:
                logger.exception(f"Error resolving social account {account_input.account_url}: {e}")
                # Continue with other accounts even if one fails
                continue

        logger.info(f"Resolved {len(resolved_accounts)} out of {len(social_account_inputs)} social accounts")
        return resolved_accounts

    async def _load_social_accounts(self, job_id: str) -> List[SocialAccountResolved]:
        """
        Load social accounts for a scraper job from the database.

        Args:
            job_id: ID of the scraper job

        Returns:
            List of SocialAccountResolved objects
        """
        try:
            response = self.db_client.service_client.table('scraper_job_social_accounts').select('*').eq(
                'scraper_job_id', job_id
            ).execute()

            if not response.data:
                return []

            social_accounts = [SocialAccountResolved(**account_data) for account_data in response.data]
            logger.debug(f"Loaded {len(social_accounts)} social accounts for job {job_id}")
            return social_accounts

        except Exception as e:
            logger.exception(f"Error loading social accounts for job {job_id}: {e}")
            return []