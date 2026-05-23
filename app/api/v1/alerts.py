from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user_id, get_effective_user_id
from app.core.database import get_supabase

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
def list_alerts(
    limit: int = 50,
    change_type: Optional[str] = None,
    severity: Optional[str] = None,
    user_id: str = Depends(get_effective_user_id),
):
    db = get_supabase()

    # Get all competitor IDs for this user (exclude their own store — they know
    # their own changes; alerts are about competitors)
    comps = db.table("competitors").select("id, hostname").eq("user_id", user_id).eq("is_my_store", False).execute()
    comp_ids = [c["id"] for c in (comps.data or [])]
    hostname_map = {c["id"]: c["hostname"] for c in (comps.data or [])}

    if not comp_ids:
        return {"data": []}

    query = db.table("change_events")\
        .select("*")\
        .in_("competitor_id", comp_ids)\
        .order("detected_at", desc=True)\
        .limit(limit)
    if change_type:
        query = query.eq("change_type", change_type)
    if severity:
        query = query.eq("severity", severity)

    result = query.execute()
    rows = result.data or []
    for row in rows:
        row["hostname"] = hostname_map.get(row["competitor_id"], "")
    return {"data": rows}


@router.put("/{change_id}/read")
def mark_read(change_id: str, user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    # Verify ownership via competitor
    event = db.table("change_events").select("competitor_id").eq("id", change_id).single().execute()
    if not event.data:
        raise HTTPException(404, "Not found")
    comp = db.table("competitors").select("user_id").eq("id", event.data["competitor_id"]).single().execute()
    if not comp.data or comp.data["user_id"] != user_id:
        raise HTTPException(404, "Not found")
    db.table("change_events").update({"alert_sent": True}).eq("id", change_id).execute()
    return {"status": "ok"}


@router.get("/unread-count")
def unread_count(user_id: str = Depends(get_effective_user_id)):
    db = get_supabase()
    comps = db.table("competitors").select("id").eq("user_id", user_id).eq("is_my_store", False).execute()
    comp_ids = [c["id"] for c in (comps.data or [])]
    if not comp_ids:
        return {"count": 0}
    result = db.table("change_events")\
        .select("id", count="exact")\
        .in_("competitor_id", comp_ids)\
        .eq("alert_sent", False)\
        .execute()
    return {"count": result.count or 0}
