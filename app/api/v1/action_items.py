from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends

from app.core.auth import get_effective_user_id
from app.core.database import get_supabase
from app.services.action_templates import action_for_change, action_for_gap

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/action-items", tags=["action-items"])

_PRIORITY = {
    ("critical", True): 100,   # critical change <48h
    ("warning", True): 80,     # warning change <48h
    ("critical", False): 60,   # critical change <7d
    ("warning", False): 50,    # warning change <7d
}


def _score_change(change: dict) -> int:
    sev = change.get("severity", "info")
    recent = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    is_recent = change.get("detected_at", "") >= recent
    return _PRIORITY.get((sev, is_recent), 0)


@router.get("")
def get_action_items(user_id: str = Depends(get_effective_user_id)):
    try:
        return _get_action_items_inner(user_id)
    except Exception as exc:
        logger.error("action_items failed for user %s: %s", user_id, exc)
        return {"data": [], "locked": False}


def _get_action_items_inner(user_id: str) -> dict:
    db = get_supabase()

    # Check tier
    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    tier = (user.data or {}).get("tier", "free")
    if tier == "free":
        return {"data": [], "locked": True}

    # Get active competitors
    comps_res = db.table("competitors")\
        .select("id, hostname")\
        .eq("user_id", user_id)\
        .eq("is_active", True)\
        .eq("is_my_store", False)\
        .eq("scan_status", "done")\
        .execute()
    competitors = comps_res.data or []
    if not competitors:
        return {"data": [], "locked": False}

    comp_ids = [c["id"] for c in competitors]
    comp_map = {c["id"]: c["hostname"] for c in competitors}

    # Get recent changes (last 7 days), filter warning/critical in Python
    # to avoid chaining two in_() calls which may behave inconsistently
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    changes_res = db.table("change_events")\
        .select("*")\
        .in_("competitor_id", comp_ids)\
        .gte("detected_at", cutoff)\
        .order("detected_at", desc=True)\
        .limit(100)\
        .execute()
    changes = [
        c for c in (changes_res.data or [])
        if c.get("severity") in ("critical", "warning")
    ]

    # Build action items from changes
    items: List[dict] = []
    seen_competitors: set = set()

    # Sort changes by priority score
    changes.sort(key=_score_change, reverse=True)

    for change in changes:
        comp_id = change["competitor_id"]
        hostname = comp_map.get(comp_id, "")
        if not hostname:
            continue

        # Max 1 item per competitor unless < 3 total competitors
        if comp_id in seen_competitors and len(competitors) >= 3:
            continue

        sev = change.get("severity", "info")
        ct = change.get("change_type", "")
        delta = change.get("delta_pct") or 0

        if ct == "price_change" and delta < 0:
            item_type = "threat"
        elif ct in ("new_product", "bulk_new_products"):
            item_type = "opportunity"
        elif ct in ("product_removed", "bulk_removal", "availability_change"):
            item_type = "opportunity"
        elif ct in ("discount_start", "bulk_price_change"):
            item_type = "threat" if sev == "critical" else "opportunity"
        elif ct == "discount_end":
            item_type = "opportunity"
        elif ct == "price_change" and delta > 0:
            item_type = "opportunity"
        else:
            item_type = "threat"

        action_text = action_for_change(change, hostname)

        # Build headline
        title = (change.get("product_title") or "")[:40]
        if ct == "price_change":
            n_products = 1
            headline = (
                f"{hostname} flash sale — {abs(delta):.0f}% off" if sev == "critical" and delta < 0
                else f"{hostname} price {'drop' if delta < 0 else 'increase'} — {abs(delta):.0f}%"
            )
        elif ct == "bulk_price_change":
            count = (change.get("old_value") or {}).get("count") or (change.get("new_value") or {}).get("count") or "several"
            headline = f"{hostname} repriced {count} products"
        elif ct == "new_product":
            headline = f"{hostname} launched: {title}" if title else f"{hostname} launched a new product"
        elif ct == "bulk_new_products":
            count = (change.get("new_value") or {}).get("count") or "several"
            headline = f"{hostname} added {count} new products"
        elif ct == "product_removed":
            headline = f"{hostname} pulled: {title}" if title else f"{hostname} removed a product"
        elif ct == "bulk_removal":
            count = (change.get("old_value") or {}).get("count") or "several"
            headline = f"{hostname} removed {count} products"
        elif ct == "discount_start":
            pct = (change.get("new_value") or {}).get("discounted_pct") or 0
            headline = f"{hostname} started discounting — {pct:.0f}% of catalog"
        elif ct == "discount_end":
            headline = f"{hostname}'s sale just ended"
        elif ct == "availability_change":
            headline = f"{hostname} has stock gaps"
        else:
            headline = f"{hostname}: {ct.replace('_', ' ')}"

        # Context: how long ago
        detected = change.get("detected_at", "")
        if detected:
            try:
                dt = datetime.fromisoformat(detected.replace("Z", "+00:00"))
                hours_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                if hours_ago < 1:
                    context = "Detected just now"
                elif hours_ago < 24:
                    context = f"Detected {hours_ago:.0f}h ago"
                else:
                    days = int(hours_ago / 24)
                    context = f"Detected {days}d ago"
            except Exception:
                context = "Recently detected"
        else:
            context = "Recently detected"

        # Tab to link to on the detail page
        if ct in ("price_change", "bulk_price_change"):
            tab = "pricing"
        elif ct in ("new_product", "bulk_new_products", "product_removed", "bulk_removal"):
            tab = "launches"
        elif ct in ("discount_start", "discount_end"):
            tab = "discounts"
        else:
            tab = "changes"

        items.append({
            "id": f"change-{change['id']}",
            "type": item_type,
            "competitor_id": comp_id,
            "hostname": hostname,
            "headline": headline,
            "action_text": action_text,
            "context": context,
            "tab": tab,
        })
        seen_competitors.add(comp_id)

    # Return top 5
    return {"data": items[:5], "locked": False}
