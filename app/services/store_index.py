"""
Verified Shopify store index — light discovery/indexing pass.

This is deliberately NOT the tracked-competitor scan pipeline. One indexing
pass makes at most 4 polite requests to a domain (homepage, /cart.js,
/products.json?limit=250, /collections.json), computes a multi-signal Shopify
confidence score from those same responses (no duplicate probes), extracts a
light profile (brand, rough catalog stats, taxonomy hints), classifies the
store, and upserts it into shopify_store_index.

Rows here compound into StoreScout's proprietary store database, which powers
index-first competitor discovery.
"""
from __future__ import annotations

import logging
import re
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.services.fetch import (
    IMPERSONATE,
    _USE_CURL_CFFI,
    _enforce_domain_rate_limit,
    _headers,
)

if _USE_CURL_CFFI:
    from curl_cffi.requests import Session as CurlSession
else:
    import httpx

logger = logging.getLogger(__name__)

# ── Sources ────────────────────────────────────────────────────────────────

# Niche queries the candidate generator rotates through. These describe
# MARKETS, not platforms — platform verification is our job, not the AI's.
SEED_QUERIES = [
    "fitness apparel",
    "skincare brand",
    "supplements store",
    "jewelry brand",
    "coffee store",
    "pet products store",
    "home decor store",
    "streetwear brand",
    "activewear brand",
    "beauty store",
]

# ── Taxonomy ───────────────────────────────────────────────────────────────
# Fixed list keeps index search consistent — classification must map into
# these, never invent new categories.

CATEGORY_TAXONOMY: Dict[str, List[str]] = {
    "Fitness Apparel":       ["Activewear", "Gym Accessories"],
    "Beauty":                ["Skincare", "Cosmetics", "Haircare"],
    "Food & Beverage":       ["Coffee", "Snacks", "Alcohol", "Tea"],
    "Pets":                  ["Pet Accessories", "Pet Food"],
    "Fashion":               ["Streetwear", "Womenswear", "Menswear", "Footwear"],
    "Jewelry":               ["Fine Jewelry", "Fashion Jewelry", "Watches"],
    "Home & Living":         ["Home Decor", "Kitchen", "Bedding", "Furniture"],
    "Supplements":           ["Sports Nutrition", "Vitamins", "Wellness"],
    "Kids & Baby":           ["Baby Gear", "Kids Apparel", "Toys"],
    "Outdoors":              ["Camping", "Cycling", "Water Sports"],
    "Electronics & Gadgets": ["Audio", "Accessories", "Smart Home"],
    "Other":                 ["General"],
}

# keyword → (category, subcategory). Checked against title + description +
# product types + tags + collections, longest keywords first so "pet food"
# beats "food".
_RULE_KEYWORDS: List[tuple] = [
    ("activewear",        ("Fitness Apparel", "Activewear")),
    ("gym wear",          ("Fitness Apparel", "Activewear")),
    ("fitness apparel",   ("Fitness Apparel", "Activewear")),
    ("leggings",          ("Fitness Apparel", "Activewear")),
    ("sports bra",        ("Fitness Apparel", "Activewear")),
    ("skincare",          ("Beauty", "Skincare")),
    ("skin care",         ("Beauty", "Skincare")),
    ("serum",             ("Beauty", "Skincare")),
    ("cosmetic",          ("Beauty", "Cosmetics")),
    ("makeup",            ("Beauty", "Cosmetics")),
    ("haircare",          ("Beauty", "Haircare")),
    ("shampoo",           ("Beauty", "Haircare")),
    ("coffee",            ("Food & Beverage", "Coffee")),
    ("espresso",          ("Food & Beverage", "Coffee")),
    ("tea",               ("Food & Beverage", "Tea")),
    ("snack",             ("Food & Beverage", "Snacks")),
    ("pet food",          ("Pets", "Pet Food")),
    ("dog treat",         ("Pets", "Pet Food")),
    ("pet",               ("Pets", "Pet Accessories")),
    ("dog",               ("Pets", "Pet Accessories")),
    ("cat",               ("Pets", "Pet Accessories")),
    ("streetwear",        ("Fashion", "Streetwear")),
    ("sneaker",           ("Fashion", "Footwear")),
    ("footwear",          ("Fashion", "Footwear")),
    ("womenswear",        ("Fashion", "Womenswear")),
    ("menswear",          ("Fashion", "Menswear")),
    ("jewelry",           ("Jewelry", "Fashion Jewelry")),
    ("jewellery",         ("Jewelry", "Fashion Jewelry")),
    ("necklace",          ("Jewelry", "Fashion Jewelry")),
    ("watch",             ("Jewelry", "Watches")),
    ("home decor",        ("Home & Living", "Home Decor")),
    ("candle",            ("Home & Living", "Home Decor")),
    ("bedding",           ("Home & Living", "Bedding")),
    ("kitchen",           ("Home & Living", "Kitchen")),
    ("furniture",         ("Home & Living", "Furniture")),
    ("supplement",        ("Supplements", "Sports Nutrition")),
    ("protein",           ("Supplements", "Sports Nutrition")),
    ("pre-workout",       ("Supplements", "Sports Nutrition")),
    ("preworkout",        ("Supplements", "Sports Nutrition")),
    ("creatine",          ("Supplements", "Sports Nutrition")),
    ("vitamin",           ("Supplements", "Vitamins")),
    ("wellness",          ("Supplements", "Wellness")),
    ("baby",              ("Kids & Baby", "Baby Gear")),
    ("kids",              ("Kids & Baby", "Kids Apparel")),
    ("toy",               ("Kids & Baby", "Toys")),
    ("camping",           ("Outdoors", "Camping")),
    ("hiking",            ("Outdoors", "Camping")),
    ("cycling",           ("Outdoors", "Cycling")),
    ("surf",              ("Outdoors", "Water Sports")),
    ("headphone",         ("Electronics & Gadgets", "Audio")),
    ("speaker",           ("Electronics & Gadgets", "Audio")),
    ("smart home",        ("Electronics & Gadgets", "Smart Home")),
    ("phone case",        ("Electronics & Gadgets", "Accessories")),
]


# ── Helpers ────────────────────────────────────────────────────────────────

def normalize_domain(url_or_domain: str) -> str:
    """'https://www.Gymshark.com/collections/x' → 'gymshark.com'."""
    d = (url_or_domain or "").strip().lower()
    if "//" in d:
        d = urlparse(d).netloc or d
    d = d.split("/")[0].split("?")[0].strip(".")
    return d[4:] if d.startswith("www.") else d


def _make_client():
    if _USE_CURL_CFFI:
        return CurlSession(impersonate=IMPERSONATE, headers=_headers())
    return httpx.Client(timeout=12.0, headers=_headers(), follow_redirects=True)


def _get(client, url: str, timeout: int = 12):
    if _USE_CURL_CFFI:
        return client.get(url, timeout=timeout, allow_redirects=True)
    return client.get(url)


_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_DESC_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', re.IGNORECASE | re.DOTALL
)
_META_DESC_RE2 = re.compile(
    r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']', re.IGNORECASE | re.DOTALL
)
_OG_SITE_RE = re.compile(
    r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\'](.*?)["\']', re.IGNORECASE
)
_LANG_RE = re.compile(r"<html[^>]+lang=[\"']([a-zA-Z-]{2,8})[\"']", re.IGNORECASE)


def _clean(text: str, max_len: int = 300) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:max_len]


# ── The light pass ─────────────────────────────────────────────────────────

def index_store_pass(domain: str) -> Dict[str, Any]:
    """
    One polite ≤4-request pass over a domain: verification signals + light
    profile together. Returns a dict with:
      reachable, confidence (0-100), signals [str], monitorable (bool),
      profile {...light-scan fields}, failure_reason (when not reachable)
    """
    domain = normalize_domain(domain)
    _enforce_domain_rate_limit(domain)

    confidence = 0
    signals: List[str] = []
    profile: Dict[str, Any] = {"homepage_url": f"https://{domain}"}
    reachable = False
    products_ok = False

    with _make_client() as client:
        # 1. Homepage — brand identity + HTML fingerprints
        html = ""
        try:
            r = _get(client, f"https://{domain}/")
            if r.status_code in (200, 403):
                reachable = True
            if r.status_code == 200:
                html = (r.text or "")[:400_000]
        except Exception as exc:
            logger.debug("index pass homepage failed for %s: %s", domain, exc)

        if html:
            if "cdn.shopify.com" in html or "cdn/shop/" in html:
                confidence += 25
                signals.append("Shopify CDN detected")
            if "Shopify.theme" in html or "window.Shopify" in html or "shopify-features" in html:
                confidence += 25
                signals.append("Shopify theme detected")
            if "shop_pay" in html or "shop-pay" in html or "shopify-payment-button" in html:
                confidence += 15
                signals.append("Shop Pay detected")
            if ".myshopify.com" in html:
                confidence += 15
                signals.append("Shopify backend domain detected")

            m = _OG_SITE_RE.search(html)
            title_m = _TITLE_RE.search(html)
            title = _clean(title_m.group(1), 150) if title_m else ""
            profile["page_title"] = title
            profile["brand_name"] = _clean(m.group(1), 80) if m else (title.split("|")[0].split("–")[0].strip()[:80] or None)
            desc_m = _META_DESC_RE.search(html) or _META_DESC_RE2.search(html)
            if desc_m:
                profile["meta_description"] = _clean(desc_m.group(1))
            lang_m = _LANG_RE.search(html)
            if lang_m:
                profile["language"] = lang_m.group(1)[:8]

        # 2. /cart.js — storefront API marker
        try:
            r = _get(client, f"https://{domain}/cart.js", timeout=8)
            if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
                data = r.json()
                if isinstance(data, dict) and "token" in data:
                    reachable = True
                    confidence += 20
                    signals.append("Storefront API detected")
                    if isinstance(data.get("currency"), str):
                        profile["currency"] = data["currency"][:6]
        except Exception:
            pass

        # 3. /products.json — catalog sample (also the "monitorable" signal)
        products: List[dict] = []
        try:
            r = _get(client, f"https://{domain}/products.json?limit=250", timeout=15)
            ct = r.headers.get("content-type", "")
            if r.status_code == 200 and "application/json" in ct:
                data = r.json()
                if isinstance(data, dict) and "products" in data:
                    reachable = True
                    products_ok = True
                    confidence += 55
                    signals.append("Product catalog accessible")
                    products = data.get("products") or []
            elif r.status_code == 403:
                # Bot-protected probe — Shopify-shaped; full scanner usually gets in
                reachable = True
                confidence += 35
                signals.append("Storefront responds (bot-protected)")
        except Exception:
            pass

        if products:
            prices: List[float] = []
            promo = 0
            types: Dict[str, int] = {}
            tags: Dict[str, int] = {}
            vendors: Dict[str, int] = {}
            for p in products:
                variants = p.get("variants") or []
                v_prices = []
                has_promo = False
                for v in variants:
                    try:
                        vp = float(v.get("price") or 0)
                    except (TypeError, ValueError):
                        continue
                    if vp > 0:
                        v_prices.append(vp)
                    try:
                        ca = float(v.get("compare_at_price") or 0)
                    except (TypeError, ValueError):
                        ca = 0
                    if ca and vp and ca > vp:
                        has_promo = True
                if v_prices:
                    prices.append(min(v_prices))
                if has_promo:
                    promo += 1
                pt = (p.get("product_type") or "").strip()
                if pt:
                    types[pt] = types.get(pt, 0) + 1
                vn = (p.get("vendor") or "").strip()
                if vn:
                    vendors[vn] = vendors.get(vn, 0) + 1
                for t in (p.get("tags") or [])[:10] if isinstance(p.get("tags"), list) else []:
                    t = str(t).strip()
                    if t:
                        tags[t] = tags.get(t, 0) + 1

            # 250 returned means the catalog is AT LEAST 250 — rough count by design
            profile["product_count"] = len(products)
            if prices:
                profile["median_price"] = round(statistics.median(prices), 2)
                profile["min_price"] = round(min(prices), 2)
                profile["max_price"] = round(max(prices), 2)
            profile["promo_rate"] = round(promo / len(products) * 100, 1) if products else None
            top = lambda d, n: [k for k, _ in sorted(d.items(), key=lambda kv: -kv[1])[:n]]
            profile["product_types"] = top(types, 15)
            profile["tags"] = top(tags, 20)
            profile["vendors"] = top(vendors, 10)

        # 4. /collections.json — taxonomy hints (only worth it on a live catalog)
        if products_ok:
            try:
                r = _get(client, f"https://{domain}/collections.json?limit=50", timeout=10)
                if r.status_code == 200 and "application/json" in r.headers.get("content-type", ""):
                    cols = (r.json().get("collections") or [])[:20]
                    profile["collections"] = [
                        {"handle": c.get("handle"), "title": c.get("title")} for c in cols
                    ]
            except Exception:
                pass

    confidence = min(100, confidence)
    return {
        "reachable": reachable,
        "confidence": confidence,
        "signals": signals,
        "monitorable": products_ok or "Storefront responds (bot-protected)" in signals,
        "profile": profile,
        "failure_reason": None if reachable else "unreachable_or_dns",
    }


# ── Market context ─────────────────────────────────────────────────────────

def derive_market_context(product_count: Optional[int], median_price: Optional[float]) -> Dict[str, Optional[str]]:
    """
    Honest heuristics from the light sample — estimates, not claims.

    product_count from the light pass caps at 250 (the products.json sample
    limit), so hitting the cap reads as a very large catalog. Tracked-store
    upserts pass the TRUE catalog count, which sharpens the estimate.
    """
    stage: Optional[str] = None
    if product_count is not None and product_count > 0:
        if product_count < 30:
            stage = "startup"
        elif product_count < 150:
            stage = "growing"
        elif product_count < 800:
            stage = "established"
        else:
            stage = "enterprise"

    tier: Optional[str] = None
    if median_price:
        if median_price < 25:
            tier = "budget"
        elif median_price < 75:
            tier = "mid-market"
        elif median_price < 200:
            tier = "premium"
        else:
            tier = "luxury"

    return {"business_stage": stage, "pricing_tier": tier}


# ── Classification ─────────────────────────────────────────────────────────

def classify_store(
    title: str = "",
    description: str = "",
    product_types: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    collections: Optional[List[dict]] = None,
    vendors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Rules first; one small Haiku call only when rules can't decide.
    Always returns a category/subcategory from CATEGORY_TAXONOMY."""
    haystack = " ".join(
        [
            title or "",
            description or "",
            " ".join(product_types or []),
            " ".join(tags or [])[:500],
            " ".join((c.get("title") or "") for c in (collections or [])),
        ]
    ).lower()

    for keyword, (cat, sub) in sorted(_RULE_KEYWORDS, key=lambda kv: -len(kv[0])):
        if keyword in haystack:
            return {"category": cat, "subcategory": sub, "description": _clean(description, 200) or None, "method": "rules"}

    # AI fallback — tiny, single-store call
    try:
        from app.core.config import get_settings
        settings = get_settings()
        if settings.anthropic_api_key and haystack.strip():
            import json as _json
            import anthropic
            taxonomy = "; ".join(f"{c}: {', '.join(subs)}" for c, subs in CATEGORY_TAXONOMY.items())
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=150,
                messages=[{
                    "role": "user",
                    "content": (
                        "Classify this ecommerce store into EXACTLY one category and subcategory "
                        f"from this taxonomy: {taxonomy}\n\n"
                        f"Store info: {haystack[:1200]}\n\n"
                        'Return ONLY JSON: {"category": "...", "subcategory": "...", "description": "one short sentence"}'
                    ),
                }],
            )
            text = msg.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = _json.loads(text)
            cat = parsed.get("category")
            if cat in CATEGORY_TAXONOMY:
                sub = parsed.get("subcategory")
                if sub not in CATEGORY_TAXONOMY[cat]:
                    sub = CATEGORY_TAXONOMY[cat][0]
                return {
                    "category": cat,
                    "subcategory": sub,
                    "description": _clean(parsed.get("description") or description, 200) or None,
                    "method": "ai",
                }
    except Exception as exc:
        logger.debug("classify_store AI fallback failed: %s", exc)

    return {"category": "Other", "subcategory": "General", "description": _clean(description, 200) or None, "method": "fallback"}


# ── Upsert ─────────────────────────────────────────────────────────────────

def upsert_index_row(db, domain: str, fields: Dict[str, Any]) -> str:
    """
    Upsert by domain. Returns 'inserted' | 'updated' | 'skipped'.
    Never downgrades a verified row back to candidate — a fresher verified/
    rejected/failed result always wins, but a mere re-candidate does not.
    """
    domain = normalize_domain(domain)
    if not domain or "." not in domain:
        return "skipped"

    now = datetime.now(timezone.utc).isoformat()
    # Drop unset fields so partial updates don't blank existing data — but keep
    # an explicit failure_reason=None, which clears a stale reason on re-verify.
    fields = {k: v for k, v in fields.items() if v is not None or k == "failure_reason"}
    fields["domain"] = domain
    fields["updated_at"] = now

    existing = None
    try:
        res = db.table("shopify_store_index").select("id, status").eq("domain", domain).maybe_single().execute()
        existing = res.data if res else None
    except Exception:
        existing = None

    # Columns added by later migrations (008: business_stage/pricing_tier/
    # expanded_at) may not exist yet — retry without them so the index keeps
    # working during the migration window.
    _NEWER_COLS = ("business_stage", "pricing_tier", "expanded_at")

    def _write(payload: Dict[str, Any]) -> None:
        if existing:
            db.table("shopify_store_index").update(payload).eq("domain", domain).execute()
        else:
            db.table("shopify_store_index").insert(payload).execute()

    if existing and existing.get("status") == "verified" and fields.get("status") == "candidate":
        return "skipped"

    try:
        _write(fields)
    except Exception as exc:
        stripped = {k: v for k, v in fields.items() if k not in _NEWER_COLS}
        if len(stripped) == len(fields):
            raise
        logger.debug("upsert retry without newer columns for %s: %s", domain, exc)
        _write(stripped)

    return "updated" if existing else "inserted"


def process_domain_into_index(db, domain: str, source: str, source_query: Optional[str] = None) -> Dict[str, Any]:
    """
    Full pipeline for one domain: light pass → threshold → classify → upsert.
    Returns {domain, outcome: verified|rejected|failed, confidence}.
    Used by the internal endpoint (web process) and admin test runs.
    """
    from app.core.config import get_settings
    settings = get_settings()
    domain = normalize_domain(domain)
    now = datetime.now(timezone.utc).isoformat()

    try:
        result = index_store_pass(domain)
    except Exception as exc:
        logger.warning("index pass crashed for %s: %s", domain, exc)
        upsert_index_row(db, domain, {
            "status": "failed", "failure_reason": f"pass_error: {exc}"[:300],
            "source": source, "source_query": source_query, "last_verified_at": now,
        })
        return {"domain": domain, "outcome": "failed", "confidence": 0}

    if not result["reachable"]:
        upsert_index_row(db, domain, {
            "status": "failed", "failure_reason": result["failure_reason"] or "unreachable",
            "source": source, "source_query": source_query, "last_verified_at": now,
        })
        return {"domain": domain, "outcome": "failed", "confidence": 0}

    confidence = result["confidence"]
    profile = result["profile"]

    if confidence < settings.shopify_index_min_confidence:
        upsert_index_row(db, domain, {
            "status": "rejected",
            "failure_reason": f"confidence {confidence} below threshold {settings.shopify_index_min_confidence}",
            "verification_confidence": confidence,
            "verification_signals": result["signals"],
            "brand_name": profile.get("brand_name"),
            "source": source, "source_query": source_query, "last_verified_at": now,
        })
        return {"domain": domain, "outcome": "rejected", "confidence": confidence}

    classification = classify_store(
        title=profile.get("page_title", ""),
        description=profile.get("meta_description", ""),
        product_types=profile.get("product_types"),
        tags=profile.get("tags"),
        collections=profile.get("collections"),
        vendors=profile.get("vendors"),
    )
    market = derive_market_context(profile.get("product_count"), profile.get("median_price"))

    upsert_index_row(db, domain, {
        "status": "verified",
        "failure_reason": None,
        "business_stage": market["business_stage"],
        "pricing_tier": market["pricing_tier"],
        "brand_name": profile.get("brand_name"),
        "homepage_url": profile.get("homepage_url"),
        "category": classification["category"],
        "subcategory": classification["subcategory"],
        "description": classification["description"] or profile.get("meta_description"),
        "language": profile.get("language"),
        "product_count": profile.get("product_count"),
        "median_price": profile.get("median_price"),
        "min_price": profile.get("min_price"),
        "max_price": profile.get("max_price"),
        "promo_rate": profile.get("promo_rate"),
        "collections": profile.get("collections"),
        "product_types": profile.get("product_types"),
        "tags": profile.get("tags"),
        "vendors": profile.get("vendors"),
        "verification_confidence": confidence,
        "verification_signals": result["signals"],
        "source": source,
        "source_query": source_query,
        "last_verified_at": now,
        "last_light_scanned_at": now,
    })
    return {"domain": domain, "outcome": "verified", "confidence": confidence}
