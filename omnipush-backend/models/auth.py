from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from enum import Enum

from .base import BaseResponse


class UserRole(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    CREATOR = "creator"
    ANALYST = "analyst"


class SubscriptionTier(str, Enum):
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# Request Models
class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    tenant_name: str = Field(min_length=1, max_length=100)
    first_name: str = Field(min_length=1, max_length=50)
    last_name: Optional[str] = Field(default="", max_length=50)


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Response Models
class UserInfo(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    tenant_id: Optional[UUID] = None
    role: Optional[UserRole] = None


class TenantInfo(BaseModel):
    id: UUID
    name: str
    subscription_tier: SubscriptionTier


class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class SignUpResponse(BaseResponse):
    user: UserInfo
    tenant: TenantInfo
    access_token: str
    refresh_token: str
    expires_in: int


class SignInResponse(BaseResponse):
    user: UserInfo
    access_token: str
    refresh_token: str
    expires_in: int


class RefreshTokenResponse(BaseResponse):
    access_token: str
    expires_in: int


class SignOutResponse(BaseResponse):
    message: str = "Successfully signed out"


# JWT Payload
class JWTPayload(BaseModel):
    sub: str  # user_id
    tenant_id: str
    role: UserRole
    exp: int
    iat: int