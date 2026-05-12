"""
Service for posts_table database operations - Supabase/PostgreSQL
"""
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models.posts_table import (
    PostCreate, PostUpdate, PostResponse,
    PostsQueryParams, PostsAggregateResponse, SentimentLabel,
)
from app.core.database import get_database

logger = logging.getLogger(__name__)


def _row_to_response(row) -> PostResponse:
    d = dict(row)
    d["id"] = str(d["id"])
    for field in ("llm_analysis", "entity_sentiments", "comparative_analysis"):
        val = d.get(field)
        if isinstance(val, str):
            try:
                d[field] = json.loads(val)
            except Exception:
                d[field] = {}
    if d.get("key_narratives") is None:
        d["key_narratives"] = []
    d.setdefault("created_at", datetime.utcnow())
    d.setdefault("updated_at", datetime.utcnow())
    resp = PostResponse(**d)
    resp.engagement_rate = resp.calculate_engagement_rate()
    return resp


class PostsTableService:
    def __init__(self):
        pass

    async def initialize(self):
        pass  # Pool is managed by database.py

    async def create_post(self, post: PostCreate) -> PostResponse:
        pool = get_database()
        d = post.dict()
        now = datetime.utcnow()

        platform_val = d["platform"].value if hasattr(d["platform"], "value") else d["platform"]
        sentiment_val = d["sentiment_label"].value if hasattr(d["sentiment_label"], "value") else d["sentiment_label"]

        async with pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    """
                    INSERT INTO posts_table (
                        platform_post_id, platform, cluster_id,
                        author_username, author_followers,
                        post_text, post_url, posted_at,
                        likes, comments, shares, views,
                        sentiment_score, sentiment_label,
                        is_threat, threat_level, threat_score,
                        key_narratives, language, has_been_responded_to,
                        llm_analysis, entity_sentiments, comparative_analysis,
                        fetched_at, created_at, updated_at
                    ) VALUES (
                        $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,
                        $13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25,$26
                    )
                    ON CONFLICT (platform, platform_post_id) DO NOTHING
                    RETURNING *
                    """,
                    d["platform_post_id"],
                    platform_val,
                    str(d["cluster_id"]),
                    d.get("author_username", "Unknown"),
                    d.get("author_followers", 0),
                    d["post_text"],
                    d["post_url"],
                    d["posted_at"],
                    d.get("likes", 0),
                    d.get("comments", 0),
                    d.get("shares", 0),
                    d.get("views", 0),
                    d.get("sentiment_score", 0.0),
                    sentiment_val,
                    d.get("is_threat", False),
                    d.get("threat_level", "None"),
                    d.get("threat_score", 0.0),
                    d.get("key_narratives", []),
                    d.get("language", "English"),
                    d.get("has_been_responded_to", False),
                    json.dumps(d.get("llm_analysis") or {}, default=str),
                    json.dumps(d.get("entity_sentiments") or {}, default=str),
                    json.dumps(d.get("comparative_analysis") or {}, default=str),
                    d.get("fetched_at", now),
                    now,
                    now,
                )
                if row:
                    return _row_to_response(row)
                # Conflict: return existing
                existing = await conn.fetchrow(
                    "SELECT * FROM posts_table WHERE platform=$1 AND platform_post_id=$2",
                    platform_val, d["platform_post_id"]
                )
                return _row_to_response(existing)
            except Exception as e:
                logger.error(f"Error creating post: {e}")
                raise

    async def update_post(self, post_id: str, update: PostUpdate) -> Optional[PostResponse]:
        pool = get_database()
        update_dict = {k: v for k, v in update.dict().items() if v is not None}
        if not update_dict:
            return None
        update_dict["updated_at"] = datetime.utcnow()

        sets, args = [], []
        for key, val in update_dict.items():
            if isinstance(val, (dict, list)):
                val = json.dumps(val, default=str)
            elif hasattr(val, "value"):
                val = val.value
            args.append(val)
            sets.append(f"{key} = ${len(args)}")
        args.append(post_id)
        query = f"UPDATE posts_table SET {', '.join(sets)} WHERE id = ${len(args)}::uuid RETURNING *"

        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
        return _row_to_response(row) if row else None

    async def get_post(self, post_id: str) -> Optional[PostResponse]:
        pool = get_database()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM posts_table WHERE id = $1::uuid", post_id
            )
        return _row_to_response(row) if row else None

    async def query_posts(self, params: PostsQueryParams) -> List[PostResponse]:
        pool = get_database()
        conditions, args = [], []

        if params.cluster_id:
            args.append(str(params.cluster_id))
            conditions.append(f"cluster_id = ${len(args)}")
        if params.platform:
            args.append(params.platform.value if hasattr(params.platform, "value") else params.platform)
            conditions.append(f"platform = ${len(args)}")
        if params.sentiment_label:
            args.append(params.sentiment_label.value if hasattr(params.sentiment_label, "value") else params.sentiment_label)
            conditions.append(f"sentiment_label = ${len(args)}")
        if params.is_threat is not None:
            args.append(params.is_threat)
            conditions.append(f"is_threat = ${len(args)}")
        if params.language:
            args.append(params.language)
            conditions.append(f"language = ${len(args)}")
        if params.posted_after:
            args.append(params.posted_after)
            conditions.append(f"posted_at >= ${len(args)}")
        if params.posted_before:
            args.append(params.posted_before)
            conditions.append(f"posted_at <= ${len(args)}")
        if params.min_engagement:
            args.append(params.min_engagement)
            conditions.append(f"(likes + comments + shares) >= ${len(args)}")

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        args += [params.limit, params.skip]
        query = f"""
            SELECT * FROM posts_table {where}
            ORDER BY posted_at DESC
            LIMIT ${len(args)-1} OFFSET ${len(args)}
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args)

        posts = []
        for row in rows:
            try:
                posts.append(_row_to_response(row))
            except Exception as e:
                logger.warning(f"Skipping invalid post row: {e}")
        return posts

    async def get_aggregate_stats(self, cluster_id: Optional[str] = None) -> PostsAggregateResponse:
        pool = get_database()
        where = f"WHERE cluster_id = $1" if cluster_id else ""
        args = [cluster_id] if cluster_id else []

        async with pool.acquire() as conn:
            total = await conn.fetchval(f"SELECT COUNT(*) FROM posts_table {where}", *args)
            by_platform = await conn.fetch(
                f"SELECT platform, COUNT(*) as cnt FROM posts_table {where} GROUP BY platform", *args
            )
            by_sentiment = await conn.fetch(
                f"SELECT sentiment_label, COUNT(*) as cnt FROM posts_table {where} GROUP BY sentiment_label", *args
            )
            threats = await conn.fetchval(
                f"SELECT COUNT(*) FROM posts_table {where + ' AND' if where else 'WHERE'} is_threat = true",
                *args
            )
            engagement = await conn.fetchrow(
                f"""SELECT SUM(likes) as tl, SUM(comments) as tc,
                           SUM(shares) as ts, SUM(views) as tv,
                           AVG(sentiment_score) as avg_s
                    FROM posts_table {where}""",
                *args
            )

        return PostsAggregateResponse(
            total_posts=total or 0,
            posts_by_platform={r["platform"]: r["cnt"] for r in by_platform},
            posts_by_sentiment={r["sentiment_label"]: r["cnt"] for r in by_sentiment},
            threat_posts=threats or 0,
            languages=[],
            total_engagement={
                "likes": int(engagement["tl"] or 0),
                "comments": int(engagement["tc"] or 0),
                "shares": int(engagement["ts"] or 0),
                "views": int(engagement["tv"] or 0),
            },
            average_sentiment_score=float(engagement["avg_s"] or 0.0),
            most_common_narratives=[],
        )

    async def delete_post(self, post_id: str) -> bool:
        pool = get_database()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM posts_table WHERE id = $1::uuid", post_id
            )
        return result == "DELETE 1"

    async def bulk_create_posts(self, posts: List[PostCreate]) -> List[PostResponse]:
        created = []
        for post in posts:
            try:
                created.append(await self.create_post(post))
            except Exception as e:
                logger.error(f"Error bulk creating post: {e}")
        return created

    async def mark_as_responded(self, post_id: str) -> bool:
        pool = get_database()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE posts_table SET has_been_responded_to=true, updated_at=now() WHERE id=$1::uuid",
                post_id,
            )
        return result == "UPDATE 1"

    async def get_posts_by_cluster_and_dashboard(
        self, cluster_id: str, dashboard_type: str, limit: int = 100
    ) -> List[PostResponse]:
        return await self.query_posts(PostsQueryParams(cluster_id=cluster_id, limit=limit))
