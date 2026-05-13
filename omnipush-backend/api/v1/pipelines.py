from fastapi import APIRouter, HTTPException, status, Depends, Query, BackgroundTasks
from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, Optional, List
import logging
import asyncio

from core.middleware import get_current_user, get_tenant_context, TenantContext
from models.auth import JWTPayload
from models.pipeline import (
    CreatePipelineRequest,
    UpdatePipelineRequest,
    FetchNewsRequest,
    ModerateContentRequest,
    ListPipelinesResponse,
    CreatePipelineResponse,
    UpdatePipelineResponse,
    DeletePipelineResponse,
    ListNewsItemsResponse,
    FetchNewsResponse,
    ModerateContentResponse,
    PipelineStatsResponse,
    Pipeline,
    NewsItem,
    PipelineStatus,
    ModerationStatus,
    ProcessingStep
)
from services.research_service import fetch_news_from_sources
from services.content_service import moderate_content_with_ai, generate_news_card_from_text
from services.news_service import NewsService
from services.social_media_service import publish_to_platforms

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipelines", tags=["content pipelines"])


@router.get("", response_model=ListPipelinesResponse)
async def list_pipelines(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    pipeline_status: Optional[PipelineStatus] = Query(None),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """List pipelines with filtering and pagination"""
    try:
        query = ctx.table('pipelines').select('*', count='exact').eq('tenant_id', ctx.tenant_id)

        if pipeline_status:
            query = query.eq('status', pipeline_status.value)
        
        count_response = query.execute()
        total = count_response.count or 0
        
        offset = (page - 1) * limit
        pipelines_response = query.range(offset, offset + limit - 1).order(
            'created_at', desc=True
        ).execute()
        
        pipelines = []
        for pipeline_data in pipelines_response.data or []:
            pipelines.append(Pipeline(
                id=pipeline_data['id'],
                name=pipeline_data['name'],
                description=pipeline_data.get('description'),
                config=pipeline_data['config'],
                status=PipelineStatus(pipeline_data['status']),
                created_by=pipeline_data['created_by'],
                created_at=datetime.fromisoformat(pipeline_data['created_at']),
                updated_at=datetime.fromisoformat(pipeline_data['updated_at']) if pipeline_data.get('updated_at') else None,
                last_run=datetime.fromisoformat(pipeline_data['last_run']) if pipeline_data.get('last_run') else None,
                total_processed=pipeline_data.get('total_processed', 0)
            ))
        
        return ListPipelinesResponse(
            pipelines=pipelines,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit
            }
        )
        
    except Exception as e:
        logger.exception(f"Failed to list pipelines: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pipelines"
        )


@router.post("", response_model=CreatePipelineResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    request: CreatePipelineRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Create a new content pipeline"""
    try:
        pipeline_id = str(uuid4())
        pipeline_data = {
            'id': pipeline_id,
            'tenant_id': current_user.tenant_id,
            'name': request.name,
            'description': request.description,
            'config': request.config.model_dump(),
            'status': request.status.value,
            'created_by': current_user.sub,
            'created_at': datetime.utcnow().isoformat(),
            'total_processed': 0
        }
        
        result = ctx.db.client.table('pipelines').insert(pipeline_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create pipeline"
            )
        
        return CreatePipelineResponse(
            id=pipeline_id,
            name=request.name,
            status=request.status,
            created_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to create pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create pipeline"
        )


@router.put("/{pipeline_id}", response_model=UpdatePipelineResponse)
async def update_pipeline(
    pipeline_id: str,
    request: UpdatePipelineRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Update a pipeline"""
    try:
        # Check if pipeline exists and user has permission
        pipeline_response = ctx.table('pipelines').select('id, created_by').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', pipeline_id).maybe_single().execute()
        
        if not pipeline_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pipeline not found"
            )
        
        pipeline = pipeline_response.data
        
        # Only creator or admin can edit
        if pipeline['created_by'] != current_user.sub and current_user.role.value != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to edit this pipeline"
            )
        
        # Build update data
        update_data = {'updated_at': datetime.utcnow().isoformat()}
        
        if request.name:
            update_data['name'] = request.name
        if request.description is not None:
            update_data['description'] = request.description
        if request.config:
            update_data['config'] = request.config.model_dump()
        if request.status:
            update_data['status'] = request.status.value
        
        result = ctx.table('pipelines').update(update_data).eq('tenant_id', ctx.tenant_id).eq('id', pipeline_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update pipeline"
            )
        
        updated_pipeline = result.data[0]
        
        return UpdatePipelineResponse(
            id=pipeline_id,
            name=updated_pipeline['name'],
            updated_at=datetime.fromisoformat(updated_pipeline['updated_at'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update pipeline"
        )


@router.delete("/{pipeline_id}", response_model=DeletePipelineResponse)
async def delete_pipeline(
    pipeline_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Delete a pipeline"""
    try:
        # Check if pipeline exists and user has permission
        pipeline_response = ctx.table('pipelines').select('id, created_by').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', pipeline_id).maybe_single().execute()
        
        if not pipeline_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pipeline not found"
            )
        
        pipeline = pipeline_response.data
        
        # Only creator or admin can delete
        if pipeline['created_by'] != current_user.sub and current_user.role.value != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this pipeline"
            )
        
        # Delete pipeline and associated data
        ctx.table('pipelines').delete().eq('tenant_id', ctx.tenant_id).eq('id', pipeline_id).execute()
        ctx.table('external_news_items').delete().eq('pipeline_id', pipeline_id).execute()

        return DeletePipelineResponse()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete pipeline"
        )


@router.post("/{pipeline_id}/fetch-news", response_model=FetchNewsResponse)
async def fetch_news(
    pipeline_id: str,
    request: FetchNewsRequest,
    background_tasks: BackgroundTasks,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Fetch news for a pipeline"""
    try:
        # Get pipeline
        pipeline_response = ctx.table('pipelines').select('*').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', pipeline_id).maybe_single().execute()
        
        if not pipeline_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pipeline not found"
            )
        
        pipeline = pipeline_response.data
        
        if pipeline['status'] != PipelineStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pipeline is not active"
            )
        
        # Create pipeline run record
        run_id = str(uuid4())
        run_data = {
            'id': run_id,
            'pipeline_id': pipeline_id,
            'status': 'running',
            'started_at': datetime.utcnow().isoformat(),
            'items_processed': 0,
            'items_published': 0
        }
        ctx.db.client.table('pipeline_runs').insert(run_data).execute()
        
        # Start background task to fetch and process news
        background_tasks.add_task(
            process_pipeline_news,
            pipeline_id=pipeline_id,
            pipeline_config=pipeline['config'],
            run_id=run_id,
            tenant_id=ctx.tenant_id,
            sources=request.sources
        )
        
        return FetchNewsResponse(
            pipeline_id=pipeline_id,
            items_fetched=0,  # Will be updated by background task
            items_moderated=0,
            items_processed=0,
            run_id=run_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to fetch news: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch news"
        )


@router.post("/{pipeline_id}/parse-social-media", response_model=ListNewsItemsResponse)
async def parse_social_media_json(
    pipeline_id: str,
    json_data: Dict[str, Any],
    city: str = Query("Coimbatore"),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Parse social media JSON data and store as news items"""
    try:
        # Verify pipeline exists and user has access
        pipeline_response = ctx.table('pipelines').select('*').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', pipeline_id).maybe_single().execute()
        
        if not pipeline_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pipeline not found"
            )
        
        pipeline = pipeline_response.data
        
        if pipeline['status'] != PipelineStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pipeline is not active"
            )
        
        # Initialize news service and parse JSON data
        news_service = NewsService()
        articles = news_service.parse_social_media_json(json_data, city=city)
        
        if not articles:
            return ListNewsItemsResponse(
                items=[],
                total=0,
                page=1,
                limit=20
            )
        
        # Store articles in database
        stored_ids = await news_service.store_news_articles(articles, pipeline_id)
        
        # Convert articles to NewsItem format
        items = []
        for article in articles:
            items.append(NewsItem(
                id=str(uuid4()),
                title=article.title,
                content=article.content,
                source=article.source,
                url=article.url,
                published_at=article.published_at.isoformat(),
                category=article.category,
                relevance_score=article.relevance_score,
                moderation_status=ModerationStatus.PENDING,
                created_at=datetime.utcnow().isoformat()
            ))
        
        return ListNewsItemsResponse(
            items=items,
            total=len(items),
            page=1,
            limit=len(items)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to parse social media JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse social media JSON"
        )


@router.get("/{pipeline_id}/news", response_model=ListNewsItemsResponse)
async def list_news_items(
    pipeline_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    moderation_status: Optional[ModerationStatus] = Query(None),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """List news items for a pipeline"""
    try:
        # Verify pipeline exists and user has access
        pipeline_response = ctx.table('pipelines').select('id').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', pipeline_id).maybe_single().execute()
        
        if not pipeline_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pipeline not found"
            )
        
        query = ctx.table('external_news_items').select('*', count='exact').eq('pipeline_id', pipeline_id)

        if moderation_status:
            query = query.eq('moderation_status', moderation_status.value)
        
        count_response = query.execute()
        total = count_response.count or 0
        
        offset = (page - 1) * limit
        items_response = query.range(offset, offset + limit - 1).order(
            'fetched_at', desc=True
        ).execute()
        
        items = []
        for item_data in items_response.data or []:
            items.append(NewsItem(
                id=item_data['id'],
                pipeline_id=item_data['pipeline_id'],
                title=item_data['title'],
                content=item_data['content'],
                source=item_data['source'],
                source_url=item_data.get('source_url'),
                published_at=datetime.fromisoformat(item_data['published_at']) if item_data.get('published_at') else None,
                fetched_at=datetime.fromisoformat(item_data['fetched_at']),
                moderation_status=ModerationStatus(item_data['moderation_status']),
                moderation_score=item_data.get('moderation_score'),
                moderation_flags=item_data.get('moderation_flags'),
                processed_content=item_data.get('processed_content'),
                generated_image_url=item_data.get('generated_image_url'),
                published_channels=item_data.get('published_channels')
            ))
        
        return ListNewsItemsResponse(
            items=items,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to list news items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve news items"
        )


@router.post("/moderate", response_model=ModerateContentResponse)
async def moderate_content(
    request: ModerateContentRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Moderate content using AI"""
    try:
        moderation_result = await moderate_content_with_ai(
            content=request.content,
            source=request.source
        )
        
        return ModerateContentResponse(
            status=moderation_result['status'],
            score=moderation_result['score'],
            flags=moderation_result['flags'],
            approved=moderation_result['approved']
        )
        
    except Exception as e:
        logger.exception(f"Failed to moderate content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to moderate content"
        )


@router.get("/{pipeline_id}/stats", response_model=PipelineStatsResponse)
async def get_pipeline_stats(
    pipeline_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get pipeline statistics"""
    try:
        # Verify pipeline exists
        pipeline_response = ctx.table('pipelines').select('last_run').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', pipeline_id).maybe_single().execute()
        
        if not pipeline_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pipeline not found"
            )
        
        # Get statistics
        total_response = ctx.table('external_news_items').select('id', count='exact').eq('pipeline_id', pipeline_id).execute()
        approved_response = ctx.table('external_news_items').select('id', count='exact').eq('pipeline_id', pipeline_id).eq('moderation_status', ModerationStatus.APPROVED.value).execute()
        rejected_response = ctx.table('external_news_items').select('id', count='exact').eq('pipeline_id', pipeline_id).eq('moderation_status', ModerationStatus.REJECTED.value).execute()
        published_response = ctx.table('external_news_items').select('id', count='exact').eq('pipeline_id', pipeline_id).not_.is_('published_channels', 'null').execute()
        
        total_items = total_response.count or 0
        approved_items = approved_response.count or 0
        rejected_items = rejected_response.count or 0
        published_items = published_response.count or 0
        
        success_rate = (approved_items / total_items * 100) if total_items > 0 else 0
        
        last_run = None
        if pipeline_response.data.get('last_run'):
            last_run = datetime.fromisoformat(pipeline_response.data['last_run'])
        
        return PipelineStatsResponse(
            pipeline_id=pipeline_id,
            total_items=total_items,
            approved_items=approved_items,
            rejected_items=rejected_items,
            published_items=published_items,
            last_run=last_run,
            success_rate=round(success_rate, 2)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get pipeline stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pipeline statistics"
        )


async def process_pipeline_news(
    pipeline_id: str,
    pipeline_config: dict,
    run_id: str,
    tenant_id: str,
    sources: Optional[List[str]] = None
):
    """Background task to process pipeline news"""
    try:
        # Fetch news from configured input channels
        input_channels = pipeline_config.get('input_channels', [])
        processing_steps = pipeline_config.get('processing_steps', [])
        output_channels = pipeline_config.get('output_channels', [])
        moderation_enabled = pipeline_config.get('moderation_enabled', True)
        auto_publish = pipeline_config.get('auto_publish', False)
        
        items_processed = 0
        items_published = 0
        errors = []
        
        for channel in input_channels:
            if channel['type'] != 'input':
                continue
            
            try:
                # Fetch news from this channel
                news_items = await fetch_news_from_sources(
                    source_type=channel['platform'],
                    config=channel['config']
                )
                
                for news_item in news_items:
                    try:
                        # Create news item record
                        item_id = str(uuid4())
                        item_data = {
                            'id': item_id,
                            'pipeline_id': pipeline_id,
                            'title': news_item['title'],
                            'content': news_item['content'],
                            'source': channel['name'],
                            'source_url': news_item.get('url'),
                            'published_at': news_item.get('published_at'),
                            'fetched_at': datetime.utcnow().isoformat(),
                            'moderation_status': ModerationStatus.PENDING.value
                        }
                        
                        # Moderate content if enabled
                        if moderation_enabled:
                            moderation_result = await moderate_content_with_ai(
                                content=news_item['content'],
                                source=channel['name']
                            )
                            
                            item_data.update({
                                'moderation_status': moderation_result['status'].value,
                                'moderation_score': moderation_result['score'],
                                'moderation_flags': moderation_result['flags']
                            })
                            
                            # Skip rejected content
                            if not moderation_result['approved']:
                                continue
                        
                        # Process content based on processing steps
                        processed_content = news_item['content']
                        generated_image_url = None
                        
                        if ProcessingStep.TEXT in processing_steps:
                            # Use original text content
                            processed_content = news_item['content']
                        
                        if ProcessingStep.IMAGE in processing_steps:
                            # Generate image/news card
                            image_result = await generate_news_card_from_text(
                                title=news_item['title'],
                                content=news_item['content'],
                                tenant_id=tenant_id
                            )
                            generated_image_url = image_result.get('url')
                        
                        item_data.update({
                            'processed_content': processed_content,
                            'generated_image_url': generated_image_url
                        })
                        
                        # Save news item
                        # Note: In production, you'd use the database connection here
                        # ctx.db.client.table('external_news_items').insert(item_data).execute()
                        
                        # Auto-publish if enabled
                        if auto_publish and output_channels:
                            published_channels = []
                            for out_channel in output_channels:
                                if out_channel['type'] == 'output':
                                    try:
                                        result = await publish_to_platforms(
                                            content=processed_content,
                                            image_url=generated_image_url,
                                            channels=[out_channel['platform']],
                                            tenant_id=tenant_id
                                        )
                                        if result:
                                            published_channels.append(out_channel['platform'])
                                    except Exception as e:
                                        errors.append(f"Failed to publish to {out_channel['platform']}: {str(e)}")
                            
                            item_data['published_channels'] = published_channels
                            items_published += 1
                        
                        items_processed += 1
                        
                    except Exception as e:
                        errors.append(f"Failed to process news item: {str(e)}")
                        continue
                
            except Exception as e:
                errors.append(f"Failed to fetch from {channel['name']}: {str(e)}")
                continue
        
        # Update pipeline run status
        run_update = {
            'status': 'completed',
            'completed_at': datetime.utcnow().isoformat(),
            'items_processed': items_processed,
            'items_published': items_published,
            'errors': errors if errors else None
        }
        
        # Note: In production, update the pipeline_runs table
        # ctx.db.client.table('pipeline_runs').update(run_update).eq('id', run_id).execute()
        
        # Update pipeline last_run timestamp
        # ctx.table('pipelines').update({
        #     'last_run': datetime.utcnow().isoformat(),
        #     'total_processed': items_processed
        # }).eq('id', pipeline_id).execute()
        
    except Exception as e:
        logger.exception(f"Pipeline processing failed: {e}")
        # Update run status to failed
        # ctx.db.client.table('pipeline_runs').update({
        #     'status': 'failed',
        #     'completed_at': datetime.utcnow().isoformat(),
        #     'errors': [str(e)]
        # }).eq('id', run_id).execute()