"""
Search API - keyword/sentence search across posts and news articles
"""
from fastapi import APIRouter, Query
from typing import Optional
from app.core.database import get_database

router = APIRouter()


@router.get("")
async def search(
    q: str = Query(..., min_length=1, description="Search keyword or sentence"),
    type: Optional[str] = Query(None, description="all | posts | news"),
    sentiment: Optional[str] = Query(None, description="Positive | Negative | Neutral"),
    limit: int = Query(50, ge=1, le=200),
):
    """Search across social posts and news by keyword or sentence"""
    results = {"query": q, "total": 0, "posts": [], "news": []}
    search_type = (type or "all").lower()

    pool = get_database()

    # ── Social posts ──────────────────────────────────────────────────
    if search_type in ("all", "posts"):
        try:
            async with pool.acquire() as conn:
                sql = """
                    SELECT
                        pt.id, pt.post_text, pt.author_username, pt.platform,
                        pt.sentiment_label, pt.posted_at, pt.post_url,
                        pt.likes, pt.shares, pt.comments, pt.views,
                        pt.is_threat, pt.cluster_id,
                        c.name  AS cluster_name,
                        c.cluster_type
                    FROM posts_table pt
                    LEFT JOIN clusters c ON c.id = pt.cluster_id
                    WHERE (pt.post_text ILIKE $1 OR pt.author_username ILIKE $1)
                """
                params = [f"%{q}%"]
                if sentiment:
                    sql += f" AND pt.sentiment_label = ${len(params)+1}"
                    params.append(sentiment)
                sql += " ORDER BY pt.posted_at DESC LIMIT $" + str(len(params)+1)
                params.append(limit)

                rows = await conn.fetch(sql, *params)
                for row in rows:
                    results["posts"].append({
                        "id": str(row["id"]),
                        "type": "post",
                        "platform": row["platform"],
                        "content": row["post_text"],
                        "author": row["author_username"] or "Unknown",
                        "sentiment": (row["sentiment_label"] or "Neutral").lower(),
                        "is_threat": row["is_threat"],
                        "url": row["post_url"],
                        "published_at": row["posted_at"].isoformat() if row["posted_at"] else None,
                        "cluster_name": row["cluster_name"],
                        "cluster_type": row["cluster_type"],
                        "engagement": {
                            "likes": row["likes"] or 0,
                            "shares": row["shares"] or 0,
                            "comments": row["comments"] or 0,
                            "views": row["views"] or 0,
                        },
                    })
        except Exception as e:
            results["posts_error"] = str(e)

    # ── News (from smart_posts table if it has news-type entries) ─────
    if search_type in ("all", "news"):
        try:
            async with pool.acquire() as conn:
                sql = """
                    SELECT
                        pt.id, pt.post_text, pt.author_username, pt.platform,
                        pt.sentiment_label, pt.posted_at, pt.post_url,
                        pt.likes, pt.shares, pt.comments, pt.views,
                        pt.is_threat, c.name AS cluster_name, c.cluster_type
                    FROM posts_table pt
                    LEFT JOIN clusters c ON c.id = pt.cluster_id
                    WHERE pt.platform NOT IN ('X', 'Facebook', 'YouTube')
                      AND (pt.post_text ILIKE $1 OR pt.author_username ILIKE $1)
                """
                params = [f"%{q}%"]
                if sentiment:
                    sql += f" AND pt.sentiment_label = ${len(params)+1}"
                    params.append(sentiment)
                sql += " ORDER BY pt.posted_at DESC LIMIT $" + str(len(params)+1)
                params.append(limit)

                rows = await conn.fetch(sql, *params)
                for row in rows:
                    results["news"].append({
                        "id": str(row["id"]),
                        "type": "news",
                        "platform": row["platform"],
                        "title": row["post_text"][:100] if row["post_text"] else "",
                        "content": row["post_text"],
                        "source": row["author_username"] or "Unknown",
                        "url": row["post_url"],
                        "published_at": row["posted_at"].isoformat() if row["posted_at"] else None,
                        "sentiment": (row["sentiment_label"] or "Neutral").lower(),
                        "is_threat": row["is_threat"],
                        "cluster_name": row["cluster_name"],
                        "cluster_type": row["cluster_type"],
                    })
        except Exception as e:
            results["news_error"] = str(e)

    results["total"] = len(results["posts"]) + len(results["news"])
    return results
