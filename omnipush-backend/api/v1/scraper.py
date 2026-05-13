from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from uuid import UUID

from core.middleware import get_current_user, get_tenant_context, TenantContext
from core.database import get_database
from models.user import User
from models.auth import JWTPayload
from models.scraper_models import (
    ScraperJob, ScraperJobCreate, ScraperJobUpdate,
    ScraperJobRun, ScraperJobList, ScraperJobWithStats
)
from services.scraper_service import ScraperJobService

router = APIRouter(prefix="/scraper", tags=["scraper"])


@router.post("/jobs", response_model=ScraperJob)
async def create_scraper_job(
    job_data: ScraperJobCreate,
    current_user: JWTPayload = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db = Depends(get_database)
):
    """Create a new scraper job"""
    try:
        scraper_service = ScraperJobService(db)
        
        job = await scraper_service.create_job(
            job_data=job_data,
            tenant_id=tenant_context.tenant_id,
            user_id=current_user.sub
        )
        
        return job
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create scraper job: {str(e)}")


@router.get("/jobs", response_model=ScraperJobList)
async def list_scraper_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    enabled_only: bool = Query(False, description="Filter to enabled jobs only"),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db = Depends(get_database)
):
    """List scraper jobs with statistics"""
    try:
        scraper_service = ScraperJobService(db)
        
        result = await scraper_service.list_jobs(
            tenant_id=tenant_context.tenant_id,
            page=page,
            size=size,
            enabled_only=enabled_only
        )
        
        return ScraperJobList(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list scraper jobs: {str(e)}")


@router.get("/jobs/{job_id}", response_model=ScraperJob)
async def get_scraper_job(
    job_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    db = Depends(get_database)
):
    """Get a specific scraper job"""
    try:
        scraper_service = ScraperJobService(db)
        
        job = await scraper_service.get_job(
            job_id=job_id,
            tenant_id=tenant_context.tenant_id
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Scraper job not found")
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scraper job: {str(e)}")


@router.put("/jobs/{job_id}", response_model=ScraperJob)
async def update_scraper_job(
    job_id: UUID,
    job_data: ScraperJobUpdate,
    tenant_context: TenantContext = Depends(get_tenant_context),
    db = Depends(get_database)
):
    """Update a scraper job"""
    try:
        scraper_service = ScraperJobService(db)
        
        job = await scraper_service.update_job(
            job_id=job_id,
            job_data=job_data,
            tenant_id=tenant_context.tenant_id
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Scraper job not found")
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update scraper job: {str(e)}")


@router.delete("/jobs/{job_id}")
async def delete_scraper_job(
    job_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    db = Depends(get_database)
):
    """Delete a scraper job"""
    try:
        scraper_service = ScraperJobService(db)
        
        success = await scraper_service.delete_job(
            job_id=job_id,
            tenant_id=tenant_context.tenant_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Scraper job not found")
        
        return {"message": "Scraper job deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete scraper job: {str(e)}")


@router.post("/jobs/{job_id}/run")
async def run_scraper_job(
    job_id: UUID,
    current_user: JWTPayload = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db = Depends(get_database)
):
    """Manually trigger a scraper job run"""
    try:
        scraper_service = ScraperJobService(db)
        
        # Get the job first
        job = await scraper_service.get_job(
            job_id=job_id,
            tenant_id=tenant_context.tenant_id
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Scraper job not found")
        
        # Execute the job
        run_result = await scraper_service.execute_scraper_job(job)
        
        return {
            "message": "Scraper job executed successfully",
            "run_id": run_result.id,
            "status": run_result.status,
            "posts_found": run_result.posts_found,
            "posts_processed": run_result.posts_processed,
            "posts_approved": run_result.posts_approved,
            "posts_published": run_result.posts_published
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run scraper job: {str(e)}")


@router.get("/jobs/{job_id}/runs", response_model=List[ScraperJobRun])
async def list_scraper_job_runs(
    job_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    tenant_context: TenantContext = Depends(get_tenant_context),
    db = Depends(get_database)
):
    """List runs for a specific scraper job"""
    try:
        # First verify the job exists and user has access
        scraper_service = ScraperJobService(db)
        job = await scraper_service.get_job(job_id, tenant_context.tenant_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Scraper job not found")
        
        # Get runs for this job
        offset = (page - 1) * size
        response = db.service_client.table('scraper_job_runs').select('*').eq(
            'scraper_job_id', str(job_id)
        ).eq(
            'tenant_id', str(tenant_context.tenant_id)
        ).order('created_at', desc=True).range(offset, offset + size - 1).execute()
        
        runs = [ScraperJobRun(**run_data) for run_data in response.data]
        
        return runs
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list job runs: {str(e)}")


@router.get("/jobs/{job_id}/runs/{run_id}", response_model=ScraperJobRun)
async def get_scraper_job_run(
    job_id: UUID,
    run_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    db = Depends(get_database)
):
    """Get a specific scraper job run"""
    try:
        # First verify the job exists and user has access
        scraper_service = ScraperJobService(db)
        job = await scraper_service.get_job(job_id, tenant_context.tenant_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Scraper job not found")
        
        # Get the specific run
        response = db.service_client.table('scraper_job_runs').select('*').eq(
            'id', str(run_id)
        ).eq(
            'scraper_job_id', str(job_id)
        ).eq(
            'tenant_id', str(tenant_context.tenant_id)
        ).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Job run not found")
        
        return ScraperJobRun(**response.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job run: {str(e)}")


@router.post("/jobs/{job_id}/enable")
async def enable_scraper_job(
    job_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    db = Depends(get_database)
):
    """Enable a scraper job"""
    try:
        scraper_service = ScraperJobService(db)
        
        job = await scraper_service.update_job(
            job_id=job_id,
            job_data=ScraperJobUpdate(is_enabled=True),
            tenant_id=tenant_context.tenant_id
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Scraper job not found")
        
        return {"message": "Scraper job enabled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enable scraper job: {str(e)}")


@router.post("/jobs/{job_id}/disable")
async def disable_scraper_job(
    job_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    db = Depends(get_database)
):
    """Disable a scraper job"""
    try:
        scraper_service = ScraperJobService(db)
        
        job = await scraper_service.update_job(
            job_id=job_id,
            job_data=ScraperJobUpdate(is_enabled=False),
            tenant_id=tenant_context.tenant_id
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Scraper job not found")
        
        return {"message": "Scraper job disabled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disable scraper job: {str(e)}")


@router.get("/jobs/{job_id}/social-accounts")
async def get_job_social_accounts(
    job_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    db = Depends(get_database)
):
    """Get social accounts for a specific scraper job"""
    try:
        scraper_service = ScraperJobService(db)

        # First verify the job exists and user has access
        job = await scraper_service.get_job(job_id, tenant_context.tenant_id)

        if not job:
            raise HTTPException(status_code=404, detail="Scraper job not found")

        # Return social accounts from the job
        return {
            "job_id": str(job_id),
            "social_accounts": job.social_accounts
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get social accounts: {str(e)}")


@router.post("/jobs/{job_id}/social-accounts/revalidate")
async def revalidate_job_social_accounts(
    job_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    db = Depends(get_database)
):
    """Re-validate and resolve failed social account URLs for a job"""
    try:
        from services.social_account_resolver import get_social_account_resolver
        from datetime import datetime
        import logging
        logger = logging.getLogger(__name__)

        scraper_service = ScraperJobService(db)

        # First verify the job exists and user has access
        job = await scraper_service.get_job(job_id, tenant_context.tenant_id)

        if not job:
            raise HTTPException(status_code=404, detail="Scraper job not found")

        # Get failed social accounts
        failed_accounts = [acc for acc in job.social_accounts if acc.resolution_status == 'failed']

        if not failed_accounts:
            return {
                "message": "No failed social accounts to revalidate",
                "revalidated_count": 0
            }

        # Re-resolve failed accounts
        resolver = get_social_account_resolver()
        revalidated_count = 0

        for account in failed_accounts:
            try:
                # Re-resolve the account
                resolution_result = await resolver.resolve_account(
                    platform=account.platform,
                    account_url=account.account_url
                )

                # Update the account in database
                update_data = {
                    'account_identifier': resolution_result.get('account_identifier'),
                    'account_id': resolution_result.get('account_id'),
                    'account_name': resolution_result.get('account_name'),
                    'account_metadata': resolution_result.get('account_metadata', {}),
                    'resolution_status': resolution_result['status'],
                    'resolution_error': resolution_result.get('error'),
                    'resolved_at': datetime.now().isoformat() if resolution_result['status'] == 'resolved' else None,
                    'last_validation_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }

                db.service_client.table('scraper_job_social_accounts').update(update_data).eq(
                    'id', str(account.id)
                ).execute()

                if resolution_result['status'] == 'resolved':
                    revalidated_count += 1

            except Exception as e:
                logger.exception(f"Error revalidating account {account.account_url}: {e}")
                continue

        return {
            "message": f"Revalidated {revalidated_count} out of {len(failed_accounts)} failed accounts",
            "revalidated_count": revalidated_count,
            "total_failed": len(failed_accounts)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to revalidate social accounts: {str(e)}")


@router.post("/validate-account-url")
async def validate_account_url(
    platform: str,
    account_url: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
    db = Depends(get_database)
):
    """Validate and resolve a social account URL without saving it"""
    try:
        from services.social_account_resolver import get_social_account_resolver
        from datetime import datetime

        resolver = get_social_account_resolver()

        # Resolve the account
        resolution_result = await resolver.resolve_account(
            platform=platform,
            account_url=account_url
        )

        return {
            "platform": platform,
            "account_url": account_url,
            "account_identifier": resolution_result.get('account_identifier'),
            "account_id": resolution_result.get('account_id'),
            "account_name": resolution_result.get('account_name'),
            "account_metadata": resolution_result.get('account_metadata', {}),
            "resolution_status": resolution_result['status'],
            "resolution_error": resolution_result.get('error'),
            "resolved_at": datetime.now().isoformat() if resolution_result['status'] == 'resolved' else None
        }

    except Exception as e:
        # Return error but don't fail the request
        return {
            "platform": platform,
            "account_url": account_url,
            "resolution_status": "failed",
            "resolution_error": str(e)
        }


@router.get("/stats")
async def get_scraper_stats(
    tenant_context: TenantContext = Depends(get_tenant_context),
    db = Depends(get_database)
):
    """Get overall scraper statistics for the tenant"""
    try:
        # Get job counts
        jobs_response = db.service_client.table('scraper_jobs').select('id, is_enabled').eq(
            'tenant_id', str(tenant_context.tenant_id)
        ).execute()
        
        total_jobs = len(jobs_response.data)
        enabled_jobs = len([job for job in jobs_response.data if job['is_enabled']])
        
        # Get run statistics
        runs_response = db.service_client.table('scraper_job_runs').select(
            'status, posts_found, posts_processed, posts_approved, posts_published'
        ).eq('tenant_id', str(tenant_context.tenant_id)).execute()
        
        runs = runs_response.data or []
        total_runs = len(runs)
        successful_runs = len([run for run in runs if run['status'] == 'completed'])
        
        total_posts_found = sum(run.get('posts_found', 0) for run in runs)
        total_posts_processed = sum(run.get('posts_processed', 0) for run in runs)
        total_posts_approved = sum(run.get('posts_approved', 0) for run in runs)
        total_posts_published = sum(run.get('posts_published', 0) for run in runs)
        
        success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0
        approval_rate = (total_posts_approved / total_posts_processed * 100) if total_posts_processed > 0 else 0
        
        return {
            "total_jobs": total_jobs,
            "enabled_jobs": enabled_jobs,
            "disabled_jobs": total_jobs - enabled_jobs,
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": total_runs - successful_runs,
            "success_rate": round(success_rate, 2),
            "total_posts_found": total_posts_found,
            "total_posts_processed": total_posts_processed,
            "total_posts_approved": total_posts_approved,
            "total_posts_published": total_posts_published,
            "approval_rate": round(approval_rate, 2),
            "avg_posts_per_run": round(total_posts_found / total_runs, 2) if total_runs > 0 else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scraper stats: {str(e)}")