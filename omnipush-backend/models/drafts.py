"""
Pydantic models for post drafts (Human-in-the-Loop review workflow)
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class DraftStatus(str, Enum):
    """Draft status enumeration"""
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class PostDraft(BaseModel):
    """Post draft model"""
    id: UUID
    tenant_id: UUID
    user_id: UUID
    external_news_id: Optional[UUID] = None
    post_id: Optional[UUID] = None
    social_account_id: UUID

    # LLM-generated content (immutable)
    generated_content: str
    generated_headline: Optional[str] = None
    generated_district: Optional[str] = None
    generated_hashtags: List[str] = Field(default_factory=list)

    # User-editable content
    final_content: str
    final_headline: Optional[str] = None
    final_district: Optional[str] = None
    final_hashtags: List[str] = Field(default_factory=list)

    # Workflow status
    status: DraftStatus

    # Timestamps
    created_at: datetime
    approved_at: Optional[datetime] = None
    approved_by: Optional[UUID] = None
    rejected_at: Optional[datetime] = None
    rejected_by: Optional[UUID] = None
    rejection_reason: Optional[str] = None

    # Publishing results
    published_at: Optional[datetime] = None
    publish_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class DraftWithDetails(PostDraft):
    """Draft with joined social account and source info"""
    social_accounts: Optional[Dict[str, Any]] = None
    external_news_items: Optional[Dict[str, Any]] = None
    posts: Optional[Dict[str, Any]] = None
    users: Optional[Dict[str, Any]] = None


class ApproveDraftRequest(BaseModel):
    """Request to approve a draft with optional edits"""
    final_content: Optional[str] = Field(None, description="Edited content (if changed)")
    final_headline: Optional[str] = Field(None, description="Edited headline (if changed)")
    final_district: Optional[str] = Field(None, description="Edited district (if changed)")
    final_hashtags: Optional[List[str]] = Field(None, description="Edited hashtags (if changed)")


class RejectDraftRequest(BaseModel):
    """Request to reject a draft"""
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection")


class PublishDraftRequest(BaseModel):
    """Request to publish an approved draft"""
    newscard_url: Optional[str] = Field(None, description="Optional newscard image URL")


class DraftListResponse(BaseModel):
    """Response for draft list endpoint"""
    items: List[DraftWithDetails]
    pagination: Dict[str, Any]


class DraftDetailResponse(BaseModel):
    """Response for draft detail endpoint"""
    draft: DraftWithDetails


class DraftStatsResponse(BaseModel):
    """Response for draft stats endpoint"""
    all: int = 0
    PENDING_REVIEW: int = 0
    APPROVED: int = 0
    REJECTED: int = 0
    PUBLISHED: int = 0
    FAILED: int = 0


class DraftActionResponse(BaseModel):
    """Generic response for draft actions (approve/reject/publish)"""
    success: bool
    message: str
    draft: Optional[DraftWithDetails] = None
    publish_result: Optional[Dict[str, Any]] = None
