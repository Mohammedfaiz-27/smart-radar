"""
Narratives API — CRUD for Narrative Bank
Stored in Supabase PostgreSQL via asyncpg.
Table is created automatically on first request.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
import asyncio
import logging
import os
from datetime import datetime, timezone

from app.core.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter()

_table_ready = False


# ── Table bootstrap ───────────────────────────────────────────────────────────

async def _ensure_table():
    global _table_ready
    if _table_ready:
        return
    pool = get_database()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS narratives (
                id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
                title       TEXT NOT NULL,
                description TEXT NOT NULL,
                category    TEXT NOT NULL DEFAULT 'policy',
                priority    TEXT NOT NULL DEFAULT 'medium',
                tags        TEXT[] DEFAULT '{}',
                usage_count INTEGER DEFAULT 0,
                last_used   TIMESTAMPTZ,
                created_by  TEXT,
                is_active   BOOLEAN DEFAULT TRUE,
                created_at  TIMESTAMPTZ DEFAULT NOW(),
                updated_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_narratives_active ON narratives(is_active)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_narratives_category ON narratives(category)"
        )
    _table_ready = True


def _row_to_dict(row) -> dict:
    if row is None:
        return None
    return dict(row)


# ── Pydantic models ───────────────────────────────────────────────────────────

class NarrativeCreate(BaseModel):
    title: str
    description: str
    category: str = "policy"
    priority: str = "medium"
    tags: List[str] = []


class NarrativeGenerateRequest(BaseModel):
    title: str
    category: str = "policy"


class NarrativeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/")
async def list_narratives(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    await _ensure_table()
    try:
        pool = get_database()
        async with pool.acquire() as conn:
            conditions = ["is_active = TRUE"]
            params = []
            idx = 1

            if category:
                conditions.append(f"category = ${idx}")
                params.append(category)
                idx += 1
            if priority:
                conditions.append(f"priority = ${idx}")
                params.append(priority)
                idx += 1
            if search:
                conditions.append(f"(title ILIKE ${idx} OR description ILIKE ${idx})")
                params.append(f"%{search}%")
                idx += 1

            where = " AND ".join(conditions)
            params += [limit, offset]
            rows = await conn.fetch(
                f"SELECT * FROM narratives WHERE {where} ORDER BY usage_count DESC LIMIT ${idx} OFFSET ${idx+1}",
                *params
            )
            items = [_row_to_dict(r) for r in rows]
            return {"narratives": items, "total": len(items)}

    except Exception as e:
        logger.error(f"Error listing narratives: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch narratives")


@router.post("/", status_code=201)
async def create_narrative(payload: NarrativeCreate):
    await _ensure_table()
    try:
        pool = get_database()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO narratives (title, description, category, priority, tags)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                payload.title, payload.description, payload.category,
                payload.priority, payload.tags
            )
            return {"narrative": _row_to_dict(row)}
    except Exception as e:
        logger.error(f"Error creating narrative: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create narrative")


@router.put("/{narrative_id}")
async def update_narrative(narrative_id: str, payload: NarrativeUpdate):
    await _ensure_table()
    try:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates["updated_at"] = datetime.now(timezone.utc)

        set_clause = ", ".join(f"{col} = ${i+2}" for i, col in enumerate(updates))
        values = list(updates.values())

        pool = get_database()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"UPDATE narratives SET {set_clause} WHERE id = $1 AND is_active = TRUE RETURNING *",
                narrative_id, *values
            )
            if not row:
                raise HTTPException(status_code=404, detail="Narrative not found")
            return {"narrative": _row_to_dict(row)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating narrative {narrative_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update narrative")


@router.delete("/{narrative_id}")
async def delete_narrative(narrative_id: str):
    await _ensure_table()
    try:
        pool = get_database()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE narratives SET is_active = FALSE, updated_at = NOW() WHERE id = $1 RETURNING id",
                narrative_id
            )
            if not row:
                raise HTTPException(status_code=404, detail="Narrative not found")
            return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting narrative {narrative_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete narrative")


@router.post("/{narrative_id}/use")
async def use_narrative(narrative_id: str):
    """Increment usage_count and update last_used timestamp."""
    await _ensure_table()
    try:
        pool = get_database()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE narratives
                SET usage_count = usage_count + 1, last_used = NOW(), updated_at = NOW()
                WHERE id = $1 AND is_active = TRUE
                RETURNING *
                """,
                narrative_id
            )
            if not row:
                raise HTTPException(status_code=404, detail="Narrative not found")
            return {"narrative": _row_to_dict(row)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording narrative use {narrative_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to record narrative usage")


# ── AI Content Generation ─────────────────────────────────────────────────────

_CATEGORY_CONTEXT = {
    "policy":     "a government policy achievement or welfare scheme",
    "crisis":     "a crisis response or rebuttal to allegations",
    "leader":     "a leadership quote or vision statement",
    "historical": "a historical electoral or political victory",
    "education":  "an education policy or student welfare initiative",
    "healthcare": "a healthcare or public health initiative",
}

@router.post("/generate-content")
async def generate_narrative_content(payload: NarrativeGenerateRequest):
    """Use Gemini to generate a short narrative description from a title."""
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured")

    category_ctx = _CATEGORY_CONTEXT.get(payload.category, "a political or government topic")
    prompt = (
        f"Write a short, professional 2-3 sentence narrative description for the following headline about {category_ctx}.\n\n"
        f"Headline: {payload.title}\n\n"
        "Requirements:\n"
        "- 2-3 sentences only, concise and impactful\n"
        "- Positive, factual, and reputation-building tone\n"
        "- Highlight real benefits or achievements\n"
        "- Do NOT use quotes, bullet points, or placeholders\n"
        "- Output only the description text, nothing else"
    )

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = await asyncio.to_thread(model.generate_content, prompt)
        content = response.text.strip()
        return {"description": content}
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="AI content generation failed")
