"""
Smart Post API — publishing, drafts, AI content, analytics, media, news cards.
Mounted at /v1 to match the frontend smartpost.js service client.
"""
import os
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel

from app.services.smart_post_service import SmartPostService

logger = logging.getLogger(__name__)
router = APIRouter()
svc = SmartPostService()

# ── Pydantic models ────────────────────────────────────────────────────────────

class SigninRequest(BaseModel):
    email: str
    password: str

class Channel(BaseModel):
    platform: str
    account_id: Optional[str] = None

class PublishRequest(BaseModel):
    title: Optional[str] = ""
    content: Dict[str, Any]
    channels: List[Channel]
    scheduled_at: Optional[str] = None

class ContentSuggestionRequest(BaseModel):
    context: Dict[str, Any]
    tone: str = "formal"
    mode: str = "counter-narrative"
    platforms: List[str] = ["twitter", "facebook"]

class NewsCardRequest(BaseModel):
    post_id: Optional[str] = None
    source_content: Optional[str] = ""
    source_platform: Optional[str] = ""
    headline: Optional[str] = ""
    message: Optional[str] = ""
    attribution: Optional[str] = "Smart Radar"
    style: Optional[str] = "news"
    theme: Optional[str] = "blue"

class RejectRequest(BaseModel):
    reason: Optional[str] = ""

class ScheduleRequest(BaseModel):
    scheduled_at: str

class DraftCreateRequest(BaseModel):
    title: Optional[str] = ""
    content: Dict[str, Any]
    channels: List[Channel]


# ── Auth ───────────────────────────────────────────────────────────────────────

@router.post("/auth/signin")
async def signin(req: SigninRequest):
    result = svc.verify_credentials(req.email, req.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return result


# ── Social Accounts ────────────────────────────────────────────────────────────

@router.get("/social-accounts")
async def get_social_accounts():
    return svc.get_social_accounts()


# ── Publishing ─────────────────────────────────────────────────────────────────

@router.post("/posts/publish-now")
async def publish_now(req: PublishRequest):
    try:
        result = await svc.publish_now(
            title=req.title or "",
            content=req.content,
            channels=[ch.dict() for ch in req.channels],
            scheduled_at=req.scheduled_at,
        )
        return result
    except Exception as e:
        logger.error(f"Publish failed: {e}")
        raise HTTPException(status_code=500, detail="Publish failed")


@router.post("/posts/{post_id}/schedule")
async def schedule_post(post_id: str, req: ScheduleRequest):
    try:
        result = await svc.publish_now(
            title=post_id,
            content={"text": ""},
            channels=[],
            scheduled_at=req.scheduled_at,
        )
        return {"post_id": post_id, "scheduled_at": req.scheduled_at, "status": "scheduled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── News Card ──────────────────────────────────────────────────────────────────

@router.post("/posts/news-card")
async def generate_news_card(req: NewsCardRequest):
    try:
        result = await svc.generate_news_card(req.dict())
        return result
    except Exception as e:
        logger.error(f"News card generation failed: {e}")
        raise HTTPException(status_code=500, detail="News card generation failed")


# ── Calendar ───────────────────────────────────────────────────────────────────

@router.get("/calendar")
async def get_calendar(limit: int = Query(50, ge=1, le=200)):
    try:
        return await svc.get_calendar(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── AI Content Suggestions ─────────────────────────────────────────────────────

@router.post("/ai/content-suggestions")
async def get_content_suggestions(req: ContentSuggestionRequest):
    try:
        result = await svc.get_content_suggestions(
            context=req.context,
            tone=req.tone,
            mode=req.mode,
            platforms=req.platforms,
        )
        return result
    except Exception as e:
        logger.error(f"Content suggestions failed: {e}")
        raise HTTPException(status_code=500, detail="Content generation failed")


# ── Media ──────────────────────────────────────────────────────────────────────

@router.get("/media")
async def get_media():
    try:
        return await svc.get_media()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/media/upload")
async def upload_media(files: List[UploadFile] = File(...)):
    try:
        uploaded = []
        for f in files:
            content = await f.read()
            # In production wire to S3/Supabase Storage.
            # For now, save metadata only.
            item = await svc.save_media(
                filename=f.filename or "upload",
                url=f"/media/{f.filename}",
                file_type=f.content_type or "image/jpeg",
                file_size=len(content),
            )
            uploaded.append(item)
        return {"items": uploaded}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/media/search-images")
async def search_images(q: str = Query(..., min_length=1)):
    try:
        return await svc.search_images(q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Drafts / Approval ──────────────────────────────────────────────────────────

@router.get("/drafts/pending")
async def get_pending_drafts():
    try:
        return await svc.get_pending_drafts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drafts")
async def create_draft(req: DraftCreateRequest):
    try:
        return await svc.create_draft(
            title=req.title or "",
            content=req.content,
            channels=[ch.dict() for ch in req.channels],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drafts/{draft_id}/approve")
async def approve_draft(draft_id: str):
    try:
        ok = await svc.approve_draft(draft_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Draft not found")
        return {"draft_id": draft_id, "status": "approved"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drafts/{draft_id}/reject")
async def reject_draft(draft_id: str, req: RejectRequest):
    try:
        ok = await svc.reject_draft(draft_id, req.reason or "")
        if not ok:
            raise HTTPException(status_code=404, detail="Draft not found")
        return {"draft_id": draft_id, "status": "rejected"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drafts/{draft_id}/publish")
async def publish_draft(draft_id: str):
    try:
        return await svc.publish_draft(draft_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Analytics ──────────────────────────────────────────────────────────────────

@router.get("/analytics/dashboard")
async def analytics_dashboard():
    try:
        return await svc.get_analytics_dashboard()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/posts/{post_id}")
async def post_analytics(post_id: str):
    return {
        "post_id": post_id,
        "impressions": 0,
        "engagements": 0,
        "clicks": 0,
        "shares": 0,
    }


@router.get("/analytics/insights")
async def get_insights():
    try:
        return await svc.get_insights()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
