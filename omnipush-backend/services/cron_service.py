"""
Cron job service for automated tasks including news fetching and processing.
Handles scheduling, execution, and management of background tasks.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable
from uuid import uuid4, UUID
import json
from dataclasses import dataclass, asdict
from croniter import croniter

from services.news_service import NewsService
from core.config import settings
from supabase import Client

logger = logging.getLogger(__name__)


@dataclass
class CronJob:
    id: str
    name: str
    schedule: str  # Cron expression
    task_type: str
    parameters: Dict[str, Any]
    tenant_id: Optional[str] = None
    is_enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class CronJobRun:
    id: str
    job_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "running"  # running, completed, failed
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class CronService:
    def __init__(self, db_client: Client):
        self.db_client = db_client
        self.news_service = NewsService()
        self.running = False
        self.active_jobs: Dict[str, CronJob] = {}
        self.job_handlers: Dict[str, Callable] = {
            "news_fetch": self._handle_news_fetch,
            "scheduled_posts": self._handle_scheduled_posts,
            "analytics_sync": self._handle_analytics_sync,
        }

    async def start(self):
        """Start the cron service"""
        if self.running:
            return
        
        self.running = True
        logger.info("Cron service started")
        
        # Load active jobs from database
        await self._load_active_jobs()
        
        # Start the main cron loop
        asyncio.create_task(self._cron_loop())

    async def stop(self):
        """Stop the cron service"""
        self.running = False
        logger.info("Cron service stopped")

    async def _load_active_jobs(self):
        """Load active cron jobs from database"""
        try:
            response = self.db_client.table('cron_jobs').select('*').eq('is_enabled', True).execute()
            
            for job_data in response.data or []:
                job = CronJob(
                    id=job_data['id'],
                    name=job_data['name'],
                    schedule=job_data['schedule'],
                    task_type=job_data['task_type'],
                    parameters=job_data['parameters'],
                    tenant_id=job_data.get('tenant_id'),
                    is_enabled=job_data['is_enabled'],
                    last_run=datetime.fromisoformat(job_data['last_run']) if job_data.get('last_run') else None,
                    next_run=datetime.fromisoformat(job_data['next_run']) if job_data.get('next_run') else None,
                    run_count=job_data.get('run_count', 0),
                    created_at=datetime.fromisoformat(job_data['created_at']) if job_data.get('created_at') else None,
                    updated_at=datetime.fromisoformat(job_data['updated_at']) if job_data.get('updated_at') else None
                )
                
                self.active_jobs[job.id] = job
                
                # Calculate next run if not set
                if not job.next_run:
                    job.next_run = self._calculate_next_run(job.schedule)
                    await self._update_job_in_db(job)
            
            logger.info(f"Loaded {len(self.active_jobs)} active cron jobs")
            
        except Exception as e:
            logger.exception(f"Failed to load cron jobs: {e}")

    async def _cron_loop(self):
        """Main cron loop that checks and executes jobs"""
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                
                for job_id, job in list(self.active_jobs.items()):
                    if job.next_run and now >= job.next_run:
                        # Execute job
                        asyncio.create_task(self._execute_job(job))
                
                # Sleep for 60 seconds before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.exception(f"Error in cron loop: {e}")
                await asyncio.sleep(60)

    async def _execute_job(self, job: CronJob):
        """Execute a cron job"""
        run_id = str(uuid4())
        job_run = CronJobRun(
            id=run_id,
            job_id=job.id,
            started_at=datetime.now(timezone.utc)
        )
        
        logger.info(f"Executing cron job: {job.name} (ID: {job.id})")
        
        try:
            # Save job run to database
            await self._save_job_run(job_run)
            
            # Execute the job handler
            handler = self.job_handlers.get(job.task_type)
            if not handler:
                raise ValueError(f"No handler found for task type: {job.task_type}")
            
            result = await handler(job)
            
            # Update job run with success
            job_run.completed_at = datetime.now(timezone.utc)
            job_run.status = "completed"
            job_run.result = result
            
            # Update job statistics
            job.last_run = job_run.started_at
            job.next_run = self._calculate_next_run(job.schedule, job.last_run)
            job.run_count += 1
            
            logger.info(f"Cron job completed successfully: {job.name}")
            
        except Exception as e:
            logger.exception(f"Cron job failed: {job.name} - {str(e)}")
            
            # Update job run with failure
            job_run.completed_at = datetime.now(timezone.utc)
            job_run.status = "failed"
            job_run.error_message = str(e)
            
            # Still update next run time for the job
            job.last_run = job_run.started_at
            job.next_run = self._calculate_next_run(job.schedule, job.last_run)
        
        finally:
            # Save final job run state
            await self._update_job_run(job_run)
            
            # Update job in database
            await self._update_job_in_db(job)

    async def _handle_news_fetch(self, job: CronJob) -> Dict[str, Any]:
        """Handle automated news fetching and post creation"""
        try:
            parameters = job.parameters
            category = parameters.get('category', 'technology')
            max_articles = parameters.get('max_articles', 5)
            tenant_id = job.tenant_id
            
            if not tenant_id:
                raise ValueError("Tenant ID is required for news fetch jobs")
            
            # Get tenant's news settings
            news_settings = await self._get_tenant_news_settings(tenant_id)
            if not news_settings.get('enabled', False):
                return {"status": "skipped", "reason": "News automation disabled for tenant"}
            
            # Process news batch
            processed_news = await self.news_service.process_news_batch(
                category=category,
                max_articles=max_articles
            )
            
            if not processed_news:
                return {"status": "completed", "articles_processed": 0, "posts_created": 0}
            
            # Get system user for automated posts
            system_user_id = await self._get_system_user_id(tenant_id)
            
            # Create posts from approved news
            created_posts = await self.news_service.create_posts_from_news(
                processed_news=processed_news,
                tenant_id=tenant_id,
                user_id=system_user_id
            )
            
            # Save posts to database
            posts_saved = 0
            for post_data in created_posts:
                try:
                    post_data['id'] = str(uuid4())
                    post_data['created_at'] = datetime.utcnow().isoformat()
                    post_data['status'] = 'draft'  # Always start as draft
                    
                    # Auto-publish if enabled in settings
                    if news_settings.get('auto_publish', False):
                        post_data['status'] = 'published'
                        post_data['published_at'] = datetime.utcnow().isoformat()
                    
                    self.db_client.table('posts').insert(post_data).execute()
                    posts_saved += 1
                    
                except Exception as e:
                    logger.exception(f"Failed to save post: {e}")
            
            return {
                "status": "completed",
                "articles_processed": len(processed_news),
                "articles_approved": len([n for n in processed_news if n.is_approved]),
                "posts_created": posts_saved,
                "category": category
            }
            
        except Exception as e:
            logger.exception(f"News fetch job failed: {e}")
            raise

    async def _handle_scheduled_posts(self, job: CronJob) -> Dict[str, Any]:
        """Find due scheduled posts and trigger publishing via BackgroundTaskService"""
        from services.background_task_service import background_task_service

        try:
            now = datetime.utcnow().isoformat()

            # Query due posts — scope to tenant if specified, else all tenants
            query = self.db_client.table('posts').select('*').eq(
                'status', 'scheduled'
            ).lte('scheduled_at', now)
            if job.tenant_id:
                query = query.eq('tenant_id', job.tenant_id)

            response = query.execute()

            # Wire up the db client once
            if not background_task_service.db_client:
                background_task_service.set_db_client(self.db_client)

            posts_triggered = 0
            for post_data in response.data or []:
                try:
                    content_data = post_data.get('content', {})
                    if isinstance(content_data, dict):
                        content_text = content_data.get('text', '')
                    else:
                        content_text = str(content_data)

                    await background_task_service.create_and_publish_post_task(
                        post_id=post_data['id'],
                        title=post_data.get('title', ''),
                        content=content_text,
                        tenant_id=post_data['tenant_id'],
                        user_id=post_data.get('created_by', ''),
                        channel_group_id=post_data.get('channel_group_id'),
                        image_url=post_data.get('image_url'),
                        post_mode=post_data.get('post_mode', 'text'),
                    )
                    posts_triggered += 1
                    logger.info(f"Triggered publishing for scheduled post: {post_data['id']}")

                except Exception as e:
                    logger.exception(f"Failed to trigger post {post_data['id']}: {e}")

            return {"status": "completed", "posts_triggered": posts_triggered}

        except Exception as e:
            logger.exception(f"Scheduled posts job failed: {e}")
            raise

    async def _handle_analytics_sync(self, job: CronJob) -> Dict[str, Any]:
        """Handle analytics synchronization"""
        # Placeholder for analytics sync functionality
        return {
            "status": "completed",
            "message": "Analytics sync not implemented yet"
        }

    def _calculate_next_run(self, schedule: str, from_time: datetime = None) -> datetime:
        """Calculate next run time from cron expression using croniter"""
        if from_time is None:
            from_time = datetime.now(timezone.utc)
        # croniter needs a naive datetime; strip tzinfo then re-add UTC
        naive = from_time.replace(tzinfo=None) if from_time.tzinfo else from_time
        try:
            cron = croniter(schedule, naive)
            next_run = cron.get_next(datetime)
            return next_run.replace(tzinfo=timezone.utc)
        except Exception:
            # Fallback: 1 hour from now
            return from_time + timedelta(hours=1)

    async def _get_tenant_news_settings(self, tenant_id: str) -> Dict[str, Any]:
        """Get news automation settings for a tenant"""
        try:
            response = self.db_client.table('tenant_settings').select(
                'news_automation'
            ).eq('tenant_id', tenant_id).maybe_single().execute()
            
            if response.data:
                return response.data.get('news_automation', {})
            
            # Default settings
            return {
                'enabled': False,
                'auto_publish': False,
                'categories': ['technology'],
                'max_articles_per_run': 5
            }
            
        except Exception:
            # Return default settings if no settings found
            return {
                'enabled': False,
                'auto_publish': False,
                'categories': ['technology'],
                'max_articles_per_run': 5
            }

    async def _get_system_user_id(self, tenant_id: str) -> str:
        """Get or create system user for automated posts"""
        try:
            # Try to find existing system user
            response = self.db_client.table('users').select('id').eq(
                'tenant_id', tenant_id
            ).eq('email', 'system@omnipush.ai').maybe_single().execute()
            
            if response.data:
                return response.data['id']
            
            # Create system user if not found
            system_user_id = str(uuid4())
            self.db_client.table('users').insert({
                'id': system_user_id,
                'tenant_id': tenant_id,
                'email': 'system@omnipush.ai',
                'first_name': 'System',
                'last_name': 'Bot',
                'role': 'system',
                'status': 'active',
                'created_at': datetime.utcnow().isoformat()
            }).execute()
            
            return system_user_id
            
        except Exception as e:
            logger.exception(f"Failed to get system user: {e}")
            # Fallback - use first admin user
            response = self.db_client.table('users').select('id').eq(
                'tenant_id', tenant_id
            ).eq('role', 'tenant_admin').limit(1).execute()
            
            if response.data:
                return response.data[0]['id']
            
            raise ValueError("No suitable user found for automated posts")

    @staticmethod
    def _is_db_id(value: str) -> bool:
        """Return True only if value is a valid UUID (i.e. persisted in the DB)."""
        try:
            UUID(value)
            return True
        except (ValueError, AttributeError):
            return False

    async def _save_job_run(self, job_run: CronJobRun):
        """Save job run to database — skipped for in-memory system jobs."""
        if not self._is_db_id(job_run.job_id):
            return
        try:
            self.db_client.table('cron_job_runs').insert({
                'id': job_run.id,
                'job_id': job_run.job_id,
                'started_at': job_run.started_at.isoformat(),
                'status': job_run.status
            }).execute()
        except Exception as e:
            logger.exception(f"Failed to save job run: {e}")

    async def _update_job_run(self, job_run: CronJobRun):
        """Update job run in database — skipped for in-memory system jobs."""
        if not self._is_db_id(job_run.job_id):
            return
        try:
            update_data = {
                'status': job_run.status,
                'completed_at': job_run.completed_at.isoformat() if job_run.completed_at else None
            }

            if job_run.result:
                update_data['result'] = json.dumps(job_run.result)

            if job_run.error_message:
                update_data['error_message'] = job_run.error_message

            self.db_client.table('cron_job_runs').update(update_data).eq('id', job_run.id).execute()

        except Exception as e:
            logger.exception(f"Failed to update job run: {e}")

    async def _update_job_in_db(self, job: CronJob):
        """Update job in database — skipped for in-memory system jobs."""
        if not self._is_db_id(job.id):
            return
        try:
            update_data = {
                'last_run': job.last_run.isoformat() if job.last_run else None,
                'next_run': job.next_run.isoformat() if job.next_run else None,
                'run_count': job.run_count,
                'updated_at': datetime.utcnow().isoformat()
            }

            self.db_client.table('cron_jobs').update(update_data).eq('id', job.id).execute()

        except Exception as e:
            logger.exception(f"Failed to update job in database: {e}")

    # Public API methods
    
    async def create_job(self, job: CronJob) -> str:
        """Create a new cron job"""
        try:
            job.id = str(uuid4())
            job.created_at = datetime.utcnow()
            job.next_run = self._calculate_next_run(job.schedule)
            
            job_data = asdict(job)
            job_data['created_at'] = job.created_at.isoformat()
            job_data['next_run'] = job.next_run.isoformat()
            if job_data.get('last_run'):
                job_data['last_run'] = job.last_run.isoformat()
            
            self.db_client.table('cron_jobs').insert(job_data).execute()
            
            if job.is_enabled:
                self.active_jobs[job.id] = job
            
            logger.info(f"Created cron job: {job.name} (ID: {job.id})")
            return job.id
            
        except Exception as e:
            logger.exception(f"Failed to create cron job: {e}")
            raise

    async def update_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """Update a cron job"""
        try:
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                
                for key, value in updates.items():
                    if hasattr(job, key):
                        setattr(job, key, value)
                
                job.updated_at = datetime.utcnow()
                
                # Recalculate next run if schedule changed
                if 'schedule' in updates:
                    job.next_run = self._calculate_next_run(job.schedule)
                
                await self._update_job_in_db(job)
            
            # Update in database
            update_data = updates.copy()
            update_data['updated_at'] = datetime.utcnow().isoformat()
            
            self.db_client.table('cron_jobs').update(update_data).eq('id', job_id).execute()
            
            return True
            
        except Exception as e:
            logger.exception(f"Failed to update cron job: {e}")
            return False

    async def delete_job(self, job_id: str) -> bool:
        """Delete a cron job"""
        try:
            # Remove from active jobs
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
            
            # Delete from database
            self.db_client.table('cron_jobs').delete().eq('id', job_id).execute()
            
            return True
            
        except Exception as e:
            logger.exception(f"Failed to delete cron job: {e}")
            return False

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a cron job"""
        try:
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                return {
                    "id": job.id,
                    "name": job.name,
                    "is_enabled": job.is_enabled,
                    "last_run": job.last_run.isoformat() if job.last_run else None,
                    "next_run": job.next_run.isoformat() if job.next_run else None,
                    "run_count": job.run_count
                }
            
            return None
            
        except Exception as e:
            logger.exception(f"Failed to get job status: {e}")
            return None