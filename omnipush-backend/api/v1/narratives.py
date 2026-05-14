"""
Narratives API — CRUD for Narrative Bank
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional, List
from pydantic import BaseModel
import logging
from datetime import datetime, timezone

from core.middleware import get_current_user
from core.database import get_database, SupabaseClient
from models.auth import JWTPayload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/narratives", tags=["narratives"])


# ── Pydantic Models ─────────────────────────────────────────────────────────

class NarrativeCreate(BaseModel):
    title: str
    description: str
    category: str = "policy"
    priority: str = "medium"
    tags: List[str] = []


class NarrativeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _narratives_table(db: SupabaseClient):
    return db.service_client.table("narratives")


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/")
async def list_narratives(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: JWTPayload = Depends(get_current_user),
    db: SupabaseClient = Depends(get_database),
):
    try:
        q = _narratives_table(db).select("*").eq("tenant_id", current_user.tenant_id).eq("is_active", True)

        if category:
            q = q.eq("category", category)
        if priority:
            q = q.eq("priority", priority)

        q = q.order("usage_count", desc=True).range(offset, offset + limit - 1)
        result = q.execute()

        items = result.data or []

        # Client-side search filter (Supabase free tier has no full-text search)
        if search:
            sl = search.lower()
            items = [
                n for n in items
                if sl in n.get("title", "").lower() or sl in n.get("description", "").lower()
            ]

        return {"narratives": items, "total": len(items)}

    except Exception as e:
        logger.error(f"Error listing narratives: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch narratives")


@router.post("/", status_code=201)
async def create_narrative(
    payload: NarrativeCreate,
    current_user: JWTPayload = Depends(get_current_user),
    db: SupabaseClient = Depends(get_database),
):
    try:
        data = {
            "tenant_id": current_user.tenant_id,
            "title": payload.title,
            "description": payload.description,
            "category": payload.category,
            "priority": payload.priority,
            "tags": payload.tags,
            "created_by": current_user.sub,
        }
        result = _narratives_table(db).insert(data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Insert returned no data")
        return {"narrative": result.data[0]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating narrative: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create narrative")


@router.put("/{narrative_id}")
async def update_narrative(
    narrative_id: str,
    payload: NarrativeUpdate,
    current_user: JWTPayload = Depends(get_current_user),
    db: SupabaseClient = Depends(get_database),
):
    try:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = (
            _narratives_table(db)
            .update(updates)
            .eq("id", narrative_id)
            .eq("tenant_id", current_user.tenant_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Narrative not found")
        return {"narrative": result.data[0]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating narrative {narrative_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update narrative")


@router.delete("/{narrative_id}", status_code=200)
async def delete_narrative(
    narrative_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    db: SupabaseClient = Depends(get_database),
):
    try:
        result = (
            _narratives_table(db)
            .update({"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", narrative_id)
            .eq("tenant_id", current_user.tenant_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Narrative not found")
        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting narrative {narrative_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete narrative")


@router.post("/{narrative_id}/use")
async def use_narrative(
    narrative_id: str,
    current_user: JWTPayload = Depends(get_current_user),
    db: SupabaseClient = Depends(get_database),
):
    """Increment usage_count and update last_used timestamp."""
    try:
        # Fetch current count
        existing = (
            _narratives_table(db)
            .select("usage_count")
            .eq("id", narrative_id)
            .eq("tenant_id", current_user.tenant_id)
            .maybe_single()
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Narrative not found")

        new_count = (existing.data.get("usage_count") or 0) + 1
        now = datetime.now(timezone.utc).isoformat()

        result = (
            _narratives_table(db)
            .update({"usage_count": new_count, "last_used": now, "updated_at": now})
            .eq("id", narrative_id)
            .eq("tenant_id", current_user.tenant_id)
            .execute()
        )
        return {"narrative": result.data[0] if result.data else None}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error using narrative {narrative_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to record narrative usage")
