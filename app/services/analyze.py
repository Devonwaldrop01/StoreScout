from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone,timedelta
from statistics import median
from typing import Any, Dict, List, Optional
import math


def detect_bulk_update_spike(update_datetimes, bucket="day"):
    """
    Returns (is_bulk, dominant_bucket_label, dominant_pct)

    A "bulk" pattern is when a large share of updates happen in the same time bucket
    (same day or same hour), suggesting a system-wide refresh rather than organic edits.
    """
    if not update_datetimes:
        return (False, None, 0.0)

    if bucket == "hour":
        key_fn = lambda d: d.strftime("%Y-%m-%d %H:00")
    else:  # "day"
        key_fn = lambda d: d.strftime("%Y-%m-%d")

    buckets = [key_fn(d) for d in update_datetimes]
    c = Counter(buckets)
    top_bucket, top_count = c.most_common(1)[0]
    dominant_pct = round(100.0 * top_count / len(update_datetimes), 1)

    # tune threshold if needed
    is_bulk = dominant_pct >= 70.0 and len(update_datetimes) >= 30
    return (is_bulk, top_bucket, dominant_pct)


def safe_float(x) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None

def pct(n: int, d: int) -> float:
    return round((n / d * 100.0), 2) if d else 0.0

def median_or_none(xs: List[float]) -> Optional[float]:
    xs = [x for x in xs if x is not None]
    return round(median(xs), 2) if xs else None

def parse_dt(s: Optional[str]) -> Optional[datetime]:
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



def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def cutoff_days(days: int) -> datetime:
    return now_utc() - timedelta(days=days)

def quantile(values: List[float], q: float) -> Optional[float]:
    if not values:
        return None
    xs = sorted(values)
    if q <= 0: return xs[0]
    if q >= 1: return xs[-1]
    pos = (len(xs) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    w = pos - lo
    return xs[lo] * (1 - w) + xs[hi] * w

def compute_new_vs_old_and_updates(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Builds:
      comparisons.new_vs_old: created counts + median prices for new items
      comparisons.update_activity: updated counts (meaningful + organic-with-sane-fallback)
    """
    now = datetime.now(timezone.utc)
    total = len(products)
    if total == 0:
        return {"new_vs_old": {}, "update_activity": {}}

    # helper to decide "created date" (created_at preferred, fallback published_at)
    def created_dt(p: Dict[str, Any]) -> Optional[datetime]:
        return parse_dt(p.get("created_at")) or parse_dt(p.get("published_at"))

    def updated_dt(p: Dict[str, Any]) -> Optional[datetime]:
        return parse_dt(p.get("updated_at"))

    # Treat "updated ~= created" as noise.
    # 1 hour is often too strict; 24h is often too aggressive.
    # 6 hours is a good middle ground.
    GRACE_SECONDS = 6 * 3600

    def meaningful_update_dt(p: Dict[str, Any]) -> Optional[datetime]:
        ud = updated_dt(p)
        if not ud:
            return None
        cd = created_dt(p)
        if cd and abs((ud - cd).total_seconds()) <= GRACE_SECONDS:
            return None
        return ud

    # windows
    windows = {
        "30": now - timedelta(days=30),
        "90": now - timedelta(days=90),
        "180": now - timedelta(days=180),
    }

    # Created counts + groups
    created_counts: Dict[str, int] = {}
    created_pcts: Dict[str, float] = {}
    created_groups: Dict[str, List[Dict[str, Any]]] = {}

    for k, cutoff in windows.items():
        group = []
        for p in products:
            cd = created_dt(p)
            if cd and cd >= cutoff:
                group.append(p)
        created_groups[k] = group
        created_counts[f"created_{k}"] = len(group)
        created_pcts[f"created_{k}_pct"] = pct(len(group), total)

    # Collect meaningful updates ONCE (one per product)
    meaningful_updates: List[datetime] = []
    for p in products:
        ud = meaningful_update_dt(p)
        if ud:
            meaningful_updates.append(ud)

    # Bulk spike detection
    is_bulk, top_bucket, dominant_pct = detect_bulk_update_spike(meaningful_updates, bucket="day")

    def bucket_day(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d")

    # Organic updates: exclude dominant bucket if bulk detected
    filtered_updates = meaningful_updates
    bulk_filter_applied = False

    if is_bulk and top_bucket:
        candidate = [d for d in meaningful_updates if bucket_day(d) != top_bucket]

        # IMPORTANT: don’t “nuke” to zero.
        # If filtering removes basically everything, keep meaningful updates but still flag bulk.
        if len(candidate) >= 10:
            filtered_updates = candidate
            bulk_filter_applied = True
        else:
            filtered_updates = meaningful_updates
            bulk_filter_applied = False

    # Updated counts (we’ll REPORT organic, but also return raw for debugging)
    updated_counts: Dict[str, int] = {}
    updated_pcts: Dict[str, float] = {}
    updated_counts_raw: Dict[str, int] = {}
    updated_pcts_raw: Dict[str, float] = {}

    for k, cutoff in windows.items():
        organic_cnt = sum(1 for d in filtered_updates if d >= cutoff)
        raw_cnt = sum(1 for d in meaningful_updates if d >= cutoff)

        updated_counts[f"updated_{k}"] = organic_cnt
        updated_pcts[f"updated_{k}_pct"] = pct(organic_cnt, total)

        updated_counts_raw[f"updated_{k}_raw"] = raw_cnt
        updated_pcts_raw[f"updated_{k}_raw_pct"] = pct(raw_cnt, total)

    # median price comparisons (new 90 vs catalog)
    catalog_prices = [safe_float(p.get("price_min")) for p in products]
    catalog_median = median_or_none(catalog_prices)

    new_90_prices = [safe_float(p.get("price_min")) for p in created_groups["90"]]
    new_90_median = median_or_none(new_90_prices)

    out_new_old = {
        **created_counts,
        **created_pcts,
        "catalog_median_price": catalog_median,
        "new_90_median_price": new_90_median,
    }

    out_updates = {
        **updated_counts,
        **updated_pcts,

        # debug / transparency fields
        **updated_counts_raw,
        **updated_pcts_raw,
        "meaningful_update_count": len(meaningful_updates),
        "organic_update_count": len(filtered_updates),

        "bulk_update_flag": bool(is_bulk),
        "bulk_update_bucket": top_bucket,
        "bulk_update_dominant_pct": dominant_pct,
        "bulk_filter_applied": bulk_filter_applied,
    }

    return {"new_vs_old": out_new_old, "update_activity": out_updates}



def compute_discounted_vs_full_price(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Builds comparisons.discounted_vs_full_price
    Uses compare_at_min vs price_min to determine a valid discount.
    """
    total = len(products)
    if total == 0:
        return {}
    
    discounted_prices = []
    full_prices = []
    discounted_count = 0

    for p in products:
        pr = safe_float(p.get("price_min"))
        ca = safe_float(p.get("compare_at_min"))
        d = compute_discount_pct(pr, ca)

        if d is not None:
            discounted_count += 1
            if pr is not None:
                discounted_prices.append(pr)
        else:
            if pr is not None:
                full_prices.append(pr)

    return {
        "discounted_count": discounted_count,
        "discounted_pct": pct(discounted_count, total),
        "discounted_median_price": median_or_none(discounted_prices),
        "full_price_median_price": median_or_none(full_prices),
    }


def compute_confidence_notes(products: List[Dict[str, Any]]) -> List[str]:
    """
    Adds 'confidence notes' explaining data coverage + what may be missing.
    """
    total = len(products)
    if total == 0:
        return ["No products were returned from /products.json. This store may block Shopify product JSON access or is not Shopify."]

    missing_created = 0
    missing_updated = 0
    missing_prices = 0
    missing_compare = 0

    for p in products:
        if not (p.get("created_at") or p.get("published_at")):
            missing_created += 1
        if not p.get("updated_at"):
            missing_updated += 1
        if safe_float(p.get("price_min")) is None:
            missing_prices += 1
        if safe_float(p.get("compare_at_min")) is None:
            missing_compare += 1

    notes = []
    notes.append("This report is based only on the public Shopify product catalog endpoint (/products.json). It does not include traffic, conversion rate, ads, or checkout data.")
    notes.append(f"Date coverage: {pct(total - missing_created, total)}% of products include created/published dates; {pct(total - missing_updated, total)}% include updated_at.")
    notes.append(f"Pricing coverage: {pct(total - missing_prices, total)}% of products include a usable price.")
    notes.append(f"Discount coverage: {pct(total - missing_compare, total)}% include compare-at pricing fields (discounts only count when compare_at > price).")
    notes.append("If a store returns HTML/404 for /products.json, it may be non-Shopify, headless Shopify with restrictions, or intentionally blocking the endpoint.")

    return notes

    
def price_bucket(price: float) -> str:
    if price < 25: return "<$25"
    if price < 50: return "$25–$49"
    if price < 100: return "$50–$99"
    if price < 200: return "$100–$199"
    if price < 300: return "$200–$299"
    if price < 500: return "$300–$499"
    return "$500+"

def compute_discount_pct(price_min: Optional[float], compare_at_min: Optional[float]) -> Optional[float]:
    if price_min is None or compare_at_min is None:
        return None
    if compare_at_min > price_min and compare_at_min > 0:
        return round((compare_at_min - price_min) / compare_at_min * 100.0, 2)
    return None
def analyze_launch_timeline(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze product launch patterns and velocity.
    
    Returns actionable insights about:
    - Launch velocity (recent vs historical)
    - Price positioning of new products
    - Seasonal launch patterns
    - SKU expansion strategy
    """
    total = len(products)
    if total == 0:
        return {}
    
    now = datetime.now(timezone.utc)
    
    # Parse creation dates
    def created_dt(p: Dict[str, Any]) -> Optional[datetime]:
        return parse_dt(p.get("created_at")) or parse_dt(p.get("published_at"))
    
    def safe_float(x) -> Optional[float]:
        if x is None:
            return None
        try:
            return float(x)
        except Exception:
            return None
    
    def pct(n: int, d: int) -> float:
        return round((n / d * 100.0), 2) if d else 0.0
    
    # Collect products with valid dates
    dated_products = []
    for p in products:
        dt = created_dt(p)
        if dt:
            dated_products.append({
                "product": p,
                "created": dt,
                "price": safe_float(p.get("price_min")),
                "vendor": p.get("vendor", "Unknown"),
            })
    
    if not dated_products:
        return {"error": "No products have created_at/published_at dates"}
    
    # Sort by date
    dated_products.sort(key=lambda x: x["created"])
    
    # Calculate time windows
    windows = {
        "7d": now - timedelta(days=7),
        "30d": now - timedelta(days=30),
        "90d": now - timedelta(days=90),
        "180d": now - timedelta(days=180),
        "1yr": now - timedelta(days=365),
    }
    
    # Count products per window
    launch_counts = {}
    launch_groups = {}
    
    for label, cutoff in windows.items():
        group = [dp for dp in dated_products if dp["created"] >= cutoff]
        launch_groups[label] = group
        launch_counts[label] = {
            "count": len(group),
            "pct": pct(len(group), total),
        }
    
    # Calculate launch velocity (products per month)
    def calc_velocity(days: int, count: int) -> float:
        if days == 0:
            return 0.0
        months = days / 30.0
        return round(count / months, 1) if months > 0 else 0.0
    
    velocity = {
        "last_30d": calc_velocity(30, launch_counts["30d"]["count"]),
        "last_90d": calc_velocity(90, launch_counts["90d"]["count"]),
        "last_1yr": calc_velocity(365, launch_counts["1yr"]["count"]),
    }
    
    # Acceleration: is launch rate increasing?
    accel_30_vs_90 = None
    if velocity["last_90d"] > 0:
        accel_30_vs_90 = round(
            ((velocity["last_30d"] - velocity["last_90d"]) / velocity["last_90d"]) * 100,
            1
        )
    
    # Price positioning: new vs catalog
    catalog_prices = [safe_float(p.get("price_min")) for p in products]
    catalog_prices = [x for x in catalog_prices if x is not None and x > 0]
    catalog_median = round(median(catalog_prices), 2) if catalog_prices else None
    
    new_30d_prices = [dp["price"] for dp in launch_groups["30d"] if dp["price"] and dp["price"] > 0]
    new_30d_median = round(median(new_30d_prices), 2) if new_30d_prices else None
    
    new_90d_prices = [dp["price"] for dp in launch_groups["90d"] if dp["price"] and dp["price"] > 0]
    new_90d_median = round(median(new_90d_prices), 2) if new_90d_prices else None
    
    # Price delta
    def delta_pct(new_val: Optional[float], catalog_val: Optional[float]) -> Optional[float]:
        if new_val is None or catalog_val is None or catalog_val == 0:
            return None
        return round(((new_val - catalog_val) / catalog_val) * 100, 1)
    
    price_delta_30d = delta_pct(new_30d_median, catalog_median)
    price_delta_90d = delta_pct(new_90d_median, catalog_median)
    
    # Monthly launch distribution (last 12 months)
    monthly_counts = Counter()
    for dp in dated_products:
        if dp["created"] >= windows["1yr"]:
            month_key = dp["created"].strftime("%Y-%m")
            monthly_counts[month_key] += 1
    
    # Find peak launch months
    peak_months = monthly_counts.most_common(3)
    
    # Vendor concentration in new products
    new_90d_vendors = Counter([dp["vendor"] for dp in launch_groups["90d"]])
    
    return {
        "launch_counts": launch_counts,
        "velocity": velocity,
        "acceleration": {
            "30d_vs_90d_pct": accel_30_vs_90,
            "trend": (
                "Accelerating" if accel_30_vs_90 and accel_30_vs_90 > 15
                else "Decelerating" if accel_30_vs_90 and accel_30_vs_90 < -15
                else "Steady"
            ),
        },
        "price_positioning": {
            "catalog_median": catalog_median,
            "new_30d_median": new_30d_median,
            "new_90d_median": new_90d_median,
            "delta_30d_pct": price_delta_30d,
            "delta_90d_pct": price_delta_90d,
            "strategy": (
                "Premium expansion" if price_delta_90d and price_delta_90d > 15
                else "Budget expansion" if price_delta_90d and price_delta_90d < -15
                else "Consistent positioning"
            ),
        },
        "monthly_distribution": {
            "counts": dict(monthly_counts),
            "peak_months": [{"month": m, "count": c} for m, c in peak_months],
        },
        "new_product_vendors": {
            "90d_top_3": [
                {"vendor": v, "count": c, "pct": pct(c, len(launch_groups["90d"]))}
                for v, c in new_90d_vendors.most_common(3)
            ] if launch_groups["90d"] else [],
        },
        "oldest_product": {
            "title": dated_products[0]["product"].get("title"),
            "created": dated_products[0]["created"].strftime("%Y-%m-%d"),
            "age_days": (now - dated_products[0]["created"]).days,
        },
        "newest_product": {
            "title": dated_products[-1]["product"].get("title"),
            "created": dated_products[-1]["created"].strftime("%Y-%m-%d"),
            "age_days": (now - dated_products[-1]["created"]).days,
        },
    }

def generate_launch_insights(analysis: Dict[str, Any]) -> List[str]:
    """Generate actionable insights from launch timeline analysis."""
    insights = []
    
    velocity = analysis.get("velocity", {})
    launch_counts = analysis.get("launch_counts", {})
    acceleration = analysis.get("acceleration", {})
    price_pos = analysis.get("price_positioning", {})
    
    # Velocity insight
    v30 = velocity.get("last_30d", 0)
    if v30 >= 10:
        insights.append(
            f"High launch velocity: {v30} products/month recently, indicating aggressive expansion."
        )
    elif v30 >= 3:
        insights.append(
            f"Moderate launch velocity: {v30} products/month, showing steady growth."
        )
    else:
        insights.append(
            f"Low launch velocity: {v30} products/month, suggesting mature/stable catalog."
        )
    
    # Acceleration insight
    trend = acceleration.get("trend")
    accel_val = acceleration.get("30d_vs_90d_pct")
    if trend == "Accelerating" and accel_val:
        insights.append(
            f"Launch rate accelerating ({accel_val:+.0f}% vs 90d avg)—they're ramping up."
        )
    elif trend == "Decelerating" and accel_val:
        insights.append(
            f"Launch rate decelerating ({accel_val:+.0f}% vs 90d avg)—expansion cooling off."
        )
    
    # Price strategy insight
    strategy = price_pos.get("strategy")
    delta = price_pos.get("delta_90d_pct")
    new_median = price_pos.get("new_90d_median")
    cat_median = price_pos.get("catalog_median")
    
    if strategy and delta is not None and new_median and cat_median:
        insights.append(
            f"{strategy}: New products (90d) at ${new_median} vs catalog ${cat_median} "
            f"({delta:+.0f}% delta)."
        )
    
    # Recency insight
    count_30d = launch_counts.get("30d", {}).get("count", 0)
    pct_30d = launch_counts.get("30d", {}).get("pct", 0)
    
    if pct_30d >= 5:
        insights.append(
            f"{pct_30d}% of catalog ({count_30d} products) launched in last 30 days—very fresh inventory."
        )
    
    return insights
def analyze_products(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(products)
    updates_pack = compute_new_vs_old_and_updates(products)
    out_new_old = updates_pack["new_vs_old"]
    out_updates = updates_pack["update_activity"]



    created_dts = [parse_dt(p.get("created_at")) for p in products]
    updated_dts = [parse_dt(p.get("updated_at")) for p in products]

    created_missing = sum(1 for d in created_dts if d is None)
    updated_missing = sum(1 for d in updated_dts if d is None)

    def count_since(dts: List[Optional[datetime]], days: int) -> int:
        cut = cutoff_days(days)
        return sum(1 for d in dts if d is not None and d >= cut)
    c30, c90, c180 = count_since(created_dts, 30), count_since(created_dts,90), count_since(created_dts, 180)
    # Replace:
# u30, u90, u180 = count_since(updated_dts, 30), ...

    u30 = out_updates.get("updated_30", 0)
    u90 = out_updates.get("updated_90", 0)
    u180 = out_updates.get("updated_180", 0)


    new_vs_old = {
        "total": total,
        "created": {
            "d30": {"count": c30, "pct": pct(c30, total)},
            "d90": {"count": c90, "pct": pct(c90, total)},
            "d180": {"count": c180, "pct": pct(c180, total)},
            "missing": created_missing,
        },
        "updated": {
            "d30": {"count": u30, "pct": pct(u30, total)},
            "d90": {"count": u90, "pct": pct(u90, total)},
            "d180": {"count": u180, "pct": pct(u180, total)},
            "missing": updated_missing,
        },
    }

    in_stock = [p for p in products if bool(p.get("available"))]
    out_stock = [p for p in products if not bool(p.get("available"))]

    vendors = Counter((p.get("vendor") or "Unknown").strip() for p in products)

    prices_all = [safe_float(p.get("price_min")) for p in products]
    prices_pos = [x for x in prices_all if x is not None and x > 0]
    zero_price_count = sum(1 for x in prices_all if x == 0)
    priced_count = sum(1 for x in prices_all if x is not None)

    # buckets
    bucket_counts = Counter()
    for p in products:
        pr = safe_float(p.get("price_min"))
        if pr is None or pr <= 0:
            continue
        bucket_counts[price_bucket(pr)] += 1

    discounts = []
    for p in products:
        pr = safe_float(p.get("price_min"))
        ca = safe_float(p.get("compare_at_min"))
        if pr is None or pr <= 0:
            continue
        d = compute_discount_pct(pr, ca)
        if d is not None:
            discounts.append(d)

    discounted_count = len(discounts)

    # lists
    def newest_dt(p):
        return parse_dt(p.get("created_at")) or parse_dt(p.get("published_at")) or datetime.min

    def updated_dt(p):
        return parse_dt(p.get("updated_at")) or datetime.min

    def expensive_key(p):
        v = safe_float(p.get("price_min"))
        return (v is not None, v or -1)

    def discount_key(p):
        pr = safe_float(p.get("price_min"))
        ca = safe_float(p.get("compare_at_min"))
        d = compute_discount_pct(pr, ca)
        return (d is not None, d or -1)

    top_expensive = sorted(products, key=expensive_key, reverse=True)[:10]
    top_discounts = [p for p in sorted(products, key=discount_key, reverse=True) if discount_key(p)[0]][:10]
    newest = sorted(products, key=newest_dt, reverse=True)[:10]
    recently_updated = sorted(products, key=updated_dt, reverse=True)[:10]

    # signals
    image_counts = [len(p.get("images", []) or []) for p in products]
    avg_images = round(sum(image_counts) / total, 2) if total else 0.0

    variants_counts = []
    for p in products:
        vc = p.get("variants_count")
        try:
            variants_counts.append(int(vc))
        except Exception:
            pass
    avg_variants = round(sum(variants_counts) / len(variants_counts), 2) if variants_counts else None

    price_median = median(prices_pos) if prices_pos else None
    price_min = min(prices_pos) if prices_pos else None
    price_max = max(prices_pos) if prices_pos else None

        # -------- COMPARATIVE INSIGHTS --------
    discounted_prices: List[float] = []
    full_prices: List[float] = []
    discount_pcts: List[float] = []

    for p in products:
        pr = safe_float(p.get("price_min"))
        ca = safe_float(p.get("compare_at_min"))
        if pr is None:
            continue
        d = compute_discount_pct(pr, ca)
        if d is not None:
            discounted_prices.append(pr)
            discount_pcts.append(d)
        else:
            full_prices.append(pr)

    discounted_share_pct = pct(len(discounted_prices), total)

    # New products (90d) vs catalog median
    cut90 = cutoff_days(90)
    new90_prices = []
    for p in products:
        dt = parse_dt(p.get("created_at")) or parse_dt(p.get("published_at"))
        pr = safe_float(p.get("price_min"))
        if dt is not None and pr is not None and dt >= cut90:
            new90_prices.append(pr)

    new90_median = median_or_none(new90_prices)
    full_median = median_or_none(full_prices)
    disc_median = median_or_none(discounted_prices)
    disc_pct_median = median_or_none(discount_pcts)

    def delta_pct(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None or b == 0:
            return None
        return round((a - b) / b * 100.0, 2)

    comparative = {
        "discounted_share": {"count": len(discounted_prices), "pct": discounted_share_pct},
        "median_price_discounted": round(disc_median, 2) if disc_median is not None else None,
        "median_price_full": round(full_median, 2) if full_median is not None else None,
        "median_discount_pct": round(disc_pct_median, 2) if disc_pct_median is not None else None,
        "new_products": {
            "window_days": 90,
            "count": len(new90_prices),
            "pct": pct(len(new90_prices), total),
            "median_price": round(new90_median, 2) if new90_median is not None else None,
            "catalog_median_price": round(price_median, 2) if price_median is not None else None,
            "price_delta_pct": delta_pct(new90_median, price_median),
        },
    }

        # -------- COMPETITIVE POSITIONING SNAPSHOT (heuristics) --------
    def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, x))

    def score_weighted(parts: List[tuple[Optional[float], float]]) -> int:
        usable = [(v, w) for (v, w) in parts if v is not None]
        if not usable:
            return 0
        total_w = sum(w for _, w in usable)
        if total_w <= 0:
            return 0
        s = sum(clamp(v) * w for v, w in usable) / total_w
        return int(round(clamp(s)))

    # Market position label based on median price (simple but works)
    market_position = "—"
    if price_median is not None:
        if price_median < 40:
            market_position = "Budget"
        elif price_median < 120:
            market_position = "Mid-Market"
        else:
            market_position = "Premium"

    promo_intensity_score = score_weighted([
        (comparative["discounted_share"]["pct"], 0.6),          # more discounted items => more promo-heavy
        (comparative["median_discount_pct"], 0.4),              # deeper discounts => more promo-heavy
    ])

    launch_velocity_score = score_weighted([
        (new_vs_old["created"]["d90"]["pct"], 0.6),
        (out_updates.get("updated_90_pct", 0), 0.4),

    ])

    # Catalog complexity: size + price spread + variants (if you have it)
    spread_score = None
    if price_min is not None and price_max is not None and price_max > price_min:
        # map a reasonable spread to 0–100 (tuned for consumer ecommerce)
        spread = price_max - price_min
        spread_score = clamp((spread / 300.0) * 100.0)

    size_score = clamp((total / 2500.0) * 100.0)  # since you cap around 2500 often

    variants_score = None
    if avg_variants is not None:
        variants_score = clamp(((avg_variants - 1.0) / 4.0) * 100.0)

    catalog_complexity_score = score_weighted([
        (size_score, 0.45),
        (spread_score, 0.35),
        (variants_score, 0.20),
    ])

    def score_label(score: int) -> str:
        if score >= 75: return "High"
        if score >= 45: return "Medium"
        return "Low"


    positioning = {
    "market_position": {
        "label": market_position,
        "note": "Based on catalog median price (simple heuristic).",
    },
    "promo_intensity": {
        "score": promo_intensity_score,
        "label": score_label(promo_intensity_score),
        "note": "Blend of discounted share + median discount depth.",
    },
    "launch_velocity": {
        "score": launch_velocity_score,
        "label": score_label(launch_velocity_score),
        "note": "Blend of new product + update activity (last 90 days).",
    },
    "catalog_complexity": {
        "score": catalog_complexity_score,
        "label": score_label(catalog_complexity_score),
        "note": "Blend of catalog size + price spread + variants.",
    },
}

    # -------- TAKEAWAYS (killer feature) --------
    takeaways: List[str] = []
    confidence_notes: List[str] = []
    launch = analyze_launch_timeline(products)
    launch_takeaways = generate_launch_insights(launch) if launch else []

    takeaways.extend(launch_takeaways)

    if total:
        in_stock_pct = pct(len(in_stock), total)
        takeaways.append(f"{in_stock_pct}% of products are currently in stock, which suggests {'stable inventory' if in_stock_pct >= 80 else 'potential stock gaps to exploit'}.")

        disc_pct = pct(discounted_count, total)
        takeaways.append(f"{disc_pct}% of products show valid discounts (compare-at > price), indicating {'aggressive promotion' if disc_pct >= 30 else 'limited discounting'}.")

        if price_median is not None and price_min is not None and price_max is not None:
            takeaways.append(f"Pricing spans ${price_min:.2f}–${price_max:.2f} with a median of ${price_median:.2f}. Position your core offer near the median to compete directly.")

        # dominant bucket
        if bucket_counts:
            top_bucket, top_bucket_count = bucket_counts.most_common(1)[0]
            top_bucket_pct = pct(top_bucket_count, total)
            takeaways.append(f"The dominant price band is {top_bucket} ({top_bucket_pct}% of products), showing where they primarily compete.")

        # new products skew vs median
        newest_prices = [safe_float(p.get("price_min")) for p in newest]
        newest_prices = [x for x in newest_prices if x is not None]
        if price_median is not None and newest_prices:
            newest_med = median(newest_prices)
            if newest_med > price_median:
                takeaways.append("Newest products skew above the store median price, suggesting a premium expansion strategy.")
            elif newest_med < price_median:
                takeaways.append("Newest products skew below the store median price, suggesting a push toward cheaper volume offers.")
            else:
                takeaways.append("Newest products price near the median, suggesting steady positioning rather than a strategic shift.")

        if avg_variants is not None:
            if avg_variants <= 1.3:
                takeaways.append("Most products have few variants, suggesting a simpler catalog (often easier ops) and fewer customization options.")
            else:
                takeaways.append("Products have multiple variants on average, suggesting upsell/option strategy (sizes, bundles, tiers).")
        if zero_price_count > 0:
            confidence_notes.append(
                f"{zero_price_count} products had a  $0 price and were excluded from price statistics (ofetn samples, placeholders, or gated pricing)"
                
            )
        if priced_count == 0:
            confidence_notes.append("No usable pricing was found in the public products.json feed")
        
    
   
    
    # Timestamp coverage
    if total:
        cm = pct(new_vs_old["created"]["missing"], total)
        um = pct(new_vs_old["updated"]["missing"], total)
        if cm > 20:
            confidence_notes.append(f"Created dates missing for {cm}% of products; new-product timing may be understated.")
        if um > 20:
            confidence_notes.append(f"Updated dates missing for {um}% of products; update-activity may be understated.")

    # Discount coverage (compare_at not always used)
    if total and comparative["discounted_share"]["pct"] < 5:
        confidence_notes.append("Low discount detection: store may not use compare-at pricing consistently.")
    
    comparisons = {
     "new_vs_old": {
        "created_30": out_new_old.get("created_30", 0),
        "created_30_pct": out_new_old.get("created_30_pct", 0),
        "created_90": out_new_old.get("created_90", 0),
        "created_90_pct": out_new_old.get("created_90_pct", 0),
        "created_180": out_new_old.get("created_180", 0),
        "created_180_pct": out_new_old.get("created_180_pct", 0),
        "new_90_median_price": out_new_old.get("new_90_median_price"),
        "catalog_median_price": out_new_old.get("catalog_median_price"),
    },
    "update_activity": {
        "updated_30": out_updates.get("updated_30", 0),
        "updated_30_pct": out_updates.get("updated_30_pct", 0),
        "updated_90": out_updates.get("updated_90", 0),
        "updated_90_pct": out_updates.get("updated_90_pct", 0),

        "bulk_update_flag": out_updates.get("bulk_update_flag", False),
        "bulk_update_bucket": out_updates.get("bulk_update_bucket"),
        "bulk_update_dominant_pct": out_updates.get("bulk_update_dominant_pct", 0),
        "bulk_filter_applied": out_updates.get("bulk_filter_applied", False),

        # optional debug fields (nice for you while testing)
        "updated_30_raw": out_updates.get("updated_30_raw", 0),
        "updated_30_raw_pct": out_updates.get("updated_30_raw_pct", 0),
        "updated_90_raw": out_updates.get("updated_90_raw", 0),
        "updated_90_raw_pct": out_updates.get("updated_90_raw_pct", 0),
    },
    "discounted_vs_full_price": {
        "discounted_count": len(discounted_prices),
        "discounted_pct": pct(len(discounted_prices), total),
        "discounted_median_price": round(disc_median, 2) if disc_median is not None else None,
        "full_price_median_price": round(full_median, 2) if full_median is not None else None,
    }
}

    if out_updates.get("bulk_update_flag"):
        confidence_notes.append(
            f"Update activity may be inflated: {out_updates.get('bulk_update_dominant_pct')}% of meaningful updates occurred on {out_updates.get('bulk_update_bucket')}. "
            + ("We filtered that spike to estimate organic edits." if out_updates.get("bulk_filter_applied") else "Spike detected, but filtering would remove nearly all updates—showing meaningful updates instead.")
        )



    confidence_notes.extend(compute_confidence_notes(products))


    def compact(p: Dict[str, Any]) -> Dict[str, Any]:
        pr = safe_float(p.get("price_min"))
        ca = safe_float(p.get("compare_at_min"))
        return {
            "title": p.get("title"),
            "product_url": p.get("product_url"),
            "price_min": pr,
            "compare_at_min": ca,
            "available": bool(p.get("available")),
            "vendor": p.get("vendor"),
            "discount_pct": compute_discount_pct(pr, ca),
            "created_at": p.get("created_at"),
            "updated_at": p.get("updated_at"),
            "images": (p.get("images") or [])[:1],
        }
    

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "takeaways": takeaways,
        "positioning": positioning,
        "new_vs_old": new_vs_old,
        "comparisons": comparisons,
        "confidence_notes": confidence_notes,
        "launch_timeline": launch,



        "catalog": {
            "total_products": total,
            "in_stock_count": len(in_stock),
            "in_stock_pct": pct(len(in_stock), total),
            "out_of_stock_count": len(out_stock),
            "out_of_stock_pct": pct(len(out_stock), total),
            "vendors": dict(vendors),
            "vendor_count": len(vendors),
        },
        "pricing": {
            "count": len(prices_pos),
            "min": round(price_min, 2) if price_min is not None else None,
            "max": round(price_max, 2) if price_max is not None else None,
            "median": round(price_median, 2) if price_median is not None else None,
            "p25": round(quantile(prices_pos, 0.25), 2) if prices_pos else None,
            "p75": round(quantile(prices_pos, 0.75), 2) if prices_pos else None,
            "price_buckets": {
                "buckets": dict(bucket_counts),
                "bucket_order": ["<$25", "$25–$49", "$50–$99", "$100–$199", "$200–$299", "$300–$499", "$500+"],
            },
        },
        "discounts": {
            "discounted_count": discounted_count,
            "discounted_pct": pct(discounted_count, total),
            "avg_discount_pct": round(sum(discounts) / len(discounts), 2) if discounts else None,
            "median_discount_pct": round(median(discounts), 2) if discounts else None,
            "max_discount_pct": round(max(discounts), 2) if discounts else None,
            "note": "A product is only counted as discounted when compare_at_min > price_min.",
        },
        "content_signals": {
            "avg_images_per_product": avg_images,
            "avg_variants_per_product": avg_variants,
        },
        "lists": {
            "top_expensive": [compact(p) for p in top_expensive],
            "top_discounts": [compact(p) for p in top_discounts],
            "newest_products": [compact(p) for p in newest],
            "recently_updated": [compact(p) for p in recently_updated],
        },
    }
