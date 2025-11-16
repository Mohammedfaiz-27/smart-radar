"""
Response Log data model for MongoDB
"""
from pydantic import BaseModel, Field
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, _source_type, _handler):
        return {"type": "string"}

class ResponseLogBase(BaseModel):
    """Base response log model"""
    original_post_id: PyObjectId
    source_platform: str
    narrative_used_id: PyObjectId
    generated_response_text: str
    responded_by_user: str

class ResponseLogCreate(ResponseLogBase):
    """Response log creation model"""
    pass

class ResponseLogInDB(ResponseLogBase):
    """Response log model stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    responded_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class ResponseLogResponse(ResponseLogBase):
    """Response log response model"""
    id: str
    responded_at: datetime