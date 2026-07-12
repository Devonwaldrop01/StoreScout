"""
Stage 1 intelligence: winning-product scoring + gap analysis.

Both operate on a single snapshot's normalized product list (the same shape
normalize_product() produces). They are pure functions — no DB, no network —
so they can run inside the scan pipeline and have their output stored in
snapshot_data for the API to serve (tier-gated).

Honest-signal philosophy: we cannot see sales numbers. Everything here is a
*proxy* derived from public catalog structure. The reasons we generate say
"this pattern usually means…", never "this sold X units."
"""
from __future__ import annotations

import re as _re
from collections import Counter
from datetime import datetime, timezone
from statistics import median
from typing import Any, Dict, List, Optional


# ── shared helpers ──────────────────────────────────────────────────────────

def _safe_float(x) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        ss = s.strip()
        if ss.endswith("Z"):
            ss = ss[:-1] + "+00:00"
        dt = datetime.fromisoformat(ss)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _age_days(p: Dict[str, Any], now: datetime) -> Optional[int]:
    dt = _parse_dt(p.get("created_at")) or _parse_dt(p.get("published_at"))
    if not dt:
        return None
    return max(0, (now - dt).days)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _months_label(days: int) -> str:
    if days < 31:
        return f"{days}d"
    months = round(days / 30.0)
    if months < 12:
        return f"{months}mo"
    years = days / 365.0
    return f"{years:.1f}yr"


# ── winning products ────────────────────────────────────────────────────────

# Signal weights — tuned so no single proxy dominates. Variant depth and
# longevity are the strongest survival/investment signals available publicly.
_W = {
    "variant_depth": 0.30,
    "longevity": 0.25,
    "full_price_confidence": 0.20,
    "availability": 0.15,
    "image_investment": 0.10,
}


def score_winning_products(products: List[Dict[str, Any]], limit: int = 25) -> Dict[str, Any]:
    """
    Score every product 0–100 on how likely it is to be a 'winner', using only
    public catalog structure as proxies. Returns a ranked list plus a separate
    'newest' list (recently launched, regardless of score).
    """
    now = datetime.now(timezone.utc)
    total = len(products)
    if total == 0:
        return {"products": [], "newest": [], "scored_total": 0}

    scored: List[Dict[str, Any]] = []
    for p in products:
        variants = p.get("variants_count") or 0
        try:
            variants = int(variants)
        except Exception:
            variants = 0

        age = _age_days(p, now)
        discount = _safe_float(p.get("discount_pct_min"))
        available = bool(p.get("available"))
        images = p.get("images") or []
        n_images = len(images) if isinstance(images, list) else 0

        # ── signals (each 0–1) ──
        # Investment: you don't build out variants for a dud.
        s_variant = _clamp01(variants / 12.0)

        # Survival: still in catalog after months. Newer products can't have
        # proven survival yet, so they score lower here (and surface in 'newest').
        s_longevity = _clamp01((age or 0) / 365.0)

        # Full-price confidence: not relying on a markdown to move it.
        if discount is None or discount <= 0:
            s_fullprice = 1.0
        else:
            s_fullprice = _clamp01(1.0 - (discount / 60.0))  # 60%+ off → ~0

        # Stocked: they keep reordering it.
        s_avail = 1.0 if available else 0.35

        # Merchandising effort: more images = more investment in the listing.
        s_images = _clamp01(n_images / 3.0)

        signals = {
            "variant_depth": round(s_variant, 3),
            "longevity": round(s_longevity, 3),
            "full_price_confidence": round(s_fullprice, 3),
            "availability": round(s_avail, 3),
            "image_investment": round(s_images, 3),
        }
        score = int(round(100 * sum(signals[k] * _W[k] for k in _W)))

        scored.append({
            "title": p.get("title"),
            "product_url": p.get("product_url"),
            "handle": p.get("handle"),
            "price_min": _safe_float(p.get("price_min")),
            "image": images[0] if n_images else None,
            "score": score,
            "signals": signals,
            "age_days": age,
            "variants_count": variants,
            "discounted": bool(discount and discount > 0),
            "discount_pct": round(discount, 1) if discount else None,
            "available": available,
            "reason": _winning_reason(age, variants, discount, available),
            "signal_tags": _winning_tags(age, variants, discount, available),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    # ── Tier assignment — scarcity IS the intelligence ─────────────────────
    # A verdict system that marks half the catalog "worth testing" destroys
    # trust. Tiers are catalog-relative with hard caps AND strict absolute
    # gates: very few products can be Heroes, and every assignment explains
    # itself. Order: hero → strong → emerging → monitor → ignore.
    import math as _math
    prices = [s["price_min"] for s in scored if s["price_min"]]
    catalog_median = sorted(prices)[len(prices) // 2] if prices else None

    hero_cap   = max(2, min(5,  _math.ceil(total * 0.02)))
    strong_cap = max(4, min(12, _math.ceil(total * 0.06)))
    emerging_cap = 8
    heroes = strongs = emergings = 0

    for s in scored:
        sig = s["signals"]
        proven   = sig["longevity"] >= 0.40          # ≥ ~5 months in catalog
        fullpx   = sig["full_price_confidence"] >= 0.80
        invested = sig["variant_depth"] >= 0.35 or sig["image_investment"] >= 0.9
        is_new   = s["age_days"] is not None and s["age_days"] <= 60
        premium  = bool(catalog_median and s["price_min"] and s["price_min"] >= catalog_median * 1.15)
        crosssell = bool(s["title"] and any(w in s["title"].lower() for w in ("bundle", " kit", " set", " pack", "duo ", " duo")))

        if heroes < hero_cap and s["score"] >= 82 and proven and fullpx and s["available"] and invested:
            tier = "hero"
            heroes += 1
        elif strongs < strong_cap and s["score"] >= 72 and proven and s["available"]:
            tier = "strong"
            strongs += 1
        elif emergings < emerging_cap and is_new and s["available"] and fullpx and s["variants_count"] >= 4:
            tier = "emerging"   # launch-invested, too new to have proven survival
            emergings += 1
        elif s["score"] >= 55:
            tier = "monitor"
        else:
            tier = "ignore"

        s["tier"] = tier
        s["premium_position"] = premium
        s["cross_sell"] = crosssell
        s["why"] = _tier_why(s, sig, premium, crosssell)
        s["reveals"] = _tier_reveals(tier, s, premium, crosssell)
        s["respond"] = _tier_respond(tier, s, premium)

    # Newest products: launched recently, regardless of winning score.
    dated = [(p, _age_days(p, now)) for p in products]
    dated = [(p, a) for p, a in dated if a is not None]
    dated.sort(key=lambda t: t[1])
    newest = [{
        "title": p.get("title"),
        "product_url": p.get("product_url"),
        "price_min": _safe_float(p.get("price_min")),
        "image": (p.get("images") or [None])[0],
        "age_days": a,
        "variants_count": int(p.get("variants_count") or 0),
        "available": bool(p.get("available")),
    } for p, a in dated[:8]]

    return {
        "products": scored[:limit],
        "newest": newest,
        "scored_total": total,
        "tier_counts": {
            t: sum(1 for s in scored if s.get("tier") == t)
            for t in ("hero", "strong", "emerging", "monitor", "ignore")
        },
    }


def _tier_why(s: Dict[str, Any], sig: Dict[str, float], premium: bool, crosssell: bool) -> List[str]:
    """Every tier assignment must explain itself — specific, evidence-first."""
    why: List[str] = []
    age = s.get("age_days")
    if age is not None and age >= 365:
        why.append(f"Survived {_months_label(age)} in the catalog — duds get culled long before this")
    elif age is not None and age >= 150:
        why.append(f"Held its place for {_months_label(age)} — past the typical cull window")
    elif age is not None and age <= 60:
        why.append(f"Launched {_months_label(age)} ago with real backing, not a quiet test")
    if s.get("variants_count", 0) >= 10:
        why.append(f"{s['variants_count']} variants — nobody builds this depth for a product that doesn't sell")
    elif s.get("variants_count", 0) >= 4:
        why.append(f"{s['variants_count']} variants — meaningful inventory commitment")
    if sig.get("full_price_confidence", 0) >= 0.99:
        why.append("Never discounted — it moves at full price")
    elif s.get("discounted"):
        why.append(f"Currently {s.get('discount_pct')}% off — needs markdown help to move")
    if premium:
        why.append("Priced above their catalog median — a margin product, not a traffic product")
    if crosssell:
        why.append("Sold as a bundle/kit — built to raise order value")
    if not s.get("available"):
        why.append("Out of stock right now — either demand outran supply or it's being retired")
    return why[:4]


def _tier_reveals(tier: str, s: Dict[str, Any], premium: bool, crosssell: bool) -> str:
    """What this product's standing reveals about the competitor's business."""
    if tier == "hero":
        return (
            "This is load-bearing revenue. Products with this longevity, variant depth, and "
            "full-price discipline are what the rest of the catalog is built around — expect "
            "them to defend it hard." + (" Its premium pricing says it also carries their margin." if premium else "")
        )
    if tier == "strong":
        return "A dependable seller in their lineup — proven, stocked, and stable. Not their identity, but real revenue."
    if tier == "emerging":
        return "They're betting on this: launch-depth variants at full price means conviction, not a test. Watch whether it survives its first 90 days."
    if tier == "monitor":
        return "Nothing decisive yet — solid catalog filler until the signals separate it from the pack."
    return "Structurally weak signals — discounted, shallow, or unstocked. Safe to ignore."


def _tier_respond(tier: str, s: Dict[str, Any], premium: bool) -> Optional[str]:
    """Should you respond, and how — only tiers worth acting on get guidance."""
    price = s.get("price_min")
    price_txt = f" around the ${price:.0f} mark" if price else ""
    if tier == "hero":
        return (
            "Yes — but don't clone it. Study what job it does for their customers and position a "
            f"differentiated alternative{price_txt}: different angle, audience, or bundle. Competing "
            "head-on with their proven hero at the same price is a losing fight."
        )
    if tier == "strong":
        return (
            "Selectively. If this category overlaps yours, a sharper offer here is winnable — "
            "they'll defend heroes before they defend this."
        )
    if tier == "emerging":
        return (
            "Not yet — let them pay for the market test. Set a mental check-in for 60–90 days: "
            "if it's still stocked and undiscounted, they found demand you can also serve."
        )
    return None


def _winning_reason(age, variants, discount, available) -> str:
    parts: List[str] = []
    if age is not None:
        if age >= 180:
            parts.append(f"in catalog {_months_label(age)} (survived)")
        elif age >= 60:
            parts.append(f"in catalog {_months_label(age)}")
        else:
            parts.append(f"launched {_months_label(age)} ago")
    if variants >= 10:
        parts.append(f"{variants} variants (heavy investment)")
    elif variants >= 4:
        parts.append(f"{variants} variants")
    if discount is None or discount <= 0:
        parts.append("never discounted")
    else:
        parts.append(f"{round(discount)}% off")
    parts.append("in stock" if available else "out of stock")
    return " · ".join(parts)


def _winning_tags(age, variants, discount, available) -> List[str]:
    tags: List[str] = []
    if age is not None and age >= 180:
        tags.append(f"Long-running ({_months_label(age)})")
    if variants >= 10:
        tags.append(f"Deep variants ({variants})")
    if discount is None or discount <= 0:
        tags.append("Full price")
    if available:
        tags.append("In stock")
    return tags


# ── gap analysis ────────────────────────────────────────────────────────────

_BUCKET_ORDER = ["<$25", "$25–$49", "$50–$99", "$100–$199", "$200–$299", "$300–$499", "$500+"]


def analyze_gaps(analysis: Dict[str, Any], products: List[Dict[str, Any]], store_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Surface where a competitor is *not* serving the market — openings a new or
    existing store could move into. Ranked by opportunity strength.
    """
    total = len(products)
    if total == 0:
        return {"gaps": [], "total": 0}

    gaps: List[Dict[str, Any]] = []

    pricing = analysis.get("pricing") or {}
    buckets = ((pricing.get("price_buckets") or {}).get("buckets")) or {}
    median_price = pricing.get("median")

    # ── 1. Underserved price bands ──
    # Only bands that are *realistic entry points* relative to where they compete:
    # cheaper lanes below their dominant band, or the one band just above it
    # (premium-adjacent). Bands two+ steps above the dominant are a different
    # market entirely, not a gap.
    if buckets:
        dominant_band, dominant_count = max(buckets.items(), key=lambda kv: kv[1])
        dominant_pct = round(100 * dominant_count / total, 1)
        dominant_idx = _BUCKET_ORDER.index(dominant_band) if dominant_band in _BUCKET_ORDER else None

        band_gaps: List[Dict[str, Any]] = []
        if dominant_idx is not None:
            for band in _BUCKET_ORDER:
                idx = _BUCKET_ORDER.index(band)
                # relevant range: from the cheapest band up to one step above dominant
                if idx > dominant_idx + 1:
                    continue
                if idx == dominant_idx:
                    continue
                count = buckets.get(band, 0)
                share = round(100 * count / total, 1)
                if share > 8.0:
                    continue  # already reasonably served

                is_below = idx < dominant_idx
                strength = (dominant_pct - share) / 100.0
                strength += 0.15 if is_below else -0.10  # cheaper lanes are the classic entry point

                if count == 0:
                    detail = (
                        f"They have nothing in the {band} range. {dominant_pct}% of their catalog "
                        f"sits in {dominant_band}. A product priced here doesn't compete with them "
                        f"head-on — it serves a customer they've chosen not to."
                    )
                else:
                    detail = (
                        f"Only {share}% of their catalog is in {band} ({count} products), versus "
                        f"{dominant_pct}% concentrated in {dominant_band}. This price point is "
                        f"thinly served — room to own it."
                    )
                band_gaps.append({
                    "type": "price_band",
                    "title": f"Underserved price band: {band}",
                    "detail": detail,
                    "opportunity": round(_clamp01(strength), 2),
                    "metric": {"band": band, "share_pct": share, "count": count},
                })

        # keep the 2 strongest band gaps so we don't flood the list
        band_gaps.sort(key=lambda g: g["opportunity"], reverse=True)
        gaps.extend(band_gaps[:2])

    # ── 2. Availability gaps (unmet demand) ──
    catalog = analysis.get("catalog") or {}
    oos_pct = catalog.get("out_of_stock_pct") or 0
    oos_count = catalog.get("out_of_stock_count") or 0
    if oos_pct >= 8:
        gaps.append({
            "type": "availability",
            "title": f"{oos_pct}% of their catalog is out of stock",
            "detail": (
                f"{oos_count} products ({oos_pct}%) are currently unavailable. Whether that's a demand "
                f"spike or a supply gap on their end, it's a likely opening: a reliably-stocked "
                f"alternative in those categories can capture shoppers who'd otherwise wait or bounce."
            ),
            "opportunity": round(_clamp01(oos_pct / 40.0), 2),
            "metric": {"out_of_stock_pct": oos_pct, "count": oos_count},
        })

    # ── 3. Discount posture ──
    discounts = analysis.get("discounts") or {}
    disc_pct = discounts.get("discounted_pct") or 0
    if disc_pct >= 40:
        gaps.append({
            "type": "discount_posture",
            "title": "Heavily promotional — premium positioning is open",
            "detail": (
                f"{disc_pct}% of their catalog is discounted. A brand that holds full price and "
                f"competes on quality/story (not markdowns) reads as the premium option against a "
                f"store that's always on sale."
            ),
            "opportunity": round(_clamp01((disc_pct - 30) / 50.0), 2),
            "metric": {"discounted_pct": disc_pct},
        })
    elif disc_pct <= 5:
        gaps.append({
            "type": "discount_posture",
            "title": "Rarely discounts — a value entrant can undercut",
            "detail": (
                f"Only {disc_pct}% of their catalog is discounted; they hold full price. A "
                f"value-priced entrant, or well-timed promotions, can win price-sensitive shoppers "
                f"they're not chasing."
            ),
            "opportunity": 0.45,
            "metric": {"discounted_pct": disc_pct},
        })

    # ── 4. Launch momentum window ──
    launch = analysis.get("launch_timeline") or {}
    accel = (launch.get("acceleration") or {})
    trend = accel.get("trend")
    accel_pct = accel.get("30d_vs_90d_pct")
    velocity = (launch.get("velocity") or {})
    v30 = velocity.get("last_30d")
    if trend == "Decelerating" or (v30 is not None and v30 < 1.0):
        if trend == "Decelerating" and accel_pct is not None:
            detail = (
                f"Their launch rate is down {abs(round(accel_pct))}% versus the 90-day average — "
                f"expansion is cooling. Catalogs that look stale create a window to launch fresh "
                f"product while attention is up for grabs."
            )
            opp = 0.6
        else:
            detail = (
                f"They're launching roughly {v30 or 0} products/month — a slow, mature cadence. "
                f"A faster-moving entrant can look more exciting and capture trend-driven demand."
            )
            opp = 0.5
        gaps.append({
            "type": "launch_momentum",
            "title": "Launch momentum is cooling — entry window",
            "detail": detail,
            "opportunity": opp,
            "metric": {"trend": trend, "accel_pct": accel_pct, "velocity_30d": v30},
        })

    # ── 5. Category concentration (thin tags they dabble in) ──
    tag_analysis = analysis.get("tag_analysis") or {}
    top_tags = tag_analysis.get("top_tags") or []
    thin = [t for t in top_tags if 0 < (t.get("pct") or 0) <= 3.0]
    if thin:
        names = ", ".join(t["tag"] for t in thin[:3])
        gaps.append({
            "type": "thin_category",
            "title": "Categories they dabble in but don't own",
            "detail": (
                f"Tags like {names} appear on only a handful of products. They're testing these "
                f"categories without committing. A store that goes deep in one of them can own a "
                f"space they're treating as an afterthought."
            ),
            "opportunity": 0.4,
            "metric": {"thin_tags": [t["tag"] for t in thin[:5]]},
        })

    # ── 6. Collection-based gaps (from extended scraping) ──
    if store_profile:
        col = store_profile.get("collection_intel") or {}
        brand = store_profile.get("brand_signals") or {}

        if not col.get("has_bundles") and total >= 15:
            gaps.append({
                "type": "no_bundles",
                "title": "No bundles or kits collection",
                "detail": (
                    "They don't sell product bundles or kits — no collection signals it. Bundles "
                    "raise average order value without changing acquisition cost. It's a lane they've "
                    "left open."
                ),
                "opportunity": 0.55,
                "metric": {},
            })

        if not col.get("has_subscription") and total >= 20:
            gaps.append({
                "type": "no_subscription",
                "title": "No subscription or replenishment tier",
                "detail": (
                    "No subscription or replenishment collection is visible. For repeat-purchase "
                    "products, subscriptions lock in LTV while they're still chasing one-time buyers."
                ),
                "opportunity": 0.50,
                "metric": {},
            })

        if not brand.get("has_wholesale") and (median_price or 0) >= 30:
            gaps.append({
                "type": "no_wholesale",
                "title": "No B2B or wholesale channel",
                "detail": (
                    "No wholesale or B2B page is visible on this store. At their price point, a "
                    "wholesale channel adds a high-volume revenue stream. If you offer trade pricing, "
                    "you can pick up buyers they're not even talking to."
                ),
                "opportunity": 0.40,
                "metric": {},
            })

    gaps.sort(key=lambda g: g["opportunity"], reverse=True)
    return {
        "gaps": gaps,
        "total": len(gaps),
        "median_price": median_price,
    }


# ── store profile (extended scraping) ──────────────────────────────────────

def analyze_store_profile(extended_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce brand intelligence signals from supplementary Shopify endpoints:
    collections.json, pages.json, blogs.json, articles.json.
    """
    collections = extended_data.get("collections") or []
    pages = extended_data.get("pages") or []
    blogs = extended_data.get("blogs") or []
    articles = extended_data.get("articles") or []

    def _match_term(item: str, term: str) -> bool:
        # Prefix patterns (e.g. "sustainab", "eco-") — keep as substring
        if term.endswith(("-", " ")):
            return term.rstrip("- ") in item
        # Multi-word phrases / hyphenated — substring is correct
        if " " in term or "-" in term:
            return term in item
        # Single clean words — word boundary to avoid "sale" → "wholesale"
        return bool(_re.search(r"\b" + _re.escape(term) + r"\b", item))

    def _match(items_lower, *terms) -> bool:
        return any(_match_term(item, t) for t in terms for item in items_lower)

    col_names_lc = [c.get("title", "").lower() for c in collections]
    col_handles_lc = [c.get("handle", "").lower() for c in collections]
    col_all_lc = col_names_lc + col_handles_lc

    collection_intel: Dict[str, Any] = {
        "count": len(collections),
        "names": [c.get("title", "") for c in collections[:40]],
        "has_sale": _match(col_all_lc, "sale", "clearance", "outlet"),
        "has_new_arrivals": _match(col_all_lc, "new arrival", "new-arrival", "just in", "new in", "new-in"),
        "has_best_sellers": _match(col_all_lc, "best seller", "bestsell", "top seller", "popular", "trending"),
        "has_bundles": _match(col_all_lc, "bundle", "kit", "set", "combo"),
        "has_subscription": _match(col_all_lc, "subscription", "subscribe", "replenish"),
        "has_gift": _match(col_all_lc, "gift"),
    }

    page_titles_lc = [p.get("title", "").lower() for p in pages]
    page_handles_lc = [p.get("handle", "").lower() for p in pages]
    page_all_lc = page_titles_lc + page_handles_lc

    brand_signals: Dict[str, Any] = {
        "has_wholesale": _match(page_all_lc, "wholesale", "trade", "b2b", "bulk order"),
        "has_affiliate": _match(page_all_lc, "affiliate", "partner", "refer", "ambassador"),
        "has_press": _match(page_all_lc, "press", "media", "as seen", "in the press"),
        "has_sustainability": _match(page_all_lc, "sustainab", "eco-", "eco ", "planet", "environment"),
        "has_size_guide": _match(page_all_lc, "size guide", "sizing", "size chart"),
        "has_rewards": _match(page_all_lc, "reward", "loyalty", "points", "vip"),
        "page_count": len(pages),
    }

    # Content investment score 0–100
    blog_count = len(blogs)
    article_count = len(articles)
    content_score = 0
    if blog_count >= 1:
        content_score += 30
    if article_count >= 5:
        content_score += 20
    if article_count >= 10:
        content_score += 20
    if blog_count >= 2:
        content_score += 15
    if articles:
        try:
            latest = articles[0].get("published_at", "")
            if latest:
                pub = _parse_dt(latest)
                if pub:
                    age_days = (datetime.now(timezone.utc) - pub).days
                    if age_days <= 30:
                        content_score += 15
                    elif age_days <= 90:
                        content_score += 8
        except Exception:
            pass

    content_intel: Dict[str, Any] = {
        "blog_count": blog_count,
        "sampled_article_count": article_count,
        "content_investment_score": min(100, content_score),
        "recent_article_titles": [a.get("title", "") for a in articles[:5]],
    }

    return {
        "collection_intel": collection_intel,
        "brand_signals": brand_signals,
        "content_intel": content_intel,
    }


# ── My Store comparison ─────────────────────────────────────────────────────
#
# Compares the user's own store against a competitor. The philosophy (from
# product direction): a smaller/newer store usually can't win head-on, so the
# output frames *matching* the table stakes and *owning a lane* the competitor
# ignores — not just "you're losing, beat them." Verdicts give the honest
# diagnosis; actions + match_strategy are the prescription.

def _fmt_price(v: Optional[float]) -> str:
    f = _safe_float(v)
    if f is None:
        return "—"
    return f"${f:.0f}" if f >= 10 else f"${f:.2f}"


def _pct_diff(mine: Optional[float], theirs: Optional[float]) -> Optional[float]:
    m, t = _safe_float(mine), _safe_float(theirs)
    if m is None or t is None or t == 0:
        return None
    return (m - t) / t * 100.0


def compare_stores(mine: Dict[str, Any], theirs: Dict[str, Any],
                   my_hostname: str = "your store",
                   their_hostname: str = "them") -> Dict[str, Any]:
    """
    Build a head-to-head comparison from two snapshot_data dicts.
    Returns overall verdict, per-dimension diagnosis + action, and a
    newcomer-aware match strategy.
    """
    my_cat = mine.get("catalog") or {}
    th_cat = theirs.get("catalog") or {}
    my_pr = mine.get("pricing") or {}
    th_pr = theirs.get("pricing") or {}
    my_disc = mine.get("discounts") or {}
    th_disc = theirs.get("discounts") or {}
    my_launch = (mine.get("launch_timeline") or {}).get("velocity") or {}
    th_launch = (theirs.get("launch_timeline") or {}).get("velocity") or {}
    my_prof = mine.get("store_profile") or {}
    th_prof = theirs.get("store_profile") or {}

    my_total = my_cat.get("total_products") or 0
    th_total = th_cat.get("total_products") or 0
    is_newcomer = my_total < 25 or (th_total and my_total < th_total * 0.4)

    dims: List[Dict[str, Any]] = []
    score = {"winning": 0, "losing": 0, "matched": 0, "neutral": 0}

    def add(key, label, verdict, your_value, their_value, insight, action):
        score[verdict] = score.get(verdict, 0) + 1
        dims.append({
            "key": key, "label": label, "verdict": verdict,
            "your_value": your_value, "their_value": their_value,
            "insight": insight, "action": action,
        })

    # ── 1. Price positioning ──
    my_med, th_med = my_pr.get("median"), th_pr.get("median")
    diff = _pct_diff(my_med, th_med)
    if diff is not None:
        yv, tv = _fmt_price(my_med), _fmt_price(th_med)
        if diff <= -15:
            add("price", "Price positioning", "neutral", yv, tv,
                f"Your median is {abs(diff):.0f}% below {their_hostname}. You're the value option — a real, defensible position.",
                "Own 'better value for the money' in your copy and PDP. Watch margin: cheaper only wins if you still profit per order.")
        elif diff >= 15:
            add("price", "Price positioning", "neutral", yv, tv,
                f"You're priced {diff:.0f}% above {their_hostname}. Premium positioning only holds if the customer can see why.",
                "Justify the gap with story, materials, service, or guarantee. If you can't, you'll lose price-shoppers to them.")
        else:
            add("price", "Price positioning", "matched", yv, tv,
                f"You're within {abs(diff):.0f}% of their median — competing head-on on price.",
                "Head-to-head on price is the hardest place for a smaller store. Differentiate on something other than price.")

    # ── 2. Catalog breadth ──
    if th_total:
        if my_total >= th_total * 1.2:
            add("catalog", "Catalog breadth", "winning", str(my_total), str(th_total),
                f"You list {my_total} products vs their {th_total} — wider selection.",
                "Breadth is a strength, but make sure your best sellers aren't buried. Merchandise a tight 'best of' collection.")
        elif my_total >= th_total * 0.7:
            add("catalog", "Catalog breadth", "matched", str(my_total), str(th_total),
                f"Comparable range — {my_total} vs {th_total} products.",
                "Range is matched, so the catalog isn't your edge. Win on curation, content, or service instead.")
        else:
            add("catalog", "Catalog breadth", "neutral", str(my_total), str(th_total),
                f"They carry {th_total} products to your {my_total}. Don't try to match their breadth.",
                "Go deep, not wide. Own one category completely rather than spreading thin across many.")

    # ── 3. Discount posture ──
    my_dp, th_dp = my_disc.get("discounted_pct"), th_disc.get("discounted_pct")
    if my_dp is not None and th_dp is not None:
        yv, tv = f"{my_dp:.0f}%", f"{th_dp:.0f}%"
        if th_dp - my_dp >= 15:
            add("discount", "Discount posture", "winning", yv, tv,
                f"They discount {th_dp:.0f}% of their catalog; you hold price ({my_dp:.0f}%). You read as the premium pick.",
                "Lean into full-price confidence. Avoid racing them to the bottom — let them train their customers to wait for sales.")
        elif my_dp - th_dp >= 15:
            add("discount", "Discount posture", "losing", yv, tv,
                f"You're more promotional — {my_dp:.0f}% of your catalog is discounted vs their {th_dp:.0f}%.",
                "Heavy discounting trains buyers to wait. Shift to fewer, time-boxed promos and protect your full-price perception.")
        else:
            add("discount", "Discount posture", "matched", yv, tv,
                f"Similar promo intensity — {my_dp:.0f}% vs {th_dp:.0f}%.",
                "Neither of you owns the value or premium lane on discounting. Pick one deliberately.")

    # ── 4. Launch velocity ──
    my_v, th_v = my_launch.get("last_30d"), th_launch.get("last_30d")
    if my_v is not None and th_v is not None:
        yv, tv = f"{my_v}/mo", f"{th_v}/mo"
        if th_v > 0 and my_v < th_v * 0.5:
            add("launch", "Launch velocity", "losing", yv, tv,
                f"They're launching ~{th_v}/month to your ~{my_v}. They look fresher to repeat visitors.",
                "Don't match their volume — pick a cadence you can sustain (e.g. one drop every 2 weeks) and market each launch hard.")
        elif my_v > th_v * 1.5:
            add("launch", "Launch velocity", "winning", yv, tv,
                f"You're launching faster — ~{my_v}/month vs their ~{th_v}.",
                "Fresh catalog is an edge with trend-driven buyers. Keep it up, but don't sacrifice winners for novelty.")
        else:
            add("launch", "Launch velocity", "matched", yv, tv,
                f"Comparable launch cadence — ~{my_v}/mo vs ~{th_v}/mo.",
                "Launch pace is matched. Compete on which launches land, not how many.")

    # ── 5. Price-band white space ──
    my_b = ((my_pr.get("price_buckets") or {}).get("buckets")) or {}
    th_b = ((th_pr.get("price_buckets") or {}).get("buckets")) or {}
    if th_b and th_total:
        # band they concentrate in but you barely touch
        their_dom = max(th_b.items(), key=lambda kv: kv[1]) if th_b else None
        if their_dom:
            band, cnt = their_dom
            their_share = cnt / th_total * 100
            my_in_band = my_b.get(band, 0)
            my_share = (my_in_band / my_total * 100) if my_total else 0
            if their_share >= 30 and my_share < 10:
                add("price_band", "Price-band coverage", "neutral", f"{my_share:.0f}% in {band}", f"{their_share:.0f}% in {band}",
                    f"They concentrate {their_share:.0f}% of their catalog in {band}; you have almost nothing there.",
                    f"That's where their volume is. Either bring a sharper offer into {band}, or deliberately skip it and own a band they ignore.")

    # ── 6. Channel / brand gaps ──
    my_col = my_prof.get("collection_intel") or {}
    th_col = th_prof.get("collection_intel") or {}
    th_brand = th_prof.get("brand_signals") or {}
    my_brand = my_prof.get("brand_signals") or {}
    channel_gaps = []
    if th_col.get("has_bundles") and not my_col.get("has_bundles"):
        channel_gaps.append("bundles/kits (they raise AOV with these, you don't)")
    if th_col.get("has_subscription") and not my_col.get("has_subscription"):
        channel_gaps.append("a subscription option (recurring revenue you're leaving on the table)")
    if th_brand.get("has_wholesale") and not my_brand.get("has_wholesale"):
        channel_gaps.append("a wholesale/B2B channel")
    if channel_gaps:
        add("channels", "Channels & offers", "losing", "missing", "present",
            f"They run {len(channel_gaps)} offer type{'s' if len(channel_gaps) != 1 else ''} you don't: " + "; ".join(channel_gaps) + ".",
            "Each of these is revenue mechanics you can copy without competing on product. Bundles are the fastest to add.")
    elif (my_col.get("has_bundles") or my_col.get("has_subscription")) and not (th_col.get("has_bundles") or th_col.get("has_subscription")):
        add("channels", "Channels & offers", "winning", "present", "missing",
            "You offer bundles/subscriptions they don't — a structural AOV/LTV edge.",
            "Promote these harder. They're advantages competitors can't match overnight.")

    # ── Overall ──
    wins, losses = score["winning"], score["losing"]
    if wins > losses + 1:
        verdict = "You're ahead overall"
    elif losses > wins + 1:
        verdict = "You're behind overall"
    else:
        verdict = "It's close"
    summary = (
        f"Across {len(dims)} dimensions, you win {wins}, lose {losses}, and match {score['matched']}. "
        + ("As the smaller store, focus on matching their table stakes and owning a lane they ignore — not beating them everywhere."
           if is_newcomer else
           "You're at comparable scale — the comparison below shows exactly where to press and where to defend.")
    )

    # ── Match strategy (the newcomer-focused prescription) ──
    match_these = [d["label"].lower() for d in dims if d["verdict"] in ("losing", "matched")][:3]
    own_these = [d["label"].lower() for d in dims if d["verdict"] in ("winning", "neutral")][:3]
    if is_newcomer:
        narrative = (
            f"You don't need to out-do {their_hostname} across the board — that's the trap most new stores fall into. "
            f"Match them on the basics customers expect (so you're not visibly behind), then pour your energy into the "
            f"one or two areas where you can genuinely be different. Pick a lane and own it."
        )
    else:
        narrative = (
            f"You're operating at similar scale to {their_hostname}. Defend the dimensions where you're ahead, shore up "
            f"the ones where you're behind before they widen the gap, and look for one move you can make before they do."
        )

    return {
        "has_store": True,
        "my_hostname": my_hostname,
        "their_hostname": their_hostname,
        "overall": {"verdict": verdict, "summary": summary, "score": score},
        "dimensions": dims,
        "match_strategy": {
            "is_newcomer": bool(is_newcomer),
            "match_these": match_these,
            "own_these": own_these,
            "narrative": narrative,
        },
    }


def compute_quick_wins(snapshot_data: dict) -> list:
    """
    Rule-based action cards derived from a single snapshot.
    No LLM cost — deterministic logic only.
    Returns up to 4 wins ordered by actionability.
    """
    wins = []
    catalog  = snapshot_data.get("catalog")  or {}
    pricing  = snapshot_data.get("pricing")  or {}
    discounts = snapshot_data.get("discounts") or {}
    launch   = snapshot_data.get("launch_timeline") or {}

    total           = catalog.get("total_products") or 0
    median          = float(pricing.get("median") or 0)
    discounted_pct  = float(discounts.get("discounted_pct") or 0)
    oos_pct         = float(catalog.get("out_of_stock_pct") or 0)
    oos_count       = catalog.get("out_of_stock_count") or 0

    launch_counts = launch.get("launch_counts") or {}
    last_30d  = (launch_counts.get("30d")  or {}).get("count") or 0
    last_90d  = (launch_counts.get("90d")  or {}).get("count") or 0
    avg_mo_90 = round(last_90d / 3, 1) if last_90d else 0

    vel = launch.get("velocity") or {}
    vel_30d = float(vel.get("last_30d") or 0)
    vel_90d = float(vel.get("last_90d") or 0)

    buckets   = (pricing.get("price_buckets") or {}).get("buckets") or {}
    under_25  = buckets.get("<$25") or 0

    # 1. Low-end gap (sparse entry tier vs. strong median)
    if total > 0 and median >= 30 and under_25 < max(10, int(total * 0.04)):
        wins.append({
            "id": "low_end_gap",
            "type": "opportunity",
            "headline": f"Only {under_25} products under $25",
            "detail": (
                f"Their catalog is anchored at ${int(median)} median with almost nothing "
                f"entry-level. If you sell under $25 you face near-zero direct competition from them."
            ),
        })

    # 2. Discount dependence — don't race them on price
    if discounted_pct >= 40:
        wins.append({
            "id": "discount_dependence",
            "type": "signal",
            "headline": f"{discounted_pct:.0f}% of catalog discounted — don't race them on price",
            "detail": (
                "Their customers are conditioned to wait for sales. "
                "Competing on discounts will only compress your margins. "
                "Win on product freshness and full-price positioning instead."
            ),
        })

    # 3. Stalled launch pace
    if vel_90d > 0 and vel_30d < vel_90d * 0.4 and last_30d <= 3:
        wins.append({
            "id": "stalled_launches",
            "type": "opportunity",
            "headline": f"Only {last_30d} new product{'s' if last_30d != 1 else ''} launched this month",
            "detail": (
                f"Recent pace ({last_30d}/month) is well below their 3-month average "
                f"({avg_mo_90}/month). Any launch you make now competes against a stale catalog."
            ),
        })

    # 4. Accelerating launch velocity — watch signal
    if vel_90d > 0 and vel_30d > vel_90d * 1.8 and last_30d >= 8:
        ratio = round(vel_30d / vel_90d, 1)
        wins.append({
            "id": "launch_surge",
            "type": "watch",
            "headline": f"{last_30d} launches this month — {ratio}× their average",
            "detail": (
                "Something is accelerating. A new collection or category push is likely underway. "
                "Watch what they're launching and whether it opens or closes a gap for you."
            ),
        })

    # 5. Stock gap — unfulfilled demand
    if total >= 20 and oos_pct >= 30:
        wins.append({
            "id": "stock_gap",
            "type": "opportunity",
            "headline": f"{oos_pct:.0f}% of their catalog is out of stock",
            "detail": (
                f"About {oos_count} products are unavailable. "
                "That's a likely opening while they're out of stock. "
                "If you carry comparable products, push visibility while they can't fulfil."
            ),
        })

    return wins[:4]
