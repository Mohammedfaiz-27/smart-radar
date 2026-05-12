"""
Response Log data model - Supabase/PostgreSQL
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ResponseLogBase(BaseModel):
    original_post_id: str
    source_platform: str
    narrative_used_id: str = ""
    generated_response_text: str
    responded_by_user: str = "user"


class ResponseLogCreate(ResponseLogBase):
    pass


class ResponseLogInDB(ResponseLogBase):
    id: str
    responded_at: datetime = Field(default_factory=datetime.utcnow)


class ResponseLogResponse(ResponseLogBase):
    id: str
    responded_at: datetime
