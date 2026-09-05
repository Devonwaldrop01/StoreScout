from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends

from app.core.auth import get_effective_user_id
from app.core.config import get_settings
from app.core.database import get_supabase

_AI_FRESHNESS_HOURS = 23

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playbook", tags=["playbook"])


@router.get("")
def get_playbook(user_id: str = Depends(get_effective_user_id)):
    try:
        return _build_playbook(user_id)
    except Exception as exc:
        logger.error("playbook failed for user %s: %s", user_id, exc, exc_info=True)
        # Try to return a meaningful competitor_count even on failure
        try:
            db = get_supabase()
            r = db.table("competitors").select("id", count="exact")\
                .eq("user_id", user_id).eq("is_active", True).eq("is_my_store", False).execute()
            count = r.count or 0
        except Exception:
            count = 0
        return {"plays": [], "competitor_count": count, "locked": False, "ai_state": "unavailable", "error": "Playbook data could not be loaded. Please retry."}


def _build_playbook(user_id: str) -> dict:
    db = get_supabase()

    user_res = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    tier = ((user_res and user_res.data) or {}).get("tier", "free")

    comps_res = (
        db.table("competitors")
        .select("id, hostname, is_my_store")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .execute()
    )
    # Include competitors regardless of current scan_status — worker outages shouldn't
    # blank the playbook. Snapshot availability is checked per-competitor below.
    competitors = [c for c in (comps_res.data or []) if not c.get("is_my_store")]

    if not competitors:
        return {"plays": [], "competitor_count": 0, "locked": False}

    comp_ids = [c["id"] for c in competitors]
    comp_map = {c["id"]: c["hostname"] for c in competitors}

    # ── Prefer fresh AI-generated plays ──────────────────────────────────────
    ai_cutoff = (datetime.now(timezone.utc) - timedelta(hours=_AI_FRESHNESS_HOURS)).isoformat()
    ai_res = (
        db.table("ai_summaries")
        .select("summary_text, generated_at")
        .in_("competitor_id", comp_ids)
        .eq("summary_type", "playbook")
        .gte("generated_at", ai_cutoff)
        .order("generated_at", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    if ai_res and ai_res.data:
        try:
            ai_data = json.loads(ai_res.data["summary_text"])
            ai_plays = ai_data.get("plays") or []
            if ai_plays and ai_data.get("user_id") == user_id and ai_data.get("engine_version") == 1:
                valid_ids = set(comp_ids)
                from app.services.action_candidates import fresh
                ai_plays = [p for p in ai_plays if p.get("competitor_id") in valid_ids
                            and (p.get("fact_confidence") == "stale" or fresh(p.get("observed_at"), datetime.now(timezone.utc)))]
                if not ai_plays:
                    raise ValueError("Cached actions have no current supported observations")
                # Sort by priority so free-tier slice always gets highest-urgency plays
                ai_plays_sorted = sorted(ai_plays, key=lambda x: x.get("priority", 0), reverse=True)
                if tier == "free":
                    shown = ai_plays_sorted[:4]
                    locked_count = max(0, len(ai_plays_sorted) - 4)
                    return {
                        "plays": shown,
                        "competitor_count": len(competitors),
                        "locked": locked_count > 0,
                        "locked_count": locked_count,
                        "ai_source": True,
                        "ai_generating": False,
                        "ai_state": "ready",
                    }
                return {
                    "plays": ai_plays_sorted,
                    "competitor_count": len(competitors),
                    "locked": False,
                    "locked_count": 0,
                    "ai_source": True,
                    "ai_generating": False,
                    "ai_state": "ready",
                }
        except Exception:
            pass  # fall through to template plays

    # No fresh AI plays — resolve a FINITE job state instead of re-dispatching on
    # every poll (which caused the indefinite "AI analysis in progress"). Dedup
    # concurrent generations and time a stuck job out.
    from app.services.ai_job import decide_ai_action, read_phase, mark_started, mark_failed
    settings = get_settings()
    phase, age = read_phase("playbook", user_id)
    ai_state, action = decide_ai_action(
        has_fresh_result=False, phase=phase, age_s=age,
        timeout_s=settings.playbook_ai_timeout_s,
    )
    if action == "dispatch":
        try:
            from app.tasks.playbook_ai import generate_ai_playbook
            generate_ai_playbook.delay(user_id)
            mark_started("playbook", user_id, ttl_s=settings.playbook_ai_timeout_s + 60)
        except Exception as exc:
            logger.warning("Could not enqueue generate_ai_playbook for %s: %s", user_id, exc)
            mark_failed("playbook", user_id)   # not generating forever — a finite failure
            ai_state = "unavailable"
    elif action == "mark_failed":
        # A job exceeded the timeout without persisting — persist the terminal
        # state so reloads stay finite and GET never re-dispatches.
        mark_failed("playbook", user_id)
    # Only claim "generating" when a job is genuinely in flight.
    ai_generating = ai_state == "generating"

    from app.services.action_candidates import load_context
    plays = load_context(db, user_id, comps_res.data or [])

    # ── 3. Deduplicate + sort ─────────────────────────────────────────────────
    seen: set[str] = set()
    unique: list[dict] = []
    for p in sorted(plays, key=lambda x: x.get("priority", 0), reverse=True):
        if p["id"] not in seen:
            seen.add(p["id"])
            unique.append(p)

    # Free tier: show 4 plays (already sorted by priority above)
    if tier == "free":
        shown = unique[:4]
        locked_count = max(0, len(unique) - 4)
        return {
            "plays": shown,
            "competitor_count": len(competitors),
            "locked": locked_count > 0,
            "locked_count": locked_count,
            "ai_source": False,
            "ai_generating": ai_generating,
            "ai_state": ai_state,
        }

    return {
        "plays": unique,
        "competitor_count": len(competitors),
        "locked": False,
        "locked_count": 0,
        "ai_source": False,
        "ai_generating": ai_generating,
        "ai_state": ai_state,
    }


@router.post("/regenerate")
def regenerate_playbook(user_id: str = Depends(get_effective_user_id)):
    """Retry AI Playbook generation after a failed/timed-out attempt. Clears the
    single-flight job marker so the next GET dispatches a fresh generation, and
    kicks one off now. Idempotent; safe to call repeatedly."""
    from app.services.ai_job import clear_job, mark_started, mark_failed
    settings = get_settings()
    clear_job("playbook", user_id)
    try:
        from app.tasks.playbook_ai import generate_ai_playbook
        generate_ai_playbook.delay(user_id)
        mark_started("playbook", user_id, ttl_s=settings.playbook_ai_timeout_s + 60)
        return {"status": "queued", "ai_state": "generating"}
    except Exception as exc:
        logger.warning("regenerate_playbook enqueue failed for %s: %s", user_id, exc)
        mark_failed("playbook", user_id)
        return {"status": "unavailable", "ai_state": "unavailable"}
