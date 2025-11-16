"""
News API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from app.models.news_article import NewsArticleCreate, NewsArticleResponse, NewsArticleUpdate
from app.services.news_article_service import NewsArticleService

router = APIRouter()
news_service = NewsArticleService()

@router.post("/", response_model=NewsArticleResponse, status_code=201)
async def create_article(article: NewsArticleCreate):
    """Create a new news article"""
    try:
        return await news_service.create_article(article)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[dict])
async def get_articles(
    platform: Optional[str] = Query(None, regex="^(web_news|print_daily|print_magazine)$", description="Platform: web_news, print_daily, or print_magazine"),
    source: Optional[str] = Query(None, description="News source name"),
    cluster_type: Optional[str] = Query(None, regex="^(own|competitor)$"),
    cluster_id: Optional[str] = None,
    threat_level: Optional[str] = Query(None, regex="^(low|medium|high|critical)$", description="v19.0 threat level"),
    category: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get news articles with optional filters - Enhanced for v19.0"""
    from app.core.database import get_database
    
    db = get_database()
    collection = db.news_articles
    
    # Build query
    query = {}
    if platform:
        query["platform"] = platform
    if source:
        query["source"] = {"$regex": source, "$options": "i"}
    if cluster_type:
        query["matched_clusters.cluster_type"] = cluster_type
    if cluster_id:
        query["matched_clusters.cluster_id"] = cluster_id
    if threat_level:
        query["intelligence.threat_level"] = {"$regex": threat_level, "$options": "i"}
    if category:
        query["category"] = {"$regex": category, "$options": "i"}
    
    # Execute query
    cursor = collection.find(query).sort("published_at", -1).skip(skip).limit(limit)
    articles = await cursor.to_list(length=limit)
    
    # Format response
    formatted_articles = []
    for article in articles:
        formatted_article = {
            "id": str(article["_id"]),
            "platform": article.get("platform", "web_news"),
            "title": article.get("title", ""),
            "summary": article.get("summary", ""),
            "content": article.get("content", ""),
            "source": article.get("source", ""),
            "author": article.get("author", ""),
            "url": article.get("url", ""),
            "published_at": article.get("published_at"),
            "collected_at": article.get("collected_at"),
            "matched_clusters": article.get("matched_clusters", []),
            "intelligence": article.get("intelligence", {}),
            "category": article.get("category", ""),
            "language": article.get("language", "en"),
            "cluster_keywords": article.get("cluster_keywords", [])
        }
        formatted_articles.append(formatted_article)
    
    return formatted_articles

@router.get("/threats", response_model=List[NewsArticleResponse])
async def get_threat_articles(
    cluster_type: Optional[str] = Query(None, regex="^(own|competitor)$"),
    impact_threshold: str = Query("medium", regex="^(low|medium|high)$")
):
    """Get news articles that are marked as threats (v19.0)"""
    return await news_service.get_threat_articles(
        cluster_type=cluster_type,
        impact_threshold=impact_threshold
    )

@router.get("/{article_id}", response_model=NewsArticleResponse)
async def get_article(article_id: str):
    """Get news article by ID"""
    article = await news_service.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

@router.patch("/{article_id}", response_model=NewsArticleResponse)
async def update_article(article_id: str, update_data: NewsArticleUpdate):
    """Update a news article"""
    article = await news_service.update_article(article_id, update_data)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

@router.delete("/{article_id}", status_code=204)
async def delete_article(article_id: str):
    """Delete a news article"""
    success = await news_service.delete_article(article_id)
    if not success:
        raise HTTPException(status_code=404, detail="Article not found")

# Platform-specific endpoints
@router.get("/platforms/web", response_model=List[NewsArticleResponse])
async def get_web_news(
    cluster_type: Optional[str] = Query(None, regex="^(own|competitor)$"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get web news articles specifically"""
    return await news_service.get_web_news(cluster_type=cluster_type, limit=limit)

@router.get("/platforms/print", response_model=List[NewsArticleResponse])
async def get_print_news(
    cluster_type: Optional[str] = Query(None, regex="^(own|competitor)$"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get print news articles (daily + magazine)"""
    return await news_service.get_print_news(cluster_type=cluster_type, limit=limit)

# v19.0 Entity-Centric endpoints
@router.get("/entity/{entity_name}/sentiment/{sentiment_label}", response_model=List[NewsArticleResponse])
async def get_articles_by_entity_sentiment(
    entity_name: str,
    sentiment_label: str,
    platform: Optional[str] = Query(None, regex="^(web_news|print_daily|print_magazine)$"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get articles where a specific entity has a specific sentiment (v19.0)"""
    return await news_service.get_articles_by_entity_sentiment(
        entity_name=entity_name,
        sentiment_label=sentiment_label,
        platform=platform,
        limit=limit
    )

@router.get("/high-impact", response_model=List[NewsArticleResponse])
async def get_high_impact_articles(
    impact_level: str = Query("high", regex="^(medium|high)$"),
    limit: int = Query(50, ge=1, le=1000)
):
    """Get articles with high impact level"""
    return await news_service.get_high_impact_articles(impact_level=impact_level, limit=limit)

# Dashboard endpoints
@router.get("/dashboard-stats")
async def get_news_dashboard_stats():
    """Get dashboard statistics for news articles"""
    return await news_service.get_dashboard_stats()

@router.get("/dashboard-stats/positive", response_model=List[NewsArticleResponse])
async def get_positive_news(limit: int = Query(100, ge=1, le=1000)):
    """Get positive news coverage for widget popup"""
    return await news_service.get_widget_articles("positive", limit)

@router.get("/dashboard-stats/negative", response_model=List[NewsArticleResponse])
async def get_negative_news(limit: int = Query(100, ge=1, le=1000)):
    """Get negative news coverage for widget popup"""
    return await news_service.get_widget_articles("negative", limit)

@router.get("/dashboard-stats/high-impact", response_model=List[NewsArticleResponse])
async def get_high_impact_news(limit: int = Query(100, ge=1, le=1000)):
    """Get high impact articles for widget popup"""
    return await news_service.get_widget_articles("high_impact", limit)

@router.get("/dashboard-stats/threats", response_model=List[NewsArticleResponse])
async def get_threat_news(limit: int = Query(100, ge=1, le=1000)):
    """Get threat articles for widget popup"""
    return await news_service.get_widget_articles("threats", limit)