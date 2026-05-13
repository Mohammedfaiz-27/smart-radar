"""
Template Management API Endpoints
=================================

CRUD operations for managing newscard templates, including S3 uploads,
template activation/deactivation, and template metadata management.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import boto3
import uuid
import mimetypes
from pathlib import Path

from core.middleware import get_current_user, get_tenant_context, TenantContext
from core.database import get_database
from core.config import settings
from models.base import BaseResponse
from models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models for templates
from pydantic import BaseModel, Field
from typing import Union

class TemplateModel(BaseModel):
    """Model for template information"""
    id: str
    template_name: str
    template_display_name: str
    template_path: str
    s3_url: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_key: Optional[str] = None
    supports_images: bool
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

class CreateTemplateRequest(BaseModel):
    """Request model for creating a new template"""
    template_name: str = Field(..., description="Unique template identifier")
    template_display_name: str = Field(..., description="Human-readable template name")
    description: Optional[str] = Field(None, description="Template description")
    supports_images: bool = Field(False, description="Whether template supports images")

class UpdateTemplateRequest(BaseModel):
    """Request model for updating template metadata"""
    template_display_name: Optional[str] = None
    description: Optional[str] = None
    supports_images: Optional[bool] = None
    is_active: Optional[bool] = None

class ListTemplatesResponse(BaseResponse):
    """Response model for listing templates"""
    templates: List[TemplateModel]
    total_count: int
    active_count: int
    templates_with_images: int
    templates_without_images: int

class TemplateResponse(BaseResponse):
    """Response model for single template operations"""
    template: TemplateModel

class UploadTemplateResponse(BaseResponse):
    """Response model for template upload"""
    template: TemplateModel
    s3_url: str
    message: str = "Template uploaded successfully"

class BulkOperationResponse(BaseResponse):
    """Response model for bulk operations"""
    total_processed: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]

# Template service functions

async def get_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
    """Get template by ID from database"""
    db = get_database()

    result = db.client.table('newscard_templates')\
        .select('*')\
        .eq('id', template_id)\
        .execute()

    return result.data[0] if result.data else None

async def get_template_by_name(template_name: str) -> Optional[Dict[str, Any]]:
    """Get template by name from database"""
    db = get_database()

    result = db.client.table('newscard_templates')\
        .select('*')\
        .eq('template_name', template_name)\
        .execute()

    return result.data[0] if result.data else None

def upload_template_to_s3(file_content: bytes, filename: str, bucket_name: str, s3_prefix: str = "templates/newscard") -> Dict[str, str]:
    """Upload template file to S3"""
    s3_client = boto3.client('s3')

    # Generate unique S3 key
    file_extension = Path(filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    s3_key = f"{s3_prefix}/{unique_filename}"

    # Determine content type
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = 'text/html'

    try:
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type,
            CacheControl='max-age=31536000'  # 1 year cache
        )

        # Generate S3 URL
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"

        return {
            's3_url': s3_url,
            's3_bucket': bucket_name,
            's3_key': s3_key
        }

    except Exception as e:
        logger.error(f"Failed to upload template to S3: {str(e)}")
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")

# API Endpoints

@router.get("/", response_model=ListTemplatesResponse)
async def list_templates(
    active_only: bool = Query(False, description="Return only active templates"),
    supports_images: Optional[bool] = Query(None, description="Filter by image support"),
    search: Optional[str] = Query(None, description="Search in template names and descriptions"),
    user: User = Depends(get_current_user)
):
    """
    List all available newscard templates with filtering options.

    Public endpoint - templates are global, not tenant-specific.
    """
    db = get_database()

    try:
        # Build query
        query = db.client.table('newscard_templates').select('*')

        if active_only:
            query = query.eq('is_active', True)

        if supports_images is not None:
            query = query.eq('supports_images', supports_images)

        if search:
            query = query.or_(f'template_display_name.ilike.%{search}%,description.ilike.%{search}%')

        # Execute query
        result = query.order('template_display_name').execute()

        templates = [TemplateModel(**template) for template in result.data]

        # Calculate statistics
        total_count = len(templates)
        active_count = len([t for t in templates if t.is_active])
        with_images_count = len([t for t in templates if t.supports_images])
        without_images_count = total_count - with_images_count

        return ListTemplatesResponse(
            success=True,
            templates=templates,
            total_count=total_count,
            active_count=active_count,
            templates_with_images=with_images_count,
            templates_without_images=without_images_count
        )

    except Exception as e:
        logger.error(f"Failed to list templates: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve templates")

@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    user: User = Depends(get_current_user)
):
    """Get a specific template by ID"""
    template_data = await get_template_by_id(template_id)

    if not template_data:
        raise HTTPException(status_code=404, detail="Template not found")

    template = TemplateModel(**template_data)

    return TemplateResponse(
        success=True,
        template=template
    )

@router.post("/", response_model=TemplateResponse)
async def create_template(
    request: CreateTemplateRequest,
    user: User = Depends(get_current_user)
):
    """
    Create a new template metadata entry.
    Note: This creates the database entry only. Use the upload endpoint to add the actual template file.
    """
    # Check if template name already exists
    existing = await get_template_by_name(request.template_name)
    if existing:
        raise HTTPException(status_code=400, detail="Template name already exists")

    db = get_database()

    try:
        template_data = {
            'template_name': request.template_name,
            'template_display_name': request.template_display_name,
            'template_path': f"/templates/custom/{request.template_name}.html",  # Default path
            'supports_images': request.supports_images,
            'description': request.description,
            'is_active': True,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        result = db.client.table('newscard_templates')\
            .insert(template_data)\
            .execute()

        template = TemplateModel(**result.data[0])

        return TemplateResponse(
            success=True,
            template=template,
            message="Template created successfully"
        )

    except Exception as e:
        logger.error(f"Failed to create template: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create template")

@router.post("/{template_id}/upload", response_model=UploadTemplateResponse)
async def upload_template_file(
    template_id: str,
    file: UploadFile = File(..., description="HTML template file"),
    bucket_name: str = Form(..., description="S3 bucket name"),
    user: User = Depends(get_current_user)
):
    """Upload a template file to S3 and update the template record"""
    # Verify template exists
    template_data = await get_template_by_id(template_id)
    if not template_data:
        raise HTTPException(status_code=404, detail="Template not found")

    # Validate file type
    if not file.filename.endswith('.html'):
        raise HTTPException(status_code=400, detail="Only HTML files are allowed")

    try:
        # Read file content
        file_content = await file.read()

        # Upload to S3
        s3_info = upload_template_to_s3(file_content, file.filename, bucket_name)

        # Update template record with S3 info
        db = get_database()

        update_data = {
            's3_url': s3_info['s3_url'],
            's3_bucket': s3_info['s3_bucket'],
            's3_key': s3_info['s3_key'],
            'updated_at': datetime.utcnow().isoformat()
        }

        result = db.client.table('newscard_templates')\
            .update(update_data)\
            .eq('id', template_id)\
            .execute()

        updated_template = TemplateModel(**result.data[0])

        return UploadTemplateResponse(
            success=True,
            template=updated_template,
            s3_url=s3_info['s3_url'],
            message="Template uploaded successfully"
        )

    except Exception as e:
        logger.error(f"Failed to upload template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest,
    user: User = Depends(get_current_user)
):
    """Update template metadata"""
    # Verify template exists
    template_data = await get_template_by_id(template_id)
    if not template_data:
        raise HTTPException(status_code=404, detail="Template not found")

    db = get_database()

    try:
        # Build update data
        update_data = {'updated_at': datetime.utcnow().isoformat()}

        if request.template_display_name is not None:
            update_data['template_display_name'] = request.template_display_name
        if request.description is not None:
            update_data['description'] = request.description
        if request.supports_images is not None:
            update_data['supports_images'] = request.supports_images
        if request.is_active is not None:
            update_data['is_active'] = request.is_active

        result = db.client.table('newscard_templates')\
            .update(update_data)\
            .eq('id', template_id)\
            .execute()

        updated_template = TemplateModel(**result.data[0])

        return TemplateResponse(
            success=True,
            template=updated_template,
            message="Template updated successfully"
        )

    except Exception as e:
        logger.error(f"Failed to update template: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update template")

@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    force: bool = Query(False, description="Force delete even if template is in use"),
    user: User = Depends(get_current_user)
):
    """
    Delete a template.
    By default, templates in use by social channel assignments cannot be deleted.
    Use force=true to override this protection.
    """
    # Verify template exists
    template_data = await get_template_by_id(template_id)
    if not template_data:
        raise HTTPException(status_code=404, detail="Template not found")

    db = get_database()

    try:
        # Check if template is in use (unless forcing)
        if not force:
            assignments = db.client.table('social_channel_template_assignments')\
                .select('id')\
                .or_(f'template_with_image.eq.{template_data["template_name"]},template_without_image.eq.{template_data["template_name"]}')\
                .execute()

            if assignments.data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Template is in use by {len(assignments.data)} channel assignments. Use force=true to delete anyway."
                )

        # Delete template
        db.client.table('newscard_templates')\
            .delete()\
            .eq('id', template_id)\
            .execute()

        # TODO: Optionally delete S3 file as well
        # This would require AWS credentials and additional logic

        return BaseResponse(
            success=True,
            message="Template deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete template: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete template")

@router.post("/{template_id}/toggle-status")
async def toggle_template_status(
    template_id: str,
    user: User = Depends(get_current_user)
):
    """Toggle template active/inactive status"""
    # Verify template exists
    template_data = await get_template_by_id(template_id)
    if not template_data:
        raise HTTPException(status_code=404, detail="Template not found")

    db = get_database()

    try:
        new_status = not template_data['is_active']

        result = db.client.table('newscard_templates')\
            .update({
                'is_active': new_status,
                'updated_at': datetime.utcnow().isoformat()
            })\
            .eq('id', template_id)\
            .execute()

        updated_template = TemplateModel(**result.data[0])

        status_text = "activated" if new_status else "deactivated"

        return TemplateResponse(
            success=True,
            template=updated_template,
            message=f"Template {status_text} successfully"
        )

    except Exception as e:
        logger.error(f"Failed to toggle template status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update template status")

@router.post("/bulk/activate", response_model=BulkOperationResponse)
async def bulk_activate_templates(
    template_ids: List[str],
    user: User = Depends(get_current_user)
):
    """Bulk activate multiple templates"""
    db = get_database()

    results = []
    successful = 0
    failed = 0

    for template_id in template_ids:
        try:
            result = db.client.table('newscard_templates')\
                .update({
                    'is_active': True,
                    'updated_at': datetime.utcnow().isoformat()
                })\
                .eq('id', template_id)\
                .execute()

            if result.data:
                successful += 1
                results.append({
                    'template_id': template_id,
                    'status': 'success',
                    'message': 'Activated successfully'
                })
            else:
                failed += 1
                results.append({
                    'template_id': template_id,
                    'status': 'failed',
                    'message': 'Template not found'
                })

        except Exception as e:
            failed += 1
            results.append({
                'template_id': template_id,
                'status': 'failed',
                'message': str(e)
            })

    return BulkOperationResponse(
        success=True,
        total_processed=len(template_ids),
        successful=successful,
        failed=failed,
        results=results,
        message=f"Bulk activation complete. {successful}/{len(template_ids)} templates activated."
    )

@router.get("/{template_id}/content")
async def get_template_content(
    template_id: str,
    user: User = Depends(get_current_user)
):
    """Get the actual HTML content of a template (from S3 or local file)"""
    template_data = await get_template_by_id(template_id)
    if not template_data:
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        # Try to fetch from S3 first
        if template_data.get('s3_url'):
            import requests
            response = requests.get(template_data['s3_url'])
            if response.status_code == 200:
                return {
                    "success": True,
                    "content": response.text,
                    "source": "s3",
                    "url": template_data['s3_url']
                }

        # Fallback to local file
        if template_data.get('template_path'):
            from pathlib import Path
            local_path = Path(__file__).parent.parent.parent / template_data['template_path'].lstrip('/')

            if local_path.exists():
                content = local_path.read_text(encoding='utf-8')
                return {
                    "success": True,
                    "content": content,
                    "source": "local",
                    "path": str(local_path)
                }

        raise HTTPException(status_code=404, detail="Template content not found")

    except Exception as e:
        logger.error(f"Failed to get template content: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve template content")