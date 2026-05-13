from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
from uuid import uuid4
from typing import List, Optional
import logging

from core.middleware import get_current_user, require_admin, get_tenant_context, TenantContext
from models.auth import JWTPayload, UserRole
from models.workflow import (
    CreateWorkflowRequest,
    ListWorkflowsResponse,
    CreateWorkflowResponse,
    Workflow,
    WorkflowStep,
    WorkflowStepType
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows", tags=["workflow management"])


async def validate_workflow_users(steps: List[WorkflowStep], tenant_id: str, ctx: TenantContext) -> None:
    """Validate that all users in workflow steps exist and are active in the tenant"""
    all_user_ids = set()
    for step in steps:
        all_user_ids.update(step.approvers)
    
    if not all_user_ids:
        return
    
    # Check if all users exist and are active
    users_response = ctx.table('users').select('id').eq(
        'tenant_id', ctx.tenant_id
    ).in_('id', list(all_user_ids)).eq('status', 'active').execute()
    
    found_user_ids = {user['id'] for user in users_response.data or []}
    missing_users = all_user_ids - found_user_ids
    
    if missing_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or inactive users in workflow: {list(missing_users)}"
        )


async def get_default_workflow_for_tenant(tenant_id: str, ctx: TenantContext) -> Optional[Workflow]:
    """Get the default workflow for a tenant"""
    try:
        workflow_response = ctx.table('workflows').select('*').eq(
            'tenant_id', ctx.tenant_id
        ).eq('is_default', True).maybe_single().execute()
        
        if not workflow_response.data:
            return None
        
        workflow_data = workflow_response.data
        return Workflow(
            id=workflow_data['id'],
            name=workflow_data['name'],
            description=workflow_data.get('description'),
            steps=[WorkflowStep(**step) for step in workflow_data['steps']],
            is_default=workflow_data['is_default'],
            created_by=workflow_data['created_by'],
            created_at=datetime.fromisoformat(workflow_data['created_at'])
        )
        
    except Exception:
        return None


@router.get("", response_model=ListWorkflowsResponse)
async def list_workflows(
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """List all workflows for the tenant"""
    try:
        workflows_response = ctx.table('workflows').select('*').eq(
            'tenant_id', ctx.tenant_id
        ).order('created_at', desc=True).execute()

        workflows = []
        for workflow_data in workflows_response.data or []:
            workflows.append(Workflow(
                id=workflow_data['id'],
                name=workflow_data['name'],
                description=workflow_data.get('description'),
                steps=[WorkflowStep(**step) for step in workflow_data['steps']],
                is_default=workflow_data.get('is_default', False),
                created_by=workflow_data['created_by'],
                created_at=datetime.fromisoformat(workflow_data['created_at'])
            ))
        
        return ListWorkflowsResponse(workflows=workflows)
        
    except Exception as e:
        logger.exception(f"Failed to list workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflows"
        )


@router.post("", response_model=CreateWorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: CreateWorkflowRequest,
    current_user: JWTPayload = Depends(require_admin),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Create a new workflow (admin only)"""
    try:
        # Validate workflow steps
        if not request.steps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow must have at least one step"
            )
        
        # Validate step ordering
        orders = [step.order for step in request.steps]
        if len(set(orders)) != len(orders):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Step orders must be unique"
            )
        
        if min(orders) != 1 or max(orders) != len(orders):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Step orders must be consecutive starting from 1"
            )
        
        # Validate users in workflow steps
        await validate_workflow_users(request.steps, current_user.tenant_id, ctx)
        
        # Create workflow
        workflow_id = str(uuid4())
        workflow_data = {
            'id': workflow_id,
            'tenant_id': current_user.tenant_id,
            'name': request.name,
            'description': request.description,
            'steps': [step.model_dump() for step in request.steps],
            'is_default': False,  # New workflows are not default
            'created_by': current_user.sub,
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = ctx.db.client.table('workflows').insert(workflow_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create workflow"
            )
        
        return CreateWorkflowResponse(
            id=workflow_id,
            name=request.name,
            created_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to create workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create workflow"
        )


@router.get("/{workflow_id}", response_model=Workflow)
async def get_workflow(
    workflow_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get a specific workflow"""
    try:
        workflow_response = ctx.table('workflows').select('*').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', workflow_id).maybe_single().execute()
        
        if not workflow_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        workflow_data = workflow_response.data
        return Workflow(
            id=workflow_data['id'],
            name=workflow_data['name'],
            description=workflow_data.get('description'),
            steps=[WorkflowStep(**step) for step in workflow_data['steps']],
            is_default=workflow_data['is_default'],
            created_by=workflow_data['created_by'],
            created_at=datetime.fromisoformat(workflow_data['created_at'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow"
        )


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    request: CreateWorkflowRequest,
    current_user: JWTPayload = Depends(require_admin),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Update an existing workflow (admin only)"""
    try:
        # Check if workflow exists
        workflow_response = ctx.table('workflows').select('id, created_by').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', workflow_id).maybe_single().execute()
        
        if not workflow_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Validate workflow steps (same validation as create)
        if not request.steps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow must have at least one step"
            )
        
        orders = [step.order for step in request.steps]
        if len(set(orders)) != len(orders):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Step orders must be unique"
            )
        
        if min(orders) != 1 or max(orders) != len(orders):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Step orders must be consecutive starting from 1"
            )
        
        await validate_workflow_users(request.steps, current_user.tenant_id, ctx)
        
        # Update workflow
        update_data = {
            'name': request.name,
            'description': request.description,
            'steps': [step.model_dump() for step in request.steps],
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = ctx.table('workflows').update(update_data).eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', workflow_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update workflow"
            )
        
        return {"message": "Workflow updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update workflow"
        )


@router.post("/{workflow_id}/set-default")
async def set_default_workflow(
    workflow_id: str,
    current_user: JWTPayload = Depends(require_admin),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Set a workflow as the default for the tenant (admin only)"""
    try:
        # Check if workflow exists
        workflow_response = ctx.table('workflows').select('id').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', workflow_id).maybe_single().execute()
        
        if not workflow_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Remove default flag from all workflows
        ctx.table('workflows').update({
            'is_default': False,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('tenant_id', current_user.tenant_id).execute()
        
        # Set new default
        ctx.table('workflows').update({
            'is_default': True,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', workflow_id).execute()
        
        return {"message": "Default workflow updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to set default workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set default workflow"
        )


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    current_user: JWTPayload = Depends(require_admin),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Delete a workflow (admin only)"""
    try:
        # Check if workflow exists
        workflow_response = ctx.table('workflows').select('id, is_default').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', workflow_id).maybe_single().execute()
        
        if not workflow_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        workflow = workflow_response.data
        
        # Prevent deletion of default workflow if it's the only one
        if workflow['is_default']:
            workflows_count = ctx.table('workflows').select(
                'id', count='exact'
            ).eq('tenant_id', ctx.tenant_id).execute().count or 0
            
            if workflows_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the only workflow. Create another workflow first."
                )
        
        # Delete workflow
        ctx.table('workflows').delete().eq('tenant_id', ctx.tenant_id).eq('id', workflow_id).execute()
        
        return {"message": "Workflow deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete workflow"
        )


@router.get("/{workflow_id}/preview")
async def preview_workflow(
    workflow_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Preview a workflow with user details"""
    try:
        # Get workflow
        workflow_response = ctx.table('workflows').select('*').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', workflow_id).maybe_single().execute()
        
        if not workflow_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        workflow_data = workflow_response.data
        
        # Get details for all approvers
        all_approver_ids = set()
        for step in workflow_data['steps']:
            all_approver_ids.update(step.get('approvers', []))
        
        if all_approver_ids:
            users_response = ctx.table('users').select(
                'id, first_name, last_name, email, role'
            ).in_('id', list(all_approver_ids)).execute()
            
            users_map = {
                user['id']: {
                    'id': user['id'],
                    'name': f"{user['first_name']} {user['last_name']}",
                    'email': user['email'],
                    'role': user['role']
                }
                for user in users_response.data or []
            }
        else:
            users_map = {}
        
        # Build preview with user details
        steps_preview = []
        for step in workflow_data['steps']:
            approvers_details = [
                users_map.get(approver_id, {'id': approver_id, 'name': 'Unknown User'})
                for approver_id in step.get('approvers', [])
            ]
            
            steps_preview.append({
                'order': step['order'],
                'type': step['type'],
                'required': step['required'],
                'approvers': approvers_details
            })
        
        return {
            'workflow': {
                'id': workflow_data['id'],
                'name': workflow_data['name'],
                'description': workflow_data.get('description'),
                'is_default': workflow_data['is_default']
            },
            'steps': steps_preview,
            'total_steps': len(steps_preview),
            'required_steps': sum(1 for step in workflow_data['steps'] if step.get('required', True))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to preview workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to preview workflow"
        )


@router.post("/initialize-default")
async def initialize_default_workflow(
    current_user: JWTPayload = Depends(require_admin),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Initialize a default workflow if none exists (admin only)"""
    try:
        # Check if any workflows exist
        existing_workflows = ctx.table('workflows').select('id').eq('tenant_id', ctx.tenant_id).execute()
        
        if existing_workflows.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflows already exist for this tenant"
            )
        
        # Get admin users to set as default approvers
        admin_users = ctx.table('users').select('id').eq(
            'tenant_id', ctx.tenant_id
        ).eq('role', UserRole.ADMIN.value).eq('status', 'active').execute()
        
        admin_ids = [user['id'] for user in admin_users.data or []]
        
        if not admin_ids:
            admin_ids = [current_user.sub]  # Fallback to current user
        
        # Create default workflow
        workflow_id = str(uuid4())
        default_workflow = {
            'id': workflow_id,
            'tenant_id': current_user.tenant_id,
            'name': 'Standard Approval',
            'description': 'Default approval workflow - all posts require admin approval',
            'steps': [{
                'order': 1,
                'type': WorkflowStepType.APPROVAL.value,
                'approvers': admin_ids,
                'required': True
            }],
            'is_default': True,
            'created_by': current_user.sub,
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = ctx.db.client.table('workflows').insert(default_workflow).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create default workflow"
            )
        
        return {
            "message": "Default workflow initialized successfully",
            "workflow_id": workflow_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to initialize default workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize default workflow"
        )