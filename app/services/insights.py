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
    }


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


def analyze_gaps(analysis: Dict[str, Any], products: List[Dict[str, Any]]) -> Dict[str, Any]:
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
                f"{oos_count} products ({oos_pct}%) are currently unavailable. Out-of-stock items "
                f"are demand they can't fulfill right now. A reliably-stocked alternative in those "
                f"categories captures shoppers who'd otherwise wait or bounce."
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

    gaps.sort(key=lambda g: g["opportunity"], reverse=True)
    return {
        "gaps": gaps,
        "total": len(gaps),
        "median_price": median_price,
    }
