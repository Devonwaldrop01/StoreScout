"""
Background Shopify store index worker.

Continuously discovers, verifies, lightly scans, classifies, and stores
Shopify stores into shopify_store_index — StoreScout's compounding
proprietary store database. Deliberately polite and cheap:

  · disabled by default (SHOPIFY_INDEX_ENABLED)
  · daily candidate cap (SHOPIFY_INDEX_DAILY_CANDIDATE_LIMIT)
  · domains are processed once; verified rows re-checked on a 60-day
    cycle capped at 10/day — nothing gets hammered repeatedly
  · ≤4 requests per domain, low thread concurrency, retries with backoff
  · fetches run on the WEB process via /internal/store-index/process
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
from app.core.config import get_settings
from app.core.database import get_supabase
from app.services.store_index import SEED_QUERIES, normalize_domain

logger = logging.getLogger(__name__)

_REVERIFY_DAYS = 60       # verified rows get a fresh pass on this cycle
_REVERIFY_DAILY_CAP = 10


def _process_via_web(domain: str, source: str, source_query: Optional[str]) -> dict:
    """Run one domain's index pass on the web service (worker IPs get blocked)."""
    settings = get_settings()
    url = f"{settings.api_internal_url}/api/v1/internal/store-index/process"
    payload = {"domain": domain, "source": source, "source_query": source_query}
    headers = {"x-internal-token": settings.internal_secret}

    for attempt in range(2):  # 1 retry with backoff
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
            if resp.status_code == 200:
                return resp.json()
            logger.warning("store-index process %s returned HTTP %d", domain, resp.status_code)
        except Exception as exc:
            logger.warning("store-index process %s failed (attempt %d): %s", domain, attempt + 1, exc)
        if attempt == 0:
            time.sleep(5)
    return {"domain": domain, "outcome": "failed", "confidence": 0}


@celery.task(name="app.tasks.store_index.generate_niche_candidates")
def generate_niche_candidates(query: str, target: int = 20) -> dict:
    """Ask Haiku for ~20 DTC brand domains in a niche (platform-agnostic —
    verification is OUR job) and insert unseen ones as candidates."""
    import json as _json
    import anthropic

    settings = get_settings()
    if not settings.anthropic_api_key:
        return {"status": "no_api_key", "inserted": 0}

    db = get_supabase()
    # StoreScout users compete against niche and growing brands, not Nike —
    # the index must represent the REAL Shopify ecosystem, so the generator
    # deliberately skews toward underdogs and category specialists.
    prompt = f"""You are mapping the DTC ecommerce landscape.

List {target} direct-to-consumer BRANDS a shopper would realistically buy from in this niche: {query}

Return ONLY valid JSON, no markdown fences:
{{"stores": [{{"domain": "example-brand.com", "name": "Example Brand"}}, ...]}}

Rules:
- domain must be the brand's own storefront domain (never marketplaces, social pages, or retailers like Amazon/Walmart/Target)
- STRONGLY favor niche, emerging, fast-growing, and mid-size independent brands — at most 3 household names in the whole list
- Include category specialists and underdogs a small store owner actually competes against
- Ignore what ecommerce platform they use — that is verified separately"""

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


@celery.task(name="app.tasks.store_index.generate_related_candidates")
def generate_related_candidates(domain: str, brand_name: str = "", category: str = "", description: str = "", target: int = 12) -> dict:
    """
    Graph expansion: every verified store becomes a seed for discovering the
    brands around it. Ask Haiku for competitors/peers of a known store and
    insert unseen ones as candidates. The seed store's expanded_at is stamped
    so each store is expanded exactly once.
    """
    import json as _json
    import anthropic

    settings = get_settings()
    if not settings.anthropic_api_key:
        return {"status": "no_api_key", "inserted": 0}

    db = get_supabase()
    who = brand_name or domain
    context = " · ".join(x for x in [category, (description or "")[:120]] if x)
    prompt = f"""You are mapping the competitive neighborhood of a DTC ecommerce brand.

Brand: {who} ({domain}){f" — {context}" if context else ""}

List {target} brands whose customers would ALSO consider {who} — direct competitors and close peers.

Return ONLY valid JSON, no markdown fences:
{{"stores": [{{"domain": "example-brand.com", "name": "Example Brand"}}, ...]}}

Rules:
- domain must be each brand's own storefront domain (never marketplaces or retailers)
- Prefer brands of a SIMILAR size and stage to {who} — peers first, giants last, at most 2 household names
- Ignore what ecommerce platform they use — that is verified separately"""

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
        # Stamp even on failure — a store that errors during expansion should
        # not be retried every single day (guarded: column may not exist yet).
        try:
            db.table("shopify_store_index").update(
                {"expanded_at": datetime.now(timezone.utc).isoformat()}
            ).eq("domain", normalize_domain(domain)).execute()
        except Exception:
            pass

    logger.info("related expansion for %s: %d new candidates", domain, inserted)
    return {"status": "ok", "inserted": inserted}


@celery.task(name="app.tasks.store_index.discover_shopify_stores_daily")
def discover_shopify_stores_daily(limit_override: Optional[int] = None, force: bool = False) -> dict:
    """
    Daily indexing run, optimized for NEW VERIFIED stores — not candidates
    processed. Works in small batches until the verified target is hit or the
    request budget runs out, topping up candidates graph-first (related-brand
    expansion of already-verified stores) and then via niche rotation.

    `force=True` is the admin test-run path: it bypasses the enabled flag and
    treats limit_override as both target and budget (a bounded small run).
    """
    settings = get_settings()
    if not settings.shopify_index_enabled and not force:
        logger.info("store index disabled (SHOPIFY_INDEX_ENABLED=false) — skipping run")
        return {"status": "disabled"}

    # Distributed lock — same pattern as enqueue_due_scans
    try:
        import redis as redis_lib
        _r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
        if not _r.set("lock:store_index_daily", "1", nx=True, ex=3600):
            logger.info("store index run already in progress — skipping")
            return {"status": "skipped_lock"}
    except Exception as exc:
        logger.warning("store index: Redis unavailable (%s) — running without lock", exc)
        _r = None

    db = get_supabase()
    if limit_override:
        verified_target = max(1, min(limit_override, 250))
        budget = verified_target
    else:
        verified_target = max(1, min(settings.shopify_index_daily_verified_target, 250))
        budget = max(verified_target, min(settings.shopify_index_daily_candidate_limit, 500))
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
        verified stores — this is what compounds the ecosystem coverage),
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

    # ── Main loop: batches until verified target hit or budget spent ──────
    while counts["verified"] < verified_target and processed < budget:
        batch = _fetch_candidates(min(batch_size, budget - processed))
        if not batch:
            if not _top_up():
                logger.info("store index: candidate sources dry — stopping at %d verified", counts["verified"])
                break
            continue
        _process_batch(batch)

    # ── Re-verification: small daily slice of stale verified rows ─────────
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
        "store index run: %(processed)d processed — %(verified)d verified, "
        "%(rejected)d rejected, %(failed)d failed, %(skipped_duplicates)d dup-skipped, "
        "%(reverified)d re-verified", summary,
    )
    return summary
