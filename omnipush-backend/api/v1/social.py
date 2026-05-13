from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
from uuid import uuid4
import logging
import base64
import json
from cryptography.fernet import Fernet

from core.middleware import get_current_user, get_tenant_context, TenantContext
from core.config import settings
from models.auth import JWTPayload
from models.social import (
    ConnectAccountRequest,
    UpdateAccountRequest,
    ListAccountsResponse,
    ConnectAccountResponse,
    DisconnectAccountResponse,
    SocialAccount,
    AccountStatus,
    ConnectionMethod,
)
from models.content import Platform
from services.social_fetch_service import SocialFetchService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/social-accounts", tags=["social accounts"])


def get_encryption_key() -> bytes:
    """Get or generate encryption key for storing tokens"""
    # In production, this should be stored securely (e.g., AWS KMS, Azure Key Vault)
    # For demo, we'll use a key derived from the JWT secret
    key = base64.urlsafe_b64encode(settings.jwt_secret_key.encode()[:32].ljust(32, b"0"))
    return key


def encrypt_token(token: str) -> str:
    """Encrypt a token for secure storage"""
    try:
        f = Fernet(get_encryption_key())
        encrypted_token = f.encrypt(token.encode())
        return base64.urlsafe_b64encode(encrypted_token).decode()
    except Exception as e:
        logger.exception(f"Failed to encrypt token: {e}")
        raise


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a stored token"""
    try:
        f = Fernet(get_encryption_key())
        decoded_token = base64.urlsafe_b64decode(encrypted_token.encode())
        return f.decrypt(decoded_token).decode()
    except Exception as e:
        logger.exception(f"Failed to decrypt token: {e}")
        raise


def obscure_token(token: str) -> str:
    """Obscure a token for display purposes"""
    if not token or len(token) < 10:
        return "****"

    # Show first 4 and last 6 characters
    return f"{token[:4]}******{token[-6:]}"


async def exchange_auth_code_for_token(platform: Platform, auth_code: str) -> dict:
    """
    Exchange OAuth authorization code for access token
    This would integrate with each platform's OAuth flow
    """
    # This is a placeholder implementation
    # In production, you would implement the OAuth flow for each platform

    if platform == Platform.FACEBOOK:
        # Facebook OAuth flow
        # 1. Exchange auth code for access token
        # 2. Get long-lived token
        # 3. Get user/page info
        return {
            "access_token": f"fb_mock_token_{auth_code}",
            "refresh_token": None,
            "expires_in": 5184000,  # 60 days
            "account_id": "mock_fb_page_id",
            "account_name": "Mock Facebook Page",
            "permissions": ["publish_post", "read_insights"],
        }

    elif platform == Platform.INSTAGRAM:
        # Instagram OAuth flow
        return {
            "access_token": f"ig_mock_token_{auth_code}",
            "refresh_token": None,
            "expires_in": 5184000,
            "account_id": "mock_ig_account_id",
            "account_name": "mock_instagram_handle",
            "permissions": ["publish_post", "read_insights"],
        }

    elif platform == Platform.TWITTER:
        # Twitter OAuth 2.0 flow
        return {
            "access_token": f"tw_mock_token_{auth_code}",
            "refresh_token": f"tw_refresh_token_{auth_code}",
            "expires_in": 7200,  # 2 hours
            "account_id": "mock_twitter_id",
            "account_name": "@mock_twitter",
            "permissions": ["tweet", "read"],
        }

    elif platform == Platform.LINKEDIN:
        # LinkedIn OAuth flow
        return {
            "access_token": f"li_mock_token_{auth_code}",
            "refresh_token": f"li_refresh_token_{auth_code}",
            "expires_in": 5184000,
            "account_id": "mock_linkedin_id",
            "account_name": "Mock LinkedIn Company",
            "permissions": ["w_member_social", "r_liteprofile"],
        }

    elif platform == Platform.WHATSAPP:
        # WhatsApp OAuth flow
        return {
            "access_token": f"wa_mock_token_{auth_code}",
            "refresh_token": None,
            "expires_in": 5184000,
            "account_id": "mock_whatsapp_periskope_id",
            "account_name": "Mock WhatsApp Business",
            "permissions": ["send_message", "read_message"],
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Platform {platform.value} not supported yet",
        )


@router.get("", response_model=ListAccountsResponse)
async def list_connected_accounts(
    page: int = 1,
    limit: int = 25,
    status: str = None,
    platform: str = None,
    search: str = None,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """List all connected social media accounts for the tenant with pagination and filters"""
    try:
        # Build base query with pagination support
        query = ctx.table("social_accounts").select(
            "id, platform, account_name, account_id, account_link, status, permissions, "
            "connected_at, last_sync, page_id, periskope_id, content_tone, custom_instructions, access_token",
            count="exact"
        )

        # Apply filters
        if status:
            query = query.eq("status", status)

        if platform:
            query = query.eq("platform", platform)

        if search:
            # Search in account_name or account_id
            query = query.or_(
                f"account_name.ilike.%{search}%,"
                f"account_id.ilike.%{search}%"
            )

        # Get total count for pagination
        count_response = query.execute()
        total_count = count_response.count if hasattr(count_response, 'count') else len(count_response.data or [])

        # Apply pagination
        offset = (page - 1) * limit
        accounts_response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        accounts = []
        for account_data in accounts_response.data or []:
            # Decrypt and obscure access token if present
            access_token_obscured = None
            if account_data.get("access_token"):
                try:
                    access_token_obscured = obscure_token(account_data["access_token"])
                except Exception as e:
                    logger.warning(
                        f"Failed to decrypt/obscure token for account {account_data['id']}: {e}"
                    )
                    access_token_obscured = "****"

            accounts.append(
                SocialAccount(
                    id=account_data["id"],
                    platform=Platform(account_data["platform"]),
                    account_name=account_data["account_name"],
                    account_id=account_data["account_id"],
                    account_link=account_data.get("account_link"),
                    status=AccountStatus(account_data["status"]),
                    permissions=account_data.get("permissions", []),
                    connected_at=datetime.fromisoformat(account_data["connected_at"]),
                    last_sync=(
                        datetime.fromisoformat(account_data["last_sync"])
                        if account_data.get("last_sync")
                        else None
                    ),
                    page_id=account_data.get("page_id"),
                    periskope_id=account_data.get("periskope_id"),
                    content_tone=account_data.get("content_tone", "professional"),
                    custom_instructions=account_data.get("custom_instructions"),
                    access_token_obscured=access_token_obscured,
                )
            )

        # Calculate pagination metadata
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

        return ListAccountsResponse(
            accounts=accounts,
            pagination={
                "page": page,
                "limit": limit,
                "total": total_count,
                "total_pages": total_pages
            }
        )

    except Exception as e:
        logger.exception(f"Failed to list social accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve social accounts",
        )


@router.get("/all", response_model=list)
async def list_all_accounts_summary(
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """
    Get a lightweight list of ALL social accounts (no pagination).
    Returns only essential fields for use in channel groups and selectors.
    """
    try:
        accounts_response = (
            ctx.table("social_accounts")
            .select("id, platform, account_name, account_id, status")
            .order("created_at", desc=True)
            .execute()
        )

        return [
            {
                "id": account["id"],
                "platform": account["platform"],
                "account_name": account["account_name"],
                "account_id": account["account_id"],
                "status": account["status"],
            }
            for account in accounts_response.data or []
        ]

    except Exception as e:
        logger.exception(f"Failed to list all social accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve social accounts",
        )


@router.post("/connect", response_model=ConnectAccountResponse, status_code=status.HTTP_201_CREATED)
async def connect_social_account(
    request: ConnectAccountRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Connect a new social media account via OAuth or manual credentials"""
    try:
        if request.connection_method == ConnectionMethod.OAUTH:
            # Validate OAuth request
            if not request.auth_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Auth code is required for OAuth connection",
                )

            # Exchange auth code for access token
            token_data = await exchange_auth_code_for_token(request.platform, request.auth_code)

            account_name = token_data["account_name"]
            account_id = token_data["account_id"]
            access_token = token_data["access_token"]
            refresh_token = token_data.get("refresh_token")
            permissions = token_data.get("permissions", [])

            # Calculate token expiration
            token_expires_at = None
            if token_data.get("expires_in"):
                from datetime import timedelta

                token_expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])

        elif request.connection_method == ConnectionMethod.MANUAL:
            # Validate manual connection request
            if not request.account_name:  # or not request.access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Account name and access token are required for manual connection",
                )

            # Platform-specific validation
            if request.platform == Platform.FACEBOOK:
                if not request.page_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Page ID is required for Facebook manual connection",
                    )
                account_id = request.page_id
            elif request.platform == Platform.WHATSAPP:
                if not request.periskope_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Periskope ID is required for WhatsApp manual connection",
                    )
                account_id = request.periskope_id
            else:
                # For Instagram and other platforms, use account name as ID
                account_id = request.account_name

            account_name = request.account_name
            access_token = request.access_token
            refresh_token = None
            permissions = ["manual_connection"]  # Default permissions for manual connection
            token_expires_at = None  # Manual tokens don't have expiration info

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid connection method"
            )

        # Check if account is already connected
        existing_account = (
            ctx.table("social_accounts")
            .select("id")
            .eq("tenant_id", ctx.tenant_id)
            .eq("platform", request.platform.value)
            .eq("account_id", account_id)
            .execute()
        )

        if existing_account.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Account already connected"
            )

        # Encrypt tokens for secure storage
        encrypted_access_token = encrypt_token(access_token)
        encrypted_refresh_token = None
        if refresh_token:
            encrypted_refresh_token = encrypt_token(refresh_token)

        # Prepare platform-specific fields
        platform_fields = {}
        if request.platform == Platform.FACEBOOK and request.page_id:
            platform_fields["page_id"] = request.page_id
        elif request.platform == Platform.WHATSAPP and request.periskope_id:
            platform_fields["periskope_id"] = request.periskope_id

        # Save to database
        account_id_uuid = str(uuid4())
        account_data = {
            "id": account_id_uuid,
            "tenant_id": current_user.tenant_id,
            "platform": request.platform.value,
            "account_name": account_name,
            "account_id": account_id,
            "user_id": current_user.sub,
            "status": AccountStatus.CONNECTED.value,
            "content_tone": request.content_tone or "professional",
            "custom_instructions": request.custom_instructions,
            "auto_image_search": request.auto_image_search or False,
            "permissions": permissions,
            "access_token": encrypted_access_token,
            "refresh_token": encrypted_refresh_token,
            "token_expires_at": token_expires_at.isoformat() if token_expires_at else None,
            "connected_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            **platform_fields,
        }

        result = ctx.db.client.table("social_accounts").insert(account_data).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save social account",
            )

        return ConnectAccountResponse(
            id=account_id_uuid,
            platform=request.platform,
            account_name=account_name,
            status=AccountStatus.CONNECTED,
            connected_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to connect social account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect social account",
        )


@router.put("/{account_id}", response_model=SocialAccount)
async def update_social_account(
    account_id: str,
    request: UpdateAccountRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Update social media account settings"""
    try:
        # Check if account exists
        account_response = (
            ctx.table("social_accounts")
            .select(
                "id, platform, account_name, account_id, account_link, status, permissions, "
                "connected_at, last_sync, page_id, periskope_id, content_tone, custom_instructions"
            )
            .eq("tenant_id", ctx.tenant_id)
            .eq("id", account_id)
            .single()
            .execute()
        )

        if not account_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found"
            )

        # Prepare update data
        update_data = {}
        if request.content_tone is not None:
            update_data["content_tone"] = request.content_tone
        if request.custom_instructions is not None:
            update_data["custom_instructions"] = request.custom_instructions
        if request.auto_image_search is not None:
            update_data["auto_image_search"] = request.auto_image_search
        if request.access_token is not None and request.access_token != "":
            # Encrypt the new access token before storing
            encrypted_access_token = encrypt_token(request.access_token)
            update_data["access_token"] = encrypted_access_token
        if request.page_id is not None:
            update_data["page_id"] = request.page_id
        if request.periskope_id is not None:
            update_data["periskope_id"] = request.periskope_id

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
            )

        update_data["updated_at"] = datetime.utcnow().isoformat()

        # Update in database
        result = (
            ctx.table("social_accounts")
            .update(update_data)
            .eq("tenant_id", ctx.tenant_id)
            .eq("id", account_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update social account",
            )

        # Get updated account data
        updated_account = (
            ctx.table("social_accounts")
            .select(
                "id, platform, account_name, account_id, account_link, status, permissions, "
                "connected_at, last_sync, page_id, periskope_id, content_tone, custom_instructions, access_token"
            )
            .eq("tenant_id", ctx.tenant_id)
            .eq("id", account_id)
            .single()
            .execute()
        )

        account_data = updated_account.data

        # Decrypt and obscure access token if present
        access_token_obscured = None
        if account_data.get("access_token"):
            try:
                access_token_obscured = obscure_token(account_data["access_token"])
            except Exception as e:
                logger.warning(
                    f"Failed to decrypt/obscure token for account {account_data['id']}: {e}"
                )
                access_token_obscured = "****"

        return SocialAccount(
            id=account_data["id"],
            platform=Platform(account_data["platform"]),
            account_name=account_data["account_name"],
            account_id=account_data["account_id"],
            account_link=account_data.get("account_link"),
            status=AccountStatus(account_data["status"]),
            permissions=account_data.get("permissions", []),
            connected_at=datetime.fromisoformat(account_data["connected_at"]),
            last_sync=(
                datetime.fromisoformat(account_data["last_sync"])
                if account_data.get("last_sync")
                else None
            ),
            page_id=account_data.get("page_id"),
            periskope_id=account_data.get("periskope_id"),
            content_tone=account_data.get("content_tone", "professional"),
            custom_instructions=account_data.get("custom_instructions"),
            access_token_obscured=access_token_obscured,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update social account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update social account",
        )


@router.delete("/{account_id}", response_model=DisconnectAccountResponse)
async def disconnect_social_account(
    account_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Disconnect a social media account"""
    try:
        # Check if account exists
        account_response = (
            ctx.table("social_accounts")
            .select("id, platform, account_id ")  # access_token_encrypted'
            .eq("tenant_id", ctx.tenant_id)
            .eq("id", account_id)
            .single()
            .execute()
        )

        if not account_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found"
            )

        account = account_response.data

        # In production, you would:
        # 1. Revoke the access token with the platform
        # 2. Clean up any webhook subscriptions
        # 3. Notify other systems about the disconnection

        # For demo, we'll just delete from database
        result = (
            ctx.table("social_accounts")
            .delete()
            .eq("tenant_id", ctx.tenant_id)
            .eq("id", account_id)
            .execute()
        )

        return DisconnectAccountResponse()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to disconnect social account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect social account",
        )


@router.post("/{account_id}/refresh-token")
async def refresh_social_token(
    account_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Refresh access token for a social account"""
    try:
        # Get account details
        account_response = (
            ctx.table("social_accounts")
            .select("id, platform, refresh_token, status")
            .eq("tenant_id", ctx.tenant_id)
            .eq("id", account_id)
            .single()
            .execute()
        )

        if not account_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found"
            )

        account = account_response.data

        if not account.get("refresh_token"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No refresh token available for this account",
            )

        # Decrypt refresh token
        refresh_token = decrypt_token(account["refresh_token"])

        # Refresh token with platform API
        # This would make actual API calls to refresh tokens
        # For demo, we'll just update the timestamps

        update_data = {
            "last_sync": datetime.utcnow().isoformat(),
            "status": AccountStatus.CONNECTED.value,
            "updated_at": datetime.utcnow().isoformat(),
        }

        result = (
            ctx.table("social_accounts")
            .update(update_data)
            .eq("tenant_id", ctx.tenant_id)
            .eq("id", account_id)
            .execute()
        )

        return {"message": "Token refreshed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to refresh social token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to refresh token"
        )


@router.get("/connection-requirements/{platform}")
async def get_connection_requirements(
    platform: Platform,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Get platform-specific connection requirements for manual connection"""
    try:
        requirements = {
            "platform": platform.value,
            "oauth_supported": True,
            "manual_supported": False,
            "oauth_fields": [],
            "manual_fields": [],
            "help_text": "",
        }

        if platform == Platform.FACEBOOK:
            requirements.update(
                {
                    "manual_supported": True,
                    "oauth_fields": ["auth_code"],
                    "manual_fields": ["account_name", "page_id", "access_token"],
                    "help_text": "For manual connection, you need your Facebook Page Name, Page ID, and Access Token. Page ID can be found in your Facebook Page settings.",
                }
            )

        elif platform == Platform.INSTAGRAM:
            requirements.update(
                {
                    "manual_supported": True,
                    "oauth_fields": ["auth_code"],
                    "manual_fields": ["account_name", "access_token"],
                    "help_text": "For manual connection, you need your Instagram username and Access Token.",
                }
            )

        elif platform == Platform.WHATSAPP:
            requirements.update(
                {
                    "manual_supported": True,
                    "oauth_fields": ["auth_code"],
                    "manual_fields": ["account_name", "periskope_id"],
                    "help_text": "For manual connection, you need your WhatsApp Business account name and Periskope ID.",
                }
            )

        elif platform == Platform.TWITTER:
            requirements.update(
                {
                    "oauth_fields": ["auth_code"],
                    "help_text": "Twitter only supports OAuth connection.",
                }
            )

        elif platform == Platform.LINKEDIN:
            requirements.update(
                {
                    "oauth_fields": ["auth_code"],
                    "help_text": "LinkedIn only supports OAuth connection.",
                }
            )

        else:
            requirements.update(
                {
                    "oauth_supported": False,
                    "help_text": f"Manual connection not supported for {platform.value}",
                }
            )

        return requirements

    except Exception as e:
        logger.exception(f"Failed to get connection requirements: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get connection requirements",
        )


@router.post("/validate-credentials")
async def validate_manual_credentials(
    request: ConnectAccountRequest,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Validate manual connection credentials before connecting"""
    try:
        if request.connection_method != ConnectionMethod.MANUAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This endpoint is only for manual connection validation",
            )

        # Validate required fields
        if not request.account_name or not request.access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account name and access token are required",
            )

        # Platform-specific validation
        validation_result = {
            "is_valid": True,
            "platform": request.platform.value,
            "account_name": request.account_name,
            "message": "Credentials are valid",
        }

        if request.platform == Platform.FACEBOOK:
            if not request.page_id:
                validation_result["is_valid"] = False
                validation_result["message"] = "Page ID is required for Facebook"
            else:
                # In production, you would validate the Facebook token and page ID
                validation_result["account_id"] = request.page_id

        elif request.platform == Platform.INSTAGRAM:
            # In production, you would validate the Instagram token
            validation_result["account_id"] = request.account_name

        elif request.platform == Platform.WHATSAPP:
            if not request.periskope_id:
                validation_result["is_valid"] = False
                validation_result["message"] = "Periskope ID is required for WhatsApp"
            else:
                # In production, you would validate the WhatsApp Periskope ID
                validation_result["account_id"] = request.periskope_id

        else:
            validation_result["is_valid"] = False
            validation_result["message"] = (
                f"Manual connection not supported for {request.platform.value}"
            )

        return validation_result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to validate credentials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate credentials",
        )


@router.get("/{account_id}/status")
async def check_account_status(
    account_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Check the status of a social media account connection"""
    try:
        account_response = (
            ctx.table("social_accounts")
            .select("id, platform, account_name, status, permissions, token_expires_at, last_sync")
            .eq("tenant_id", ctx.tenant_id)
            .eq("id", account_id)
            .single()
            .execute()
        )

        if not account_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found"
            )

        account = account_response.data

        # Check if token is expired
        is_token_expired = False
        if account.get("token_expires_at"):
            expires_at = datetime.fromisoformat(account["token_expires_at"])
            is_token_expired = datetime.utcnow() > expires_at

        return {
            "id": account["id"],
            "platform": account["platform"],
            "account_name": account["account_name"],
            "status": account["status"],
            "permissions": account.get("permissions", []),
            "is_token_expired": is_token_expired,
            "last_sync": account.get("last_sync"),
            "needs_refresh": is_token_expired or account["status"] == AccountStatus.ERROR.value,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to check account status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check account status",
        )


@router.post("/{account_id}/fetch-content")
async def fetch_social_content(
    account_id: str,
    query: str = None,
    max_items: int = 20,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Fetch social media content with cursor tracking and deduplication"""
    try:
        # Verify account exists and belongs to tenant
        account_response = (
            ctx.table("social_accounts")
            .select("id, platform, account_name, status")
            .eq("tenant_id", ctx.tenant_id)
            .eq("id", account_id)
            .single()
            .execute()
        )

        if not account_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found"
            )

        account = account_response.data

        if account["status"] != AccountStatus.CONNECTED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Account is not connected"
            )

        # Initialize social fetch service
        social_fetch_service = SocialFetchService(ctx.db.client)

        # Fetch content based on platform
        platform = Platform(account["platform"])
        success, posts = await social_fetch_service.fetch_social_content(
            account_id, platform, query, max_items
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch social content",
            )

        return {
            "success": True,
            "account_id": account_id,
            "platform": account["platform"],
            "query": query,
            "posts_fetched": len(posts),
            "message": f"Successfully fetched {len(posts)} posts from {account['account_name']}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to fetch social content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch social content",
        )


@router.get("/{account_id}/sync-state")
async def get_sync_state(
    account_id: str,
    sync_type: str = "posts",
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Get the current sync state for a social account"""
    try:
        # Verify account exists and belongs to tenant
        account_response = (
            ctx.table("social_accounts")
            .select("id, platform, account_name")
            .eq("tenant_id", ctx.tenant_id)
            .eq("id", account_id)
            .single()
            .execute()
        )

        if not account_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found"
            )

        # Get sync state
        social_fetch_service = SocialFetchService(ctx.db.client)
        sync_state = await social_fetch_service.get_sync_state(account_id, sync_type)

        return {
            "account_id": account_id,
            "platform": account_response.data["platform"],
            "sync_type": sync_type,
            "sync_state": sync_state,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get sync state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get sync state"
        )


@router.get("/content/unprocessed")
async def get_unprocessed_content(
    platform: Platform = None,
    limit: int = 50,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Get unprocessed social media content for moderation/analysis"""
    try:
        social_fetch_service = SocialFetchService(ctx.db.client)
        content = await social_fetch_service.get_unprocessed_content(ctx.tenant_id, platform, limit)

        return {
            "tenant_id": ctx.tenant_id,
            "platform": platform.value if platform else None,
            "content_count": len(content),
            "content": content,
        }

    except Exception as e:
        logger.exception(f"Failed to get unprocessed content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get unprocessed content",
        )


@router.post("/content/mark-processed")
async def mark_content_processed(
    content_ids: list[str],
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Mark social media content as processed"""
    try:
        social_fetch_service = SocialFetchService(ctx.db.client)
        success = await social_fetch_service.mark_content_processed(content_ids)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to mark content as processed",
            )

        return {
            "success": True,
            "content_ids": content_ids,
            "message": f"Marked {len(content_ids)} content items as processed",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to mark content as processed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark content as processed",
        )


@router.post("/{account_id}/reset-sync")
async def reset_sync_state(
    account_id: str,
    sync_type: str = "posts",
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Reset sync state for a social account (removes cursor tracking)"""
    try:
        # Verify account exists and belongs to tenant
        account_response = (
            ctx.table("social_accounts")
            .select("id, platform, account_name")
            .eq("tenant_id", ctx.tenant_id)
            .eq("id", account_id)
            .single()
            .execute()
        )

        if not account_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found"
            )

        # Reset sync state by updating with null values
        social_fetch_service = SocialFetchService(ctx.db.client)
        success = await social_fetch_service.update_sync_state(
            account_id, sync_type, last_cursor=None, last_item_id=None, status="reset"
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset sync state",
            )

        return {
            "success": True,
            "account_id": account_id,
            "sync_type": sync_type,
            "message": "Sync state reset successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to reset sync state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reset sync state"
        )
