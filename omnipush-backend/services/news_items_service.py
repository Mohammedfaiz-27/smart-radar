"""
News Items Service - CRUD operations for external_news_items table
Handles fetched and processed news content with moderation support
NOTE: Post-migration, this service now uses the unified external_news_items table
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from uuid import uuid4

from core.database import get_database
from core.middleware import TenantContext

logger = logging.getLogger(__name__)


class NewsItemsService:
    """Service for managing news items with tenant isolation"""
    
    def __init__(self):
        self.db = get_database()
    
    async def create_news_item(
        self,
        pipeline_id: str,
        title: str,
        content: str,
        source: str,
        source_url: Optional[str] = None,
        category: Optional[str] = None,
        published_at: Optional[datetime] = None,
        url: Optional[str] = None,
        tenant_id: Optional[str] = None,
        moderation_score: Optional[float] = None,
        generated_image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new news item"""
        try:
            news_item_id = str(uuid4())
            
            # Prepare news item data for external_news_items
            news_data = {
                "id": news_item_id,
                "pipeline_id": pipeline_id,
                "tenant_id": tenant_id,
                "external_source": "pipeline",  # Pipeline-sourced content
                "external_id": news_item_id,  # Use ID as external_id
                "title": title[:500],  # Ensure title length limit
                "content": content,
                "source_name": source,  # Display name
                "source_url": source_url or url,
                "category": category,
                "published_at": published_at.isoformat() if published_at else None,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                # Moderation fields
                "moderation_status": "pending",
                "moderation_score": moderation_score,
                "is_approved": False,
                "approval_status": "pending",
                # Publishing
                "generated_image_url": generated_image_url,
                "published_channels": [],
                "status": "pending_moderation"
            }
            
            # Remove None values
            news_data = {k: v for k, v in news_data.items() if v is not None}
            
            response = self.db.service_client.table("external_news_items")\
                .insert(news_data)\
                .execute()
            
            if response.data:
                logger.info(f"Created news item: {title}")
                return response.data[0]
            else:
                raise Exception("Failed to create news item")
                
        except Exception as e:
            logger.exception(f"Failed to create news item: {e}")
            raise e
    
    async def get_news_item(self, news_item_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific news item by ID"""
        try:
            response = self.db.service_client.table("external_news_items")\
                .select("*")\
                .eq("id", news_item_id)\
                .single()\
                .execute()
            
            return response.data if response.data else None
            
        except Exception as e:
            logger.exception(f"Failed to get news item {news_item_id}: {e}")
            return None
    
    async def get_news_items_by_pipeline(
        self,
        pipeline_id: str,
        status: Optional[str] = None,
        moderation_status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get news items for a specific pipeline with optional filtering

        Note: moderation_status param now filters by manual approval status:
        - 'pending': Awaiting manual approval (is_approved=false, not rejected)
        - 'approved': Manually approved (is_approved=true)
        - 'rejected': Rejected by AI or user
        """
        try:
            query = self.db.service_client.table("external_news_items")\
                .select("*")\
                .eq("pipeline_id", pipeline_id)\
                .order("fetched_at", desc=True)\
                .range(offset, offset + limit - 1)

            if status:
                query = query.eq("status", status)

            # Map moderation_status to manual approval status
            if moderation_status:
                mod_status_value = moderation_status.value if hasattr(moderation_status, 'value') else moderation_status

                if mod_status_value == "approved":
                    # Approved = manually approved by user
                    query = query.eq("is_approved", True)
                elif mod_status_value == "rejected":
                    # Rejected = rejected by AI or user
                    # Note: Using 'or' filter for status or moderation_status
                    query = query.or_("status.eq.rejected,moderation_status.eq.rejected")
                elif mod_status_value == "pending":
                    # Pending = awaiting manual approval (not approved, not rejected)
                    query = query.eq("is_approved", False)\
                                 .neq("status", "rejected")\
                                 .neq("moderation_status", "rejected")

            response = query.execute()
            return response.data or []

        except Exception as e:
            logger.exception(f"Failed to get news items for pipeline {pipeline_id}: {e}")
            return []
    
    async def get_news_items_by_tenant(
        self,
        tenant_id: str,
        status: Optional[str] = None,
        moderation_status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get news items for a specific tenant with optional filtering

        IMPORTANT: This endpoint is used for the "Social Post" tab which shows
        scraper job posts from social media platforms (twitter, facebook, instagram).
        It filters OUT newsit, slack, and pipeline sources.

        Note: moderation_status param now filters by manual approval status:
        - 'pending': Awaiting manual approval (is_approved=false, not rejected)
        - 'approved': Manually approved (is_approved=true)
        - 'rejected': Rejected by AI or user
        """
        try:
            # Filter to only social media scraper sources (exclude newsit, slack, pipeline)
            # Social media platforms: twitter, facebook, instagram, linkedin, social_media
            query = self.db.service_client.table("external_news_items")\
                .select("*")\
                .eq("tenant_id", tenant_id)\
                .in_("external_source", ["facebook", "twitter", "instagram", "linkedin", "social_media"])\
                .order("fetched_at", desc=True)\
                .range(offset, offset + limit - 1)

            if status:
                query = query.eq("status", status)

            # Map moderation_status to manual approval status
            if moderation_status:
                mod_status_value = moderation_status.value if hasattr(moderation_status, 'value') else moderation_status

                if mod_status_value == "approved":
                    # Approved = manually approved by user
                    query = query.eq("is_approved", True)
                elif mod_status_value == "rejected":
                    # Rejected = rejected by AI or user
                    query = query.or_("status.eq.rejected,moderation_status.eq.rejected")
                elif mod_status_value == "pending":
                    # Pending = awaiting manual approval (not approved, not rejected)
                    query = query.eq("is_approved", False)\
                                 .neq("status", "rejected")\
                                 .neq("moderation_status", "rejected")

            if category:
                query = query.eq("category", category)

            response = query.execute()
            news_items = response.data or []

            # Optimize: Batch fetch linked posts to avoid N+1 query problem
            # Instead of querying for each news item individually, fetch all at once
            if news_items:
                news_item_ids = [item['id'] for item in news_items]
                linked_posts_map = await self._batch_get_linked_posts(news_item_ids)
                
                # Attach linked posts to each news item
                for item in news_items:
                    item['linked_posts'] = linked_posts_map.get(item['id'], [])

            return news_items

        except Exception as e:
            logger.exception(f"Failed to get news items for tenant {tenant_id}: {e}")
            return []
    
    async def _batch_get_linked_posts(self, news_item_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Batch fetch posts linked to multiple news items (optimized to avoid N+1 queries)
        
        Args:
            news_item_ids: List of news item IDs
            
        Returns:
            Dictionary mapping news_item_id to list of linked posts
        """
        try:
            if not news_item_ids:
                return {}
            
            # Single query to fetch all linked posts for all news items
            response = self.db.service_client.table("posts")\
                .select("id, title, status, published_at, created_at, news_item_id")\
                .in_("news_item_id", news_item_ids)\
                .order("created_at", desc=True)\
                .execute()
            
            # Group posts by news_item_id
            posts_map = {}
            for post in (response.data or []):
                news_item_id = post.get('news_item_id')
                if news_item_id:
                    if news_item_id not in posts_map:
                        posts_map[news_item_id] = []
                    # Remove news_item_id from post object before adding
                    post_copy = {k: v for k, v in post.items() if k != 'news_item_id'}
                    posts_map[news_item_id].append(post_copy)
            
            return posts_map
            
        except Exception as e:
            logger.exception(f"Failed to batch fetch linked posts: {e}")
            return {}

    async def get_linked_posts(self, news_item_id: str) -> List[Dict[str, Any]]:
        """Get posts linked to a specific news item"""
        try:
            response = self.db.service_client.table("posts")\
                .select("id, title, status, published_at, created_at")\
                .eq("news_item_id", news_item_id)\
                .order("created_at", desc=True)\
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.exception(f"Failed to get linked posts for news item {news_item_id}: {e}")
            return []
    
    async def update_news_item(
        self,
        news_item_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a news item with provided fields"""
        try:            
            response = self.db.service_client.table("external_news_items")\
                .update(updates)\
                .eq("id", news_item_id)\
                .execute()
            
            if response.data:
                logger.info(f"Updated news item: {news_item_id}")
                return response.data[0]
            return None
            
        except Exception as e:
            logger.exception(f"Failed to update news item {news_item_id}: {e}")
            raise e
    
    async def update_moderation_status(
        self,
        news_item_id: str,
        moderation_status: str,
        moderation_score: Optional[float] = None,
        moderation_flags: Optional[List[str]] = None,
        moderation_reason: Optional[str] = None,
        processed_content: Optional[str] = None,
        is_approved: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """Update moderation-specific fields for a news item (AI moderation only)"""
        try:
            updates = {
                "moderation_status": moderation_status,
                "moderated_at": datetime.now(timezone.utc).isoformat()
            }

            if moderation_score is not None:
                updates["moderation_score"] = moderation_score
            if moderation_flags is not None:
                updates["moderation_flags"] = moderation_flags
            if moderation_reason is not None:
                updates["moderation_reason"] = moderation_reason
            if processed_content is not None:
                updates["processed_content"] = processed_content
            if is_approved is not None:
                updates["is_approved"] = is_approved

            return await self.update_news_item(news_item_id, updates)

        except Exception as e:
            logger.exception(f"Failed to update moderation for news item {news_item_id}: {e}")
            raise e
    
    async def update_published_channels(
        self,
        news_item_id: str,
        channels: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Update the published channels for a news item"""
        try:
            updates = {
                "published_channels": channels,
                "status": "published" if channels else "draft"
            }
            
            return await self.update_news_item(news_item_id, updates)
            
        except Exception as e:
            logger.exception(f"Failed to update published channels for news item {news_item_id}: {e}")
            raise e
    
    async def delete_news_item(self, news_item_id: str) -> bool:
        """Delete a news item"""
        try:
            response = self.db.service_client.table("external_news_items")\
                .delete()\
                .eq("id", news_item_id)\
                .execute()
            
            success = bool(response.data)
            if success:
                logger.info(f"Deleted news item: {news_item_id}")
            return success
            
        except Exception as e:
            logger.exception(f"Failed to delete news item {news_item_id}: {e}")
            return False
    
    async def get_pending_moderation_items(
        self,
        pipeline_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get news items pending manual approval

        Returns items that are awaiting manual user approval:
        - Not yet manually approved (is_approved=false)
        - Not rejected by AI or user
        - May have passed AI moderation or still pending AI moderation
        """
        try:
            query = self.db.service_client.table("external_news_items")\
                .select("*")\
                .eq("is_approved", False)\
                .neq("status", "rejected")\
                .neq("moderation_status", "rejected")\
                .order("fetched_at", desc=False)\
                .limit(limit)

            if pipeline_id:
                query = query.eq("pipeline_id", pipeline_id)
            if tenant_id:
                query = query.eq("tenant_id", tenant_id)

            response = query.execute()
            return response.data or []

        except Exception as e:
            logger.exception(f"Failed to get pending moderation items: {e}")
            return []
    
    async def get_approved_items(
        self,
        pipeline_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        unpublished_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get approved news items, optionally only unpublished ones"""
        try:
            query = self.db.service_client.table("external_news_items")\
                .select("*")\
                .eq("moderation_status", "approved")\
                .eq("is_approved", True)\
                .order("fetched_at", desc=True)\
                .limit(limit)
            
            if pipeline_id:
                query = query.eq("pipeline_id", pipeline_id)
            if tenant_id:
                query = query.eq("tenant_id", tenant_id)
            if unpublished_only:
                query = query.is_("published_channels", "null").or_("published_channels.eq.{}")
            
            response = query.execute()
            return response.data or []
            
        except Exception as e:
            logger.exception(f"Failed to get approved items: {e}")
            return []
    
    async def search_news_items(
        self,
        search_term: str,
        pipeline_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search news items by title or content"""
        try:
            query = self.db.service_client.table("external_news_items")\
                .select("*")\
                .or_(f"title.ilike.%{search_term}%,content.ilike.%{search_term}%")\
                .order("fetched_at", desc=True)\
                .limit(limit)
            
            if pipeline_id:
                query = query.eq("pipeline_id", pipeline_id)
            if tenant_id:
                query = query.eq("tenant_id", tenant_id)
            
            response = query.execute()
            return response.data or []
            
        except Exception as e:
            logger.exception(f"Failed to search news items: {e}")
            return []
    
    async def get_news_items_stats(
        self,
        pipeline_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Get statistics for news items using optimized single-query aggregation

        Optimized from 5+ separate COUNT queries to 1 aggregated query using
        PostgreSQL's FILTER clause and direct RPC call for better performance.

        Counts based on manual user approval status:
        - pending: Awaiting manual approval (is_approved=false, not rejected)
        - approved: Manually approved by user (is_approved=true)
        - rejected: Rejected by AI moderation or by user
        - published: Has published channels
        """
        try:
            # Use direct PostgreSQL RPC function for aggregated stats
            # This executes a single query with conditional counts using FILTER
            from core.database import db
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            # Build WHERE clause based on filters
            where_conditions = []
            params = []
            
            if pipeline_id:
                where_conditions.append("pipeline_id = %s")
                params.append(pipeline_id)
            if tenant_id:
                where_conditions.append("tenant_id = %s")
                params.append(tenant_id)
            
            where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
            
            # Single aggregated query using COUNT FILTER for all stats at once
            sql = f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE is_approved = true) as approved,
                    COUNT(*) FILTER (WHERE 
                        (moderation_status = 'rejected' OR status = 'rejected')
                    ) as rejected,
                    COUNT(*) FILTER (WHERE 
                        is_approved = false 
                        AND COALESCE(moderation_status, '') != 'rejected'
                        AND COALESCE(status, '') != 'rejected'
                    ) as pending,
                    COUNT(*) FILTER (WHERE 
                        published_channels IS NOT NULL 
                        AND array_length(published_channels, 1) > 0
                    ) as published
                FROM news_items
                {where_clause}
            """
            
            try:
                # Try to use direct PostgreSQL connection for optimized query
                conn_params = db._get_pg_connection_params()
                conn = psycopg2.connect(**conn_params)
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                cursor.execute(sql, params)
                result = cursor.fetchone()
                
                conn.close()
                
                stats = {
                    "total": result["total"] or 0,
                    "pending": result["pending"] or 0,
                    "approved": result["approved"] or 0,
                    "rejected": result["rejected"] or 0,
                    "published": result["published"] or 0
                }
                
                logger.info(f"Stats computed (optimized): {stats}")
                return stats
                
            except Exception as pg_error:
                logger.warning(f"Direct PostgreSQL stats query failed, falling back to Supabase: {pg_error}")
                # Fallback to original Supabase approach if direct connection fails
                return await self._get_news_items_stats_fallback(pipeline_id, tenant_id)

        except Exception as e:
            logger.exception(f"Failed to get news items stats: {e}")
            return {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "published": 0}
    
    async def _get_news_items_stats_fallback(
        self,
        pipeline_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Fallback method for stats using multiple Supabase queries
        (used if direct PostgreSQL connection fails)
        """
        try:
            stats = {
                "total": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0,
                "published": 0
            }

            # Build base query
            def build_query(base_query):
                if pipeline_id:
                    base_query = base_query.eq("pipeline_id", pipeline_id)
                if tenant_id:
                    base_query = base_query.eq("tenant_id", tenant_id)
                return base_query

            # Get total count
            total_query = build_query(self.db.service_client.table("external_news_items").select("id", count="exact"))
            total_response = total_query.execute()
            stats["total"] = total_response.count if hasattr(total_response, 'count') else 0

            # Get approved count
            approved_query = build_query(
                self.db.service_client.table("external_news_items").select("id", count="exact").eq("is_approved", True)
            )
            approved_response = approved_query.execute()
            stats["approved"] = approved_response.count if hasattr(approved_response, 'count') else 0

            # Get rejected count
            rejected_query = build_query(
                self.db.service_client.table("external_news_items").select("id", count="exact")
                .or_("moderation_status.eq.rejected,status.eq.rejected")
            )
            rejected_response = rejected_query.execute()
            stats["rejected"] = rejected_response.count if hasattr(rejected_response, 'count') else 0

            # Get pending count
            pending_query = build_query(
                self.db.service_client.table("external_news_items").select("id", count="exact")
                .eq("is_approved", False)
                .neq("moderation_status", "rejected")
                .neq("status", "rejected")
            )
            pending_response = pending_query.execute()
            stats["pending"] = pending_response.count if hasattr(pending_response, 'count') else 0

            # Get published count
            published_query = build_query(
                self.db.service_client.table("external_news_items").select("published_channels", count="exact")
                .not_.is_("published_channels", "null")
            )
            published_response = published_query.execute()
            if published_response.data:
                stats["published"] = sum(
                    1 for item in published_response.data 
                    if item.get("published_channels") and len(item.get("published_channels", [])) > 0
                )
            else:
                stats["published"] = 0

            logger.info(f"Stats computed (fallback): {stats}")
            return stats

        except Exception as e:
            logger.exception(f"Failed to get news items stats (fallback): {e}")
            return {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "published": 0}
    
    async def bulk_update_moderation_status(
        self,
        news_item_ids: List[str],
        moderation_status: str,
        is_approved: Optional[bool] = None
    ) -> List[str]:
        """
        Bulk update moderation status for multiple news items
        
        Optimized to use PostgreSQL's IN clause for batch updates instead of
        individual UPDATE queries, reducing database round-trips significantly.
        """
        try:
            if not news_item_ids:
                return []
            
            updates = {
                "moderation_status": moderation_status,
                "moderated_at": datetime.now(timezone.utc).isoformat()
            }
            
            if is_approved is not None:
                updates["is_approved"] = is_approved
            
            # Use Supabase's in_ filter for batch update (single query instead of N queries)
            # This executes: UPDATE news_items SET ... WHERE id IN (...)
            response = self.db.service_client.table("external_news_items")\
                .update(updates)\
                .in_("id", news_item_ids)\
                .execute()
            
            # Extract updated IDs from response
            updated_ids = [item["id"] for item in response.data] if response.data else []
            
            logger.info(f"Bulk updated {len(updated_ids)}/{len(news_item_ids)} news items")
            return updated_ids
            
        except Exception as e:
            logger.exception(f"Failed to bulk update moderation status: {e}")
            # Fallback to individual updates if batch update fails
            logger.info("Falling back to individual updates...")
            updated_ids = []
            for news_id in news_item_ids:
                try:
                    response = self.db.service_client.table("external_news_items")\
                        .update(updates)\
                        .eq("id", news_id)\
                        .execute()
                    
                    if response.data:
                        updated_ids.append(news_id)
                        
                except Exception as e:
                    logger.exception(f"Failed to update news item {news_id}: {e}")
                    continue
            
            logger.info(f"Bulk updated (fallback) {len(updated_ids)}/{len(news_item_ids)} news items")
            return updated_ids


# Convenience function to get database instance
def get_database():
    from core.database import db
    return db