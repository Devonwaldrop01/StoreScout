from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from .celery_app import celery
from app.core.config import get_settings
from app.core.database import get_supabase
from app.services.fetch import fetch_products_shopify
from app.services.normalize import normalize_product
from app.services.analyze import analyze_products

logger = logging.getLogger(__name__)


def _interval_for_tier(tier: str) -> int:
    s = get_settings()
    return {
        "pro": s.pro_scan_interval_hours,
        "agency": s.agency_scan_interval_hours,
    }.get(tier, s.free_scan_interval_hours)


@celery.task(bind=True, max_retries=3, default_retry_delay=30, name="app.tasks.scan.scan_competitor")
def scan_competitor(self, competitor_id: str) -> dict:
    db = get_supabase()

    # Mark as scanning
    db.table("competitors").update({
        "scan_status": "scanning",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", competitor_id).execute()

    try:
        # Fetch competitor record
        result = db.table("competitors").select("*, user_profiles(tier)").eq("id", competitor_id).maybe_single().execute()
        competitor = result.data if result else None
        if not competitor:
            return {"status": "error", "reason": "competitor_not_found"}

        store_url = competitor["store_url"]
        tier = (competitor.get("user_profiles") or {}).get("tier", "free")

        # Skip-if-unchanged optimization: only probe if a previous snapshot exists
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
                    prev_data = last_snap.data[0]["snapshot_data"]
                    prev_newest = (prev_data.get("lists") or {}).get("recently_updated", [])
                    if prev_newest and prev_newest[0].get("updated_at") == latest_updated:
                        interval_h = _interval_for_tier(tier)
                        next_scan = datetime.now(timezone.utc) + timedelta(hours=interval_h)
                        db.table("competitors").update({
                            "scan_status": "done",
                            "last_scanned_at": datetime.now(timezone.utc).isoformat(),
                            "next_scan_at": next_scan.isoformat(),
                        }).eq("id", competitor_id).execute()
                        return {"status": "unchanged"}
        except Exception:
            pass  # Skip optimization on any error — proceed with full fetch

        # Full fetch + analyze
        raw = fetch_products_shopify(store_url)
        if not raw:
            raise ValueError(f"No products returned for {store_url}")

        normalized = [normalize_product(p, store_url) for p in raw]
        insights = analyze_products(normalized)

        # Extract key metrics for fast queries
        pricing = insights.get("pricing", {})
        discounts = insights.get("discounts", {})
        launch = insights.get("launch_timeline", {})

        median_price = pricing.get("median")
        promo_rate = discounts.get("discounted_pct")
        new_30d = (launch.get("launch_counts") or {}).get("30d", {}).get("count")
        product_count = (insights.get("catalog") or {}).get("total_products")

        now = datetime.now(timezone.utc)

        # Write snapshot
        snap_result = db.table("scan_snapshots").insert({
            "competitor_id": competitor_id,
            "scanned_at": now.isoformat(),
            "product_count": product_count,
            "median_price": median_price,
            "promo_rate": promo_rate,
            "new_30d": new_30d,
            "snapshot_data": insights,
        }).execute()

        snapshot_id = snap_result.data[0]["id"] if snap_result.data else None

        # Update competitor record
        interval_h = _interval_for_tier(tier)
        next_scan = now + timedelta(hours=interval_h)
        db.table("competitors").update({
            "scan_status": "done",
            "last_scanned_at": now.isoformat(),
            "next_scan_at": next_scan.isoformat(),
            "product_count": product_count,
            "error_message": None,
        }).eq("id", competitor_id).execute()

        # Chain change detection
        if snapshot_id:
            from app.tasks.detect_changes import detect_changes
            detect_changes.delay(competitor_id, snapshot_id)

        return {"status": "ok", "products": product_count, "snapshot_id": snapshot_id}

    except Exception as exc:
        logger.error(f"Scan failed for {competitor_id}: {exc}")
        err_str = str(exc)
        # 403 = store blocked this IP — retrying just makes it worse
        is_permanent = "403" in err_str or "Forbidden" in err_str
        retry_count = self.request.retries
        if is_permanent or retry_count >= self.max_retries:
            db.table("competitors").update({
                "scan_status": "error",
                "error_message": err_str[:500],
            }).eq("id", competitor_id).execute()
        else:
            db.table("competitors").update({"scan_status": "pending"}).eq("id", competitor_id).execute()
            raise self.retry(exc=exc, countdown=30 * (2 ** retry_count))
        return {"status": "error", "reason": err_str}


@celery.task(name="app.tasks.scan.manual_rescan")
def manual_rescan(competitor_id: str) -> dict:
    """Triggered by user — goes to priority queue."""
    return scan_competitor(competitor_id)
