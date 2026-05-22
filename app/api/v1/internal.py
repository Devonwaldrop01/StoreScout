from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Header, HTTPException

from app.core.config import get_settings
from app.core.database import get_supabase
from app.services.fetch import fetch_products_shopify
from app.services.normalize import normalize_product
from app.services.analyze import analyze_products

router = APIRouter(prefix="/internal", tags=["internal"])
logger = logging.getLogger(__name__)


def _require_internal(x_internal_token: str = Header(...)):
    if x_internal_token != get_settings().internal_secret:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/scan/{competitor_id}")
def internal_scan(competitor_id: str, x_internal_token: str = Header(...)):
    """
    Runs the Shopify fetch + analyze + DB write on the web service process,
    which uses the web service's outbound IP (not the worker's IP).
    Called by the Celery worker instead of hitting Shopify directly.
    """
    _require_internal(x_internal_token)
    settings = get_settings()
    db = get_supabase()

    result = db.table("competitors")\
        .select("store_url, user_profiles(tier)")\
        .eq("id", competitor_id)\
        .maybe_single()\
        .execute()

    if not result or not result.data:
        return {"status": "error", "reason": "competitor_not_found"}

    competitor = result.data
    store_url = competitor["store_url"]
    tier = (competitor.get("user_profiles") or {}).get("tier", "free")

    # Skip-if-unchanged: only probe if a previous snapshot exists
    try:
        last_snap = db.table("scan_snapshots")\
            .select("snapshot_data")\
            .eq("competitor_id", competitor_id)\
            .order("scanned_at", desc=True)\
            .limit(1)\
            .execute()
        if last_snap.data:
            probe = fetch_products_shopify(store_url, max_products=1)
            if probe:
                latest_updated = probe[0].get("updated_at", "")
                prev_newest = (last_snap.data[0]["snapshot_data"].get("lists") or {}).get("recently_updated", [])
                if prev_newest and prev_newest[0].get("updated_at") == latest_updated:
                    interval_h = _interval_for_tier(tier, settings)
                    next_scan = datetime.now(timezone.utc) + timedelta(hours=interval_h)
                    db.table("competitors").update({
                        "scan_status": "done",
                        "last_scanned_at": datetime.now(timezone.utc).isoformat(),
                        "next_scan_at": next_scan.isoformat(),
                    }).eq("id", competitor_id).execute()
                    return {"status": "unchanged"}
    except Exception:
        pass

    raw = fetch_products_shopify(store_url)
    if not raw:
        return {"status": "error", "reason": f"No products returned for {store_url}"}

    normalized = [normalize_product(p, store_url) for p in raw]
    insights = analyze_products(normalized)

    pricing = insights.get("pricing", {})
    discounts = insights.get("discounts", {})
    launch = insights.get("launch_timeline", {})
    now = datetime.now(timezone.utc)

    snap_result = db.table("scan_snapshots").insert({
        "competitor_id": competitor_id,
        "scanned_at": now.isoformat(),
        "product_count": (insights.get("catalog") or {}).get("total_products"),
        "median_price": pricing.get("median"),
        "promo_rate": discounts.get("discounted_pct"),
        "new_30d": (launch.get("launch_counts") or {}).get("30d", {}).get("count"),
        "snapshot_data": insights,
    }).execute()

    snapshot_id = snap_result.data[0]["id"] if snap_result.data else None

    interval_h = _interval_for_tier(tier, settings)
    db.table("competitors").update({
        "scan_status": "done",
        "last_scanned_at": now.isoformat(),
        "next_scan_at": (now + timedelta(hours=interval_h)).isoformat(),
        "product_count": (insights.get("catalog") or {}).get("total_products"),
        "error_message": None,
    }).eq("id", competitor_id).execute()

    logger.info("Internal scan complete for %s: snapshot %s", competitor_id, snapshot_id)
    return {"status": "ok", "snapshot_id": snapshot_id}


def _interval_for_tier(tier: str, settings) -> int:
    return {"pro": settings.pro_scan_interval_hours, "agency": settings.agency_scan_interval_hours}.get(
        tier, settings.free_scan_interval_hours
    )
