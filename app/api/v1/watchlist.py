from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import get_effective_user_id
from app.core.database import get_supabase
from app.core.obs import safe_read
from app.tasks.detect_changes import _product_index

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

def _cap_for(db, user_id: str) -> int:
    # How many products each tier can pin — canonical source in entitlements.
    from app.services.entitlements import watch_cap_for, resolve_tier
    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    return watch_cap_for(resolve_tier(user.data if user else None))


def _latest_index(db, competitor_id: str) -> dict:
    """Current handle -> product dict from the competitor's most recent snapshot."""
    res = (
        db.table("scan_snapshots")
        .select("snapshot_data")
        .eq("competitor_id", competitor_id)
        .order("scanned_at", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        return {}
    return _product_index(res.data[0].get("snapshot_data") or {})


class AddWatchRequest(BaseModel):
    competitor_id: str
    product_handle: str
    product_title: Optional[str] = None
    product_url: Optional[str] = None
    pinned_price: Optional[float] = None


@router.get("")
@safe_read("GET /watchlist", {"data": [], "cap": 0})
def list_watches(user_id: str = Depends(get_effective_user_id)):
    """Return the user's pinned products enriched with current price + delta."""
    db = get_supabase()
    rows = (
        db.table("product_watches")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    ).data or []
    if not rows:
        return {"data": [], "cap": _cap_for(db, user_id)}

    # Hostname lookup + a cached snapshot index per competitor
    comp_ids = list({r["competitor_id"] for r in rows if r.get("competitor_id")})
    hosts: dict[str, str] = {}
    if comp_ids:
        comps = db.table("competitors").select("id, hostname").in_("id", comp_ids).execute()
        hosts = {c["id"]: c.get("hostname", "") for c in (comps.data or [])}

    index_cache: dict[str, dict] = {}
    out = []
    for r in rows:
        cid = r.get("competitor_id")
        if cid not in index_cache:
            index_cache[cid] = _latest_index(db, cid) if cid else {}
        prod = index_cache[cid].get(r.get("product_handle")) or {}
        current_price = prod.get("price_min")
        pinned = r.get("pinned_price")
        delta_pct = None
        if pinned and current_price is not None and float(pinned) > 0:
            delta_pct = round((float(current_price) - float(pinned)) / float(pinned) * 100, 1)
        out.append({
            "id": r["id"],
            "competitor_id": cid,
            "hostname": hosts.get(cid, ""),
            "handle": r.get("product_handle"),
            "title": r.get("product_title"),
            "url": r.get("product_url"),
            "pinned_price": pinned,
            "current_price": current_price,
            "available": prod.get("available"),
            "removed": not prod,  # not found in latest snapshot = delisted
            "delta_pct": delta_pct,
        })
    return {"data": out, "cap": _cap_for(db, user_id)}


@router.post("")
def add_watch(body: AddWatchRequest, user_id: str = Depends(get_effective_user_id)):
    db = get_supabase()

    # Ownership: the competitor must belong to the user
    owner = (
        db.table("competitors").select("user_id")
        .eq("id", body.competitor_id).maybe_single().execute()
    )
    if not owner or not owner.data or owner.data.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Competitor not found")

    cap = _cap_for(db, user_id)
    existing = (
        db.table("product_watches").select("id", count="exact")
        .eq("user_id", user_id).execute()
    )
    count = existing.count if existing.count is not None else len(existing.data or [])
    if count >= cap:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"code": "watchlist_limit_reached", "limit": cap},
        )

    db.table("product_watches").upsert({
        "user_id": user_id,
        "competitor_id": body.competitor_id,
        "product_handle": body.product_handle,
        "product_title": body.product_title,
        "product_url": body.product_url,
        "pinned_price": body.pinned_price,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id,competitor_id,product_handle").execute()

    return {"status": "ok"}


@router.delete("/{watch_id}", status_code=204)
def remove_watch(watch_id: str, user_id: str = Depends(get_effective_user_id)):
    db = get_supabase()
    db.table("product_watches").delete().eq("id", watch_id).eq("user_id", user_id).execute()
