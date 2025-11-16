"""
Migration service for upgrading existing data to multi-perspective analysis
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from bson import ObjectId
import logging

from app.core.database import get_database
from app.services.cluster_service import ClusterService
from app.services.intelligence_service import IntelligenceService
from app.models.common import ClusterMatch

logger = logging.getLogger(__name__)


class MigrationService:
    """Service for migrating existing data to new multi-perspective format"""
    
    def __init__(self):
        self._db = None
        self.cluster_service = ClusterService()
        self.intelligence_service = IntelligenceService()
        
        # Migration configuration
        self.config = {
            "batch_size": 100,
            "delay_between_batches": 5,  # seconds
            "max_daily_documents": 1000,  # API cost control
            "skip_recent_hours": 24,  # Skip documents from last N hours
        }
    
    @property
    def database(self):
        if self._db is None:
            self._db = get_database()
        return self._db
    
    async def get_migration_stats(self) -> Dict[str, int]:
        """Get migration statistics"""
        try:
            # Count documents by migration status
            news_collection = self.database.news_articles
            posts_collection = self.database.social_posts
            
            # News articles stats
            news_total = await news_collection.count_documents({})
            news_migrated = await news_collection.count_documents({"migration_status": "completed"})
            news_pending = await news_collection.count_documents({
                "$or": [
                    {"migration_status": {"$exists": False}},
                    {"migration_status": "pending"}
                ]
            })
            
            # Social posts stats
            posts_total = await posts_collection.count_documents({})
            posts_migrated = await posts_collection.count_documents({"migration_status": "completed"})
            posts_pending = await posts_collection.count_documents({
                "$or": [
                    {"migration_status": {"$exists": False}},
                    {"migration_status": "pending"}
                ]
            })
            
            return {
                "news_articles": {
                    "total": news_total,
                    "migrated": news_migrated,
                    "pending": news_pending
                },
                "social_posts": {
                    "total": posts_total,
                    "migrated": posts_migrated,
                    "pending": posts_pending
                },
                "totals": {
                    "total": news_total + posts_total,
                    "migrated": news_migrated + posts_migrated,
                    "pending": news_pending + posts_pending
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting migration stats: {str(e)}")
            raise
    
    async def mark_existing_data_for_migration(self) -> Dict[str, int]:
        """Mark all existing data that needs migration"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.config["skip_recent_hours"])
            
            # Mark news articles for migration (only those without migration_status)
            news_result = await self.database.news_articles.update_many(
                {
                    "migration_status": {"$exists": False},
                    "collected_at": {"$lt": cutoff_time}
                },
                {
                    "$set": {
                        "migration_status": "pending",
                        "marked_for_migration_at": datetime.utcnow()
                    }
                }
            )
            
            # Mark social posts for migration
            posts_result = await self.database.social_posts.update_many(
                {
                    "migration_status": {"$exists": False},
                    "collected_at": {"$lt": cutoff_time}
                },
                {
                    "$set": {
                        "migration_status": "pending",
                        "marked_for_migration_at": datetime.utcnow()
                    }
                }
            )
            
            return {
                "news_articles_marked": news_result.modified_count,
                "social_posts_marked": posts_result.modified_count,
                "total_marked": news_result.modified_count + posts_result.modified_count
            }
            
        except Exception as e:
            logger.error(f"Error marking data for migration: {str(e)}")
            raise
    
    async def process_migration_batch(
        self, 
        collection_name: str,
        batch_size: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Process a batch of documents for migration"""
        try:
            if batch_size is None:
                batch_size = self.config["batch_size"]
            
            collection = getattr(self.database, collection_name)
            
            # Get all clusters for multi-perspective analysis
            all_clusters = await self.cluster_service.get_clusters()
            all_clusters_dict = [
                {
                    "id": c.id,
                    "name": c.name,
                    "cluster_type": c.cluster_type,
                    "keywords": c.keywords
                }
                for c in all_clusters
            ]
            
            # Find documents that need migration
            query = {"migration_status": "pending"}
            
            # Get batch of documents
            cursor = collection.find(query).limit(batch_size)
            documents = await cursor.to_list(length=batch_size)
            
            if not documents:
                return {
                    "processed": 0,
                    "updated": 0,
                    "errors": 0,
                    "remaining": 0
                }
            
            logger.info(f"Processing batch of {len(documents)} {collection_name} documents")
            
            processed_count = 0
            updated_count = 0
            error_count = 0
            
            for doc in documents:
                try:
                    # Process the document
                    update_fields = await self._reprocess_document(
                        doc, 
                        all_clusters_dict, 
                        collection_name
                    )
                    
                    if not dry_run and update_fields:
                        # Update the document in database
                        await collection.update_one(
                            {"_id": doc["_id"]},
                            {"$set": update_fields}
                        )
                        updated_count += 1
                    
                    processed_count += 1
                    
                    if processed_count % 10 == 0:
                        logger.info(f"Processed {processed_count}/{len(documents)} documents")
                
                except Exception as e:
                    logger.error(f"Error processing document {doc.get('_id', 'unknown')}: {str(e)}")
                    error_count += 1
                    
                    # Mark document as failed
                    if not dry_run:
                        await collection.update_one(
                            {"_id": doc["_id"]},
                            {
                                "$set": {
                                    "migration_status": "failed",
                                    "migration_error": str(e),
                                    "failed_at": datetime.utcnow()
                                }
                            }
                        )
            
            # Count remaining documents
            remaining = await collection.count_documents({"migration_status": "pending"})
            
            return {
                "processed": processed_count,
                "updated": updated_count,
                "errors": error_count,
                "remaining": remaining,
                "dry_run": dry_run
            }
            
        except Exception as e:
            logger.error(f"Error in process_migration_batch: {str(e)}")
            raise
    
    async def _reprocess_document(
        self, 
        doc: Dict[str, Any], 
        all_clusters: List[Dict], 
        collection_name: str
    ) -> Dict[str, Any]:
        """Reprocess a single document with multi-perspective analysis"""
        try:
            # Extract content based on document type
            if collection_name == "news_articles":
                content = f"{doc.get('title', '')} {doc.get('summary', '')} {doc.get('content', '')}"
                content_type = "news"
            else:  # social_posts
                content = doc.get('content', '')
                content_type = "social_post"
            
            content = content.strip()
            if not content:
                logger.warning(f"No content found for document {doc.get('_id')}")
                return {}
            
            # Detect all matching clusters
            matched_clusters = await self.intelligence_service.detect_matched_clusters(
                content, 
                all_clusters
            )
            
            # Determine perspective type
            own_clusters = [c for c in matched_clusters if c.cluster_type == "own"]
            competitor_clusters = [c for c in matched_clusters if c.cluster_type == "competitor"]
            
            if len(own_clusters) > 0 and len(competitor_clusters) > 0:
                perspective_type = "multi-perspective"
            elif len(own_clusters) > 0:
                perspective_type = "own"
            elif len(competitor_clusters) > 0:
                perspective_type = "competitor"
            else:
                perspective_type = "single"
            
            # Perform appropriate intelligence analysis
            if len(matched_clusters) > 1:
                # Multi-perspective analysis
                intelligence = await self.intelligence_service.analyze_multi_perspective_content(
                    content,
                    content_type,
                    matched_clusters
                )
            else:
                # Single perspective - keep existing intelligence if available
                existing_intelligence = doc.get('intelligence', {})
                if existing_intelligence:
                    intelligence = existing_intelligence
                else:
                    # Fallback: analyze with current method
                    if content_type == "news":
                        intelligence = await self.intelligence_service.analyze_news_content(content)
                    else:
                        # For social posts, we need engagement metrics
                        engagement_metrics = doc.get('engagement_metrics', {})
                        intelligence = await self.intelligence_service.analyze_post(content, engagement_metrics)
            
            # Prepare update fields
            update_fields = {
                "migration_status": "completed",
                "migrated_at": datetime.utcnow(),
                "perspective_type": perspective_type,
                "intelligence": intelligence
            }
            
            # Add matched_clusters if any found
            if matched_clusters:
                update_fields["matched_clusters"] = [
                    {
                        "cluster_id": mc.cluster_id,
                        "cluster_name": mc.cluster_name,
                        "cluster_type": mc.cluster_type,
                        "keywords_matched": mc.keywords_matched
                    }
                    for mc in matched_clusters
                ]
            else:
                update_fields["matched_clusters"] = []
            
            logger.info(f"Successfully processed document {doc.get('_id')} - {perspective_type} perspective")
            return update_fields
            
        except Exception as e:
            logger.error(f"Error reprocessing document {doc.get('_id', 'unknown')}: {str(e)}")
            raise
    
    async def run_full_migration(
        self, 
        collection_name: str,
        max_batches: Optional[int] = None
    ) -> Dict[str, Any]:
        """Run full migration for a collection"""
        try:
            logger.info(f"Starting full migration for {collection_name}")
            
            total_stats = {
                "total_processed": 0,
                "total_updated": 0,
                "total_errors": 0,
                "batches_processed": 0
            }
            
            batch_count = 0
            while True:
                # Check if we've hit the batch limit
                if max_batches and batch_count >= max_batches:
                    logger.info(f"Reached maximum batch limit: {max_batches}")
                    break
                
                # Process a batch
                batch_result = await self.process_migration_batch(collection_name)
                
                # Update totals
                total_stats["total_processed"] += batch_result["processed"]
                total_stats["total_updated"] += batch_result["updated"]
                total_stats["total_errors"] += batch_result["errors"]
                total_stats["batches_processed"] += 1
                batch_count += 1
                
                logger.info(
                    f"Batch {batch_count} completed: "
                    f"processed={batch_result['processed']}, "
                    f"updated={batch_result['updated']}, "
                    f"errors={batch_result['errors']}, "
                    f"remaining={batch_result['remaining']}"
                )
                
                # Check if we're done
                if batch_result["remaining"] == 0:
                    logger.info(f"Migration completed for {collection_name}")
                    break
                
                # Wait between batches to avoid overwhelming the system
                await asyncio.sleep(self.config["delay_between_batches"])
            
            return total_stats
            
        except Exception as e:
            logger.error(f"Error in run_full_migration: {str(e)}")
            raise