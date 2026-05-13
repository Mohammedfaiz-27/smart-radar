"""
Channel Groups Service - CRUD operations for channel_groups table
Handles social media channel grouping and organization
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from uuid import uuid4, UUID

from core.database import get_database

logger = logging.getLogger(__name__)


class ChannelGroupsService:
    """Service for managing channel groups with tenant isolation"""
    
    def __init__(self):
        self.db = get_database()
    
    async def create_channel_group(
        self,
        tenant_id: str,
        name: str,
        created_by: str,
        description: Optional[str] = None,
        color: str = '#3b82f6',
        social_account_ids: List[str] = []
    ) -> Dict[str, Any]:
        """Create a new channel group"""
        try:
            group_id = str(uuid4())
            now = datetime.now(timezone.utc).isoformat()
            
            # Convert string IDs to UUIDs
            account_ids_uuid = [aid for aid in social_account_ids] if social_account_ids else []
            
            # Prepare group data
            group_data = {
                "id": group_id,
                "tenant_id": tenant_id,
                "name": name,
                "description": description,
                "color": color,
                "social_account_ids": account_ids_uuid,
                "is_active": True,
                "created_by": created_by,
                "created_at": now,
                "updated_at": now
            }
            
            # Remove None values
            group_data = {k: v for k, v in group_data.items() if v is not None}
            
            response = self.db.service_client.table("channel_groups")\
                .insert(group_data)\
                .execute()
            
            if response.data:
                logger.info(f"Created channel group: {name}")
                return response.data[0]
            else:
                raise Exception("Failed to create channel group")
                
        except Exception as e:
            logger.exception(f"Failed to create channel group: {e}")
            raise e
    
    async def get_channel_group(self, group_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific channel group by ID"""
        try:
            response = self.db.service_client.table("channel_groups")\
                .select("*")\
                .eq("id", group_id)\
                .eq("tenant_id", str(tenant_id))\
                .eq("is_active", True)\
                .single()\
                .execute()
            
            return response.data if response.data else None
            
        except Exception as e:
            logger.exception(f"Failed to get channel group {group_id}: {e}")
            return None
    
    async def list_channel_groups(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List channel groups for a tenant"""
        try:
            response = self.db.service_client.table("channel_groups")\
                .select("*")\
                .eq("tenant_id", tenant_id)\
                .eq("is_active", True)\
                .order("created_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.exception(f"Failed to list channel groups: {e}")
            return []
    
    async def update_channel_group(
        self,
        group_id: str,
        tenant_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a channel group"""
        try:
            # Add updated_at timestamp
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Convert social_account_ids to UUIDs if provided
            if "social_account_ids" in updates and updates["social_account_ids"] is not None:
                updates["social_account_ids"] = [str(aid) for aid in updates["social_account_ids"]]
            
            # Remove None values
            updates = {k: v for k, v in updates.items() if v is not None}
            
            response = self.db.service_client.table("channel_groups")\
                .update(updates)\
                .eq("id", group_id)\
                .eq("tenant_id", tenant_id)\
                .eq("is_active", True)\
                .execute()
            
            if response.data:
                logger.info(f"Updated channel group: {group_id}")
                return response.data[0]
            else:
                return None
                
        except Exception as e:
            logger.exception(f"Failed to update channel group {group_id}: {e}")
            return None
    
    async def delete_channel_group(self, group_id: str, tenant_id: str) -> bool:
        """Soft delete a channel group"""
        try:
            response = self.db.service_client.table("channel_groups")\
                .update({
                    "is_active": False,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })\
                .eq("id", group_id)\
                .eq("tenant_id", tenant_id)\
                .eq("is_active", True)\
                .execute()
            
            if response.data:
                logger.info(f"Deleted channel group: {group_id}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.exception(f"Failed to delete channel group {group_id}: {e}")
            return False
    
    async def validate_social_accounts(
        self,
        social_account_ids: List[str],
        tenant_id: str
    ) -> bool:
        """Validate that social account IDs belong to the tenant"""
        try:
            if not social_account_ids:
                return True
            
            account_ids_uuid = [UUID(aid) for aid in social_account_ids]
            
            response = self.db.service_client.table("social_accounts")\
                .select("id")\
                .in_("id", account_ids_uuid)\
                .eq("tenant_id", tenant_id)\
                .execute()
            
            # Check if all provided IDs exist and belong to the tenant
            found_ids = {str(account["id"]) for account in response.data}
            provided_ids = set(social_account_ids)
            
            return found_ids == provided_ids
            
        except Exception as e:
            logger.exception(f"Failed to validate social accounts: {e}")
            return False
