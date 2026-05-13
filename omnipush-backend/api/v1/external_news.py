"""
External News API Endpoints
REST API for managing external news items (NewsIt, RSS, etc.)
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query, BackgroundTasks
from uuid import UUID
from typing import Optional
import logging

from core.middleware import get_current_user, get_current_tenant
from core.database import get_database, SupabaseClient
from models.auth import JWTPayload
from models.external_news import (
    ExternalNewsItem,
    ListExternalNewsResponse,
    ExternalNewsDetailResponse,
    RejectNewsRequest,
    PublishToChannelGroupsRequest,
    PublishNewsResponse,
    ExternalNewsPublication
)
from services.external_news_service import get_external_news_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/external-news", tags=["external-news"])


@router.get("/", response_model=ListExternalNewsResponse)
async def list_external_news(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    approval_status: Optional[str] = Query(None, description="Filter by approval status: all, pending, approved, rejected"),
    external_source: Optional[str] = Query(None, description="Filter by source: newsit, rss, etc."),
    is_breaking: Optional[bool] = Query(None, description="Filter by breaking news"),
    district: Optional[str] = Query(None, description="Filter by district name (searches in city_data.name and multilingual_names)"),
    current_user: JWTPayload = Depends(get_current_user),
    db: SupabaseClient = Depends(get_database)
):
    """
    List external news items with pagination and filters

    Requires authentication and filters by current tenant.
    """
    try:
        news_service = get_external_news_service()

        result = await news_service.get_external_news(
            tenant_id=current_user.tenant_id,
            approval_status=approval_status,
            external_source=external_source,
            is_breaking=is_breaking,
            district=district,
            page=page,
            limit=limit
        )

        return ListExternalNewsResponse(
            items=result["items"],
            pagination=result["pagination"]
        )

    except Exception as e:
        logger.error(f"Error listing external news: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch external news"
        )


@router.get("/status-counts")
async def get_status_counts(
    external_source: Optional[str] = Query(None, description="Filter by source: newsit, twitter, facebook, etc."),
    current_user: JWTPayload = Depends(get_current_user)
):
    """
    Get count of news items by approval status

    Returns counts for all, pending, approved, and rejected.
    Optionally filter by external_source to get counts for specific source only.
    """
    try:
        news_service = get_external_news_service()

        counts = await news_service.get_news_status_counts(
            tenant_id=current_user.tenant_id,
            external_source=external_source
        )

        return counts

    except Exception as e:
        logger.error(f"Error getting status counts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get status counts"
        )


@router.get("/{news_id}", response_model=ExternalNewsDetailResponse)
async def get_external_news(
    news_id: UUID,
    current_user: JWTPayload = Depends(get_current_user)
):
    """
    Get single external news item with full details and publication history
    """
    try:
        news_service = get_external_news_service()

        # Get news item
        news_item = await news_service.get_external_news_by_id(
            news_id=news_id,
            tenant_id=current_user.tenant_id
        )

        if not news_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="News item not found"
            )

        # Get publication history
        publications = await news_service.get_publication_history(
            news_id=news_id,
            tenant_id=current_user.tenant_id
        )

        return ExternalNewsDetailResponse(
            news_item=news_item,
            publications=publications
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching news item {news_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch news item"
        )


@router.put("/{news_id}/approve")
async def approve_external_news(
    news_id: UUID,
    current_user: JWTPayload = Depends(get_current_user)
):
    """
    Approve external news item

    Changes approval status to 'approved'.
    Frontend should then show channel group selection popup.
    """
    try:
        news_service = get_external_news_service()

        # Approve the news item
        updated_item = await news_service.approve_news(
            news_id=news_id,
            approved_by=UUID(current_user.sub),
            tenant_id=current_user.tenant_id
        )

        if not updated_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="News item not found"
            )

        logger.info(f"News item {news_id} approved by user {current_user.sub}")

        return {
            "success": True,
            "message": "News item approved successfully",
            "news_item": updated_item
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving news item {news_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve news item"
        )


@router.put("/{news_id}/reject")
async def reject_external_news(
    news_id: UUID,
    rejection_data: RejectNewsRequest,
    current_user: JWTPayload = Depends(get_current_user)
):
    """
    Reject external news item with reason

    Changes approval status to 'rejected'.
    """
    try:
        news_service = get_external_news_service()

        # Reject the news item
        updated_item = await news_service.reject_news(
            news_id=news_id,
            rejected_by=UUID(current_user.sub),
            rejection_reason=rejection_data.rejection_reason,
            tenant_id=current_user.tenant_id
        )

        if not updated_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="News item not found"
            )

        logger.info(f"News item {news_id} rejected by user {current_user.sub}")

        return {
            "success": True,
            "message": "News item rejected",
            "news_item": updated_item
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting news item {news_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject news item"
        )


async def _publish_news_background_task(
    news_id: UUID,
    channel_group_ids: list,
    initiated_by: UUID,
    tenant_id: str,
    selected_language: Optional[str],
    customized_title: Optional[str],
    customized_content: Optional[str],
    create_drafts: bool
):
    """Background task to publish external news to channel groups"""
    try:
        news_service = get_external_news_service()

        result = await news_service.publish_to_channel_groups(
            news_id=news_id,
            channel_group_ids=channel_group_ids,
            initiated_by=initiated_by,
            tenant_id=tenant_id,
            selected_language=selected_language,
            customized_title=customized_title,
            customized_content=customized_content,
            create_drafts=create_drafts
        )

        logger.info(
            f"Background publishing completed for news item {news_id}: "
            f"{result.get('total_successful', 0)}/{result.get('total_attempted', 0)} successful"
        )

    except Exception as e:
        logger.error(f"Background publishing failed for news item {news_id}: {e}", exc_info=True)


@router.post("/{news_id}/publish", status_code=status.HTTP_202_ACCEPTED)
async def publish_to_channel_groups(
    news_id: UUID,
    publish_request: PublishToChannelGroupsRequest,
    background_tasks: BackgroundTasks,
    current_user: JWTPayload = Depends(get_current_user)
):
    """
    Publish approved news to selected channel groups (Background Processing)

    Initiates publishing in the background and returns immediately.
    News item must be in 'approved' status.

    Returns 202 Accepted - Publishing happens asynchronously.
    Check publication history endpoint to track progress.
    """
    try:
        # Validate news item exists and is approved
        news_service = get_external_news_service()
        news_item = await news_service.get_external_news_by_id(
            news_id=news_id,
            tenant_id=current_user.tenant_id
        )

        if not news_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="News item not found"
            )

        if news_item.get('approval_status') != 'approved':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="News item must be approved before publishing"
            )

        # Queue background task
        background_tasks.add_task(
            _publish_news_background_task,
            news_id=news_id,
            channel_group_ids=publish_request.channel_group_ids,
            initiated_by=UUID(current_user.sub),
            tenant_id=current_user.tenant_id,
            selected_language=publish_request.selected_language,
            customized_title=publish_request.customized_title,
            customized_content=publish_request.customized_content,
            create_drafts=publish_request.create_drafts
        )

        logger.info(
            f"Queued background publishing for news item {news_id} to "
            f"{len(publish_request.channel_group_ids)} channel group(s) by user {current_user.sub}"
        )

        return {
            "success": True,
            "message": f"Publishing initiated for {len(publish_request.channel_group_ids)} channel group(s). Check publication history for progress.",
            "publications": [],
            "status": "processing"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating publishing for news item {news_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate publishing"
        )


@router.get("/{news_id}/publications")
async def get_publication_history(
    news_id: UUID,
    current_user: JWTPayload = Depends(get_current_user)
):
    """
    Get publishing history for a news item

    Returns all publication records with status and results.
    """
    try:
        news_service = get_external_news_service()

        publications = await news_service.get_publication_history(
            news_id=news_id,
            tenant_id=current_user.tenant_id
        )

        return {
            "success": True,
            "publications": publications
        }

    except Exception as e:
        logger.error(f"Error fetching publication history for {news_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch publication history"
        )


# Additional utility endpoint for testing/debugging
@router.post("/test-sqs-message")
async def test_sqs_message(
    news_id: str,
    current_user: JWTPayload = Depends(get_current_user)
):
    """
    Test endpoint to manually trigger processing of a NewsIt news item
    (simulates SQS message processing)

    For development/testing only.
    """
    try:
        news_service = get_external_news_service()

        message_data = {
            "news_id": news_id,
            "source": "newsit"
        }

        result = await news_service.process_newsit_message(
            message_data=message_data,
            tenant_id=current_user.tenant_id,
            sqs_message_id=f"test-{news_id}-{current_user.sub}"
        )

        return {
            "success": result.success,
            "news_item_id": str(result.news_item_id) if result.news_item_id else None,
            "external_id": result.external_id,
            "is_duplicate": result.is_duplicate,
            "error_message": result.error_message
        }

    except Exception as e:
        logger.error(f"Error in test SQS message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
