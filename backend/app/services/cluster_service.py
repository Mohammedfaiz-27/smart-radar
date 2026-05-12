"""
Business logic for cluster management - Supabase/PostgreSQL
"""
import json
import logging
from typing import List, Optional
from datetime import datetime

from app.core.database import get_database
from app.models.cluster import ClusterCreate, ClusterUpdate, ClusterResponse

logger = logging.getLogger(__name__)


def _row_to_response(row) -> ClusterResponse:
    d = dict(row)
    d["id"] = str(d["id"])
    for field in ("thresholds", "platform_config"):
        if isinstance(d.get(field), str):
            d[field] = json.loads(d[field])
    if isinstance(d.get("keywords"), str):
        d["keywords"] = json.loads(d["keywords"])
    return ClusterResponse(**d)


class ClusterService:
    def __init__(self):
        pass

    async def create_cluster(self, cluster_data: ClusterCreate) -> ClusterResponse:
        pool = get_database()
        d = cluster_data.dict()
        now = datetime.utcnow()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO clusters
                    (name, cluster_type, dashboard_type, keywords, thresholds,
                     platform_config, fetch_frequency_minutes, is_active,
                     created_at, updated_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                RETURNING *
                """,
                d["name"],
                d["cluster_type"],
                d.get("dashboard_type", "Own") if not hasattr(d.get("dashboard_type"), "value") else d["dashboard_type"].value,
                d.get("keywords", []),
                json.dumps(d.get("thresholds", {}), default=str),
                json.dumps(d.get("platform_config", {}), default=str),
                d.get("fetch_frequency_minutes", 30),
                d.get("is_active", True),
                now,
                now,
            )
        return _row_to_response(row)

    async def get_cluster(self, cluster_id: str) -> Optional[ClusterResponse]:
        pool = get_database()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM clusters WHERE id = $1::uuid", cluster_id
            )
        return _row_to_response(row) if row else None

    async def get_clusters(
        self,
        cluster_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ClusterResponse]:
        pool = get_database()
        conditions = []
        args = []
        if cluster_type:
            args.append(cluster_type)
            conditions.append(f"cluster_type = ${len(args)}")
        if is_active is not None:
            args.append(is_active)
            conditions.append(f"is_active = ${len(args)}")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        args += [limit, skip]
        query = f"SELECT * FROM clusters {where} ORDER BY created_at DESC LIMIT ${len(args)-1} OFFSET ${len(args)}"
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
        return [_row_to_response(r) for r in rows]

    async def update_cluster(self, cluster_id: str, cluster_data: ClusterUpdate) -> Optional[ClusterResponse]:
        update = {k: v for k, v in cluster_data.dict().items() if v is not None}
        if not update:
            return await self.get_cluster(cluster_id)
        update["updated_at"] = datetime.utcnow()

        sets = []
        args = []
        for key, val in update.items():
            args.append(json.dumps(val, default=str) if isinstance(val, dict) else val)
            sets.append(f"{key} = ${len(args)}")
        args.append(cluster_id)
        query = f"UPDATE clusters SET {', '.join(sets)} WHERE id = ${len(args)}::uuid RETURNING *"
        pool = get_database()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
        return _row_to_response(row) if row else None

    async def delete_cluster(self, cluster_id: str) -> bool:
        pool = get_database()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM clusters WHERE id = $1::uuid", cluster_id
            )
        return result == "DELETE 1"
