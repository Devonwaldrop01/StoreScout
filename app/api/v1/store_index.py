"""
Shopify store index API.

  · GET  /store-index/search           — authenticated; verified stores only.
    Powers (and will increasingly power) competitor discovery.
  · GET  /api/v1/admin/store-index/stats — admin console data
  · POST /api/v1/admin/store-index/seed  — manual candidate ingestion
  · POST /api/v1/admin/store-index/run   — small manual indexing run

Admin endpoints require the X-Admin-Token header to equal ADMIN_TOKEN; while
that env var is empty they are hard-disabled (403 for every request).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.auth import get_effective_user_id
from app.core.config import get_settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(tags=["store-index"])

_SEARCH_FIELDS = (
    "domain, brand_name, category, subcategory, description, "
    "product_count, median_price, promo_rate, verification_confidence, "
    "business_stage, pricing_tier"
)


def _require_admin(token: Optional[str]) -> None:
    settings = get_settings()
    # Empty ADMIN_TOKEN = admin surface disabled entirely
    if not settings.admin_token or token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Forbidden")


# ── Search (authenticated users; internal consumer: discovery) ────────────

@router.get("/store-index/search")
def search_store_index(
    q: str = "",
    category: str = "",
    limit: int = 20,
    user_id: str = Depends(get_effective_user_id),
):
    db = get_supabase()
    limit = max(1, min(limit, 50))

    query = db.table("shopify_store_index")\
        .select(_SEARCH_FIELDS)\
        .eq("status", "verified")\
        .order("verification_confidence", desc=True)\
        .limit(limit)

    if category:
        query = query.eq("category", category)

    terms = [t.strip() for t in (q or "").split() if len(t.strip()) >= 3][:5]
    if terms:
        ors = []
        for t in terms:
            for col in ("brand_name", "description", "category", "subcategory", "domain"):
                ors.append(f"{col}.ilike.%{t}%")
        query = query.or_(",".join(ors))

    try:
        result = query.execute()
        return {"data": result.data or []}
    except Exception as exc:
        # Table may not exist yet (migration pending) — empty result, not a 500
        logger.warning("store-index search failed: %s", exc)
        return {"data": []}


# ── Admin ──────────────────────────────────────────────────────────────────

@router.get("/admin/store-index/stats")
def store_index_stats(
    status: str = "",
    category: str = "",
    domain: str = "",
    x_admin_token: Optional[str] = Header(default=None),
):
    _require_admin(x_admin_token)
    db = get_supabase()

    def _count(**filters) -> int:
        try:
            q = db.table("shopify_store_index").select("id", count="exact")
            for k, v in filters.items():
                q = q.eq(k, v)
            return q.execute().count or 0
        except Exception:
            return 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")
    try:
        added_today = db.table("shopify_store_index")\
            .select("id", count="exact").gte("created_at", today).execute().count or 0
    except Exception:
        added_today = 0

    rows: List[dict] = []
    try:
        q = db.table("shopify_store_index")\
            .select("domain, brand_name, category, subcategory, status, verification_confidence, "
                    "product_count, median_price, promo_rate, source, source_query, failure_reason, "
                    "business_stage, pricing_tier, last_verified_at, created_at")\
            .order("updated_at", desc=True)\
            .limit(50)
        if status:
            q = q.eq("status", status)
        if category:
            q = q.eq("category", category)
        if domain:
            q = q.ilike("domain", f"%{domain}%")
        rows = q.execute().data or []
    except Exception as exc:
        logger.warning("store-index stats rows failed (table missing?): %s", exc)

    # ── Quality aggregates — computed in Python over a slim sample of up to
    # 5000 rows (plenty for early scale; PostgREST has no group-by).
    categories: dict = {}
    sources: dict = {}
    failures: dict = {}
    conf_sum = 0
    conf_n = 0
    verified_today = 0
    try:
        agg = db.table("shopify_store_index")\
            .select("status, category, source, failure_reason, verification_confidence, last_verified_at")\
            .order("updated_at", desc=True)\
            .limit(5000)\
            .execute()
        for r in agg.data or []:
            if r.get("status") == "verified":
                if r.get("category"):
                    categories[r["category"]] = categories.get(r["category"], 0) + 1
                if r.get("verification_confidence") is not None:
                    conf_sum += r["verification_confidence"]
                    conf_n += 1
                if (r.get("last_verified_at") or "") >= today:
                    verified_today += 1
            if r.get("source"):
                sources[r["source"]] = sources.get(r["source"], 0) + 1
            if r.get("status") in ("rejected", "failed") and r.get("failure_reason"):
                key = r["failure_reason"][:80]
                failures[key] = failures.get(key, 0) + 1
    except Exception as exc:
        logger.warning("store-index quality aggregates failed: %s", exc)

    verified_n = _count(status="verified")
    rejected_n = _count(status="rejected")
    failed_n = _count(status="failed")
    attempted = verified_n + rejected_n + failed_n

    runs: List[dict] = []
    try:
        runs = db.table("store_index_runs")\
            .select("ran_at, trigger, processed, verified, rejected, failed, duplicates, reverified, source_counts")\
            .order("ran_at", desc=True)\
            .limit(14)\
            .execute().data or []
    except Exception:
        pass  # table lands with migration 008

    _top = lambda d, n: sorted(d.items(), key=lambda kv: -kv[1])[:n]
    return {
        "data": {
            "total": _count(),
            "verified": verified_n,
            "candidates": _count(status="candidate"),
            "rejected": rejected_n,
            "failed": failed_n,
            "added_today": added_today,
            "verified_today": verified_today,
            "success_rate": round(verified_n / attempted * 100, 1) if attempted else None,
            "avg_confidence": round(conf_sum / conf_n, 1) if conf_n else None,
            "categories": [{"name": k, "count": v} for k, v in _top(categories, 12)],
            "sources": [{"name": k, "count": v} for k, v in _top(sources, 8)],
            "top_failures": [{"reason": k, "count": v} for k, v in _top(failures, 6)],
            "runs": runs,
            "rows": rows,
        }
    }


# ── Index Operations dashboard — the three-stage pipeline at a glance ────────

@router.get("/admin/index-ops")
def index_ops(x_admin_token: Optional[str] = Header(default=None)):
    """
    Everything the operator needs to see what the index is doing right now:
    the discovery→verification→knowledge funnel, today's throughput, success
    rate, category coverage, discovery sources + progress, recent failures with
    reasons, and index growth. Degrades to zeros pre-migration (never 500s).
    """
    _require_admin(x_admin_token)
    db = get_supabase()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")

    def _count(**filters) -> int:
        try:
            q = db.table("shopify_store_index").select("id", count="exact")
            for k, v in filters.items():
                q = q.eq(k, v)
            return q.execute().count or 0
        except Exception:
            return 0

    def _count_gte(col: str, val: str, **filters) -> int:
        try:
            q = db.table("shopify_store_index").select("id", count="exact").gte(col, val)
            for k, v in filters.items():
                q = q.eq(k, v)
            return q.execute().count or 0
        except Exception:
            return 0

    # ── Pipeline funnel (lifetime) ──
    discovered = _count(status="discovered")
    verified = _count(status="verified")
    rejected = _count(status="rejected")
    failed = _count(status="failed")
    candidates = _count(status="candidate")
    attempted = verified + rejected + failed

    # Knowledge completion among verified stores.
    try:
        knowledge_done = db.table("shopify_store_index").select("id", count="exact")\
            .eq("status", "verified").not_.is_("knowledge_at", "null").execute().count or 0
    except Exception:
        knowledge_done = 0

    # ── Today ──
    discovered_today = _count_gte("discovered_at", today)
    verified_today = _count_gte("verified_at", today, status="verified")
    rejected_today = _count_gte("verified_at", today, status="rejected")
    attempted_today = verified_today + rejected_today
    knowledge_today = _count_gte("knowledge_at", today)

    # ── Category coverage + failure reasons (slim sample; PostgREST has no GROUP BY) ──
    categories: dict = {}
    low_conf_categories = 0
    reasons: dict = {}
    conf_sum = 0
    conf_n = 0
    cat_min = get_settings().shopify_index_category_min_confidence
    try:
        agg = db.table("shopify_store_index")\
            .select("status, category, category_confidence, rejection_reason")\
            .in_("status", ["verified", "rejected"])\
            .order("updated_at", desc=True).limit(5000).execute()
        for r in agg.data or []:
            if r.get("status") == "verified" and r.get("category"):
                categories[r["category"]] = categories.get(r["category"], 0) + 1
                cc = r.get("category_confidence")
                if cc is not None:
                    conf_sum += cc
                    conf_n += 1
                    if cc < cat_min:
                        low_conf_categories += 1
            if r.get("status") == "rejected" and r.get("rejection_reason"):
                reasons[r["rejection_reason"]] = reasons.get(r["rejection_reason"], 0) + 1
    except Exception as exc:
        logger.warning("index-ops aggregates failed: %s", exc)

    # ── Discovery sources + cursors ──
    sources: List[dict] = []
    try:
        cur = db.table("discovery_cursors")\
            .select("source, cursor, enabled, last_run_at, discovered").execute()
        sources = cur.data or []
    except Exception:
        pass  # table lands with migration 015

    # ── Index growth (last 14 daily runs) ──
    runs: List[dict] = []
    try:
        runs = db.table("store_index_runs")\
            .select("ran_at, trigger, processed, verified, rejected, failed")\
            .order("ran_at", desc=True).limit(14).execute().data or []
    except Exception:
        pass

    # ── Worker heartbeat: most recent verified/rejected stamp ──
    last_activity = None
    try:
        la = db.table("shopify_store_index").select("verified_at")\
            .not_.is_("verified_at", "null").order("verified_at", desc=True)\
            .limit(1).execute()
        if la and la.data:
            last_activity = la.data[0].get("verified_at")
    except Exception:
        pass

    _top = lambda d, n: sorted(d.items(), key=lambda kv: -kv[1])[:n]
    from app.services.runtime_config import get_config
    settings = get_settings()
    return {
        "data": {
            "pipeline": {
                "discovered": discovered,
                "candidates": candidates,
                "verified": verified,
                "rejected": rejected,
                "failed": failed,
                "knowledge_done": knowledge_done,
                "knowledge_pending": max(0, verified - knowledge_done),
            },
            "today": {
                "discovered": discovered_today,
                "verified": verified_today,
                "rejected": rejected_today,
                "knowledge": knowledge_today,
                "success_rate": round(verified_today / attempted_today * 100, 1) if attempted_today else None,
            },
            "success_rate": round(verified / attempted * 100, 1) if attempted else None,
            "avg_category_confidence": round(conf_sum / conf_n, 1) if conf_n else None,
            "low_confidence_categories": low_conf_categories,
            "category_min_confidence": cat_min,
            "knowledge_completion": round(knowledge_done / verified * 100, 1) if verified else None,
            "categories": [{"name": k, "count": v} for k, v in _top(categories, 14)],
            "top_failures": [{"reason": k, "count": v} for k, v in _top(reasons, 8)],
            "sources": sources,
            "runs": runs,
            "worker": {
                "enabled": bool(get_config("shopify_index_enabled", settings.shopify_index_enabled)),
                "last_activity": last_activity,
            },
        }
    }


# ── Store Inspector — one indexed store, everything we know + re-run actions ──

@router.get("/admin/store-inspector/{domain}")
def store_inspector(domain: str, x_admin_token: Optional[str] = Header(default=None)):
    _require_admin(x_admin_token)
    from app.services.store_index import normalize_domain, graph_neighbors
    db = get_supabase()
    domain = normalize_domain(domain)

    try:
        res = db.table("shopify_store_index").select("*").eq("domain", domain).maybe_single().execute()
        row = res.data if res else None
    except Exception as exc:
        logger.warning("store-inspector fetch failed for %s: %s", domain, exc)
        raise HTTPException(status_code=404, detail="not found")
    if not row:
        raise HTTPException(status_code=404, detail="not found")

    # Relationship-graph foundation — neighbors if any edges exist (placeholder-safe).
    related: List[dict] = []
    try:
        neighbors = graph_neighbors(db, [domain], limit=8)
        related = [{"domain": d, "weight": w} for d, w in
                   sorted(neighbors.items(), key=lambda kv: -kv[1]) if w > 0][:8]
    except Exception:
        pass

    return {"data": {"store": row, "related": related}}


class InspectorActionBody(BaseModel):
    action: str  # "reverify" | "reclassify"


@router.post("/admin/store-inspector/{domain}/action")
def store_inspector_action(domain: str, body: InspectorActionBody,
                           x_admin_token: Optional[str] = Header(default=None)):
    """Re-run verification (re-fetches storefront via the web process) or
    re-run knowledge (re-classifies from stored signals) for one store."""
    _require_admin(x_admin_token)
    from app.services.store_index import normalize_domain, run_knowledge, verify_and_store
    db = get_supabase()
    domain = normalize_domain(domain)

    if body.action == "reverify":
        try:
            row = db.table("shopify_store_index").select("source, source_query")\
                .eq("domain", domain).maybe_single().execute()
            src = (row.data or {}).get("source") if row else None
            sq = (row.data or {}).get("source_query") if row else None
        except Exception:
            src, sq = None, None
        result = verify_and_store(db, domain, src or "admin_reverify", sq)
        return {"data": result}

    if body.action == "reclassify":
        try:
            row = db.table("shopify_store_index").select(
                "domain, brand_name, homepage_message, description, product_types, "
                "product_titles, tags, collections, pricing_tier, product_count, "
                "median_price, min_price, max_price, price_bands").eq("domain", domain)\
                .maybe_single().execute()
        except Exception:
            row = None
        if not row or not row.data:
            raise HTTPException(status_code=404, detail="not found")
        result = run_knowledge(db, row.data)
        return {"data": result}

    raise HTTPException(status_code=422, detail="unknown action")


class SeedBody(BaseModel):
    urls: List[str]


@router.post("/admin/store-index/seed")
def seed_store_index(body: SeedBody, x_admin_token: Optional[str] = Header(default=None)):
    _require_admin(x_admin_token)
    from app.services.store_index import normalize_domain

    db = get_supabase()
    domains = [normalize_domain(u) for u in body.urls]
    domains = list(dict.fromkeys(d for d in domains if d and "." in d))[:200]
    if not domains:
        return {"inserted": 0, "duplicates": 0}

    try:
        existing = db.table("shopify_store_index").select("domain").in_("domain", domains).execute()
        seen = {r["domain"] for r in (existing.data or [])}
    except Exception as exc:
        logger.error("seed: existing-domain lookup failed (migration applied?): %s", exc)
        raise HTTPException(status_code=500, detail="shopify_store_index table unavailable — apply migration 007")

    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {"domain": d, "status": "candidate", "source": "seed", "created_at": now, "updated_at": now}
        for d in domains if d not in seen
    ]
    if rows:
        db.table("shopify_store_index").insert(rows).execute()
    return {"inserted": len(rows), "duplicates": len(domains) - len(rows)}


class RunBody(BaseModel):
    limit: int = 10


@router.post("/admin/store-index/run")
def run_store_index(body: RunBody, x_admin_token: Optional[str] = Header(default=None)):
    """Small manual indexing run for testing. Runs synchronously via Celery
    if available, otherwise inline — force=True bypasses the enabled flag,
    caps and politeness still apply."""
    _require_admin(x_admin_token)
    limit = max(1, min(body.limit, 25))

    from app.tasks.store_index import discover_shopify_stores_daily
    try:
        # Prefer async via Celery so the HTTP request returns fast…
        task = discover_shopify_stores_daily.delay(limit_override=limit, force=True)
        return {"status": "queued", "task_id": str(task.id), "limit": limit}
    except Exception as exc:
        # …but run inline when no broker is reachable (local/dev testing)
        logger.warning("store-index run: Celery unavailable (%s) — running inline", exc)
        result = discover_shopify_stores_daily(limit_override=limit, force=True)
        return {"status": "completed_inline", "result": result, "limit": limit}


# ── Runtime engine controls — flip toggles/limits without a redeploy ────────

@router.get("/admin/config")
def get_admin_config(x_admin_token: Optional[str] = Header(default=None)):
    """Effective values of the runtime-configurable engine knobs."""
    _require_admin(x_admin_token)
    from app.services.runtime_config import get_all
    return {"data": get_all()}


class ConfigBody(BaseModel):
    # All optional — only sent keys are updated; unknown keys are ignored.
    shopify_index_enabled: Optional[bool] = None
    shopify_index_daily_verified_target: Optional[int] = None
    shopify_index_daily_candidate_limit: Optional[int] = None
    lead_engine_enabled: Optional[bool] = None
    lead_engine_daily_target: Optional[int] = None
    lead_engine_min_qualification: Optional[int] = None


@router.put("/admin/config")
def update_admin_config(body: ConfigBody, x_admin_token: Optional[str] = Header(default=None)):
    """Override engine knobs. Takes effect within ~15s (worker cache window);
    no redeploy or restart. Env vars remain the defaults for a fresh deploy."""
    _require_admin(x_admin_token)
    from app.services.runtime_config import set_config
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail="nothing to update")
    return {"data": set_config(updates)}
