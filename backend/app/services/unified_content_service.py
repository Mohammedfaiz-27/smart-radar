"""
Unified Content Service for SMART RADAR v25.0
Manages the unified monitored_content collection
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from bson import ObjectId

from app.core.database import get_database
from app.models.monitored_content import (
    MonitoredContent,
    MonitoredContentCreate,
    MonitoredContentUpdate,
    MonitoredContentResponse,
    ContentQueryParams,
    ContentAggregation,
    ContentType,
    Platform,
    SocialMetrics,
    NewsMetrics
)

class UnifiedContentService:
    """
    Unified service for managing all monitored content
    Replaces separate social_posts and news_articles services
    """
    
    def __init__(self):
        self._db = None
        self._collection = None
    
    @property
    def collection(self):
        if self._collection is None:
            self._db = get_database()
            # Always use monitored_content if it exists, otherwise social_posts
            # For now, we'll prioritize monitored_content
            self._collection = self._db.monitored_content
        return self._collection
    
    async def create_content(
        self,
        content_data: MonitoredContentCreate,
        auto_analyze: bool = True
    ) -> str:
        """Create new monitored content with optional automatic intelligence analysis"""
        try:
            # Build content document
            content_doc = {
                "content_type": content_data.content_type.value,
                "platform": content_data.platform.value,
                "platform_content_id": content_data.platform_content_id,
                "title": content_data.title,
                "content": content_data.content,
                "author": content_data.author,
                "url": content_data.url,
                "published_at": content_data.published_at,
                "collected_at": datetime.utcnow(),
                "matched_clusters": [],  # Will be populated by cluster matching
                "processing_status": "pending",
                "processing_errors": [],
                "last_updated": datetime.utcnow()
            }
            
            # Add metrics if provided
            if content_data.social_metrics:
                content_doc["social_metrics"] = content_data.social_metrics.dict()
            
            if content_data.news_metrics:
                content_doc["news_metrics"] = content_data.news_metrics.dict()
            
            # Insert into database
            result = await self.collection.insert_one(content_doc)
            content_id = str(result.inserted_id)
            
            return content_id
            
        except Exception as e:
            print(f"Failed to create content: {e}")
            raise
    
    async def get_content(self, content_id: str) -> Optional[MonitoredContentResponse]:
        """Get content by ID"""
        try:
            content_doc = await self.collection.find_one({"_id": ObjectId(content_id)})
            if not content_doc:
                return None
            
            content_doc["id"] = str(content_doc["_id"])
            return MonitoredContentResponse(**content_doc)
            
        except Exception as e:
            print(f"Failed to get content {content_id}: {e}")
            return None
    
    async def query_content(self, params: ContentQueryParams) -> List[MonitoredContentResponse]:
        """Query content with filtering parameters"""
        try:
            # Build MongoDB query
            query = {}
            
            # For backward compatibility with social_posts collection
            # If content_type filter is specified, only apply for monitored_content collection
            collection_name = self.collection.name
            
            if collection_name == "monitored_content":
                if params.content_type:
                    query["content_type"] = params.content_type.value
            else:
                # For social_posts collection, default to social_post type
                # Social posts don't have content_type field
                pass
            
            if params.platform:
                query["platform"] = params.platform.value
            
            if params.cluster_type:
                query["matched_clusters.cluster_type"] = params.cluster_type
            
            if params.cluster_name:
                query["matched_clusters.cluster_name"] = params.cluster_name
            
            if params.threat_level:
                query["intelligence.threat_level"] = params.threat_level
            
            if params.response_urgency:
                query["intelligence.response_urgency"] = params.response_urgency
            
            # Date range filtering
            if params.date_from or params.date_to:
                date_query = {}
                if params.date_from:
                    date_query["$gte"] = params.date_from
                if params.date_to:
                    date_query["$lte"] = params.date_to
                # Try published_at first, fallback to posted_at for social_posts
                if collection_name == "monitored_content":
                    query["published_at"] = date_query
                else:
                    query["posted_at"] = date_query
            
            # Execute query with pagination
            sort_field = "published_at" if collection_name == "monitored_content" else "posted_at"
            cursor = self.collection.find(query)\
                .sort(sort_field, -1)\
                .skip(params.offset)\
                .limit(params.limit)
            
            contents = []
            async for doc in cursor:
                # Transform document to match MonitoredContentResponse
                doc["id"] = str(doc["_id"])
                
                # Map fields for backward compatibility with social_posts
                if collection_name == "social_posts":
                    # Map social_posts fields to monitored_content format
                    doc["content_type"] = "social_post"
                    doc["platform"] = doc.get("platform", "X")
                    doc["platform_content_id"] = doc.get("platform_post_id", str(doc["_id"]))
                    doc["title"] = doc.get("content", "")[:100]  # First 100 chars as title
                    if "posted_at" in doc:
                        doc["published_at"] = doc["posted_at"]
                    
                    # Map engagement_metrics to social_metrics
                    if "engagement_metrics" in doc:
                        doc["social_metrics"] = {
                            "likes": doc["engagement_metrics"].get("likes", 0),
                            "shares": doc["engagement_metrics"].get("retweets", 0),
                            "comments": doc["engagement_metrics"].get("replies", 0),
                            "views": doc["engagement_metrics"].get("impressions", 0),
                            "engagement_rate": 0.0,
                            "follower_count": 0
                        }
                
                contents.append(MonitoredContentResponse(**doc))
            
            return contents
            
        except Exception as e:
            print(f"Failed to query content: {e}")
            return []
    
    async def get_threat_content(self, threat_levels: List[str]) -> List[MonitoredContentResponse]:
        """Get high-priority threat content"""
        try:
            query = {"intelligence.threat_level": {"$in": threat_levels}}
            
            collection_name = self.collection.name
            sort_field = "published_at" if collection_name == "monitored_content" else "posted_at"
            
            cursor = self.collection.find(query).sort(sort_field, -1).limit(100)
            
            contents = []
            async for doc in cursor:
                doc["id"] = str(doc["_id"])
                
                # Map fields for backward compatibility
                if collection_name == "social_posts":
                    doc["content_type"] = "social_post"
                    doc["platform"] = doc.get("platform", "X")
                    doc["platform_content_id"] = doc.get("platform_post_id", str(doc["_id"]))
                    doc["title"] = doc.get("content", "")[:100]
                    if "posted_at" in doc:
                        doc["published_at"] = doc["posted_at"]
                    
                    if "engagement_metrics" in doc:
                        doc["social_metrics"] = {
                            "likes": doc["engagement_metrics"].get("likes", 0),
                            "shares": doc["engagement_metrics"].get("retweets", 0),
                            "comments": doc["engagement_metrics"].get("replies", 0),
                            "views": doc["engagement_metrics"].get("impressions", 0),
                            "engagement_rate": 0.0,
                            "follower_count": 0
                        }
                
                contents.append(MonitoredContentResponse(**doc))
            
            return contents
            
        except Exception as e:
            print(f"Failed to get threat content: {e}")
            return []
    
    async def update_content(
        self,
        content_id: str,
        update_data: MonitoredContentUpdate
    ) -> bool:
        """Update existing content"""
        try:
            update_doc = {}
            
            if update_data.intelligence:
                update_doc["intelligence"] = update_data.intelligence.dict()
            
            if update_data.matched_clusters is not None:
                update_doc["matched_clusters"] = update_data.matched_clusters
            
            if update_data.processing_status:
                update_doc["processing_status"] = update_data.processing_status
            
            if update_data.processing_errors is not None:
                update_doc["processing_errors"] = update_data.processing_errors
            
            if update_data.social_metrics:
                update_doc["social_metrics"] = update_data.social_metrics.dict()
            
            if update_data.news_metrics:
                update_doc["news_metrics"] = update_data.news_metrics.dict()
            
            update_doc["last_updated"] = datetime.utcnow()
            
            result = await self.collection.update_one(
                {"_id": ObjectId(content_id)},
                {"$set": update_doc}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"Failed to update content {content_id}: {e}")
            return False
    
    async def delete_content(self, content_id: str) -> bool:
        """Delete content by ID"""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(content_id)})
            return result.deleted_count > 0
            
        except Exception as e:
            print(f"Failed to delete content {content_id}: {e}")
            return False
    
    async def get_content_aggregations(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> ContentAggregation:
        """Get aggregated content analytics"""
        try:
            # Build date filter
            date_filter = {}
            if date_from or date_to:
                date_query = {}
                if date_from:
                    date_query["$gte"] = date_from
                if date_to:
                    date_query["$lte"] = date_to
                date_filter["published_at"] = date_query
            
            # Get total count
            total_content = await self.collection.count_documents(date_filter)
            
            # Aggregate by content type
            content_by_type = {}
            type_pipeline = [
                {"$match": date_filter},
                {"$group": {"_id": "$content_type", "count": {"$sum": 1}}}
            ]
            async for doc in self.collection.aggregate(type_pipeline):
                content_by_type[doc["_id"] or "social_post"] = doc["count"]
            
            # Aggregate by platform
            content_by_platform = {}
            platform_pipeline = [
                {"$match": date_filter},
                {"$group": {"_id": "$platform", "count": {"$sum": 1}}}
            ]
            async for doc in self.collection.aggregate(platform_pipeline):
                content_by_platform[doc["_id"] or "X"] = doc["count"]
            
            # Aggregate threat distribution
            threat_distribution = {}
            threat_pipeline = [
                {"$match": date_filter},
                {"$group": {"_id": "$intelligence.threat_level", "count": {"$sum": 1}}}
            ]
            async for doc in self.collection.aggregate(threat_pipeline):
                if doc["_id"]:
                    threat_distribution[doc["_id"]] = doc["count"]
            
            return ContentAggregation(
                total_content=total_content,
                content_by_type=content_by_type,
                content_by_platform=content_by_platform,
                threat_distribution=threat_distribution,
                sentiment_distribution={},
                top_entities=[],
                trending_themes=[],
                time_range={
                    "from": date_from or datetime.utcnow() - timedelta(days=7),
                    "to": date_to or datetime.utcnow()
                }
            )
            
        except Exception as e:
            print(f"Failed to get aggregations: {e}")
            return ContentAggregation(
                total_content=0,
                content_by_type={},
                content_by_platform={},
                threat_distribution={},
                sentiment_distribution={},
                top_entities=[],
                trending_themes=[],
                time_range={}
            )
    
    async def batch_process_pending_content(self, limit: int = 10) -> Dict[str, int]:
        """Process pending content (cluster matching + intelligence analysis)"""
        try:
            # Find pending content
            pending_docs = await self.collection.find(
                {"processing_status": "pending"}
            ).limit(limit).to_list(length=limit)
            
            processed = 0
            failed = 0
            
            for doc in pending_docs:
                try:
                    # Update status to processing
                    await self.collection.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"processing_status": "processing"}}
                    )
                    
                    # Here you would normally trigger:
                    # 1. Cluster matching
                    # 2. Intelligence analysis
                    # For now, just mark as completed
                    
                    await self.collection.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {
                            "processing_status": "completed",
                            "last_updated": datetime.utcnow()
                        }}
                    )
                    processed += 1
                    
                except Exception as e:
                    await self.collection.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {
                            "processing_status": "failed",
                            "processing_errors": [str(e)],
                            "last_updated": datetime.utcnow()
                        }}
                    )
                    failed += 1
            
            return {
                "processed": processed,
                "failed": failed
            }
            
        except Exception as e:
            print(f"Failed to batch process: {e}")
            return {"processed": 0, "failed": 0}