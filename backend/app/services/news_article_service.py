"""
Business logic for news article management with v19.0 Entity-Centric Intelligence
"""
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime

from app.core.database import get_database
from app.models.news_article import NewsArticleCreate, NewsArticleInDB, NewsArticleResponse, NewsArticleUpdate
from app.models.common import ClusterMatch


class NewsArticleService:
    def __init__(self):
        self._db = None
        self._collection = None
    
    @property
    def collection(self):
        if self._collection is None:
            self._db = get_database()
            self._collection = self._db.news_articles
        return self._collection

    async def create_article(self, article_data: NewsArticleCreate) -> NewsArticleResponse:
        """Create a new news article with v19.0 intelligence"""
        article_dict = article_data.dict()
        article_dict["collected_at"] = datetime.utcnow()
        
        result = await self.collection.insert_one(article_dict)
        created_article = await self.collection.find_one({"_id": result.inserted_id})
        
        return self._format_article_response(created_article)

    async def get_article(self, article_id: str) -> Optional[NewsArticleResponse]:
        """Get article by ID"""
        if not ObjectId.is_valid(article_id):
            return None
            
        article = await self.collection.find_one({"_id": ObjectId(article_id)})
        if article:
            return self._format_article_response(article)
        return None

    async def get_articles(self, 
                          platform: Optional[str] = None,
                          source: Optional[str] = None,
                          cluster_type: Optional[str] = None,
                          cluster_id: Optional[str] = None,
                          threat_level: Optional[str] = None,
                          category: Optional[str] = None,
                          skip: int = 0,
                          limit: int = 100) -> List[NewsArticleResponse]:
        """Get all articles with optional filters - Enhanced for v19.0"""
        query = {}
        
        # Filter by platform (web_news, print_daily, print_magazine)
        if platform:
            query["platform"] = platform
        
        # Filter by news source
        if source:
            query["source"] = {"$regex": source, "$options": "i"}  # Case-insensitive search
        
        # Filter by cluster type (for matched_clusters array)
        if cluster_type:
            query["matched_clusters.cluster_type"] = cluster_type
        
        # Filter by specific cluster ID
        if cluster_id:
            query["matched_clusters.cluster_id"] = cluster_id
        
        # Filter by threat level (v19.0 format)
        if threat_level:
            query["intelligence.threat_level"] = threat_level
        
        # Filter by category
        if category:
            query["category"] = category

        cursor = self.collection.find(query).sort("published_at", -1).skip(skip).limit(limit)
        articles = await cursor.to_list(length=limit)
        
        return [self._format_article_response(article) for article in articles]

    async def get_threat_articles(self, 
                                 cluster_type: Optional[str] = None,
                                 impact_threshold: str = "medium") -> List[NewsArticleResponse]:
        """Get articles that meet threat criteria"""
        query = {
            "$and": [
                {"intelligence.threat_level": {"$in": ["medium", "high", "critical"]}},
                {"intelligence.impact_level": {"$in": ["medium", "high"]}}
            ]
        }
        
        if cluster_type:
            query["matched_clusters.cluster_type"] = cluster_type

        cursor = self.collection.find(query).sort("published_at", -1)
        articles = await cursor.to_list(length=None)
        
        return [self._format_article_response(article) for article in articles]

    async def update_article(self, article_id: str, update_data: NewsArticleUpdate) -> Optional[NewsArticleResponse]:
        """Update an existing article"""
        if not ObjectId.is_valid(article_id):
            return None
        
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        if not update_dict:
            return await self.get_article(article_id)
        
        result = await self.collection.update_one(
            {"_id": ObjectId(article_id)},
            {"$set": update_dict}
        )
        
        if result.matched_count > 0:
            return await self.get_article(article_id)
        return None

    async def delete_article(self, article_id: str) -> bool:
        """Delete an article"""
        if not ObjectId.is_valid(article_id):
            return False
            
        result = await self.collection.delete_one({"_id": ObjectId(article_id)})
        return result.deleted_count > 0

    def _format_article_response(self, article_data: dict) -> NewsArticleResponse:
        """Format article data for response"""
        # Create a copy to avoid modifying original data
        formatted_data = article_data.copy()
        
        # Convert ObjectId fields to strings
        formatted_data["id"] = str(formatted_data["_id"])
        del formatted_data["_id"]
        
        # Ensure all required fields have default values if missing
        formatted_data.setdefault("platform", "web_news")
        formatted_data.setdefault("title", "")
        formatted_data.setdefault("source", "Unknown")
        formatted_data.setdefault("url", "")
        formatted_data.setdefault("published_at", formatted_data.get("collected_at", datetime.utcnow()))
        formatted_data.setdefault("collected_at", datetime.utcnow())
        formatted_data.setdefault("matched_clusters", [])
        formatted_data.setdefault("perspective_type", "multi")
        formatted_data.setdefault("tags", [])
        
        # Ensure intelligence structure exists
        if "intelligence" not in formatted_data:
            from app.models.news_article import NewsArticleIntelligence
            formatted_data["intelligence"] = NewsArticleIntelligence(
                relational_summary="Not analyzed",
                entity_sentiments={},
                threat_level="low",
                impact_level="medium",
                confidence_score=0.0
            ).dict()
        
        return NewsArticleResponse(**formatted_data)
    
    # Platform-specific query methods
    async def get_web_news(self, cluster_type: Optional[str] = None, limit: int = 100) -> List[NewsArticleResponse]:
        """Get web news articles specifically"""
        return await self.get_articles(platform="web_news", cluster_type=cluster_type, limit=limit)
    
    async def get_print_news(self, cluster_type: Optional[str] = None, limit: int = 100) -> List[NewsArticleResponse]:
        """Get print news articles (daily + magazine)"""
        query = {"platform": {"$in": ["print_daily", "print_magazine"]}}
        if cluster_type:
            query["matched_clusters.cluster_type"] = cluster_type
        
        cursor = self.collection.find(query).sort("published_at", -1).limit(limit)
        articles = await cursor.to_list(length=limit)
        
        return [self._format_article_response(article) for article in articles]
    
    async def get_articles_by_entity_sentiment(self, entity_name: str, sentiment_label: str, 
                                             platform: Optional[str] = None, limit: int = 100) -> List[NewsArticleResponse]:
        """Get articles where a specific entity has a specific sentiment (v19.0)"""
        query = {
            f"intelligence.entity_sentiments.{entity_name}.label": sentiment_label
        }
        
        if platform:
            query["platform"] = platform
        
        cursor = self.collection.find(query).sort("published_at", -1).limit(limit)
        articles = await cursor.to_list(length=limit)
        
        return [self._format_article_response(article) for article in articles]
    
    async def get_high_impact_articles(self, impact_level: str = "high", limit: int = 50) -> List[NewsArticleResponse]:
        """Get articles with high impact level"""
        query = {"intelligence.impact_level": impact_level}
        
        cursor = self.collection.find(query).sort("published_at", -1).limit(limit)
        articles = await cursor.to_list(length=limit)
        
        return [self._format_article_response(article) for article in articles]

    async def get_dashboard_stats(self) -> dict:
        """Get dashboard statistics for news articles using entity-centric sentiment v19.0"""
        from datetime import datetime, timedelta
        
        # Calculate today's date range (UTC)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # Get total articles count
        articles_today = await self.collection.count_documents({})
        
        # Get DMK (own) positive coverage
        dmk_positive_pipeline = [
            {"$match": {"matched_clusters.cluster_name": "DMK"}},
            {"$match": {"intelligence.entity_sentiments.DMK.label": "Positive"}},
            {"$count": "total"}
        ]
        dmk_positive_result = await self.collection.aggregate(dmk_positive_pipeline).to_list(1)
        dmk_positive = dmk_positive_result[0]["total"] if dmk_positive_result else 0
        
        # Get DMK (own) negative coverage
        dmk_negative_pipeline = [
            {"$match": {"matched_clusters.cluster_name": "DMK"}},
            {"$match": {"intelligence.entity_sentiments.DMK.label": "Negative"}},
            {"$count": "total"}
        ]
        dmk_negative_result = await self.collection.aggregate(dmk_negative_pipeline).to_list(1)
        dmk_negative = dmk_negative_result[0]["total"] if dmk_negative_result else 0
        
        # Get high impact articles
        high_impact_pipeline = [
            {"$match": {"intelligence.impact_level": "high"}},
            {"$count": "total"}
        ]
        impact_result = await self.collection.aggregate(high_impact_pipeline).to_list(1)
        high_impact = impact_result[0]["total"] if impact_result else 0
        
        return {
            "articles_today": articles_today,
            "positive_coverage": dmk_positive,
            "negative_coverage": dmk_negative,
            "high_impact_articles": high_impact
        }

    async def get_widget_articles(self, widget_type: str, limit: int = 100) -> List[NewsArticleResponse]:
        """Get articles for specific widget type using entity-centric sentiment v19.0"""
        if widget_type == "positive":
            # DMK positive coverage
            query = {
                "matched_clusters.cluster_name": "DMK",
                "intelligence.entity_sentiments.DMK.label": "Positive"
            }
        elif widget_type == "negative":
            # DMK negative coverage  
            query = {
                "matched_clusters.cluster_name": "DMK",
                "intelligence.entity_sentiments.DMK.label": "Negative"
            }
        elif widget_type == "high_impact":
            # High impact articles
            query = {
                "intelligence.impact_level": "high"
            }
        elif widget_type == "threats":
            # Threat-level articles
            query = {
                "intelligence.threat_level": {"$in": ["medium", "high", "critical"]}
            }
        else:
            raise ValueError(f"Invalid widget type: {widget_type}")
        
        # Fetch articles with the query
        cursor = self.collection.find(query).sort("published_at", -1).limit(limit)
        articles = await cursor.to_list(length=limit)
        
        # Format and return articles
        return [self._format_article_response(article) for article in articles]