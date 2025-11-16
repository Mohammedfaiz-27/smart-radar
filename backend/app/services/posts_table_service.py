"""
Service for managing posts_table database operations
Handles CRUD operations for processed social media posts
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.models.posts_table import (
    PostCreate, PostUpdate, PostInDB, PostResponse,
    PostsQueryParams, PostsAggregateResponse, Platform, SentimentLabel
)
from app.core.database import get_database

class PostsTableService:
    """Service for posts_table operations"""
    
    def __init__(self):
        """Initialize posts table service"""
        self._db = None
        self._collection = None
    
    async def initialize(self):
        """Initialize database connection"""
        if self._db is None:
            self._db = get_database()  # Don't await, it returns the database directly
            self._collection = self._db.posts_table
            
            # Create indexes for efficient querying
            await self._create_indexes()
    
    async def _create_indexes(self):
        """Create database indexes for performance"""
        try:
            # Compound index for common queries
            await self._collection.create_index([
                ("cluster_id", 1),
                ("posted_at", -1)
            ])
            
            # Individual indexes
            await self._collection.create_index("platform")
            await self._collection.create_index("platform_post_id")
            await self._collection.create_index("sentiment_label")
            await self._collection.create_index("is_threat")
            await self._collection.create_index("posted_at")
            await self._collection.create_index("fetched_at")
            
            # Skip text index to avoid language restrictions for Tamil content
            # MongoDB text indexes have language limitations that prevent Tamil storage
            
            # Unique index to prevent duplicates
            await self._collection.create_index(
                [("platform", 1), ("platform_post_id", 1)],
                unique=True
            )
        except Exception as e:
            print(f"Error creating indexes: {e}")
    
    async def create_post(self, post: PostCreate) -> PostResponse:
        """
        Create a new post in database
        
        Args:
            post: PostCreate model with post data
            
        Returns:
            Created post with ID
        """
        await self.initialize()
        
        try:
            # Convert to dict and add timestamps
            post_dict = post.dict()
            post_dict["created_at"] = datetime.utcnow()
            post_dict["updated_at"] = datetime.utcnow()
            
            # Insert into database
            result = await self._collection.insert_one(post_dict)
            
            # Retrieve created post
            created_post = await self._collection.find_one({"_id": result.inserted_id})
            
            # Convert to response model
            created_post["id"] = str(created_post.pop("_id"))
            response = PostResponse(**created_post)
            response.engagement_rate = response.calculate_engagement_rate()
            
            return response
            
        except Exception as e:
            if "duplicate key error" in str(e).lower():
                # Post already exists, update instead
                existing = await self._collection.find_one({
                    "platform": post.platform,
                    "platform_post_id": post.platform_post_id
                })
                if existing:
                    existing["id"] = str(existing.pop("_id"))
                    return PostResponse(**existing)
            raise e
    
    async def update_post(self, post_id: str, update: PostUpdate) -> Optional[PostResponse]:
        """
        Update an existing post
        
        Args:
            post_id: Post ID
            update: Fields to update
            
        Returns:
            Updated post or None if not found
        """
        await self.initialize()
        
        try:
            # Filter out None values
            update_dict = {k: v for k, v in update.dict().items() if v is not None}
            
            if not update_dict:
                return None
            
            # Add updated timestamp
            update_dict["updated_at"] = datetime.utcnow()
            
            # Update in database
            result = await self._collection.update_one(
                {"_id": ObjectId(post_id)},
                {"$set": update_dict}
            )
            
            if result.modified_count == 0:
                return None
            
            # Retrieve updated post
            updated_post = await self._collection.find_one({"_id": ObjectId(post_id)})
            if updated_post:
                updated_post["id"] = str(updated_post.pop("_id"))
                response = PostResponse(**updated_post)
                response.engagement_rate = response.calculate_engagement_rate()
                return response
                
            return None
            
        except Exception as e:
            print(f"Error updating post: {e}")
            return None
    
    async def get_post(self, post_id: str) -> Optional[PostResponse]:
        """
        Get a single post by ID
        
        Args:
            post_id: Post ID
            
        Returns:
            Post or None if not found
        """
        await self.initialize()
        
        try:
            post = await self._collection.find_one({"_id": ObjectId(post_id)})
            if post:
                post["id"] = str(post.pop("_id"))
                response = PostResponse(**post)
                response.engagement_rate = response.calculate_engagement_rate()
                return response
            return None
        except Exception as e:
            print(f"Error getting post: {e}")
            return None
    
    async def query_posts(self, params: PostsQueryParams) -> List[PostResponse]:
        """
        Query posts with filters
        
        Args:
            params: Query parameters
            
        Returns:
            List of matching posts
        """
        await self.initialize()
        
        # Build query filter
        query = {}
        
        if params.cluster_id:
            query["cluster_id"] = params.cluster_id
        
        if params.platform:
            query["platform"] = params.platform
        
        if params.sentiment_label:
            query["sentiment_label"] = params.sentiment_label
        
        if params.is_threat is not None:
            query["is_threat"] = params.is_threat
        
        if params.language:
            query["language"] = params.language
        
        if params.posted_after or params.posted_before:
            date_filter = {}
            if params.posted_after:
                date_filter["$gte"] = params.posted_after
            if params.posted_before:
                date_filter["$lte"] = params.posted_before
            query["posted_at"] = date_filter
        
        if params.min_engagement:
            query["$expr"] = {
                "$gte": [
                    {"$add": ["$likes", "$comments", "$shares"]},
                    params.min_engagement
                ]
            }
        
        # Execute query
        cursor = self._collection.find(query).sort("posted_at", -1)
        
        # Apply pagination
        cursor = cursor.skip(params.skip).limit(params.limit)
        
        # Convert to response models
        posts = []
        skipped_count = 0
        async for post in cursor:
            try:
                post_id = str(post["_id"])  # Get ID before modifying
                post["id"] = str(post.pop("_id"))
                
                # Ensure required timestamp fields exist
                current_time = datetime.utcnow()
                if "created_at" not in post:
                    post["created_at"] = current_time
                if "updated_at" not in post:
                    post["updated_at"] = current_time
                
                response = PostResponse(**post)
                response.engagement_rate = response.calculate_engagement_rate()
                posts.append(response)
            except Exception as e:
                # Log invalid post and skip it
                skipped_count += 1
                print(f"Skipping invalid post {post_id}: {str(e)}")
                # Log the problematic fields
                if "platform" in str(e):
                    print(f"  Invalid platform: {post.get('platform', 'missing')}")
                if "sentiment_label" in str(e):
                    print(f"  Invalid sentiment: {post.get('sentiment_label', 'missing')}")
                if "post_url" in str(e):
                    print(f"  Missing post_url: {'post_url' in post}")
                continue
        
        if skipped_count > 0:
            print(f"Skipped {skipped_count} invalid posts out of {skipped_count + len(posts)} total")
        
        return posts
    
    async def get_posts_by_cluster_and_dashboard(
        self,
        cluster_id: str,
        dashboard_type: str,
        limit: int = 100
    ) -> List[PostResponse]:
        """
        Get posts for a specific cluster and dashboard type
        
        Args:
            cluster_id: Cluster ID
            dashboard_type: Dashboard type (Own/Competitor)
            limit: Maximum number of posts
            
        Returns:
            List of posts
        """
        await self.initialize()
        
        # For now, use cluster_id directly
        # In future, can join with clusters collection to filter by dashboard_type
        params = PostsQueryParams(
            cluster_id=cluster_id,
            limit=limit
        )
        
        return await self.query_posts(params)
    
    async def get_aggregate_stats(self, cluster_id: Optional[str] = None) -> PostsAggregateResponse:
        """
        Get aggregated statistics for posts
        
        Args:
            cluster_id: Optional cluster ID to filter
            
        Returns:
            Aggregated statistics
        """
        await self.initialize()
        
        # Build match stage
        match_stage = {}
        if cluster_id:
            match_stage["cluster_id"] = cluster_id
        
        # Aggregation pipeline
        pipeline = []
        
        if match_stage:
            pipeline.append({"$match": match_stage})
        
        # Get various aggregations
        pipeline.extend([
            {
                "$facet": {
                    "total": [{"$count": "count"}],
                    "by_platform": [
                        {"$group": {"_id": "$platform", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}}
                    ],
                    "by_sentiment": [
                        {"$group": {"_id": "$sentiment_label", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}}
                    ],
                    "threats": [
                        {"$match": {"is_threat": True}},
                        {"$count": "count"}
                    ],
                    "languages": [
                        {"$group": {"_id": "$language"}},
                        {"$limit": 10}
                    ],
                    "engagement": [
                        {
                            "$group": {
                                "_id": None,
                                "total_likes": {"$sum": "$likes"},
                                "total_comments": {"$sum": "$comments"},
                                "total_shares": {"$sum": "$shares"},
                                "total_views": {"$sum": "$views"},
                                "avg_sentiment": {"$avg": "$sentiment_score"}
                            }
                        }
                    ],
                    "narratives": [
                        {"$unwind": "$key_narratives"},
                        {"$group": {"_id": "$key_narratives", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}},
                        {"$limit": 10}
                    ]
                }
            }
        ])
        
        # Execute aggregation
        result = await self._collection.aggregate(pipeline).to_list(1)
        
        if not result:
            return PostsAggregateResponse(
                total_posts=0,
                posts_by_platform={},
                posts_by_sentiment={},
                threat_posts=0,
                languages=[],
                total_engagement={},
                average_sentiment_score=0.0,
                most_common_narratives=[]
            )
        
        facets = result[0]
        
        # Process results
        total_posts = facets["total"][0]["count"] if facets["total"] else 0
        
        posts_by_platform = {
            item["_id"]: item["count"] 
            for item in facets["by_platform"]
        }
        
        posts_by_sentiment = {
            item["_id"]: item["count"] 
            for item in facets["by_sentiment"]
        }
        
        threat_posts = facets["threats"][0]["count"] if facets["threats"] else 0
        
        languages = [item["_id"] for item in facets["languages"] if item["_id"]]
        
        engagement = facets["engagement"][0] if facets["engagement"] else {}
        total_engagement = {
            "likes": engagement.get("total_likes", 0),
            "comments": engagement.get("total_comments", 0),
            "shares": engagement.get("total_shares", 0),
            "views": engagement.get("total_views", 0)
        }
        
        avg_sentiment = engagement.get("avg_sentiment", 0.0)
        
        narratives = [
            {"narrative": item["_id"], "count": item["count"]}
            for item in facets["narratives"]
        ]
        
        return PostsAggregateResponse(
            total_posts=total_posts,
            posts_by_platform=posts_by_platform,
            posts_by_sentiment=posts_by_sentiment,
            threat_posts=threat_posts,
            languages=languages,
            total_engagement=total_engagement,
            average_sentiment_score=avg_sentiment,
            most_common_narratives=narratives
        )
    
    async def delete_post(self, post_id: str) -> bool:
        """
        Delete a post
        
        Args:
            post_id: Post ID
            
        Returns:
            True if deleted, False otherwise
        """
        await self.initialize()
        
        try:
            result = await self._collection.delete_one({"_id": ObjectId(post_id)})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting post: {e}")
            return False
    
    async def bulk_create_posts(self, posts: List[PostCreate]) -> List[PostResponse]:
        """
        Create multiple posts in bulk
        
        Args:
            posts: List of posts to create
            
        Returns:
            List of created posts
        """
        created_posts = []
        
        for post in posts:
            try:
                created = await self.create_post(post)
                created_posts.append(created)
            except Exception as e:
                print(f"Error creating post: {e}")
                continue
        
        return created_posts
    
    async def mark_as_responded(self, post_id: str) -> bool:
        """
        Mark a post as responded to
        
        Args:
            post_id: Post ID
            
        Returns:
            True if updated, False otherwise
        """
        await self.initialize()
        
        try:
            result = await self._collection.update_one(
                {"_id": ObjectId(post_id)},
                {"$set": {"has_been_responded_to": True}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error marking post as responded: {e}")
            return False