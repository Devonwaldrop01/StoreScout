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
    prompt = f"""You are mapping the DTC ecommerce landscape.

List {target} direct-to-consumer BRANDS a shopper would realistically buy from in this niche: {query}

Return ONLY valid JSON, no markdown fences:
{{"stores": [{{"domain": "gymshark.com", "name": "Gymshark"}}, ...]}}

Rules:
- domain must be the brand's own storefront domain (never marketplaces, social pages, or retailers like Amazon/Walmart/Target)
- Mix well-known and smaller/emerging brands
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


@celery.task(name="app.tasks.store_index.discover_shopify_stores_daily")
def discover_shopify_stores_daily(limit_override: Optional[int] = None, force: bool = False) -> dict:
    """
    Daily indexing run. Pulls candidates → verifies + lightly scans (via the
    web process) → classifies → upserts. `force=True` is used by the admin
    test-run endpoint to bypass the enabled flag (caps/cooldowns still apply).
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
    limit = max(1, min(limit_override or settings.shopify_index_daily_candidate_limit, 500))
    reverify_cutoff = (datetime.now(timezone.utc) - timedelta(days=_REVERIFY_DAYS)).isoformat()

    # ── Gather work: candidates first, oldest first ───────────────────────
    # Candidates are unprocessed by definition (processing always moves them
    # to verified/rejected/failed), so no cooldown filter is needed here —
    # the cooldown protects re-verification, which is capped separately below.
    work: List[dict] = []
    try:
        res = db.table("shopify_store_index")\
            .select("domain, source, source_query")\
            .eq("status", "candidate")\
            .order("created_at")\
            .limit(limit)\
            .execute()
        work = res.data or []
    except Exception as exc:
        logger.error("store index: candidate fetch failed (table missing?): %s", exc)

    # Top up from the niche-query generator (rotating through SEED_QUERIES)
    if len(work) < min(limit, 25):
        try:
            idx = 0
            if _r is not None:
                idx = int(_r.incr("store_index:niche_rotation")) % len(SEED_QUERIES)
            query = SEED_QUERIES[idx]
            gen = generate_niche_candidates(query)  # synchronous — we want the rows now
            if gen.get("inserted"):
                res = db.table("shopify_store_index")\
                    .select("domain, source, source_query")\
                    .eq("status", "candidate")\
                    .eq("source_query", query)\
                    .order("created_at", desc=True)\
                    .limit(limit - len(work))\
                    .execute()
                known = {w["domain"] for w in work}
                work.extend(r for r in (res.data or []) if r["domain"] not in known)
        except Exception as exc:
            logger.warning("store index: niche top-up failed: %s", exc)

    # Re-verification picks — small daily slice of stale verified rows
    reverify_count = 0
    try:
        res = db.table("shopify_store_index")\
            .select("domain, source, source_query")\
            .eq("status", "verified")\
            .lt("last_verified_at", reverify_cutoff)\
            .order("last_verified_at")\
            .limit(_REVERIFY_DAILY_CAP)\
            .execute()
        known = {w["domain"] for w in work}
        for r in res.data or []:
            if r["domain"] not in known:
                work.append(r)
                reverify_count += 1
    except Exception:
        pass

    # Dedupe, cap
    seen: set = set()
    queue: List[dict] = []
    skipped_duplicates = 0
    for w in work:
        d = normalize_domain(w["domain"])
        if d in seen:
            skipped_duplicates += 1
            continue
        seen.add(d)
        queue.append({**w, "domain": d})
    queue = queue[:limit]

    if not queue:
        logger.info("store index: nothing to process (no candidates, generator dry)")
        return {"status": "ok", "processed": 0, "verified": 0, "rejected": 0, "failed": 0,
                "skipped_duplicates": skipped_duplicates, "reverified": 0}

    # ── Process politely: low concurrency, via web process ────────────────
    counts = {"verified": 0, "rejected": 0, "failed": 0}
    concurrency = max(1, min(settings.shopify_index_concurrency, 4))
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(
            lambda w: _process_via_web(w["domain"], w.get("source") or "unknown", w.get("source_query")),
            queue,
        ))
    for r in results:
        counts[r.get("outcome", "failed")] = counts.get(r.get("outcome", "failed"), 0) + 1

    summary = {
        "status": "ok",
        "processed": len(queue),
        "verified": counts.get("verified", 0),
        "rejected": counts.get("rejected", 0),
        "failed": counts.get("failed", 0),
        "skipped_duplicates": skipped_duplicates,
        "reverified": reverify_count,
    }
    logger.info(
        "store index run: %(processed)d processed — %(verified)d verified, "
        "%(rejected)d rejected, %(failed)d failed, %(skipped_duplicates)d dup-skipped, "
        "%(reverified)d re-verified", summary,
    )
    return summary
