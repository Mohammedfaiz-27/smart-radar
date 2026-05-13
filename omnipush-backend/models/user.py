from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from enum import Enum

from .base import BaseResponse, PaginatedResponse
from .auth import UserRole


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"


# Request Models
class InviteUserRequest(BaseModel):
    email: EmailStr
    role: UserRole
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)


class UpdateUserRoleRequest(BaseModel):
    role: UserRole


# Response Models
class User(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    status: UserStatus
    last_login: Optional[datetime]
    created_at: datetime


class ListUsersResponse(PaginatedResponse):
    users: List[User]


class Invitation(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    status: InvitationStatus
    expires_at: datetime


class InviteUserResponse(BaseResponse):
    invitation: Invitation


class UpdateUserRoleResponse(BaseResponse):
    id: UUID
    role: UserRole
    updated_at: datetime


class DeactivateUserResponse(BaseResponse):
    message: str = "User deactivated successfully"