"""
Sentiment analysis service for calculating sentiment statistics
"""
from typing import List, Dict, Any
from app.core.database import get_database

class SentimentAnalysisService:
    def __init__(self):
        self._db = None
        self._collection = None
    
    @property
    def collection(self):
        if self._collection is None:
            self._db = get_database()
            self._collection = self._db.posts_table  # Updated to use posts_table
        return self._collection
    
    async def get_sentiment_analysis(self, entity_name: str = None) -> Dict[str, Any]:
        """Get entity-centric sentiment analysis v19.0"""

        if not entity_name:
            # Default to DMK if no entity specified
            entity_name = "DMK"

        # Get cluster_id by name
        from app.services.cluster_service import ClusterService
        import logging
        logger = logging.getLogger(__name__)

        cluster_service = ClusterService()
        clusters = await cluster_service.get_clusters()
        cluster_id = None
        for cluster in clusters:
            if cluster.name.strip().upper() == entity_name.strip().upper():
                cluster_id = cluster.id
                break

        logger.info(f"🔍 Sentiment Analysis: entity={entity_name}, cluster_id={cluster_id}")

        if not cluster_id:
            # Return empty data if cluster not found
            logger.warning(f"⚠️ Cluster not found for entity: {entity_name}")
            return {
                "entity": entity_name,
                "overall_sentiment": {
                    "positive_percentage": 0,
                    "neutral_percentage": 0,
                    "negative_percentage": 0,
                    "total_posts": 0
                },
                "platform_breakdown": {},
                "overall_sentiment_change": 0.0
            }

        # Build aggregation pipeline using posts_table schema
        # Note: Using sentiment_label field since multi-entity sentiments aren't populated yet
        pipeline = [
            {"$match": {"cluster_id": cluster_id}},
            {"$group": {
                "_id": {
                    "platform": "$platform",
                    "sentiment": "$sentiment_label"  # Use basic sentiment_label field
                },
                "count": {"$sum": 1},
                "avg_score": {"$avg": "$sentiment_score"},  # Use basic sentiment_score
                "threat_count": {
                    "$sum": {
                        "$cond": [{"$eq": ["$is_threat", True]}, 1, 0]
                    }
                }
            }},
            {"$group": {
                "_id": "$_id.platform",
                "sentiments": {
                    "$push": {
                        "sentiment": "$_id.sentiment",
                        "count": "$count",
                        "avg_score": "$avg_score"
                    }
                },
                "total_posts": {"$sum": "$count"},
                "total_threats": {"$sum": "$threat_count"}
            }}
        ]
        
        # Execute aggregation
        logger.info(f"📊 Executing aggregation pipeline on collection: {self.collection.name}")
        logger.info(f"📋 Pipeline: {pipeline}")

        platform_data = {}
        result_count = 0
        async for result in self.collection.aggregate(pipeline):
            result_count += 1
            logger.info(f"📈 Aggregation result #{result_count}: {result}")
            platform = result["_id"]
            sentiments = {"Positive": 0, "Neutral": 0, "Negative": 0}

            for sentiment_data in result["sentiments"]:
                sentiment_label = sentiment_data["sentiment"]
                if sentiment_label:
                    sentiments[sentiment_label] = sentiment_data["count"]

            platform_data[platform] = {
                "total_posts": result["total_posts"],
                "sentiments": sentiments,
                "threat_count": result["total_threats"],
                "sentiment_change": self._calculate_sentiment_change(platform, entity_name)
            }

        logger.info(f"✅ Aggregation complete: {result_count} platform results, total platform_data: {platform_data}")

        # Calculate overall sentiment for the entity
        overall_sentiment = self._calculate_overall_sentiment(platform_data)
        
        return {
            "entity": entity_name,
            "overall_sentiment": overall_sentiment,
            "platform_breakdown": platform_data,
            "overall_sentiment_change": 3.2  # Mock value for now
        }
    
    def _calculate_overall_sentiment(self, platform_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall sentiment across all platforms"""
        total_positive = 0
        total_neutral = 0
        total_negative = 0
        total_posts = 0
        
        for platform, data in platform_data.items():
            sentiments = data["sentiments"]
            total_positive += sentiments.get("Positive", 0)
            total_neutral += sentiments.get("Neutral", 0)
            total_negative += sentiments.get("Negative", 0)
            total_posts += data["total_posts"]
        
        if total_posts == 0:
            return {
                "positive_percentage": 0,
                "neutral_percentage": 0,
                "negative_percentage": 0,
                "total_posts": 0
            }
        
        return {
            "positive_percentage": round((total_positive / total_posts) * 100),
            "neutral_percentage": round((total_neutral / total_posts) * 100),
            "negative_percentage": round((total_negative / total_posts) * 100),
            "total_posts": total_posts
        }
    
    def _calculate_sentiment_change(self, platform: str, cluster_type: str = None) -> float:
        """Calculate sentiment change percentage (mock implementation)"""
        # Mock values for demonstration
        changes = {
            "x": 2.1,
            "facebook": 1.8,
            "youtube": 4.2,
            "instagram": 3.5
        }
        return changes.get(platform.lower(), 2.0)
    
    async def get_organization_sentiment(self, entity_name: str = "DMK") -> Dict[str, Any]:
        """Get sentiment analysis for our organization entity v19.0"""
        return await self.get_sentiment_analysis(entity_name)
    
    async def get_competitor_sentiment(self, entity_name: str = "BJP") -> Dict[str, Any]:
        """Get sentiment analysis for competitor entity v19.0"""
        return await self.get_sentiment_analysis(entity_name)
    
    async def get_consolidated_competitor_sentiment(self) -> Dict[str, Any]:
        """Get consolidated sentiment analysis for ALL competitor entities"""
        # Get all competitor cluster names
        competitor_entities = ["BJP", "TVK", "ADMK"]
        
        # Aggregate data for all competitors
        all_platform_data = {}
        cluster_breakdown = {}
        total_posts = 0
        
        for entity in competitor_entities:
            entity_data = await self.get_sentiment_analysis(entity)
            entity_posts = entity_data["overall_sentiment"]["total_posts"]
            
            # Always include in cluster breakdown, even if 0 posts
            total_posts += entity_posts
            cluster_breakdown[entity] = {
                "total_posts": entity_posts,
                "sentiment_percentages": entity_data["overall_sentiment"]
            }
            
            # Only merge platform data if there are posts
            if entity_posts > 0:
                # Merge platform data
                for platform, platform_data in entity_data["platform_breakdown"].items():
                    if platform not in all_platform_data:
                        all_platform_data[platform] = {
                            "total_posts": 0,
                            "sentiments": {"Positive": 0, "Neutral": 0, "Negative": 0},
                            "threat_count": 0,
                            "sentiment_change": 0
                        }
                    
                    all_platform_data[platform]["total_posts"] += platform_data["total_posts"]
                    for sentiment, count in platform_data["sentiments"].items():
                        all_platform_data[platform]["sentiments"][sentiment] += count
                    all_platform_data[platform]["threat_count"] += platform_data["threat_count"]
        
        # Calculate consolidated overall sentiment
        overall_sentiment = self._calculate_overall_sentiment(all_platform_data)
        
        return {
            "entity": "All Competitors",
            "overall_sentiment": overall_sentiment,
            "platform_breakdown": all_platform_data,
            "cluster_breakdown": cluster_breakdown,
            "overall_sentiment_change": 3.2
        }
    
    async def get_consolidated_overall_sentiment(self) -> Dict[str, Any]:
        """Get consolidated sentiment analysis for ALL entities (organization + competitors)"""
        # Get all cluster names
        all_entities = ["DMK", "BJP", "TVK", "ADMK"]
        
        # Aggregate data for all entities
        all_platform_data = {}
        cluster_breakdown = {}
        total_posts = 0
        
        for entity in all_entities:
            entity_data = await self.get_sentiment_analysis(entity)
            entity_posts = entity_data["overall_sentiment"]["total_posts"]
            
            if entity_posts > 0:
                total_posts += entity_posts
                cluster_breakdown[entity] = {
                    "total_posts": entity_posts,
                    "sentiment_percentages": entity_data["overall_sentiment"]
                }
                
                # Merge platform data
                for platform, platform_data in entity_data["platform_breakdown"].items():
                    if platform not in all_platform_data:
                        all_platform_data[platform] = {
                            "total_posts": 0,
                            "sentiments": {"Positive": 0, "Neutral": 0, "Negative": 0},
                            "threat_count": 0,
                            "sentiment_change": 0
                        }
                    
                    all_platform_data[platform]["total_posts"] += platform_data["total_posts"]
                    for sentiment, count in platform_data["sentiments"].items():
                        all_platform_data[platform]["sentiments"][sentiment] += count
                    all_platform_data[platform]["threat_count"] += platform_data["threat_count"]
        
        # Calculate consolidated overall sentiment
        overall_sentiment = self._calculate_overall_sentiment(all_platform_data)
        
        return {
            "entity": "Overall Public",
            "overall_sentiment": overall_sentiment,
            "platform_breakdown": all_platform_data,
            "cluster_breakdown": cluster_breakdown,
            "overall_sentiment_change": 3.2
        }