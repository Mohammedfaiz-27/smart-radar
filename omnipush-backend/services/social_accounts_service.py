import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.database import db

logger = logging.getLogger(__name__)


@dataclass
class SocialAccount:
    """Data class representing a social media account"""
    id: str
    tenant_id: str
    user_id: str
    platform: str
    account_name: str
    account_id: str
    page_id: Optional[str] = None
    periskope_id: Optional[str] = None
    permissions: List[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    status: str = "connected"
    content_tone: str = "professional"
    custom_instructions: Optional[str] = None
    metadata: Dict[str, Any] = None
    connected_at: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    last_cursor: Optional[str] = None
    sync_config: Dict[str, Any] = None
    last_sync_status: str = "success"
    sync_error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []
        if self.metadata is None:
            self.metadata = {}
        if self.sync_config is None:
            self.sync_config = {}


class SocialAccountsService:
    """Service for managing social media accounts"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_accounts_by_tenant(self, tenant_id: str, platform: Optional[str] = None) -> List[SocialAccount]:
        """
        Get all social accounts for a tenant, optionally filtered by platform

        Args:
            tenant_id: The tenant ID
            platform: Optional platform filter ('facebook', 'instagram', 'whatsapp', etc.)

        Returns:
            List of SocialAccount objects
        """
        try:
            query = db.client.table('social_accounts').select('*').eq('tenant_id', tenant_id)

            if platform:
                query = query.eq('platform', platform)

            response = query.execute()

            if not response.data:
                self.logger.info(f"No social accounts found for tenant {tenant_id}, platform: {platform}")
                return []

            accounts = []
            for row in response.data:
                account = SocialAccount(
                    id=row['id'],
                    tenant_id=row['tenant_id'],
                    user_id=row['user_id'],
                    platform=row['platform'],
                    account_name=row['account_name'],
                    account_id=row['account_id'],
                    page_id=row.get('page_id'),
                    periskope_id=row.get('periskope_id'),
                    permissions=row.get('permissions', []),
                    access_token=row.get('access_token'),
                    refresh_token=row.get('refresh_token'),
                    token_expires_at=row.get('token_expires_at'),
                    status=row.get('status', 'connected'),
                    content_tone=row.get('content_tone', 'professional'),
                    custom_instructions=row.get('custom_instructions'),
                    metadata=row.get('metadata', {}),
                    connected_at=row.get('connected_at'),
                    last_sync=row.get('last_sync'),
                    last_cursor=row.get('last_cursor'),
                    sync_config=row.get('sync_config', {}),
                    last_sync_status=row.get('last_sync_status', 'success'),
                    sync_error_message=row.get('sync_error_message'),
                    created_at=row.get('created_at'),
                    updated_at=row.get('updated_at')
                )
                accounts.append(account)

            self.logger.info(f"Found {len(accounts)} social accounts for tenant {tenant_id}, platform: {platform}")
            return accounts

        except Exception as e:
            self.logger.error(f"Error fetching social accounts for tenant {tenant_id}: {e}")
            raise

    def get_account_by_id(self, account_id: str, tenant_id: str) -> Optional[SocialAccount]:
        """
        Get a specific social account by ID and tenant

        Args:
            account_id: The social account ID
            tenant_id: The tenant ID for security

        Returns:
            SocialAccount object or None if not found
        """
        try:
            response = db.client.table('social_accounts').select('*').eq('id', account_id).eq('tenant_id', tenant_id).maybe_single().execute()

            if not response.data:
                self.logger.warning(f"Social account {account_id} not found for tenant {tenant_id}")
                return None

            row = response.data
            account = SocialAccount(
                id=row['id'],
                tenant_id=row['tenant_id'],
                user_id=row['user_id'],
                platform=row['platform'],
                account_name=row['account_name'],
                account_id=row['account_id'],
                page_id=row.get('page_id'),
                periskope_id=row.get('periskope_id'),
                permissions=row.get('permissions', []),
                access_token=row.get('access_token'),
                refresh_token=row.get('refresh_token'),
                token_expires_at=row.get('token_expires_at'),
                status=row.get('status', 'connected'),
                content_tone=row.get('content_tone', 'professional'),
                custom_instructions=row.get('custom_instructions'),
                metadata=row.get('metadata', {}),
                connected_at=row.get('connected_at'),
                last_sync=row.get('last_sync'),
                last_cursor=row.get('last_cursor'),
                sync_config=row.get('sync_config', {}),
                last_sync_status=row.get('last_sync_status', 'success'),
                sync_error_message=row.get('sync_error_message'),
                created_at=row.get('created_at'),
                updated_at=row.get('updated_at')
            )

            self.logger.info(f"Found social account {account_id} for tenant {tenant_id}")
            return account

        except Exception as e:
            self.logger.error(f"Error fetching social account {account_id} for tenant {tenant_id}: {e}")
            return None

    def get_connected_accounts(self, tenant_id: str, platform: Optional[str] = None) -> List[SocialAccount]:
        """
        Get all connected (active) social accounts for a tenant

        Args:
            tenant_id: The tenant ID
            platform: Optional platform filter

        Returns:
            List of connected SocialAccount objects
        """
        try:
            query = db.client.table('social_accounts').select('*').eq('tenant_id', tenant_id).eq('status', 'connected')

            if platform:
                query = query.eq('platform', platform)

            response = query.execute()

            if not response.data:
                self.logger.info(f"No connected social accounts found for tenant {tenant_id}, platform: {platform}")
                return []

            accounts = []
            for row in response.data:
                # Filter out accounts with missing required credentials
                if self._has_valid_credentials(row):
                    account = SocialAccount(
                        id=row['id'],
                        tenant_id=row['tenant_id'],
                        user_id=row['user_id'],
                        platform=row['platform'],
                        account_name=row['account_name'],
                        account_id=row['account_id'],
                        page_id=row.get('page_id'),
                        periskope_id=row.get('periskope_id'),
                        permissions=row.get('permissions', []),
                        access_token=row.get('access_token'),
                        refresh_token=row.get('refresh_token'),
                        token_expires_at=row.get('token_expires_at'),
                        status=row.get('status', 'connected'),
                        content_tone=row.get('content_tone', 'professional'),
                        custom_instructions=row.get('custom_instructions'),
                        metadata=row.get('metadata', {}),
                        connected_at=row.get('connected_at'),
                        last_sync=row.get('last_sync'),
                        last_cursor=row.get('last_cursor'),
                        sync_config=row.get('sync_config', {}),
                        last_sync_status=row.get('last_sync_status', 'success'),
                        sync_error_message=row.get('sync_error_message'),
                        created_at=row.get('created_at'),
                        updated_at=row.get('updated_at')
                    )
                    accounts.append(account)

            self.logger.info(f"Found {len(accounts)} connected social accounts for tenant {tenant_id}, platform: {platform}")
            return accounts

        except Exception as e:
            self.logger.error(f"Error fetching connected social accounts for tenant {tenant_id}: {e}")
            raise

    def _has_valid_credentials(self, account_row: Dict[str, Any]) -> bool:
        """
        Check if a social account has valid credentials for posting

        Args:
            account_row: Database row data for the account

        Returns:
            True if account has valid credentials, False otherwise
        """
        platform = account_row.get('platform')

        if platform in ['facebook', 'instagram', 'threads']:
            # Facebook-based platforms need access_token and either page_id or account_id
            return (
                account_row.get('access_token') and
                (account_row.get('page_id') or account_row.get('account_id'))
            )
        elif platform == 'whatsapp':
            # WhatsApp needs periskope_id (and API key from env)
            return bool(account_row.get('periskope_id'))
        else:
            # For other platforms, just check if we have an access token
            return bool(account_row.get('access_token'))

    def update_last_sync(self, account_id: str, tenant_id: str, status: str = "success", error_message: Optional[str] = None):
        """
        Update the last sync information for a social account

        Args:
            account_id: The social account ID
            tenant_id: The tenant ID for security
            status: Sync status ('success', 'error', etc.)
            error_message: Optional error message if status is 'error'
        """
        try:
            update_data = {
                'last_sync': datetime.utcnow().isoformat(),
                'last_sync_status': status,
                'updated_at': datetime.utcnow().isoformat()
            }

            if error_message:
                update_data['sync_error_message'] = error_message
            elif status == 'success':
                update_data['sync_error_message'] = None

            db.client.table('social_accounts').update(update_data).eq('id', account_id).eq('tenant_id', tenant_id).execute()

            self.logger.info(f"Updated sync status for account {account_id}: {status}")

        except Exception as e:
            self.logger.error(f"Error updating sync status for account {account_id}: {e}")