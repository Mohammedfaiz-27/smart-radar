"""
Unified Content API for SMART RADAR v25.0
Single endpoint for all monitored content (social posts + news articles)
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from app.models.monitored_content import (
    MonitoredContentResponse,
    MonitoredContentCreate,
    MonitoredContentUpdate,
    ContentQueryParams,
    ContentAggregation,
    ContentType,
    Platform
)
from app.services.unified_content_service import UnifiedContentService
from app.services.migration_service import MigrationService

router = APIRouter()

# Dependency to get content service
def get_content_service() -> UnifiedContentService:
    return UnifiedContentService()

# Dependency to get migration service
def get_migration_service() -> MigrationService:
    return MigrationService()

@router.get("/", response_model=List[MonitoredContentResponse])
async def get_content(
    content_type: Optional[ContentType] = Query(None, description="Filter by content type"),
    platform: Optional[Platform] = Query(None, description="Filter by platform"),
    cluster_type: Optional[str] = Query(None, description="Filter by cluster type (own/competitor)"),
    cluster_name: Optional[str] = Query(None, description="Filter by specific cluster name"),
    threat_level: Optional[str] = Query(None, description="Filter by threat level"),
    response_urgency: Optional[str] = Query(None, description="Filter by response urgency"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    limit: int = Query(50, ge=1, le=1000, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    service: UnifiedContentService = Depends(get_content_service)
) -> List[MonitoredContentResponse]:
    """Get monitored content with filtering options"""
    try:
        params = ContentQueryParams(
            content_type=content_type,
            platform=platform,
            cluster_type=cluster_type,
            cluster_name=cluster_name,
            threat_level=threat_level,
            response_urgency=response_urgency,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset
        )
        
        return await service.query_content(params)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/threats", response_model=List[MonitoredContentResponse])
async def get_threat_content(
    threat_levels: Optional[str] = Query("high,critical", description="Comma-separated threat levels"),
    service: UnifiedContentService = Depends(get_content_service)
) -> List[MonitoredContentResponse]:
    """Get high-priority threat content"""
    try:
        levels = threat_levels.split(",") if threat_levels else ["high", "critical"]
        return await service.get_threat_content(levels)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/aggregations", response_model=ContentAggregation)
async def get_content_aggregations(
    date_from: Optional[datetime] = Query(None, description="Aggregation start date"),
    date_to: Optional[datetime] = Query(None, description="Aggregation end date"),
    service: UnifiedContentService = Depends(get_content_service)
) -> ContentAggregation:
    """Get aggregated content analytics"""
    try:
        return await service.get_content_aggregations(date_from, date_to)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{content_id}", response_model=MonitoredContentResponse)
async def get_content_by_id(
    content_id: str,
    service: UnifiedContentService = Depends(get_content_service)
) -> MonitoredContentResponse:
    """Get specific content by ID"""
    try:
        content = await service.get_content(content_id)
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")
        return content
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Dict[str, str])
async def create_content(
    content_data: MonitoredContentCreate,
    auto_analyze: bool = Query(True, description="Automatically analyze content intelligence"),
    service: UnifiedContentService = Depends(get_content_service)
) -> Dict[str, str]:
    """Create new monitored content"""
    try:
        content_id = await service.create_content(content_data, auto_analyze)
        return {"content_id": content_id, "status": "created"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{content_id}", response_model=Dict[str, str])
async def update_content(
    content_id: str,
    update_data: MonitoredContentUpdate,
    service: UnifiedContentService = Depends(get_content_service)
) -> Dict[str, str]:
    """Update existing content"""
    try:
        success = await service.update_content(content_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="Content not found")
        return {"content_id": content_id, "status": "updated"}
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{content_id}", response_model=Dict[str, str])
async def delete_content(
    content_id: str,
    service: UnifiedContentService = Depends(get_content_service)
) -> Dict[str, str]:
    """Delete content by ID"""
    try:
        success = await service.delete_content(content_id)
        if not success:
            raise HTTPException(status_code=404, detail="Content not found")
        return {"content_id": content_id, "status": "deleted"}
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Batch processing endpoints
@router.post("/batch/process", response_model=Dict[str, int])
async def batch_process_content(
    limit: int = Query(10, ge=1, le=100, description="Number of items to process"),
    service: UnifiedContentService = Depends(get_content_service)
) -> Dict[str, int]:
    """Process pending content (cluster matching + intelligence analysis)"""
    try:
        return await service.batch_process_pending_content(limit)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Legacy compatibility endpoints for existing frontend
@router.get("/posts", response_model=List[MonitoredContentResponse])
async def get_posts_legacy(
    cluster_type: Optional[str] = Query(None, description="Filter by cluster type (own/competitor)"),
    limit: int = Query(50, ge=1, le=1000),
    service: UnifiedContentService = Depends(get_content_service)
) -> List[MonitoredContentResponse]:
    """Legacy endpoint for posts (maps to social content)"""
    try:
        params = ContentQueryParams(
            content_type=ContentType.SOCIAL_POST,
            cluster_type=cluster_type,
            limit=limit
        )
        return await service.query_content(params)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/posts/threats", response_model=List[MonitoredContentResponse])
async def get_threat_posts_legacy(
    service: UnifiedContentService = Depends(get_content_service)
) -> List[MonitoredContentResponse]:
    """Legacy endpoint for threat posts"""
    try:
        # Filter to only social posts with high threat levels
        all_threats = await service.get_threat_content(["high", "critical"])
        return [content for content in all_threats if content.content_type == ContentType.SOCIAL_POST]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Migration endpoints
@router.post("/migrate/all", response_model=Dict[str, Any])
async def migrate_all_data(
    migration_service: MigrationService = Depends(get_migration_service)
) -> Dict[str, Any]:
    """Migrate all data from separate collections to unified collection"""
    try:
        return await migration_service.migrate_all_data()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/migrate/social-posts", response_model=Dict[str, int])
async def migrate_social_posts(
    migration_service: MigrationService = Depends(get_migration_service)
) -> Dict[str, int]:
    """Migrate social posts to unified collection"""
    try:
        return await migration_service.migrate_social_posts()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/migrate/news-articles", response_model=Dict[str, int])
async def migrate_news_articles(
    migration_service: MigrationService = Depends(get_migration_service)
) -> Dict[str, int]:
    """Migrate news articles to unified collection"""
    try:
        return await migration_service.migrate_news_articles()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/migrate/validate", response_model=Dict[str, Any])
async def validate_migration(
    migration_service: MigrationService = Depends(get_migration_service)
) -> Dict[str, Any]:
    """Validate migration results"""
    try:
        return await migration_service.validate_migration()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Sentiment analysis endpoints (compatibility with existing frontend)
class SentimentResponse(BaseModel):
    entity: str
    overall_sentiment: Dict[str, Any]
    platform_breakdown: Dict[str, Any]
    overall_sentiment_change: float

@router.get("/sentiment/organization", response_model=SentimentResponse)
async def get_organization_sentiment(
    entity_name: str = Query("DMK", description="Organization entity name"),
    service: UnifiedContentService = Depends(get_content_service)
) -> SentimentResponse:
    """Get sentiment analysis for organization entity"""
    try:
        # Query organization content
        params = ContentQueryParams(
            cluster_type="own",
            cluster_name=entity_name,
            limit=1000
        )
        
        contents = await service.query_content(params)
        return await _calculate_entity_sentiment(entity_name, contents)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sentiment/competitors", response_model=SentimentResponse)
async def get_competitor_sentiment(
    service: UnifiedContentService = Depends(get_content_service)
) -> SentimentResponse:
    """Get consolidated sentiment analysis for all competitor entities"""
    try:
        # Query competitor content
        params = ContentQueryParams(
            cluster_type="competitor",
            limit=1000
        )
        
        contents = await service.query_content(params)
        return await _calculate_entity_sentiment("All Competitors", contents)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sentiment/cluster/{cluster_name}", response_model=SentimentResponse)
async def get_cluster_sentiment(
    cluster_name: str,
    service: UnifiedContentService = Depends(get_content_service)
) -> SentimentResponse:
    """Get sentiment analysis for specific cluster"""
    try:
        # Query cluster content
        params = ContentQueryParams(
            cluster_name=cluster_name,
            limit=1000
        )
        
        contents = await service.query_content(params)
        return await _calculate_entity_sentiment(cluster_name, contents)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def _calculate_entity_sentiment(entity_name: str, contents: List[MonitoredContentResponse]) -> SentimentResponse:
    """Calculate sentiment analysis from content list"""
    platform_breakdown = {}
    total_positive = 0
    total_negative = 0
    total_neutral = 0
    total_posts = 0
    
    for content in contents:
        platform = content.platform
        
        if platform not in platform_breakdown:
            platform_breakdown[platform] = {
                "total_posts": 0,
                "sentiments": {"Positive": 0, "Negative": 0, "Neutral": 0},
                "threat_count": 0,
                "sentiment_change": 2.0  # Mock value
            }
        
        # Extract entity sentiment from intelligence
        entity_sentiments = content.intelligence.entity_sentiments if content.intelligence else {}
        
        for entity, sentiment_data in entity_sentiments.items():
            if entity.upper() == entity_name.upper() or entity_name == "All Competitors":
                sentiment_label = sentiment_data.label
                
                platform_breakdown[platform]["total_posts"] += 1
                platform_breakdown[platform]["sentiments"][sentiment_label] += 1
                
                if sentiment_label == "Positive":
                    total_positive += 1
                elif sentiment_label == "Negative":
                    total_negative += 1
                else:
                    total_neutral += 1
                
                total_posts += 1
                
                # Count threats
                if content.intelligence and content.intelligence.threat_level in ["high", "critical"]:
                    platform_breakdown[platform]["threat_count"] += 1
    
    # Calculate overall sentiment percentages
    if total_posts > 0:
        overall_sentiment = {
            "positive_percentage": round((total_positive / total_posts) * 100),
            "negative_percentage": round((total_negative / total_posts) * 100),
            "neutral_percentage": round((total_neutral / total_posts) * 100),
            "total_posts": total_posts
        }
    else:
        overall_sentiment = {
            "positive_percentage": 0,
            "negative_percentage": 0,
            "neutral_percentage": 0,
            "total_posts": 0
        }
    
    return SentimentResponse(
        entity=entity_name,
        overall_sentiment=overall_sentiment,
        platform_breakdown=platform_breakdown,
        overall_sentiment_change=3.2  # Mock value for compatibility
    )