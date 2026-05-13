from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from datetime import datetime
import logging
from uuid import UUID, uuid4

from core.middleware import get_current_user, get_tenant_context, TenantContext
from models.auth import JWTPayload
from pydantic import BaseModel
from services.channel_groups_service import ChannelGroupsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/channel-groups", tags=["channel groups"])


# Pydantic models
class ChannelGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = '#3b82f6'
    social_account_ids: List[str] = []


class ChannelGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    social_account_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ChannelGroupResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str]
    color: str
    social_account_ids: List[str]
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime


class ListChannelGroupsResponse(BaseModel):
    channel_groups: List[ChannelGroupResponse]


@router.get("", response_model=ListChannelGroupsResponse)
async def list_channel_groups(
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: JWTPayload = Depends(get_current_user)
):
    """List all channel groups for the current tenant"""
    try:
        service = ChannelGroupsService()
        groups_data = await service.list_channel_groups(
            tenant_id=tenant_context.tenant_id
        )
        
        channel_groups = []
        for group_data in groups_data:
            channel_groups.append(ChannelGroupResponse(
                id=str(group_data['id']),
                tenant_id=str(group_data['tenant_id']),
                name=group_data['name'],
                description=group_data['description'],
                color=group_data['color'],
                social_account_ids=[str(aid) for aid in (group_data['social_account_ids'] or [])],
                is_active=group_data['is_active'],
                created_by=str(group_data['created_by']),
                created_at=group_data['created_at'],
                updated_at=group_data['updated_at']
            ))
        
        return ListChannelGroupsResponse(channel_groups=channel_groups)
        
    except Exception as e:
        logger.exception(f"Failed to list channel groups: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve channel groups"
        )


@router.post("", response_model=ChannelGroupResponse)
async def create_channel_group(
    group_data: ChannelGroupCreate,
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: JWTPayload = Depends(get_current_user)
):
    """Create a new channel group"""
    try:
        service = ChannelGroupsService()
        
        # Validate social account IDs belong to this tenant
        if group_data.social_account_ids:
            is_valid = await service.validate_social_accounts(
                social_account_ids=group_data.social_account_ids,
                tenant_id=tenant_context.tenant_id
            )
            
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Some social account IDs are invalid or don't belong to this tenant"
                )
        
        result = await service.create_channel_group(
            tenant_id=tenant_context.tenant_id,
            name=group_data.name,
            created_by=current_user.sub,
            description=group_data.description,
            color=group_data.color,
            social_account_ids=group_data.social_account_ids
        )
        
        return ChannelGroupResponse(
            id=str(result['id']),
            tenant_id=str(result['tenant_id']),
            name=result['name'],
            description=result['description'],
            color=result['color'],
            social_account_ids=[str(aid) for aid in (result['social_account_ids'] or [])],
            is_active=result['is_active'],
            created_by=str(result['created_by']),
            created_at=result['created_at'],
            updated_at=result['updated_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to create channel group: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create channel group"
        )


@router.get("/{group_id}", response_model=ChannelGroupResponse)
async def get_channel_group(
    group_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: JWTPayload = Depends(get_current_user)
):
    """Get a specific channel group"""
    try:
        service = ChannelGroupsService()
        result = await service.get_channel_group(
            group_id=group_id,
            tenant_id=tenant_context.tenant_id
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel group not found"
            )
        
        return ChannelGroupResponse(
            id=str(result['id']),
            tenant_id=str(result['tenant_id']),
            name=result['name'],
            description=result['description'],
            color=result['color'],
            social_account_ids=[str(aid) for aid in (result['social_account_ids'] or [])],
            is_active=result['is_active'],
            created_by=str(result['created_by']),
            created_at=result['created_at'],
            updated_at=result['updated_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get channel group: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve channel group"
        )


@router.put("/{group_id}", response_model=ChannelGroupResponse)
async def update_channel_group(
    group_id: str,
    group_data: ChannelGroupUpdate,
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: JWTPayload = Depends(get_current_user)
):
    """Update an existing channel group"""
    try:
        service = ChannelGroupsService()
        
        # Check if group exists
        existing = await service.get_channel_group(
            group_id=group_id,
            tenant_id=tenant_context.tenant_id
        )
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel group not found"
            )
        
        # Validate social account IDs if provided
        if group_data.social_account_ids is not None:
            is_valid = await service.validate_social_accounts(
                social_account_ids=group_data.social_account_ids,
                tenant_id=tenant_context.tenant_id
            )
            
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Some social account IDs are invalid or don't belong to this tenant"
                )
        
        # Convert request to dict and remove None values
        updates = group_data.dict(exclude_unset=True)
        
        result = await service.update_channel_group(
            group_id=group_id,
            tenant_id=tenant_context.tenant_id,
            updates=updates
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update channel group"
            )
        
        return ChannelGroupResponse(
            id=str(result['id']),
            tenant_id=str(result['tenant_id']),
            name=result['name'],
            description=result['description'],
            color=result['color'],
            social_account_ids=[str(aid) for aid in (result['social_account_ids'] or [])],
            is_active=result['is_active'],
            created_by=str(result['created_by']),
            created_at=result['created_at'],
            updated_at=result['updated_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update channel group: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update channel group"
        )


@router.delete("/{group_id}")
async def delete_channel_group(
    group_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
    current_user: JWTPayload = Depends(get_current_user)
):
    """Delete a channel group (soft delete)"""
    try:
        service = ChannelGroupsService()
        
        success = await service.delete_channel_group(
            group_id=group_id,
            tenant_id=tenant_context.tenant_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel group not found"
            )
        
        return {"message": "Channel group deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete channel group: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete channel group"
        )