from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timedelta
import logging

from core.database import get_database, SupabaseClient
from core.middleware import get_current_user, require_admin, get_current_tenant
from models.auth import JWTPayload, SubscriptionTier
from models.tenant import (
    UpdateTenantRequest,
    ChangeSubscriptionRequest,
    GetTenantResponse,
    UpdateTenantResponse,
    GetSubscriptionResponse,
    ChangeSubscriptionResponse,
    GetInvoicesResponse,
    TenantDetails,
    SubscriptionDetails,
    SubscriptionStatus,
    Invoice,
)
from models.base import UsageLimits, CurrentUsage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tenants", tags=["tenant management"])


def get_usage_limits(tier: SubscriptionTier) -> UsageLimits:
    """Get usage limits for subscription tier"""
    limits = {
        SubscriptionTier.BASIC: UsageLimits(
            users=3, posts_per_month=100, ai_generations_per_month=10, storage_gb=10
        ),
        SubscriptionTier.PRO: UsageLimits(
            users=10, posts_per_month=1000, ai_generations_per_month=100, storage_gb=50
        ),
        SubscriptionTier.ENTERPRISE: UsageLimits(
            users=999999,  # "unlimited"
            posts_per_month=999999,
            ai_generations_per_month=1000,
            storage_gb=500,
        ),
    }
    return limits.get(tier, limits[SubscriptionTier.BASIC])


async def calculate_current_usage(tenant_id: str, db: SupabaseClient) -> CurrentUsage:
    """Calculate current usage for tenant"""
    try:
        # Count active users
        users_response = (
            db.client.table("users")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .eq("status", "active")
            .execute()
        )

        user_count = users_response.count or 0

        # Count posts this month
        current_month = datetime.utcnow().strftime("%Y-%m-01")
        posts_response = (
            db.client.table("posts")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .gte("created_at", current_month)
            .execute()
        )

        posts_count = posts_response.count or 0

        # Count AI generations this month (from media table)
        ai_media_response = (
            db.client.table("media")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .not_.is_("generation_prompt", "null")
            .gte("created_at", current_month)
            .execute()
        )

        ai_count = ai_media_response.count or 0

        # Calculate storage usage (sum of media file sizes)
        try:
            storage_response = (
                db.client.table("media").select("size").eq("tenant_id", tenant_id).execute()
            )

            total_bytes = sum(item.get("size", 0) for item in storage_response.data or [])
            storage_gb = total_bytes / (1024 * 1024 * 1024)  # Convert to GB
        except Exception as storage_error:
            # Fallback: count media files and estimate size
            logger.warning(f"Could not calculate exact storage usage: {storage_error}")
            media_count_response = (
                db.client.table("media")
                .select("id", count="exact")
                .eq("tenant_id", tenant_id)
                .execute()
            )

            media_count = media_count_response.count or 0
            # Estimate 1MB per media file as fallback
            estimated_bytes = media_count * 1024 * 1024
            storage_gb = estimated_bytes / (1024 * 1024 * 1024)

        return CurrentUsage(
            users=user_count,
            posts_this_month=posts_count,
            ai_generations_this_month=ai_count,
            storage_used_gb=round(storage_gb, 2),
        )

    except Exception as e:
        logger.exception(f"Failed to calculate usage: {e}")
        # Return zero usage on error
        return CurrentUsage(
            users=0, posts_this_month=0, ai_generations_this_month=0, storage_used_gb=0.0
        )


@router.get("/me", response_model=GetTenantResponse)
async def get_tenant_details(
    current_user: JWTPayload = Depends(get_current_user),
    tenant: dict = Depends(get_current_tenant),
    db: SupabaseClient = Depends(get_database),
):
    """
    Get current tenant details with usage information
    """
    try:
        logger.info(f"Fetching tenant details for tenant_id: {current_user.tenant_id}")

        # Get full tenant details
        tenant_response = (
            db.client.table("tenants").select("*").eq("id", current_user.tenant_id).execute()
        )

        logger.info(f"Tenant query response: {tenant_response.data}")

        if not tenant_response.data or len(tenant_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant not found for ID: {current_user.tenant_id}",
            )

        tenant_data = tenant_response.data[0]
        subscription_tier = SubscriptionTier(tenant_data["subscription_tier"])

        # Get usage limits and current usage (not implemented yet)
        usage_limits = get_usage_limits(subscription_tier)
        current_usage = await calculate_current_usage(current_user.tenant_id, db)

        return GetTenantResponse(
            id=tenant_data["id"],
            name=tenant_data["name"],
            subscription_tier=subscription_tier,
            subscription_status=SubscriptionStatus(tenant_data["subscription_status"]),
            billing_email=tenant_data.get("billing_email"),
            created_at=datetime.fromisoformat(tenant_data["created_at"]),
            usage_limits=usage_limits,
            current_usage=current_usage,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get tenant details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tenant information",
        )


@router.put("/me", response_model=UpdateTenantResponse)
async def update_tenant(
    request: UpdateTenantRequest,
    current_user: JWTPayload = Depends(require_admin),
    db: SupabaseClient = Depends(get_database),
):
    """
    Update tenant information (admin only)
    """
    try:
        update_data = {}
        if request.name:
            update_data["name"] = request.name
        if request.billing_email:
            update_data["billing_email"] = request.billing_email

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided"
            )

        update_data["updated_at"] = datetime.utcnow().isoformat()

        result = (
            db.client.table("tenants")
            .update(update_data)
            .eq("id", current_user.tenant_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

        updated_tenant = result.data[0]

        return UpdateTenantResponse(
            id=updated_tenant["id"],
            name=updated_tenant["name"],
            billing_email=updated_tenant.get("billing_email"),
            updated_at=datetime.fromisoformat(updated_tenant["updated_at"]),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update tenant"
        )


@router.get("/me/subscription", response_model=GetSubscriptionResponse)
async def get_subscription_details(
    current_user: JWTPayload = Depends(get_current_user), db: SupabaseClient = Depends(get_database)
):
    """
    Get current subscription details
    """
    try:
        subscription_response = (
            db.client.table("subscriptions")
            .select("*")
            .eq("tenant_id", current_user.tenant_id)
            .single()
            .execute()
        )

        if not subscription_response.data:
            # Create default subscription record
            default_subscription = {
                "tenant_id": current_user.tenant_id,
                "tier": SubscriptionTier.BASIC.value,
                "status": SubscriptionStatus.ACTIVE.value,
                "current_period_start": datetime.utcnow().isoformat(),
                "current_period_end": (datetime.utcnow().replace(day=1) + timedelta(days=32))
                .replace(day=1)
                .isoformat(),
                "created_at": datetime.utcnow().isoformat(),
            }

            result = db.client.table("subscriptions").insert(default_subscription).execute()
            subscription_data = result.data[0]
        else:
            subscription_data = subscription_response.data

        return GetSubscriptionResponse(
            tier=SubscriptionTier(subscription_data["tier"]),
            status=SubscriptionStatus(subscription_data["status"]),
            current_period_start=datetime.fromisoformat(subscription_data["current_period_start"]),
            current_period_end=datetime.fromisoformat(subscription_data["current_period_end"]),
            stripe_customer_id=subscription_data.get("stripe_customer_id"),
            stripe_subscription_id=subscription_data.get("stripe_subscription_id"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription information",
        )


@router.post("/me/subscription/change", response_model=ChangeSubscriptionResponse)
async def change_subscription(
    request: ChangeSubscriptionRequest,
    current_user: JWTPayload = Depends(require_admin),
    db: SupabaseClient = Depends(get_database),
):
    """
    Change subscription tier (admin only)
    Note: This would integrate with Stripe in production
    """
    try:
        # For demo purposes, we'll just update the database
        # In production, this would create/update Stripe subscription

        change_date = datetime.utcnow()
        update_data = {"tier": request.tier.value, "updated_at": change_date.isoformat()}

        # Update tenant subscription tier
        db.client.table("tenants").update(
            {"subscription_tier": request.tier.value, "updated_at": change_date.isoformat()}
        ).eq("id", current_user.tenant_id).execute()

        # Update subscription record
        db.client.table("subscriptions").update(update_data).eq(
            "tenant_id", current_user.tenant_id
        ).execute()

        return ChangeSubscriptionResponse(
            tier=request.tier, status=SubscriptionStatus.ACTIVE, change_effective_date=change_date
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to change subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change subscription",
        )


@router.get("/me/billing/invoices", response_model=GetInvoicesResponse)
async def get_billing_invoices(
    current_user: JWTPayload = Depends(require_admin), db: SupabaseClient = Depends(get_database)
):
    """
    Get billing history (admin only)
    Note: This would integrate with Stripe in production
    """
    try:
        # For demo purposes, return empty list
        # In production, this would fetch from Stripe API

        return GetInvoicesResponse(invoices=[])

    except Exception as e:
        logger.exception(f"Failed to get invoices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve billing information",
        )
