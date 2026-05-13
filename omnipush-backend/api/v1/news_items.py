from fastapi import APIRouter, HTTPException, status, Depends, Query
from datetime import datetime
from typing import Optional, List
import logging

from core.middleware import get_current_user, get_tenant_context, TenantContext
from models.auth import JWTPayload
from models.news_item import (
    CreateNewsItemRequest,
    UpdateNewsItemRequest,
    UpdateModerationRequest,
    UpdatePublishedChannelsRequest,
    BulkModerationRequest,
    CreateNewsItemResponse,
    UpdateNewsItemResponse,
    DeleteNewsItemResponse,
    ListNewsItemsResponse,
    SearchNewsItemsResponse,
    NewsItemsStatsResponse,
    BulkModerationResponse,
    NewsItem,
    ModerationStatus,
    NewsItemsFilters
)
from services.news_items_service import NewsItemsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/news-items", tags=["news items"])


@router.post("", response_model=CreateNewsItemResponse)
async def create_news_item(
    request: CreateNewsItemRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Create a new news item"""
    try:
        service = NewsItemsService()
        
        # Set tenant_id from context if not provided
        tenant_id = request.tenant_id or ctx.tenant_id
        
        news_item_data = await service.create_news_item(
            pipeline_id=request.pipeline_id,
            title=request.title,
            content=request.content,
            source=request.source,
            source_url=request.source_url,
            category=request.category,
            published_at=request.published_at,
            url=request.url,
            tenant_id=tenant_id,
            moderation_score=request.moderation_score,
            generated_image_url=request.generated_image_url
        )
        
        news_item = NewsItem(**news_item_data)
        
        return CreateNewsItemResponse(news_item=news_item)
        
    except Exception as e:
        logger.exception(f"Failed to create news item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create news item: {str(e)}"
        )


@router.get("/{news_item_id}", response_model=NewsItem)
async def get_news_item(
    news_item_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get a specific news item by ID"""
    try:
        service = NewsItemsService()
        news_item_data = await service.get_news_item(news_item_id)
        
        if not news_item_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="News item not found"
            )
        
        # Verify tenant access if tenant_id is set
        if news_item_data.get("tenant_id") and news_item_data["tenant_id"] != ctx.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this news item"
            )
        
        return NewsItem(**news_item_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get news item {news_item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get news item: {str(e)}"
        )


@router.get("", response_model=ListNewsItemsResponse)
async def list_news_items(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    pipeline_id: Optional[str] = Query(None),
    item_status: Optional[str] = Query(None, alias="status"),
    moderation_status: Optional[ModerationStatus] = Query(None),
    category: Optional[str] = Query(None),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """List news items with filtering and pagination"""
    try:
        service = NewsItemsService()
        offset = (page - 1) * limit

        if pipeline_id:
            items = await service.get_news_items_by_pipeline(
                pipeline_id=pipeline_id,
                status=item_status,
                moderation_status=moderation_status,
                limit=limit,
                offset=offset
            )
        else:
            items = await service.get_news_items_by_tenant(
                tenant_id=ctx.tenant_id,
                status=item_status,
                moderation_status=moderation_status,
                category=category,
                limit=limit,
                offset=offset
            )
        
        news_items = [NewsItem(**item) for item in items]
        
        # Calculate pagination info (simplified - would need total count for accurate pagination)
        total_items = len(news_items)
        total_pages = max(1, (total_items + limit - 1) // limit)
        
        return ListNewsItemsResponse(
            items=news_items,
            pagination={
                "page": page,
                "limit": limit,
                "total": total_items,
                "total_pages": total_pages
            }
        )
        
    except Exception as e:
        logger.exception(f"Failed to list news items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list news items: {str(e)}"
        )


@router.put("/{news_item_id}", response_model=UpdateNewsItemResponse)
async def update_news_item(
    news_item_id: str,
    request: UpdateNewsItemRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Update a news item"""
    try:
        service = NewsItemsService()
        
        # Verify news item exists and user has access
        existing_item = await service.get_news_item(news_item_id)
        if not existing_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="News item not found"
            )
        
        if existing_item.get("tenant_id") and existing_item["tenant_id"] != ctx.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this news item"
            )
        
        # Convert request to dict and remove None values
        updates = request.dict(exclude_unset=True)
        
        updated_item = await service.update_news_item(news_item_id, updates)
        
        if not updated_item:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update news item"
            )
        
        news_item = NewsItem(**updated_item)
        
        return UpdateNewsItemResponse(news_item=news_item)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update news item {news_item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update news item: {str(e)}"
        )


@router.patch("/{news_item_id}/moderation", response_model=UpdateNewsItemResponse)
async def update_moderation_status(
    news_item_id: str,
    request: UpdateModerationRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Update moderation status of a news item"""
    try:
        service = NewsItemsService()
        
        # Verify news item exists and user has access
        existing_item = await service.get_news_item(news_item_id)
        if not existing_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="News item not found"
            )
        
        if existing_item.get("tenant_id") and existing_item["tenant_id"] != ctx.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this news item"
            )
        
        updated_item = await service.update_moderation_status(
            news_item_id=news_item_id,
            moderation_status=request.moderation_status,
            moderation_score=request.moderation_score,
            moderation_flags=request.moderation_flags,
            moderation_reason=request.moderation_reason,
            processed_content=request.processed_content,
            is_approved=request.is_approved
        )
        
        if not updated_item:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update moderation status"
            )
        
        news_item = NewsItem(**updated_item)
        
        return UpdateNewsItemResponse(news_item=news_item)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update moderation status for {news_item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update moderation status: {str(e)}"
        )


@router.patch("/{news_item_id}/published-channels", response_model=UpdateNewsItemResponse)
async def update_published_channels(
    news_item_id: str,
    request: UpdatePublishedChannelsRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Update published channels for a news item"""
    try:
        service = NewsItemsService()
        
        # Verify news item exists and user has access
        existing_item = await service.get_news_item(news_item_id)
        if not existing_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="News item not found"
            )
        
        if existing_item.get("tenant_id") and existing_item["tenant_id"] != ctx.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this news item"
            )
        
        updated_item = await service.update_published_channels(
            news_item_id=news_item_id,
            channels=request.channels
        )
        
        if not updated_item:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update published channels"
            )
        
        news_item = NewsItem(**updated_item)
        
        return UpdateNewsItemResponse(news_item=news_item)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update published channels for {news_item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update published channels: {str(e)}"
        )


@router.delete("/{news_item_id}", response_model=DeleteNewsItemResponse)
async def delete_news_item(
    news_item_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Delete a news item"""
    try:
        service = NewsItemsService()
        
        # Verify news item exists and user has access
        existing_item = await service.get_news_item(news_item_id)
        if not existing_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="News item not found"
            )
        
        if existing_item.get("tenant_id") and existing_item["tenant_id"] != ctx.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this news item"
            )
        
        success = await service.delete_news_item(news_item_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete news item"
            )
        
        return DeleteNewsItemResponse(success=True, deleted_id=news_item_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete news item {news_item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete news item: {str(e)}"
        )


@router.get("/pending/moderation", response_model=ListNewsItemsResponse)
async def get_pending_moderation_items(
    pipeline_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get news items pending moderation"""
    try:
        service = NewsItemsService()
        
        items = await service.get_pending_moderation_items(
            pipeline_id=pipeline_id,
            tenant_id=ctx.tenant_id,
            limit=limit
        )
        
        news_items = [NewsItem(**item) for item in items]
        
        return ListNewsItemsResponse(
            items=news_items,
            pagination={
                "page": 1,
                "limit": limit,
                "total": len(news_items),
                "total_pages": 1
            }
        )
        
    except Exception as e:
        logger.exception(f"Failed to get pending moderation items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending moderation items: {str(e)}"
        )


@router.get("/approved/items", response_model=ListNewsItemsResponse)
async def get_approved_items(
    pipeline_id: Optional[str] = Query(None),
    unpublished_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get approved news items"""
    try:
        service = NewsItemsService()
        
        items = await service.get_approved_items(
            pipeline_id=pipeline_id,
            tenant_id=ctx.tenant_id,
            unpublished_only=unpublished_only,
            limit=limit
        )
        
        news_items = [NewsItem(**item) for item in items]
        
        return ListNewsItemsResponse(
            items=news_items,
            pagination={
                "page": 1,
                "limit": limit,
                "total": len(news_items),
                "total_pages": 1
            }
        )
        
    except Exception as e:
        logger.exception(f"Failed to get approved items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get approved items: {str(e)}"
        )


@router.get("/search/{search_term}", response_model=SearchNewsItemsResponse)
async def search_news_items(
    search_term: str,
    pipeline_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Search news items by title or content"""
    try:
        service = NewsItemsService()
        
        items = await service.search_news_items(
            search_term=search_term,
            pipeline_id=pipeline_id,
            tenant_id=ctx.tenant_id,
            limit=limit
        )
        
        news_items = [NewsItem(**item) for item in items]
        
        return SearchNewsItemsResponse(
            items=news_items,
            total_results=len(news_items)
        )
        
    except Exception as e:
        logger.exception(f"Failed to search news items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search news items: {str(e)}"
        )


@router.get("/stats/summary", response_model=NewsItemsStatsResponse)
async def get_news_items_stats(
    pipeline_id: Optional[str] = Query(None),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get statistics for news items"""
    try:
        service = NewsItemsService()
        
        stats = await service.get_news_items_stats(
            pipeline_id=pipeline_id,
            tenant_id=ctx.tenant_id
        )
        
        return NewsItemsStatsResponse(stats=stats)
        
    except Exception as e:
        logger.exception(f"Failed to get news items stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get news items stats: {str(e)}"
        )


@router.patch("/bulk/moderation", response_model=BulkModerationResponse)
async def bulk_update_moderation(
    request: BulkModerationRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Bulk update moderation status for multiple news items"""
    try:
        service = NewsItemsService()
        
        updated_ids = await service.bulk_update_moderation_status(
            news_item_ids=request.news_item_ids,
            moderation_status=request.moderation_status,
            is_approved=request.is_approved
        )
        
        return BulkModerationResponse(
            updated_count=len(updated_ids),
            total_requested=len(request.news_item_ids),
            updated_ids=updated_ids
        )
        
    except Exception as e:
        logger.exception(f"Failed to bulk update moderation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk update moderation: {str(e)}"
        )