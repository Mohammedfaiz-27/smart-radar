from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from uuid import UUID
import logging

from .database import get_database, SupabaseClient
from models.auth import JWTPayload, UserRole

logger = logging.getLogger(__name__)

# HTTP Bearer scheme kept so existing clients that send a token don't get
# a 422 "field required" error — but the token is never validated.
security = HTTPBearer(auto_error=False)

# Internal admin email used as the bypass identity
_INTERNAL_EMAIL = "admin@smartradar.internal"

# Cached bypass payload — populated on first request
_bypass_payload: Optional[JWTPayload] = None
_bypass_tenant: Optional[dict] = None


def _make_fallback_payload() -> JWTPayload:
    """Return a safe fallback when the DB lookup fails."""
    return JWTPayload(
        sub="00000000-0000-0000-0000-000000000001",
        tenant_id="00000000-0000-0000-0000-000000000001",
        role=UserRole.ADMIN,
        exp=9999999999,
        iat=0,
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: SupabaseClient = Depends(get_database),
) -> JWTPayload:
    """
    Auth bypass — JWT validation is disabled.
    Returns the internal admin user's real IDs so tenant-scoped DB
    queries continue to work correctly.
    """
    global _bypass_payload

    if _bypass_payload is not None:
        return _bypass_payload

    try:
        resp = db.service_client.table("users").select(
            "id, tenant_id, role, status"
        ).eq("email", _INTERNAL_EMAIL).maybe_single().execute()

        if resp.data and resp.data.get("status") == "active":
            _bypass_payload = JWTPayload(
                sub=resp.data["id"],
                tenant_id=resp.data["tenant_id"],
                role=UserRole(resp.data.get("role", "admin")),
                exp=9999999999,
                iat=0,
            )
            logger.info(
                f"Auth bypass: resolved internal admin "
                f"user={resp.data['id']} tenant={resp.data['tenant_id']}"
            )
            return _bypass_payload
    except Exception as e:
        logger.warning(f"Auth bypass: DB lookup failed ({e}), using fallback identity")

    _bypass_payload = _make_fallback_payload()
    return _bypass_payload


async def get_current_tenant(
    current_user: JWTPayload = Depends(get_current_user),
    db: SupabaseClient = Depends(get_database),
) -> dict:
    """
    Tenant bypass — returns the internal admin tenant without subscription checks.
    """
    global _bypass_tenant

    if _bypass_tenant is not None:
        return _bypass_tenant

    try:
        resp = db.service_client.table("tenants").select(
            "id, name, subscription_tier, subscription_status"
        ).eq("id", current_user.tenant_id).maybe_single().execute()

        if resp.data:
            _bypass_tenant = resp.data
            return _bypass_tenant
    except Exception as e:
        logger.warning(f"Auth bypass: tenant lookup failed ({e}), using fallback")

    _bypass_tenant = {
        "id": current_user.tenant_id,
        "name": "Smart Radar",
        "subscription_tier": "enterprise",
        "subscription_status": "active",
    }
    return _bypass_tenant


def require_roles(*allowed_roles: UserRole):
    """Role check — always passes in bypass mode."""
    def role_checker(current_user: JWTPayload = Depends(get_current_user)):
        return current_user
    return role_checker


def require_admin(current_user: JWTPayload = Depends(get_current_user)):
    """Always passes in bypass mode."""
    return current_user


def require_editor_or_above(current_user: JWTPayload = Depends(get_current_user)):
    """Always passes in bypass mode."""
    return current_user


async def validate_tenant_header(
    request: Request,
    current_user: JWTPayload = Depends(get_current_user),
) -> None:
    """Tenant-header check — skipped in bypass mode."""
    return None


class TenantContext:
    """Context manager for tenant-scoped database operations."""

    def __init__(self, db: SupabaseClient, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    def table(self, table_name: str):
        return self.db.client.table(table_name)

    def get_tenant_filter(self, table_name: str):
        tenant_scoped_tables = [
            "users", "posts", "media", "social_accounts",
            "workflows", "analytics", "webhooks",
        ]
        if table_name in tenant_scoped_tables:
            return {"tenant_id": self.tenant_id}
        return {}


def get_tenant_context(
    current_user: JWTPayload = Depends(get_current_user),
    db: SupabaseClient = Depends(get_database),
) -> TenantContext:
    return TenantContext(db, current_user.tenant_id, current_user.sub)
