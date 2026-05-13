"""
Automation API endpoints for managing cron jobs and automated news processing.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4
from pydantic import BaseModel
import logging

from core.middleware import get_current_user, get_tenant_context, TenantContext
from models.auth import JWTPayload
from services.cron_service import CronService, CronJob
from services.news_service import NewsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/automation", tags=["automation"])


# Request/Response Models
class CreateCronJobRequest(BaseModel):
    name: str
    schedule: str  # Cron expression
    task_type: str  # news_fetch, scheduled_posts, analytics_sync
    parameters: Dict[str, Any] = {}
    is_enabled: bool = True


class UpdateCronJobRequest(BaseModel):
    name: Optional[str] = None
    schedule: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None


class CronJobResponse(BaseModel):
    id: str
    name: str
    schedule: str
    task_type: str
    parameters: Dict[str, Any]
    tenant_id: Optional[str]
    is_enabled: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    run_count: int
    created_at: datetime
    updated_at: Optional[datetime]


class NewsSettingsRequest(BaseModel):
    enabled: bool = False
    auto_publish: bool = False
    categories: List[str] = ["technology"]
    max_articles_per_run: int = 5
    schedule: str = "0 */2 * * *"  # Every 2 hours


class NewsSettingsResponse(BaseModel):
    enabled: bool
    auto_publish: bool
    categories: List[str]
    max_articles_per_run: int
    schedule: str
    job_id: Optional[str] = None


class TestNewsResponse(BaseModel):
    status: str
    articles_processed: int
    articles_approved: int
    posts_created: int
    sample_posts: List[Dict[str, Any]]


class FetchNewsRequest(BaseModel):
    city: str = "Coimbatore"
    pipeline_id: Optional[str] = None


class FetchNewsResponse(BaseModel):
    success: bool
    articles_fetched: int
    articles_stored: int
    last_sync: Optional[str] = None
    new_sync_time: Optional[str] = None
    error: Optional[str] = None


# Global service instances (would be initialized in main app)
cron_service: Optional[CronService] = None
news_service: Optional[NewsService] = None


def get_news_service() -> NewsService:
    """Get the global news service instance"""
    global news_service
    if not news_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="News service not available"
        )
    return news_service


def get_cron_service() -> CronService:
    """Get the global cron service instance"""
    global cron_service
    if not cron_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Automation service not available"
        )
    return cron_service


@router.get("/cron-jobs", response_model=List[CronJobResponse])
async def list_cron_jobs(
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """List all cron jobs for the tenant"""
    try:
        response = ctx.db.client.table('cron_jobs').select('*').eq(
            'tenant_id', ctx.tenant_id
        ).order('created_at', desc=True).execute()
        
        jobs = []
        for job_data in response.data or []:
            jobs.append(CronJobResponse(
                id=job_data['id'],
                name=job_data['name'],
                schedule=job_data['schedule'],
                task_type=job_data['task_type'],
                parameters=job_data['parameters'],
                tenant_id=job_data['tenant_id'],
                is_enabled=job_data['is_enabled'],
                last_run=datetime.fromisoformat(job_data['last_run']) if job_data.get('last_run') else None,
                next_run=datetime.fromisoformat(job_data['next_run']) if job_data.get('next_run') else None,
                run_count=job_data.get('run_count', 0),
                created_at=datetime.fromisoformat(job_data['created_at']),
                updated_at=datetime.fromisoformat(job_data['updated_at']) if job_data.get('updated_at') else None
            ))
        
        return jobs
        
    except Exception as e:
        logger.exception(f"Failed to list cron jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cron jobs"
        )


@router.post("/cron-jobs", response_model=CronJobResponse, status_code=status.HTTP_201_CREATED)
async def create_cron_job(
    request: CreateCronJobRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
    cron_service: CronService = Depends(get_cron_service)
):
    """Create a new cron job"""
    try:
        # Only admins can create cron jobs
        if current_user.role.value != 'admin' and current_user.role.value != 'tenant_admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create cron jobs"
            )
        
        job = CronJob(
            id="",  # Will be generated in create_job
            name=request.name,
            schedule=request.schedule,
            task_type=request.task_type,
            parameters=request.parameters,
            tenant_id=ctx.tenant_id,
            is_enabled=request.is_enabled
        )
        
        job_id = await cron_service.create_job(job)
        job.id = job_id
        
        return CronJobResponse(
            id=job.id,
            name=job.name,
            schedule=job.schedule,
            task_type=job.task_type,
            parameters=job.parameters,
            tenant_id=job.tenant_id,
            is_enabled=job.is_enabled,
            last_run=job.last_run,
            next_run=job.next_run,
            run_count=job.run_count,
            created_at=job.created_at or datetime.utcnow(),
            updated_at=job.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to create cron job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create cron job"
        )


@router.put("/cron-jobs/{job_id}", response_model=CronJobResponse)
async def update_cron_job(
    job_id: str,
    request: UpdateCronJobRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
    cron_service: CronService = Depends(get_cron_service)
):
    """Update a cron job"""
    try:
        # Only admins can update cron jobs
        if current_user.role.value != 'admin' and current_user.role.value != 'tenant_admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can update cron jobs"
            )
        
        # Check if job exists and belongs to tenant
        response = ctx.db.client.table('cron_jobs').select('*').eq(
            'id', job_id
        ).eq('tenant_id', ctx.tenant_id).maybe_single().execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cron job not found"
            )

        # Build update data
        updates = {}
        if request.name is not None:
            updates['name'] = request.name
        if request.schedule is not None:
            updates['schedule'] = request.schedule
        if request.parameters is not None:
            updates['parameters'] = request.parameters
        if request.is_enabled is not None:
            updates['is_enabled'] = request.is_enabled
        
        success = await cron_service.update_job(job_id, updates)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update cron job"
            )
        
        # Get updated job
        updated_response = ctx.db.client.table('cron_jobs').select('*').eq('id', job_id).maybe_single().execute()
        job_data = updated_response.data
        
        return CronJobResponse(
            id=job_data['id'],
            name=job_data['name'],
            schedule=job_data['schedule'],
            task_type=job_data['task_type'],
            parameters=job_data['parameters'],
            tenant_id=job_data['tenant_id'],
            is_enabled=job_data['is_enabled'],
            last_run=datetime.fromisoformat(job_data['last_run']) if job_data.get('last_run') else None,
            next_run=datetime.fromisoformat(job_data['next_run']) if job_data.get('next_run') else None,
            run_count=job_data.get('run_count', 0),
            created_at=datetime.fromisoformat(job_data['created_at']),
            updated_at=datetime.fromisoformat(job_data['updated_at']) if job_data.get('updated_at') else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update cron job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update cron job"
        )


@router.delete("/cron-jobs/{job_id}")
async def delete_cron_job(
    job_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
    cron_service: CronService = Depends(get_cron_service)
):
    """Delete a cron job"""
    try:
        # Only admins can delete cron jobs
        if current_user.role.value != 'admin' and current_user.role.value != 'tenant_admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can delete cron jobs"
            )
        
        # Check if job exists and belongs to tenant
        response = ctx.db.client.table('cron_jobs').select('id').eq(
            'id', job_id
        ).eq('tenant_id', ctx.tenant_id).maybe_single().execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cron job not found"
            )
        
        success = await cron_service.delete_job(job_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete cron job"
            )
        
        return {"message": "Cron job deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete cron job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete cron job"
        )


@router.get("/news-settings", response_model=NewsSettingsResponse)
async def get_news_settings(
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get automated news settings for the tenant"""
    try:
        # Get tenant settings
        response = ctx.db.client.table('tenant_settings').select('*').eq(
            'tenant_id', ctx.tenant_id
        ).maybe_single().execute()
        
        news_settings = {}
        job_id = None
        
        if response and response.data:
            news_settings = response.data.get('news_automation', {})
            
            # Find associated cron job
            job_response = ctx.db.client.table('cron_jobs').select('id').eq(
                'tenant_id', ctx.tenant_id
            ).eq('task_type', 'news_fetch').execute()
            
            if job_response.data:
                job_id = job_response.data[0]['id']
        
        return NewsSettingsResponse(
            enabled=news_settings.get('enabled', False),
            auto_publish=news_settings.get('auto_publish', False),
            categories=news_settings.get('categories', ['technology']),
            max_articles_per_run=news_settings.get('max_articles_per_run', 5),
            schedule=news_settings.get('schedule', '0 */2 * * *'),
            job_id=job_id
        )
        
    except Exception as e:
        logger.exception(f"Failed to get news settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve news settings"
        )


@router.post("/news-settings", response_model=NewsSettingsResponse)
async def update_news_settings(
    request: NewsSettingsRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
    cron_service: CronService = Depends(get_cron_service)
):
    """Update automated news settings for the tenant"""
    try:
        # Only admins can update settings
        if current_user.role.value != 'admin' and current_user.role.value != 'tenant_admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can update news settings"
            )
        
        settings_data = {
            'enabled': request.enabled,
            'auto_publish': request.auto_publish,
            'categories': request.categories,
            'max_articles_per_run': request.max_articles_per_run,
            'schedule': request.schedule
        }
        
        # Update or create tenant settings
        try:
            # Try to update existing settings
            ctx.db.client.table('tenant_settings').update({
                'news_automation': settings_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('tenant_id', ctx.tenant_id).execute()
            
        except:
            # Create new settings if not exist
            ctx.db.client.table('tenant_settings').insert({
                'tenant_id': ctx.tenant_id,
                'news_automation': settings_data,
                'created_at': datetime.utcnow().isoformat()
            }).execute()
        
        # Manage cron job
        job_id = None
        if request.enabled:
            # Find existing news job
            job_response = ctx.db.client.table('cron_jobs').select('id').eq(
                'tenant_id', ctx.tenant_id
            ).eq('task_type', 'news_fetch').execute()
            
            if job_response.data:
                # Update existing job
                job_id = job_response.data[0]['id']
                await cron_service.update_job(job_id, {
                    'schedule': request.schedule,
                    'parameters': {
                        'categories': request.categories,
                        'max_articles': request.max_articles_per_run,
                        'auto_publish': request.auto_publish
                    },
                    'is_enabled': True
                })
            else:
                # Create new job
                job = CronJob(
                    id="",
                    name=f"News Automation - {ctx.tenant_id}",
                    schedule=request.schedule,
                    task_type="news_fetch",
                    parameters={
                        'categories': request.categories,
                        'max_articles': request.max_articles_per_run,
                        'auto_publish': request.auto_publish
                    },
                    tenant_id=ctx.tenant_id,
                    is_enabled=True
                )
                job_id = await cron_service.create_job(job)
        else:
            # Disable existing job
            job_response = ctx.db.client.table('cron_jobs').select('id').eq(
                'tenant_id', ctx.tenant_id
            ).eq('task_type', 'news_fetch').execute()
            
            if job_response.data:
                job_id = job_response.data[0]['id']
                await cron_service.update_job(job_id, {'is_enabled': False})
        
        return NewsSettingsResponse(
            enabled=request.enabled,
            auto_publish=request.auto_publish,
            categories=request.categories,
            max_articles_per_run=request.max_articles_per_run,
            schedule=request.schedule,
            job_id=job_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update news settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update news settings"
        )


@router.post("/test-news", response_model=TestNewsResponse)
async def test_news_automation(
    category: str = "technology",
    max_articles: int = 3,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Test news automation without saving posts"""
    try:
        # Only admins can test
        if current_user.role.value != 'admin' and current_user.role.value != 'tenant_admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can test news automation"
            )
        
        news_service = NewsService()
        
        # Process news batch
        processed_news = await news_service.process_news_batch(
            category=category,
            max_articles=max_articles
        )
        
        if not processed_news:
            return TestNewsResponse(
                status="completed",
                articles_processed=0,
                articles_approved=0,
                posts_created=0,
                sample_posts=[]
            )
        
        # Create sample posts (don't save to database)
        sample_posts = []
        for news in processed_news[:2]:  # Show max 2 samples
            if news.is_approved and news.post_content:
                sample_posts.append({
                    "title": news.article.title,
                    "content": news.post_content,
                    "source": news.article.source,
                    "category": news.article.category,
                    "published_at": news.article.published_at.isoformat()
                })
        
        return TestNewsResponse(
            status="completed",
            articles_processed=len(processed_news),
            articles_approved=len([n for n in processed_news if n.is_approved]),
            posts_created=len([n for n in processed_news if n.is_approved and n.post_content]),
            sample_posts=sample_posts
        )
        
    except Exception as e:
        logger.exception(f"Failed to test news automation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test news automation"
        )


@router.post("/fetch-news", response_model=FetchNewsResponse)
async def fetch_and_store_news(
    request: FetchNewsRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Fetch latest news from local endpoint and store them in database"""
    try:
        # Only admins can fetch news
        if current_user.role.value != 'admin' and current_user.role.value != 'tenant_admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can fetch news"
            )
        
        news_service = get_news_service()
        
        # Fetch and store news
        result = await news_service.fetch_and_store_new_news(
            city=request.city,
            pipeline_id=request.pipeline_id
        )
        
        return FetchNewsResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to fetch and store news: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch and store news"
        )


@router.get("/news-items/{pipeline_id}", response_model=List[Dict[str, Any]])
async def get_news_items(
    pipeline_id: str,
    limit: int = 10,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get news items for a specific pipeline"""
    try:
        news_service = get_news_service()
        
        # Get news items from database
        news_items = await news_service.get_pending_news_articles(
            pipeline_id=pipeline_id,
            limit=limit
        )
        
        return news_items
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get news items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get news items"
        )


# Initialize services (this would be called from main app)
def initialize_cron_service(db_client):
    """Initialize the global cron service"""
    global cron_service
    cron_service = CronService(db_client)


def initialize_news_service():
    """Initialize the global news service"""
    global news_service
    news_service = NewsService()