from __future__ import annotations
import asyncio
import json as _json
import logging
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from urllib.parse import urlparse

import anthropic as _anthropic

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from app.core.auth import get_current_user_id, get_effective_user_id
from app.core.config import get_settings
from app.core.database import get_supabase
from app.core.obs import safe_read

router = APIRouter(prefix="/competitors", tags=["competitors"])


class AddCompetitorRequest(BaseModel):
    store_url: str
    display_name: Optional[str] = None

    @field_validator("store_url")
    @classmethod
    def normalize_url(cls, v: str) -> str:
        v = v.strip().lower()
        if not v.startswith("http"):
            v = "https://" + v
        parsed = urlparse(v)
        netloc = parsed.netloc.rstrip("/")
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return f"https://{netloc}"


class UpdateCompetitorRequest(BaseModel):
    display_name: Optional[str] = None
    is_active: Optional[bool] = None


def _tier_limits(tier: str) -> dict:
    s = get_settings()
    return {
        "free": {"max_competitors": s.free_max_competitors, "scan_hours": s.free_scan_interval_hours},
        "pro": {"max_competitors": s.pro_max_competitors, "scan_hours": s.pro_scan_interval_hours},
        "agency": {"max_competitors": s.agency_max_competitors, "scan_hours": s.agency_scan_interval_hours},
    }.get(tier, {"max_competitors": 1, "scan_hours": 168})


@router.get("")
@safe_read("GET /competitors", {"data": []})
def list_competitors(user_id: str = Depends(get_effective_user_id)):
    db = get_supabase()
    result = db.table("competitors").select("*").eq("user_id", user_id).eq("is_my_store", False).order("created_at", desc=True).execute()
    competitors = result.data or []

    # Enrich each competitor with metrics from its most recent snapshot so the
    # list view can show median price, promo rate and 30-day new-product counts.
    # These live on scan_snapshots, not the competitors table.
    ids = [c["id"] for c in competitors if c.get("id")]
    if ids:
        snaps = (
            db.table("scan_snapshots")
            .select("competitor_id, scanned_at, median_price, promo_rate, new_30d")
            .in_("competitor_id", ids)
            .order("scanned_at", desc=True)
            .execute()
        )
        latest: dict = {}
        for s in snaps.data or []:
            cid = s.get("competitor_id")
            if cid and cid not in latest:  # newest first → first seen wins
                latest[cid] = s
        for c in competitors:
            snap = latest.get(c.get("id"))
            if snap:
                c["median_price"] = snap.get("median_price")
                c["promo_rate"] = snap.get("promo_rate")
                c["new_30d"] = snap.get("new_30d")

    return {"data": competitors}


@router.post("", status_code=status.HTTP_201_CREATED)
def add_competitor(body: AddCompetitorRequest, user_id: str = Depends(get_effective_user_id)):
    db = get_supabase()
    settings = get_settings()

    # Check tier limits — auto-provision if profile missing (handles users who skipped onboarding)
    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    if not user or not user.data:
        try:
            db.table("user_profiles").insert({
                "id": user_id,
                "email": "",
                "tier": "free",
                "max_competitors": settings.free_max_competitors,
                "scan_interval_hours": settings.free_scan_interval_hours,
                "subscription_status": "inactive",
            }).execute()
        except Exception as provision_exc:
            # Likely a race (row already exists) or an RLS policy mismatch. Log it so
            # we can diagnose paid-user-gets-free-defaults incidents, then re-fetch so
            # we read the real tier rather than blindly defaulting.
            logger.warning("user_profiles auto-provision failed for %s: %s", user_id, provision_exc)
        # Re-fetch after provision attempt — picks up the real tier even if insert failed
        user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    tier = (user.data or {}).get("tier", "free") if (user and user.data) else "free"
    limits = _tier_limits(tier)

    existing = db.table("competitors").select("id").eq("user_id", user_id).eq("is_active", True).eq("is_my_store", False).execute()
    if len(existing.data or []) >= limits["max_competitors"]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "competitor_limit_reached",
                "tier": tier,
                "limit": limits["max_competitors"],
                "upgrade_url": f"{settings.public_base_url}/settings/billing",
            },
        )

    # Check for duplicate
    dupe = db.table("competitors").select("id").eq("user_id", user_id).eq("store_url", body.store_url).execute()
    if dupe.data:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Competitor already tracked")

    # Validate the URL is actually a Shopify store before creating the row.
    # This surfaces the failure immediately instead of after a 60s scan attempt.
    try:
        from app.services.fetch import check_store
        probe = check_store(body.store_url)
        if not probe.get("ok"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "not_shopify",
                    "message": "This doesn't appear to be a Shopify store. Check the URL and try again.",
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Probe network error — allow the add and let the scan fail gracefully
        logger.warning("check_store probe failed for %s: %s", body.store_url, exc)

    hostname = urlparse(body.store_url).netloc
    now = datetime.now(timezone.utc)

    try:
        row = db.table("competitors").insert({
            "user_id": user_id,
            "store_url": body.store_url,
            "hostname": hostname,
            "display_name": body.display_name,
            "scan_status": "pending",
            "next_scan_at": now.isoformat(),
        }).execute()
    except Exception as exc:
        # Unique constraint violation (user_id, store_url) — treat as duplicate.
        # Also catches the limit race: two concurrent requests that both passed the
        # count check; whichever inserts second hits 23505 and gets a clean 409.
        err_str = str(exc)
        if "23505" in err_str or "duplicate" in err_str.lower() or "unique" in err_str.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Competitor already tracked")
        raise

    competitor_id = row.data[0]["id"]

    # Trigger immediate scan — non-fatal if Celery is unreachable
    try:
        from app.tasks.scan import scan_competitor
        scan_competitor.delay(competitor_id)
    except Exception as exc:
        logger.warning("Could not enqueue initial scan for %s: %s", competitor_id, exc)

    # Feed the competitor graph — tracking is the strongest relationship signal
    try:
        from app.services.store_index import record_competitor_edge, normalize_domain
        ms = db.table("competitors").select("hostname").eq("user_id", user_id)\
            .eq("is_my_store", True).maybe_single().execute()
        source_key = (ms.data or {}).get("hostname") if ms else None
        record_competitor_edge(db, source_key or f"user:{user_id}", normalize_domain(hostname), "tracked", delta=2)
    except Exception as exc:
        logger.debug("tracked-edge write skipped: %s", exc)

    return {"data": row.data[0]}


# Curated fallback: well-known Shopify stores shown when there's no tag/vendor data to
# match against (new users, fresh competitors with no scan yet).
_CURATED_STORES = [
    {"hostname": "gymshark.com",       "category": "Apparel",  "tag": "Fitness apparel"},
    {"hostname": "allbirds.com",       "category": "Apparel",  "tag": "Sustainable footwear"},
    {"hostname": "fashionnova.com",    "category": "Apparel",  "tag": "Fast fashion"},
    {"hostname": "chubbiesshorts.com", "category": "Apparel",  "tag": "Men's shorts"},
    {"hostname": "vuori.com",          "category": "Apparel",  "tag": "Performance apparel"},
    {"hostname": "kyliecosmetics.com", "category": "Beauty",   "tag": "Makeup"},
    {"hostname": "colourpop.com",      "category": "Beauty",   "tag": "Affordable cosmetics"},
    {"hostname": "fentybeauty.com",    "category": "Beauty",   "tag": "Inclusive beauty"},
    {"hostname": "iliabeauty.com",     "category": "Beauty",   "tag": "Clean beauty"},
    {"hostname": "brooklinen.com",     "category": "Home",     "tag": "Luxury bedding"},
    {"hostname": "parachutehome.com",  "category": "Home",     "tag": "Home essentials"},
    {"hostname": "ruggable.com",       "category": "Home",     "tag": "Washable rugs"},
    {"hostname": "pourri.com",         "category": "Home",     "tag": "Lifestyle & wellness"},
    {"hostname": "bombas.com",         "category": "Apparel",  "tag": "Socks & basics"},
    {"hostname": "mvmtwatches.com",    "category": "Accessories","tag": "Minimalist watches"},
    {"hostname": "puravidabracelets.com","category": "Accessories","tag": "Bracelets & jewelry"},
    {"hostname": "tentree.com",        "category": "Apparel",  "tag": "Sustainable fashion"},
    {"hostname": "skims.com",          "category": "Apparel",  "tag": "Shapewear"},
]


# IMPORTANT: /discover must be registered before /{competitor_id} so FastAPI doesn't
# try to parse the literal string "discover" as a UUID competitor_id.
@router.get("/discover")
def discover_similar(user_id: str = Depends(get_effective_user_id)):
    """
    Suggest similar Shopify stores to track based on tag/vendor overlap
    with the user's currently tracked competitors. Falls back to curated
    popular stores for new users or when no tag data is available.
    """
    try:
        return _discover_similar_inner(user_id)
    except Exception as exc:
        logger.error("discover failed for user %s: %s", user_id, exc, exc_info=True)
        curated = [
            {
                "hostname": s["hostname"], "competitor_id": s["hostname"],
                "score": 0, "match_reasons": [s["tag"]],
                "product_count": None, "median_price": None,
                "market_position": None, "is_curated": True, "category": s["category"],
            }
            for s in _CURATED_STORES
        ][:6]
        return {"data": {"suggestions": curated}}


def _discover_similar_inner(user_id: str) -> dict:
    db = get_supabase()

    # User's current competitors
    user_comps = db.table("competitors")\
        .select("id, hostname")\
        .eq("user_id", user_id)\
        .eq("is_active", True)\
        .eq("is_my_store", False)\
        .execute()

    tracked_hostnames = {c["hostname"] for c in (user_comps.data or [])}
    tracked_ids = [c["id"] for c in (user_comps.data or [])]

    def _curated_fallback() -> list:
        return [
            {
                "hostname": s["hostname"],
                "competitor_id": s["hostname"],  # no DB id — frontend uses hostname for dedup
                "score": 0,
                "match_reasons": [s["tag"]],
                "product_count": None,
                "median_price": None,
                "market_position": None,
                "is_curated": True,
                "category": s["category"],
            }
            for s in _CURATED_STORES
            if s["hostname"] not in tracked_hostnames
        ][:6]

    # No tracked competitors — return curated list
    if not tracked_ids:
        return {"data": {"suggestions": _curated_fallback()}}

    # Aggregate top tags + vendors from user's tracked competitors' snapshots
    agg_tags: Counter = Counter()
    agg_vendors: Counter = Counter()
    for comp_id in tracked_ids:
        data = _latest_snapshot_data(db, comp_id)
        if not data:
            continue
        for t in (data.get("tag_analysis") or {}).get("top_tags", [])[:10]:
            agg_tags[str(t.get("tag", ""))] += t.get("count", 1)
        for v in (data.get("vendor_analysis") or {}).get("top_vendors", [])[:5]:
            agg_vendors[str(v.get("vendor", "")).lower()] += v.get("count", 1)

    top_tags = {t for t, _ in agg_tags.most_common(15)}
    top_vendors = {v for v, _ in agg_vendors.most_common(8)}

    if not top_tags and not top_vendors:
        return {"data": {"suggestions": _curated_fallback()}}

    # Find other recently-scanned competitors (not tracked by this user).
    # Step 1: get unique competitor_ids from recent scan_snapshots.
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    recent_snaps = db.table("scan_snapshots")\
        .select("competitor_id")\
        .gte("scanned_at", thirty_days_ago)\
        .order("scanned_at", desc=True)\
        .limit(200)\
        .execute()

    candidate_ids = list({
        s["competitor_id"] for s in (recent_snaps.data or [])
        if s.get("competitor_id") and s["competitor_id"] not in tracked_ids
    })[:60]

    if not candidate_ids:
        return {"data": {"suggestions": _curated_fallback()}}

    # Step 2: get hostnames for those competitor_ids from the competitors table.
    cand_comps_res = db.table("competitors")\
        .select("id, hostname")\
        .in_("id", candidate_ids)\
        .execute()

    cand_map = {
        c["id"]: c["hostname"]
        for c in (cand_comps_res.data or [])
        if c.get("hostname") and c["hostname"] not in tracked_hostnames
    }

    if not cand_map:
        return {"data": {"suggestions": _curated_fallback()}}

    # Step 3: score each candidate by tag + vendor overlap with user's tracked stores.
    scored = []
    for cid, hostname in cand_map.items():
        data = _latest_snapshot_data(db, cid)
        if not data:
            continue

        cand_tags = {str(t.get("tag", "")) for t in (data.get("tag_analysis") or {}).get("top_tags", [])[:10]}
        cand_vendors = {str(v.get("vendor", "")).lower() for v in (data.get("vendor_analysis") or {}).get("top_vendors", [])[:5]}

        tag_matches = top_tags & cand_tags
        vendor_matches = top_vendors & cand_vendors
        score = len(tag_matches) * 2 + len(vendor_matches) * 3
        if score == 0:
            continue

        reasons = [f"vendor: {v}" for v in sorted(vendor_matches)[:2]]
        reasons += [t for t in sorted(tag_matches)[:3] if t not in (r.split(": ")[-1] for r in reasons)]

        pricing = data.get("pricing") or {}
        pos = (data.get("positioning") or {}).get("market_position") or {}
        market_pos = pos.get("label") if isinstance(pos, dict) else None

        scored.append({
            "hostname": hostname,
            "competitor_id": cid,
            "score": score,
            "match_reasons": reasons[:4],
            "product_count": (data.get("catalog") or {}).get("total_products"),
            "median_price": pricing.get("median"),
            "market_position": market_pos,
            "is_curated": False,
            "category": None,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:6]
    if not top:
        return {"data": {"suggestions": _curated_fallback()}}
    return {"data": {"suggestions": top}}


# ── AI-powered competitor discovery ──────────────────────────────────────────

class DiscoverAIRequest(BaseModel):
    description: str


@router.post("/discover-ai")
async def discover_ai(
    body: DiscoverAIRequest,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    settings = get_settings()

    if not settings.anthropic_api_key:
        logger.error("discover-ai: ANTHROPIC_API_KEY is not configured")
        raise HTTPException(status_code=500, detail="AI service not configured — contact support.")

    FREE_LIMIT = 1

    # Fetch user tier + usage — handle missing columns gracefully
    user_data: dict = {}
    try:
        user = db.table("user_profiles").select(
            "tier, discovery_searches_used, discovery_searches_month"
        ).eq("id", user_id).maybe_single().execute()
        user_data = (user.data or {}) if user else {}
    except Exception as _ue:
        # Columns may not exist yet (migration pending) — fall back to tier only
        logger.warning("discover-ai: full user fetch failed (%s), retrying with tier only", _ue)
        try:
            user2 = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
            user_data = (user2.data or {}) if user2 else {}
        except Exception:
            pass
    tier = user_data.get("tier", "free")
    is_free = tier == "free"

    searches_used = 0
    if is_free:
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        stored_month = user_data.get("discovery_searches_month") or ""
        searches_used = user_data.get("discovery_searches_used") or 0
        if stored_month != current_month:
            searches_used = 0  # new month — reset

        if searches_used >= FREE_LIMIT:
            raise HTTPException(
                status_code=402,
                detail={"code": "discovery_limit_reached", "limit": FREE_LIMIT},
            )

        # Increment immediately — counts even if Claude fails
        new_count = searches_used + 1
        try:
            db.table("user_profiles").update({
                "discovery_searches_used": new_count,
                "discovery_searches_month": current_month,
            }).eq("id", user_id).execute()
            searches_used = new_count
        except Exception as inc_exc:
            logger.warning("discovery_searches increment failed: %s", inc_exc)

    # Pull connected store context for richer suggestions
    store_context = ""
    user_stage: Optional[str] = None
    user_price_tier: Optional[str] = None
    my_store_hostname: Optional[str] = None
    try:
        my_store = db.table("competitors").select("id, hostname, product_count").eq(
            "user_id", user_id
        ).eq("is_my_store", True).maybe_single().execute()
        if my_store and my_store.data:
            ms = my_store.data
            snap = db.table("scan_snapshots").select("median_price, promo_rate").eq(
                "competitor_id", ms["id"]
            ).order("scanned_at", desc=True).limit(1).maybe_single().execute()
            parts = [f"store: {ms['hostname']}"]
            if ms.get("product_count"):
                parts.append(f"{ms['product_count']} products")
            if snap and snap.data:
                if snap.data.get("median_price"):
                    parts.append(f"median price ${snap.data['median_price']:.2f}")
                if snap.data.get("promo_rate"):
                    parts.append(f"{snap.data['promo_rate']:.0f}% on sale")
            store_context = "\nConnected " + ", ".join(parts) + "."
            my_store_hostname = ms.get("hostname")
            # The user's own stage/tier drives relevance ranking of index hits —
            # a startup should see growing peers, not enterprise giants.
            from app.services.store_index import derive_market_context
            mc = derive_market_context(
                ms.get("product_count"),
                (snap.data or {}).get("median_price") if snap else None,
            )
            user_stage = mc["business_stage"]
            user_price_tier = mc["pricing_tier"]
    except Exception as ctx_exc:
        logger.debug("discover-ai store context fetch failed: %s", ctx_exc)

    # ── Staged pipeline ──────────────────────────────────────────────────
    # Claude answers ONE question — "who does this business compete with?" —
    # ranked by market similarity, platform ignored. StoreScout then answers
    # the second question itself (multi-signal Shopify verification), refills
    # with additional Claude batches until enough verified stores exist, and
    # returns non-Shopify competitors separately instead of dropping them.
    TARGET_VERIFIED = 8
    MAX_BATCHES = 3

    def _discovery_prompt(exclude: list) -> str:
        exclusions = ", ".join(exclude) if exclude else "none"
        n = 25 if not exclude else 15
        return f"""You are a DTC ecommerce market analyst helping a store owner map their competitive landscape.

Business: {body.description.strip()}{store_context}

Identify {n} brands this business's customers would realistically compare before making a purchase, ranked most-similar first. Judge purely on market overlap — product category, price point, target customer, positioning. IGNORE what ecommerce platform each brand uses; that is verified separately.

Return ONLY valid JSON with no markdown, no code fences, no explanation:
{{
  "suggestions": [
    {{"domain": "gymshark.com", "reason": "premium activewear, similar $60-80 price point"}},
    ...
  ]
}}

Rules:
- domain must be the brand's own storefront domain (never a marketplace or social page)
- Brands that sell primarily through their own website — exclude pure marketplaces and department stores (Amazon, Walmart, Target, Etsy)
- Each reason under 12 words, specific about WHY it competes (price, audience, product type)
- Mix well-known brands with smaller/emerging ones
- Do NOT include any of these: {exclusions}"""

    def _call_claude(prompt: str) -> list:
        client = _anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text
        logger.info("discover-ai raw response: %s", raw_text[:500])
        text = raw_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0].strip()
        return _json.loads(text).get("suggestions", [])

    async def _verify(domain: str) -> dict:
        try:
            from app.services.fetch import verify_shopify as _verify_shopify
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(None, _verify_shopify, domain),
                timeout=15.0,
            )
        except Exception:
            return {"verified": False, "monitorable": False, "confidence": 0, "signals": []}

    def _norm(domain: str) -> str:
        d = (domain or "").strip().lower()
        d = d.replace("https://", "").replace("http://", "").split("/")[0]
        return d[4:] if d.startswith("www.") else d

    # Exclude stores the user already tracks from every batch
    already_tracked: set = set()
    try:
        tracked = db.table("competitors").select("hostname").eq("user_id", user_id).execute()
        already_tracked = {_norm(t["hostname"]) for t in (tracked.data or [])}
    except Exception:
        pass

    seen: set = set(already_tracked)
    verified: list = []          # Shopify-verified AND scannable → trackable
    relevant_other: list = []    # real competitors we can't monitor (yet)
    blocked: set = set()         # user-confirmed "not a competitor" domains

    # ── Stage 0a: the competitor knowledge graph — StoreScout's own
    # accumulated who-competes-with-whom map. Queried BEFORE any AI call;
    # confirmed non-competitors (negative weight) are excluded everywhere.
    graph_keys = [k for k in [my_store_hostname, f"user:{user_id}"] if k]
    try:
        from app.services.store_index import graph_neighbors
        neighbors = graph_neighbors(db, graph_keys, limit=12)
        blocked = {d for d, w in neighbors.items() if w < 0}
        positive = [d for d, w in sorted(neighbors.items(), key=lambda kv: -kv[1])
                    if w > 0 and d not in seen]
        if positive:
            g_res = db.table("shopify_store_index")\
                .select("domain, brand_name, category, subcategory, description, verification_confidence, verification_signals")\
                .eq("status", "verified")\
                .gte("verification_confidence", settings.shopify_index_min_confidence)\
                .in_("domain", positive[:12])\
                .execute()
            g_rows = {r["domain"]: r for r in (g_res.data or [])}
            for d in positive:
                row = g_rows.get(d)
                if not row or d in seen or len(verified) >= 4:
                    continue
                seen.add(d)
                verified.append({
                    "domain": d,
                    "reason": (row.get("description") or "in your competitive neighborhood")[:90],
                    "confidence": row.get("verification_confidence"),
                    "signals": row.get("verification_signals") or [],
                    "source": "graph",
                })
            if verified:
                logger.info("discover-ai: %d matches from the competitor graph", len(verified))
    except Exception as g_exc:
        logger.debug("discover-ai graph lookup skipped: %s", g_exc)

    # ── Stage 0b: index-first — search our own verified store index before
    # asking Claude. Every hit here is pre-verified, instant, and free.
    # Guarded end-to-end so discovery works identically before migration 007.
    try:
        import re as _re
        terms = [t for t in _re.split(r"[^a-z0-9]+", body.description.lower()) if len(t) >= 4][:6]
        if terms:
            ors = ",".join(
                f"{col}.ilike.%{t}%"
                for t in terms
                for col in ("category", "subcategory", "description", "brand_name")
            )
            def _idx_query(with_cat_conf: bool):
                cols = ("domain, brand_name, category, subcategory, description, "
                        "verification_confidence, verification_signals, business_stage, pricing_tier")
                if with_cat_conf:
                    cols += ", category_confidence, category_evidence"
                return db.table("shopify_store_index")\
                    .select(cols)\
                    .eq("status", "verified")\
                    .gte("verification_confidence", settings.shopify_index_min_confidence)\
                    .or_(ors)\
                    .order("verification_confidence", desc=True)\
                    .limit(TARGET_VERIFIED * 3)\
                    .execute()
            # Prefer the category-confidence columns (migration 015); fall back
            # cleanly to the pre-015 shape so discovery never breaks.
            try:
                idx_res = _idx_query(True)
            except Exception:
                idx_res = _idx_query(False)

            # Category-confidence floor — the guard against weak guesses
            # ("Everlane for pet accessories"). A store is only recommended when
            # its category is confident enough; rows without a score yet (not
            # knowledge-processed) are allowed through on verification confidence.
            cat_floor = settings.shopify_index_category_min_confidence

            # Relevance ranking: prefer stores the user actually competes
            # against. A startup fitness brand should see growing peers first —
            # giants may still appear, but they never dominate the list.
            def _relevance(row: dict) -> float:
                score = float(row.get("verification_confidence") or 0)
                stage = row.get("business_stage")
                tier = row.get("pricing_tier")
                if user_stage and stage:
                    order = ["startup", "growing", "established", "enterprise"]
                    try:
                        gap = abs(order.index(stage) - order.index(user_stage))
                        score += (3 - gap) * 8   # same stage +24, one apart +16…
                    except ValueError:
                        pass
                if user_price_tier and tier:
                    score += 12 if tier == user_price_tier else 0
                if stage == "enterprise" and user_stage in (None, "startup", "growing"):
                    score -= 30  # underdogs first — Nike shouldn't crowd out peers
                return score

            ranked = sorted(idx_res.data or [], key=_relevance, reverse=True)

            # Cap index hits at 5 of the 8 slots — keyword matching is crude,
            # so Claude always gets room to add description-tailored picks.
            for row in ranked:
                d = row["domain"]
                if d in seen or d in blocked or len(verified) >= 5:
                    continue
                # Withhold low-confidence classifications — quality over padding.
                cc = row.get("category_confidence")
                if cc is not None and cc < cat_floor:
                    continue
                seen.add(d)
                reason = row.get("description") or " · ".join(
                    x for x in [row.get("category"), row.get("subcategory")] if x
                ) or "verified Shopify store in our index"
                verified.append({
                    "domain": d,
                    "reason": reason[:90],
                    "confidence": row.get("verification_confidence"),
                    "signals": row.get("verification_signals") or [],
                    "source": "index",
                })
            if verified:
                logger.info("discover-ai: %d instant matches from store index", len(verified))
    except Exception as idx_exc:
        logger.debug("discover-ai index-first lookup skipped: %s", idx_exc)

    loop_error: Exception | None = None
    for batch in range(MAX_BATCHES):
        try:
            suggestions = await asyncio.get_event_loop().run_in_executor(
                None, _call_claude, _discovery_prompt(sorted(seen))
            )
        except Exception as ai_exc:
            loop_error = ai_exc
            break

        fresh = []
        for s in suggestions:
            d = _norm(s.get("domain", ""))
            if d and "." in d and d not in seen and d not in blocked:
                seen.add(d)
                fresh.append({"domain": d, "reason": (s.get("reason") or "").strip()})
        if not fresh:
            break

        # ── Verification cache: the index already knows many of these domains —
        # a verified row skips the network probe, a recent rejection skips the
        # candidate. Guarded so discovery works before migration 007.
        cached_rows: dict = {}
        try:
            cache_res = db.table("shopify_store_index")\
                .select("domain, status, verification_confidence, verification_signals, last_verified_at")\
                .in_("domain", [s["domain"] for s in fresh])\
                .execute()
            cached_rows = {r["domain"]: r for r in (cache_res.data or [])}
        except Exception:
            pass

        recent_cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        to_probe = []
        for s in fresh:
            row = cached_rows.get(s["domain"])
            if row and row.get("status") == "verified" and (row.get("verification_confidence") or 0) >= settings.shopify_index_min_confidence:
                verified.append({
                    **s,
                    "confidence": row.get("verification_confidence"),
                    "signals": row.get("verification_signals") or [],
                    "source": "index",
                })
            elif row and row.get("status") in ("rejected", "failed") and (row.get("last_verified_at") or "") >= recent_cutoff:
                relevant_other.append({**s, "note": "Not a Shopify store — we can't monitor it yet"})
            else:
                to_probe.append(s)

        results = await asyncio.gather(*[_verify(s["domain"]) for s in to_probe])
        writeback_rows = []
        probe_now = datetime.now(timezone.utc).isoformat()
        for s, v in zip(to_probe, results):
            if v["verified"] and v["monitorable"]:
                verified.append({**s, "confidence": v["confidence"], "signals": v["signals"]})
            elif v["verified"]:
                # Real Shopify store with a locked catalog — show it honestly
                relevant_other.append({**s, "note": "Shopify store, but its catalog is private — we can't scan it yet"})
            else:
                relevant_other.append({**s, "note": "Not a Shopify store — we can't monitor it yet"})
            # Write every probe back into the index — discovery compounds it for free
            writeback_rows.append({
                "domain": s["domain"],
                "status": "verified" if (v["verified"] and v["monitorable"]) else "rejected",
                "verification_confidence": v["confidence"],
                "verification_signals": v["signals"],
                "failure_reason": None if (v["verified"] and v["monitorable"]) else "discovery probe below threshold or catalog locked",
                "source": "discovery",
                "source_query": body.description.strip()[:200],
                "last_verified_at": probe_now,
                "updated_at": probe_now,
            })
        if writeback_rows:
            try:
                # These domains had no fresh verified index row (else they'd have
                # been served from cache), so a blind upsert can't downgrade one.
                db.table("shopify_store_index").upsert(writeback_rows, on_conflict="domain").execute()
            except Exception as wb_exc:
                logger.debug("discover-ai index write-back skipped: %s", wb_exc)

        logger.info(
            "discover-ai batch %d: %d fresh candidates, %d verified total, %d non-monitorable",
            batch + 1, len(fresh), len(verified), len(relevant_other),
        )
        if len(verified) >= TARGET_VERIFIED:
            break

    if not verified and not relevant_other:
        # Nothing at all came back — surface the real failure instead of an empty list
        if isinstance(loop_error, _anthropic.AuthenticationError):
            raise HTTPException(status_code=500, detail="AI service authentication failed — contact support.")
        if isinstance(loop_error, _anthropic.RateLimitError):
            raise HTTPException(status_code=429, detail="AI service is busy — please try again in a moment.")
        raise HTTPException(status_code=500, detail="Failed to generate suggestions — please try again.")

    # ── Feed the graph: every verified suggestion strengthens the map, so
    # the next search (by this user or a similar store) needs less AI.
    try:
        from app.services.store_index import record_competitor_edge
        primary_key = my_store_hostname or f"user:{user_id}"
        for v in verified[:10]:
            record_competitor_edge(db, primary_key, v["domain"], "discovery")
    except Exception as edge_exc:
        logger.debug("discover-ai edge write-back skipped: %s", edge_exc)

    return {
        "data": {
            "suggestions": verified[:10],
            "relevant_non_shopify": relevant_other[:8],
            "searches_used": searches_used if is_free else None,
            "searches_limit": FREE_LIMIT if is_free else None,
        }
    }


class DiscoveryFeedbackRequest(BaseModel):
    domain: str
    correct: bool


@router.post("/discovery-feedback")
def discovery_feedback(body: DiscoveryFeedbackRequest, user_id: str = Depends(get_current_user_id)):
    """✓ correct competitor / ✕ not a competitor — writes straight into the
    knowledge graph. A confirmation strengthens the edge; a rejection pins it
    negative so that domain never surfaces for this user (or store) again."""
    db = get_supabase()
    from app.services.store_index import record_competitor_edge, normalize_domain

    domain = normalize_domain(body.domain)
    if not domain or "." not in domain:
        raise HTTPException(status_code=422, detail="valid domain required")

    source_key = f"user:{user_id}"
    try:
        ms = db.table("competitors").select("hostname").eq("user_id", user_id)\
            .eq("is_my_store", True).maybe_single().execute()
        if ms and ms.data and ms.data.get("hostname"):
            source_key = ms.data["hostname"]
    except Exception:
        pass

    if body.correct:
        record_competitor_edge(db, source_key, domain, "feedback", delta=3)
    else:
        record_competitor_edge(db, source_key, domain, "feedback", set_weight=-5)
    return {"status": "ok", "domain": domain, "correct": body.correct}


@router.get("/{competitor_id}")
def get_competitor(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    """Fetch a single competitor record (no snapshot data)."""
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    result = db.table("competitors")\
        .select("*")\
        .eq("id", competitor_id)\
        .maybe_single()\
        .execute()
    if not result or not result.data:
        raise HTTPException(status_code=404, detail="Not found")
    return {"data": result.data}


@router.patch("/{competitor_id}")
def update_competitor(
    competitor_id: str,
    body: UpdateCompetitorRequest,
    user_id: str = Depends(get_effective_user_id),
):
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = db.table("competitors").update(updates).eq("id", competitor_id).execute()
    return {"data": result.data[0] if result.data else {}}


@router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_competitor(competitor_id: str, user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    db.table("competitors").delete().eq("id", competitor_id).execute()


@router.post("/{competitor_id}/rescan")
def manual_rescan(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)

    competitor = db.table("competitors").select("scan_status").eq("id", competitor_id).single().execute()
    if (competitor.data or {}).get("scan_status") == "scanning":
        raise HTTPException(status_code=409, detail="Scan already in progress")

    # Redis-based cooldown — 60s between rescans per competitor (non-fatal if Redis unavailable)
    try:
        import redis as redis_lib
        r = redis_lib.from_url(get_settings().redis_url, socket_connect_timeout=1)
        rl_key = f"ratelimit:rescan:{competitor_id}"
        if r.exists(rl_key):
            raise HTTPException(status_code=429, detail="Rescan cooldown active — please wait 60 seconds")
        r.set(rl_key, "1", ex=60)
    except HTTPException:
        raise
    except Exception:
        pass  # Redis unavailable — allow the rescan

    try:
        from app.tasks.scan import manual_rescan as _rescan
        _rescan.apply_async(args=[competitor_id], queue="priority")
    except Exception as exc:
        logger.warning("Could not enqueue rescan for %s: %s", competitor_id, exc)
        raise HTTPException(
            status_code=503,
            detail="Scan queue temporarily unavailable — the worker may be restarting. Please try again in a minute.",
        )
    return {"status": "queued"}


@router.get("/{competitor_id}/snapshots/latest")
def get_latest_snapshot(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    result = db.table("scan_snapshots")\
        .select("id, scanned_at, product_count, median_price, promo_rate, new_30d, snapshot_data")\
        .eq("competitor_id", competitor_id)\
        .order("scanned_at", desc=True)\
        .limit(1)\
        .execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="No snapshots yet")
    return {"data": result.data[0]}


@router.get("/{competitor_id}/snapshots")
def list_snapshots(
    competitor_id: str,
    limit: int = 30,
    user_id: str = Depends(get_effective_user_id),
):
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)

    # History is a paid feature
    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    tier = (user.data or {}).get("tier", "free") if user else "free"
    if tier == "free":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"code": "history_locked", "upgrade_url": "/settings/billing"},
        )

    settings = get_settings()
    cutoff_days = 90 if tier == "pro" else 9999
    cutoff = (datetime.now(timezone.utc) - timedelta(days=cutoff_days)).isoformat()

    result = db.table("scan_snapshots")\
        .select("id, scanned_at, product_count, median_price, promo_rate, new_30d")\
        .eq("competitor_id", competitor_id)\
        .gte("scanned_at", cutoff)\
        .order("scanned_at", desc=True)\
        .limit(limit)\
        .execute()
    return {"data": result.data or []}


@router.get("/{competitor_id}/changes")
def get_changes(
    competitor_id: str,
    limit: int = 50,
    change_type: Optional[str] = None,
    user_id: str = Depends(get_effective_user_id),
):
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)

    query = db.table("change_events")\
        .select("*")\
        .eq("competitor_id", competitor_id)\
        .order("detected_at", desc=True)\
        .limit(limit)
    if change_type:
        query = query.eq("change_type", change_type)
    result = query.execute()
    return {"data": result.data or []}


@router.get("/{competitor_id}/ai-summary")
def get_ai_summary(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)

    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    tier = (user.data or {}).get("tier", "free") if user else "free"
    if tier == "free":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"code": "ai_summary_locked"},
        )

    # The paid experience is the strategist report (summary_type="pro") — a
    # different product from the free Scout Brief, not a longer rewrite of it.
    _PRO_FRESHNESS_HOURS = 23
    result = db.table("ai_summaries")\
        .select("*")\
        .eq("competitor_id", competitor_id)\
        .eq("summary_type", "pro")\
        .order("generated_at", desc=True)\
        .limit(1)\
        .execute()
    row = result.data[0] if result.data else None

    fresh = False
    if row:
        try:
            generated = datetime.fromisoformat(row["generated_at"].replace("Z", "+00:00"))
            fresh = (datetime.now(timezone.utc) - generated) < timedelta(hours=_PRO_FRESHNESS_HOURS)
        except Exception:
            fresh = False

    if not fresh:
        try:
            from app.tasks.ai_summaries import generate_pro_analysis
            generate_pro_analysis.delay(competitor_id)
        except Exception as exc:
            logger.warning("Could not enqueue pro analysis for %s: %s", competitor_id, exc)

    if row:
        return {"data": row, "status": "ok" if fresh else "refreshing"}
    return {"data": None, "status": "generating"}


@router.post("/{competitor_id}/ai-summary/regenerate")
def regenerate_ai_summary(competitor_id: str, user_id: str = Depends(get_current_user_id)):
    """Trigger a fresh Pro analysis on demand (Pro/Agency only)."""
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)

    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    tier = (user.data or {}).get("tier", "free") if user else "free"
    if tier == "free":
        raise HTTPException(status_code=402, detail={"code": "ai_summary_locked"})

    from app.tasks.ai_summaries import generate_pro_analysis
    generate_pro_analysis.delay(competitor_id)
    return {"status": "triggered"}


@router.get("/{competitor_id}/winning-products")
@safe_read("GET /winning-products", {"data": {"products": [], "newest": [], "locked": False, "locked_count": 0}})
def get_winning_products(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    """
    Winning-product analysis. Free tier sees the #1 product (score visible, the
    'why' locked) plus a locked count. Pro/Agency see the full ranked list,
    signal breakdowns, reasons, and the newest-products list.
    """
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    tier = _user_tier(db, user_id)

    data = _latest_snapshot_data(db, competitor_id)
    wp = (data.get("winning_products") or {}) if data else {}
    products = wp.get("products") or []
    newest = wp.get("newest") or []

    if not products:
        return {"data": {"products": [], "newest": [], "locked": tier == "free", "locked_count": 0, "tier": tier}}

    if tier == "free":
        # Free sees the top 3 products (title/price/score visible) — enough to
        # explore and pin to the watchlist; the 'why/verdict' stays Pro-only.
        teasers = [{
            "handle": p.get("handle"),
            "title": p.get("title"),
            "product_url": p.get("product_url"),
            "price_min": p.get("price_min"),
            "image": p.get("image"),
            "score": p.get("score"),
            # 'why' is locked
            "reason": None,
            "signal_tags": [],
            "locked": True,
        } for p in products[:3]]
        return {
            "data": {
                "products": teasers,
                "newest": [],
                "locked": True,
                "locked_count": max(0, len(products) - 3),
                "tier": tier,
            }
        }

    return {
        "data": {
            "products": products,
            "newest": newest,
            "locked": False,
            "locked_count": 0,
            "tier": tier,
        }
    }


@router.get("/{competitor_id}/gaps")
@safe_read("GET /gaps", {"data": {"gaps": [], "locked": False, "locked_count": 0}})
def get_gaps(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    """
    Gap analysis. Free tier sees the top 2 gap titles (detail locked) plus a
    locked count. Pro/Agency see every gap with full detail and metrics.
    """
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    tier = _user_tier(db, user_id)

    data = _latest_snapshot_data(db, competitor_id)
    ga = (data.get("gap_analysis") or {}) if data else {}
    gaps = ga.get("gaps") or []

    if not gaps:
        return {"data": {"gaps": [], "locked": tier == "free", "locked_count": 0, "tier": tier}}

    if tier == "free":
        teasers = [{
            "type": g.get("type"),
            "title": g.get("title"),
            "detail": None,  # locked
            "opportunity": g.get("opportunity"),
            "locked": True,
        } for g in gaps[:3]]
        return {
            "data": {
                "gaps": teasers,
                "locked": True,
                "locked_count": max(0, len(gaps) - 3),
                "tier": tier,
            }
        }

    return {"data": {"gaps": gaps, "locked": False, "locked_count": 0, "tier": tier}}


@router.get("/{competitor_id}/store-profile")
@safe_read("GET /store-profile", {"data": None})
def get_store_profile(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    """
    Brand intelligence from extended scraping (collections, pages, blogs).
    Free tier: top-level signals only (collection count, key boolean flags).
    Pro/Agency: full collection names, all brand signals, content intelligence.
    """
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    tier = _user_tier(db, user_id)

    data = _latest_snapshot_data(db, competitor_id)
    profile = (data.get("store_profile") or {}) if data else {}

    col = profile.get("collection_intel") or {}
    brand = profile.get("brand_signals") or {}
    content = profile.get("content_intel") or {}

    # Free tier: surface key signals, lock the details
    if tier == "free":
        return {
            "data": {
                "collection_count": col.get("count", 0),
                "has_sale_collection": col.get("has_sale", False),
                "has_new_arrivals": col.get("has_new_arrivals", False),
                "has_best_sellers": col.get("has_best_sellers", False),
                "has_blog": content.get("blog_count", 0) > 0,
                "has_wholesale": brand.get("has_wholesale", False),
                "content_investment_score": content.get("content_investment_score"),
                "locked": True,
                "tier": tier,
            }
        }

    return {
        "data": {
            "collection_intel": col,
            "brand_signals": brand,
            "content_intel": content,
            "locked": False,
            "tier": tier,
        }
    }


@router.get("/{competitor_id}/comparison")
@safe_read("GET /comparison", {"data": {"has_store": False}})
def get_comparison(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    """
    Head-to-head: the user's own store vs this competitor. Requires the user to
    have set their store. Free tier sees the diagnosis (verdicts + insights);
    action items and the match strategy are Pro.
    """
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    tier = _user_tier(db, user_id)

    # Find the user's own store
    my = db.table("competitors")\
        .select("id, hostname")\
        .eq("user_id", user_id)\
        .eq("is_my_store", True)\
        .maybe_single()\
        .execute()
    if not my or not my.data:
        return {"data": {"has_store": False}}

    my_data = _latest_snapshot_data(db, my.data["id"])
    their_data = _latest_snapshot_data(db, competitor_id)
    if not my_data:
        return {"data": {"has_store": True, "ready": False, "reason": "my_store_scanning"}}
    if not their_data:
        return {"data": {"has_store": True, "ready": False, "reason": "competitor_scanning"}}

    their = db.table("competitors").select("hostname").eq("id", competitor_id).single().execute()
    their_hostname = (their.data or {}).get("hostname", "them")

    from app.services.insights import compare_stores
    result = compare_stores(my_data, their_data, my.data["hostname"], their_hostname)
    result["ready"] = True

    # Tier gate: free sees diagnosis, Pro gets prescription
    if tier == "free":
        for d in result.get("dimensions", []):
            d["action"] = None
            d["action_locked"] = True
        ms = result.get("match_strategy") or {}
        result["match_strategy"] = {
            "is_newcomer": ms.get("is_newcomer", False),
            "narrative": None,
            "match_these": [],
            "own_these": [],
            "locked": True,
        }
        result["locked"] = True
    else:
        result["locked"] = False

    result["tier"] = tier
    return {"data": result}


@router.get("/{competitor_id}/quick-wins")
def get_quick_wins(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    """
    Rule-based action cards from the latest snapshot.
    Free tier: 1 card visible + locked_count.  Pro/Agency: all cards.
    """
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    tier = _user_tier(db, user_id)

    data = _latest_snapshot_data(db, competitor_id)
    if not data:
        return {"data": {"wins": [], "locked": False, "locked_count": 0, "tier": tier}}

    from app.services.insights import compute_quick_wins
    wins = compute_quick_wins(data)

    if not wins:
        return {"data": {"wins": [], "locked": False, "locked_count": 0, "tier": tier}}

    if tier == "free":
        return {"data": {
            "wins": wins[:2],
            "locked": True,
            "locked_count": max(0, len(wins) - 2),
            "tier": tier,
        }}

    return {"data": {"wins": wins, "locked": False, "locked_count": 0, "tier": tier}}


@router.get("/{competitor_id}/price-history")
@safe_read("GET /price-history", {"data": {"points": [], "locked": False}})
def get_price_history(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    """
    Time-series of median_price and promo_rate across scans.
    Free: last 2 data points + locked flag.  Pro: 90 days.  Agency: unlimited.
    """
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    tier = _user_tier(db, user_id)
    now = datetime.now(timezone.utc)

    if tier == "free":
        result = db.table("scan_snapshots")\
            .select("scanned_at, median_price, promo_rate, product_count")\
            .eq("competitor_id", competitor_id)\
            .order("scanned_at", desc=True)\
            .limit(7)\
            .execute()
        points = list(reversed(result.data or []))
        total = db.table("scan_snapshots").select("id", count="exact")\
            .eq("competitor_id", competitor_id).execute()
        total_count = total.count or len(points)
        return {"data": {
            "points": points,
            "locked": True,
            "locked_count": max(0, total_count - 7),
            "tier": tier,
        }}

    query = db.table("scan_snapshots")\
        .select("scanned_at, median_price, promo_rate, product_count")\
        .eq("competitor_id", competitor_id)\
        .order("scanned_at", desc=False)\
        .limit(365)

    if tier == "pro":
        cutoff = (now - timedelta(days=90)).isoformat()
        query = query.gte("scanned_at", cutoff)

    result = query.execute()
    return {"data": {
        "points": result.data or [],
        "locked": False,
        "locked_count": 0,
        "tier": tier,
    }}


@router.get("/{competitor_id}/market-context")
@safe_read("GET /market-context", {"data": {"category": None, "saturation": 0, "peers": []}})
def get_market_context(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    """Market research context for Product Intelligence: this competitor's
    category, its verified peers from StoreScout's own store index, and
    saturation. Every number here is VERIFIED index data — the frontend
    layers clearly-labeled estimates (wholesale ranges) on top."""
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)

    comp = db.table("competitors").select("hostname").eq("id", competitor_id).maybe_single().execute()
    hostname = ((comp and comp.data) or {}).get("hostname") or ""
    from app.services.store_index import normalize_domain
    domain = normalize_domain(hostname)

    empty = {"category": None, "saturation": 0, "peers": []}
    try:
        row = db.table("shopify_store_index")\
            .select("category, subcategory, median_price, pricing_tier")\
            .eq("domain", domain).maybe_single().execute()
        me = (row and row.data) or {}
        category = me.get("category")
        if not category or category == "Other":
            return {"data": empty}

        saturation = db.table("shopify_store_index").select("id", count="exact")\
            .eq("status", "verified").eq("category", category).execute().count or 0

        peers_res = db.table("shopify_store_index")\
            .select("domain, brand_name, median_price, business_stage, pricing_tier")\
            .eq("status", "verified").eq("category", category)\
            .neq("domain", domain)\
            .order("verification_confidence", desc=True)\
            .limit(8).execute()

        return {"data": {
            "category": category,
            "subcategory": me.get("subcategory"),
            "saturation": saturation,
            "peers": peers_res.data or [],
        }}
    except Exception as exc:
        logger.debug("market-context skipped for %s: %s", domain, exc)
        return {"data": empty}


@router.get("/{competitor_id}/brief")
def get_brief(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    """Latest Intelligence Brief for this competitor (available to all tiers)."""
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)

    result = db.table("ai_summaries")\
        .select("*")\
        .eq("competitor_id", competitor_id)\
        .eq("summary_type", "brief")\
        .order("generated_at", desc=True)\
        .limit(1)\
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="No brief available yet")
    return {"data": result.data[0]}


@router.get("/{competitor_id}/export/products.csv")
def export_products_csv(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    """Download a CSV of the competitor's latest product catalog. Pro/Agency only."""
    import csv, io
    from fastapi.responses import Response

    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    tier = _user_tier(db, user_id)
    if tier == "free":
        raise HTTPException(status_code=403, detail={"code": "upgrade_required", "message": "CSV export requires Pro or Agency plan"})

    result = db.table("scan_snapshots")\
        .select("snapshot_data, scanned_at")\
        .eq("competitor_id", competitor_id)\
        .order("scanned_at", desc=True)\
        .limit(1)\
        .execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="No snapshot found")

    data = result.data[0].get("snapshot_data") or {}
    hostname = data.get("hostname") or competitor_id
    product_index = data.get("_product_index") or {}

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["title", "handle", "url", "price", "compare_at", "discount_pct", "available"],
        extrasaction="ignore",
    )
    writer.writeheader()
    for handle, p in product_index.items():
        price = p.get("price_min") or 0
        ca = p.get("compare_at_min")
        disc = round((ca - price) / ca * 100, 1) if ca and ca > price else ""
        writer.writerow({
            "title": p.get("title") or "",
            "handle": handle,
            "url": p.get("product_url") or "",
            "price": price,
            "compare_at": ca or "",
            "discount_pct": disc,
            "available": p.get("available", True),
        })

    safe_hostname = hostname.replace(".", "_").replace("/", "_")
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe_hostname}_products.csv"'},
    )


def _user_tier(db, user_id: str) -> str:
    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    return (user.data or {}).get("tier", "free") if user else "free"


def _latest_snapshot_data(db, competitor_id: str) -> Optional[dict]:
    result = db.table("scan_snapshots")\
        .select("snapshot_data")\
        .eq("competitor_id", competitor_id)\
        .order("scanned_at", desc=True)\
        .limit(1)\
        .execute()
    if not result.data:
        return None
    return result.data[0].get("snapshot_data") or {}


def _assert_owner(db, competitor_id: str, user_id: str):
    result = db.table("competitors").select("user_id").eq("id", competitor_id).maybe_single().execute()
    if not result or not result.data or result.data["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Not found")
