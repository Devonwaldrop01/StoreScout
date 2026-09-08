"""
Background Shopify store index worker.

Continuously discovers, verifies, lightly scans, classifies, and stores
Shopify stores into shopify_store_index â€” StoreScout's compounding
proprietary store database. Deliberately polite and cheap:

  Â· disabled by default (SHOPIFY_INDEX_ENABLED)
  Â· daily candidate cap (SHOPIFY_INDEX_DAILY_CANDIDATE_LIMIT)
  Â· domains are processed once; verified rows re-checked on a 60-day
    cycle capped at 10/day â€” nothing gets hammered repeatedly
  Â· â‰¤4 requests per domain, low thread concurrency, retries with backoff
  Â· fetches run on the WEB process via /internal/store-index/process
    (same IP-reputation pattern as the tracked-competitor scanner)

Tracked competitors are never touched by this worker.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import httpx

from .celery_app import celery
from .index_hold import IndexTask
from app.core.config import get_settings
from app.core.database import get_supabase
from app.services.scheduler_status import scheduled_index_task
from app.services.store_index import SEED_QUERIES, normalize_domain, run_knowledge

logger = logging.getLogger(__name__)

_REVERIFY_DAYS = 60       # verified rows get a fresh pass on this cycle
_REVERIFY_DAILY_CAP = 10


def _process_via_web(domain: str, source: str, source_query: Optional[str]) -> dict:
    from app.services.verification_delivery import verify_via_web
    return verify_via_web(domain, source, source_query, endpoint="process")


def _verify_via_web(domain: str, source: str, source_query: Optional[str]) -> dict:
    from app.services.verification_delivery import verify_via_web
    return verify_via_web(domain, source, source_query)


@celery.task(base=IndexTask, name="app.tasks.store_index.verification_canary_wave")
def verification_canary_wave(wave: str = "sentinel") -> dict:
    """Manual only. No Beat entry, implicit arming, acquisition or paid AI."""
    from app.core.index_hold import require_index_writes
    require_index_writes()
    import asyncio
    import json
    from app.services.verification_canary import load_manifest
    from app.services.verification_delivery import deliver
    settings = get_settings()
    if not settings.store_index_canary_enabled:
        return {"status": "disabled"}
    if wave not in {"sentinel", "remaining"}:
        raise ValueError("invalid canary wave")
    manifest, digest = load_manifest(settings)
    entries = manifest["stores"][:3] if wave == "sentinel" else manifest["stores"][3:]
    results = []
    for entry in entries:
        result = asyncio.run(deliver(
            f"{settings.api_internal_url}/api/v1/internal/store-index/canary/verify",
            {"domain": entry["domain"], "manifest_sha256": digest},
            {"x-internal-token": settings.internal_secret},
        ))
        results.append(result)
        logger.info("[CANARY] %s", json.dumps(result))
        if result.get("reason") == "web_unreachable" or result.get("canary_state") != "ready":
            break
    return {"status": "stopped", "wave": wave, "results": results}


@celery.task(base=IndexTask, name="app.tasks.store_index.stage_discovery")
@scheduled_index_task("stage_discovery")
def stage_discovery(limit_override: Optional[int] = None, force: bool = False) -> dict:
    """
    Stage 1. Cheap + bulk. For sources that yield raw refs needing resolution
    (Shop App), harvest thousands of refs straight into the discovery_queue with
    NO per-store fetches â€” this is what lets the discovered universe scale to
    100k+. For sources that already yield real domains, insert them straight
    into shopify_store_index as 'discovered'. Resumable per-source cursor.
    """
    from app.services.runtime_config import get_config
    from app.services.discovery_sources import all_sources

    settings = get_settings()
    if not get_config("shopify_index_enabled", settings.shopify_index_enabled) and not force:
        return {"status": "disabled"}

    db = get_supabase()
    harvest_batch = max(1, min(limit_override or get_config(
        "shopify_index_harvest_batch", settings.shopify_index_harvest_batch), 5000))
    now = datetime.now(timezone.utc).isoformat()

    totals = {"queued": 0, "discovered": 0, "duplicates": 0}
    by_source: dict = {}

    for source in all_sources():
        cursor = None
        enabled = True
        try:
            cur = db.table("discovery_cursors").select("cursor, enabled")\
                .eq("source", source.name).maybe_single().execute()
            if cur and cur.data:
                cursor = cur.data.get("cursor")
                enabled = cur.data.get("enabled", True)
        except Exception:
            pass
        if not enabled:
            continue

        added = 0
        if getattr(source, "needs_resolution", False):
            # â”€â”€ Bulk harvest raw refs into the discovery_queue (cheap) â”€â”€
            try:
                refs, next_cursor = source.harvest(cursor, harvest_batch)
            except Exception as exc:
                logger.warning("harvest %s failed: %s", source.name, exc)
                continue
            if refs:
                rows = [{"source": source.name, "ref": r, "status": "pending",
                         "discovered_at": now, "updated_at": now}
                        for r in dict.fromkeys(refs)]
                try:
                    # upsert on (source, ref) so re-harvested refs don't error
                    res = db.table("discovery_queue").upsert(
                        rows, on_conflict="source,ref", ignore_duplicates=True).execute()
                    added = len(res.data or [])
                except Exception as exc:
                    logger.warning("discovery_queue insert (%s) failed: %s", source.name, exc)
            totals["queued"] += added
        else:
            # â”€â”€ Source yields real domains â†’ straight to index 'discovered' â”€â”€
            try:
                domains, next_cursor = source.fetch(cursor, harvest_batch)
            except Exception as exc:
                logger.warning("discovery source %s fetch failed: %s", source.name, exc)
                continue
            if domains:
                try:
                    existing = db.table("shopify_store_index").select("domain")\
                        .in_("domain", domains).execute()
                    seen = {r["domain"] for r in (existing.data or [])}
                except Exception:
                    seen = set()
                rows = [{"domain": d, "status": "discovered", "discovery_source": source.name,
                         "source": source.name, "discovered_at": now,
                         "created_at": now, "updated_at": now}
                        for d in dict.fromkeys(domains) if d not in seen]
                if rows:
                    try:
                        db.table("shopify_store_index").insert(rows).execute()
                        added = len(rows)
                    except Exception as exc:
                        logger.warning("discovery insert (%s) failed: %s", source.name, exc)
            totals["discovered"] += added

        by_source[source.name] = added
        try:
            db.table("discovery_cursors").upsert({
                "source": source.name, "cursor": next_cursor,
                "last_run_at": now, "updated_at": now,
            }, on_conflict="source").execute()
        except Exception as exc:
            logger.debug("discovery cursor persist (%s) skipped: %s", source.name, exc)

    logger.info("stage_discovery: queued %d, discovered %d %s",
                totals["queued"], totals["discovered"], by_source)
    return {"status": "ok", **totals, "by_source": by_source}


# â”€â”€ Stage 1.5: RESOLUTION â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Turn queued raw refs (shop.app/m/{handle}) into real merchant domains and
# promote them into the index as 'discovered'. This is the rate-limited step,
# isolated from cheap discovery and paced so it never bursts.

@celery.task(base=IndexTask, name="app.tasks.store_index.stage_resolution")
@scheduled_index_task("stage_resolution")
def stage_resolution(limit_override: Optional[int] = None, force: bool = False) -> dict:
    from app.services.runtime_config import get_config
    settings = get_settings()
    if not get_config("shopify_index_enabled", settings.shopify_index_enabled) and not force:
        return {"status": "disabled"}

    db = get_supabase()
    batch = max(1, min(limit_override or get_config(
        "shopify_index_resolve_batch", settings.shopify_index_resolve_batch), 60))
    now = datetime.now(timezone.utc).isoformat()

    try:
        res = db.table("discovery_queue").select("id, ref, attempts")\
            .eq("status", "pending").eq("source", "shop_app")\
            .order("discovered_at").limit(batch).execute()
        pending = res.data or []
    except Exception as exc:
        logger.error("stage_resolution: queue fetch failed (apply migration 017): %s", exc)
        return {"status": "error", "resolved": 0}

    if not pending:
        return {"status": "ok", "resolved": 0, "note": "queue_empty"}

    refs = [p["ref"] for p in pending]
    # Rate-limited resolution runs on the web process.
    url = f"{settings.api_internal_url}/api/v1/internal/shop-app-resolve"
    stats: dict = {}
    try:
        resp = httpx.post(url, json={"refs": refs},
                          headers={"x-internal-token": settings.internal_secret}, timeout=180.0)
        body = resp.json() if resp.status_code == 200 else {}
        resolved = body.get("resolved", [])
        stats = body.get("stats", {}) or {}
    except Exception as exc:
        logger.warning("stage_resolution: resolve call failed: %s", exc)
        resolved = []

    ref_to_domain = {r["ref"]: r["domain"] for r in resolved if r.get("domain")}

    # Promote resolved domains into the index as 'discovered'; dedupe first.
    domains = list(dict.fromkeys(ref_to_domain.values()))
    seen = set()
    if domains:
        try:
            ex = db.table("shopify_store_index").select("domain").in_("domain", domains).execute()
            seen = {r["domain"] for r in (ex.data or [])}
        except Exception:
            seen = set()
        new_rows = [{"domain": d, "status": "discovered", "discovery_source": "shop_app",
                     "source": "shop_app", "discovered_at": now, "created_at": now, "updated_at": now}
                    for d in domains if d not in seen]
        if new_rows:
            try:
                db.table("shopify_store_index").insert(new_rows).execute()
            except Exception as exc:
                logger.warning("stage_resolution: index insert failed: %s", exc)

    # Update the queue rows: resolved (success) or bump attempts / fail.
    promoted = 0
    for p in pending:
        ref = p["ref"]
        if ref in ref_to_domain:
            try:
                db.table("discovery_queue").update({
                    "status": "resolved", "resolved_domain": ref_to_domain[ref],
                    "resolved_at": now, "updated_at": now,
                }).eq("id", p["id"]).execute()
                promoted += 1
            except Exception:
                pass
        else:
            attempts = (p.get("attempts") or 0) + 1
            try:
                db.table("discovery_queue").update({
                    "attempts": attempts,
                    "status": "failed" if attempts >= 4 else "pending",
                    "updated_at": now,
                }).eq("id", p["id"]).execute()
            except Exception:
                pass

    new_count = len([d for d in domains if d not in seen])
    logger.info("stage_resolution: %d/%d refs resolved â†’ %d new index rows (rate_limited=%s)",
                promoted, len(pending), new_count, stats.get("rate_limited"))
    return {"status": "ok", "processed": len(pending), "resolved": promoted,
            "new_domains": new_count, "rate_limited": stats.get("rate_limited"),
            "no_domain": stats.get("no_domain")}


# â”€â”€ Stage 2: VERIFICATION â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Turn DISCOVERED domains into VERIFIED or REJECTED (with a reason). Fetches
# run on the web process. Chunked so the shared worker stays within memory.

@celery.task(base=IndexTask, name="app.tasks.store_index.stage_verification")
@scheduled_index_task("stage_verification")
def stage_verification(limit_override: Optional[int] = None, force: bool = False) -> dict:
    from app.services.verification_lifecycle import plan_verification, RENEW_AFTER, timestamp
    from app.services.runtime_config import get_config
    settings = get_settings()
    if not get_config("shopify_index_enabled", settings.shopify_index_enabled) and not force:
        return {"status": "disabled"}

    db = get_supabase()
    batch = max(1, min(limit_override or get_config(
        "shopify_index_verify_batch", settings.shopify_index_verify_batch), 200))
    concurrency = max(1, min(settings.shopify_index_concurrency, 4))

    now = datetime.now(timezone.utc)
    try:
        rows = []
        # Reserve supply from every lifecycle lane. No category/confidence
        # filter: unclassified rows must make progress as well.
        for statuses in (["discovered"], ["candidate"], ["failed", "rejected"], ["verified"]):
            q = db.table("shopify_store_index").select(
                "domain, source, source_query, status, created_at, updated_at, last_verified_at, "
                "next_verification_at, last_attempted_at, verification_attempts, catalog_observation"
            ).in_("status", statuses)
            if statuses == ["verified"]:
                q = q.or_(f"next_verification_at.lte.{now.isoformat()},and(next_verification_at.is.null,last_verified_at.lte.{(now - RENEW_AFTER).isoformat()}),and(next_verification_at.is.null,last_verified_at.is.null)")
            else:
                q = q.or_(f"next_verification_at.is.null,next_verification_at.lte.{now.isoformat()}")
            rows.extend(q.order("next_verification_at", nullsfirst=True).order("created_at").order("domain").limit(batch).execute().data or [])
        rows = plan_verification(rows, now, batch)
    except Exception as exc:
        logger.error("stage_verification: discovered/candidate fetch failed: %s", exc)
        return {"status": "error", "verified": 0}

    if not rows:
        return {"status": "ok", "processed": 0, "verified": 0, "rejected": 0,
                "failed": 0, "reverified": 0, "note": "queue_empty"}

    from app.services.index_lease import current_lease
    lease = current_lease.get()

    def dispatch(row):
        # ContextVars are not inherited by executor threads: capture explicitly.
        if lease is not None:
            lease.require()
        return _verify_via_web(row["domain"], row.get("source") or "unknown", row.get("source_query"))

    work = rows
    counts = {"verified": 0, "rejected": 0, "failed": 0, "reverified": 0, "skipped": 0}
    successful_catalogs = 0
    storefront_attempts = 0
    delivery_unknown = 0
    reasons: dict = {}
    # Chunk the batch so the worker never holds too many results at once.
    chunk = max(concurrency * 5, 10)
    for i in range(0, len(work), chunk):
        part = work[i:i + chunk]
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            results = list(pool.map(
                dispatch,
                part,
            ))
        for row, r in zip(part, results):
            if r.get("reason") == "web_unreachable":
                delivery_unknown += 1
                # Delivery failure isn't a storefront attempt. CAS prevents an
                # ambiguous HTTP timeout from undoing a successful web write.
                q = db.table("shopify_store_index").update({
                    "next_verification_at": (now + timedelta(hours=1)).isoformat(),
                    "updated_at": now.isoformat(),
                }).eq("domain", row["domain"])
                q = q.eq("updated_at", row["updated_at"]) if row.get("updated_at") else q.is_("updated_at", "null")
                q.execute()
            outcome = r.get("outcome", "failed")
            if outcome == "verified" and r.get("reverified"):
                outcome = "reverified"
            counts[outcome] = counts.get(outcome, 0) + 1
            successful_catalogs += r.get("successful_catalogs", int(outcome in {"verified", "reverified"}))
            storefront_attempts += bool(r.get("attempted"))
            if r.get("reason"):
                reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1

    logger.info("stage_verification: %d attempted â†’ %d verified, %d rejected, %d failed %s",
                len(work), counts["verified"], counts["rejected"], counts["failed"], reasons)
    # Keep renewals separate from first successful verifications; HTTP delivery
    # failures are not confirmed storefront attempts.
    return {"status": "ok", "processed": len(work) - counts["skipped"],
            **counts, "rejection_reasons": reasons, "attempt_reasons": reasons,
            "successful_catalogs": successful_catalogs,
            "confirmed_storefront_attempts": storefront_attempts,
            "delivery_outcome_unknown": delivery_unknown,
            "oldest_queue_age_days": max(((now - timestamp(r["created_at"])).total_seconds() / 86400
                                            for r in work if timestamp(r.get("created_at"))), default=0),
            "selected_by_status": {s: sum(r.get("status") == s for r in work)
                                   for s in {r.get("status") for r in work}}}


# â”€â”€ Stage 3: KNOWLEDGE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Runs ONLY on verified stores and ONLY on their stored signals â€” no network.
# Because there is no storefront fetch, it runs directly in the worker.

@celery.task(base=IndexTask, name="app.tasks.store_index.stage_knowledge")
@scheduled_index_task("stage_knowledge")
def stage_knowledge(limit_override: Optional[int] = None, force: bool = False) -> dict:
    from app.services.runtime_config import get_config
    settings = get_settings()
    if not get_config("shopify_index_enabled", settings.shopify_index_enabled) and not force:
        return {"status": "disabled"}

    db = get_supabase()
    batch = max(1, min(limit_override or get_config(
        "shopify_index_knowledge_batch", settings.shopify_index_knowledge_batch), 300))

    _full_cols = ("domain, category, subcategory, category_confidence, category_evidence, brand_keywords, target_customer, store_dna, dna_keywords, dna_signature, dna_at, brand_name, homepage_message, description, product_types, "
                  "product_titles, tags, collections, pricing_tier, product_count, "
                  "median_price, min_price, max_price, price_bands, catalog_observation")
    # product_titles (016) may lag behind 015 â€” fall back to a select without it
    # so knowledge still runs (it just loses the product-title signal).
    _fallback_cols = ("domain, category, subcategory, category_confidence, category_evidence, brand_keywords, target_customer, store_dna, dna_keywords, dna_signature, dna_at, brand_name, homepage_message, description, product_types, "
                      "tags, collections, pricing_tier, product_count, "
                      "median_price, min_price, max_price, price_bands, catalog_observation")
    rows = []
    for cols in (_full_cols, _fallback_cols):
        try:
            res = db.table("shopify_store_index")\
                .select(cols)\
                .eq("status", "verified")\
                .is_("knowledge_at", "null")\
                .or_("catalog_observation->>classification_retry_at.is.null,catalog_observation->>classification_retry_at.lte." + datetime.now(timezone.utc).isoformat())\
                .order("verified_at")\
                .limit(batch).execute()
            rows = res.data or []
            break
        except Exception as exc:
            if cols is _full_cols:
                logger.warning("stage_knowledge: full select failed (%s) â€” retrying without product_titles", exc)
                continue
            logger.error("stage_knowledge: verified fetch failed (apply migration 015): %s", exc)
            return {"status": "error", "classified": 0}

    if not rows:
        return {"status": "ok", "processed": 0, "classified": 0, "note": "queue_empty"}

    classified = 0
    low_conf = 0
    cat_min = get_config("shopify_index_category_min_confidence", settings.shopify_index_category_min_confidence)
    for row in rows:
        try:
            out = run_knowledge(db, row)
            if out.get("status") == "superseded":
                continue
            classified += 1
            if (out.get("confidence") or 0) < cat_min:
                low_conf += 1
        except Exception as exc:
            logger.warning("stage_knowledge: %s failed: %s", row.get("domain"), exc)

    logger.info("stage_knowledge: %d attempted â†’ %d classified (%d below category threshold)",
                len(rows), classified, low_conf)
    # processed = rows attempted; classified = those that produced a category.
    return {"status": "ok", "processed": len(rows), "classified": classified,
            "below_threshold": low_conf}


@celery.task(base=IndexTask, name="app.tasks.store_index.generate_niche_candidates")
def generate_niche_candidates(query: str, target: int = 20) -> dict:
    """Ask Haiku for ~20 DTC brand domains in a niche (platform-agnostic â€”
    verification is OUR job) and insert unseen ones as candidates."""
    from app.core.index_hold import require_index_writes
    require_index_writes()
    import json as _json
    import anthropic

    settings = get_settings()
    if not settings.anthropic_api_key:
        return {"status": "no_api_key", "inserted": 0}

    db = get_supabase()
    # StoreScout users compete against niche and growing brands, not Nike â€”
    # the index must represent the REAL Shopify ecosystem, so the generator
    # deliberately skews toward underdogs and category specialists.
    prompt = f"""You are mapping the DTC ecommerce landscape.

List {target} direct-to-consumer BRANDS a shopper would realistically buy from in this niche: {query}

Return ONLY valid JSON, no markdown fences:
{{"stores": [{{"domain": "example-brand.com", "name": "Example Brand"}}, ...]}}

Rules:
- domain must be the brand's own storefront domain (never marketplaces, social pages, or retailers like Amazon/Walmart/Target)
- STRONGLY favor niche, emerging, fast-growing, and mid-size independent brands â€” at most 3 household names in the whole list
- Include category specialists and underdogs a small store owner actually competes against
- Ignore what ecommerce platform they use â€” that is verified separately"""

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        stores = _json.loads(text).get("stores", [])
    except Exception as exc:
        logger.error("generate_niche_candidates(%r) Claude call failed: %s", query, exc)
        return {"status": "error", "inserted": 0}

    domains = [normalize_domain(s.get("domain", "")) for s in stores]
    domains = [d for d in domains if d and "." in d]
    if not domains:
        return {"status": "empty", "inserted": 0}

    # Skip anything already in the index (any status)
    try:
        existing = db.table("shopify_store_index").select("domain").in_("domain", domains).execute()
        seen = {r["domain"] for r in (existing.data or [])}
    except Exception:
        seen = set()

    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "domain": d,
            "status": "candidate",
            "source": "ai_niche_query",
            "source_query": query,
            "created_at": now,
            "updated_at": now,
        }
        for d in dict.fromkeys(domains)  # dedupe, keep order
        if d not in seen
    ]
    inserted = 0
    if rows:
        try:
            db.table("shopify_store_index").insert(rows).execute()
            inserted = len(rows)
        except Exception as exc:
            logger.warning("generate_niche_candidates insert failed: %s", exc)

    logger.info("generate_niche_candidates(%r): %d suggested, %d new candidates", query, len(domains), inserted)
    return {"status": "ok", "inserted": inserted, "suggested": len(domains)}


@celery.task(base=IndexTask, name="app.tasks.store_index.generate_related_candidates")
def generate_related_candidates(domain: str, brand_name: str = "", category: str = "", description: str = "", target: int = 12) -> dict:
    """
    Graph expansion: every verified store becomes a seed for discovering the
    brands around it. Ask Haiku for competitors/peers of a known store and
    insert unseen ones as candidates. The seed store's expanded_at is stamped
    so each store is expanded exactly once.
    """
    from app.core.index_hold import require_index_writes
    require_index_writes()
    import json as _json
    import anthropic

    settings = get_settings()
    if not settings.anthropic_api_key:
        return {"status": "no_api_key", "inserted": 0}

    db = get_supabase()
    who = brand_name or domain
    context = " Â· ".join(x for x in [category, (description or "")[:120]] if x)
    prompt = f"""You are mapping the competitive neighborhood of a DTC ecommerce brand.

Brand: {who} ({domain}){f" â€” {context}" if context else ""}

List {target} brands whose customers would ALSO consider {who} â€” direct competitors and close peers.

Return ONLY valid JSON, no markdown fences:
{{"stores": [{{"domain": "example-brand.com", "name": "Example Brand"}}, ...]}}

Rules:
- domain must be each brand's own storefront domain (never marketplaces or retailers)
- Prefer brands of a SIMILAR size and stage to {who} â€” peers first, giants last, at most 2 household names
- Ignore what ecommerce platform they use â€” that is verified separately"""

    inserted = 0
    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        stores = _json.loads(text).get("stores", [])

        domains = [normalize_domain(s.get("domain", "")) for s in stores]
        domains = [d for d in dict.fromkeys(domains) if d and "." in d and d != normalize_domain(domain)]
        if domains:
            try:
                existing = db.table("shopify_store_index").select("domain").in_("domain", domains).execute()
                seen = {r["domain"] for r in (existing.data or [])}
            except Exception:
                seen = set()
            now = datetime.now(timezone.utc).isoformat()
            rows = [
                {"domain": d, "status": "candidate", "source": "related_expansion",
                 "source_query": normalize_domain(domain), "created_at": now, "updated_at": now}
                for d in domains if d not in seen
            ]
            if rows:
                db.table("shopify_store_index").insert(rows).execute()
                inserted = len(rows)
    except Exception as exc:
        logger.error("generate_related_candidates(%s) failed: %s", domain, exc)
        return {"status": "error", "inserted": 0}
    finally:
        # Stamp even on failure â€” a store that errors during expansion should
        # not be retried every single day (guarded: column may not exist yet).
        try:
            db.table("shopify_store_index").update(
                {"expanded_at": datetime.now(timezone.utc).isoformat()}
            ).eq("domain", normalize_domain(domain)).execute()
        except Exception:
            pass

    logger.info("related expansion for %s: %d new candidates", domain, inserted)
    return {"status": "ok", "inserted": inserted}


@celery.task(base=IndexTask, name="app.tasks.store_index.generate_candidates_rotating")
@scheduled_index_task("stage_candidates")
def generate_candidates_rotating(limit_override: Optional[int] = None, force: bool = False) -> dict:
    """Proactively grow index BREADTH so it can cover almost any niche a user
    describes. Each run advances a cursor through the full niche list (â‰ˆ90
    taxonomy niches + seeds) and generates candidates for the next few, plus a
    couple of graph expansions off recently-verified stores. Candidates land as
    'candidate' and are drained by stage_verification. Gated + single-flight
    (via the decorator); no-ops unless the pipeline is enabled."""
    from app.services.runtime_config import get_config
    from app.services.store_index import niche_queries
    settings = get_settings()
    if not get_config("shopify_index_enabled", settings.shopify_index_enabled) and not force:
        return {"status": "disabled"}

    per_run = max(1, min(limit_override or get_config(
        "shopify_index_niche_per_run", settings.shopify_index_niche_per_run), 10))
    queries = niche_queries()
    inserted = 0
    used: list = []

    # Cursor rotates through EVERY niche over time (persisted in Redis; falls
    # back to a stable slice if Redis is down).
    start = 0
    try:
        import redis as _redis
        _r = _redis.from_url(settings.redis_url, socket_connect_timeout=2)
        start = int(_r.incrby("store_index:niche_cursor", per_run)) - per_run
    except Exception:
        pass
    for i in range(per_run):
        q = queries[(start + i) % len(queries)]
        try:
            out = generate_niche_candidates(q)
            inserted += int(out.get("inserted") or 0)
            used.append(q)
        except Exception as exc:
            logger.warning("generate_candidates_rotating: %r failed: %s", q, exc)

    # A little graph expansion too â€” peers of the freshest verified stores.
    try:
        db = get_supabase()
        recent = db.table("shopify_store_index")\
            .select("domain, brand_name, category, description")\
            .eq("status", "verified").is_("expanded_at", "null")\
            .order("verified_at", desc=True).limit(2).execute().data or []
        for r in recent:
            out = generate_related_candidates(
                r["domain"], r.get("brand_name") or "", r.get("category") or "", r.get("description") or "")
            inserted += int(out.get("inserted") or 0)
    except Exception as exc:
        logger.debug("generate_candidates_rotating: graph expansion skipped: %s", exc)

    logger.info("generate_candidates_rotating: %d candidates from %d niches %s", inserted, len(used), used)
    # 'processed' = candidates added, so it shows in the Worker Runs panel.
    return {"status": "ok", "processed": inserted, "discovered": inserted, "niches": used}


@celery.task(base=IndexTask, name="app.tasks.store_index.discover_shopify_stores_daily")
def discover_shopify_stores_daily(limit_override: Optional[int] = None, force: bool = False) -> dict:
    """
    Daily indexing run, optimized for NEW VERIFIED stores â€” not candidates
    processed. Works in small batches until the verified target is hit or the
    request budget runs out, topping up candidates graph-first (related-brand
    expansion of already-verified stores) and then via niche rotation.

    `force=True` is the admin test-run path: it bypasses the enabled flag and
    treats limit_override as both target and budget (a bounded small run).
    """
    from app.core.index_hold import require_index_writes
    require_index_writes()
    settings = get_settings()
    from app.services.runtime_config import get_config
    if not get_config("shopify_index_enabled", settings.shopify_index_enabled) and not force:
        logger.info("store index disabled (toggle off) â€” skipping run")
        return {"status": "disabled"}

    # Distributed lock â€” same pattern as enqueue_due_scans
    try:
        import redis as redis_lib
        _r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
        if not _r.set("lock:store_index_daily", "1", nx=True, ex=3600):
            logger.info("store index run already in progress â€” skipping")
            return {"status": "skipped_lock"}
    except Exception as exc:
        logger.warning("store index: Redis unavailable (%s) â€” running without lock", exc)
        _r = None

    db = get_supabase()
    if limit_override:
        verified_target = max(1, min(limit_override, 250))
        budget = verified_target
    else:
        verified_target = max(1, min(get_config("shopify_index_daily_verified_target", settings.shopify_index_daily_verified_target), 250))
        budget = max(verified_target, min(get_config("shopify_index_daily_candidate_limit", settings.shopify_index_daily_candidate_limit), 500))
    reverify_cutoff = (datetime.now(timezone.utc) - timedelta(days=_REVERIFY_DAYS)).isoformat()
    concurrency = max(1, min(settings.shopify_index_concurrency, 4))
    batch_size = max(concurrency * 5, 10)

    counts = {"verified": 0, "rejected": 0, "failed": 0}
    source_counts: dict = {}
    processed = 0
    skipped_duplicates = 0
    done_domains: set = set()
    topups_used = {"expansion": 0, "niche": 0}

    def _fetch_candidates(n: int) -> List[dict]:
        """Oldest unprocessed candidates, excluding this run's domains.
        Candidates are unprocessed by definition (processing always moves
        them to verified/rejected/failed)."""
        nonlocal skipped_duplicates
        try:
            res = db.table("shopify_store_index")\
                .select("domain, source, source_query")\
                .eq("status", "candidate")\
                .order("created_at")\
                .limit(n + len(done_domains))\
                .execute()
        except Exception as exc:
            logger.error("store index: candidate fetch failed (table missing?): %s", exc)
            return []
        out: List[dict] = []
        for r in res.data or []:
            d = normalize_domain(r["domain"])
            if d in done_domains:
                skipped_duplicates += 1
                continue
            out.append({**r, "domain": d})
            if len(out) >= n:
                break
        return out

    def _top_up() -> bool:
        """Generate more candidates. Graph expansion first (peers of already-
        verified stores â€” this is what compounds the ecosystem coverage),
        then niche-query rotation. Returns True if anything new landed."""
        # Related-brand expansion: up to 3 unexpanded verified stores per top-up
        if topups_used["expansion"] < 3:
            try:
                res = db.table("shopify_store_index")\
                    .select("domain, brand_name, category, description")\
                    .eq("status", "verified")\
                    .is_("expanded_at", "null")\
                    .order("last_verified_at", desc=True)\
                    .limit(3)\
                    .execute()
                seeds = res.data or []
            except Exception:
                seeds = []  # expanded_at column may not exist yet (migration 008)
            added = 0
            for s in seeds:
                topups_used["expansion"] += 1
                gen = generate_related_candidates(
                    s["domain"], s.get("brand_name") or "", s.get("category") or "", s.get("description") or ""
                )
                added += gen.get("inserted", 0)
            if added:
                return True

        # Niche rotation
        if topups_used["niche"] < 2:
            topups_used["niche"] += 1
            try:
                idx = 0
                if _r is not None:
                    idx = int(_r.incr("store_index:niche_rotation")) % len(SEED_QUERIES)
                gen = generate_niche_candidates(SEED_QUERIES[idx])
                return bool(gen.get("inserted"))
            except Exception as exc:
                logger.warning("store index: niche top-up failed: %s", exc)
        return False

    def _process_batch(batch: List[dict]) -> None:
        nonlocal processed
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            results = list(pool.map(
                lambda w: _process_via_web(w["domain"], w.get("source") or "unknown", w.get("source_query")),
                batch,
            ))
        for w, r in zip(batch, results):
            outcome = r.get("outcome", "failed")
            counts[outcome] = counts.get(outcome, 0) + 1
            src = w.get("source") or "unknown"
            source_counts[src] = source_counts.get(src, 0) + 1
            done_domains.add(w["domain"])
        processed += len(batch)

    # â”€â”€ Main loop: batches until verified target hit or budget spent â”€â”€â”€â”€â”€â”€
    while counts["verified"] < verified_target and processed < budget:
        batch = _fetch_candidates(min(batch_size, budget - processed))
        if not batch:
            if not _top_up():
                logger.info("store index: candidate sources dry â€” stopping at %d verified", counts["verified"])
                break
            continue
        _process_batch(batch)

    # â”€â”€ Re-verification: small daily slice of stale verified rows â”€â”€â”€â”€â”€â”€â”€â”€â”€
    new_verified = counts.get("verified", 0)  # snapshot before re-verify so
    # refreshing old rows doesn't inflate the new-verified number
    reverify_count = 0
    if not limit_override:  # skip during small admin test runs
        try:
            res = db.table("shopify_store_index")\
                .select("domain, source, source_query")\
                .eq("status", "verified")\
                .lt("last_verified_at", reverify_cutoff)\
                .order("last_verified_at")\
                .limit(_REVERIFY_DAILY_CAP)\
                .execute()
            stale = [{**r, "domain": normalize_domain(r["domain"])} for r in (res.data or [])
                     if normalize_domain(r["domain"]) not in done_domains]
            if stale:
                reverify_count = len(stale)
                _process_batch(stale)
        except Exception:
            pass

    summary = {
        "status": "ok",
        "processed": processed,
        "verified": new_verified,
        "rejected": counts.get("rejected", 0),
        "failed": counts.get("failed", 0),
        "skipped_duplicates": skipped_duplicates,
        "reverified": reverify_count,
        "verified_target": verified_target,
        "source_counts": source_counts,
    }

    # Run history for the admin quality dashboard (table from migration 008)
    try:
        db.table("store_index_runs").insert({
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "trigger": "manual" if limit_override else "cron",
            "processed": summary["processed"],
            "verified": summary["verified"],
            "rejected": summary["rejected"],
            "failed": summary["failed"],
            "duplicates": summary["skipped_duplicates"],
            "reverified": summary["reverified"],
            "source_counts": source_counts,
            "notes": f"target {verified_target}, budget {budget}",
        }).execute()
    except Exception as exc:
        logger.debug("store index: run-history insert skipped (%s)", exc)
    logger.info(
        "store index run: %(processed)d processed â€” %(verified)d verified, "
        "%(rejected)d rejected, %(failed)d failed, %(skipped_duplicates)d dup-skipped, "
        "%(reverified)d re-verified", summary,
    )
    return summary
