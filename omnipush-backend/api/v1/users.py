from fastapi import APIRouter, HTTPException, status, Depends, Query
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Optional
import logging

from core.database import get_database, SupabaseClient
from core.middleware import get_current_user, require_admin, get_tenant_context, TenantContext
from core.security import hash_password
from models.auth import JWTPayload, UserRole
from models.user import (
    InviteUserRequest,
    UpdateUserRoleRequest,
    ListUsersResponse,
    InviteUserResponse,
    UpdateUserRoleResponse,
    DeactivateUserResponse,
    User,
    Invitation,
    UserStatus,
    InvitationStatus
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["user management"])


@router.get("", response_model=ListUsersResponse)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[UserRole] = Query(None),
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """
    List users in current tenant
    """
    try:
        # Build query with tenant filter
        query = ctx.table('users').select(
            'id, email, first_name, last_name, role, status, last_login, created_at',
            count='exact'
        ).eq('tenant_id', ctx.tenant_id)
        
        if role:
            query = query.eq('role', role.value)
        
        # Get total count
        count_response = query.execute()
        total = count_response.count or 0
        
        # Get paginated results
        offset = (page - 1) * limit
        users_response = query.range(offset, offset + limit - 1).execute()
        
        users = []
        for user_data in users_response.data or []:
            users.append(User(
                id=user_data['id'],
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                role=UserRole(user_data['role']),
                status=UserStatus(user_data['status']),
                last_login=datetime.fromisoformat(user_data['last_login']) if user_data['last_login'] else None,
                created_at=datetime.fromisoformat(user_data['created_at'])
            ))
        
        return ListUsersResponse(
            users=users,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit
            }
        )
        
    except Exception as e:
        logger.exception(f"Failed to list users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.post("/invite", response_model=InviteUserResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    request: InviteUserRequest,
    current_user: JWTPayload = Depends(require_admin),
    db: SupabaseClient = Depends(get_database)
):
    """
    Invite a new user to the tenant (admin only)
    """
    try:
        # Check if user already exists in this tenant
        existing_user = db.client.table('users').select('id').eq(
            'email', request.email
        ).eq('tenant_id', current_user.tenant_id).execute()
        
        if existing_user.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists in this tenant"
            )
        
        # Check if there's a pending invitation
        existing_invite = db.client.table('invitations').select('id').eq(
            'email', request.email
        ).eq('tenant_id', current_user.tenant_id).eq(
            'status', InvitationStatus.PENDING.value
        ).execute()
        
        if existing_invite.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Pending invitation already exists for this email"
            )
        
        # Create invitation
        invitation_id = str(uuid4())
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        invitation_data = {
            'id': invitation_id,
            'tenant_id': current_user.tenant_id,
            'email': request.email,
            'role': request.role.value,
            'first_name': request.first_name,
            'last_name': request.last_name,
            'status': InvitationStatus.PENDING.value,
            'expires_at': expires_at.isoformat(),
            'invited_by': current_user.sub,
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = db.client.table('invitations').insert(invitation_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create invitation"
            )
        
        # TODO: Send invitation email
        
        return InviteUserResponse(
            invitation=Invitation(
                id=invitation_id,
                email=request.email,
                role=request.role,
                status=InvitationStatus.PENDING,
                expires_at=expires_at
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to invite user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send invitation"
        )


@router.put("/{user_id}/role", response_model=UpdateUserRoleResponse)
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    current_user: JWTPayload = Depends(require_admin),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """
    Update user role (admin only)
    """
    try:
        # Check if user exists in tenant
        user_response = ctx.table('users').select('id, role').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', user_id).maybe_single().execute()
        
        if not user_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent admin from changing their own role
        if user_id == current_user.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot change your own role"
            )
        
        # Update role
        update_data = {
            'role': request.role.value,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = ctx.table('users').update(update_data).eq('tenant_id', ctx.tenant_id).eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user role"
            )
        
        return UpdateUserRoleResponse(
            id=user_id,
            role=request.role,
            updated_at=datetime.fromisoformat(result.data[0]['updated_at'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update user role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role"
        )


@router.delete("/{user_id}", response_model=DeactivateUserResponse)
async def deactivate_user(
    user_id: str,
    current_user: JWTPayload = Depends(require_admin),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """
    Deactivate user (admin only)
    """
    try:
        # Check if user exists in tenant
        user_response = ctx.table('users').select('id, status').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', user_id).maybe_single().execute()
        
        if not user_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent admin from deactivating themselves
        if user_id == current_user.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot deactivate your own account"
            )
        
        # Deactivate user
        update_data = {
            'status': UserStatus.INACTIVE.value,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = ctx.table('users').update(update_data).eq('tenant_id', ctx.tenant_id).eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate user"
            )
        
        return DeactivateUserResponse()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to deactivate user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user"
        )