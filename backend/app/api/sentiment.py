"""
API endpoints for sentiment analysis
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional

from app.services.sentiment_analysis_service import SentimentAnalysisService

router = APIRouter()

@router.get("/sentiment/organization")
async def get_organization_sentiment(cluster_id: Optional[str] = Query(None, description="Filter by specific cluster ID")) -> Dict[str, Any]:
    """Get sentiment analysis for our organization posts"""
    try:
        service = SentimentAnalysisService()
        # For now, default to DMK as the organization entity
        return await service.get_organization_sentiment(entity_name="DMK")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sentiment/competitors")
async def get_competitor_sentiment(cluster_id: Optional[str] = Query(None, description="Filter by specific cluster ID")) -> Dict[str, Any]:
    """Get sentiment analysis for competitor posts"""
    try:
        service = SentimentAnalysisService()
        # Get consolidated sentiment for all competitor entities
        return await service.get_consolidated_competitor_sentiment()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sentiment/overall")
async def get_overall_sentiment() -> Dict[str, Any]:
    """Get overall sentiment analysis across all posts"""
    try:
        service = SentimentAnalysisService()
        return await service.get_consolidated_overall_sentiment()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sentiment/cluster/{cluster_name}")
async def get_cluster_sentiment(cluster_name: str) -> Dict[str, Any]:
    """Get sentiment analysis for a specific cluster"""
    try:
        # Validate cluster name
        valid_clusters = ["DMK", "BJP", "TVK", "ADMK"]
        if cluster_name.upper() not in valid_clusters:
            raise HTTPException(status_code=400, detail=f"Invalid cluster name. Must be one of: {valid_clusters}")
        
        service = SentimentAnalysisService()
        return await service.get_sentiment_analysis(entity_name=cluster_name.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))