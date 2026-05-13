from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional, List
import logging
from uuid import UUID

from core.middleware import get_current_user, get_tenant_context, TenantContext
from models.auth import JWTPayload
from models.content import Platform
from models.template_assignment import (
    AssignTemplatesRequest,
    BulkAssignDefaultTemplatesRequest,
    ListTemplatesResponse,
    ListTemplateAssignmentsResponse,
    AssignTemplatesResponse,
    TemplateAssignmentSummaryResponse,
    BulkAssignmentResponse,
    TemplateAssignmentStatusResponse,
    RemoveAssignmentResponse,
    NewscardTemplateModel,
    SocialChannelTemplateAssignmentModel,
    SocialAccountSummary
)
from services.social_template_assignment_service import SocialTemplateAssignmentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/template-assignments", tags=["template assignments"])


@router.get("/templates", response_model=ListTemplatesResponse)
async def list_available_templates(
    supports_images: Optional[bool] = Query(None, description="Filter templates by image support"),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """List all available newscard templates, optionally filtered by image support"""
    try:
        service = SocialTemplateAssignmentService(ctx.db.client)
        templates = await service.get_available_templates(supports_images=supports_images)

        # Convert to response models
        template_models = [
            NewscardTemplateModel(
                id=t.id,
                template_name=t.template_name,
                template_display_name=t.template_display_name,
                template_path=t.template_path,
                supports_images=t.supports_images,
                description=t.description,
                is_active=t.is_active,
                s3_url=t.s3_url,
                s3_bucket=t.s3_bucket,
                s3_key=t.s3_key,
                created_at=t.created_at,
                updated_at=t.updated_at
            )
            for t in templates
        ]

        # Calculate counts
        templates_with_images = sum(1 for t in template_models if t.supports_images)
        templates_without_images = sum(1 for t in template_models if not t.supports_images)

        return ListTemplatesResponse(
            templates=template_models,
            total_count=len(template_models),
            templates_with_images=templates_with_images,
            templates_without_images=templates_without_images
        )

    except Exception as e:
        logger.exception(f"Failed to list available templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available templates"
        )


@router.get("/assignments", response_model=ListTemplateAssignmentsResponse)
async def list_template_assignments(
    social_account_id: Optional[str] = Query(None, description="Filter by specific social account"),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """List template assignments for the tenant, optionally filtered by social account"""
    try:
        service = SocialTemplateAssignmentService(ctx.db.client)
        assignments = await service.get_template_assignments(
            tenant_id=ctx.tenant_id,
            social_account_id=social_account_id
        )

        # Convert to response models
        assignment_models = [
            SocialChannelTemplateAssignmentModel(
                id=a.id,
                tenant_id=a.tenant_id,
                social_account_id=a.social_account_id,
                platform=a.platform,
                template_with_image=a.template_with_image,
                template_without_image=a.template_without_image,
                created_at=a.created_at,
                updated_at=a.updated_at
            )
            for a in assignments
        ]

        return ListTemplateAssignmentsResponse(
            assignments=assignment_models,
            total_count=len(assignment_models)
        )

    except Exception as e:
        logger.exception(f"Failed to list template assignments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template assignments"
        )


@router.post("/assign", response_model=AssignTemplatesResponse, status_code=status.HTTP_201_CREATED)
async def assign_templates_to_social_channel(
    request: AssignTemplatesRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Assign templates to a social channel for content with and without images"""
    try:
        # Validate that at least one template is provided
        if not request.template_with_image and not request.template_without_image:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one template must be specified"
            )

        # Verify the social account exists and belongs to the tenant
        social_account = ctx.table('social_accounts').select(
            'id, platform, account_name'
        ).eq('tenant_id', ctx.tenant_id).eq('id', request.social_account_id).maybe_single().execute()

        if not social_account.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Social account not found"
            )

        account_data = social_account.data
        platform = Platform(account_data['platform'])

        # Assign templates
        service = SocialTemplateAssignmentService(ctx.db.client)
        success = await service.assign_templates_to_social_channel(
            tenant_id=ctx.tenant_id,
            social_account_id=request.social_account_id,
            platform=platform,
            template_with_image=request.template_with_image,
            template_without_image=request.template_without_image,
            user_id=current_user.sub
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to assign templates"
            )

        # Retrieve the created/updated assignment
        assignments = await service.get_template_assignments(
            tenant_id=ctx.tenant_id,
            social_account_id=request.social_account_id
        )

        if not assignments:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Assignment created but could not be retrieved"
            )

        assignment = assignments[0]
        assignment_model = SocialChannelTemplateAssignmentModel(
            id=assignment.id,
            tenant_id=assignment.tenant_id,
            social_account_id=assignment.social_account_id,
            platform=assignment.platform,
            template_with_image=assignment.template_with_image,
            template_without_image=assignment.template_without_image,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at
        )

        return AssignTemplatesResponse(
            assignment=assignment_model,
            message=f"Templates assigned successfully to {account_data['account_name']}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to assign templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign templates"
        )


@router.get("/summary", response_model=TemplateAssignmentSummaryResponse)
async def get_template_assignment_summary(
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get a summary of template assignments for all social channels"""
    try:
        service = SocialTemplateAssignmentService(ctx.db.client)
        summary = await service.get_template_assignment_summary(ctx.tenant_id)

        if 'error' in summary:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=summary['error']
            )

        # Convert accounts to response models
        account_summaries = [
            SocialAccountSummary(
                social_account_id=account['social_account_id'],
                platform=Platform(account['platform']),
                account_name=account['account_name'],
                has_assignment=account['has_assignment'],
                template_with_image=account['template_with_image'],
                template_without_image=account['template_without_image']
            )
            for account in summary['accounts']
        ]

        return TemplateAssignmentSummaryResponse(
            tenant_id=summary['tenant_id'],
            total_social_accounts=summary['total_social_accounts'],
            accounts_with_assignments=summary['accounts_with_assignments'],
            accounts_without_assignments=summary['accounts_without_assignments'],
            accounts=account_summaries
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get template assignment summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template assignment summary"
        )


@router.post("/bulk-assign-defaults", response_model=BulkAssignmentResponse)
async def bulk_assign_default_templates(
    request: BulkAssignDefaultTemplatesRequest = BulkAssignDefaultTemplatesRequest(),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Assign default templates to all social channels that don't have assignments"""
    try:
        service = SocialTemplateAssignmentService(ctx.db.client)
        result = await service.bulk_assign_default_templates(ctx.tenant_id)

        if not result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get('message', 'Failed to bulk assign default templates')
            )

        return BulkAssignmentResponse(
            total_accounts=result['total_accounts'],
            assigned_count=result['assigned_count'],
            failed_count=result['failed_count'],
            default_template_with_image=result['default_template_with_image'],
            default_template_without_image=result['default_template_without_image'],
            message=f"Successfully assigned default templates to {result['assigned_count']} social channels"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to bulk assign default templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk assign default templates"
        )


@router.get("/status/{social_account_id}", response_model=TemplateAssignmentStatusResponse)
async def get_template_assignment_status(
    social_account_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get template assignment status for a specific social channel"""
    try:
        # Verify the social account exists and belongs to the tenant
        social_account = ctx.table('social_accounts').select(
            'id, platform, account_name'
        ).eq('tenant_id', ctx.tenant_id).eq('id', social_account_id).maybe_single().execute()

        if not social_account.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Social account not found"
            )

        account_data = social_account.data
        platform = Platform(account_data['platform'])

        # Get template assignment
        service = SocialTemplateAssignmentService(ctx.db.client)
        assignments = await service.get_template_assignments(
            tenant_id=ctx.tenant_id,
            social_account_id=social_account_id
        )

        has_assignment = len(assignments) > 0
        assignment = assignments[0] if assignments else None

        # Determine which templates will actually be used
        will_use_for_images = None
        will_use_for_text = None

        if assignment:
            # For content with images
            will_use_for_images = assignment.template_with_image or assignment.template_without_image
            # For text-only content
            will_use_for_text = assignment.template_without_image or assignment.template_with_image

        return TemplateAssignmentStatusResponse(
            social_account_id=social_account_id,
            platform=platform,
            account_name=account_data['account_name'],
            has_assignment=has_assignment,
            assigned_template_with_image=assignment.template_with_image if assignment else None,
            assigned_template_without_image=assignment.template_without_image if assignment else None,
            will_use_for_images=will_use_for_images,
            will_use_for_text=will_use_for_text
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get template assignment status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template assignment status"
        )


@router.delete("/assignments/{social_account_id}", response_model=RemoveAssignmentResponse)
async def remove_template_assignment(
    social_account_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Remove template assignment for a social channel"""
    try:
        # Verify the social account exists and belongs to the tenant
        social_account = ctx.table('social_accounts').select(
            'id, account_name'
        ).eq('tenant_id', ctx.tenant_id).eq('id', social_account_id).maybe_single().execute()

        if not social_account.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Social account not found"
            )

        # Remove template assignment
        service = SocialTemplateAssignmentService(ctx.db.client)
        success = await service.remove_template_assignment(
            tenant_id=ctx.tenant_id,
            social_account_id=social_account_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove template assignment"
            )

        account_name = social_account.data['account_name']
        return RemoveAssignmentResponse(
            social_account_id=social_account_id,
            message=f"Template assignment removed successfully for {account_name}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to remove template assignment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove template assignment"
        )


@router.get("/channel/{social_account_id}/template")
async def get_template_for_channel(
    social_account_id: str,
    has_images: bool = Query(False, description="Whether the content has images"),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get the assigned template for a specific social channel and content type (internal use)"""
    try:
        # Verify the social account exists and belongs to the tenant
        social_account = ctx.table('social_accounts').select(
            'id, platform, account_name'
        ).eq('tenant_id', ctx.tenant_id).eq('id', social_account_id).maybe_single().execute()

        if not social_account.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Social account not found"
            )

        # Get assigned template
        service = SocialTemplateAssignmentService(ctx.db.client)
        template_name = await service.get_assigned_template_for_channel(
            tenant_id=ctx.tenant_id,
            social_account_id=social_account_id,
            has_images=has_images
        )

        return {
            "social_account_id": social_account_id,
            "platform": social_account.data['platform'],
            "account_name": social_account.data['account_name'],
            "has_images": has_images,
            "assigned_template": template_name,
            "has_assignment": template_name is not None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get template for channel: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template for channel"
        )