from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends

from app.core.auth import get_effective_user_id
from app.core.database import get_supabase
from app.services.playbook_intelligence import snapshot_intelligence, change_event_play

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playbook", tags=["playbook"])


@router.get("")
def get_playbook(user_id: str = Depends(get_effective_user_id)):
    try:
        return _build_playbook(user_id)
    except Exception as exc:
        logger.error("playbook failed for user %s: %s", user_id, exc)
        return {"plays": [], "competitor_count": 0, "locked": False}


def _build_playbook(user_id: str) -> dict:
    db = get_supabase()

    # Get user tier
    user_res = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    tier = (user_res.data or {}).get("tier", "free")

    # Get active, scanned competitors
    comps_res = (
        db.table("competitors")
        .select("id, hostname")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .eq("scan_status", "done")
        .execute()
    )
    # Filter out my_store if column exists
    competitors = [
        c for c in (comps_res.data or [])
        if not c.get("is_my_store")
    ]

    if not competitors:
        return {"plays": [], "competitor_count": 0, "locked": False}

    comp_ids  = [c["id"] for c in competitors]
    comp_map  = {c["id"]: c["hostname"] for c in competitors}

    plays: list[dict] = []

    # ── 1. Snapshot intelligence (always available) ───────────────────────────
    for comp in competitors:
        cid  = comp["id"]
        host = comp["hostname"]
        snap_res = (
            db.table("scan_snapshots")
            .select("product_count, median_price, promo_rate, new_30d, snapshot_data, scanned_at")
            .eq("competitor_id", cid)
            .order("scanned_at", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        snap = snap_res.data
        if not snap:
            continue
        plays.extend(snapshot_intelligence(snap, host, cid))

    # ── 2. Change-event plays (reactive, last 7 days) ─────────────────────────
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    changes_res = (
        db.table("change_events")
        .select("*")
        .in_("competitor_id", comp_ids)
        .gte("detected_at", cutoff)
        .order("detected_at", desc=True)
        .limit(150)
        .execute()
    )
    raw_changes = [
        c for c in (changes_res.data or [])
        if c.get("severity") in ("critical", "warning")
    ]

    # Deduplicate change plays per competitor (max 2 change plays per competitor)
    change_count: dict[str, int] = {}
    for chg in sorted(raw_changes, key=lambda c: c.get("detected_at", ""), reverse=True):
        cid  = chg["competitor_id"]
        host = comp_map.get(cid)
        if not host:
            continue
        if change_count.get(cid, 0) >= 2:
            continue
        play = change_event_play(chg, host, cid)
        if play:
            plays.append(play)
            change_count[cid] = change_count.get(cid, 0) + 1

    # ── 3. Deduplicate by id, sort by priority ────────────────────────────────
    seen_ids: set[str] = set()
    unique: list[dict] = []
    for p in sorted(plays, key=lambda x: x.get("priority", 0), reverse=True):
        if p["id"] not in seen_ids:
            seen_ids.add(p["id"])
            unique.append(p)

    # Free users: show 4 plays, mark rest as locked_count
    if tier == "free":
        shown   = unique[:4]
        locked_count = max(0, len(unique) - 4)
        return {
            "plays": shown,
            "competitor_count": len(competitors),
            "locked": locked_count > 0,
            "locked_count": locked_count,
        }

    return {
        "plays": unique,
        "competitor_count": len(competitors),
        "locked": False,
        "locked_count": 0,
    }
