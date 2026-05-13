from fastapi import APIRouter, HTTPException, status, Depends, Query, UploadFile, File, Form
from datetime import datetime
from uuid import uuid4
from typing import Optional, List
import logging
try:
    import magic
    _MAGIC_AVAILABLE = True
except ImportError:
    _MAGIC_AVAILABLE = False
from PIL import Image
import io
import os
import requests
# from serpapi import GoogleSearch
# from serpapi.google_search import GoogleSearch  # Now using image_search_service instead
from pydantic import BaseModel

from core.middleware import get_current_user, get_tenant_context, TenantContext
from core.config import settings
from models.auth import JWTPayload
from services.s3_service import s3_service
from services.social_util import convert_video_for_upload
from models.media import (
    UpdateMediaRequest,
    GenerateAIImageRequest,
    ListMediaResponse,
    UploadMediaResponse,
    GenerateAIImageResponse,
    UpdateMediaResponse,
    DeleteMediaResponse,
    Media,
    MediaType,
    MediaMetadata,
    AIImageStyle,
    AIImageSize,
    SearchImagesRequest,
    SearchImagesResponse,
    SearchImageResult
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/media", tags=["media management"])


def get_media_type(filename: str, content_type: str) -> MediaType:
    """Determine media type from filename and content type"""
    if content_type.startswith('image/'):
        return MediaType.IMAGE
    elif content_type.startswith('video/'):
        return MediaType.VIDEO
    elif content_type in ['application/pdf']:
        return MediaType.DOCUMENT
    else:
        # Fallback to extension-based detection
        ext = filename.lower().split('.')[-1]
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            return MediaType.IMAGE
        elif ext in ['mp4', 'mov', 'avi', 'mkv']:
            return MediaType.VIDEO
        else:
            return MediaType.DOCUMENT


def get_image_metadata(file_content: bytes) -> Optional[MediaMetadata]:
    """Extract metadata from image content"""
    try:
        image = Image.open(io.BytesIO(file_content))
        return MediaMetadata(
            width=image.width,
            height=image.height,
            format=image.format.lower() if image.format else None
        )
    except Exception as e:
        logger.warning(f"Failed to extract image metadata: {e}")
        return None


async def save_file_to_storage(
    file_content: bytes,
    filename: str,
    tenant_id: str,
    media_id: str
) -> tuple[str, str]:
    """
    Save file to S3 storage and return URLs
    """
    try:
        # Upload original file to S3
        upload_result = await s3_service.upload_file(
            file_content, 
            filename, 
            tenant_id, 
            media_type="media",
            metadata={
                'media_id': media_id,
                'original_filename': filename
            }
        )
        
        file_url = upload_result['url']
        thumbnail_url = None
        
        # Generate thumbnail for images and videos
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            try:
                image = Image.open(io.BytesIO(file_content))
                image.thumbnail((300, 300))
                
                # Save thumbnail to bytes
                thumbnail_buffer = io.BytesIO()
                image.save(thumbnail_buffer, format='JPEG')
                thumbnail_content = thumbnail_buffer.getvalue()
                
                # Upload thumbnail to S3
                thumb_filename = f"thumb_{filename.rsplit('.', 1)[0]}.jpg"
                thumbnail_result = await s3_service.upload_file(
                    thumbnail_content,
                    thumb_filename,
                    tenant_id,
                    media_type="thumbnails",
                    metadata={
                        'media_id': media_id,
                        'original_filename': filename,
                        'thumbnail_type': 'auto_generated'
                    }
                )
                thumbnail_url = thumbnail_result['url']
                
            except Exception as e:
                logger.warning(f"Failed to generate image thumbnail: {e}")
                
        elif filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            try:
                # Generate a placeholder thumbnail for videos
                # In production, you'd use FFmpeg to extract a frame from the video
                # For now, create a video placeholder thumbnail
                thumbnail_image = Image.new('RGB', (300, 300), color=(60, 60, 60))
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(thumbnail_image)
                
                # Add video icon and filename
                try:
                    draw.text((50, 120), "VIDEO", fill=(255, 255, 255), align="center")
                    draw.text((50, 150), filename[:20], fill=(200, 200, 200), align="center")
                except:
                    pass  # Skip text if font issues
                
                # Save thumbnail to bytes
                thumbnail_buffer = io.BytesIO()
                thumbnail_image.save(thumbnail_buffer, format='JPEG')
                thumbnail_content = thumbnail_buffer.getvalue()
                
                # Upload thumbnail to S3
                thumb_filename = f"thumb_{filename.rsplit('.', 1)[0]}.jpg"
                thumbnail_result = await s3_service.upload_file(
                    thumbnail_content,
                    thumb_filename,
                    tenant_id,
                    media_type="thumbnails",
                    metadata={
                        'media_id': media_id,
                        'original_filename': filename,
                        'thumbnail_type': 'video_placeholder'
                    }
                )
                thumbnail_url = thumbnail_result['url']
                
            except Exception as e:
                logger.warning(f"Failed to generate video thumbnail: {e}")
        
        return file_url, thumbnail_url
        
    except Exception as e:
        logger.exception(f"Failed to upload to S3: {e}")
        raise RuntimeError(f"File storage failed: {e}")


@router.get("", response_model=ListMediaResponse)
async def list_media(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[MediaType] = Query(None),
    search: Optional[str] = Query(None),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """List media files with filtering and pagination"""
    try:
        # Build query with tenant filter
        query = ctx.table('media').select('*', count='exact').eq('tenant_id', ctx.tenant_id)
        
        if type:
            query = query.eq('type', type.value)
        
        if search:
            # Search in filename, description, and tags
            query = query.or_(
                f'file_name.ilike.%{search}%,'
                f'description.ilike.%{search}%,'
                f'tags.cs.{{{search}}}'
            )
        
        # Get total count
        count_response = query.execute()
        total = count_response.count or 0
        
        # Get paginated results
        offset = (page - 1) * limit
        media_response = query.range(offset, offset + limit - 1).order(
            'created_at', desc=True
        ).execute()
        
        media_list = []
        for media_data in media_response.data or []:
            # Handle both 'size' and 'file_size' fields for backward compatibility
            file_size = media_data.get('size') or media_data.get('file_size')
            
            # Determine media type from content_type or media_type
            media_type = None
            if media_data.get('media_type'):
                try:
                    media_type = MediaType(media_data['media_type'])
                except:
                    pass
            elif media_data.get('content_type'):
                if media_data['content_type'].startswith('image/'):
                    media_type = MediaType.IMAGE
                elif media_data['content_type'].startswith('video/'):
                    media_type = MediaType.VIDEO
                else:
                    media_type = MediaType.DOCUMENT
            
            # Build thumbnail URL from S3 key if available
            thumbnail_url = None
            if media_data.get('thumbnail_s3_key'):
                # Construct thumbnail URL from S3 key
                bucket = media_data.get('s3_bucket', 'omnipush-media')
                thumbnail_url = f"https://{bucket}.s3.amazonaws.com/{media_data['thumbnail_s3_key']}"
            
            media_list.append(Media(
                id=media_data['id'],
                filename=media_data['file_name'],
                type=media_type,
                size=file_size,
                url=media_data['file_path'],
                thumbnail_url=thumbnail_url,
                metadata=MediaMetadata(**media_data['metadata']) if media_data.get('metadata') else None,
                created_at=datetime.fromisoformat(media_data['created_at'])
            ))
        
        return ListMediaResponse(
            media=media_list,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit
            }
        )
        
    except Exception as e:
        logger.exception(f"Failed to list media: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve media"
        )


@router.post("/upload", response_model=UploadMediaResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None),  # JSON string array
    description: Optional[str] = Form(None),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Upload a media file"""
    try:
        # Validate file type
        if file.content_type not in settings.allowed_file_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file.content_type} not allowed"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Validate file size
        if len(file_content) > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large"
            )
        
        # Convert video to MP4 if it's a video file
        original_filename = file.filename
        final_filename = file.filename
        final_content_type = file.content_type
        
        try:
            file_content, new_filename, new_content_type = convert_video_for_upload(
                file_content, file.filename
            )
            if new_content_type:
                final_filename = new_filename
                final_content_type = new_content_type
                
        except RuntimeError as e:
            logger.warning(f"Video conversion failed for {original_filename}: {e}")
            logger.warning(f"Proceeding with original video format for {original_filename}")
        
        # Re-validate file size after potential conversion
        if len(file_content) > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large after processing"
            )
        
        # Validate actual file type using python-magic if available
        if _MAGIC_AVAILABLE:
            detected_type = magic.from_buffer(file_content, mime=True)
            if detected_type not in settings.allowed_file_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File content does not match extension"
                )
        
        media_id = str(uuid4())
        media_type = get_media_type(final_filename, final_content_type)
        
        # Extract metadata
        metadata = None
        if media_type == MediaType.IMAGE:
            metadata = get_image_metadata(file_content)
        
        # Save file to S3 storage
        file_url, thumbnail_url = await save_file_to_storage(
            file_content, final_filename, current_user.tenant_id, media_id
        )
        
        # Parse tags
        parsed_tags = []
        if tags:
            try:
                import json
                parsed_tags = json.loads(tags)
            except:
                parsed_tags = [tag.strip() for tag in tags.split(',')]
        
        # Extract S3 keys from URLs for database storage
        s3_key = None
        thumbnail_s3_key = None
        
        if 'amazonaws.com' in file_url:
            s3_key = file_url.split('.com/')[-1]
        if thumbnail_url and 'amazonaws.com' in thumbnail_url:
            thumbnail_s3_key = thumbnail_url.split('.com/')[-1]

        # Save to database
        media_data = {
            'id': media_id,
            'tenant_id': current_user.tenant_id,
            'file_name': final_filename,
            'file_path': file_url,
            'file_size': len(file_content),
            'mime_type': final_content_type,
            'content_type': final_content_type,
            'media_type': media_type.value,
            's3_key': s3_key,
            's3_bucket': 'omnipush-media' if s3_key else None,
            'thumbnail_s3_key': thumbnail_s3_key,
            'metadata': metadata.model_dump() if metadata else None,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Size is already included in file_size, remove this duplicate
        # (keeping for backward compatibility if needed)
        try:
            media_data['size'] = len(file_content)
        except Exception:
            pass
        
        result = ctx.db.client.table('media').insert(media_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save media record"
            )
        
        
        return UploadMediaResponse(
            id=media_id,
            filename=final_filename,
            type=media_type,
            size=len(file_content),
            url=file_url,
            thumbnail_url=thumbnail_url,
            uploaded_by=current_user.sub,
            created_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to upload media: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )


@router.post("/generate-ai", response_model=GenerateAIImageResponse, status_code=status.HTTP_201_CREATED)
async def generate_ai_image(
    request: GenerateAIImageRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Generate AI image using OpenAI DALL-E or similar service"""
    try:
        # Check AI usage limits (this would integrate with subscription management)
        # For demo, we'll skip this check
        
        # Generate image using AI service
        # This is a placeholder - in production you'd integrate with OpenAI DALL-E
        # or other AI image generation services
        
        # For demo, create a placeholder response
        media_id = str(uuid4())
        filename = f"ai-generated-{media_id}.jpg"
        
        # In production, you would:
        # 1. Call OpenAI DALL-E API with the prompt
        # 2. Download the generated image
        # 3. Save it to storage
        # 4. Extract metadata
        
        # Generate placeholder image and upload to S3
        # For now, create a simple colored rectangle as placeholder
        from PIL import Image, ImageDraw, ImageFont
        
        # Create placeholder image
        width, height = map(int, request.size.value.split('x'))
        image = Image.new('RGB', (width, height), color=(100, 150, 200))
        draw = ImageDraw.Draw(image)
        
        # Add text overlay (simple version)
        text = f"AI Generated: {request.prompt[:50]}..."
        try:
            draw.text((20, height//2), text, fill=(255, 255, 255))
        except:
            pass  # Skip text if font issues
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='JPEG')
        img_content = img_buffer.getvalue()
        
        # Upload to S3
        upload_result = await s3_service.upload_file(
            img_content,
            filename,
            current_user.tenant_id,
            media_type="ai_generated",
            metadata={
                'generation_prompt': request.prompt,
                'style': request.style.value,
                'size': request.size.value
            }
        )
        
        mock_url = upload_result['url']
        
        # Extract S3 key for database storage
        s3_key = upload_result['key'] if 'amazonaws.com' in mock_url else None
        
        # Save to database
        media_data = {
            'id': media_id,
            'tenant_id': current_user.tenant_id,
            'file_name': filename,
            'file_path': mock_url,
            'file_size': upload_result['size'],
            'mime_type': 'image/jpeg',
            'content_type': 'image/jpeg',
            'media_type': MediaType.IMAGE.value,
            's3_key': s3_key,
            's3_bucket': 'omnipush-media' if s3_key else None,
            'generation_prompt': request.prompt,
            'metadata': {
                'width': int(request.size.value.split('x')[0]),
                'height': int(request.size.value.split('x')[1]),
                'format': 'jpeg',
                'ai_generated': True,
                'style': request.style.value
            },
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Size is already included in file_size
        try:
            media_data['size'] = upload_result['size']
        except Exception:
            pass
        
        result = ctx.db.client.table('media').insert(media_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save AI generated image"
            )
        
        return GenerateAIImageResponse(
            id=media_id,
            filename=filename,
            type=MediaType.IMAGE,
            url=mock_url,
            generation_prompt=request.prompt,
            created_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to generate AI image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI image"
        )


@router.put("/{media_id}", response_model=UpdateMediaResponse)
async def update_media(
    media_id: str,
    request: UpdateMediaRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Update media metadata"""
    try:
        # Check if media exists and user has permission
        media_response = ctx.table('media').select('id, uploaded_by').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', media_id).maybe_single().execute()
        
        if not media_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media not found"
            )
        
        media = media_response.data
        
        # Only uploader or admin can edit
        if media['uploaded_by'] != current_user.sub and current_user.role.value != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to edit this media"
            )
        
        # Build update data
        update_data = {'updated_at': datetime.utcnow().isoformat()}
        
        if request.tags is not None:
            update_data['tags'] = request.tags
        if request.description is not None:
            update_data['description'] = request.description
        
        if not any(key in update_data for key in ['tags', 'description']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided"
            )
        
        result = ctx.table('media').update(update_data).eq('tenant_id', ctx.tenant_id).eq('id', media_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update media"
            )
        
        updated_media = result.data[0]
        
        return UpdateMediaResponse(
            id=media_id,
            tags=updated_media.get('tags', []),
            description=updated_media.get('description'),
            updated_at=datetime.fromisoformat(updated_media['updated_at'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update media: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update media"
        )


@router.get("/screenshots", response_model=ListMediaResponse)
async def list_screenshots(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """List screenshots stored in S3"""
    try:
        # Query media table for screenshots (media_type = screenshots)
        query = ctx.table('media').select('*', count='exact').eq('tenant_id', ctx.tenant_id).eq('media_type', 'screenshots')
        
        # Get total count
        count_response = query.execute()
        total = count_response.count or 0
        
        # Get paginated results
        offset = (page - 1) * limit
        media_response = query.range(offset, offset + limit - 1).order(
            'created_at', desc=True
        ).execute()
        
        media_list = []
        for media_data in media_response.data or []:
            # Handle both 'size' and 'file_size' fields for backward compatibility
            file_size = media_data.get('size') or media_data.get('file_size') or 0
            
            media_list.append(Media(
                id=media_data['id'],
                filename=media_data['file_name'],
                type=MediaType.IMAGE,
                size=file_size,
                url=media_data['file_path'],
                thumbnail_url=media_data.get('thumbnail_url'),
                metadata=MediaMetadata(**media_data['metadata']) if media_data.get('metadata') else None,
                created_at=datetime.fromisoformat(media_data['created_at'])
            ))
        
        return ListMediaResponse(
            media=media_list,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit
            }
        )
        
    except Exception as e:
        logger.exception(f"Failed to list screenshots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve screenshots"
        )


@router.delete("/{media_id}", response_model=DeleteMediaResponse)
async def delete_media(
    media_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Delete a media file"""
    try:
        # Check if media exists and user has permission
        media_response = ctx.table('media').select('id, uploaded_by, url, thumbnail_url').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', media_id).maybe_single().execute()
        
        if not media_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media not found"
            )
        
        media = media_response.data
        
        # Only uploader or admin can delete
        if media['uploaded_by'] != current_user.sub and current_user.role.value != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this media"
            )
        
        # Delete from database
        result = ctx.table('media').delete().eq('tenant_id', ctx.tenant_id).eq('id', media_id).execute()
        
        # Delete files from S3
        try:
            # Extract S3 key from URL for deletion
            if media['url'] and 'amazonaws.com' in media['url']:
                s3_key = media['url'].split('.com/')[-1]
                await s3_service.delete_file(s3_key)
            
            # Delete thumbnail from S3
            if media.get('thumbnail_url') and 'amazonaws.com' in media['thumbnail_url']:
                thumb_s3_key = media['thumbnail_url'].split('.com/')[-1]
                await s3_service.delete_file(thumb_s3_key)
                
        except Exception as e:
            logger.warning(f"Failed to delete S3 files: {e}")
        
        return DeleteMediaResponse()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete media: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete media"
        )


@router.post("/search-images", response_model=SearchImagesResponse)
async def search_images(
    request: SearchImagesRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Search for images using configured image search provider (Google Custom Search or SerpAPI)"""
    try:
        # Import the image search service
        from services.image_search_service import image_search_service

        # Check if image search is configured
        if not image_search_service.google_api_key and not image_search_service.serpapi_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Image search service not configured"
            )

        # Search using the configured provider
        logger.info(f"Searching for images with provider: {image_search_service.provider}")
        images_results = await image_search_service.search_images_urls(
            search_term=request.query,
            num_results=request.num_results
        )

        if not images_results:
            logger.warning(f"No images found for query: {request.query}")
            return SearchImagesResponse(results=[])

        # Format results
        search_results = []
        for img in images_results:
            try:
                # Get image data
                original_url = img.get("url")
                thumbnail_url = img.get("thumbnail")
                title = img.get("title", "")
                source = img.get("source", "")

                # Skip if no URLs available
                if not original_url or not thumbnail_url:
                    continue

                # Extract dimensions if available
                width = img.get("width")
                height = img.get("height")

                search_results.append(SearchImageResult(
                    url=original_url,
                    thumbnail_url=thumbnail_url,
                    title=title or "Untitled",
                    source=source or "Unknown",
                    width=width,
                    height=height
                ))
                
            except Exception as e:
                logger.warning(f"Failed to process image result: {e}")
                continue
        
        return SearchImagesResponse(results=search_results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to search images: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search images"
        )


class UploadFromUrlRequest(BaseModel):
    image_url: str
    filename: Optional[str] = None
    description: Optional[str] = None

@router.post("/upload-from-url", response_model=UploadMediaResponse, status_code=status.HTTP_201_CREATED)
async def upload_media_from_url(
    request: UploadFromUrlRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Upload media from URL (for image search results)"""
    try:
        # Download image from URL
        response = requests.get(request.image_url, timeout=10, headers={
            'User-Agent': 'OmniPush/1.0'
        })
        response.raise_for_status()
        
        # Validate content type
        content_type = response.headers.get('content-type', '').lower()
        if not content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL does not point to a valid image"
            )
        
        if content_type not in settings.allowed_file_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image type {content_type} not supported"
            )
        
        file_content = response.content
        
        # Validate file size
        if len(file_content) > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image too large"
            )
        
        # Generate filename if not provided
        filename = request.filename
        if not filename:
            from urllib.parse import urlparse
            parsed_url = urlparse(request.image_url)
            filename = os.path.basename(parsed_url.path)
            if not filename or '.' not in filename:
                # Create filename based on content type
                ext_map = {
                    'image/jpeg': 'jpg',
                    'image/jpg': 'jpg', 
                    'image/png': 'png',
                    'image/gif': 'gif',
                    'image/webp': 'webp'
                }
                ext = ext_map.get(content_type, 'jpg')
                filename = f"image_{uuid4().hex[:8]}.{ext}"
        
        # Validate file content using python-magic if available
        if _MAGIC_AVAILABLE:
            detected_type = magic.from_buffer(file_content, mime=True)
            if detected_type not in settings.allowed_file_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid image content"
                )
        
        media_id = str(uuid4())
        media_type = get_media_type(filename, content_type)
        
        # Extract metadata
        metadata = None
        if media_type == MediaType.IMAGE:
            metadata = get_image_metadata(file_content)
        
        # Save file to S3 storage
        file_url, thumbnail_url = await save_file_to_storage(
            file_content, filename, current_user.tenant_id, media_id
        )
        
        # Parse tags (not used in this endpoint currently)
        parsed_tags = []
        
        # Extract S3 keys from URLs for database storage
        s3_key = None
        thumbnail_s3_key = None
        
        if 'amazonaws.com' in file_url:
            s3_key = file_url.split('.com/')[-1]
        if thumbnail_url and 'amazonaws.com' in thumbnail_url:
            thumbnail_s3_key = thumbnail_url.split('.com/')[-1]

        # Save to database
        media_data = {
            'id': media_id,
            'tenant_id': current_user.tenant_id,
            'file_name': filename,
            'file_path': file_url,
            'file_size': len(file_content),
            'mime_type': content_type,
            'content_type': content_type,
            'media_type': media_type.value,
            's3_key': s3_key,
            's3_bucket': 'omnipush-media' if s3_key else None,
            'thumbnail_s3_key': thumbnail_s3_key,
            'metadata': metadata.model_dump() if metadata else None,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Add source URL for tracking
        if metadata:
            metadata_dict = metadata.model_dump()
            metadata_dict['source_url'] = request.image_url
            media_data['metadata'] = metadata_dict
        else:
            media_data['metadata'] = {'source_url': request.image_url}
        
        try:
            media_data['size'] = len(file_content)
        except Exception:
            pass
        
        result = ctx.db.client.table('media').insert(media_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save media record"
            )
        
        return UploadMediaResponse(
            id=media_id,
            filename=filename,
            type=media_type,
            size=len(file_content),
            url=file_url,
            thumbnail_url=thumbnail_url,
            uploaded_by=current_user.sub,
            created_at=datetime.utcnow()
        )
        
    except requests.RequestException as e:
        logger.error(f"Failed to download image from URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to download image from URL"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to upload media from URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image"
        )