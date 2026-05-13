from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from datetime import datetime
from uuid import uuid4
import logging
import hmac
import hashlib
import json
import httpx
from typing import Dict, Any, List

from core.middleware import get_current_user, require_admin, get_tenant_context, TenantContext
from models.auth import JWTPayload
from models.webhook import (
    RegisterWebhookRequest,
    RegisterWebhookResponse,
    Webhook,
    WebhookEvent,
    WebhookEventPayload,
    PostPublishedEventData,
    PlatformPublishInfo
)
from models.content import Platform

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks & events"])


async def send_webhook(
    webhook_url: str,
    secret: str,
    event_data: WebhookEventPayload,
    webhook_id: str = None
) -> bool:
    """Send webhook payload to configured URL with signature"""
    try:
        payload = event_data.model_dump_json()
        
        # Generate signature
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': f'sha256={signature}',
            'X-Webhook-Event': event_data.event.value,
            'X-Webhook-Timestamp': str(int(event_data.timestamp.timestamp())),
            'User-Agent': 'OmniPush-Webhooks/1.0'
        }
        
        if webhook_id:
            headers['X-Webhook-ID'] = webhook_id
        
        # Send webhook with timeout
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook_url,
                content=payload,
                headers=headers
            )
            
            # Consider 2xx status codes as successful
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Webhook sent successfully to {webhook_url}: {response.status_code}")
                return True
            else:
                logger.exception(f"Webhook failed for {webhook_url}: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.exception(f"Failed to send webhook to {webhook_url}: {e}")
        return False


async def get_tenant_webhooks(tenant_id: str, event: WebhookEvent, ctx: TenantContext) -> List[Webhook]:
    """Get all active webhooks for a tenant that subscribe to a specific event"""
    try:
        webhooks_response = ctx.table('webhooks').select('*').eq(
            'tenant_id', ctx.tenant_id
        ).eq('is_active', True).contains('events', [event.value]).execute()
        
        webhooks = []
        for webhook_data in webhooks_response.data or []:
            webhooks.append(Webhook(
                id=webhook_data['id'],
                url=webhook_data['url'],
                events=[WebhookEvent(e) for e in webhook_data['events']],
                created_at=datetime.fromisoformat(webhook_data['created_at'])
            ))
        
        return webhooks
        
    except Exception as e:
        logger.exception(f"Failed to get tenant webhooks: {e}")
        return []


async def trigger_webhooks(
    event: WebhookEvent,
    event_data: Dict[str, Any],
    tenant_id: str,
    ctx: TenantContext,
    background_tasks: BackgroundTasks
):
    """Trigger webhooks for a specific event"""
    try:
        # Get webhooks for this event
        webhooks = await get_tenant_webhooks(tenant_id, event, ctx)
        
        if not webhooks:
            return
        
        # Create event payload
        webhook_payload = WebhookEventPayload(
            event=event,
            data=event_data,
            timestamp=datetime.utcnow()
        )
        
        # Send webhooks in background
        for webhook in webhooks:
            # Get webhook secret from database
            webhook_secret_response = ctx.table('webhooks').select('secret').eq(
                'tenant_id', ctx.tenant_id
            ).eq('id', webhook.id).maybe_single().execute()
            
            if webhook_secret_response.data:
                secret = webhook_secret_response.data['secret']
                background_tasks.add_task(
                    send_webhook,
                    webhook.url,
                    secret,
                    webhook_payload,
                    str(webhook.id)
                )
        
    except Exception as e:
        logger.exception(f"Failed to trigger webhooks for event {event.value}: {e}")


@router.get("", response_model=List[Webhook])
async def list_webhooks(
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """List all webhooks for the tenant"""
    try:
        webhooks_response = ctx.table('webhooks').select(
            'id, url, events, is_active, created_at'
        ).eq('tenant_id', ctx.tenant_id).order('created_at', desc=True).execute()
        
        webhooks = []
        for webhook_data in webhooks_response.data or []:
            webhooks.append(Webhook(
                id=webhook_data['id'],
                url=webhook_data['url'],
                events=[WebhookEvent(e) for e in webhook_data['events']],
                created_at=datetime.fromisoformat(webhook_data['created_at'])
            ))
        
        return webhooks
        
    except Exception as e:
        logger.exception(f"Failed to list webhooks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve webhooks"
        )


@router.post("", response_model=RegisterWebhookResponse, status_code=status.HTTP_201_CREATED)
async def register_webhook(
    request: RegisterWebhookRequest,
    current_user: JWTPayload = Depends(require_admin),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Register a new webhook (admin only)"""
    try:
        # Validate events
        for event in request.events:
            if event not in WebhookEvent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid webhook event: {event}"
                )
        
        # Check if webhook URL already exists
        existing_webhook = ctx.table('webhooks').select('id').eq(
            'tenant_id', ctx.tenant_id
        ).eq('url', str(request.url)).execute()
        
        if existing_webhook.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Webhook URL already registered"
            )
        
        # Create webhook
        webhook_id = str(uuid4())
        webhook_data = {
            'id': webhook_id,
            'tenant_id': current_user.tenant_id,
            'url': str(request.url),
            'events': [e.value for e in request.events],
            'secret': request.secret,
            'is_active': True,
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = ctx.db.client.table('webhooks').insert(webhook_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register webhook"
            )
        
        return RegisterWebhookResponse(
            id=webhook_id,
            url=request.url,
            events=request.events,
            created_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to register webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register webhook"
        )


@router.put("/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    request: RegisterWebhookRequest,
    current_user: JWTPayload = Depends(require_admin),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Update an existing webhook (admin only)"""
    try:
        # Check if webhook exists
        webhook_response = ctx.table('webhooks').select('id').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', webhook_id).maybe_single().execute()
        
        if not webhook_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Update webhook
        update_data = {
            'url': str(request.url),
            'events': [e.value for e in request.events],
            'secret': request.secret,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = ctx.table('webhooks').update(update_data).eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', webhook_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update webhook"
            )
        
        return {"message": "Webhook updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update webhook"
        )


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    background_tasks: BackgroundTasks,
    current_user: JWTPayload = Depends(require_admin),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Send a test event to a webhook (admin only)"""
    try:
        # Get webhook details
        webhook_response = ctx.table('webhooks').select('*').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', webhook_id).maybe_single().execute()
        
        if not webhook_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        webhook_data = webhook_response.data
        
        # Create test event
        test_event = WebhookEventPayload(
            event=WebhookEvent.POST_PUBLISHED,  # Use a common event for testing
            data={
                "test": True,
                "message": "This is a test webhook event",
                "webhook_id": webhook_id,
                "tenant_id": current_user.tenant_id
            },
            timestamp=datetime.utcnow()
        )
        
        # Send test webhook
        background_tasks.add_task(
            send_webhook,
            webhook_data['url'],
            webhook_data['secret'],
            test_event,
            webhook_id
        )
        
        return {"message": "Test webhook sent"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to test webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test webhook"
        )


@router.post("/{webhook_id}/toggle")
async def toggle_webhook(
    webhook_id: str,
    current_user: JWTPayload = Depends(require_admin),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Toggle webhook active/inactive status (admin only)"""
    try:
        # Get current status
        webhook_response = ctx.table('webhooks').select('is_active').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', webhook_id).maybe_single().execute()
        
        if not webhook_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        current_status = webhook_response.data['is_active']
        new_status = not current_status
        
        # Update status
        result = ctx.table('webhooks').update({
            'is_active': new_status,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('tenant_id', ctx.tenant_id).eq('id', webhook_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to toggle webhook status"
            )
        
        status_text = "activated" if new_status else "deactivated"
        return {"message": f"Webhook {status_text} successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to toggle webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle webhook status"
        )


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user: JWTPayload = Depends(require_admin),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Delete a webhook (admin only)"""
    try:
        # Check if webhook exists
        webhook_response = ctx.table('webhooks').select('id').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', webhook_id).maybe_single().execute()
        
        if not webhook_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Delete webhook
        ctx.table('webhooks').delete().eq('tenant_id', ctx.tenant_id).eq('id', webhook_id).execute()
        
        return {"message": "Webhook deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete webhook"
        )


@router.get("/{webhook_id}/deliveries")
async def get_webhook_deliveries(
    webhook_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Get webhook delivery history (mock implementation)"""
    try:
        # Check if webhook exists
        webhook_response = ctx.table('webhooks').select('id').eq(
            'tenant_id', ctx.tenant_id
        ).eq('id', webhook_id).maybe_single().execute()
        
        if not webhook_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Mock delivery history
        # In production, you would store webhook delivery logs
        deliveries = [
            {
                "id": str(uuid4()),
                "event": "post.published",
                "status": "success",
                "response_code": 200,
                "delivered_at": datetime.utcnow().isoformat(),
                "attempts": 1
            },
            {
                "id": str(uuid4()),
                "event": "post.failed", 
                "status": "failed",
                "response_code": 500,
                "delivered_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "attempts": 3,
                "error": "Internal Server Error"
            }
        ]
        
        return {
            "webhook_id": webhook_id,
            "deliveries": deliveries,
            "total_deliveries": len(deliveries),
            "success_rate": 0.5
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get webhook deliveries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve webhook deliveries"
        )


# Event trigger functions (used by other parts of the application)
async def trigger_post_published_event(
    post_id: str,
    tenant_id: str,
    platforms: List[Dict[str, Any]],
    ctx: TenantContext,
    background_tasks: BackgroundTasks
):
    """Trigger post.published webhook event"""
    platform_info = [
        PlatformPublishInfo(
            platform=Platform(p['platform']),
            platform_post_id=p['platform_post_id'],
            published_at=datetime.fromisoformat(p['published_at'])
        ) for p in platforms
    ]
    
    event_data = PostPublishedEventData(
        post_id=post_id,
        tenant_id=tenant_id,
        platforms=platform_info
    ).model_dump()
    
    await trigger_webhooks(
        WebhookEvent.POST_PUBLISHED,
        event_data,
        tenant_id,
        ctx,
        background_tasks
    )


async def trigger_post_failed_event(
    post_id: str,
    tenant_id: str,
    error_message: str,
    ctx: TenantContext,
    background_tasks: BackgroundTasks
):
    """Trigger post.failed webhook event"""
    event_data = {
        "post_id": post_id,
        "tenant_id": tenant_id,
        "error": error_message,
        "failed_at": datetime.utcnow().isoformat()
    }
    
    await trigger_webhooks(
        WebhookEvent.POST_FAILED,
        event_data,
        tenant_id,
        ctx,
        background_tasks
    )


async def trigger_approval_required_event(
    post_id: str,
    tenant_id: str,
    approvers: List[str],
    ctx: TenantContext,
    background_tasks: BackgroundTasks
):
    """Trigger approval.required webhook event"""
    event_data = {
        "post_id": post_id,
        "tenant_id": tenant_id,
        "approvers": approvers,
        "submitted_at": datetime.utcnow().isoformat()
    }
    
    await trigger_webhooks(
        WebhookEvent.APPROVAL_REQUIRED,
        event_data,
        tenant_id,
        ctx,
        background_tasks
    )