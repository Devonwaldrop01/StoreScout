from __future__ import annotations
import logging
import traceback
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

from fastapi import APIRouter, Header, HTTPException

from app.core.config import get_settings
from app.core.database import get_supabase
from app.services.fetch import fetch_products_shopify
from app.services.normalize import normalize_product
from app.services.analyze import analyze_products

router = APIRouter(prefix="/internal", tags=["internal"])
logger = logging.getLogger(__name__)


def _require_internal(token: str) -> None:
    if token != get_settings().internal_secret:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/scan/{competitor_id}")
def internal_scan(competitor_id: str, x_internal_token: str = Header(...)):
    """
    Runs the Shopify fetch + analyze + DB write on the web service process.
    Called by the Celery worker so the fetch uses the web service's outbound IP.
    """
    _require_internal(x_internal_token)
    settings = get_settings()
    db = get_supabase()

    # ── 1. Load competitor from DB ──────────────────────────────────────────
    logger.info("[SCAN %s] loading competitor from DB", competitor_id)
    try:
        result = db.table("competitors")\
            .select("store_url, hostname, display_name, user_profiles(tier)")\
            .eq("id", competitor_id)\
            .maybe_single()\
            .execute()
    except Exception as exc:
        logger.error("[SCAN %s] DB lookup failed: %s\n%s", competitor_id, exc, traceback.format_exc())
        return {"status": "error", "reason": f"DB lookup failed: {exc}"}

    if not result or not result.data:
        logger.error("[SCAN %s] competitor not found in DB", competitor_id)
        return {"status": "error", "reason": "competitor_not_found"}

    competitor = result.data
    store_url = competitor["store_url"]
    tier = (competitor.get("user_profiles") or {}).get("tier", "free")
    hostname = competitor.get("hostname") or urlparse(store_url).netloc
    display_name = competitor.get("display_name") or hostname
    logger.info("[SCAN %s] store_url=%r tier=%r", competitor_id, store_url, tier)

    # ── 2. Skip-if-unchanged probe (only when a previous snapshot exists) ───
    try:
        last_snap = db.table("scan_snapshots")\
            .select("snapshot_data")\
            .eq("competitor_id", competitor_id)\
            .order("scanned_at", desc=True)\
            .limit(1)\
            .execute()

        if last_snap.data:
            logger.info("[SCAN %s] previous snapshot exists, probing for changes", competitor_id)
            probe = fetch_products_shopify(store_url, max_products=1)
            if probe:
                latest_updated = probe[0].get("updated_at", "")
                prev_newest = (last_snap.data[0]["snapshot_data"].get("lists") or {}).get("recently_updated", [])
                if prev_newest and prev_newest[0].get("updated_at") == latest_updated:
                    logger.info("[SCAN %s] skip-if-unchanged: no change detected", competitor_id)
                    interval_h = _interval_for_tier(tier, settings)
                    next_scan = datetime.now(timezone.utc) + timedelta(hours=interval_h)
                    db.table("competitors").update({
                        "scan_status": "done",
                        "last_scanned_at": datetime.now(timezone.utc).isoformat(),
                        "next_scan_at": next_scan.isoformat(),
                    }).eq("id", competitor_id).execute()
                    return {"status": "unchanged"}
            else:
                logger.warning("[SCAN %s] probe returned 0 products — proceeding with full scan anyway", competitor_id)
        else:
            logger.info("[SCAN %s] no previous snapshot — skipping probe, going straight to full scan", competitor_id)
    except Exception as exc:
        logger.warning("[SCAN %s] skip-if-unchanged probe failed (non-fatal): %s\n%s",
                       competitor_id, exc, traceback.format_exc())

    # ── 3. Full fetch (memory-capped) ────────────────────────────────────────
    # Bound the catalog size so peak memory across fetch/normalize/analyze/
    # detect stays under the dyno limit. Huge stores are staged: we take the
    # cap and record that the catalog was truncated for transparency.
    cap = settings.scan_max_products or None
    logger.info("[SCAN %s] starting full fetch for %r (cap=%s)", competitor_id, store_url, cap)
    try:
        raw = fetch_products_shopify(store_url, max_products=cap)
    except Exception as exc:
        logger.error("[SCAN %s] fetch_products_shopify raised exception: %s\n%s",
                     competitor_id, exc, traceback.format_exc())
        _mark_error(db, competitor_id, f"fetch exception: {exc}")
        return {"status": "error", "reason": f"fetch exception: {exc}"}

    logger.info("[SCAN %s] fetch returned %d raw products", competitor_id, len(raw))

    if not raw:
        logger.error("[SCAN %s] fetch returned empty list for %r — see FETCH logs above for root cause",
                     competitor_id, store_url)
        _mark_error(db, competitor_id,
            "Could not access this store's catalog. It may use bot protection that blocks automated access. "
            "Try rescanning, or remove it and add a different competitor."
        )
        return {"status": "error", "reason": f"No products returned for {store_url}"}

    # ── 4. Normalize ─────────────────────────────────────────────────────────
    logger.info("[SCAN %s] normalizing %d products", competitor_id, len(raw))
    try:
        normalized = [normalize_product(p, store_url) for p in raw]
        logger.info("[SCAN %s] normalized OK: %d products", competitor_id, len(normalized))
    except Exception as exc:
        logger.error("[SCAN %s] normalize failed: %s\n%s", competitor_id, exc, traceback.format_exc())
        _mark_error(db, competitor_id, f"normalize exception: {exc}")
        return {"status": "error", "reason": f"normalize exception: {exc}"}

    # ── 5. Analyze ───────────────────────────────────────────────────────────
    logger.info("[SCAN %s] analyzing products", competitor_id)
    try:
        insights = analyze_products(normalized)
        total_products = (insights.get("catalog") or {}).get("total_products", len(normalized))
        logger.info("[SCAN %s] analyze OK: total_products=%d", competitor_id, total_products)
    except Exception as exc:
        logger.error("[SCAN %s] analyze failed: %s\n%s", competitor_id, exc, traceback.format_exc())
        _mark_error(db, competitor_id, f"analyze exception: {exc}")
        return {"status": "error", "reason": f"analyze exception: {exc}"}

    # Transparency: note when a huge catalog was capped for memory safety.
    if cap and len(raw) >= cap:
        insights["catalog_truncated"] = True
        insights["catalog_scanned"] = len(raw)
        logger.info("[SCAN %s] catalog capped at %d products (memory guard)", competitor_id, cap)

    # Compact per-product index so detect_changes can diff the full catalog.
    # Keyed by handle; stores only the fields needed for change detection.
    insights["_product_index"] = {
        p["handle"]: {
            "title": p.get("title"),
            "product_url": p.get("product_url"),
            "price_min": p.get("price_min"),
            "compare_at_min": p.get("compare_at_min"),
            "available": p.get("available"),
        }
        for p in normalized
        if p.get("handle")
    }

    # ── 5b. Extended scraping (collections, pages, blogs) ───────────────────
    store_profile: dict = {}
    try:
        from app.services.fetch import fetch_extended_data
        from app.services.insights import analyze_store_profile
        extended = fetch_extended_data(store_url)
        store_profile = analyze_store_profile(extended)
        insights["store_profile"] = store_profile
        logger.info("[SCAN %s] extended: collections=%d pages=%d blogs=%d articles=%d",
                    competitor_id,
                    len(extended.get("collections", [])),
                    len(extended.get("pages", [])),
                    len(extended.get("blogs", [])),
                    len(extended.get("articles", [])))
    except Exception as exc:
        logger.error("[SCAN %s] extended scraping failed (non-fatal): %s\n%s",
                     competitor_id, exc, traceback.format_exc())
        insights["store_profile"] = {}

    # Stage 1 intelligence — winning products + gap analysis, computed from the
    # full normalized catalog and stored in the snapshot for tier-gated serving.
    try:
        from app.services.insights import score_winning_products, analyze_gaps
        insights["winning_products"] = score_winning_products(normalized)
        insights["gap_analysis"] = analyze_gaps(insights, normalized, store_profile=store_profile or None)
        logger.info("[SCAN %s] insights: %d winning products, %d gaps",
                    competitor_id,
                    insights["winning_products"].get("scored_total", 0),
                    insights["gap_analysis"].get("total", 0))
    except Exception as exc:
        logger.error("[SCAN %s] insights computation failed (non-fatal): %s\n%s",
                     competitor_id, exc, traceback.format_exc())
        insights["winning_products"] = {"products": [], "newest": [], "scored_total": 0}
        insights["gap_analysis"] = {"gaps": [], "total": 0}

    # Stamp hostname/display_name so frontend can render without a separate DB call
    insights["hostname"] = hostname
    insights["display_name"] = display_name

    # ── 6. Write snapshot ────────────────────────────────────────────────────
    pricing = insights.get("pricing", {})
    discounts = insights.get("discounts", {})
    launch = insights.get("launch_timeline", {})
    now = datetime.now(timezone.utc)

    logger.info("[SCAN %s] inserting scan_snapshot (product_count=%d)", competitor_id, total_products)
    try:
        snap_result = db.table("scan_snapshots").insert({
            "competitor_id": competitor_id,
            "scanned_at": now.isoformat(),
            "product_count": total_products,
            "median_price": pricing.get("median"),
            "promo_rate": discounts.get("discounted_pct"),
            "new_30d": (launch.get("launch_counts") or {}).get("30d", {}).get("count"),
            "snapshot_data": insights,
        }).execute()
        snapshot_id = snap_result.data[0]["id"] if snap_result.data else None
        logger.info("[SCAN %s] snapshot inserted: id=%s", competitor_id, snapshot_id)
    except Exception as exc:
        logger.error("[SCAN %s] snapshot insert failed: %s\n%s", competitor_id, exc, traceback.format_exc())
        _mark_error(db, competitor_id, f"snapshot insert failed: {exc}")
        return {"status": "error", "reason": f"snapshot insert failed: {exc}"}

    # ── 7. Update competitor row ─────────────────────────────────────────────
    interval_h = _interval_for_tier(tier, settings)
    try:
        db.table("competitors").update({
            "scan_status": "done",
            "last_scanned_at": now.isoformat(),
            "next_scan_at": (now + timedelta(hours=interval_h)).isoformat(),
            "product_count": total_products,
            "error_message": None,
        }).eq("id", competitor_id).execute()
        logger.info("[SCAN %s] competitor updated to scan_status=done", competitor_id)
    except Exception as exc:
        logger.error("[SCAN %s] competitor update failed: %s\n%s", competitor_id, exc, traceback.format_exc())
        # Snapshot is already written — don't fail the whole request over this

    # ── 8. Feed the store index — every successfully scanned store is a
    # verified Shopify store we already have fresh data for. Zero extra
    # requests; failures here never break the scan.
    try:
        from app.services.store_index import upsert_index_row, classify_store, normalize_domain, derive_market_context
        profile = insights.get("store_profile") or {}
        market = derive_market_context(total_products, pricing.get("median"))
        classification = classify_store(
            title=display_name or hostname,
            description=(profile.get("about") or "")[:300] if isinstance(profile.get("about"), str) else "",
            product_types=[t.get("tag") if isinstance(t, dict) else str(t) for t in ((insights.get("tag_analysis") or {}).get("top_tags") or [])][:15] or None,
            collections=(profile.get("collections") or [])[:20] or None,
        )
        upsert_index_row(db, normalize_domain(hostname), {
            "status": "verified",
            "failure_reason": None,
            "brand_name": display_name,
            "homepage_url": f"https://{hostname}",
            "category": classification["category"],
            "subcategory": classification["subcategory"],
            "description": classification["description"],
            "product_count": total_products,
            "median_price": pricing.get("median"),
            "promo_rate": discounts.get("discounted_pct"),
            "business_stage": market["business_stage"],
            "pricing_tier": market["pricing_tier"],
            "verification_confidence": 100,
            "verification_signals": ["Actively scanned by StoreScout"],
            "source": "tracked",
            "last_verified_at": now.isoformat(),
            "last_light_scanned_at": now.isoformat(),
        })
        logger.info("[SCAN %s] store index upsert OK for %s", competitor_id, hostname)
    except Exception as exc:
        logger.debug("[SCAN %s] store index upsert failed (non-fatal): %s", competitor_id, exc)

    logger.info("[SCAN %s] COMPLETE snapshot_id=%s", competitor_id, snapshot_id)
    return {"status": "ok", "snapshot_id": snapshot_id}


@router.post("/store-index/process")
def internal_store_index_process(body: dict, x_internal_token: str = Header(...)):
    """
    Run one domain's index pass (verify + light scan + classify + upsert) on
    the web service process — worker IPs get blocked, this one doesn't.
    Called by app/tasks/store_index.py.
    """
    _require_internal(x_internal_token)
    from app.services.store_index import process_domain_into_index

    domain = (body or {}).get("domain") or ""
    if not domain:
        raise HTTPException(status_code=422, detail="domain required")
    source = (body or {}).get("source") or "unknown"
    source_query = (body or {}).get("source_query")

    db = get_supabase()
    result = process_domain_into_index(db, domain, source, source_query)
    logger.info("[INDEX %s] outcome=%s confidence=%s", domain, result["outcome"], result["confidence"])
    return result


@router.post("/store-index/verify")
def internal_store_index_verify(body: dict, x_internal_token: str = Header(...)):
    """
    Stage 2 of the index pipeline: fetch one domain's storefront ONCE and store
    a VERIFIED row (raw signals only, no classification) or a REJECTED row with
    a strict reason. Runs on the web process (worker IPs get blocked). Called by
    app.tasks.store_index.stage_verification.
    """
    _require_internal(x_internal_token)
    from app.services.store_index import verify_and_store

    domain = (body or {}).get("domain") or ""
    if not domain:
        raise HTTPException(status_code=422, detail="domain required")
    source = (body or {}).get("source") or "unknown"
    source_query = (body or {}).get("source_query")

    db = get_supabase()
    result = verify_and_store(db, domain, source, source_query)
    logger.info("[VERIFY %s] outcome=%s reason=%s", domain, result["outcome"], result.get("reason"))
    return result


@router.post("/shop-app-page")
def internal_shop_app_page(body: dict, x_internal_token: str = Header(...)):
    """
    Discovery Source #1 fetcher: return a page of candidate Shopify merchant
    domains from the Shop App. This runs on the web process because the worker's
    IP is blocked from outbound fetches. shop.app has no stable public discovery
    API, so this degrades gracefully — on any failure it returns an empty list
    and the source holds its cursor (never fabricates domains).

    Body: {"cursor": {child, offset}, "limit": int}.
    Returns {"domains": [str], "cursor": {...}, "note": str}.
    """
    _require_internal(x_internal_token)
    cursor = (body or {}).get("cursor") or {}
    limit = max(1, min(int((body or {}).get("limit") or 30), 50))

    result = _shop_app_discover(cursor, limit)
    logger.info("[SHOP_APP] cursor=%s processed=%s resolved=%s rate_limited=%s → %d domains (%s)",
                cursor, result.get("processed"), result.get("resolved"),
                result.get("rate_limited"), len(result.get("domains", [])), result.get("note") or "ok")
    return {
        "domains": result.get("domains", []),
        "cursor": result.get("cursor", cursor),
        "note": result.get("note"),
        "processed": result.get("processed"),
        "resolved": result.get("resolved"),
        "rate_limited": result.get("rate_limited"),
        "no_domain": result.get("no_domain"),
        "child_total": result.get("child_total"),
    }


@router.post("/shop-app-count")
def internal_shop_app_count(body: dict, x_internal_token: str = Header(...)):
    """Return how many storefront handles Shop App publishes (the discovery
    ceiling) — cheap, no per-store fetches. Runs on the web process."""
    _require_internal(x_internal_token)
    return _shop_app_count()


@router.post("/shop-app-harvest")
def internal_shop_app_harvest(body: dict, x_internal_token: str = Header(...)):
    """
    Stage 1 (Discovery), cheap + bulk: return a page of raw Shop App refs
    (shop.app/m/{handle} URLs) straight from the storefronts sitemap — NO
    per-store page fetches, so this scales to thousands per run. Resolution to
    real domains happens separately. Body: {cursor, limit}. Returns
    {refs, cursor, child_total}.
    """
    _require_internal(x_internal_token)
    cursor = (body or {}).get("cursor") or {}
    limit = max(1, min(int((body or {}).get("limit") or 500), 5000))
    result = _shop_app_harvest(cursor, limit)
    logger.info("[SHOP_APP_HARVEST] cursor=%s → %d refs (child_total=%s)",
                cursor, len(result.get("refs", [])), result.get("child_total"))
    return result


@router.post("/shop-app-resolve")
def internal_shop_app_resolve(body: dict, x_internal_token: str = Header(...)):
    """
    Stage 2 (Resolution), rate-limited: given raw Shop App refs, fetch each
    store page and return its real merchant domain. Concurrent + 429-backoff.
    Body: {refs: [url]}. Returns {resolved: [{ref, domain}], stats}.
    """
    _require_internal(x_internal_token)
    from concurrent.futures import ThreadPoolExecutor
    refs = [r for r in ((body or {}).get("refs") or []) if r][:60]
    if not refs:
        return {"resolved": [], "stats": {"processed": 0}}

    resolved = []
    rate_limited = no_domain = 0
    # Modest concurrency + per-request backoff: steady beats bursty under a
    # rate limit (a big burst just trips more 429s).
    with ThreadPoolExecutor(max_workers=4) as pool:
        for ref, (domain, st) in zip(refs, pool.map(lambda r: _shop_app_resolve_one(r), refs)):
            if domain:
                resolved.append({"ref": ref, "domain": domain})
            elif st == 429:
                rate_limited += 1
            else:
                no_domain += 1
    return {"resolved": resolved,
            "stats": {"processed": len(refs), "resolved": len(resolved),
                      "rate_limited": rate_limited, "no_domain": no_domain}}


_SHOP_APP_SKIP = (
    "shop.app", "shopify.com", "cdn.shopify", "shopifycdn", "myshopify.com",
    "shopifyinc.com", "shopifycloud", "shopifysvc", "shopifyapps.com",
    "google", "facebook", "instagram", "tiktok", "youtube", "twitter", "x.com",
    "apple.com", "gstatic", "cloudflare", "fbcdn", "gravatar", "w3.org",
    "schema.org", "sentry", "cookielaw", "onetrust", "klaviyo", "pinterest",
    "linkedin", "vimeo", "googletagmanager", "doubleclick", "cdnjs", "cloudfront",
    "jsdelivr", "unpkg", "recaptcha", "paypal", "amazonaws", "akamai",
)


def _shop_app_extract(html: str, limit: int) -> list:
    """Pull candidate merchant storefront hosts from a Shop App HTML payload.
    Shop App is a JS app, but its server response embeds initial state as JSON
    inside <script> tags — this scans the whole payload (anchors + embedded
    JSON) for external hosts, prioritizing explicit merchant-URL keys."""
    import re as _re
    hosts: list = []
    seen = set()

    def _add(h: str):
        h = (h or "").lower().strip().strip("/")
        h = h.split("/")[0]
        if not h or "." not in h or h in seen:
            return
        if any(bad in h for bad in _SHOP_APP_SKIP):
            return
        seen.add(h)
        hosts.append(h)

    # 1. Explicit merchant-URL keys in embedded JSON (highest confidence).
    for m in _re.finditer(r'"(?:url|storeUrl|website|onlineStoreUrl|primaryDomain|domain)"\s*:\s*"https?://([^"/]+)', html, _re.I):
        _add(m.group(1))
        if len(hosts) >= limit:
            return hosts[:limit]

    # 2. Any external host anywhere in the payload (lower confidence).
    for m in _re.finditer(r'https?://([a-z0-9][a-z0-9\-.]+\.[a-z]{2,})', html, _re.I):
        _add(m.group(1))
        if len(hosts) >= limit:
            break
    return hosts[:limit]


def _shop_app_analyze(html: str) -> dict:
    """Dig a Shop App store-page payload for the merchant's real identity and
    the internal data endpoints. Shop App is Remix-based and inlines loader
    state as JSON, so the merchant's domain / myshopify domain is usually in
    the HTML even though the page 'looks' client-rendered."""
    import re as _re
    txt = html or ""

    myshopify = list(dict.fromkeys(_re.findall(r"([a-z0-9][a-z0-9\-]*\.myshopify\.com)", txt, _re.I)))[:20]

    # JSON keys that carry a store's domain/url, with their values.
    domain_keys = []
    for m in _re.finditer(
        r'"(primaryDomain|myshopifyDomain|shopDomain|storeDomain|domain|url|website|host|onlineStoreUrl|canonicalUrl|shopUrl)"\s*:\s*(?:\{[^}]*"host"\s*:\s*)?"([^"]{3,120})"',
        txt, _re.I,
    ):
        val = m.group(2)
        if "shop.app" in val or val.startswith("/") or " " in val:
            continue
        domain_keys.append(f"{m.group(1)}={val}")
        if len(domain_keys) >= 30:
            break

    # Internal API / Remix data-endpoint hints — how the page loads its data.
    api_hints = list(dict.fromkeys(
        _re.findall(r'(https?://[a-z0-9.\-]*shop\.app/[^"\'\\ ]*(?:api|graphql|storefront|_data)[^"\'\\ ]*)', txt, _re.I)
        + _re.findall(r'(https?://server\.shop\.app[^"\'\\ ]*)', txt, _re.I)
        + _re.findall(r'(_data=[^"\'&\\ ]+)', txt)
        + _re.findall(r'(https?://[a-z0-9.\-]+\.shopify\.com/[^"\'\\ ]*(?:api|graphql)[^"\'\\ ]*)', txt, _re.I)
    ))[:20]

    remix = "__remixContext" in txt or "window.__remix" in txt or "routeModules" in txt

    return {"myshopify": myshopify, "domain_keys": domain_keys[:30],
            "api_hints": api_hints, "remix": remix}


def _shop_app_raw_fetch(url: str, timeout: int = 20, follow_done: bool = False) -> dict:
    """Fetch one URL and report status, size, a short text sample, and any
    external hosts found. Pure diagnostic — used to discover which shop.app
    endpoints actually return usable content."""
    from app.services.fetch import IMPERSONATE, _USE_CURL_CFFI, _headers
    status = None
    text = ""
    err = None
    try:
        if _USE_CURL_CFFI:
            from curl_cffi.requests import Session as CurlSession
            with CurlSession() as client:
                r = client.get(url, headers=_headers(), impersonate=IMPERSONATE, timeout=timeout)
                status = r.status_code
                raw = r.content
        else:
            import httpx
            with httpx.Client(follow_redirects=True) as client:
                r = client.get(url, headers=_headers(), timeout=timeout)
                status = r.status_code
                raw = r.content
        # Shop App's child sitemaps are gzip FILES (.xml.gz) — decompress when
        # the URL says .gz or the bytes carry the gzip magic number.
        if raw and (url.endswith(".gz") or raw[:2] == b"\x1f\x8b"):
            import gzip as _gzip
            try:
                raw = _gzip.decompress(raw)
            except Exception:
                pass
        text = raw.decode("utf-8", "replace") if raw else ""
    except Exception as exc:
        err = f"{exc}"[:200]
    domains = _shop_app_extract(text, 15) if (status == 200 and text) else []
    # For small text files (robots.txt, sitemap XML) return the FULL body so we
    # can read the sitemap structure; otherwise a short sample of the shell.
    is_textmap = url.endswith(".txt") or url.endswith(".xml") or "sitemap" in url
    sample_cap = 8000 if is_textmap else 400
    # Also surface every shop.app/child-sitemap <loc> URL — the map we actually
    # want to follow (the domain extractor deliberately skips shop.app hosts).
    import re as _re
    all_locs = _re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", text or "", _re.I)
    locs = all_locs[:50]
    sitemaps = _re.findall(r"Sitemap:\s*(\S+)", text or "", _re.I)[:20]

    # If this is a sitemap INDEX (its locs point to more .xml sitemaps), follow
    # the first child one level so a single probe reveals the whole chain down
    # to real page URLs. Bounded to one extra fetch.
    child_url = None
    child_locs: list = []
    if all_locs and all_locs[0].endswith(".xml") and not follow_done:
        child_url = all_locs[0]
        try:
            child = _shop_app_raw_fetch(child_url, timeout=timeout, follow_done=True)
            child_locs = (child.get("locs") or [])[:30]
        except Exception:
            pass

    # For a store page (/m/{handle}) run the deep analyzer for the merchant's
    # real domain + the internal data endpoints.
    analysis = _shop_app_analyze(text) if ("/m/" in url and status == 200 and text) else None

    return {
        "url": url,
        "http_status": status,
        "bytes": len(text),
        "domains": domains,
        "locs": locs,
        "child_url": child_url,
        "child_locs": child_locs,
        "sitemaps": sitemaps,
        "analysis": analysis,
        "sample": (text[:sample_cap] if text else None),
        "error": err,
    }


def _shop_app_probe_battery() -> list:
    """Try a battery of plausible shop.app entry points so the operator can see
    — in one click — which routes return 200 and which yield merchant domains.
    robots.txt/sitemaps are the reliable way to enumerate valid pages."""
    candidates = [
        "https://shop.app/robots.txt",
        # The real prize: Shopify's published sitemap of Shop App storefronts.
        "https://shop.app/cdn/shopifycloud/shop-web/sitemaps/storefronts/sitemap_storefronts.xml",
        "https://shop.app/cdn/shopifycloud/shop-web/sitemaps/products/sitemap_products.xml",
    ]
    return [_shop_app_raw_fetch(u) for u in candidates]


_STOREFRONTS_INDEX = "https://shop.app/cdn/shopifycloud/shop-web/sitemaps/storefronts/sitemap_storefronts.xml"


def _shop_app_get(url: str, timeout: int = 20):
    """Fetch a URL, decompress .gz, return (status, text). ('' on any error.)"""
    from app.services.fetch import IMPERSONATE, _USE_CURL_CFFI, _headers
    try:
        if _USE_CURL_CFFI:
            from curl_cffi.requests import Session as CurlSession
            with CurlSession() as client:
                r = client.get(url, headers=_headers(), impersonate=IMPERSONATE, timeout=timeout)
                status, raw = r.status_code, r.content
        else:
            import httpx
            with httpx.Client(follow_redirects=True) as client:
                r = client.get(url, headers=_headers(), timeout=timeout)
                status, raw = r.status_code, r.content
        if raw and (url.endswith(".gz") or raw[:2] == b"\x1f\x8b"):
            import gzip as _gzip
            try:
                raw = _gzip.decompress(raw)
            except Exception:
                pass
        return status, (raw.decode("utf-8", "replace") if raw else "")
    except Exception:
        return None, ""


def _shop_app_resolve_one(handle_url: str, timeout: int = 20, retry_429: bool = True):
    """Resolve one shop.app/m/{handle} store page to the merchant's real domain.
    Prefers the vanity domain (most-frequent external host on the page); falls
    back to the {shop}.myshopify.com domain, which is always a live Shopify
    storefront. Retries through throttling with exponential backoff so a 429
    doesn't waste the ref. Returns (domain|None, http_status)."""
    import re as _re
    import time as _time
    status, text = _shop_app_get(handle_url, timeout)
    if retry_429:
        for backoff in (2.0, 5.0, 10.0):
            if status != 429:
                break
            _time.sleep(backoff)
            status, text = _shop_app_get(handle_url, timeout)
    if status != 200 or not text:
        return None, status

    # Vanity domain: the merchant's own site appears many times (canonical, og,
    # links, JSON). Tally external hosts and take the most frequent non-infra one.
    counts: dict = {}
    for m in _re.finditer(r'https?://([a-z0-9][a-z0-9\-.]+\.[a-z]{2,})', text, _re.I):
        h = m.group(1).lower().strip(".")
        if "." not in h or h.startswith("checkout.") or h.startswith("cdn."):
            continue
        if any(bad in h for bad in _SHOP_APP_SKIP):
            continue
        counts[h] = counts.get(h, 0) + 1
    vanity = max(counts, key=counts.get) if counts else None

    myshopify = None
    mm = _re.search(r'([a-z0-9][a-z0-9\-]*\.myshopify\.com)', text, _re.I)
    if mm:
        myshopify = mm.group(1).lower()

    return (vanity or myshopify), status


def _shop_app_children() -> tuple:
    """(children list, index http status) for the storefronts sitemap index."""
    import re as _re
    idx_status, idx_text = _shop_app_get(_STOREFRONTS_INDEX)
    children = [l for l in _re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", idx_text or "", _re.I)
                if l.endswith(".xml") or l.endswith(".gz")]
    return children, idx_status


def _shop_app_count() -> dict:
    """Count every storefront handle Shop App publishes — the discovery ceiling.
    Cheap: 10-ish gzipped sitemaps, no per-store page fetches."""
    import re as _re
    children, idx_status = _shop_app_children()
    if not children:
        return {"total_handles": 0, "children": 0, "note": f"index unreadable (HTTP {idx_status})"}
    per_child = []
    total = 0
    for c in children:
        st, txt = _shop_app_get(c)
        n = len(_re.findall(r"<loc>[^<]*?/m/", txt or "", _re.I))
        per_child.append({"child": c.rsplit("/", 1)[-1], "handles": n, "status": st})
        total += n
    return {"total_handles": total, "children": len(children), "per_child": per_child}


def _shop_app_harvest(cursor: dict, limit: int) -> dict:
    """Cheap bulk harvest: read one child sitemap and return a page of
    shop.app/m/{handle} refs, advancing a {child, offset} cursor. No per-store
    fetches — this is how discovery scales to the full ceiling fast."""
    import re as _re
    cursor = cursor or {}
    child_i = int(cursor.get("child", 0))
    offset = int(cursor.get("offset", 0))

    children, idx_status = _shop_app_children()
    if not children:
        return {"refs": [], "cursor": cursor, "note": f"index unreadable (HTTP {idx_status})"}

    child_i %= len(children)
    _, ch_text = _shop_app_get(children[child_i])
    handles = _re.findall(r"<loc>\s*([^<\s]+/m/[^<\s]+)\s*</loc>", ch_text or "", _re.I)
    if not handles:
        return {"refs": [], "cursor": {"child": (child_i + 1) % len(children), "offset": 0},
                "child_total": 0}

    refs = handles[offset: offset + limit]
    new_offset = offset + len(refs)
    if new_offset >= len(handles):
        new_cursor = {"child": (child_i + 1) % len(children), "offset": 0}
    else:
        new_cursor = {"child": child_i, "offset": new_offset}
    return {"refs": refs, "cursor": new_cursor, "child": child_i, "child_total": len(handles)}


def _shop_app_discover(cursor: dict, limit: int) -> dict:
    """
    Resumable Shop App discovery. Walks the storefronts sitemap:
      index → child .xml.gz → shop.app/m/{handle} pages → resolve real domain.
    The cursor {child, offset} remembers exactly where it stopped, so each run
    continues over time and never rediscovers. Resolves a batch concurrently
    (bounded pool) with a 429 backoff so it moves faster without bursting.
    """
    import re as _re
    from concurrent.futures import ThreadPoolExecutor

    cursor = cursor or {}
    child_i = int(cursor.get("child", 0))
    offset = int(cursor.get("offset", 0))
    batch = max(1, min(limit, 50))

    children, idx_status = _shop_app_children()
    if not children:
        return {"domains": [], "cursor": cursor,
                "note": f"storefronts index unreadable (HTTP {idx_status})"}

    child_i %= len(children)
    ch_status, ch_text = _shop_app_get(children[child_i])
    handles = _re.findall(r"<loc>\s*([^<\s]+/m/[^<\s]+)\s*</loc>", ch_text or "", _re.I)
    if not handles:
        return {"domains": [], "cursor": {"child": (child_i + 1) % len(children), "offset": 0},
                "note": f"child {child_i} empty (HTTP {ch_status})"}

    slice_ = handles[offset: offset + batch]
    domains: list = []
    resolved = rate_limited = no_domain = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        for d, st in pool.map(lambda h: _shop_app_resolve_one(h), slice_):
            if d:
                domains.append(d)
                resolved += 1
            elif st == 429:
                rate_limited += 1
            else:
                no_domain += 1

    new_offset = offset + len(slice_)
    if new_offset >= len(handles):
        new_cursor = {"child": (child_i + 1) % len(children), "offset": 0}
    else:
        new_cursor = {"child": child_i, "offset": new_offset}

    domains = list(dict.fromkeys(domains))
    note = None
    if rate_limited:
        note = f"{rate_limited}/{len(slice_)} rate-limited (429)"
    return {"domains": domains, "cursor": new_cursor,
            "processed": len(slice_), "resolved": resolved,
            "rate_limited": rate_limited, "no_domain": no_domain,
            "child": child_i, "child_total": len(handles), "note": note}


@router.post("/debug-fetch")
def debug_fetch(body: dict, x_internal_token: str = Header(...)):
    """
    Diagnostic endpoint: run fetch_products_shopify against any store_url and
    return the full result including product count and any failure details.
    Does NOT write to DB. Use for live testing without Celery.

    Body: {"store_url": "https://gymshark.com"}
    """
    _require_internal(x_internal_token)
    import time as _time

    store_url = (body.get("store_url") or "").strip()
    if not store_url:
        raise HTTPException(status_code=400, detail="store_url required")

    logger.info("[DEBUG_FETCH] store_url=%r", store_url)
    t0 = _time.monotonic()

    try:
        raw = fetch_products_shopify(store_url)
        elapsed = round(_time.monotonic() - t0, 2)
        n = len(raw)
        logger.info("[DEBUG_FETCH] done in %ss products=%d", elapsed, n)

        result = {
            "store_url": store_url,
            "elapsed_seconds": elapsed,
            "products_returned": n,
            "status": "ok" if n > 0 else "empty",
        }
        if n > 0:
            result["first_product_title"] = raw[0].get("title")
            result["first_product_updated_at"] = raw[0].get("updated_at")
        return result

    except Exception as exc:
        elapsed = round(_time.monotonic() - t0, 2)
        logger.error("[DEBUG_FETCH] exception after %ss: %s\n%s", elapsed, exc, traceback.format_exc())
        return {
            "store_url": store_url,
            "elapsed_seconds": elapsed,
            "products_returned": 0,
            "status": "exception",
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }


def _mark_error(db, competitor_id: str, message: str) -> None:
    try:
        db.table("competitors").update({
            "scan_status": "error",
            "error_message": message[:500],
        }).eq("id", competitor_id).execute()
    except Exception:
        pass


def _interval_for_tier(tier: str, settings) -> int:
    return {"pro": settings.pro_scan_interval_hours, "agency": settings.agency_scan_interval_hours}.get(
        tier, settings.free_scan_interval_hours
    )
