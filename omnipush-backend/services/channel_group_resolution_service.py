"""
Channel Group Resolution Service

Resolves channel groups based on district/city information for intelligent routing.
Used by scraper jobs with "Recommended Channels" option enabled.
"""

import logging
from typing import List, Optional
from uuid import UUID

from core.database import get_database
from constants.district_channel_mapping import get_suggested_channel_group_name

logger = logging.getLogger(__name__)


class ChannelGroupResolutionService:
    """Service for resolving channel groups based on district/location data"""

    def __init__(self):
        self.db = get_database()

    async def find_channel_groups_by_district(
        self,
        district: str,
        tenant_id: UUID
    ) -> List[str]:
        """
        Find matching channel groups for a given district

        Args:
            district: District name (Tamil or English)
            tenant_id: Tenant ID to filter channel groups

        Returns:
            List of channel group IDs that match the district
        """
        try:
            # Get suggested channel group name from mapping
            suggested_group_name = get_suggested_channel_group_name(district)

            if not suggested_group_name:
                logger.warning(f"No channel group mapping found for district: {district}")
                # Fallback to TamilNadu general group
                suggested_group_name = get_suggested_channel_group_name('தமிழ்நாடு')
                if not suggested_group_name:
                    logger.error("Fallback to TamilNadu also failed, no channel groups found")
                    return []

            logger.info(f"District '{district}' mapped to channel group pattern: {suggested_group_name}")

            # Query channel_groups table for matching groups (partial name match)
            response = self.db.client.table('channel_groups')\
                .select('id, name')\
                .eq('tenant_id', str(tenant_id))\
                .execute()

            if not response.data:
                logger.warning(f"No channel groups found for tenant: {tenant_id}")
                return []

            # Filter groups using partial case-insensitive match
            # This allows flexible matching (e.g., "Chennai_Channels_Group" matches "Chennai Channels")
            matched_groups = []
            suggested_lower = suggested_group_name.lower()

            for group in response.data:
                group_name_lower = group['name'].lower()

                # Partial match in both directions
                if suggested_lower in group_name_lower or group_name_lower in suggested_lower:
                    matched_groups.append(group['id'])
                    logger.info(f"✓ Matched channel group: {group['name']} (ID: {group['id']})")

            if not matched_groups:
                logger.warning(
                    f"No channel groups matched pattern '{suggested_group_name}' for district '{district}'. "
                    f"Please create a channel group with name containing '{suggested_group_name}'"
                )

            return matched_groups

        except Exception as e:
            logger.error(f"Error finding channel groups for district '{district}': {e}", exc_info=True)
            return []

    async def resolve_channel_group_ids(
        self,
        channel_group_ids: List[str],
        district: Optional[str],
        tenant_id: UUID
    ) -> List[str]:
        """
        Resolve channel group IDs, replacing magic "RECOMMENDED" value with actual IDs

        Args:
            channel_group_ids: List of channel group IDs (may contain RECOMMENDED magic value)
            district: District name for resolution (required if RECOMMENDED in list)
            tenant_id: Tenant ID

        Returns:
            List of resolved channel group IDs
        """
        from models.scraper_models import RECOMMENDED_CHANNELS_MAGIC_VALUE

        if not channel_group_ids:
            return []

        resolved_ids = []

        for group_id in channel_group_ids:
            if group_id == RECOMMENDED_CHANNELS_MAGIC_VALUE:
                # Resolve to actual channel groups based on district
                if district:
                    logger.info(f"Resolving RECOMMENDED to actual channel groups for district: {district}")
                    suggested_ids = await self.find_channel_groups_by_district(district, tenant_id)
                    resolved_ids.extend(suggested_ids)
                else:
                    logger.warning("RECOMMENDED option selected but no district available, skipping")
            else:
                # Regular channel group ID
                resolved_ids.append(group_id)

        # Remove duplicates while preserving order
        seen = set()
        unique_resolved = []
        for group_id in resolved_ids:
            if group_id not in seen:
                seen.add(group_id)
                unique_resolved.append(group_id)

        logger.info(f"Resolved {len(channel_group_ids)} channel group IDs to {len(unique_resolved)} unique groups")
        return unique_resolved


# Singleton instance
_channel_group_resolution_service_instance: Optional[ChannelGroupResolutionService] = None


def get_channel_group_resolution_service() -> ChannelGroupResolutionService:
    """Get or create channel group resolution service singleton instance"""
    global _channel_group_resolution_service_instance

    if _channel_group_resolution_service_instance is None:
        _channel_group_resolution_service_instance = ChannelGroupResolutionService()

    return _channel_group_resolution_service_instance
