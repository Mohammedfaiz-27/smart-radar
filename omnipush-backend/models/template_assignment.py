from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum

from .base import BaseResponse
from .content import Platform


class NewscardTemplateModel(BaseModel):
    """Model for newscard template information"""
    id: str
    template_name: str
    template_display_name: str
    template_path: str
    s3_url: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_key: Optional[str] = None
    supports_images: bool
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SocialChannelTemplateAssignmentModel(BaseModel):
    """Model for social channel template assignment"""
    id: str
    tenant_id: str
    social_account_id: str
    platform: Platform
    template_with_image: Optional[str] = None
    template_without_image: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SocialAccountSummary(BaseModel):
    """Summary of a social account with template assignment status"""
    social_account_id: str
    platform: Platform
    account_name: str
    has_assignment: bool
    template_with_image: Optional[str] = None
    template_without_image: Optional[str] = None


# Request Models
class AssignTemplatesRequest(BaseModel):
    """Request model for assigning templates to a social channel"""
    social_account_id: str
    template_with_image: Optional[str] = Field(None, description="Template to use when content has images")
    template_without_image: Optional[str] = Field(None, description="Template to use when content has no images")

    class Config:
        json_schema_extra = {
            "example": {
                "social_account_id": "123e4567-e89b-12d3-a456-426614174000",
                "template_with_image": "template_1_modern_card_with_image",
                "template_without_image": "template_1_modern_gradient"
            }
        }


class BulkAssignDefaultTemplatesRequest(BaseModel):
    """Request model for bulk assigning default templates"""
    force_override: bool = Field(False, description="Whether to override existing assignments")


# Response Models
class ListTemplatesResponse(BaseResponse):
    """Response model for listing available templates"""
    templates: List[NewscardTemplateModel]
    total_count: int
    templates_with_images: int
    templates_without_images: int


class ListTemplateAssignmentsResponse(BaseResponse):
    """Response model for listing template assignments"""
    assignments: List[SocialChannelTemplateAssignmentModel]
    total_count: int


class AssignTemplatesResponse(BaseResponse):
    """Response model for template assignment"""
    assignment: SocialChannelTemplateAssignmentModel
    message: str = "Templates assigned successfully"


class TemplateAssignmentSummaryResponse(BaseResponse):
    """Response model for template assignment summary"""
    tenant_id: str
    total_social_accounts: int
    accounts_with_assignments: int
    accounts_without_assignments: int
    accounts: List[SocialAccountSummary]


class BulkAssignmentResponse(BaseResponse):
    """Response model for bulk template assignment"""
    total_accounts: int
    assigned_count: int
    failed_count: int
    default_template_with_image: str
    default_template_without_image: str
    message: str


class TemplateAssignmentStatusResponse(BaseResponse):
    """Response model for checking template assignment status for a specific channel"""
    social_account_id: str
    platform: Platform
    account_name: str
    has_assignment: bool
    assigned_template_with_image: Optional[str] = None
    assigned_template_without_image: Optional[str] = None
    will_use_for_images: Optional[str] = None  # Template that will actually be used for content with images
    will_use_for_text: Optional[str] = None    # Template that will actually be used for text-only content


class RemoveAssignmentResponse(BaseResponse):
    """Response model for removing template assignment"""
    social_account_id: str
    message: str = "Template assignment removed successfully"