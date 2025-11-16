"""
Business logic for cluster management
"""
from typing import List, Optional
from bson import ObjectId
from datetime import datetime

from app.core.database import get_database
from app.models.cluster import ClusterCreate, ClusterUpdate, ClusterInDB, ClusterResponse

class ClusterService:
    def __init__(self):
        pass

    async def create_cluster(self, cluster_data: ClusterCreate) -> ClusterResponse:
        """Create a new cluster"""
        db = get_database()
        if db is None:
            raise RuntimeError("Database connection is not available")
        collection = db.clusters
        
        cluster_dict = cluster_data.dict()
        cluster_dict["created_at"] = datetime.utcnow()
        cluster_dict["updated_at"] = datetime.utcnow()
        
        result = await collection.insert_one(cluster_dict)
        created_cluster = await collection.find_one({"_id": result.inserted_id})
        
        return self._format_cluster_response(created_cluster)

    async def get_cluster(self, cluster_id: str) -> Optional[ClusterResponse]:
        """Get cluster by ID"""
        if not ObjectId.is_valid(cluster_id):
            return None

        db = get_database()
        if db is None:
            raise RuntimeError("Database connection is not available")
        collection = db.clusters
        cluster = await collection.find_one({"_id": ObjectId(cluster_id)})
        if cluster:
            return self._format_cluster_response(cluster)
        return None

    async def get_clusters(self,
                          cluster_type: Optional[str] = None,
                          is_active: Optional[bool] = None,
                          skip: int = 0,
                          limit: int = 100) -> List[ClusterResponse]:
        """Get all clusters with optional filters"""
        query = {}
        if cluster_type:
            query["cluster_type"] = cluster_type
        if is_active is not None:
            query["is_active"] = is_active

        db = get_database()
        if db is None:
            raise RuntimeError("Database connection is not available")

        collection = db.clusters
        cursor = collection.find(query).skip(skip).limit(limit)
        clusters = await cursor.to_list(length=limit)

        return [self._format_cluster_response(cluster) for cluster in clusters]

    async def update_cluster(self, cluster_id: str, cluster_data: ClusterUpdate) -> Optional[ClusterResponse]:
        """Update cluster by ID"""
        if not ObjectId.is_valid(cluster_id):
            return None

        update_data = {k: v for k, v in cluster_data.dict().items() if v is not None}
        if not update_data:
            return None

        update_data["updated_at"] = datetime.utcnow()

        db = get_database()
        if db is None:
            raise RuntimeError("Database connection is not available")
        collection = db.clusters
        result = await collection.update_one(
            {"_id": ObjectId(cluster_id)},
            {"$set": update_data}
        )
        
        if result.matched_count:
            updated_cluster = await collection.find_one({"_id": ObjectId(cluster_id)})
            return self._format_cluster_response(updated_cluster)
        return None

    async def delete_cluster(self, cluster_id: str) -> bool:
        """Delete cluster by ID"""
        if not ObjectId.is_valid(cluster_id):
            return False

        db = get_database()
        if db is None:
            raise RuntimeError("Database connection is not available")
        collection = db.clusters
        result = await collection.delete_one({"_id": ObjectId(cluster_id)})
        return result.deleted_count > 0

    def _format_cluster_response(self, cluster_data: dict) -> ClusterResponse:
        """Format cluster data for response"""
        cluster_data["id"] = str(cluster_data["_id"])
        del cluster_data["_id"]
        
        # Handle missing timestamps for existing data
        current_time = datetime.utcnow()
        if "created_at" not in cluster_data:
            cluster_data["created_at"] = current_time
        if "updated_at" not in cluster_data:
            cluster_data["updated_at"] = current_time
            
        return ClusterResponse(**cluster_data)