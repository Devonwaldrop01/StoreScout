from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.database import get_supabase

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{snapshot_id}")
def get_public_report(snapshot_id: str):
    """
    Public (no auth) endpoint for shareable report pages.
    Returns aggregate intelligence from a snapshot — no individual product data.
    """
    db = get_supabase()

    result = db.table("scan_snapshots")\
        .select("id, scanned_at, product_count, median_price, promo_rate, new_30d, snapshot_data")\
        .eq("id", snapshot_id)\
        .maybe_single()\
        .execute()

    if not result or not result.data:
        raise HTTPException(status_code=404, detail="Report not found")

    snap = result.data
    data = snap.get("snapshot_data") or {}

    pricing = data.get("pricing") or {}
    discounts = data.get("discounts") or {}
    positioning = data.get("positioning") or {}
    launch = data.get("launch_timeline") or {}
    takeaways = data.get("takeaways") or []

    return {
        "data": {
            "snapshot_id": snap["id"],
            "scanned_at": snap["scanned_at"],
            "hostname": data.get("hostname") or data.get("display_name") or "Unknown Store",
            "product_count": snap.get("product_count"),
            "pricing": {
                "median": pricing.get("median"),
                "min": pricing.get("min"),
                "max": pricing.get("max"),
                "p25": pricing.get("p25"),
                "p75": pricing.get("p75"),
                "bucket_counts": pricing.get("bucket_counts") or {},
            },
            "discounts": {
                "discounted_pct": discounts.get("discounted_pct"),
                "avg_discount_pct": discounts.get("avg_discount_pct"),
            },
            "launch": {
                "new_30d": ((launch.get("launch_counts") or {}).get("30d") or {}).get("count"),
                "new_90d": ((launch.get("launch_counts") or {}).get("90d") or {}).get("count"),
            },
            "positioning": {
                "market_position": positioning.get("market_position"),
                "promo_intensity": positioning.get("promo_intensity"),
                "launch_velocity": positioning.get("launch_velocity"),
                "catalog_complexity": positioning.get("catalog_complexity"),
            },
            "takeaways": takeaways[:5],
        }
    }
