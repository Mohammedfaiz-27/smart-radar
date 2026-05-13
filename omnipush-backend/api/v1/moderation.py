"""
Moderation API endpoints for content filtering.
Provides endpoints for moderating content with configurable city/keyword focus and generic news.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import logging

from core.middleware import get_current_user
from services.moderation_service import ModerationService, ModerationResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/moderation", tags=["moderation"])


class ContentModerationRequest(BaseModel):
    """Request model for content moderation"""
    title: str
    content: str
    source: Optional[str] = "unknown"
    category: Optional[str] = "general"
    city_or_keyword: Optional[str] = "coimbatore"


class ContentModerationResponse(BaseModel):
    """Response model for content moderation"""
    is_approved: bool
    reason: str
    content_type: str
    confidence: float
    flagged_categories: Optional[List[str]] = None
    suggested_actions: Optional[List[str]] = None


class BatchModerationRequest(BaseModel):
    """Request model for batch moderation"""
    articles: List[ContentModerationRequest]


class BatchModerationResponse(BaseModel):
    """Response model for batch moderation"""
    results: List[ContentModerationResponse]
    statistics: dict


@router.post("/moderate", response_model=ContentModerationResponse)
async def moderate_content(
    request: ContentModerationRequest,
    current_user = Depends(get_current_user)
):
    """
    Moderate a single piece of content for relevance to a specified city/keyword and general news.

    The moderation system checks for:
    - Location/keyword-specific content (local news, events, developments)
    - High-quality generic news (technology, science, business, health)
    - Spam and harmful content filtering

    Parameters:
    - city_or_keyword: The city or keyword to filter content for (defaults to 'coimbatore')
    """
    try:
        moderation_service = ModerationService()
        
        result = await moderation_service.moderate_content(
            title=request.title,
            content=request.content,
            source=request.source,
            category=request.category,
            city_or_keyword=request.city_or_keyword
        )
        
        return ContentModerationResponse(
            is_approved=result.is_approved,
            reason=result.reason,
            content_type=result.content_type,
            confidence=result.confidence,
            flagged_categories=result.flagged_categories,
            suggested_actions=result.suggested_actions
        )
        
    except Exception as e:
        logger.exception(f"Moderation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Moderation failed: {str(e)}")


@router.post("/moderate/batch", response_model=BatchModerationResponse)
async def moderate_content_batch(
    request: BatchModerationRequest,
    current_user = Depends(get_current_user)
):
    """
    Moderate multiple pieces of content in batch.
    
    Useful for processing multiple articles at once and getting overall statistics.
    """
    try:
        moderation_service = ModerationService()
        
        # Convert to list of dicts for batch processing
        articles = [
            {
                'title': article.title,
                'content': article.content,
                'source': article.source,
                'category': article.category,
                'city_or_keyword': article.city_or_keyword
            }
            for article in request.articles
        ]
        
        results = await moderation_service.batch_moderate(articles)
        
        # Convert results to response format
        response_results = [
            ContentModerationResponse(
                is_approved=result.is_approved,
                reason=result.reason,
                content_type=result.content_type,
                confidence=result.confidence,
                flagged_categories=result.flagged_categories,
                suggested_actions=result.suggested_actions
            )
            for result in results
        ]
        
        # Get statistics
        statistics = moderation_service.get_moderation_stats(results)
        
        return BatchModerationResponse(
            results=response_results,
            statistics=statistics
        )
        
    except Exception as e:
        logger.exception(f"Batch moderation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch moderation failed: {str(e)}")


@router.get("/health")
async def moderation_health():
    """
    Health check endpoint for the moderation service.
    
    Returns the status of the moderation system and configuration.
    """
    try:
        moderation_service = ModerationService()
        
        # Test with a simple content
        test_result = await moderation_service.moderate_content(
            title="Test Article",
            content="This is a test article for health check.",
            source="Test Source",
            category="test",
            city_or_keyword="test"
        )
        
        return {
            "status": "healthy",
            "service": "moderation",
            "openai_configured": moderation_service.openai_client is not None,
            "test_result": {
                "is_approved": test_result.is_approved,
                "content_type": test_result.content_type,
                "confidence": test_result.confidence
            }
        }
        
    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "moderation",
            "error": str(e)
        }


@router.get("/info")
async def moderation_info():
    """
    Get information about the moderation system.
    
    Returns details about what content is accepted and rejected.
    """
    return {
        "moderation_system": "OmniPush Content Moderation",
        "focus_areas": [
            "Location/keyword-specific content",
            "High-quality generic news",
            "Spam and harmful content filtering"
        ],
        "accepted_content": {
            "location_specific": [
                "Local news, events, developments in the specified city/keyword",
                "Business, technology, education, healthcare related to the location/keyword",
                "Cultural, social, community news from the specified area",
                "Infrastructure, real estate, economic developments in the location",
                "Local government, civic issues, and public services",
                "Content directly mentioning or related to the specified city/keyword"
            ],
            "generic_news": [
                "Major national/international developments",
                "Technology breakthroughs and innovations",
                "Scientific discoveries and research",
                "Business and economic news of significance",
                "Health and wellness updates",
                "Environmental and sustainability news"
            ]
        },
        "rejected_content": [
            "Spam, clickbait, or low-quality content",
            "Harmful, misleading, or fake news",
            "Content unrelated to specified location/keyword or general news",
            "Overly promotional or commercial content",
            "Content that could cause harm or spread misinformation"
        ],
        "moderation_steps": [
            "Safety check using OpenAI moderation API",
            "Relevance check using GPT-4 for content analysis with dynamic location/keyword",
            "Fallback keyword-based moderation with dynamic keyword generation"
        ],
        "parameters": {
            "city_or_keyword": "Configurable city or keyword to focus content filtering (default: 'coimbatore')"
        }
    }
