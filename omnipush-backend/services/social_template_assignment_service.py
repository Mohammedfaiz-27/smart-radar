import logging
from typing import Dict, List, Optional, Tuple
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass

from models.content import Platform

logger = logging.getLogger(__name__)

@dataclass
class NewscardTemplate:
    """Represents a newscard template"""
    id: str
    template_name: str
    template_display_name: str
    template_path: str
    supports_images: bool
    description: Optional[str] = None
    is_active: bool = True
    s3_url: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_key: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class SocialChannelTemplateAssignment:
    """Represents a template assignment for a social channel"""
    id: str
    tenant_id: str
    social_account_id: str
    platform: Platform
    template_with_image: Optional[str]
    template_without_image: Optional[str]
    created_at: datetime
    updated_at: datetime


class SocialTemplateAssignmentService:
    """Service for managing template assignments to social channels"""

    def __init__(self, db_client):
        self.db = db_client

    async def get_available_templates(self, supports_images: Optional[bool] = None) -> List[NewscardTemplate]:
        """Get all available newscard templates, optionally filtered by image support"""
        try:
            query = self.db.table('newscard_templates').select('*').eq('is_active', True)

            if supports_images is not None:
                query = query.eq('supports_images', supports_images)

            result = query.execute()

            templates = []
            for row in result.data or []:
                templates.append(NewscardTemplate(
                    id=row['id'],
                    template_name=row['template_name'],
                    template_display_name=row['template_display_name'],
                    template_path=row['template_path'],
                    supports_images=row['supports_images'],
                    description=row.get('description'),
                    is_active=row.get('is_active', True),
                    s3_url=row.get('s3_url'),
                    s3_bucket=row.get('s3_bucket'),
                    s3_key=row.get('s3_key'),
                    created_at=row.get('created_at'),
                    updated_at=row.get('updated_at')
                ))

            logger.info(f"Retrieved {len(templates)} available templates (supports_images={supports_images})")
            return templates

        except Exception as e:
            logger.exception(f"Failed to get available templates: {e}")
            return []

    async def get_template_assignments(self, tenant_id: str, social_account_id: Optional[str] = None) -> List[SocialChannelTemplateAssignment]:
        """Get template assignments for a tenant, optionally filtered by social account"""
        try:
            query = self.db.table('social_channel_template_assignments').select(
                'id, tenant_id, social_account_id, platform, template_with_image, '
                'template_without_image, created_at, updated_at'
            ).eq('tenant_id', tenant_id)

            if social_account_id:
                query = query.eq('social_account_id', social_account_id)

            result = query.execute()

            assignments = []
            for row in result.data or []:
                assignments.append(SocialChannelTemplateAssignment(
                    id=row['id'],
                    tenant_id=row['tenant_id'],
                    social_account_id=row['social_account_id'],
                    platform=Platform(row['platform']),
                    template_with_image=row.get('template_with_image'),
                    template_without_image=row.get('template_without_image'),
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                ))

            logger.info(f"Retrieved {len(assignments)} template assignments for tenant {tenant_id}")
            return assignments

        except Exception as e:
            logger.exception(f"Failed to get template assignments: {e}")
            return []

    async def assign_templates_to_social_channel(
        self,
        tenant_id: str,
        social_account_id: str,
        platform: Platform,
        template_with_image: Optional[str] = None,
        template_without_image: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """Assign templates to a social channel"""
        try:
            if not template_with_image and not template_without_image:
                logger.error("At least one template must be specified")
                return False

            # Validate that the templates exist
            if template_with_image:
                template_exists = await self._validate_template_exists(template_with_image, supports_images=True)
                if not template_exists:
                    logger.error(f"Template '{template_with_image}' does not exist or does not support images")
                    return False

            if template_without_image:
                template_exists = await self._validate_template_exists(template_without_image, supports_images=False)
                if not template_exists:
                    logger.error(f"Template '{template_without_image}' does not exist or supports images")
                    return False

            # Check if assignment already exists
            existing = self.db.table('social_channel_template_assignments').select('id').eq(
                'tenant_id', tenant_id
            ).eq('social_account_id', social_account_id).execute()

            assignment_data = {
                'tenant_id': tenant_id,
                'social_account_id': social_account_id,
                'platform': platform.value,
                'template_with_image': template_with_image,
                'template_without_image': template_without_image,
                'updated_at': datetime.utcnow().isoformat()
            }

            if existing.data:
                # Update existing assignment
                result = self.db.table('social_channel_template_assignments').update(
                    assignment_data
                ).eq('tenant_id', tenant_id).eq('social_account_id', social_account_id).execute()
                logger.info(f"Updated template assignment for social account {social_account_id}")
            else:
                # Create new assignment
                assignment_data.update({
                    'created_at': datetime.utcnow().isoformat(),
                    'created_by': user_id
                })
                result = self.db.table('social_channel_template_assignments').insert(assignment_data).execute()
                logger.info(f"Created new template assignment for social account {social_account_id}")

            return bool(result.data)

        except Exception as e:
            logger.exception(f"Failed to assign templates to social channel: {e}")
            return False

    async def remove_template_assignment(self, tenant_id: str, social_account_id: str) -> bool:
        """Remove template assignment for a social channel"""
        try:
            result = self.db.table('social_channel_template_assignments').delete().eq(
                'tenant_id', tenant_id
            ).eq('social_account_id', social_account_id).execute()

            logger.info(f"Removed template assignment for social account {social_account_id}")
            return True

        except Exception as e:
            logger.exception(f"Failed to remove template assignment: {e}")
            return False

    async def get_assigned_template_for_channel(
        self,
        tenant_id: str,
        social_account_id: str,
        has_images: bool = False
    ) -> Optional[str]:
        """Get the assigned template for a specific social channel and content type"""
        try:
            result = self.db.table('social_channel_template_assignments').select(
                'template_with_image, template_without_image'
            ).eq('tenant_id', tenant_id).eq('social_account_id', social_account_id).execute()

            if not result or not result.data or len(result.data) == 0:
                logger.info(f"No template assignment found for social account {social_account_id}")
                return None

            assignment = result.data[0]
            if has_images:
                template_name = assignment.get('template_with_image')
                if not template_name:
                    # Fallback to template without image if no image template is assigned
                    template_name = assignment.get('template_without_image')
                    logger.info(f"Using fallback template (no image template assigned) for social account {social_account_id}")
            else:
                template_name = assignment.get('template_without_image')
                if not template_name:
                    # Fallback to template with image if no regular template is assigned
                    template_name = assignment.get('template_with_image')
                    logger.info(f"Using fallback template (no regular template assigned) for social account {social_account_id}")

            if template_name:
                logger.info(f"Found assigned template '{template_name}' for social account {social_account_id} (has_images={has_images})")

            return template_name

        except Exception as e:
            logger.exception(f"Failed to get assigned template for channel: {e}")
            return None

    async def get_template_assignment_summary(self, tenant_id: str) -> Dict:
        """Get a summary of template assignments for all social channels in a tenant"""
        try:
            # Get all social accounts for the tenant
            social_accounts = self.db.table('social_accounts').select(
                'id, platform, account_name'
            ).eq('tenant_id', tenant_id).execute()

            # Get all template assignments
            assignments = await self.get_template_assignments(tenant_id)
            assignment_dict = {a.social_account_id: a for a in assignments}

            summary = {
                'tenant_id': tenant_id,
                'total_social_accounts': len(social_accounts.data or []),
                'accounts_with_assignments': len(assignments),
                'accounts_without_assignments': 0,
                'accounts': []
            }

            for account in social_accounts.data or []:
                account_id = account['id']
                assignment = assignment_dict.get(account_id)

                account_summary = {
                    'social_account_id': account_id,
                    'platform': account['platform'],
                    'account_name': account['account_name'],
                    'has_assignment': assignment is not None,
                    'template_with_image': assignment.template_with_image if assignment else None,
                    'template_without_image': assignment.template_without_image if assignment else None
                }

                if not assignment:
                    summary['accounts_without_assignments'] += 1

                summary['accounts'].append(account_summary)

            logger.info(f"Generated template assignment summary for tenant {tenant_id}")
            return summary

        except Exception as e:
            logger.exception(f"Failed to get template assignment summary: {e}")
            return {'error': str(e)}

    async def _validate_template_exists(self, template_name: str, supports_images: Optional[bool] = None) -> bool:
        """Validate that a template exists and optionally check image support"""
        try:
            query = self.db.table('newscard_templates').select('id').eq(
                'template_name', template_name
            ).eq('is_active', True)

            if supports_images is not None:
                query = query.eq('supports_images', supports_images)

            result = query.execute()
            return bool(result.data)

        except Exception as e:
            logger.exception(f"Failed to validate template existence: {e}")
            return False

    async def bulk_assign_default_templates(self, tenant_id: str) -> Dict:
        """Assign default templates to all social channels that don't have assignments"""
        try:
            # Get available templates
            templates_with_images = await self.get_available_templates(supports_images=True)
            templates_without_images = await self.get_available_templates(supports_images=False)

            if not templates_with_images or not templates_without_images:
                logger.error("No templates available for bulk assignment")
                return {'success': False, 'message': 'No templates available'}

            # Get social accounts without assignments
            social_accounts = self.db.table('social_accounts').select(
                'id, platform, account_name'
            ).eq('tenant_id', tenant_id).execute()

            existing_assignments = await self.get_template_assignments(tenant_id)
            assigned_accounts = {a.social_account_id for a in existing_assignments}

            unassigned_accounts = [
                account for account in (social_accounts.data or [])
                if account['id'] not in assigned_accounts
            ]

            # Assign default templates
            default_with_image = templates_with_images[0].template_name
            default_without_image = templates_without_images[0].template_name

            assigned_count = 0
            failed_count = 0

            for account in unassigned_accounts:
                success = await self.assign_templates_to_social_channel(
                    tenant_id=tenant_id,
                    social_account_id=account['id'],
                    platform=Platform(account['platform']),
                    template_with_image=default_with_image,
                    template_without_image=default_without_image
                )

                if success:
                    assigned_count += 1
                else:
                    failed_count += 1

            result = {
                'success': True,
                'total_accounts': len(unassigned_accounts),
                'assigned_count': assigned_count,
                'failed_count': failed_count,
                'default_template_with_image': default_with_image,
                'default_template_without_image': default_without_image
            }

            logger.info(f"Bulk assigned default templates: {result}")
            return result

        except Exception as e:
            logger.exception(f"Failed to bulk assign default templates: {e}")
            return {'success': False, 'message': str(e)}