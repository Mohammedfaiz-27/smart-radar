"""
Research API - AI-powered topic analysis
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services import research_service

router = APIRouter()


class ResearchRequest(BaseModel):
    query: str
    understanding: Optional[str] = None


class GeneratePostsRequest(BaseModel):
    query: str
    about: Optional[str] = None
    current_affairs: Optional[str] = None


@router.post("/about")
async def research_about(req: ResearchRequest):
    try:
        about = await research_service.get_understanding(req.query)
        return {"about": about}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history")
async def research_history(req: ResearchRequest):
    try:
        history = await research_service.get_history(req.query, req.understanding)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/current-affairs")
async def research_current_affairs(req: ResearchRequest):
    try:
        current_affairs = await research_service.get_current_affairs(req.query, req.understanding)
        return {"current_affairs": current_affairs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/competitors")
async def research_competitors(req: ResearchRequest):
    try:
        competitors = await research_service.get_competitors(req.query, req.understanding)
        return {"competitors": competitors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/challenges")
async def research_challenges(req: ResearchRequest):
    try:
        challenges = await research_service.get_challenges(req.query, req.understanding)
        return {"challenges": challenges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plus-points")
async def research_plus_points(req: ResearchRequest):
    try:
        plus_points = await research_service.get_plus_points(req.query, req.understanding)
        return {"plus_points": plus_points}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/negative-points")
async def research_negative_points(req: ResearchRequest):
    try:
        negative_points = await research_service.get_negative_points(req.query, req.understanding)
        return {"negative_points": negative_points}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-posts")
async def generate_social_posts(req: GeneratePostsRequest):
    try:
        posts = await research_service.generate_social_posts(req.query, req.about, req.current_affairs)
        return posts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
