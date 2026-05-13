from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from enum import Enum

from .base import BaseResponse, UsageLimits, CurrentUsage
from .auth import SubscriptionTier


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELED = "canceled"
    PAST_DUE = "past_due"


# Request Models
class UpdateTenantRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    billing_email: Optional[EmailStr] = None


class ChangeSubscriptionRequest(BaseModel):
    tier: SubscriptionTier


# Response Models
class TenantDetails(BaseModel):
    id: UUID
    name: str
    subscription_tier: SubscriptionTier
    subscription_status: SubscriptionStatus
    billing_email: Optional[EmailStr]
    created_at: datetime
    usage_limits: UsageLimits
    current_usage: CurrentUsage


class GetTenantResponse(BaseResponse):
    id: UUID
    name: str
    subscription_tier: SubscriptionTier
    subscription_status: SubscriptionStatus
    billing_email: Optional[EmailStr]
    created_at: datetime
    usage_limits: Optional[UsageLimits] = None
    current_usage: Optional[CurrentUsage] = None


class UpdateTenantResponse(BaseResponse):
    id: UUID
    name: str
    billing_email: Optional[EmailStr]
    updated_at: datetime


class SubscriptionDetails(BaseModel):
    tier: SubscriptionTier
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]


class GetSubscriptionResponse(BaseResponse):
    tier: SubscriptionTier
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]


class ChangeSubscriptionResponse(BaseResponse):
    tier: SubscriptionTier
    status: SubscriptionStatus
    change_effective_date: datetime


class Invoice(BaseModel):
    id: str
    amount: int  # cents
    currency: str
    status: str
    created: datetime
    invoice_pdf: Optional[str]


class GetInvoicesResponse(BaseResponse):
    invoices: List[Invoice]