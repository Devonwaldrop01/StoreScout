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

    # ── 3. Full fetch ────────────────────────────────────────────────────────
    logger.info("[SCAN %s] starting full fetch for %r", competitor_id, store_url)
    try:
        raw = fetch_products_shopify(store_url)
    except Exception as exc:
        logger.error("[SCAN %s] fetch_products_shopify raised exception: %s\n%s",
                     competitor_id, exc, traceback.format_exc())
        _mark_error(db, competitor_id, f"fetch exception: {exc}")
        return {"status": "error", "reason": f"fetch exception: {exc}"}

    logger.info("[SCAN %s] fetch returned %d raw products", competitor_id, len(raw))

    if not raw:
        logger.error("[SCAN %s] fetch returned empty list for %r — see FETCH logs above for root cause",
                     competitor_id, store_url)
        _mark_error(db, competitor_id, f"No products returned for {store_url}")
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

    logger.info("[SCAN %s] COMPLETE snapshot_id=%s", competitor_id, snapshot_id)
    return {"status": "ok", "snapshot_id": snapshot_id}


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
