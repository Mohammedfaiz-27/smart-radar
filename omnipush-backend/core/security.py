from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from uuid import UUID
import logging

from .config import settings
from models.auth import JWTPayload, UserRole

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: Union[str, UUID],
    tenant_id: Union[str, UUID],
    role: UserRole,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token"""
    # Validate JWT secret key
    if not settings.jwt_secret_key:
        logger.exception("JWT_SECRET_KEY is not configured. Please set the JWT_SECRET_KEY environment variable.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT configuration error"
        )
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
    
    to_encode = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role.value,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    try:
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.jwt_secret_key, 
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt
    except Exception as e:
        logger.exception(f"Failed to create JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create authentication token"
        )


def create_refresh_token(user_id: Union[str, UUID]) -> str:
    """Create a JWT refresh token"""
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    
    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt
    except Exception as e:
        logger.exception(f"Failed to create refresh token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create refresh token"
        )


def verify_token(token: str) -> JWTPayload:
    """Verify and decode a JWT token"""
    # Validate JWT secret key
    if not settings.jwt_secret_key:
        logger.exception("JWT_SECRET_KEY is not configured. Please set the JWT_SECRET_KEY environment variable.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT configuration error"
        )
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Check if token has expired
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        
        # Validate required fields for access tokens
        if payload.get("type") != "refresh":
            user_id = payload.get("sub")
            tenant_id = payload.get("tenant_id")
            role = payload.get("role")
            
            if not user_id or not tenant_id or not role:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            return JWTPayload(**payload)
        else:
            # Refresh token - only needs user_id
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
            return JWTPayload(
                sub=user_id,
                tenant_id="",  # Not needed for refresh tokens
                role=UserRole.CREATOR,  # Default role
                exp=payload.get("exp", 0),
                iat=payload.get("iat", 0)
            )
            
    except JWTError as e:
        logger.exception(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def verify_refresh_token(token: str) -> str:
    """Verify a refresh token and return user_id"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Check if token has expired
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )
        
        # Check if it's actually a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token payload"
            )
        
        return user_id
        
    except JWTError as e:
        logger.exception(f"Refresh token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token"
        )