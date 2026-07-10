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
    assess_fit_ai,
    generate_outreach,
    research_prospect,
    score_lead_fit,
)

logger = logging.getLogger(__name__)

_POOL_MULTIPLIER = 5  # examine up to target×5 stores to find target keepers


@celery.task(name="app.tasks.lead_engine.scan_intent_signals")
def scan_intent_signals(limit_override: Optional[int] = None, force: bool = False) -> dict:
    """
    Phase 2: capture inbound buying-intent from public discussions. Fetches
    Reddit (via the web process), scores each post's intent, extracts a store
    domain when the poster linked one, and stores signals. High-intent posts
    with an extractable domain are flagged for promotion into the lead pipeline.
    Disabled by default (INTENT_ENGINE_ENABLED).
    """
    settings = get_settings()
    from app.services.runtime_config import get_config
    if not get_config("intent_engine_enabled", settings.intent_engine_enabled) and not force:
        return {"status": "disabled"}

    from app.services.intent_signals import fetch_reddit_via_web, score_intent, extract_domain

    db = get_supabase()
    min_score = get_config("intent_min_score", settings.intent_min_score)
    per_query = max(5, min(limit_override or 15, 40))

    posts = fetch_reddit_via_web(per_query)
    if not posts:
        return {"status": "ok", "fetched": 0, "created": 0, "note": "no posts (source blocked or empty)"}

    # Skip anything we've already captured.
    ext_ids = [p["external_id"] for p in posts if p.get("external_id")]
    seen = set()
    try:
        ex = db.table("intent_signals").select("external_id").in_("external_id", ext_ids).execute()
        seen = {r["external_id"] for r in (ex.data or [])}
    except Exception as exc:
        logger.error("intent scan: table unavailable (migration 019?): %s", exc)
        return {"status": "error", "reason": "intent_signals table unavailable"}

    from datetime import datetime as _dt
    created = 0
    high = 0
    for p in posts:
        if p["external_id"] in seen:
            continue
        scored = score_intent(p.get("title", ""), p.get("body", ""))
        if scored["score"] < min_score:
            continue
        domain = extract_domain(f"{p.get('title','')} {p.get('body','')}")
        posted = None
        if p.get("created_utc"):
            try:
                posted = _dt.utcfromtimestamp(float(p["created_utc"])).isoformat()
            except Exception:
                posted = None
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "source": "reddit", "external_id": p["external_id"],
            "title": p.get("title"), "quote": (p.get("body") or p.get("title") or "")[:1000],
            "author": p.get("author"), "url": p.get("url"), "channel": p.get("channel"),
            "intent_score": scored["score"], "intent_reason": scored["reason"],
            "matched_domain": domain, "status": "new",
            "created_at": now, "posted_at": posted, "updated_at": now,
        }
        try:
            db.table("intent_signals").insert(row).execute()
            created += 1
            if scored["score"] >= 75:
                high += 1
        except Exception as exc:
            logger.debug("intent insert failed for %s: %s", p["external_id"], exc)

    logger.info("intent scan: %d fetched, %d signals created (%d high-intent)", len(posts), created, high)
    return {"status": "ok", "fetched": len(posts), "created": created, "high_intent": high}


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
        _cols = ("domain, brand_name, category, subcategory, country, language, business_stage, "
                 "pricing_tier, product_count, median_price, promo_rate, verification_confidence, description, "
                 "tech_signals, contact_email, contact_source, sells_wholesale, multi_market")
        try:
            pool_res = db.table("shopify_store_index").select(_cols)\
                .eq("status", "verified").order("last_verified_at", desc=True)\
                .limit(target * _POOL_MULTIPLIER + len(existing)).execute()
        except Exception:
            # Pre-migration-018 fallback (no commercial-signal columns yet).
            pool_res = db.table("shopify_store_index")\
                .select("domain, brand_name, category, subcategory, country, language, business_stage, "
                        "pricing_tier, product_count, median_price, promo_rate, verification_confidence, description")\
                .eq("status", "verified").order("last_verified_at", desc=True)\
                .limit(target * _POOL_MULTIPLIER + len(existing)).execute()
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
        scored = score_lead_fit(db, store, research)

        # Cheap heuristic gate first — only spend an AI call on plausible fits.
        if scored["fit_tier"] == "not_a_fit":
            below_threshold += 1
            continue

        # Individualized AI verdict: fold sophistication into the score and let
        # the model veto a clear non-fit the heuristics missed.
        verdict = assess_fit_ai(store, research)
        fit_score = min(100, scored["fit_score"] + verdict["sophistication_points"])
        tier = scored["fit_tier"]
        if verdict["disqualify"]:
            tier, fit_score = "not_a_fit", min(fit_score, 30)
            scored["disqualifiers"].append("AI verdict: clear non-fit for StoreScout")
        elif fit_score >= 75 and store.get("contact_email"):
            tier = "hot"
        elif fit_score >= 55:
            tier = "warm" if tier != "hot" else "hot"

        if tier == "not_a_fit":
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
            "lead_score": fit_score,
            "qualification_score": fit_score,
            "fit_tier": tier,
            "fit_reasoning": verdict["reasoning"],
            "contact_email": store.get("contact_email"),
            "contact_source": store.get("contact_source"),
            "tech_signals": store.get("tech_signals"),
            "score_breakdown": scored["score_breakdown"],
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
        # Insert with graceful fallback if migration 018 columns aren't applied.
        try:
            db.table("lead_prospects").insert(row).execute()
            created += 1
        except Exception as exc:
            _new = ("fit_tier", "fit_reasoning", "contact_email", "contact_source",
                    "tech_signals", "score_breakdown")
            slim = {k: v for k, v in row.items() if k not in _new}
            try:
                db.table("lead_prospects").insert(slim).execute()
                created += 1
            except Exception as exc2:
                logger.warning("lead engine: insert failed for %s: %s", store["domain"], exc2)

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
