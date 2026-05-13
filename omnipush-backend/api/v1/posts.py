from fastapi import APIRouter, HTTPException, status, Depends, Query, UploadFile, File
from datetime import datetime
from uuid import uuid4
from typing import Optional, List
import logging
import openai
import os
import shutil
from pathlib import Path
from core.config import settings
from services.content_service import generate_html_preview, capture_screenshot
from services.social_media_service import publish_to_platforms
from services.s3_service import s3_service

from core.middleware import get_current_user, get_tenant_context, TenantContext
from models.auth import JWTPayload
from models.content import (
    CreatePostRequest,
    UpdatePostRequest,
    SubmitApprovalRequest,
    ReviewPostRequest,
    ListPostsResponse,
    CreatePostResponse,
    UpdatePostResponse,
    DeletePostResponse,
    SubmitApprovalResponse,
    ReviewPostResponse,
    Post,
    PostStatus,
    EnhancePostRequest,
    EnhancePostResponse,
    PreviewPostRequest,
    PreviewPostResponse,
    NewsCardRequest,
    NewsCardResponse,
    PublishPostRequest,
    PublishPostResponse,
    SchedulePostRequest,
    SchedulePostResponse
)
from services.publish_service import PublishService, PublishConfig
from services.channel_groups_service import ChannelGroupsService
from services.social_util import convert_video_for_upload
from services.background_task_service import get_background_task_service
from services.ai_content_service import ai_content_service
from pydantic import BaseModel
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/posts", tags=["content management"])


class PublishNowRequest(BaseModel):
    """Request model for immediate post publishing"""
    post_id: str
    title: str
    content: str
    channel_group_id: Optional[str] = None  # Deprecated: use channel_group_ids
    channel_group_ids: Optional[List[str]] = None  # Support multiple channel groups
    image_url: Optional[str] = None
    media_ids: Optional[List[str]] = None
    mode: Optional[str] = None  # "news_card", "text", or "image"
    headline: Optional[str] = None  # User-provided headline (30-50 chars) for newscard modes
    background_processing: Optional[bool] = True  # Enable background processing by default
    source_image_url: Optional[str] = None  # Original reshare post image for LLM vision analysis (repost flow only)


class PublishNowResponse(BaseModel):
    """Response model for publishing results"""
    success: bool
    error: Optional[str] = None
    channels: Optional[dict] = None
    published_at: Optional[str] = None
    news_card_url: Optional[str] = None
    # Background processing fields
    background_task_id: Optional[str] = None
    processing_status: Optional[str] = None


class MediaUploadResponse(BaseModel):
    """Response model for media upload"""
    success: bool
    media_id: Optional[str] = None
    url: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None


@router.get("", response_model=ListPostsResponse)
async def list_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[PostStatus] = Query(None),
    created_by: Optional[str] = Query(None),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """List posts with filtering and pagination"""
    try:
        try:
            query = ctx.table('posts').select(
                '*, external_news_item:external_news_items(*)',
                count='exact'
            ).eq('tenant_id', ctx.tenant_id)
        except Exception as e:
            logger.warning(f"Failed to join news tables, falling back to basic query: {e}")
            query = ctx.table('posts').select('*', count='exact').eq('tenant_id', ctx.tenant_id)
        
        if status:
            query = query.eq('status', status.value)
        if created_by:
            query = query.eq('created_by', created_by)
        
        # Get total count
        count_response = query.execute()
        total = count_response.count or 0
        
        # Get paginated results
        offset = (page - 1) * limit
        posts_response = query.range(offset, offset + limit - 1).order(
            'created_at', desc=True
        ).execute()
        
        posts = []
        logger.info(f"Retrieved {len(posts_response.data or [])} posts for tenant {ctx.tenant_id}")

        for i, post_data in enumerate(posts_response.data or []):
            logger.debug(f"Processing post {i+1}: {post_data.get('id', 'unknown')} - has news_item: {bool(post_data.get('news_item'))}")
            # Get media information from content.media_ids if they exist
            media_list = []
            post_content = post_data['content'] or {}
            
            if isinstance(post_content, dict) and post_content.get('media_ids'):
                media_ids = post_content.get('media_ids', [])
                if media_ids:
                    try:
                        # Get media files for this post - try both table names
                        try:
                            media_response = ctx.table('media').select(
                                'id, file_name, content_type, file_size'
                            ).in_('id', media_ids).eq('tenant_id', ctx.tenant_id).execute()
                        except Exception:
                            # Try media_assets table as fallback
                            media_response = ctx.table('media_assets').select(
                                'id, file_name, content_type, file_size'
                            ).in_('id', media_ids).eq('tenant_id', ctx.tenant_id).execute()
                        
                        for media in media_response.data or []:
                            media_list.append({
                                'id': media['id'],
                                'file_name': media['file_name'],
                                'content_type': media['content_type'],
                                'file_size': media['file_size'],
                                'url': media.get('file_path') or f"/media/{ctx.tenant_id}/{media['file_name']}"
                            })
                    except Exception as e:
                        logger.warning(f"Failed to fetch media for post {post_data['id']}: {e}")
            
            # Create post content with media
            if isinstance(post_content, dict):
                post_content['media'] = media_list
            else:
                # If content is a string, convert to object format
                post_content = {
                    'text': post_content,
                    'media': media_list
                }
            
            # Parse news_item if present
            news_item = None
            if post_data.get('external_news_item') and isinstance(post_data['external_news_item'], dict):
                try:
                    news_item_data = post_data['external_news_item']
                    from models.content import NewsItem
                    news_item = NewsItem(
                        id=news_item_data['id'],
                        title=news_item_data['title'],
                        content=news_item_data['content'],
                        source=news_item_data['source'],
                        source_url=news_item_data.get('source_url'),
                        url=news_item_data.get('url'),
                        category=news_item_data.get('category'),
                        status=news_item_data.get('status'),
                        is_approved=news_item_data.get('is_approved', False),
                        published_at=datetime.fromisoformat(news_item_data['published_at']) if news_item_data.get('published_at') else None,
                        fetched_at=datetime.fromisoformat(news_item_data['fetched_at']),
                        moderation_status=news_item_data.get('moderation_status'),
                        processed_content=news_item_data.get('processed_content'),
                        generated_image_url=news_item_data.get('generated_image_url'),
                        published_channels=news_item_data.get('published_channels'),
                        created_at=datetime.fromisoformat(news_item_data['created_at'])
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse news_item data: {e}")
                    news_item = None

            posts.append(Post(
                id=post_data['id'],
                title=post_data['title'],
                content=post_content,
                channels=post_data['channels'],
                status=PostStatus(post_data['status']),
                created_by=post_data['created_by'],
                created_at=datetime.fromisoformat(post_data['created_at']),
                updated_at=datetime.fromisoformat(post_data['updated_at']) if post_data.get('updated_at') else None,
                scheduled_at=datetime.fromisoformat(post_data['scheduled_at']) if post_data.get('scheduled_at') else None,
                published_at=datetime.fromisoformat(post_data['published_at']) if post_data.get('published_at') else None,
                news_item_id=post_data.get('news_item_id'),
                news_item=news_item,
                keywords=post_data.get('keywords', []),
                image_search_caption=post_data.get('image_search_caption'),
                publish_results=post_data.get('publish_results')
            ))
        
        return ListPostsResponse(
            posts=posts,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit
            }
        )
        
    except Exception as e:
        logger.exception(f"Failed to list posts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve posts"
        )


@router.get("/social", response_model=ListPostsResponse)
async def list_social_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    approval_status: Optional[str] = Query(None, description="Filter by approval status: pending, approved, rejected, or all"),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """
    List social posts from hit jobs with filtering and pagination.
    Only returns posts that have a news_item_id (posts created from Twitter/social scraping).
    """
    try:
        try:
            query = ctx.table('posts').select(
                '*, external_news_item:external_news_items(*)',
                count='exact'
            ).eq('tenant_id', ctx.tenant_id).not_.is_('external_news_id', 'null')
        except Exception as e:
            logger.warning(f"Failed to join news_items, falling back to basic query: {e}")
            query = ctx.table('posts').select('*', count='exact').eq(
                'tenant_id', ctx.tenant_id
            ).not_.is_('external_news_id', 'null')

        # Filter by approval status if provided
        if approval_status and approval_status != 'all':
            query = query.eq('approval_status', approval_status)

        # Get total count
        count_response = query.execute()
        total = count_response.count or 0

        # Get paginated results
        offset = (page - 1) * limit
        posts_response = query.range(offset, offset + limit - 1).order(
            'created_at', desc=True
        ).execute()

        posts = []
        logger.info(f"Retrieved {len(posts_response.data or [])} social posts for tenant {ctx.tenant_id}")

        for i, post_data in enumerate(posts_response.data or []):
            logger.debug(f"Processing social post {i+1}: {post_data.get('id', 'unknown')}")

            # Get media information
            media_list = []
            post_content = post_data['content'] or {}

            if isinstance(post_content, dict) and post_content.get('media_ids'):
                media_ids = post_content.get('media_ids', [])
                if media_ids:
                    try:
                        try:
                            media_response = ctx.table('media').select(
                                'id, file_name, content_type, file_size'
                            ).in_('id', media_ids).eq('tenant_id', ctx.tenant_id).execute()
                        except Exception:
                            media_response = ctx.table('media_assets').select(
                                'id, file_name, content_type, file_size'
                            ).in_('id', media_ids).eq('tenant_id', ctx.tenant_id).execute()

                        for media in media_response.data or []:
                            media_list.append({
                                'id': media['id'],
                                'file_name': media['file_name'],
                                'content_type': media['content_type'],
                                'file_size': media['file_size'],
                                'url': media.get('file_path') or f"/media/{ctx.tenant_id}/{media['file_name']}"
                            })
                    except Exception as e:
                        logger.warning(f"Failed to fetch media for post {post_data['id']}: {e}")

            # Create post content with media
            if isinstance(post_content, dict):
                post_content['media'] = media_list
            else:
                post_content = {
                    'text': post_content,
                    'media': media_list
                }

            # Parse news_item if present
            news_item = None
            if post_data.get('external_news_item') and isinstance(post_data['external_news_item'], dict):
                try:
                    news_item_data = post_data['external_news_item']
                    from models.content import NewsItem
                    news_item = NewsItem(
                        id=news_item_data['id'],
                        title=news_item_data['title'],
                        content=news_item_data['content'],
                        source=news_item_data['source'],
                        source_url=news_item_data.get('source_url'),
                        published_at=datetime.fromisoformat(news_item_data['published_at']) if news_item_data.get('published_at') else None,
                        fetched_at=datetime.fromisoformat(news_item_data['fetched_at']),
                        moderation_status=news_item_data.get('moderation_status', ''),
                        moderation_score=news_item_data.get('moderation_score'),
                        moderation_flags=news_item_data.get('moderation_flags'),
                        moderation_reason=news_item_data.get('moderation_reason'),
                        processed_content=news_item_data.get('processed_content'),
                        generated_image_url=news_item_data.get('generated_image_url')
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse news_item for post {post_data['id']}: {e}")

            posts.append(Post(
                id=post_data['id'],
                tenant_id=post_data['tenant_id'],
                title=post_data['title'],
                content=post_content,
                channels=post_data['channels'],
                status=PostStatus(post_data['status']),
                created_by=post_data['created_by'],
                created_at=datetime.fromisoformat(post_data['created_at']),
                updated_at=datetime.fromisoformat(post_data['updated_at']) if post_data.get('updated_at') else None,
                scheduled_at=datetime.fromisoformat(post_data['scheduled_at']) if post_data.get('scheduled_at') else None,
                published_at=datetime.fromisoformat(post_data['published_at']) if post_data.get('published_at') else None,
                news_item_id=post_data.get('news_item_id'),
                news_item=news_item,
                keywords=post_data.get('keywords', []),
                image_search_caption=post_data.get('image_search_caption'),
                publish_results=post_data.get('publish_results'),
                approval_status=post_data.get('approval_status', 'pending')
            ))

        return ListPostsResponse(
            posts=posts,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit
            }
        )

    except Exception as e:
        logger.exception(f"Failed to list social posts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve social posts"
        )


@router.post("", response_model=CreatePostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    request: CreatePostRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Create a new post"""
    try:
        # Validate that we have either content text or media
        has_text = request.content and request.content.text and request.content.text.strip()
        has_media = request.content and request.content.media_ids and len(request.content.media_ids) > 0

        if not has_text and not has_media:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Post must have either text content or media attachments"
            )

        # Generate keywords and image search caption if we have text content
        keywords = []
        image_search_caption = None

        if has_text:
            try:
                # Combine title and content for better analysis
                full_content = f"{request.title}\n{request.content.text}" if request.title else request.content.text
                ai_analysis = await ai_content_service.analyze_post_content(full_content)
                keywords = ai_analysis.get('keywords', [])
                image_search_caption = ai_analysis.get('image_search_caption')
                logger.info(f"AI analysis complete - Keywords: {keywords}, Caption: {image_search_caption}")
            except Exception as e:
                logger.warning(f"AI content analysis failed, continuing without keywords/caption: {e}")

        post_id = str(uuid4())
        post_data = {
            'id': post_id,
            'tenant_id': current_user.tenant_id,
            'user_id': current_user.sub,
            'title': request.title,
            'content': request.content.model_dump(),
            'channels': [channel.model_dump() for channel in request.channels],
            'status': PostStatus.DRAFT.value,
            'created_by': current_user.sub,
            'created_at': datetime.utcnow().isoformat(),
            'scheduled_at': request.scheduled_at.isoformat() if request.scheduled_at else None,
            'channel_group_id': request.channel_group_ids[0] if request.channel_group_ids and len(request.channel_group_ids) > 0 else request.channel_group_id,
            'keywords': keywords,
            'image_search_caption': image_search_caption
        }

        result = ctx.db.client.table('posts').insert(post_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create post"
            )
        
        # Media associations are now stored directly in the post content (media_ids)
        
        return CreatePostResponse(
            id=post_id,
            title=request.title,
            status=PostStatus.DRAFT,
            created_by=current_user.sub,
            created_at=datetime.utcnow(),
            keywords=keywords,
            image_search_caption=image_search_caption
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to create post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create post"
        )


@router.put("/{post_id}", response_model=UpdatePostResponse)
async def update_post(
    post_id: str,
    request: UpdatePostRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Update a post"""
    try:
        # Check if post exists and user has permission
        post_response = ctx.table('posts').select('id, created_by, status').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', post_id).maybe_single().execute()
        
        if not post_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        post = post_response.data
        
        # Only creator or admin can edit
        if post['created_by'] != current_user.sub and current_user.role.value != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to edit this post"
            )
        
        # Build update data
        update_data = {'updated_at': datetime.utcnow().isoformat()}

        if request.title:
            update_data['title'] = request.title
        if request.content:
            update_data['content'] = request.content.model_dump()
            # Regenerate keywords and caption if content changed
            if request.content.text and request.content.text.strip():
                try:
                    full_content = f"{request.title or post['title']}\n{request.content.text}"
                    ai_analysis = await ai_content_service.analyze_post_content(full_content)
                    update_data['keywords'] = ai_analysis.get('keywords', [])
                    update_data['image_search_caption'] = ai_analysis.get('image_search_caption')
                    logger.info(f"Updated AI analysis for post {post_id}")
                except Exception as e:
                    logger.warning(f"Failed to update AI analysis for post {post_id}: {e}")
        if request.channels:
            update_data['channels'] = [channel.model_dump() for channel in request.channels]
        if request.scheduled_at:
            update_data['scheduled_at'] = request.scheduled_at.isoformat()
        
        result = ctx.table('posts').update(update_data).eq('tenant_id', ctx.tenant_id).eq('id', post_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update post"
            )
        
        updated_post = result.data[0]
        
        return UpdatePostResponse(
            id=post_id,
            title=updated_post['title'],
            updated_at=datetime.fromisoformat(updated_post['updated_at'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update post"
        )


@router.delete("/{post_id}", response_model=DeletePostResponse)
async def delete_post(
    post_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Delete a post"""
    try:
        # Check if post exists and user has permission
        post_response = ctx.table('posts').select('id, created_by').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', post_id).maybe_single().execute()
        
        if not post_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        post = post_response.data
        
        # Only creator or admin can delete
        if post['created_by'] != current_user.sub and current_user.role.value != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this post"
            )
        
        result = ctx.table('posts').delete().eq('tenant_id', ctx.tenant_id).eq('id', post_id).execute()
        
        return DeletePostResponse()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete post"
        )


@router.post("/enhance", response_model=EnhancePostResponse)
async def enhance_post_content(
    request: EnhancePostRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Enhance post content with AI"""
    try:
        # Validate input
        if not request.text or not request.text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content text is required"
            )
        
        if len(request.text) > 2000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content text is too long (max 2000 characters)"
            )
        
        if settings.openai_api_key:
            try:
                from openai import AsyncOpenAI
                openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
                
                response = await openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a social media content expert. Enhance the given text to make it more engaging, professional, and social-media friendly. Keep the core message but improve the writing style, add relevant emojis if appropriate, and make it more compelling. Keep it concise and under 500 characters."},
                        {"role": "user", "content": request.text}
                    ],
                    max_tokens=500,
                    temperature=0.7
                )
                
                enhanced_text = response.choices[0].message.content.strip()
            except Exception as openai_error:
                logger.warning(f"OpenAI enhancement failed: {openai_error}")
                # Fallback to simple enhancement
                enhanced_text = f"✨ {request.text}"
                if not request.text.endswith(('!', '?', '.')):
                    enhanced_text += "!"
                enhanced_text += " 🚀"
        else:
            # Fallback enhancement without OpenAI
            enhanced_text = f"✨ {request.text}"
            if not request.text.endswith(('!', '?', '.')):
                enhanced_text += "!"
            enhanced_text += " 🚀"
        
        return EnhancePostResponse(enhanced_text=enhanced_text)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to enhance post content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enhance content. Please try again."
        )


@router.post("/preview", response_model=PublishNowResponse, status_code=status.HTTP_201_CREATED)
async def create_preview_post(
    request: CreatePostRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Create a preview post using the publish service in preview mode"""
    try:
        logger.info(f"Preview request for new post by user {current_user.sub}")
        
        # Validate content
        has_text = request.content and request.content.text and request.content.text.strip()
        has_media = request.content and request.content.media_ids and len(request.content.media_ids) > 0
        
        if not has_text and not has_media:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Post must have either text content or media attachments"
            )
        
        # Create the post
        post_id = str(uuid4())
        post_data = {
            'id': post_id,
            'tenant_id': current_user.tenant_id,
            'user_id': current_user.sub,
            'title': request.title,
            'content': request.content.model_dump(),
            'channels': [channel.model_dump() for channel in request.channels],
            'status': PostStatus.DRAFT.value,
            'created_by': current_user.sub,
            'created_at': datetime.utcnow().isoformat(),
            'scheduled_at': request.scheduled_at.isoformat() if request.scheduled_at else None,
            'channel_group_id': request.channel_group_ids[0] if request.channel_group_ids and len(request.channel_group_ids) > 0 else request.channel_group_id
        }

        result = ctx.db.client.table('posts').insert(post_data).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create preview post"
            )

        # Convert to PublishNowRequest format and use existing publish logic with preview_mode
        publish_request = PublishNowRequest(
            post_id=post_id,
            title=request.title,
            content=request.content.text or "",
            channel_group_ids=request.channel_group_ids,
            channel_group_id=request.channel_group_id,
            image_url=None,  # Let the service determine this
            media_ids=request.content.media_ids or [],
            mode="image"
        )
        
        # Use the existing publish_post_now logic but with preview_mode
        # This ensures complete consistency with the actual publish flow
        return await _publish_with_mode(publish_request, current_user, ctx, preview_mode=True)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to create preview post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create preview post"
        )


async def _publish_with_mode(
    request: PublishNowRequest,
    current_user: JWTPayload,
    ctx: TenantContext,
    preview_mode: bool = False
) -> PublishNowResponse:
    """Shared publish logic for both actual publishing and preview"""
    logger.info(f"{'Preview' if preview_mode else 'Publish'} request for post {request.post_id}")
    
    # Initialize services
    channel_groups_service = ChannelGroupsService()
    
    # Get social accounts from channel group
    social_accounts = []
    if request.channel_group_id:
        channel_group = await channel_groups_service.get_channel_group(
            group_id=request.channel_group_id,
            tenant_id=current_user.tenant_id
        )
        
        if not channel_group:
            raise HTTPException(status_code=404, detail="Channel group not found")
        
        social_account_ids = channel_group.get('social_account_ids', [])
        if social_account_ids:
            accounts_response = ctx.table('social_accounts').select(
                'id, platform, account_name, account_id, status, page_id, periskope_id, auto_image_search, access_token'
            ).in_('id', social_account_ids).eq('tenant_id', current_user.tenant_id).execute()
            
            social_accounts = accounts_response.data or []
    
    if not social_accounts:
        return PublishNowResponse(
            success=False,
            error="No social accounts found in the selected channel group"
        )
    
    # Check if we have media files to determine if we should generate newscards
    has_media_files = bool(request.media_ids and len(request.media_ids) > 0)

    # Initialize publish service
    # Disable newscard generation when we have media files (like AI-generated images)
    # Support both single and multiple channel groups (use first for backward compatibility)
    channel_group_ids = request.channel_group_ids or (
        [request.channel_group_id] if request.channel_group_id else []
    )
    first_channel_group = channel_group_ids[0] if channel_group_ids else None

    # Determine if we should generate headlines via LLM
    # Generate only if mode is newscard and headline is NOT provided
    should_include_headline = (
        request.mode in ["news_card", "newscard_with_image"] and
        not request.headline  # Only generate if not provided by user
    )

    publish_config = PublishConfig(
        channels=[],
        publish_text=True,
        publish_image=True,
        generate_news_card=True if request.mode in ["news_card", "newscard_with_image"] else False,  # Don't generate newscards if we have media files
        facebook_access_token=os.getenv("FB_LONG_LIVED_TOKEN") or os.getenv("FACEBOOK_ACCESS_TOKEN"),
        periskope_api_key=os.getenv("PERISKOPE_API_KEY"),
        channel_group_id=first_channel_group,
        social_accounts=social_accounts
    )
    
    publish_service = PublishService(publish_config)
    publish_service.set_db_client(ctx.db)
    
    # Get media URLs
    media_urls = []
    if request.media_ids:
        try:
            media_response = ctx.table('media').select(
                'file_path, file_name'
            ).in_('id', request.media_ids).eq('tenant_id', current_user.tenant_id).execute()
        except Exception:
            try:
                media_response = ctx.table('media_assets').select(
                    'file_path, file_name'
                ).in_('id', request.media_ids).eq('tenant_id', current_user.tenant_id).execute()
            except Exception:
                media_response = None
        
        if media_response:
            for media in media_response.data or []:
                # Use the full file_path from database instead of constructing local path
                # The file_path should contain the full URL (S3 URL or absolute path)
                media_url = media.get('file_path') or f"/media/{current_user.tenant_id}/{media['file_name']}"
                media_urls.append(media_url)
    
    # Use provided image_url or first media URL
    image_url = request.image_url or (media_urls[0] if media_urls else None)
    
    # Determine post mode
    has_text = bool(request.content and request.content.strip())
    has_media = bool(request.media_ids and len(request.media_ids) > 0) or bool(image_url)
    
    if request.mode:
        post_mode = request.mode
    elif has_text and has_media:
        # Default to newscard_with_image when both text and image are present
        post_mode = "newscard_with_image"
    elif has_text and not has_media:
        post_mode = "text"
    elif not has_text and has_media:
        post_mode = "image"
    else:
        post_mode = None

    # Store headline and include_headline flag for publish service
    publish_service._should_include_headline = should_include_headline
    publish_service._provided_headline = request.headline

    # Use PublishService with appropriate mode
    result = await publish_service.publish_post(
        post_id=request.post_id,
        title=request.title,
        content=request.content,
        tenant_id=current_user.tenant_id,
        user_id=current_user.sub,
        image_url=image_url,
        post_mode=post_mode,
        preview_mode=preview_mode
    )
    
    return PublishNowResponse(
        success=result['success'],
        error=result.get('error'),
        channels=result.get('channels'),
        published_at=result.get('published_at') if not preview_mode else None,
        news_card_url=result.get('news_card_url')
    )


@router.post("/html-preview", response_model=PreviewPostResponse)
async def generate_post_html_preview(
    request: PreviewPostRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Generate HTML preview for post"""
    try:
        html = generate_html_preview(request.title, request.content)
        return PreviewPostResponse(html=html)
        
    except Exception as e:
        logger.exception(f"Failed to generate HTML preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate HTML preview"
        )


@router.get("/media", response_model=List[dict])
async def list_media(
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """List all media files for the current tenant"""
    try:
        # Get all media for the tenant - try both table names
        try:
            media_response = ctx.table('media').select(
                'id, file_name, content_type, file_size, created_at'
            ).eq('tenant_id', current_user.tenant_id).order(
                'created_at', desc=True
            ).execute()
        except Exception:
            # Try media_assets table as fallback
            try:
                media_response = ctx.table('media_assets').select(
                    'id, file_name, content_type, file_size, created_at'
                ).eq('tenant_id', current_user.tenant_id).order(
                    'created_at', desc=True
                ).execute()
            except Exception as e:
                logger.exception(f"Failed to query both 'media' and 'media_assets' tables: {e}")
                return []
        
        media_list = []
        for media in media_response.data or []:
            media_list.append({
                'id': media['id'],
                'file_name': media['file_name'],
                'content_type': media['content_type'],
                'file_size': media['file_size'],
                'url': media.get('file_path') or f"/media/{current_user.tenant_id}/{media['file_name']}",
                'created_at': media['created_at']
            })
        
        return media_list
        
    except Exception as e:
        logger.exception(f"Failed to list media: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list media files"
        )


@router.post("/upload-media", response_model=MediaUploadResponse)
async def upload_media(
    files: List[UploadFile] = File(...),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Upload media files for posts to S3"""
    try:
        if len(files) > 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 4 files allowed per upload"
            )
        
        uploaded_files = []
        
        for file in files:
            # Validate file type (support both images and videos)
            if not file.content_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File {file.filename} has unknown content type"
                )
            
            is_image = file.content_type.startswith('image/')
            is_video = file.content_type.startswith('video/')
            
            if not is_image and not is_video:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File {file.filename} must be an image or video file"
                )
            
            # Read file content
            file_content = await file.read()
            original_filename = file.filename
            final_filename = file.filename
            final_content_type = file.content_type
            
            # Convert video to MP4 if it's a video file
            if is_video:
                try:
                    file_content, new_filename, new_content_type = convert_video_for_upload(
                        file_content, file.filename
                    )
                    if new_filename != file.filename:
                        final_filename = new_filename
                        final_content_type = new_content_type
                        logger.info(f"Video converted: {original_filename} -> {final_filename}")
                        
                except RuntimeError as e:
                    logger.warning(f"Video conversion failed for {original_filename}: {e}")
                    logger.warning(f"Proceeding with original video format for {original_filename}")
            
            # Validate file size (10MB for images, 100MB for videos) - after potential conversion
            max_size = 100 * 1024 * 1024 if is_video else 10 * 1024 * 1024
            max_size_label = "100MB" if is_video else "10MB"
            
            if len(file_content) > max_size:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File {final_filename} is too large (max {max_size_label})"
                )
            
            # Generate unique media ID
            media_id = str(uuid4())
            
            try:
                # Upload to S3
                upload_result = await s3_service.upload_file(
                    file_content,
                    final_filename or f"{media_id}.jpg",
                    current_user.tenant_id,
                    media_type="posts",
                    metadata={
                        'uploaded_via': 'posts_endpoint',
                        'media_id': media_id
                    }
                )
                
                file_url = upload_result['url']
                s3_key = upload_result['key']
                
            except Exception as e:
                logger.warning(f"S3 upload failed for {final_filename}, falling back to local: {e}")
                
                # Fallback to local storage
                media_dir = Path("media") / str(current_user.tenant_id)
                media_dir.mkdir(parents=True, exist_ok=True)
                
                file_extension = Path(final_filename or '').suffix or ('.mp4' if is_video else '.jpg')
                filename = f"{media_id}{file_extension}"
                file_path = media_dir / filename
                
                # Save file locally
                with open(file_path, "wb") as buffer:
                    buffer.write(file_content)
                
                file_url = f"/media/{current_user.tenant_id}/{filename}"
                s3_key = None
            
            # Store in database
            media_data = {
                'id': media_id,
                'tenant_id': current_user.tenant_id,
                'file_name': final_filename or f"{media_id}{'.mp4' if is_video else '.jpg'}",
                'content_type': final_content_type,
                'mime_type': final_content_type,
                'media_type': 'video' if is_video else 'image',
                'file_size': len(file_content),
                'file_path': file_url,
                's3_key': s3_key,
                's3_bucket': os.getenv('AWS_S3_BUCKET') if s3_key else None,
                'size': len(file_content),
                'created_at': datetime.utcnow().isoformat()
            }
            
            try:
                ctx.table('media').insert(media_data).execute()
            except Exception as e:
                logger.warning(f"Failed to insert into 'media' table, trying 'media_assets': {e}")
                # Try media_assets table as fallback
                try:
                    ctx.table('media_assets').insert(media_data).execute()
                except Exception as e2:
                    logger.exception(f"Failed to insert into both 'media' and 'media_assets' tables: {e2}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to store media metadata"
                    )
            
            uploaded_files.append({
                'media_id': media_id,
                'url': file_url,
                'filename': final_filename or f"{media_id}{'.mp4' if is_video else '.jpg'}"
            })
        
        return MediaUploadResponse(
            success=True,
            media_id=uploaded_files[0]['media_id'] if uploaded_files else None,
            url=uploaded_files[0]['url'] if uploaded_files else None,
            filename=uploaded_files[0]['filename'] if uploaded_files else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to upload media: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload media files"
        )


@router.post("/news-card", response_model=NewsCardResponse)
async def generate_news_card(
    request: NewsCardRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Generate news card from HTML"""
    try:
        if not request.html or not request.html.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="HTML content is required"
            )
        
        image_info = await capture_screenshot(request.html)
        return NewsCardResponse(
            image_url=image_info["url"],
            filename=image_info["filename"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to generate news card: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate news card. Please try again."
        )


@router.post("/publish-now", response_model=PublishNowResponse)
async def publish_post_now(
    request: PublishNowRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Immediately publish a post to all channels in one or more channel groups"""
    try:
        # Support both single channel_group_id (backward compatibility) and multiple channel_group_ids
        channel_group_ids = request.channel_group_ids or (
            [request.channel_group_id] if request.channel_group_id else []
        )

        # If no channel groups specified, fall back to all tenant channel groups
        if not channel_group_ids:
            cg_resp = ctx.table('channel_groups').select('id').eq(
                'tenant_id', ctx.tenant_id
            ).execute()
            channel_group_ids = [row['id'] for row in (cg_resp.data or [])]

        if not channel_group_ids:
            raise HTTPException(
                status_code=400,
                detail="No channel groups found. Please create a channel group first."
            )

        # Check if background processing is enabled
        if request.background_processing:
            # Get social accounts from all channel groups
            social_accounts = []
            all_account_ids = set()

            channel_groups_service = ChannelGroupsService()
            for channel_group_id in channel_group_ids:
                channel_group = await channel_groups_service.get_channel_group(
                    group_id=channel_group_id,
                    tenant_id=current_user.tenant_id
                )

                if channel_group:
                    social_account_ids = channel_group.get('social_account_ids', [])
                    all_account_ids.update(social_account_ids)

            # Fetch all unique social accounts
            if all_account_ids:
                accounts_response = ctx.table('social_accounts').select(
                    'id, platform, account_name, account_id, status, page_id, periskope_id, auto_image_search, access_token'
                ).in_('id', list(all_account_ids)).eq('tenant_id', current_user.tenant_id).execute()

                social_accounts = accounts_response.data or []

            # Initialize background task service
            background_service = get_background_task_service()
            background_service.set_db_client(ctx.db)

            # Create background task for immediate publishing
            # Use first channel group for backward compatibility with single-group tasks
            task_id = await background_service.create_and_publish_post_task(
                post_id=request.post_id,
                title=request.title,
                content=request.content,
                tenant_id=current_user.tenant_id,
                user_id=current_user.sub,
                channel_group_id=channel_group_ids[0],  # Backward compatibility
                media_ids=request.media_ids,
                image_url=request.image_url,
                post_mode=request.mode,
                headline=request.headline,  # Pass headline to background task
                social_accounts=social_accounts,
                source_image_url=request.source_image_url  # Pass source image for LLM vision
            )

            # Return immediately with task ID
            return PublishNowResponse(
                success=True,
                background_task_id=task_id,
                processing_status="processing",
                channels=None,  # Will be populated when processing completes
                published_at=None  # Will be set when publishing completes
            )
        else:
            # Use synchronous processing (original behavior)
            return await _publish_with_mode(request, current_user, ctx, preview_mode=False)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Manual publish failed for post {request.post_id}: {e}")
        return PublishNowResponse(
            success=False,
            error=str(e)
        )


@router.post("/{post_id}/publish", response_model=PublishPostResponse)
async def publish_post(
    post_id: str,
    request: PublishPostRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Publish post to social media platforms"""
    try:
        # Get post
        post_response = ctx.table('posts').select('*').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', post_id).maybe_single().execute()
        
        if not post_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        post = post_response.data
        
        # Check if user has permission
        if post['created_by'] != current_user.sub and current_user.role.value != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to publish this post"
            )
        
        # Publish to selected channels or all post channels
        from services.social_posting_service import SocialPostingService

        posting_service = SocialPostingService()

        # Get accounts to publish to
        if request.account_ids:
            # Retry specific accounts - validate they exist first
            account_response = ctx.table('social_accounts').select('id, platform, account_name, status').in_(
                'id', request.account_ids
            ).eq('tenant_id', ctx.tenant_id).execute()

            valid_accounts = account_response.data or []
            account_ids = [acc['id'] for acc in valid_accounts]

            # Check if any requested accounts don't exist
            missing_ids = set(request.account_ids) - set(account_ids)
            if missing_ids:
                logger.warning(f"Some account IDs not found for tenant {ctx.tenant_id}: {missing_ids}")

                # If all requested accounts are missing, try fallback to platform-based lookup
                if not account_ids and request.channels:
                    logger.info(f"Falling back to platform-based lookup for channels: {request.channels}")
                    fallback_response = ctx.table('social_accounts').select('id').in_(
                        'platform', request.channels
                    ).eq('tenant_id', ctx.tenant_id).eq('status', 'connected').execute()
                    account_ids = [acc['id'] for acc in (fallback_response.data or [])]

                    if not account_ids:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No active social accounts found for platforms: {request.channels}"
                        )
        else:
            # Publish to all accounts for selected channels
            channels_to_publish = request.channels or [ch['platform'] for ch in post['channels']]
            account_response = ctx.table('social_accounts').select('id').in_('platform', channels_to_publish).eq('tenant_id', ctx.tenant_id).eq('status', 'connected').execute()
            account_ids = [acc['id'] for acc in (account_response.data or [])]

        # Check if we have any accounts to publish to
        if not account_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active social accounts found for publishing"
            )

        # Publish to each account
        results = {}
        for account_id in account_ids:
            result = posting_service.post_to_account(
                account_id=account_id,
                tenant_id=ctx.tenant_id,
                content=post['content']['text'],
                media_url=post.get('news_card_url'),
                media_type='IMAGE'
            )

            # Format result for storage
            platform_key = f"{result.platform}_{account_id}"
            results[platform_key] = {
                'platform': result.platform,
                'account_id': account_id,
                'account_name': getattr(result, 'account_name', None),
                'success': result.error is None,
                'error': result.error,
                'message': result.message,
                'post_id': result.post_id,
                'published_at': datetime.utcnow().isoformat() if result.error is None else None
            }

        # Update or merge publish results
        existing_results = post.get('publish_results') or {}
        existing_results.update(results)

        # Update post status with publish results
        ctx.table('posts').update({
            'status': PostStatus.PUBLISHED.value,
            'published_at': datetime.utcnow().isoformat(),
            'publish_results': existing_results,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('tenant_id', ctx.tenant_id).eq('id', post_id).execute()

        return PublishPostResponse(published_channels=results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to publish post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish post"
        )


@router.post("/{post_id}/schedule", response_model=SchedulePostResponse)
async def schedule_post(
    post_id: str,
    request: SchedulePostRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Schedule post for future publishing"""
    try:
        # Check if post exists and user has permission
        post_response = ctx.table('posts').select('id, created_by').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', post_id).maybe_single().execute()
        
        if not post_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        post = post_response.data
        
        if post['created_by'] != current_user.sub and current_user.role.value != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to schedule this post"
            )
        
        # Validate scheduled time is in the future
        if request.scheduled_at <= datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scheduled time must be in the future"
            )
        
        # Update post with scheduled time and status
        ctx.table('posts').update({
            'scheduled_at': request.scheduled_at.isoformat(),
            'status': PostStatus.SCHEDULED.value,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('tenant_id', ctx.tenant_id).eq('id', post_id).execute()
        
        return SchedulePostResponse(scheduled_at=request.scheduled_at)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to schedule post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule post"
        )


@router.get("/{post_id}/status")
async def get_post_processing_status(
    post_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get the current processing status of a post including background task progress"""
    try:
        # Get background task service
        background_service = get_background_task_service()
        background_service.set_db_client(ctx.db)

        # Get post processing status
        status_info = await background_service.get_post_processing_status(post_id, current_user.tenant_id)

        if status_info:
            return status_info

        # Fallback: Get basic post status from database
        post_response = ctx.table('posts').select(
            'id, status, published_at, news_card_url, metadata, processing_task_id, error_message'
        ).eq('tenant_id', ctx.tenant_id).eq('id', post_id).maybe_single().execute()

        if not post_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )

        post_data = post_response.data
        return {
            "post_id": post_id,
            "status": post_data.get('status'),
            "published_at": post_data.get('published_at'),
            "news_card_url": post_data.get('news_card_url'),
            "processing_task_id": post_data.get('processing_task_id'),
            "error_message": post_data.get('error_message'),
            "metadata": post_data.get('metadata', {})
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get post status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get post status"
        )


@router.get("/background-tasks/{task_id}")
async def get_background_task_status(
    task_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get the status of a specific background task"""
    try:
        background_service = get_background_task_service()
        task_status = background_service.get_task_status(task_id)

        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Background task not found"
            )

        # Verify the task belongs to the current tenant (security check)
        task = background_service.tasks.get(task_id)
        if task and task.data.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this task"
            )

        return task_status

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get background task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task status"
        )


@router.get("/background-tasks")
async def list_background_tasks(
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """List all background tasks for the current tenant"""
    try:
        background_service = get_background_task_service()
        all_tasks = background_service.get_active_tasks()

        # Filter tasks by tenant for security
        tenant_tasks = []
        for task_info in all_tasks:
            task = background_service.tasks.get(task_info["task_id"])
            if task and task.data.get("tenant_id") == current_user.tenant_id:
                tenant_tasks.append(task_info)

        return {
            "tasks": tenant_tasks,
            "statistics": background_service.get_task_statistics()
        }

    except Exception as e:
        logger.exception(f"Failed to list background tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list background tasks"
        )

