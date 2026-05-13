from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum

from .base import BaseResponse
from .content import Platform


class AccountStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    EXPIRED = "expired"


class ConnectionMethod(str, Enum):
    OAUTH = "oauth"
    MANUAL = "manual"


# Request Models
class ConnectAccountRequest(BaseModel):
    platform: Platform
    connection_method: ConnectionMethod
    # OAuth fields
    auth_code: Optional[str] = None
    # Manual connection fields
    account_name: Optional[str] = None
    access_token: Optional[str] = None
    # Platform-specific fields
    page_id: Optional[str] = None  # Facebook page ID
    periskope_id: Optional[str] = None  # WhatsApp Periskope ID
    # Content customization fields
    content_tone: Optional[str] = "professional"
    custom_instructions: Optional[str] = None
    auto_image_search: Optional[bool] = False


class UpdateAccountRequest(BaseModel):
    content_tone: Optional[str] = None
    custom_instructions: Optional[str] = None
    auto_image_search: Optional[bool] = None
    access_token: Optional[str] = None
    page_id: Optional[str] = None
    periskope_id: Optional[str] = None


# Response Models
class SocialAccount(BaseModel):
    id: UUID
    platform: Platform
    account_name: str
    account_id: str  # platform-specific account ID
    account_link: Optional[str] = None  # Link to the social media account page
    status: AccountStatus
    permissions: List[str] = []
    connected_at: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    # Platform-specific fields
    page_id: Optional[str] = None  # Facebook page ID
    periskope_id: Optional[str] = None  # WhatsApp Periskope ID
    # Content customization fields
    content_tone: Optional[str] = "professional"
    custom_instructions: Optional[str] = None
    # Token field (obscured)
    access_token_obscured: Optional[str] = None

class PaginationMetadata(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int

class PaginationMetadata(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class ListAccountsResponse(BaseResponse):
    accounts: List[SocialAccount]
    pagination: Optional[PaginationMetadata] = None


class ConnectAccountResponse(BaseResponse):
    id: UUID
    platform: Platform
    account_name: str
    status: AccountStatus
    connected_at: datetime


class DisconnectAccountResponse(BaseResponse):
    message: str = "Account disconnected successfully"