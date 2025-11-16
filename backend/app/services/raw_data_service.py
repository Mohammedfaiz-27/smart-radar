"""
Service for managing raw_data database operations
Handles storage and retrieval of unprocessed API responses
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.models.raw_data import (
    RawDataCreate, RawDataUpdate, RawDataInDB,
    RawDataResponse, RawDataQueryParams, RawDataStats,
    ProcessingStatus, RawDataPlatform
)
from app.core.database import get_database

class RawDataService:
    """Service for raw_data operations"""
    
    def __init__(self):
        """Initialize raw data service"""
        self._db = None
        self._collection = None
    
    async def initialize(self):
        """Initialize database connection"""
        if self._db is None:
            self._db = get_database()  # Don't await, it returns the database directly
            self._collection = self._db.raw_data
            
            # Create indexes
            await self._create_indexes()
    
    async def _create_indexes(self):
        """Create database indexes for performance"""
        try:
            # Index for querying by status
            await self._collection.create_index("processing_status")
            # Index for platform
            await self._collection.create_index("platform")
            # Index for cluster
            await self._collection.create_index("cluster_id")
            # Index for fetched date
            await self._collection.create_index("fetched_at")
            # Compound index for common queries
            await self._collection.create_index([
                ("processing_status", 1),
                ("fetched_at", 1)
            ])
        except Exception as e:
            print(f"Error creating indexes: {e}")
    
    async def create_entry(self, raw_data: RawDataCreate) -> RawDataResponse:
        """
        Create a new raw data entry
        
        Args:
            raw_data: RawDataCreate model
            
        Returns:
            Created entry with ID
        """
        await self.initialize()
        
        # Convert to dict and add timestamps
        data_dict = raw_data.dict()
        data_dict["created_at"] = datetime.utcnow()
        data_dict["updated_at"] = datetime.utcnow()
        
        # Insert into database
        result = await self._collection.insert_one(data_dict)
        
        # Retrieve created entry
        created = await self._collection.find_one({"_id": result.inserted_id})
        created["id"] = str(created.pop("_id"))
        
        return RawDataResponse(**created)
    
    async def bulk_create(self, entries: List[RawDataCreate]) -> List[RawDataResponse]:
        """
        Create multiple raw data entries
        
        Args:
            entries: List of RawDataCreate models
            
        Returns:
            List of created entries
        """
        if not entries:
            return []
        
        await self.initialize()
        
        # Prepare documents
        documents = []
        for entry in entries:
            doc = entry.dict()
            doc["created_at"] = datetime.utcnow()
            doc["updated_at"] = datetime.utcnow()
            documents.append(doc)
        
        # Bulk insert
        result = await self._collection.insert_many(documents)
        
        # Retrieve created entries
        created_entries = []
        for inserted_id in result.inserted_ids:
            entry = await self._collection.find_one({"_id": inserted_id})
            if entry:
                entry["id"] = str(entry.pop("_id"))
                created_entries.append(RawDataResponse(**entry))
        
        return created_entries
    
    async def update_entry(
        self,
        entry_id: str,
        update: RawDataUpdate
    ) -> Optional[RawDataResponse]:
        """
        Update a raw data entry
        
        Args:
            entry_id: Entry ID
            update: Fields to update
            
        Returns:
            Updated entry or None
        """
        await self.initialize()
        
        # Filter out None values
        update_dict = {k: v for k, v in update.dict().items() if v is not None}
        
        if not update_dict:
            return None
        
        # Add updated timestamp
        update_dict["updated_at"] = datetime.utcnow()
        
        # Update in database
        result = await self._collection.update_one(
            {"_id": ObjectId(entry_id)},
            {"$set": update_dict}
        )
        
        if result.modified_count == 0:
            return None
        
        # Retrieve updated entry
        updated = await self._collection.find_one({"_id": ObjectId(entry_id)})
        if updated:
            updated["id"] = str(updated.pop("_id"))
            return RawDataResponse(**updated)
        
        return None
    
    async def get_entry(self, entry_id: str) -> Optional[RawDataResponse]:
        """
        Get a single entry by ID
        
        Args:
            entry_id: Entry ID
            
        Returns:
            Entry or None
        """
        await self.initialize()
        
        entry = await self._collection.find_one({"_id": ObjectId(entry_id)})
        if entry:
            entry["id"] = str(entry.pop("_id"))
            return RawDataResponse(**entry)
        return None
    
    async def query_entries(self, params: RawDataQueryParams) -> List[RawDataResponse]:
        """
        Query raw data entries with filters
        
        Args:
            params: Query parameters
            
        Returns:
            List of matching entries
        """
        await self.initialize()
        
        # Build query
        query = {}
        
        if params.platform:
            query["platform"] = params.platform
        
        if params.cluster_id:
            query["cluster_id"] = params.cluster_id
        
        if params.processing_status:
            query["processing_status"] = params.processing_status
        
        if params.fetched_after or params.fetched_before:
            date_filter = {}
            if params.fetched_after:
                date_filter["$gte"] = params.fetched_after
            if params.fetched_before:
                date_filter["$lte"] = params.fetched_before
            query["fetched_at"] = date_filter
        
        if params.has_error is not None:
            if params.has_error:
                query["processing_error"] = {"$ne": None}
            else:
                query["processing_error"] = None
        
        # Execute query
        cursor = self._collection.find(query).sort("fetched_at", -1)
        
        # Apply pagination
        cursor = cursor.skip(params.skip).limit(params.limit)
        
        # Convert to response models
        entries = []
        async for entry in cursor:
            entry["id"] = str(entry.pop("_id"))
            entries.append(RawDataResponse(**entry))
        
        return entries
    
    async def get_pending_entries(self, limit: int = 100) -> List[RawDataResponse]:
        """
        Get pending entries for processing
        
        Args:
            limit: Maximum number of entries
            
        Returns:
            List of pending entries
        """
        params = RawDataQueryParams(
            processing_status=ProcessingStatus.PENDING,
            limit=limit
        )
        return await self.query_entries(params)
    
    async def mark_as_processed(
        self,
        entry_id: str,
        posts_extracted: int = 0,
        error: Optional[str] = None
    ) -> Optional[RawDataResponse]:
        """
        Mark an entry as processed
        
        Args:
            entry_id: Entry ID
            posts_extracted: Number of posts extracted
            error: Error message if processing failed
            
        Returns:
            Updated entry
        """
        status = ProcessingStatus.FAILED if error else ProcessingStatus.COMPLETED
        
        update = RawDataUpdate(
            processing_status=status,
            processed_at=datetime.utcnow(),
            processing_error=error,
            posts_extracted=posts_extracted
        )
        
        return await self.update_entry(entry_id, update)
    
    async def get_statistics(self) -> RawDataStats:
        """
        Get statistics for raw data collection
        
        Returns:
            Statistics object
        """
        await self.initialize()
        
        # Aggregation pipeline
        pipeline = [
            {
                "$facet": {
                    "total": [{"$count": "count"}],
                    "by_platform": [
                        {"$group": {"_id": "$platform", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}}
                    ],
                    "by_status": [
                        {"$group": {"_id": "$processing_status", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}}
                    ],
                    "posts_extracted": [
                        {"$group": {"_id": None, "total": {"$sum": "$posts_extracted"}}}
                    ],
                    "failed": [
                        {"$match": {"processing_status": ProcessingStatus.FAILED}},
                        {"$count": "count"}
                    ],
                    "pending": [
                        {"$match": {"processing_status": ProcessingStatus.PENDING}},
                        {"$count": "count"}
                    ],
                    "oldest_pending": [
                        {"$match": {"processing_status": ProcessingStatus.PENDING}},
                        {"$sort": {"fetched_at": 1}},
                        {"$limit": 1},
                        {"$project": {"fetched_at": 1}}
                    ],
                    "total_size": [
                        {"$group": {"_id": None, "size": {"$sum": "$response_size_bytes"}}}
                    ]
                }
            }
        ]
        
        # Execute aggregation
        result = await self._collection.aggregate(pipeline).to_list(1)
        
        if not result:
            return RawDataStats(
                total_records=0,
                records_by_platform={},
                records_by_status={},
                total_posts_extracted=0,
                failed_processing_count=0,
                pending_processing_count=0,
                oldest_unprocessed=None,
                total_size_mb=0.0
            )
        
        facets = result[0]
        
        # Process results
        total_records = facets["total"][0]["count"] if facets["total"] else 0
        
        records_by_platform = {
            item["_id"]: item["count"]
            for item in facets["by_platform"]
        }
        
        records_by_status = {
            item["_id"]: item["count"]
            for item in facets["by_status"]
        }
        
        total_posts = facets["posts_extracted"][0]["total"] if facets["posts_extracted"] else 0
        failed_count = facets["failed"][0]["count"] if facets["failed"] else 0
        pending_count = facets["pending"][0]["count"] if facets["pending"] else 0
        
        oldest_pending = None
        if facets["oldest_pending"]:
            oldest_pending = facets["oldest_pending"][0]["fetched_at"]
        
        total_size_bytes = facets["total_size"][0]["size"] if facets["total_size"] else 0
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        return RawDataStats(
            total_records=total_records,
            records_by_platform=records_by_platform,
            records_by_status=records_by_status,
            total_posts_extracted=total_posts,
            failed_processing_count=failed_count,
            pending_processing_count=pending_count,
            oldest_unprocessed=oldest_pending,
            total_size_mb=round(total_size_mb, 2)
        )
    
    async def cleanup_old_data(self, days: int = 30) -> int:
        """
        Delete old processed data
        
        Args:
            days: Delete data older than this many days
            
        Returns:
            Number of entries deleted
        """
        await self.initialize()
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = await self._collection.delete_many({
            "processing_status": ProcessingStatus.COMPLETED,
            "fetched_at": {"$lt": cutoff_date}
        })
        
        return result.deleted_count