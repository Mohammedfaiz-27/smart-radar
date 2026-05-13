"""
Post Drafts API Endpoints
REST API for managing LLM-generated content drafts in the approval workflow
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query, BackgroundTasks
from uuid import UUID
from typing import Optional
import logging

from core.middleware import get_current_user, get_current_tenant
from core.database import get_database, SupabaseClient
from models.auth import JWTPayload
from models.drafts import (
    DraftListResponse,
    DraftDetailResponse,
    ApproveDraftRequest,
    RejectDraftRequest,
    PublishDraftRequest,
    DraftActionResponse,
    DraftStatsResponse,
    DraftWithDetails
)
from services.draft_service import get_draft_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/drafts", tags=["drafts"])


@router.get("/pending", response_model=DraftListResponse)
async def list_pending_drafts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query("PENDING_REVIEW", description="Filter by status"),
    external_news_id: Optional[UUID] = Query(None, description="Filter by external news ID"),
    post_id: Optional[UUID] = Query(None, description="Filter by post ID"),
    current_user: JWTPayload = Depends(get_current_user),
    db: SupabaseClient = Depends(get_database)
):
    """
    List drafts with pagination and filters
    Defaults to PENDING_REVIEW status

    Requires authentication and filters by current tenant.
    """
    try:
        draft_service = get_draft_service()
        draft_service.db = db

        result = await draft_service.get_pending_drafts(
            tenant_id=current_user.tenant_id,
            page=page,
            limit=limit,
            status=status,
            external_news_id=external_news_id,
            post_id=post_id
        )

        return DraftListResponse(
            items=result["items"],
            pagination=result["pagination"]
        )

    except Exception as e:
        logger.error(f"Error listing drafts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch drafts"
        )


@router.get("/stats", response_model=DraftStatsResponse)
async def get_draft_stats(
    external_news_id: Optional[UUID] = Query(None, description="Filter by external news ID"),
    post_id: Optional[UUID] = Query(None, description="Filter by post ID"),
    current_user: JWTPayload = Depends(get_current_user)
):
    """
    Get count of drafts by status

    Returns counts for all statuses.
    Optionally filter by external_news_id or post_id.
    """
    try:
        draft_service = get_draft_service()

        stats = await draft_service.get_draft_stats(
            tenant_id=current_user.tenant_id,
            external_news_id=external_news_id,
            post_id=post_id
        )

        return DraftStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting draft stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get draft stats"
        )


@router.get("/{draft_id}", response_model=DraftDetailResponse)
async def get_draft(
    draft_id: UUID,
    current_user: JWTPayload = Depends(get_current_user)
):
    """
    Get single draft with full details
    """
    try:
        draft_service = get_draft_service()

        # Get draft
        draft = await draft_service.get_draft_by_id(
            draft_id=draft_id,
            tenant_id=current_user.tenant_id
        )

        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found"
            )

        return DraftDetailResponse(draft=draft)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching draft {draft_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch draft"
        )


@router.put("/{draft_id}", response_model=DraftActionResponse)
async def update_draft(
    draft_id: UUID,
    update_data: ApproveDraftRequest,
    current_user: JWTPayload = Depends(get_current_user)
):
    """
    Update draft content without changing status

    Only updates the final_* fields without approving the draft.
    Status remains PENDING_REVIEW.
    """
    try:
        draft_service = get_draft_service()

        # Update the draft fields without changing status
        success, updated_draft, error_msg = await draft_service.update_draft(
            draft_id=draft_id,
            tenant_id=current_user.tenant_id,
            final_content=update_data.final_content,
            final_headline=update_data.final_headline,
            final_district=update_data.final_district,
            final_hashtags=update_data.final_hashtags
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Failed to update draft"
            )

        logger.info(f"Draft {draft_id} updated by user {current_user.sub}")

        return DraftActionResponse(
            success=True,
            message="Draft updated successfully",
            draft=updated_draft
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating draft {draft_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update draft"
        )


@router.put("/{draft_id}/approve", response_model=DraftActionResponse)
async def approve_draft(
    draft_id: UUID,
    approval_data: ApproveDraftRequest,
    current_user: JWTPayload = Depends(get_current_user)
):
    """
    Approve draft with optional content edits

    Updates status to APPROVED and saves edited final_* fields.
    Frontend should then call POST /{draft_id}/publish to publish.
    """
    try:
        draft_service = get_draft_service()

        # Approve the draft
        success, updated_draft, error_msg = await draft_service.approve_draft(
            draft_id=draft_id,
            tenant_id=current_user.tenant_id,
            approved_by=UUID(current_user.sub),
            final_content=approval_data.final_content,
            final_headline=approval_data.final_headline,
            final_district=approval_data.final_district,
            final_hashtags=approval_data.final_hashtags
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Failed to approve draft"
            )

        logger.info(f"Draft {draft_id} approved by user {current_user.sub}")

        return DraftActionResponse(
            success=True,
            message="Draft approved successfully",
            draft=updated_draft
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving draft {draft_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve draft"
        )


@router.put("/{draft_id}/reject", response_model=DraftActionResponse)
async def reject_draft(
    draft_id: UUID,
    rejection_data: RejectDraftRequest,
    current_user: JWTPayload = Depends(get_current_user)
):
    """
    Reject draft with optional reason

    Updates status to REJECTED.
    """
    try:
        draft_service = get_draft_service()

        # Reject the draft
        success, updated_draft, error_msg = await draft_service.reject_draft(
            draft_id=draft_id,
            tenant_id=current_user.tenant_id,
            rejected_by=UUID(current_user.sub),
            rejection_reason=rejection_data.rejection_reason
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Failed to reject draft"
            )

        logger.info(f"Draft {draft_id} rejected by user {current_user.sub}")

        return DraftActionResponse(
            success=True,
            message="Draft rejected successfully",
            draft=updated_draft
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting draft {draft_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject draft"
        )


@router.post("/{draft_id}/publish", response_model=DraftActionResponse)
async def publish_draft(
    draft_id: UUID,
    publish_data: PublishDraftRequest,
    background_tasks: BackgroundTasks,
    current_user: JWTPayload = Depends(get_current_user)
):
    """
    Publish an approved draft to social media

    Draft must be in APPROVED status.
    Publishing happens in background, returns immediately.
    """
    try:
        draft_service = get_draft_service()

        # Validate draft is approved
        draft = await draft_service.get_draft_by_id(draft_id, current_user.tenant_id)
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found"
            )

        if draft['status'] != 'APPROVED':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Draft must be APPROVED to publish (current status: {draft['status']})"
            )

        # Publish in background
        async def publish_task():
            success, publish_result, error_msg = await draft_service.publish_approved_draft(
                draft_id=draft_id,
                tenant_id=current_user.tenant_id,
                newscard_url=publish_data.newscard_url
            )

            if not success:
                logger.error(f"Background publishing failed for draft {draft_id}: {error_msg}")
            else:
                logger.info(f"Background publishing completed for draft {draft_id}")

        background_tasks.add_task(publish_task)

        logger.info(f"Draft {draft_id} queued for publishing")

        return DraftActionResponse(
            success=True,
            message="Draft queued for publishing",
            draft=draft
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing draft {draft_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish draft"
        )


@router.post("/bulk-approve", response_model=DraftActionResponse)
async def bulk_approve_drafts(
    draft_ids: list[UUID],
    current_user: JWTPayload = Depends(get_current_user)
):
    """
    Approve multiple drafts at once

    Useful for approving all drafts for a single post/news item.
    """
    try:
        draft_service = get_draft_service()

        approved_count = 0
        failed_count = 0
        errors = []

        for draft_id in draft_ids:
            success, _, error_msg = await draft_service.approve_draft(
                draft_id=draft_id,
                tenant_id=current_user.tenant_id,
                approved_by=UUID(current_user.sub)
            )

            if success:
                approved_count += 1
            else:
                failed_count += 1
                errors.append(f"{draft_id}: {error_msg}")

        logger.info(f"Bulk approved {approved_count}/{len(draft_ids)} drafts by user {current_user.sub}")

        return DraftActionResponse(
            success=approved_count > 0,
            message=f"Approved {approved_count} drafts, {failed_count} failed",
            draft=None
        )

    except Exception as e:
        logger.error(f"Error bulk approving drafts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk approve drafts"
        )
