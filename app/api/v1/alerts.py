from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_current_user_id, get_effective_user_id
from app.core.database import get_supabase

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _user_competitor_ids(db, user_id: str) -> tuple[list[str], dict[str, str]]:
    """Return (comp_ids, hostname_map) for all non-own-store competitors."""
    comps = (
        db.table("competitors")
        .select("id, hostname")
        .eq("user_id", user_id)
        .eq("is_my_store", False)
        .execute()
    )
    ids = [c["id"] for c in (comps.data or [])]
    hmap = {c["id"]: c["hostname"] for c in (comps.data or [])}
    return ids, hmap


@router.get("")
def list_alerts(
    limit: int = 50,
    change_type: Optional[str] = None,
    severity: Optional[str] = None,
    user_id: str = Depends(get_effective_user_id),
):
    db = get_supabase()
    comp_ids, hostname_map = _user_competitor_ids(db, user_id)

    if not comp_ids:
        return {"data": []}

    query = (
        db.table("change_events")
        .select("*")
        .in_("competitor_id", comp_ids)
        .order("detected_at", desc=True)
        .limit(limit)
    )
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
    """Mark a single alert as read in-app (sets read_at, not alert_sent)."""
    db = get_supabase()

    event = (
        db.table("change_events")
        .select("competitor_id")
        .eq("id", change_id)
        .single()
        .execute()
    )
    if not event.data:
        raise HTTPException(404, "Not found")

    comp = (
        db.table("competitors")
        .select("user_id")
        .eq("id", event.data["competitor_id"])
        .single()
        .execute()
    )
    if not comp.data or comp.data["user_id"] != user_id:
        raise HTTPException(404, "Not found")

    now = datetime.now(timezone.utc).isoformat()
    db.table("change_events").update({"read_at": now}).eq("id", change_id).execute()
    return {"status": "ok"}


@router.post("/mark-all-read")
def mark_all_read(user_id: str = Depends(get_effective_user_id)):
    """
    Mark all unread alerts as read for this user.
    Called when the user visits the alerts page so the notification bell clears.
    """
    db = get_supabase()
    comp_ids, _ = _user_competitor_ids(db, user_id)

    if not comp_ids:
        return {"status": "ok", "marked": 0}

    now = datetime.now(timezone.utc).isoformat()
    result = (
        db.table("change_events")
        .update({"read_at": now})
        .in_("competitor_id", comp_ids)
        .is_("read_at", "null")
        .execute()
    )
    marked = len(result.data or [])
    return {"status": "ok", "marked": marked}


@router.get("/unread-count")
def unread_count(user_id: str = Depends(get_effective_user_id)):
    """
    Count unread in-app alerts (read_at IS NULL).
    Intentionally separate from alert_sent, which tracks email cooldown.
    """
    db = get_supabase()
    comp_ids, _ = _user_competitor_ids(db, user_id)

    if not comp_ids:
        return {"count": 0}

    result = (
        db.table("change_events")
        .select("id", count="exact")
        .in_("competitor_id", comp_ids)
        .is_("read_at", "null")
        .execute()
    )
    return {"count": result.count or 0}
