"""
Response generation and logging API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.models.response_log import ResponseLogResponse
from app.services.response_service import ResponseService

router = APIRouter()
response_service = ResponseService()

class GenerateResponseRequest(BaseModel):
    original_post_id: str
    tone: str = "Sarcastic"  # Sarcastic, Assertive, Professional
    language: str = "Tamil"  # Tamil, English
    user_id: str = "default"

class LogResponseRequest(BaseModel):
    original_post_id: str
    generated_text: str
    tone: str = "Sarcastic"
    language: str = "Tamil"
    user_id: str = "default"

@router.post("/generate")
async def generate_response(request: GenerateResponseRequest):
    """Generate AI-powered autonomous response with fact-finding"""
    try:
        result = await response_service.generate_response(
            original_post_id=request.original_post_id,
            tone=request.tone,
            language=request.language,
            user_id=request.user_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate response")

@router.post("/log", response_model=ResponseLogResponse, status_code=201)
async def log_response(request: LogResponseRequest):
    """Log a generated response"""
    try:
        return await response_service.log_response(
            original_post_id=request.original_post_id,
            generated_text=request.generated_text,
            tone=request.tone,
            language=request.language,
            user_id=request.user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to log response")