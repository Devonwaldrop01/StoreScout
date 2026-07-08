"""
Daily lead discovery worker (internal growth engine — never customer-facing).

Pipeline per store, reusing the verified Shopify index end to end:
  verified index row → research (index-only) → qualify → score →
  outreach angle + email draft → lead_prospects row, status 'ready'

Optimizes for QUALITY: it walks the freshest verified stores, skips anything
below the qualification threshold, and stops once the daily target of
high-quality prospects is reached — never "process 500 mediocre ones".
Disabled by default (LEAD_ENGINE_ENABLED); the admin dashboard can force
small manual runs. Zero new store-facing requests — all research reads the
index; the only network calls are the outreach-draft generations.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from .celery_app import celery
from app.core.config import get_settings
from app.core.database import get_supabase
from app.services.lead_engine import (
    generate_outreach,
    qualify_and_score,
    research_prospect,
)

logger = logging.getLogger(__name__)

_POOL_MULTIPLIER = 5  # examine up to target×5 stores to find target keepers


@celery.task(name="app.tasks.lead_engine.discover_leads_daily")
def discover_leads_daily(limit_override: Optional[int] = None, force: bool = False) -> dict:
    settings = get_settings()
    from app.services.runtime_config import get_config
    if not get_config("lead_engine_enabled", settings.lead_engine_enabled) and not force:
        logger.info("lead engine disabled (toggle off) — skipping run")
        return {"status": "disabled"}

    # Distributed lock — same pattern as the index worker
    try:
        import redis as redis_lib
        _r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
        if not _r.set("lock:lead_engine_daily", "1", nx=True, ex=3600):
            logger.info("lead engine run already in progress — skipping")
            return {"status": "skipped_lock"}
    except Exception as exc:
        logger.warning("lead engine: Redis unavailable (%s) — running without lock", exc)

    db = get_supabase()
    target = max(1, min(limit_override or get_config("lead_engine_daily_target", settings.lead_engine_daily_target), 50))
    min_qual = get_config("lead_engine_min_qualification", settings.lead_engine_min_qualification)

    # Domains already in the pipeline (any stage) are never re-prospected
    try:
        existing_res = db.table("lead_prospects").select("domain").limit(10000).execute()
        existing = {r["domain"] for r in (existing_res.data or [])}
    except Exception as exc:
        logger.error("lead engine: lead_prospects unavailable (migration 009 applied?): %s", exc)
        return {"status": "error", "reason": "lead_prospects table unavailable"}

    # Candidate pool: freshest verified stores not yet prospected
    try:
        pool_res = db.table("shopify_store_index")\
            .select("domain, brand_name, category, subcategory, country, language, business_stage, "
                    "pricing_tier, product_count, median_price, promo_rate, verification_confidence, description")\
            .eq("status", "verified")\
            .order("last_verified_at", desc=True)\
            .limit(target * _POOL_MULTIPLIER + len(existing))\
            .execute()
        pool = [s for s in (pool_res.data or []) if s["domain"] not in existing][: target * _POOL_MULTIPLIER]
    except Exception as exc:
        logger.error("lead engine: store index pool fetch failed: %s", exc)
        return {"status": "error", "reason": "store index unavailable"}

    created = 0
    examined = 0
    below_threshold = 0
    draft_failures = 0

    for store in pool:
        if created >= target:
            break
        examined += 1

        research = research_prospect(db, store)
        scored = qualify_and_score(db, store, research)

        if scored["qualification_score"] < min_qual:
            below_threshold += 1
            continue

        outreach = generate_outreach(store, research) or {}
        if not outreach:
            draft_failures += 1  # still a good prospect — save without draft

        now = datetime.now(timezone.utc).isoformat()
        row = {
            "domain": store["domain"],
            "brand_name": store.get("brand_name"),
            "category": store.get("category"),
            "subcategory": store.get("subcategory"),
            "country": store.get("country"),
            "business_stage": store.get("business_stage"),
            "pricing_tier": store.get("pricing_tier"),
            "lead_score": scored["lead_score"],
            "qualification_score": scored["qualification_score"],
            "score_reasons": scored["score_reasons"],
            "disqualifiers": scored["disqualifiers"],
            "outreach_status": "ready" if outreach else "research_complete",
            "research_status": "complete",
            "competitors_found": research["competitors_found"],
            "tracked_in_index": True,
            "generated_insights": {
                "findings": research["findings"],
                "competitors": research["competitors"],
                "market": research["market"],
            },
            "recommended_angle": outreach.get("angle"),
            "suggested_subject": outreach.get("subject"),
            "suggested_email": outreach.get("email"),
            "created_at": now,
            "updated_at": now,
        }
        try:
            db.table("lead_prospects").insert(row).execute()
            created += 1
        except Exception as exc:
            logger.warning("lead engine: insert failed for %s: %s", store["domain"], exc)

    summary = {
        "status": "ok",
        "created": created,
        "target": target,
        "examined": examined,
        "below_threshold": below_threshold,
        "draft_failures": draft_failures,
        "pool_size": len(pool),
    }
    logger.info(
        "lead engine run: %(created)d/%(target)d prospects created — %(examined)d examined, "
        "%(below_threshold)d below threshold, %(draft_failures)d draft failures, pool %(pool_size)d",
        summary,
    )
    return summary
