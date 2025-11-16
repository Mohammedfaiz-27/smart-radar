"""
Business logic for social post management
"""
from typing import List, Optional
from bson import ObjectId
from datetime import datetime

from app.core.database import get_database
from app.models.social_post import SocialPostCreate, SocialPostInDB, SocialPostResponse

class SocialPostService:
    def __init__(self):
        self._db = None
        self._collection = None
    
    @property
    def collection(self):
        if self._collection is None:
            self._db = get_database()
            # Use social_posts collection for new data
            self._collection = self._db.social_posts
        return self._collection

    async def create_post(self, post_data: SocialPostCreate) -> SocialPostResponse:
        """Create a new social post"""
        post_dict = post_data.dict()
        post_dict["collected_at"] = datetime.utcnow()
        
        result = await self.collection.insert_one(post_dict)
        created_post = await self.collection.find_one({"_id": result.inserted_id})
        
        return self._format_post_response(created_post)

    async def get_post(self, post_id: str) -> Optional[SocialPostResponse]:
        """Get post by ID"""
        if not ObjectId.is_valid(post_id):
            return None
            
        post = await self.collection.find_one({"_id": ObjectId(post_id)})
        if post:
            return self._format_post_response(post)
        return None

    async def get_posts(self, 
                       cluster_type: Optional[str] = None,
                       cluster_id: Optional[str] = None,
                       platform: Optional[str] = None,
                       is_threat: Optional[bool] = None,
                       threat_level: Optional[str] = None,
                       skip: int = 0,
                       limit: int = 100) -> List[SocialPostResponse]:
        """Get all posts with optional filters - Enhanced for v19.0 multi-platform"""
        query = {}
        
        # Filter by cluster type (for matched_clusters array)
        if cluster_type:
            query["matched_clusters.cluster_type"] = cluster_type
        
        # Filter by specific cluster ID
        if cluster_id:
            query["matched_clusters.cluster_id"] = cluster_id
        
        # Filter by platform (X, Facebook, YouTube)
        if platform:
            query["platform"] = platform
        
        # Filter by threat level (v19.0 format)
        if threat_level:
            query["intelligence.threat_level"] = threat_level
        
        # Legacy threat support (backwards compatibility)
        if is_threat is not None:
            if is_threat:
                query["intelligence.threat_level"] = {"$in": ["medium", "high", "critical"]}
            else:
                query["intelligence.threat_level"] = "low"

        cursor = self.collection.find(query).sort("collected_at", -1).skip(skip).limit(limit)
        posts = await cursor.to_list(length=limit)
        
        return [self._format_post_response(post) for post in posts]

    async def get_threat_posts(self, 
                              cluster_type: Optional[str] = None,
                              sentiment_threshold: float = -0.5) -> List[SocialPostResponse]:
        """Get posts that meet threat criteria"""
        query = {
            "$and": [
                {"intelligence.is_threat": True},
                {"intelligence.sentiment_score": {"$lt": sentiment_threshold}}
            ]
        }
        
        if cluster_type:
            query["cluster_type"] = cluster_type

        cursor = self.collection.find(query).sort("collected_at", -1)
        posts = await cursor.to_list(length=None)
        
        return [self._format_post_response(post) for post in posts]

    async def mark_as_responded(self, post_id: str) -> bool:
        """Mark post as responded to"""
        if not ObjectId.is_valid(post_id):
            return False
            
        result = await self.collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": {"has_been_responded_to": True}}
        )
        
        return result.matched_count > 0

    def _format_post_response(self, post_data: dict) -> SocialPostResponse:
        """Format post data for response"""
        # Create a copy to avoid modifying original data
        formatted_data = post_data.copy()
        
        # Convert ObjectId fields to strings
        formatted_data["id"] = str(formatted_data["_id"])
        if "cluster_id" in formatted_data:
            formatted_data["cluster_id"] = str(formatted_data["cluster_id"])
        
        # Remove the original _id field
        del formatted_data["_id"]
        
        # Extract author information more intelligently
        author = self._extract_author_info(formatted_data)
        
        # Ensure all required fields have default values if missing
        formatted_data.setdefault("platform", "x")
        formatted_data.setdefault("cluster_type", "own")
        formatted_data.setdefault("content", "")
        formatted_data["author"] = author  # Use extracted author
        formatted_data.setdefault("post_url", "")
        formatted_data.setdefault("posted_at", formatted_data.get("collected_at", datetime.utcnow()))
        formatted_data.setdefault("engagement_metrics", {})
        formatted_data.setdefault("intelligence", {})
        formatted_data.setdefault("has_been_responded_to", False)
        formatted_data.setdefault("collected_at", datetime.utcnow())
        
        # Convert sentiment from intelligence.sentiment_label if missing
        if not formatted_data.get("sentiment"):
            intelligence = formatted_data.get("intelligence", {})
            sentiment_label = intelligence.get("sentiment_label")
            if sentiment_label:
                # Convert from "Neutral"/"Positive"/"Negative" to lowercase
                formatted_data["sentiment"] = sentiment_label.lower()
            else:
                # Fallback to converting from sentiment_score
                formatted_data["sentiment"] = self._convert_sentiment_score_to_text(formatted_data)
        
        return SocialPostResponse(**formatted_data)
    
    def _extract_author_info(self, post_data: dict) -> str:
        """Extract author information from various possible fields"""
        import re
        
        # Try direct author fields first
        possible_author_fields = ['author', 'username', 'user', 'handle', 'screen_name', 'author_name', 'user_name', 'created_by']
        
        for field in possible_author_fields:
            if post_data.get(field) and post_data[field] not in ['', 'Unknown', 'unknown']:
                return post_data[field]
        
        # Try to extract from content using regex patterns
        content = post_data.get('content', '')
        
        # Look for @mentions at the beginning of the content (author)
        author_patterns = [
            r'^@(\w+)',  # @username at start
            r'@(\w+)\s',  # @username followed by space
        ]
        
        for pattern in author_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        
        # Look for mentions in the content (extract first mention as potential author)
        mentions = re.findall(r'@(\w+)', content)
        if mentions:
            return mentions[0]  # Return first mention as author
        
        # If nothing found, return unknown
        return "unknown"
    
    def _convert_sentiment_score_to_text(self, post_data: dict) -> str:
        """Convert numeric sentiment score to text label"""
        intelligence = post_data.get("intelligence", {})
        sentiment_score = intelligence.get("sentiment_score")
        
        if sentiment_score is None:
            return "neutral"
        
        # Convert numeric score to text based on thresholds
        # Assuming sentiment_score is between -1 and 1
        if sentiment_score >= 0.3:
            return "positive"
        elif sentiment_score <= -0.3:
            return "negative"
        else:
            return "neutral"
    
    async def fix_cluster_types(self) -> int:
        """Fix incorrect cluster types in existing posts"""
        # Import here to avoid circular imports
        from app.services.cluster_service import ClusterService
        
        cluster_service = ClusterService()
        
        # Get all clusters to build mapping
        clusters_response = await cluster_service.get_clusters()
        cluster_map = {str(cluster.id): cluster.cluster_type for cluster in clusters_response}
        
        # Find and fix posts with incorrect cluster_type
        fixed_count = 0
        
        async for post in self.collection.find():
            cluster_id = str(post.get("cluster_id", ""))
            current_cluster_type = post.get("cluster_type", "")
            correct_cluster_type = cluster_map.get(cluster_id)
            
            if correct_cluster_type and current_cluster_type != correct_cluster_type:
                await self.collection.update_one(
                    {"_id": post["_id"]},
                    {"$set": {"cluster_type": correct_cluster_type}}
                )
                fixed_count += 1
        
        return fixed_count
    
    # Platform-specific query methods
    async def get_x_posts(self, cluster_type: Optional[str] = None, limit: int = 100) -> List[SocialPostResponse]:
        """Get X (Twitter) posts specifically"""
        return await self.get_posts(platform="X", cluster_type=cluster_type, limit=limit)
    
    async def get_facebook_posts(self, cluster_type: Optional[str] = None, limit: int = 100) -> List[SocialPostResponse]:
        """Get Facebook posts specifically"""
        return await self.get_posts(platform="Facebook", cluster_type=cluster_type, limit=limit)
    
    async def get_youtube_posts(self, cluster_type: Optional[str] = None, limit: int = 100) -> List[SocialPostResponse]:
        """Get YouTube posts specifically"""
        return await self.get_posts(platform="YouTube", cluster_type=cluster_type, limit=limit)
    
    async def get_posts_by_entity_sentiment(self, entity_name: str, sentiment_label: str, 
                                          platform: Optional[str] = None, limit: int = 100) -> List[SocialPostResponse]:
        """Get posts where a specific entity has a specific sentiment (v19.0)"""
        query = {
            f"intelligence.entity_sentiments.{entity_name}.label": sentiment_label
        }
        
        if platform:
            query["platform"] = platform
        
        cursor = self.collection.find(query).sort("collected_at", -1).limit(limit)
        posts = await cursor.to_list(length=limit)
        
        return [self._format_post_response(post) for post in posts]
    
    async def get_high_engagement_posts(self, platform: str, engagement_threshold: int = 100, 
                                      limit: int = 50) -> List[SocialPostResponse]:
        """Get posts with high engagement metrics by platform"""
        query = {"platform": platform}
        
        if platform == "X":
            query["$or"] = [
                {"engagement_metrics.retweets": {"$gte": engagement_threshold}},
                {"engagement_metrics.likes": {"$gte": engagement_threshold * 2}}
            ]
        elif platform == "Facebook":
            query["$or"] = [
                {"engagement_metrics.shares": {"$gte": engagement_threshold}},
                {"engagement_metrics.likes": {"$gte": engagement_threshold * 2}}
            ]
        elif platform == "YouTube":
            query["$or"] = [
                {"engagement_metrics.views": {"$gte": engagement_threshold * 10}},
                {"engagement_metrics.likes": {"$gte": engagement_threshold}}
            ]
        
        cursor = self.collection.find(query).sort("collected_at", -1).limit(limit)
        posts = await cursor.to_list(length=limit)
        
        return [self._format_post_response(post) for post in posts]

    async def get_dashboard_stats(self) -> dict:
        """Get dashboard statistics for all clusters"""
        from datetime import datetime, timedelta
        
        # Get total posts count (only social_post type from monitored_content)
        posts_today = await self.collection.count_documents({"content_type": "social_post"})
        
        # Count positive posts for "own" clusters
        # Look for posts where matched_clusters has cluster_type="own" 
        # AND any entity has positive sentiment
        own_positive_pipeline = [
            {"$match": {"content_type": "social_post"}},
            {"$match": {"matched_clusters.cluster_type": "own"}},
            {"$unwind": "$intelligence.entity_sentiments"},
            {"$match": {"intelligence.entity_sentiments.label": "Positive"}},
            {"$group": {"_id": "$_id"}},  # De-duplicate by document ID
            {"$count": "total"}
        ]
        
        # Alternative approach - count documents with at least one positive sentiment
        own_positive = 0
        own_negative = 0
        competitor_negative = 0
        
        # Query all social posts
        cursor = self.collection.find({"content_type": "social_post"})
        
        async for doc in cursor:
            # Check if this post has "own" cluster type
            has_own_cluster = False
            has_competitor_cluster = False
            
            if "matched_clusters" in doc:
                for cluster in doc.get("matched_clusters", []):
                    if cluster.get("cluster_type") == "own":
                        has_own_cluster = True
                    elif cluster.get("cluster_type") == "competitor":
                        has_competitor_cluster = True
            
            # Check sentiments
            if doc.get("intelligence") and doc["intelligence"].get("entity_sentiments"):
                sentiments = doc["intelligence"]["entity_sentiments"]
                
                # For own clusters, count positive and negative
                if has_own_cluster:
                    for entity, sentiment_data in sentiments.items():
                        if isinstance(sentiment_data, dict) and sentiment_data.get("label") == "Positive":
                            own_positive += 1
                            break  # Count each post only once
                    
                    for entity, sentiment_data in sentiments.items():
                        if isinstance(sentiment_data, dict) and sentiment_data.get("label") == "Negative":
                            own_negative += 1
                            break  # Count each post only once
                
                # For competitor clusters, count negative (opportunities)
                if has_competitor_cluster:
                    for entity, sentiment_data in sentiments.items():
                        if isinstance(sentiment_data, dict) and sentiment_data.get("label") == "Negative":
                            competitor_negative += 1
                            break  # Count each post only once
        
        return {
            "posts_today": posts_today,
            "positive_posts": own_positive,
            "negative_posts": own_negative,
            "opportunities": competitor_negative
        }

    async def get_widget_posts(self, widget_type: str, limit: int = 100) -> List[SocialPostResponse]:
        """Get posts for specific widget type using entity-centric sentiment v19.0"""
        if widget_type == "positive":
            # DMK positive posts
            query = {
                "matched_clusters.cluster_name": "DMK",
                "intelligence.entity_sentiments.DMK.label": "Positive"
            }
        elif widget_type == "negative":
            # DMK negative posts  
            query = {
                "matched_clusters.cluster_name": "DMK",
                "intelligence.entity_sentiments.DMK.label": "Negative"
            }
        elif widget_type == "opportunities":
            # Competitor negative posts
            query = {
                "matched_clusters.cluster_type": "competitor",
                "$or": [
                    {"intelligence.entity_sentiments.BJP.label": "Negative"},
                    {"intelligence.entity_sentiments.ADMK.label": "Negative"},
                    {"intelligence.entity_sentiments.TVK.label": "Negative"}
                ]
            }
        else:
            raise ValueError(f"Invalid widget type: {widget_type}")
        
        # Fetch posts with the query
        cursor = self.collection.find(query).sort("collected_at", -1).limit(limit)
        posts = await cursor.to_list(length=limit)
        
        # Format and return posts
        return [self._format_post_response(post) for post in posts]