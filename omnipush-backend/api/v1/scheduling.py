from fastapi import APIRouter, HTTPException, status, Depends, Query, UploadFile, File
from datetime import datetime, date, timedelta
from uuid import uuid4
from typing import Optional, List
import logging
import csv
import io
import json
from celery import Celery

from core.middleware import get_current_user, get_tenant_context, TenantContext
from core.config import settings
from models.auth import JWTPayload
from models.scheduling import (
    BulkScheduleResponse,
    PublishPostRequest,
    RevokePostRequest,
    GetCalendarResponse,
    PublishPostResponse,
    RevokePostResponse,
    CalendarEvent,
    CalendarSummary,
    BulkImportError,
    PlatformPublishResult,
    PlatformRevokeResult,
    CalendarView,
    PublishStatus
)
from models.content import Platform, PostStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calendar", tags=["scheduling & publishing"])

# Initialize Celery for background tasks
# In production, this would be in a separate module
celery_app = Celery('omnipush', broker=settings.redis_url)


async def publish_to_platform(
    platform: Platform,
    account_id: str,
    content: dict,
    tenant_id: str
) -> PlatformPublishResult:
    """
    Publish content to a specific platform
    This would integrate with each platform's API
    """
    try:
        # Mock implementation - in production, integrate with actual platform APIs
        
        if platform == Platform.FACEBOOK:
            # Facebook Graph API integration
            platform_post_id = f"fb_post_{uuid4()}"
            return PlatformPublishResult(
                platform=platform,
                status=PublishStatus.SUCCESS,
                platform_post_id=platform_post_id,
                published_at=datetime.utcnow()
            )
        
        elif platform == Platform.INSTAGRAM:
            # Instagram Graph API integration
            platform_post_id = f"ig_post_{uuid4()}"
            return PlatformPublishResult(
                platform=platform,
                status=PublishStatus.SUCCESS,
                platform_post_id=platform_post_id,
                published_at=datetime.utcnow()
            )
        
        elif platform == Platform.TWITTER:
            # Twitter API v2 integration
            platform_post_id = f"tw_post_{uuid4()}"
            return PlatformPublishResult(
                platform=platform,
                status=PublishStatus.SUCCESS,
                platform_post_id=platform_post_id,
                published_at=datetime.utcnow()
            )
        
        else:
            return PlatformPublishResult(
                platform=platform,
                status=PublishStatus.FAILED,
                error=f"Platform {platform.value} not yet supported"
            )
    
    except Exception as e:
        logger.exception(f"Failed to publish to {platform.value}: {e}")
        return PlatformPublishResult(
            platform=platform,
            status=PublishStatus.FAILED,
            error=str(e)
        )


async def revoke_from_platform(
    platform: Platform,
    platform_post_id: str,
    tenant_id: str
) -> PlatformRevokeResult:
    """
    Revoke/delete a post from a specific platform
    """
    try:
        # Mock implementation - in production, integrate with actual platform APIs
        
        if platform == Platform.FACEBOOK:
            # Facebook Graph API delete
            return PlatformRevokeResult(
                platform=platform,
                status=PublishStatus.SUCCESS,
                deleted_at=datetime.utcnow()
            )
        
        elif platform == Platform.TWITTER:
            # Twitter API delete tweet
            return PlatformRevokeResult(
                platform=platform,
                status=PublishStatus.SUCCESS,
                deleted_at=datetime.utcnow()
            )
        
        else:
            return PlatformRevokeResult(
                platform=platform,
                status=PublishStatus.FAILED,
                error=f"Platform {platform.value} deletion not supported"
            )
    
    except Exception as e:
        logger.exception(f"Failed to revoke from {platform.value}: {e}")
        return PlatformRevokeResult(
            platform=platform,
            status=PublishStatus.FAILED,
            error=str(e)
        )


@router.get("", response_model=GetCalendarResponse)
async def get_calendar_view(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    view: CalendarView = Query(CalendarView.MONTH),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get calendar view of scheduled and published posts"""
    try:
        # Set default date range based on view
        if not start_date or not end_date:
            today = date.today()
            if view == CalendarView.MONTH:
                start_date = today.replace(day=1)
                next_month = start_date.replace(month=start_date.month + 1) if start_date.month < 12 else start_date.replace(year=start_date.year + 1, month=1)
                end_date = next_month - timedelta(days=1)
            elif view == CalendarView.WEEK:
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=6)
            else:  # DAY
                start_date = end_date = today
        
        # Convert dates to datetime for comparison
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Query posts in date range
        posts_response = ctx.table('posts').select(
            'id, title, content, scheduled_at, published_at, status, channels, created_by'
        ).gte('scheduled_at', start_datetime.isoformat()).lte(
            'scheduled_at', end_datetime.isoformat()
        ).order('scheduled_at').execute()
        
        events = []
        for post_data in posts_response.data or []:
            # Extract platforms from channels
            platforms = [Platform(channel['platform']) for channel in post_data.get('channels', [])]
            
            # Use scheduled_at or published_at
            event_time = post_data.get('scheduled_at') or post_data.get('published_at')
            if event_time:
                # Extract content text from content object or string
                content_data = post_data.get('content', {})
                content_text = content_data.get('text', '') if isinstance(content_data, dict) else str(content_data)
                
                events.append(CalendarEvent(
                    post_id=post_data['id'],
                    title=post_data['title'],
                    content=content_text,
                    scheduled_at=datetime.fromisoformat(event_time),
                    platforms=platforms,
                    status=PostStatus(post_data['status']),
                    created_by=post_data['created_by']
                ))
        
        # Calculate summary statistics
        total_posts = len(events)
        published = sum(1 for e in events if e.status == PostStatus.PUBLISHED)
        scheduled = sum(1 for e in events if e.status == PostStatus.SCHEDULED)
        failed = sum(1 for e in events if e.status == PostStatus.FAILED)
        
        summary = CalendarSummary(
            total_posts=total_posts,
            published=published,
            scheduled=scheduled,
            failed=failed
        )
        
        return GetCalendarResponse(
            events=events,
            summary=summary
        )
        
    except Exception as e:
        logger.exception(f"Failed to get calendar view: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve calendar data"
        )


@router.post("/posts/bulk-schedule", response_model=BulkScheduleResponse, status_code=status.HTTP_201_CREATED)
async def bulk_schedule_posts(
    csv_file: UploadFile = File(...),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Bulk schedule posts from CSV file"""
    try:
        # Validate file type
        if not csv_file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a CSV"
            )
        
        # Read CSV content
        content = await csv_file.read()
        csv_string = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_string))
        
        # Expected CSV columns: title, content, platform, account_id, scheduled_at, media_urls
        required_columns = ['title', 'content', 'platform', 'account_id', 'scheduled_at']
        
        if not all(col in csv_reader.fieldnames for col in required_columns):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CSV must contain columns: {required_columns}"
            )
        
        # Process rows
        imported = 0
        failed = 0
        errors = []
        job_id = str(uuid4())
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 to account for header
            try:
                # Validate required fields
                if not all(row.get(col, '').strip() for col in required_columns):
                    errors.append(BulkImportError(
                        row=row_num,
                        error="Missing required fields"
                    ))
                    failed += 1
                    continue
                
                # Validate platform
                try:
                    platform = Platform(row['platform'].lower())
                except ValueError:
                    errors.append(BulkImportError(
                        row=row_num,
                        error=f"Invalid platform: {row['platform']}"
                    ))
                    failed += 1
                    continue
                
                # Parse scheduled_at
                try:
                    scheduled_at = datetime.fromisoformat(row['scheduled_at'])
                except ValueError:
                    errors.append(BulkImportError(
                        row=row_num,
                        error="Invalid scheduled_at format (use ISO format)"
                    ))
                    failed += 1
                    continue
                
                # Parse media URLs if provided
                media_ids = []
                if row.get('media_urls'):
                    media_urls = [url.strip() for url in row['media_urls'].split(',')]
                    # In production, you would validate these URLs and convert to media_ids
                    # For demo, we'll create mock media_ids
                    media_ids = [str(uuid4()) for _ in media_urls]
                
                # Create post
                post_id = str(uuid4())
                post_data = {
                    'id': post_id,
                    'tenant_id': current_user.tenant_id,
                    'user_id': current_user.sub,
                    'title': row['title'],
                    'content': {
                        'text': row['content'],
                        'media_ids': media_ids
                    },
                    'channels': [{
                        'platform': platform.value,
                        'account_id': row['account_id'],
                        'customizations': {}
                    }],
                    'status': PostStatus.SCHEDULED.value,
                    'created_by': current_user.sub,
                    'scheduled_at': scheduled_at.isoformat(),
                    'created_at': datetime.utcnow().isoformat()
                }
                
                result = ctx.db.client.table('posts').insert(post_data).execute()
                
                if result.data:
                    imported += 1
                    # The global cron loop (started at app startup) picks up
                    # all 'scheduled' posts every minute and triggers publishing
                    # via BackgroundTaskService when scheduled_at becomes due.
                else:
                    errors.append(BulkImportError(
                        row=row_num,
                        error="Failed to save post to database"
                    ))
                    failed += 1
                
            except Exception as e:
                logger.exception(f"Error processing row {row_num}: {e}")
                errors.append(BulkImportError(
                    row=row_num,
                    error=str(e)
                ))
                failed += 1
        
        return BulkScheduleResponse(
            imported=imported,
            failed=failed,
            errors=errors,
            job_id=job_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Bulk schedule failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process bulk schedule"
        )


@router.post("/posts/{post_id}/publish", response_model=PublishPostResponse)
async def publish_post_now(
    post_id: str,
    request: Optional[PublishPostRequest] = None,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Publish a post immediately to all or selected platforms"""
    try:
        # Get post details
        post_response = ctx.table('posts').select('*').eq('tenant_id', ctx.tenant_id).eq('id', post_id).maybe_single().execute()
        
        if not post_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        post = post_response.data
        
        # Check if user can publish this post
        if post['created_by'] != current_user.sub and current_user.role.value not in ['admin', 'editor']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to publish this post"
            )
        
        # Check if post is in publishable state
        if post['status'] not in [PostStatus.APPROVED.value, PostStatus.SCHEDULED.value, PostStatus.DRAFT.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot publish post with status: {post['status']}"
            )
        
        # Update post status to publishing
        ctx.table('posts').update({
            'status': PostStatus.PUBLISHING.value,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('tenant_id', ctx.tenant_id).eq('id', post_id).execute()
        
        # Determine which platforms to publish to
        channels = post['channels']
        if request and request.platforms:
            # Filter channels by requested platforms
            channels = [ch for ch in channels if Platform(ch['platform']) in request.platforms]
        
        # Publish to each platform
        platform_results = []
        for channel in channels:
            platform = Platform(channel['platform'])
            result = await publish_to_platform(
                platform=platform,
                account_id=channel['account_id'],
                content=post['content'],
                tenant_id=current_user.tenant_id
            )
            platform_results.append(result)
        
        # Update post status based on results
        all_success = all(r.status == PublishStatus.SUCCESS for r in platform_results)
        any_success = any(r.status == PublishStatus.SUCCESS for r in platform_results)
        
        if all_success:
            new_status = PostStatus.PUBLISHED
        elif any_success:
            new_status = PostStatus.PUBLISHED  # Partially published is still published
        else:
            new_status = PostStatus.FAILED
        
        # Update post with results
        update_data = {
            'status': new_status.value,
            'published_at': datetime.utcnow().isoformat() if any_success else None,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        ctx.table('posts').update(update_data).eq('tenant_id', ctx.tenant_id).eq('id', post_id).execute()
        
        return PublishPostResponse(
            post_id=post_id,
            status="publishing",
            platforms=platform_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to publish post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish post"
        )


@router.post("/posts/{post_id}/revoke", response_model=RevokePostResponse)
async def revoke_published_post(
    post_id: str,
    request: RevokePostRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Revoke/delete a published post from specified platforms"""
    try:
        # Get post details
        post_response = ctx.table('posts').select('*').eq('tenant_id', ctx.tenant_id).eq('id', post_id).maybe_single().execute()
        
        if not post_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        post = post_response.data
        
        # Check if user can revoke this post
        if post['created_by'] != current_user.sub and current_user.role.value not in ['admin', 'editor']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to revoke this post"
            )
        
        # Check if post was published
        if post['status'] != PostStatus.PUBLISHED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Post was not published"
            )
        
        # Get platform post IDs (would be stored when publishing)
        # For demo, we'll use mock platform post IDs
        revocation_results = []
        for platform in request.platforms:
            # In production, you'd get the actual platform_post_id from database
            mock_platform_post_id = f"{platform.value}_post_{post_id}"
            
            result = await revoke_from_platform(
                platform=platform,
                platform_post_id=mock_platform_post_id,
                tenant_id=current_user.tenant_id
            )
            revocation_results.append(result)
        
        return RevokePostResponse(
            post_id=post_id,
            revocation_results=revocation_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to revoke post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke post"
        )


@router.get("/posts/{post_id}/schedule-status")
async def get_post_schedule_status(
    post_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get the scheduling status of a post"""
    try:
        post_response = ctx.table('posts').select(
            'id, title, status, scheduled_at, published_at, channels'
        ).eq('tenant_id', ctx.tenant_id).eq('id', post_id).maybe_single().execute()
        
        if not post_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        post = post_response.data
        
        # Calculate time until scheduled publication
        time_until_publish = None
        if post.get('scheduled_at') and post['status'] == PostStatus.SCHEDULED.value:
            scheduled_time = datetime.fromisoformat(post['scheduled_at'])
            time_until_publish = (scheduled_time - datetime.utcnow()).total_seconds()
        
        return {
            "post_id": post['id'],
            "title": post['title'],
            "status": post['status'],
            "scheduled_at": post.get('scheduled_at'),
            "published_at": post.get('published_at'),
            "time_until_publish_seconds": time_until_publish,
            "platforms": [ch['platform'] for ch in post.get('channels', [])],
            "can_publish_now": post['status'] in [PostStatus.APPROVED.value, PostStatus.SCHEDULED.value],
            "can_cancel": post['status'] == PostStatus.SCHEDULED.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get schedule status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get schedule status"
        )