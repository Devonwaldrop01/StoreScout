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
    "Fitness Apparel":       ["Activewear", "Gym Accessories", "Athleisure"],
    "Fashion":               ["Womenswear", "Menswear", "Streetwear", "Swimwear", "Lingerie", "Outerwear", "Denim"],
    "Footwear":              ["Sneakers", "Sandals", "Boots", "Heels", "Kids Shoes"],
    "Accessories":           ["Bags", "Sunglasses", "Wallets", "Hats", "Belts", "Scarves"],
    "Jewelry":               ["Fine Jewelry", "Fashion Jewelry", "Watches", "Engagement"],
    "Beauty":                ["Skincare", "Cosmetics", "Haircare", "Fragrance", "Nails", "Tools"],
    "Health & Personal Care":["Personal Care", "Sexual Wellness", "Oral Care", "Medical", "Vision"],
    "Supplements":           ["Sports Nutrition", "Vitamins", "Wellness", "Protein"],
    "Food & Beverage":       ["Coffee", "Tea", "Snacks", "Alcohol", "Condiments", "Beverages", "Candy"],
    "Pets":                  ["Pet Accessories", "Pet Food", "Pet Toys", "Pet Health"],
    "Home & Living":         ["Home Decor", "Kitchen", "Bedding", "Furniture", "Bath", "Candles", "Cleaning"],
    "Home Improvement":      ["Tools", "Hardware", "Lighting", "Doors & Windows", "Garden"],
    "Kids & Baby":           ["Baby Gear", "Kids Apparel", "Nursery", "Maternity", "Feeding"],
    "Toys & Games":          ["Toys", "Board Games", "Puzzles", "Collectibles", "Hobbies"],
    "Outdoors":              ["Camping", "Cycling", "Water Sports", "Hunting & Fishing", "Hiking"],
    "Sporting Goods":        ["Equipment", "Team Sports", "Golf", "Combat Sports"],
    "Electronics & Gadgets": ["Audio", "Wearables", "Smart Home", "Computers", "Cameras"],
    "Tech Accessories":      ["Phone Cases", "Chargers & Cables", "Mounts", "Screen Protectors"],
    "Automotive":            ["Car Accessories", "Parts", "Motorcycle", "Detailing"],
    "Arts & Crafts":         ["Craft Supplies", "Stationery", "Art", "Sewing"],
    "Books & Media":         ["Books", "Music", "Films", "Games"],
    "Adult":                 ["General"],
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

            # Commercial signals for lead scoring — proof of budget/marketing
            # maturity + a contact. Extracted from the homepage we already have,
            # so near-zero added cost.
            commercial = extract_commercial_signals(html, domain)
            profile["tech_signals"] = commercial["tech_signals"]
            profile["contact_email"] = commercial["contact_email"]
            profile["contact_source"] = commercial["contact_source"]
            profile["sells_wholesale"] = commercial["sells_wholesale"]
            profile["multi_market"] = commercial["multi_market"]

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
            titles: List[str] = []
            for p in products:
                _t = (p.get("title") or "").strip()
                if _t and len(titles) < 40:
                    titles.append(_t[:80])
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
                # Persist price quartiles now — the knowledge stage classifies
                # from stored data and never re-fetches, so price bands have to
                # be captured here while the sample is in hand.
                _sp = sorted(prices)
                _q = lambda f: round(_sp[min(len(_sp) - 1, int(f * (len(_sp) - 1)))], 2)
                profile["price_p25"] = _q(0.25)
                profile["price_p75"] = _q(0.75)
            profile["promo_rate"] = round(promo / len(products) * 100, 1) if products else None
            top = lambda d, n: [k for k, _ in sorted(d.items(), key=lambda kv: -kv[1])[:n]]
            profile["product_types"] = top(types, 15)
            profile["tags"] = top(tags, 20)
            profile["vendors"] = top(vendors, 10)
            profile["product_titles"] = titles

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


# ── Commercial signals (lead-quality intelligence) ─────────────────────────
# What a merchant spends money on tells us far more about whether they'll BUY
# than how big their catalog is. These footprints are the highest-signal, and
# they're free — the homepage is already fetched for verification.

# marker substrings → (signal key, category). Category groups feed scoring.
_TECH_MARKERS: List[tuple] = [
    ("klaviyo", ("klaviyo", "email_marketing")),
    ("attentive", ("attentive", "sms_marketing")),
    ("postscript", ("postscript", "sms_marketing")),
    ("connect.facebook.net", ("meta_pixel", "paid_ads")),
    ("fbevents.js", ("meta_pixel", "paid_ads")),
    ("analytics.tiktok.com", ("tiktok_pixel", "paid_ads")),
    ("snap.licdn.com", ("linkedin_pixel", "paid_ads")),
    ("googletagmanager.com", ("gtm", "analytics")),
    ("gtag(", ("google_ads", "paid_ads")),
    ("judge.me", ("judgeme", "reviews")),
    ("yotpo", ("yotpo", "reviews")),
    ("stamped.io", ("stamped", "reviews")),
    ("loox", ("loox", "reviews")),
    ("okendo", ("okendo", "reviews")),
    ("reviews.io", ("reviewsio", "reviews")),
    ("rechargecdn", ("recharge", "subscriptions")),
    ("recharge.com", ("recharge", "subscriptions")),
    ("appstle", ("appstle", "subscriptions")),
    ("seal-subscriptions", ("seal", "subscriptions")),
    ("gorgias", ("gorgias", "support")),
    ("intercom", ("intercom", "support")),
    ("tidio", ("tidio", "support")),
    ("zendesk", ("zendesk", "support")),
    ("privy", ("privy", "email_capture")),
    ("justuno", ("justuno", "email_capture")),
    ("optinmonster", ("optinmonster", "email_capture")),
    ("rebuy", ("rebuy", "upsell")),
    ("zipify", ("zipify", "upsell")),
    ("aftersell", ("aftersell", "upsell")),
    ("bold", ("bold", "upsell")),
]

_EMAIL_RE = re.compile(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", re.I)
_MAILTO_RE = re.compile(r'mailto:([a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,})', re.I)
_EMAIL_JUNK = ("example.com", "sentry", "wixpress", "godaddy", "your-email",
               "email.com", "domain.com", "shopify.com", "@2x", "sentry.io",
               "wordpress", "squarespace", "test.com")
_PREFERRED_INBOX = ("hello@", "info@", "contact@", "support@", "sales@", "team@", "hi@")


def extract_commercial_signals(html: str, domain: str) -> Dict[str, Any]:
    """Detect budget/marketing footprints, a contact email, wholesale posture,
    and multi-market presence from a storefront's HTML."""
    h = (html or "").lower()
    tech: List[str] = []
    cats = set()
    for marker, (key, cat) in _TECH_MARKERS:
        if marker in h and key not in tech:
            tech.append(key)
            cats.add(cat)

    # Contact email — prefer a mailto, then a role inbox on the brand's domain,
    # then any plausible address; drop obvious junk/vendor addresses.
    email = None
    source = None
    root = normalize_domain(domain).split(":")[0]
    root_base = root[4:] if root.startswith("www.") else root
    candidates = []
    for m in _MAILTO_RE.finditer(html or ""):
        candidates.append(("mailto", m.group(1).lower()))
    for m in _EMAIL_RE.finditer(html or ""):
        candidates.append(("page", m.group(0).lower()))
    for src, cand in candidates:
        if any(j in cand for j in _EMAIL_JUNK):
            continue
        on_brand = root_base.split(".")[0] in cand
        role = any(cand.startswith(p) for p in _PREFERRED_INBOX)
        if email is None:
            email, source = cand, src
        # upgrade to an on-brand role inbox if we find one
        if on_brand and role:
            email, source = cand, src
            break
        if on_brand and email and root_base.split(".")[0] not in email:
            email, source = cand, src

    sells_wholesale = any(k in h for k in (
        "/pages/wholesale", "wholesale enquir", "wholesale inquir",
        "trade account", "become a stockist", "minimum order quantity", "b2b portal"))
    # Multi-market: several hreflang alternates or Shopify markets selector.
    multi_market = h.count("hreflang=") >= 3 or "localization" in h and "country" in h

    return {
        "tech_signals": tech,
        "tech_categories": sorted(cats),
        "contact_email": email,
        "contact_source": source,
        "sells_wholesale": sells_wholesale,
        "multi_market": bool(multi_market),
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


# ── Multi-signal classification (confidence + evidence) ────────────────────
# The old classifier took the FIRST keyword hit anywhere in the text, so a
# single stray word ("gift" on a pet store) could misclassify — that's how
# Everlane ends up recommended for pet accessories. v2 SCORES every category
# by weighted evidence across distinct signals and only commits when the
# winner clearly leads, recording exactly why.

# Signal weights: what a merchant DECLARES (product_type) counts far more than
# an incidental homepage word.
_SIGNAL_WEIGHT = {
    "product_type": 4,   # merchant-assigned; strongest
    "product_title": 2,
    "collection": 2,
    "tag": 1,
    "homepage": 1,
}


def classify_store_v2(
    title: str = "",
    description: str = "",
    homepage_text: str = "",
    product_types: Optional[List[str]] = None,
    product_titles: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    collections: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    """
    Score every taxonomy category by weighted keyword evidence across distinct
    signals. Returns {category, subcategory, confidence (0-100),
    evidence: [{signal, detail, category}], method}. Confidence reflects how
    decisively the winner beat the field AND how much evidence backed it —
    thin or contested classifications score low so callers can withhold them.
    """
    signals: List[tuple] = []  # (signal_kind, text)
    for pt in (product_types or []):
        signals.append(("product_type", str(pt).lower()))
    for t in (product_titles or [])[:60]:
        signals.append(("product_title", str(t).lower()))
    for c in (collections or []):
        signals.append(("collection", str(c.get("title") or "").lower()))
    for tg in (tags or [])[:40]:
        signals.append(("tag", str(tg).lower()))
    hp = " ".join([title or "", description or "", homepage_text or ""]).lower()
    if hp.strip():
        signals.append(("homepage", hp[:2000]))

    scores: Dict[str, float] = {}
    sub_hits: Dict[str, Dict[str, int]] = {}
    evidence: Dict[str, List[dict]] = {}

    for kind, text in signals:
        w = _SIGNAL_WEIGHT.get(kind, 1)
        for keyword, (cat, sub) in _RULE_KEYWORDS:
            if keyword in text:
                scores[cat] = scores.get(cat, 0) + w
                sub_hits.setdefault(cat, {})
                sub_hits[cat][sub] = sub_hits[cat].get(sub, 0) + w
                evidence.setdefault(cat, [])
                # keep the strongest few distinct evidence items per category
                if len(evidence[cat]) < 6 and not any(e["detail"] == keyword for e in evidence[cat]):
                    evidence[cat].append({"signal": kind, "detail": keyword, "weight": w})

    if not scores:
        return {"category": "Other", "subcategory": "General", "confidence": 0,
                "evidence": [], "method": "no_signal"}

    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    winner, top = ranked[0]
    runner = ranked[1][1] if len(ranked) > 1 else 0
    total = sum(scores.values())

    # Confidence blends three things: share of total evidence, margin over the
    # runner-up, and absolute evidence volume (a single hit is never confident).
    share = top / total
    margin = (top - runner) / top if top else 0
    volume = min(1.0, top / 12.0)
    confidence = int(round(100 * (0.45 * share + 0.35 * margin + 0.20 * volume)))
    confidence = max(0, min(100, confidence))

    sub = max(sub_hits.get(winner, {"General": 1}).items(), key=lambda kv: kv[1])[0]
    ev = sorted(evidence.get(winner, []), key=lambda e: -e["weight"])[:6]

    # AI tiebreak ONLY when the top two are close and confidence is middling —
    # cheap, and only where the rules are genuinely uncertain.
    method = "multi_signal"
    if confidence < 70 and runner and (top - runner) <= _SIGNAL_WEIGHT["product_type"]:
        ai = _ai_classify_tiebreak(hp, [winner, ranked[1][0]])
        if ai and ai in scores:
            winner = ai
            sub = max(sub_hits.get(winner, {"General": 1}).items(), key=lambda kv: kv[1])[0]
            ev = sorted(evidence.get(winner, []), key=lambda e: -e["weight"])[:6]
            confidence = max(confidence, 72)
            method = "multi_signal+ai"

    return {
        "category": winner,
        "subcategory": sub,
        "confidence": confidence,
        "evidence": ev,
        "method": method,
    }


def classify_store_ai(
    brand: str = "",
    description: str = "",
    product_types: Optional[List[str]] = None,
    product_titles: Optional[List[str]] = None,
    collections: Optional[List[dict]] = None,
    tags: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    AI-primary classification — the reliable way to KNOW what a store sells.
    Claude reads the store's actual product titles/types/collections (the ground
    truth) and assigns a category + subcategory from the fixed taxonomy, plus a
    confidence and short evidence. It is explicitly told to ignore stray words
    (colour names like 'baby blue', materials, marketing copy) and to return
    'Other' at low confidence rather than guess. Returns None on failure so the
    caller can fall back to the keyword classifier.
    """
    import json as _json
    import anthropic
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.anthropic_api_key:
        return None

    titles = [str(t) for t in (product_titles or [])][:40]
    ptypes = [str(t) for t in (product_types or [])][:20]
    colls = [str(c.get("title") or "") for c in (collections or [])][:20]
    if not (titles or ptypes or colls or (description or "").strip()):
        return None  # nothing to reason over

    taxonomy = "\n".join(f"- {c}: {', '.join(subs)}" for c, subs in CATEGORY_TAXONOMY.items())
    payload = (
        f"STORE: {brand or '(unknown)'}\n"
        f"DESCRIPTION: {(description or '')[:300]}\n"
        f"PRODUCT TYPES: {', '.join(ptypes) or '(none)'}\n"
        f"COLLECTIONS: {', '.join(colls) or '(none)'}\n"
        f"PRODUCT TITLES (the ground truth — judge by these):\n"
        + "\n".join(f"  · {t}" for t in titles[:40])
    )
    prompt = f"""You categorize Shopify stores. Decide what the store ACTUALLY SELLS, based on the product titles and product types — those are the ground truth.

Pick EXACTLY ONE category and one subcategory from this fixed taxonomy:
{taxonomy}

Hard rules:
- Judge by the actual products. If the titles are men's/women's sandals and clothing, it is Footwear or Fashion — NOT Kids & Baby, even if the word "baby" appears in a colour or material.
- IGNORE stray words: colour names ("baby blue", "kids size"), materials, marketing fluff, shipping/returns text.
- If the products are mixed or don't clearly fit, use category "Other" with a LOW confidence. Never guess a specific category you aren't sure of.
- confidence 0-100 = how certain you are. Be honest; a single ambiguous signal is low.

{payload}

Return ONLY JSON:
{{"category": "<exact category>", "subcategory": "<exact subcategory>", "confidence": <0-100>, "evidence": ["<=3 short product-based reasons"]}}"""

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=220,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        p = _json.loads(text)
        cat = str(p.get("category") or "").strip()
        if cat not in CATEGORY_TAXONOMY:
            # Snap to the closest valid category name, else Other.
            cat = next((c for c in CATEGORY_TAXONOMY if c.lower() == cat.lower()), "Other")
        subs = CATEGORY_TAXONOMY[cat]
        sub = str(p.get("subcategory") or "").strip()
        if sub not in subs:
            sub = next((s for s in subs if s.lower() == sub.lower()), subs[0])
        conf = max(0, min(100, int(p.get("confidence") or 0)))
        ev = [{"signal": "ai", "detail": str(e)[:80], "weight": 0} for e in (p.get("evidence") or [])[:3]]
        return {"category": cat, "subcategory": sub, "confidence": conf,
                "evidence": ev, "method": "ai"}
    except Exception as exc:
        logger.debug("classify_store_ai failed: %s", exc)
        return None


def _ai_classify_tiebreak(text: str, candidates: List[str]) -> Optional[str]:
    try:
        from app.core.config import get_settings
        settings = get_settings()
        if not settings.anthropic_api_key or not text.strip():
            return None
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{"role": "user", "content": (
                f"This ecommerce store could be one of: {', '.join(candidates)}. "
                f"Based on this store text, reply with ONLY the single best-fitting one, verbatim.\n\n{text[:1000]}"
            )}],
        )
        ans = msg.content[0].text.strip()
        for c in candidates:
            if c.lower() in ans.lower():
                return c
    except Exception as exc:
        logger.debug("ai tiebreak failed: %s", exc)
    return None


# ── Stage 2: Verification ──────────────────────────────────────────────────
# Turn a DISCOVERED domain into VERIFIED or REJECTED. Verification fetches the
# storefront ONCE and stores the raw signals; it does NOT classify. Every
# rejection records a strict, machine-readable reason. Classification is a
# separate stage that reads those stored signals with zero extra network — the
# memory-efficient split the pipeline is built around.

# Strict rejection codes (mirror the migration comment).
REJECT_DEAD          = "dead_domain"
REJECT_NOT_SHOPIFY   = "not_shopify"
REJECT_NO_PRODUCTS   = "no_products"
REJECT_PASSWORD      = "password_protected"
REJECT_INVALID       = "invalid_storefront"
REJECT_DUPLICATE     = "duplicate"


def _rejection_reason(result: Dict[str, Any]) -> str:
    """Map a light-pass result onto one strict rejection code."""
    if not result.get("reachable"):
        return REJECT_DEAD
    signals = result.get("signals") or []
    profile = result.get("profile") or {}
    shopify_marker = any(
        s in signals for s in (
            "Storefront API detected",
            "Product catalog accessible",
            "Storefront responds (bot-protected)",
        )
    )
    if not shopify_marker:
        return REJECT_NOT_SHOPIFY
    # Shopify-shaped but the catalog came back empty.
    if not profile.get("product_count"):
        return REJECT_NO_PRODUCTS
    return REJECT_INVALID


def verify_and_store(db, domain: str, source: str, source_query: Optional[str] = None) -> Dict[str, Any]:
    """
    Stage 2. Fetch the storefront once; persist a VERIFIED row with raw signals
    (no classification) or a REJECTED row with a reason. Returns
    {domain, outcome: verified|rejected|failed, reason}.
    """
    from app.core.config import get_settings
    settings = get_settings()
    domain = normalize_domain(domain)
    now = datetime.now(timezone.utc).isoformat()

    def _reject(reason: str) -> Dict[str, Any]:
        upsert_index_row(db, domain, {
            "status": "rejected",
            "rejection_reason": reason,
            "failure_reason": reason,
            "source": source, "source_query": source_query,
            "last_verified_at": now, "verified_at": now,
        })
        return {"domain": domain, "outcome": "rejected", "reason": reason}

    try:
        result = index_store_pass(domain)
    except Exception as exc:
        logger.warning("verify pass crashed for %s: %s", domain, exc)
        upsert_index_row(db, domain, {
            "status": "failed", "failure_reason": f"pass_error: {exc}"[:300],
            "rejection_reason": None,
            "source": source, "source_query": source_query,
            "last_verified_at": now, "verified_at": now,
        })
        return {"domain": domain, "outcome": "failed", "reason": "pass_error"}

    confidence = result.get("confidence") or 0
    profile = result.get("profile") or {}

    # Reject anything that fails the storefront bar, or scores below the
    # configured Shopify-confidence threshold.
    if not result.get("reachable") or confidence < settings.shopify_index_min_confidence:
        return _reject(_rejection_reason(result))

    # Duplicate guard: a DIFFERENT domain already verified under the same brand
    # is almost certainly the same merchant (brand.com vs brand.myshopify.com).
    brand = (profile.get("brand_name") or "").strip()
    if brand and len(brand) > 2:
        try:
            dup = db.table("shopify_store_index").select("domain")\
                .eq("brand_name", brand).eq("status", "verified")\
                .neq("domain", domain).limit(1).execute()
            if dup and dup.data:
                return _reject(REJECT_DUPLICATE)
        except Exception:
            pass

    # VERIFIED — store raw signals only. Classification happens in Stage 3.
    market = derive_market_context(profile.get("product_count"), profile.get("median_price"))
    upsert_index_row(db, domain, {
        "status": "verified",
        "rejection_reason": None,
        "failure_reason": None,
        "business_stage": market["business_stage"],
        "pricing_tier": market["pricing_tier"],
        "brand_name": profile.get("brand_name"),
        "homepage_url": profile.get("homepage_url"),
        "homepage_message": profile.get("meta_description"),
        "language": profile.get("language"),
        "product_count": profile.get("product_count"),
        "collection_count": len(profile.get("collections") or []) or None,
        "median_price": profile.get("median_price"),
        "min_price": profile.get("min_price"),
        "max_price": profile.get("max_price"),
        "price_bands": {
            "p25": profile.get("price_p25"),
            "p50": profile.get("median_price"),
            "p75": profile.get("price_p75"),
        } if profile.get("median_price") is not None else None,
        "promo_rate": profile.get("promo_rate"),
        "collections": profile.get("collections"),
        "product_types": profile.get("product_types"),
        "product_titles": profile.get("product_titles"),
        "tags": profile.get("tags"),
        "vendors": profile.get("vendors"),
        "verification_confidence": confidence,
        "verification_signals": result.get("signals"),
        # Commercial signals for lead scoring (migration 018).
        "tech_signals": profile.get("tech_signals"),
        "contact_email": profile.get("contact_email"),
        "contact_source": profile.get("contact_source"),
        "sells_wholesale": profile.get("sells_wholesale"),
        "multi_market": profile.get("multi_market"),
        "source": source,
        "discovery_source": source,
        "source_query": source_query,
        "verified_at": now,
        "last_verified_at": now,
        "last_light_scanned_at": now,
    })
    return {"domain": domain, "outcome": "verified", "reason": None}


# ── Stage 3: Knowledge ─────────────────────────────────────────────────────
# Runs ONLY on verified stores. Its job is understanding, not discovery: it
# reads the raw signals stored at verification and builds a confidence-scored
# category (with evidence), price bands, target customer, and brand keywords —
# no network access at all.

def _derive_target_customer(pricing_tier: Optional[str], category: Optional[str]) -> Optional[str]:
    tier_map = {
        "budget":     "value-conscious shoppers",
        "mid-market": "mainstream shoppers",
        "premium":    "quality-focused buyers",
        "luxury":     "affluent, premium-seeking buyers",
    }
    return tier_map.get(pricing_tier or "")


def _brand_keywords(row: Dict[str, Any], evidence: List[dict]) -> List[str]:
    """Compact, human-readable descriptors — the strongest distinct evidence
    terms plus the merchant's own top product types."""
    kws: List[str] = []
    for e in evidence:
        d = (e.get("detail") or "").strip()
        if d and d not in kws:
            kws.append(d)
    for pt in (row.get("product_types") or []):
        pt = str(pt).strip().lower()
        if pt and pt not in kws:
            kws.append(pt)
        if len(kws) >= 8:
            break
    return kws[:8]


def run_knowledge(db, row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 3. Classify a verified store from its STORED signals (no re-fetch).
    Writes category/subcategory/confidence/evidence, price bands, target
    customer and brand keywords, and stamps knowledge_at. Returns
    {domain, category, confidence}.
    """
    domain = normalize_domain(row.get("domain") or "")
    now = datetime.now(timezone.utc).isoformat()

    # AI-primary classification (reads the real product titles) is far more
    # accurate than keyword matching; fall back to the keyword scorer only if AI
    # is unavailable or errors.
    classification = classify_store_ai(
        brand=row.get("brand_name") or domain,
        description=row.get("homepage_message") or row.get("description") or "",
        product_types=row.get("product_types"),
        product_titles=row.get("product_titles"),
        collections=row.get("collections"),
        tags=row.get("tags"),
    )
    if not classification:
        classification = classify_store_v2(
            title=row.get("brand_name") or "",
            description=row.get("homepage_message") or row.get("description") or "",
            homepage_text=row.get("homepage_message") or "",
            product_types=row.get("product_types"),
            product_titles=row.get("product_titles"),
            tags=row.get("tags"),
            collections=row.get("collections"),
        )

    evidence = classification.get("evidence") or []
    pricing_tier = row.get("pricing_tier") or derive_market_context(
        row.get("product_count"), row.get("median_price")
    )["pricing_tier"]

    price_bands = row.get("price_bands")
    if not price_bands and row.get("median_price") is not None:
        price_bands = {
            "p25": row.get("min_price"),
            "p50": row.get("median_price"),
            "p75": row.get("max_price"),
        }

    brand_keywords = _brand_keywords(row, evidence)
    target_customer = _derive_target_customer(pricing_tier, classification["category"])

    # Store DNA — the semantic business profile that lets the index rank TRUE
    # direct competitors, not just same-category stores. One cheap Haiku call,
    # cached by an input signature so it never re-runs unless the picture
    # changes. Fully guarded: DNA is a bonus layer, never a gate on knowledge.
    dna = dna_kws = dna_sig = None
    try:
        from app.services.store_dna import dna_signature, generate_store_dna
        dna_ctx = {
            "brand_name": row.get("brand_name"), "domain": domain,
            "category": classification["category"],
            "subcategory": classification["subcategory"],
            "pricing_tier": pricing_tier, "median_price": row.get("median_price"),
            "product_count": row.get("product_count"),
            "product_types": row.get("product_types"),
            "product_titles": row.get("product_titles"),
            "collections": row.get("collections"),
            "brand_keywords": brand_keywords, "target_customer": target_customer,
            "homepage_message": row.get("homepage_message"),
            "description": row.get("description"),
        }
        dna_sig = dna_signature(dna_ctx)
        if row.get("dna_signature") == dna_sig and row.get("store_dna"):
            dna, dna_kws = row.get("store_dna"), row.get("dna_keywords")  # unchanged — reuse
        else:
            dna = generate_store_dna(dna_ctx)
            dna_kws = (dna or {}).get("keywords")
    except Exception as dna_exc:
        logger.debug("store DNA skipped for %s: %s", domain, dna_exc)

    upsert_index_row(db, domain, {
        "category": classification["category"],
        "subcategory": classification["subcategory"],
        "category_confidence": classification["confidence"],
        "category_evidence": evidence,
        "description": row.get("description") or row.get("homepage_message"),
        "price_bands": price_bands,
        "target_customer": target_customer,
        "brand_keywords": brand_keywords,
        "store_dna": dna,
        "dna_keywords": dna_kws,
        "dna_signature": dna_sig,
        "dna_at": now if dna else None,
        "knowledge_at": now,
    })
    return {
        "domain": domain,
        "category": classification["category"],
        "confidence": classification["confidence"],
    }


# ── Competitor knowledge graph ─────────────────────────────────────────────

def record_competitor_edge(db, source_key: str, target_domain: str, edge_source: str, delta: int = 1, set_weight: Optional[int] = None) -> None:
    """Strengthen (or, with set_weight, pin) a who-competes-with-whom edge.
    Guarded end-to-end — graph writes must never break the caller."""
    try:
        source_key = source_key if source_key.startswith("user:") else normalize_domain(source_key)
        target_domain = normalize_domain(target_domain)
        if not source_key or not target_domain or source_key == target_domain:
            return
        now = datetime.now(timezone.utc).isoformat()
        existing = db.table("competitor_edges").select("id, weight")\
            .eq("source_key", source_key).eq("target_domain", target_domain).maybe_single().execute()
        if existing and existing.data:
            weight = set_weight if set_weight is not None else (existing.data.get("weight") or 0) + delta
            db.table("competitor_edges").update({
                "weight": weight, "edge_source": edge_source, "updated_at": now,
            }).eq("id", existing.data["id"]).execute()
        else:
            db.table("competitor_edges").insert({
                "source_key": source_key, "target_domain": target_domain,
                "weight": set_weight if set_weight is not None else delta,
                "edge_source": edge_source, "created_at": now, "updated_at": now,
            }).execute()
    except Exception as exc:
        logger.debug("competitor edge write skipped (%s→%s): %s", source_key, target_domain, exc)


def graph_neighbors(db, source_keys: List[str], limit: int = 12) -> Dict[str, int]:
    """Positive-weight neighbors of any of the source keys → {domain: weight}.
    Negative-weight edges are returned too (weight < 0) so callers can
    EXCLUDE confirmed non-competitors."""
    out: Dict[str, int] = {}
    try:
        keys = [k if k.startswith("user:") else normalize_domain(k) for k in source_keys if k]
        if not keys:
            return out
        res = db.table("competitor_edges").select("target_domain, weight")\
            .in_("source_key", keys).order("weight", desc=True).limit(limit * 4).execute()
        for r in res.data or []:
            d = r["target_domain"]
            out[d] = max(out.get(d, -999), r.get("weight") or 0) if d in out else (r.get("weight") or 0)
    except Exception as exc:
        logger.debug("graph neighbors lookup skipped: %s", exc)
    return out


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

    # Columns added by later migrations may not exist yet — retry without them
    # so the index keeps working during the migration window (008:
    # business_stage/pricing_tier/expanded_at; 015: the three-stage pipeline
    # fields; 016: product_titles).
    _NEWER_COLS = (
        "business_stage", "pricing_tier", "expanded_at",
        "discovery_source", "discovered_at", "verified_at", "knowledge_at",
        "rejection_reason", "category_confidence", "category_evidence",
        "price_bands", "target_customer", "brand_keywords", "homepage_message",
        "collection_count", "related_ready", "product_titles",
        "tech_signals", "contact_email", "contact_source", "sells_wholesale", "multi_market",
        "store_dna", "dna_keywords", "dna_signature", "dna_at",
    )

    def _write(payload: Dict[str, Any]) -> None:
        if existing:
            db.table("shopify_store_index").update(payload).eq("domain", domain).execute()
        else:
            db.table("shopify_store_index").insert(payload).execute()

    if existing and existing.get("status") == "verified" and fields.get("status") == "candidate":
        return "skipped"

    # Write, and if the schema is missing a column (partial migration), drop
    # exactly the offending column named in the error and retry — so applying
    # 015 but not 016 (or vice-versa) still persists everything that DOES exist.
    payload = dict(fields)
    for _ in range(len(_NEWER_COLS) + 1):
        try:
            _write(payload)
            return "updated" if existing else "inserted"
        except Exception as exc:
            missing = _missing_column(str(exc))
            if missing and missing in payload and missing != "domain":
                payload.pop(missing, None)
                logger.debug("upsert dropping missing column %r for %s", missing, domain)
                continue
            # Fall back to stripping all known-newer columns at once.
            stripped = {k: v for k, v in payload.items() if k not in _NEWER_COLS}
            if len(stripped) < len(payload):
                logger.debug("upsert retry without newer columns for %s: %s", domain, exc)
                try:
                    _write(stripped)
                    return "updated" if existing else "inserted"
                except Exception:
                    raise
            raise
    return "updated" if existing else "inserted"


_MISSING_COL_RES = (
    re.compile(r"column\s+(?:[\w.]+\.)?[\"']?([\w]+)[\"']?\s+does not exist", re.I),
    re.compile(r"Could not find the '([\w]+)' column", re.I),
    re.compile(r"['\"]([\w]+)['\"] column of", re.I),
)


def _missing_column(msg: str) -> Optional[str]:
    for rx in _MISSING_COL_RES:
        m = rx.search(msg or "")
        if m:
            return m.group(1)
    return None


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
