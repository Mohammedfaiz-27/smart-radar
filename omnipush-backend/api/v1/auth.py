from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials
from uuid import uuid4
import logging

from core.database import get_database, SupabaseClient
from core.security import (
    hash_password, 
    verify_password, 
    create_access_token, 
    create_refresh_token,
    verify_refresh_token
)
from core.middleware import security
from models.auth import (
    SignUpRequest,
    SignInRequest, 
    RefreshTokenRequest,
    SignUpResponse,
    SignInResponse,
    RefreshTokenResponse,
    SignOutResponse,
    UserRole,
    SubscriptionTier
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/signup", response_model=SignUpResponse, status_code=status.HTTP_201_CREATED)
async def sign_up(
    request: SignUpRequest,
    db: SupabaseClient = Depends(get_database)
):
    """
    Sign up a new user and create their tenant workspace
    """
    try:
        # Check if user already exists
        existing_user = db.service_client.table('users').select('id').eq(
            'email', request.email
        ).execute()
        
        if existing_user.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        
        # Create tenant first
        tenant_id = str(uuid4())
        # Generate slug from tenant name (URL-friendly version)
        base_slug = request.tenant_name.lower().replace(' ', '-').replace('_', '-')
        # Remove any non-alphanumeric characters except hyphens
        import re
        base_slug = re.sub(r'[^a-z0-9-]', '', base_slug)
        # Ensure slug is not empty
        if not base_slug:
            base_slug = f"tenant-{tenant_id[:8]}"
        
        # Check if slug already exists and make it unique
        slug = base_slug
        counter = 1
        while True:
            existing_tenant = db.service_client.table('tenants').select('id').eq('slug', slug).execute()
            if not existing_tenant.data:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        tenant_data = {
            'id': tenant_id,
            'name': request.tenant_name,
            'slug': slug,
            'subscription_tier': SubscriptionTier.BASIC.value,
            'subscription_status': 'active',
            'created_at': datetime.utcnow().isoformat()
        }
        
        tenant_result = db.service_client.table('tenants').insert(tenant_data).execute()
        
        if not tenant_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create tenant"
            )
        
        # Create user
        user_id = str(uuid4())
        hashed_password = hash_password(request.password)
        
        # Try with minimal required fields first
        user_data = {
            'id': user_id,
            'email': request.email,
            'first_name': request.first_name,
            'last_name': request.last_name or "",
            'password_hash': hashed_password,
            'tenant_id': tenant_id,
            'role': UserRole.ADMIN.value,  # First user is admin
            'status': 'active',
            'created_at': datetime.utcnow().isoformat()
        }
        
        user_result = db.service_client.table('users').insert(user_data).execute()
        
        if not user_result.data:
            # Rollback tenant creation
            db.service_client.table('tenants').delete().eq('id', tenant_id).execute()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        # Generate tokens
        access_token = create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            role=UserRole.ADMIN
        )
        refresh_token = create_refresh_token(user_id=user_id)
        
        return SignUpResponse(
            user={
                "id": user_id,
                "email": request.email,
                "first_name": request.first_name,
                "last_name": request.last_name or ""
            },
            tenant={
                "id": tenant_id,
                "name": request.tenant_name,
                "subscription_tier": SubscriptionTier.BASIC
            },
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Signup failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during signup: {str(e)}"
        )


@router.post("/signin", response_model=SignInResponse)
async def sign_in(
    request: SignInRequest,
    db: SupabaseClient = Depends(get_database)
):
    """
    Sign in an existing user
    """
    try:
        # Get user by email
        user_response = db.service_client.table('users').select(
            'id, email, password_hash, first_name, last_name, tenant_id, role, status'
        ).eq('email', request.email).maybe_single().execute()
        
        if not user_response.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user = user_response.data
        
        # Verify password
        if not verify_password(request.password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check user status
        if user['status'] != 'active':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Update last login
        db.service_client.table('users').update({
            'last_login': datetime.utcnow().isoformat()
        }).eq('id', user['id']).execute()
        
        # Generate tokens
        user_role = UserRole(user['role'])
        access_token = create_access_token(
            user_id=user['id'],
            tenant_id=user['tenant_id'],
            role=user_role
        )
        refresh_token = create_refresh_token(user_id=user['id'])
        
        return SignInResponse(
            user={
                "id": user['id'],
                "email": user['email'],
                "tenant_id": user['tenant_id'],
                "role": user_role,
                "first_name": user['first_name'],
                "last_name": user['last_name']
            },
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Signin failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during signin"
        )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: SupabaseClient = Depends(get_database)
):
    """
    Refresh an access token using a refresh token
    """
    try:
        # Verify refresh token and get user_id
        user_id = verify_refresh_token(request.refresh_token)
        
        # Get user details
        user_response = db.service_client.table('users').select(
            'id, tenant_id, role, status'
        ).eq('id', user_id).maybe_single().execute()
        
        if not user_response.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        user = user_response.data
        
        if user['status'] != 'active':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive"
            )
        
        # Generate new access token
        user_role = UserRole(user['role'])
        access_token = create_access_token(
            user_id=user['id'],
            tenant_id=user['tenant_id'],
            role=user_role
        )
        
        return RefreshTokenResponse(
            access_token=access_token,
            expires_in=3600
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during token refresh"
        )


@router.post("/signout", response_model=SignOutResponse)
async def sign_out(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Sign out user (invalidate token)
    Note: In a production system, you would add the token to a blacklist
    """
    # For now, just return success - token will expire naturally
    # In production, you would store token in Redis blacklist with TTL
    return SignOutResponse()