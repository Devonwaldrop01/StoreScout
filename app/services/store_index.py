"""
Verified Shopify store index â€” light discovery/indexing pass.

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
from app.services import verification_lifecycle as lifecycle

if _USE_CURL_CFFI:
    from curl_cffi.requests import Session as CurlSession
else:
    import httpx

logger = logging.getLogger(__name__)

# â”€â”€ Sources â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# Niche queries the candidate generator rotates through. These describe
# MARKETS, not platforms â€” platform verification is our job, not the AI's.
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


def niche_queries() -> "list[str]":
    """The full set of niche queries the candidate generator rotates through so
    the index grows broad enough to cover almost any store a user describes.
    Built from every taxonomy subcategory (â‰ˆ90 niches) plus the hand seeds â€”
    deterministic, deduped, order-stable. No AI, no network."""
    out: list = list(SEED_QUERIES)
    seen = {q.lower() for q in out}
    for cat, subs in CATEGORY_TAXONOMY.items():
        if cat in ("Other", "Adult"):
            continue
        for sub in subs:
            for q in (f"{sub.lower()} brand", f"{sub.lower()} {cat.split(' ')[0].lower()} store"):
                if q not in seen:
                    seen.add(q)
                    out.append(q)
    return out

# â”€â”€ Taxonomy â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Fixed list keeps index search consistent â€” classification must map into
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

# keyword â†’ (category, subcategory). Checked against title + description +
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
    # Generic product-type terms â€” broaden deterministic classification of
    # free-text discovery reasons (not tied to any single query).
    ("nail",              ("Beauty", "Nails")),
    ("manicure",          ("Beauty", "Nails")),
    ("perfume",           ("Beauty", "Fragrance")),
    ("fragrance",         ("Beauty", "Fragrance")),
    ("cologne",           ("Beauty", "Fragrance")),
    ("apparel",           ("Fashion", "Womenswear")),
    ("clothing",          ("Fashion", "Womenswear")),
    ("t-shirt",           ("Fashion", "Streetwear")),
    ("dress",             ("Fashion", "Womenswear")),
    ("boots",             ("Footwear", "Boots")),
    ("sandals",           ("Footwear", "Sandals")),
    ("sneakers",          ("Footwear", "Sneakers")),
    ("ceramic",           ("Home & Living", "Home Decor")),
    ("pottery",           ("Home & Living", "Home Decor")),
    ("homeware",          ("Home & Living", "Home Decor")),
    ("home decor",        ("Home & Living", "Home Decor")),
    ("trinket",           ("Home & Living", "Home Decor")),
    ("vase",              ("Home & Living", "Home Decor")),
    ("mug",               ("Home & Living", "Kitchen")),
]


def classify_text_rules(text: str) -> Optional[str]:
    """Deterministic top-level category from the keyword rules â€” NO AI, NO
    network. Longest keyword wins ('pet food' beats 'food'). Returns None when
    nothing fires, so callers can treat it as 'unknown' (never a guess)."""
    t = (text or "").lower()
    for kw, (cat, _sub) in sorted(_RULE_KEYWORDS, key=lambda x: -len(x[0])):
        if kw in t:
            return cat
    return None


def rank_discovery_candidates(candidates: List[dict], user_category: Optional[str]) -> List[dict]:
    """Stable re-rank of discovery suggestions so a HARD category contradiction
    with the user's store (e.g. sneakers/apparel/nail products for a Home &
    Living store) can never outrank a plausible or adjacent candidate.

    Deterministic and network-free: each candidate's category is taken from its
    row if classified, else inferred from its reason/domain via the keyword
    rules; only a *confident* cross-cluster contradiction is demoted. Candidates
    that stay in place keep their original relative order (Python sort is
    stable), so graph/index/plausible picks are untouched.
    """
    if not user_category:
        return list(candidates)
    from app.services.store_dna import category_relation

    def _demote(c: dict) -> int:
        cat = c.get("category") or classify_text_rules(
            f"{c.get('reason', '')} {c.get('domain', '')}"
        )
        if cat and category_relation(cat, user_category) == "contradiction":
            return 1
        return 0

    return sorted(candidates, key=_demote)


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def normalize_domain(url_or_domain: str) -> str:
    """'https://www.Gymshark.com/collections/x' â†’ 'gymshark.com'."""
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
    from app.core.index_hold import require_index_writes
    require_index_writes()
    from app.services.verification_canary import probe_context
    guard = probe_context.get()
    if guard is not None:
        return guard.get(client, url, timeout, _USE_CURL_CFFI)
    if _USE_CURL_CFFI:
        return client.get(url, timeout=timeout, allow_redirects=True)
    return client.get(url, timeout=timeout)


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


# â”€â”€ The light pass â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def index_store_pass(domain: str) -> Dict[str, Any]:
    """
    One polite â‰¤4-request pass over a domain: verification signals + light
    profile together. Returns a dict with:
      reachable, confidence (0-100), signals [str], monitorable (bool),
      profile {...light-scan fields}, failure_reason (when not reachable)
    """
    from app.core.index_hold import require_index_writes
    require_index_writes()
    domain = urlparse(domain if "://" in domain else f"https://{domain}").hostname or ""
    _enforce_domain_rate_limit(domain)

    confidence = 0
    signals: List[str] = []
    profile: Dict[str, Any] = {"homepage_url": f"https://{domain}"}
    reachable = False
    products_ok = False
    access_state = None
    catalog_observation = None
    home_status = cart_status = None
    home_password = home_challenge = False

    with _make_client() as client:
        # 1. Homepage â€” brand identity + HTML fingerprints
        html = ""
        try:
            r = _get(client, f"https://{domain}/")
            home_status = r.status_code
            if r.status_code in (200, 403):
                reachable = True
            if r.status_code == 200:
                html = (r.text or "")[:400_000]
                lower = html.lower()
                home_password = 'action="/password"' in lower or "shopify-section-main-password" in lower
                home_challenge = "cf-chl-" in lower or "challenge-platform" in lower
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
            profile["brand_name"] = _clean(m.group(1), 80) if m else (title.split("|")[0].split("â€“")[0].strip()[:80] or None)
            desc_m = _META_DESC_RE.search(html) or _META_DESC_RE2.search(html)
            if desc_m:
                profile["meta_description"] = _clean(desc_m.group(1))
            lang_m = _LANG_RE.search(html)
            if lang_m:
                profile["language"] = lang_m.group(1)[:8]

            # Commercial signals for lead scoring â€” proof of budget/marketing
            # maturity + a contact. Extracted from the homepage we already have,
            # so near-zero added cost.
            commercial = extract_commercial_signals(html, domain)
            profile["tech_signals"] = commercial["tech_signals"]
            profile["contact_email"] = commercial["contact_email"]
            profile["contact_source"] = commercial["contact_source"]
            profile["sells_wholesale"] = commercial["sells_wholesale"]
            profile["multi_market"] = commercial["multi_market"]

        # 2. /cart.js â€” storefront API marker
        try:
            r = _get(client, f"https://{domain}/cart.js", timeout=8)
            cart_status = r.status_code
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

        # 3. /products.json â€” catalog sample (also the "monitorable" signal)
        products: List[dict] = []
        try:
            r = _get(client, f"https://{domain}/products.json?limit=250", timeout=15)
            ct = r.headers.get("content-type", "")
            if r.status_code == 200 and "application/json" in ct:
                data = r.json()
                if isinstance(data, dict) and lifecycle.valid_products(data.get("products")):
                    reachable = True
                    products_ok = True
                    confidence += 55
                    signals.append("Product catalog accessible")
                    products = data.get("products") or []
                    catalog_observation = lifecycle.successful_catalog(products, datetime.now(timezone.utc), "index_probe")
                else:
                    access_state = "no_readable_catalog"
            elif r.status_code in (401, 403, 429):
                reachable = True
                access_state = "blocked"
                signals.append("Storefront responds (bot-protected)")
            elif r.status_code == 402:
                access_state = "storefront_unavailable"
            elif r.status_code >= 500:
                access_state = "temporarily_unreachable"
            else:
                access_state = "no_readable_catalog"
                lower_catalog = (getattr(r, "text", "") or "")[:400_000].lower()
                if 'action="/password"' in lower_catalog or "shopify-section-main-password" in lower_catalog:
                    access_state = "password_protected"
                elif "cf-chl-" in lower_catalog or "challenge-platform" in lower_catalog:
                    access_state = "blocked"
                # No markers is not enough. Require an accessible competing
                # commerce platform plus both Shopify API endpoints missing.
                if (r.status_code == 404 and cart_status == 404 and home_status == 200
                        and not signals and "woocommerce" in html.lower()):
                    access_state = "non_shopify"
        except Exception:
            access_state = "temporarily_unreachable"

        if home_password:
            access_state, products_ok = "password_protected", False
        elif home_challenge:
            access_state, products_ok = "blocked", False
        elif home_status == 402:
            access_state, products_ok = "storefront_unavailable", False

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

            # 250 returned means the catalog is AT LEAST 250 â€” rough count by design
            profile["product_count"] = len(products)
            if prices:
                profile["median_price"] = round(statistics.median(prices), 2)
                profile["min_price"] = round(min(prices), 2)
                profile["max_price"] = round(max(prices), 2)
                # Persist price quartiles now â€” the knowledge stage classifies
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

        # 4. /collections.json â€” taxonomy hints (only worth it on a live catalog)
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

    from app.services.verification_canary import probe_context
    guard = probe_context.get()
    if guard is not None and guard.stop_state:
        access_state, products_ok = guard.stop_state, False
    confidence = min(100, confidence)
    return {
        "reachable": reachable,
        "confidence": confidence,
        "signals": signals,
        "monitorable": products_ok,
        "access_state": access_state,
        "catalog_observation": catalog_observation if products_ok else None,
        "profile": profile,
        "failure_reason": None if reachable else "unreachable_or_dns",
    }


# â”€â”€ Commercial signals (lead-quality intelligence) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# What a merchant spends money on tells us far more about whether they'll BUY
# than how big their catalog is. These footprints are the highest-signal, and
# they're free â€” the homepage is already fetched for verification.

# marker substrings â†’ (signal key, category). Category groups feed scoring.
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

    # Contact email â€” prefer a mailto, then a role inbox on the brand's domain,
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


# â”€â”€ Market context â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def derive_market_context(product_count: Optional[int], median_price: Optional[float]) -> Dict[str, Optional[str]]:
    """
    Honest heuristics from the light sample â€” estimates, not claims.

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


# â”€â”€ Classification â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

    # AI fallback â€” tiny, single-store call
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


# â”€â”€ Multi-signal classification (confidence + evidence) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# The old classifier took the FIRST keyword hit anywhere in the text, so a
# single stray word ("gift" on a pet store) could misclassify â€” that's how
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

# Product nouns omitted from the original small seed vocabulary. These map to
# existing taxonomy entries; ambiguous brands/model names remain unclassified.
_PRODUCT_NOUNS = [
    ('wallet', ('Accessories', 'Wallets')), ('money clip', ('Accessories', 'Wallets')),
    ('handkerchief', ('Accessories', 'Scarves')), ('handbag', ('Accessories', 'Bags')),
    ('bandana', ('Accessories', 'Scarves')),
    ('championship belt', ('Sporting Goods', 'Combat Sports')),
    ('jeans', ('Fashion', 'Denim')), ('shorts', ('Fashion', 'Womenswear')),
    ('skirt', ('Fashion', 'Womenswear')), ('shirt', ('Fashion', 'Womenswear')),
    ('tee', ('Fashion', 'Streetwear')), ('hoodie', ('Fashion', 'Streetwear')),
    ('sweater', ('Fashion', 'Womenswear')), ('cardigan', ('Fashion', 'Womenswear')),
    ('pants', ('Fashion', 'Womenswear')), ('jacket', ('Fashion', 'Outerwear')),
    ('vestido', ('Fashion', 'Womenswear')),
    ('compression sleeve', ('Fitness Apparel', 'Gym Accessories')),
    ('compression shorts', ('Fitness Apparel', 'Activewear')),
    ('cardstock', ('Arts & Crafts', 'Craft Supplies')), ('stencil', ('Arts & Crafts', 'Craft Supplies')),
    ('embroidery', ('Arts & Crafts', 'Sewing')), ('scrapbooking', ('Arts & Crafts', 'Craft Supplies')),
    ('embossing', ('Arts & Crafts', 'Craft Supplies')), ('stamp', ('Arts & Crafts', 'Craft Supplies')),
    ('planner', ('Arts & Crafts', 'Stationery')), ('notebook', ('Arts & Crafts', 'Stationery')),
    ('pipe fitting', ('Home Improvement', 'Hardware')), ('grinder', ('Home Improvement', 'Tools')),
    ('welding', ('Home Improvement', 'Tools')), ('electrode', ('Home Improvement', 'Tools')),
    ('brake', ('Automotive', 'Parts')), ('wheelset', ('Automotive', 'Parts')),
    ('motor', ('Automotive', 'Parts')),
    ('phone case', ('Tech Accessories', 'Phone Cases')),
    ('screen protector', ('Tech Accessories', 'Screen Protectors')),
    ('tablet case', ('Tech Accessories', 'Phone Cases')),
    ('keyboard', ('Electronics & Gadgets', 'Computers')),
    ('pajama', ('Fashion', 'Lingerie')), ('romper', ('Fashion', 'Womenswear')),
    ('stroller', ('Kids & Baby', 'Baby Gear')), ('bassinet', ('Kids & Baby', 'Nursery')),
    ('moisturizer', ('Beauty', 'Skincare')), ('cleanser', ('Beauty', 'Skincare')),
    ('eau de parfum', ('Beauty', 'Fragrance')), ('eau de toilette', ('Beauty', 'Fragrance')),
]


def classify_store_v2(
    title: str = "",
    description: str = "",
    homepage_text: str = "",
    product_types: Optional[List[str]] = None,
    product_titles: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    collections: Optional[List[dict]] = None,
    allow_ai: bool = True,
) -> Dict[str, Any]:
    """
    Score every taxonomy category by weighted keyword evidence across distinct
    signals. Returns {category, subcategory, confidence (0-100),
    evidence: [{signal, detail, category}], method}. Confidence reflects how
    decisively the winner beat the field AND how much evidence backed it â€”
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
    support: Dict[str, set] = {}
    sub_hits: Dict[str, Dict[str, int]] = {}
    evidence: Dict[str, List[dict]] = {}

    observed_catalog = bool(product_types or product_titles)
    def hits(text):
        vocabulary = _PRODUCT_NOUNS + _RULE_KEYWORDS if observed_catalog else _RULE_KEYWORDS
        matches = [(kw, target) for kw, target in vocabulary
                   if re.search(r"(?<!\w)" + re.escape(kw) + r"(?:s)?(?!\w)", text)]
        if not observed_catalog:
            return matches
        # A more specific phrase owns its component words (phone case is not
        # audio equipment; compression shorts are not generic fashion).
        return [(kw, target) for kw, target in matches
                if not any(kw != longer and kw in longer for longer, _ in matches)]
    rules = {kw:target for kw,target in _RULE_KEYWORDS}
    if observed_catalog:
        rules.update(dict(_PRODUCT_NOUNS))
    # Actual product signals take precedence over contradictory old home text,
    # marketing collections and stray tags. Keep sparse/no-signal inputs honest.
    product_support = sum(bool(hits(t)) for kind,t in signals if kind in ('product_type','product_title'))
    for kind, text in signals:
        if product_support >= 2 and kind not in ('product_type','product_title'):
            continue
        w = _SIGNAL_WEIGHT.get(kind, 1)
        for keyword in dict.fromkeys(kw for kw,_ in hits(text)):
            cat, sub = rules[keyword]
            if observed_catalog and cat == 'Fashion' and re.search(r"\b(?:baby|boys?|girls?|kids?|children)\b", text):
                cat, sub = 'Kids & Baby', 'Kids Apparel'
            support.setdefault(cat, set()).add((kind, text))
            scores[cat] = scores.get(cat, 0) + w
            sub_hits.setdefault(cat, {})
            sub_hits[cat][sub] = sub_hits[cat].get(sub, 0) + w
            evidence.setdefault(cat, [])
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
    if len(support.get(winner, set())) < 2 or top < 6:
        confidence = min(confidence, 54)  # sparse evidence stays below the index recommendation floor

    sub = max(sub_hits.get(winner, {"General": 1}).items(), key=lambda kv: kv[1])[0]
    ev = sorted(evidence.get(winner, []), key=lambda e: -e["weight"])[:6]

    # AI tiebreak ONLY when the top two are close and confidence is middling â€”
    # cheap, and only where the rules are genuinely uncertain.
    method = "multi_signal"
    if allow_ai and confidence < 70 and runner and (top - runner) <= _SIGNAL_WEIGHT["product_type"]:
        ai = _ai_classify_tiebreak(hp, [winner, ranked[1][0]])
        if ai and ai in scores:
            winner = ai
            sub = max(sub_hits.get(winner, {"General": 1}).items(), key=lambda kv: kv[1])[0]
            ev = sorted(evidence.get(winner, []), key=lambda e: -e["weight"])[:6]
            confidence = max(confidence, 72)
            method = "multi_signal+ai"

    if len(support.get(winner, set())) < 2 or scores.get(winner, 0) < 6:
        confidence = min(confidence, 54)
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
    AI-primary classification â€” the reliable way to KNOW what a store sells.
    Claude reads the store's actual product titles/types/collections (the ground
    truth) and assigns a category + subcategory from the fixed taxonomy, plus a
    confidence and short evidence. It is explicitly told to ignore stray words
    (colour names like 'baby blue', materials, marketing copy) and to return
    'Other' at low confidence rather than guess. Returns None on failure so the
    caller can fall back to the keyword classifier.
    """
    from app.core.index_hold import require_index_writes
    require_index_writes()
    from app.core.config import get_settings
    from app.services.ai import UNTRUSTED_DATA_NOTE, call_claude, parse_json

    if not get_settings().anthropic_api_key:
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
        f"PRODUCT TITLES (the ground truth â€” judge by these):\n"
        + "\n".join(f"  Â· {t}" for t in titles[:40])
    )
    prompt = f"""You categorize Shopify stores. Decide what the store ACTUALLY SELLS, based on the product titles and product types â€” those are the ground truth.

{UNTRUSTED_DATA_NOTE}

Pick EXACTLY ONE category and one subcategory from this fixed taxonomy:
{taxonomy}

Hard rules:
- Judge by the actual products. If the titles are men's/women's sandals and clothing, it is Footwear or Fashion â€” NOT Kids & Baby, even if the word "baby" appears in a colour or material.
- IGNORE stray words: colour names ("baby blue", "kids size"), materials, marketing fluff, shipping/returns text.
- If the products are mixed or don't clearly fit, use category "Other" with a LOW confidence. Never guess a specific category you aren't sure of.
- confidence 0-100 = how certain you are. Be honest; a single ambiguous signal is low.

{payload}

Return ONLY JSON:
{{"category": "<exact category>", "subcategory": "<exact subcategory>", "confidence": <0-100>, "evidence": ["<=3 short product-based reasons"]}}"""

    res = call_claude(
        "classify_store", prompt,
        model="claude-haiku-4-5-20251001", max_tokens=220,
    )
    if not res.ok:
        return None
    p = parse_json(res.text)
    if not isinstance(p, dict):
        return None
    try:
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
        logger.debug("classify_store_ai parse failed: %s", exc)
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


# â”€â”€ Stage 2: Verification â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Turn a DISCOVERED domain into VERIFIED or REJECTED. Verification fetches the
# storefront ONCE and stores the raw signals; it does NOT classify. Every
# rejection records a strict, machine-readable reason. Classification is a
# separate stage that reads those stored signals with zero extra network â€” the
# memory-efficient split the pipeline is built around.

# Access-state and retry decisions live in verification_lifecycle. Absence of
# platform evidence and transient network failures are never permanent labels.


def _claim_verification(db, domain, source, source_query, force=False, expected_row=None):
    """Compare-and-set claim, shared by scheduled and manual verification.

    Fail closed when lifecycle columns are absent. A five-minute lease outlives
    the bounded HTTP pass; abandoned claims become retryable automatically.
    """
    from app.core.index_hold import require_index_writes
    require_index_writes()
    from uuid import uuid4
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    res = db.table("shopify_store_index").select("*").eq("domain", domain).maybe_single().execute()
    row = res.data if res else None
    if expected_row is not None:
        from app.services.verification_canary import same_row_version
        if force or not same_row_version(row, expected_row):
            return None
    if not row:
        domain = normalize_domain(domain)
        upsert_index_row(db, domain, {"status": "candidate", "source": source, "source_query": source_query})
        row = db.table("shopify_store_index").select("*").eq("domain", domain).maybe_single().execute().data
    if lifecycle.due_at(row) > now and (not force or row.get("verification_token")):
        return None
    token = str(uuid4())
    q = db.table("shopify_store_index").update({
        "verification_token": token, "last_attempted_at": now.isoformat(),
        "next_verification_at": (now + timedelta(minutes=5)).isoformat(), "updated_at": now.isoformat(),
    }).eq("domain", domain)
    q = q.eq("updated_at", row["updated_at"]) if row.get("updated_at") else q.is_("updated_at", "null")
    q = q.eq("verification_token", row["verification_token"]) if row.get("verification_token") else q.is_("verification_token", "null")
    if not q.execute().data:
        return None
    return row, token


def _finish_verification(db, domain, token, payload):
    # A late HTTP response cannot overwrite a newer tracked scan or verifier.
    from app.core.index_hold import require_index_writes
    require_index_writes()
    payload = {**payload, "updated_at": datetime.now(timezone.utc).isoformat(), "verification_token": None}
    return bool(db.table("shopify_store_index").update(payload).eq("domain", domain)
                .eq("verification_token", token)
                .gt("next_verification_at", datetime.now(timezone.utc).isoformat()).execute().data)


def verify_and_store(db, domain: str, source: str, source_query: Optional[str] = None, force: bool = False, *, expected_row=None) -> Dict[str, Any]:
    """
    Stage 2. Fetch the storefront once; persist a VERIFIED row with raw signals
    (no classification) or a REJECTED row with a reason. Returns
    {domain, outcome: verified|rejected|failed, reason}.
    """
    from app.core.index_hold import require_index_writes
    require_index_writes()
    from app.core.config import get_settings
    settings = get_settings()
    # Preserve an existing row's exact hostname; www aliases are not proven
    # interchangeable merchants and must not strand the original queue entry.
    domain = urlparse(domain if "://" in domain else f"https://{domain}").hostname or ""
    claim = _claim_verification(db, domain, source, source_query, force=force, expected_row=expected_row)
    if not claim:
        return {"domain": domain, "outcome": "skipped", "reason": "not_due_or_claimed"}
    previous, token = claim
    domain = previous["domain"]
    now = datetime.now(timezone.utc).isoformat()

    def _failure(state):
        fields = lifecycle.retry_fields(previous, state, datetime.now(timezone.utc))
        saved = _finish_verification(db, domain, token, fields)
        return {"domain": domain, "outcome": ("rejected" if state in lifecycle.TERMINAL else "failed") if saved else "skipped",
                "reason": state if saved else "superseded", "successful_catalogs": 0, "attempted": True, "confidence": 0}

    try:
        result = index_store_pass(domain)
    except Exception as exc:
        logger.warning("verify pass crashed for %s: %s", domain, exc)
        return _failure("temporarily_unreachable")

    confidence = result.get("confidence") or 0
    profile = result.get("profile") or {}

    # Reject anything that fails the storefront bar, or scores below the
    # configured Shopify-confidence threshold.
    state = lifecycle.classify_probe(result, settings.shopify_index_min_confidence)
    if state != "verified_shopify":
        return _failure(state)

    # Shared brand text is not proof of canonical identity. Keep both domains
    # until redirect or Shopify shop identity evidence establishes equivalence.

    # VERIFIED â€” store raw signals only. Classification happens in Stage 3.
    market = derive_market_context(profile.get("product_count"), profile.get("median_price"))
    fields = {
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
    }
    fields.update(lifecycle.successful_fields(result["catalog_observation"], confidence, result.get("signals")))
    fields.update(classification_transition(previous, fields))
    saved = _finish_verification(db, domain, token, fields)
    return {"domain": domain, "outcome": "verified" if saved else "skipped",
            "reason": None if saved else "superseded", "successful_catalogs": int(saved),
            "attempted": True,
            "confidence": confidence,
            "reverified": bool(saved and previous.get("last_verified_at"))}


# â”€â”€ Stage 3: Knowledge â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Runs ONLY on verified stores. Its job is understanding, not discovery: it
# reads the raw signals stored at verification and builds a confidence-scored
# category (with evidence), price bands, target customer, and brand keywords â€”
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
    """Compact, human-readable descriptors â€” the strongest distinct evidence
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


def classification_transition(previous, fields):
    """First signatures are not proof of a changed business. Carry a useful
    classification provisionally, bounded by its original verification expiry
    and seven days, unless fresh products confidently contradict it.
    """
    from datetime import timedelta
    from app.services.discovery_quality import is_recent_verified
    observation = dict(fields['catalog_observation'])
    old = previous.get('catalog_observation') or {}
    if observation.get('signature') == old.get('signature'):
        # Reverification must never reset the provisional expiry/retry clock.
        observation.update({k:v for k,v in old.items() if k.startswith('classification_')})
        return {'catalog_observation':observation}
    now = lifecycle.timestamp(observation['observed_at'])
    fallback = classify_store_v2(product_types=fields.get('product_types'), product_titles=fields.get('product_titles'),allow_ai=False)
    from app.services.store_dna import category_relation
    contradiction = fallback['confidence'] >= 70 and category_relation(fallback['category'],previous.get('category')) == 'contradiction'
    until = lifecycle.timestamp(old.get('classification_valid_until'))
    if until is None:
        verified = lifecycle.timestamp(previous.get('last_verified_at'))
        until = min(verified + timedelta(days=60),now + timedelta(days=7)) if verified else now
    useful = (is_recent_verified(previous,now=now) and previous.get('category')
              and (previous.get('category_confidence') or 0) >= 55 and until > now and not contradiction)
    observation.update(classification_state='provisional' if useful else 'pending',
        classification_valid_until=until.isoformat() if useful else None,
        classification_prior_signature=old.get('signature'))
    out={'catalog_observation':observation, 'knowledge_at':None}
    if not useful:
        out.update(category_confidence=0,category=None,subcategory=None,description=None,
            store_dna=None,dna_keywords=None,dna_signature=None,dna_at=None,target_customer=None)
    return out


def run_knowledge(db, row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 3. Classify a verified store from its STORED signals (no re-fetch).
    Writes category/subcategory/confidence/evidence, price bands, target
    customer and brand keywords, and stamps knowledge_at. Returns
    {domain, category, confidence}.
    """
    from app.core.index_hold import require_index_writes
    require_index_writes()
    domain = row.get("domain") or ""
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

    # Store DNA â€” the semantic business profile that lets the index rank TRUE
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
            dna, dna_kws = row.get("store_dna"), row.get("dna_keywords")  # unchanged â€” reuse
        else:
            dna = generate_store_dna(dna_ctx)
            dna_kws = (dna or {}).get("keywords")
    except Exception as dna_exc:
        logger.debug("store DNA skipped for %s: %s", domain, dna_exc)

    payload = {
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
        "updated_at": now,
    }
    observation = dict(row.get('catalog_observation') or {})
    if observation:
        from datetime import timedelta
        from app.services.discovery_quality import is_classification_usable
        adequate = classification['confidence'] >= 55
        carry = not adequate and observation.get('classification_state') == 'provisional' and is_classification_usable(row)
        if carry:
            for key in ('category','subcategory','category_confidence','category_evidence','description',
                        'target_customer','brand_keywords','store_dna','dna_keywords','dna_signature','dna_at'):
                payload[key] = row.get(key)
        if not adequate:
            payload['knowledge_at'] = None
        observation['classification_state'] = ('current' if adequate else
            'provisional' if carry else 'uncertain')
        observation['classification_attempt_confidence'] = classification['confidence']
        observation['classification_retry_at'] = ((datetime.now(timezone.utc)+timedelta(days=1)).isoformat() if not adequate else None)
        if adequate:
            observation['classification_valid_until'] = None
        payload['catalog_observation'] = observation
    q = db.table("shopify_store_index").update(payload).eq("domain", domain).eq("status", "verified")
    q = q.eq("updated_at", row["updated_at"]) if row.get("updated_at") else q.is_("updated_at", "null")
    q = q.is_("verification_token", "null")
    signature = (row.get("catalog_observation") or {}).get("signature")
    q = q.eq("catalog_observation->>signature", signature) if signature else q.is_("catalog_observation", "null")
    if not q.execute().data:
        return {"domain": domain, "status": "superseded"}
    return {
        "domain": domain,
        "category": classification["category"],
        "confidence": classification["confidence"],
        "classification_state": (payload.get('catalog_observation') or {}).get('classification_state'),
    }


# â”€â”€ Competitor knowledge graph â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def record_competitor_edge(db, source_key: str, target_domain: str, edge_source: str, delta: int = 1, set_weight: Optional[int] = None) -> None:
    """Strengthen (or, with set_weight, pin) a who-competes-with-whom edge.
    Guarded end-to-end â€” graph writes must never break the caller."""
    from app.core.index_hold import require_index_writes
    require_index_writes()
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
        logger.debug("competitor edge write skipped (%sâ†’%s): %s", source_key, target_domain, exc)


def graph_neighbors(db, source_keys: List[str], limit: int = 12) -> Dict[str, int]:
    """Positive-weight neighbors of any of the source keys â†’ {domain: weight}.
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
            out[d] = max(out.get(d, -999), r.get("weight") or 0)
        negatives = db.table("competitor_edges").select("target_domain, weight").in_("source_key", keys).lt("weight", 0).limit(1000).execute()
        for r in negatives.data or []:
            out[r["target_domain"]] = r["weight"]
    except Exception as exc:
        logger.debug("graph neighbors lookup skipped: %s", exc)
    return out


# â”€â”€ Upsert â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def upsert_index_row(db, domain: str, fields: Dict[str, Any]) -> str:
    """
    Upsert by domain. Returns 'inserted' | 'updated' | 'skipped'.
    Never downgrades a verified row back to candidate â€” a fresher verified/
    rejected/failed result always wins, but a mere re-candidate does not.
    """
    from app.core.index_hold import require_index_writes
    require_index_writes()
    domain = normalize_domain(domain)
    if not domain or "." not in domain:
        return "skipped"

    now = datetime.now(timezone.utc).isoformat()
    # Drop unset fields so partial updates don't blank existing data â€” but keep
    # an explicit failure_reason=None, which clears a stale reason on re-verify.
    fields = {k: v for k, v in fields.items() if v is not None or k in {"failure_reason", "rejection_reason", "knowledge_at", "verification_token"}}
    fields["domain"] = domain
    fields["updated_at"] = now

    existing = None
    try:
        res = db.table("shopify_store_index").select("*").eq("domain", domain).maybe_single().execute()
        existing = res.data if res else None
    except Exception:
        # A failed existence lookup is not evidence that the row is absent.
        raise

    observation = fields.get("catalog_observation")
    if observation and existing:
        if observation.get("signature") == (existing.get("catalog_observation") or {}).get("signature"):
            fields.update(classification_transition(existing,fields))
            for key in ("knowledge_at", "category_confidence", "category", "subcategory", "description"):
                fields.pop(key, None)
        else:
            transition = classification_transition(existing, fields)
            if transition['catalog_observation']['classification_state'] == 'provisional':
                for key in ('category','subcategory','category_confidence','description'):
                    fields.pop(key,None)
            fields.update(transition)

    # Columns added by later migrations may not exist yet â€” retry without them
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

    def _write(payload: Dict[str, Any]) -> bool:
        if existing:
            q = db.table("shopify_store_index").update(payload).eq("domain", domain)
            q = q.eq("updated_at", existing["updated_at"]) if existing.get("updated_at") else q.is_("updated_at", "null")
            q = q.eq("verification_token", existing["verification_token"]) if existing.get("verification_token") else q.is_("verification_token", "null")
            return bool(q.execute().data)
        # PostgREST emits ON CONFLICT(domain) DO NOTHING. A racing creator
        # retains its entire row, including its lease and classification.
        return bool(db.table("shopify_store_index").upsert(
            payload, on_conflict="domain", ignore_duplicates=True).execute().data)

    if existing and fields.get("status") in {"candidate", "discovered"}:
        return "skipped"

    # Write, and if the schema is missing a column (partial migration), drop
    # exactly the offending column named in the error and retry â€” so applying
    # 015 but not 016 (or vice-versa) still persists everything that DOES exist.
    payload = dict(fields)
    for _ in range(len(_NEWER_COLS) + 1):
        try:
            if not _write(payload):
                return "skipped"
            return "updated" if existing else "inserted"
        except Exception as exc:
            missing = _missing_column(str(exc))
            if missing and missing in payload and missing not in {"domain", "verification_state", "catalog_observation", "last_attempted_at", "next_verification_at", "verification_attempts", "verification_token"}:
                payload.pop(missing, None)
                logger.debug("upsert dropping missing column %r for %s", missing, domain)
                continue
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
    Full pipeline for one domain: light pass â†’ threshold â†’ classify â†’ upsert.
    Returns {domain, outcome: verified|rejected|failed, confidence}.
    Used by the internal endpoint (web process) and admin test runs.
    """
    from app.core.index_hold import require_index_writes
    require_index_writes()
    result = verify_and_store(db, domain, source, source_query)
    if result.get("outcome") == "verified":
        try:
            row = db.table("shopify_store_index").select("*").eq("domain", result["domain"]).maybe_single().execute().data
            if row and not row.get("knowledge_at"):
                run_knowledge(db, row)
        except Exception:
            logger.exception("Knowledge pending after verification for %s", domain)
    return result
