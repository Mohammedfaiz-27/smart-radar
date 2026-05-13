from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum

from .base import BaseResponse


class WorkflowStepType(str, Enum):
    APPROVAL = "approval"
    REVIEW = "review"
    NOTIFICATION = "notification"


# Request Models
class WorkflowStep(BaseModel):
    order: int = Field(ge=1)
    type: WorkflowStepType
    approvers: List[UUID]
    required: bool = True


class CreateWorkflowRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    steps: List[WorkflowStep]


# Response Models
class Workflow(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    steps: List[WorkflowStep]
    is_default: bool
    created_by: UUID
    created_at: datetime


class ListWorkflowsResponse(BaseResponse):
    workflows: List[Workflow]


class CreateWorkflowResponse(BaseResponse):
    id: UUID
    name: str
    created_at: datetime