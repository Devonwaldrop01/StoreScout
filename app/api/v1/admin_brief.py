"""
Morning Executive Brief — StoreScout's intelligence philosophy applied to
StoreScout itself. One ADMIN_TOKEN-gated endpoint that answers, from real
database facts only: what happened, why it matters, and what Devon should
do today.

Honesty rules mirror the product: MRR is an ESTIMATE (tier × list price,
labeled), the funnel is computed from actual rows, content ideas come from
real detected changes, and anything we can't measure (session paths, scroll
depth) simply isn't shown — no fabricated analytics.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException

from app.core.config import get_settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/brief", tags=["admin-brief"])

_PLAN_PRICE = {"pro": 29, "agency": 79}


def _require_admin(token: Optional[str]) -> None:
    settings = get_settings()
    if not settings.admin_token or token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Forbidden")


def _count(db, table: str, **filters) -> int:
    try:
        q = db.table(table).select("id", count="exact")
        for k, v in filters.items():
            if k.endswith("__gte"):
                q = q.gte(k[:-5], v)
            elif k.endswith("__neq"):
                q = q.neq(k[:-5], v)
            else:
                q = q.eq(k, v)
        return q.execute().count or 0
    except Exception:
        return 0


@router.get("")
def morning_brief(x_admin_token: Optional[str] = Header(default=None)):
    _require_admin(x_admin_token)
    db = get_supabase()
    now = datetime.now(timezone.utc)
    day_ago = (now - timedelta(hours=24)).isoformat()
    week_ago = (now - timedelta(days=7)).isoformat()

    # ── Business ──────────────────────────────────────────────────────────
    users_total = _count(db, "user_profiles")
    users_24h = _count(db, "user_profiles", created_at__gte=day_ago)
    users_7d = _count(db, "user_profiles", created_at__gte=week_ago)
    pro_n = _count(db, "user_profiles", tier="pro")
    agency_n = _count(db, "user_profiles", tier="agency")
    mrr_estimate = pro_n * _PLAN_PRICE["pro"] + agency_n * _PLAN_PRICE["agency"]

    # ── Activation funnel — real rows, not events ─────────────────────────
    # Distinct users at each stage, computed from what actually exists in the DB.
    def _distinct_users(table: str, extra: Dict[str, Any] | None = None) -> int:
        try:
            q = db.table(table).select("user_id")
            for k, v in (extra or {}).items():
                q = q.eq(k, v)
            rows = q.limit(20000).execute().data or []
            return len({r["user_id"] for r in rows if r.get("user_id")})
        except Exception:
            return 0

    with_competitor = _distinct_users("competitors", {"is_my_store": False})
    with_own_store = _distinct_users("competitors", {"is_my_store": True})
    with_saved_play = _distinct_users("playbook_items")
    paid = pro_n + agency_n

    funnel = [
        {"stage": "Signed up", "count": users_total},
        {"stage": "Added a competitor", "count": with_competitor},
        {"stage": "Connected own store", "count": with_own_store},
        {"stage": "Saved a playbook move", "count": with_saved_play},
        {"stage": "Paid", "count": paid},
    ]
    # Biggest drop-off (absolute users lost between consecutive stages)
    biggest_drop = None
    for a, b in zip(funnel, funnel[1:]):
        lost = a["count"] - b["count"]
        if a["count"] > 0 and (biggest_drop is None or lost > biggest_drop["lost"]):
            biggest_drop = {"from": a["stage"], "to": b["stage"], "lost": lost,
                            "rate": round(b["count"] / a["count"] * 100, 1)}

    # ── Platform health ───────────────────────────────────────────────────
    scans_24h = _count(db, "scan_snapshots", scanned_at__gte=day_ago)
    scan_errors = _count(db, "competitors", scan_status="error")
    scans_stuck = _count(db, "competitors", scan_status="scanning")
    changes_24h = _count(db, "change_events", detected_at__gte=day_ago)
    competitors_active = _count(db, "competitors", is_active=True, is_my_store=False)

    # Recent failed jobs — worker health at a glance
    failed_jobs: List[dict] = []
    try:
        fj = db.table("competitors")\
            .select("hostname, error_message, updated_at")\
            .eq("scan_status", "error")\
            .order("updated_at", desc=True)\
            .limit(8).execute().data or []
        failed_jobs = [{
            "hostname": f.get("hostname"),
            "error": (f.get("error_message") or "")[:140],
            "at": f.get("updated_at"),
        } for f in fj]
    except Exception:
        pass

    # ── Engines ───────────────────────────────────────────────────────────
    index_verified = _count(db, "shopify_store_index", status="verified")
    index_verified_24h = 0
    last_index_run = None
    try:
        index_verified_24h = db.table("shopify_store_index").select("id", count="exact")\
            .eq("status", "verified").gte("last_verified_at", day_ago).execute().count or 0
        runs = db.table("store_index_runs").select("ran_at, verified, processed, failed")\
            .order("ran_at", desc=True).limit(1).execute().data or []
        last_index_run = runs[0] if runs else None
    except Exception:
        pass

    leads_ready = _count(db, "lead_prospects", outreach_status="ready")
    leads_today = _count(db, "lead_prospects", created_at__gte=day_ago)
    leads_contacted = _count(db, "lead_prospects", outreach_status="contacted")
    leads_replied = _count(db, "lead_prospects", outreach_status="replied")
    leads_customers = _count(db, "lead_prospects", outreach_status="customer") \
        + _count(db, "lead_prospects", outreach_status="trial_started")

    # ── Content opportunities — from real detected changes ───────────────
    content_ideas: List[str] = []
    try:
        two_days = (now - timedelta(hours=48)).isoformat()
        evs = db.table("change_events")\
            .select("change_type, product_title, delta_pct, severity, competitor_id, competitors(hostname)")\
            .gte("detected_at", two_days)\
            .in_("severity", ["critical", "warning"])\
            .order("detected_at", desc=True)\
            .limit(30).execute().data or []
        seen_hosts: set = set()
        for e in evs:
            host = ((e.get("competitors") or {}).get("hostname") or "").replace("www.", "")
            if not host or host in seen_hosts:
                continue
            seen_hosts.add(host)
            ct = e.get("change_type")
            if ct == "price_change" and (e.get("delta_pct") or 0) < 0:
                content_ideas.append(
                    f"{host} just cut prices ({e.get('delta_pct'):+.0f}% on {e.get('product_title') or 'key products'}) — post: \"what a discount war looks like from the inside\""
                )
            elif ct in ("new_product", "bulk_new_products"):
                content_ideas.append(
                    f"{host} is launching — post: \"we watched a DTC brand drop a new line in real time; here's the playbook\""
                )
            elif ct in ("bulk_removal", "product_removed"):
                content_ideas.append(
                    f"{host} pulled products this week — post: \"reading a catalog cull: what removals reveal\""
                )
            if len(content_ideas) >= 3:
                break
    except Exception as exc:
        logger.debug("content ideas skipped: %s", exc)

    # ── Interpretation: today's single priority — deterministic rules ────
    priority = None
    if scan_errors >= max(3, competitors_active // 5 or 1):
        priority = f"Scanner health: {scan_errors} competitors stuck in error — merchants are seeing stale data. Fix this before anything else."
    elif leads_ready > 0 and leads_contacted == 0:
        priority = f"Outreach: {leads_ready} researched prospects are sitting in Ready with zero contacted. Send 5 emails today — the drafts are already written."
    elif biggest_drop and biggest_drop["lost"] > 0 and users_total >= 5 and biggest_drop["rate"] < 50:
        priority = f"Funnel: the biggest leak is {biggest_drop['from']} → {biggest_drop['to']} ({biggest_drop['rate']}% convert). Watch one new user session end-to-end and fix the first point of confusion."
    elif index_verified < 100:
        priority = f"Index depth: {index_verified} verified stores. Discovery and lead quality both compound on this — seed 3 target niches and run the worker."
    elif users_7d == 0:
        priority = "Growth: zero signups this week. The product is ahead of distribution — today is a content/outreach day, not a build day."
    else:
        priority = "Steady state — spend today talking to an active user instead of shipping."

    return {
        "data": {
            "generated_at": now.isoformat(),
            "priority": priority,
            "business": {
                "users_total": users_total,
                "users_24h": users_24h,
                "users_7d": users_7d,
                "pro": pro_n,
                "agency": agency_n,
                "mrr_estimate": mrr_estimate,  # tier × list price — labeled estimated in UI
            },
            "funnel": funnel,
            "biggest_drop": biggest_drop,
            "health": {
                "competitors_active": competitors_active,
                "scans_24h": scans_24h,
                "scan_errors": scan_errors,
                "scans_stuck": scans_stuck,
                "changes_24h": changes_24h,
                "failed_jobs": failed_jobs,
            },
            "engines": {
                "index_verified": index_verified,
                "index_verified_24h": index_verified_24h,
                "last_index_run": last_index_run,
                "leads_ready": leads_ready,
                "leads_today": leads_today,
                "leads_contacted": leads_contacted,
                "leads_replied": leads_replied,
                "leads_customers": leads_customers,
            },
            "content_ideas": content_ideas,
        }
    }
