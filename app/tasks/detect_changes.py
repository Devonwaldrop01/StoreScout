from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .celery_app import celery
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

# Changes below this price-delta % are noise
PRICE_CHANGE_THRESHOLD_PCT = 3.0
# Flash sale = 5+ products with avg >= 20% drop
FLASH_SALE_COUNT = 5
FLASH_SALE_AVG_PCT = 20.0


def _index_products(snapshot_data: dict) -> Dict[str, dict]:
    """Build handle → product dict from lists.recently_updated + lists.newest_products."""
    products: Dict[str, dict] = {}
    lists = snapshot_data.get("lists") or {}
    for section in ("recently_updated", "newest_products", "top_expensive", "top_discounts"):
        for p in lists.get(section) or []:
            handle = p.get("handle")
            if handle:
                products[handle] = p
    return products


def _detect(old_snap: dict, new_snap: dict) -> List[dict]:
    """Return list of change dicts from two snapshot_data blobs."""
    changes: List[dict] = []
    old_products = _index_products(old_snap)
    new_products = _index_products(new_snap)

    # New products (in new but not old)
    for handle, prod in new_products.items():
        if handle not in old_products:
            changes.append({
                "change_type": "new_product",
                "product_handle": handle,
                "product_title": prod.get("title"),
                "product_url": prod.get("product_url"),
                "old_value": None,
                "new_value": {"price_min": prod.get("price_min")},
                "delta_pct": None,
                "severity": "info",
            })

    # Products removed (in old but not new)
    for handle, prod in old_products.items():
        if handle not in new_products:
            changes.append({
                "change_type": "product_removed",
                "product_handle": handle,
                "product_title": prod.get("title"),
                "product_url": prod.get("product_url"),
                "old_value": {"price_min": prod.get("price_min")},
                "new_value": None,
                "delta_pct": None,
                "severity": "info",
            })

    # Price changes
    price_drops: List[float] = []
    for handle, new_prod in new_products.items():
        old_prod = old_products.get(handle)
        if not old_prod:
            continue
        old_price = old_prod.get("price_min")
        new_price = new_prod.get("price_min")
        if old_price is None or new_price is None or old_price == 0:
            continue
        delta_pct = round((new_price - old_price) / old_price * 100, 2)
        if abs(delta_pct) < PRICE_CHANGE_THRESHOLD_PCT:
            continue
        severity = "info"
        if delta_pct <= -10:
            severity = "warning"
            price_drops.append(abs(delta_pct))
        changes.append({
            "change_type": "price_change",
            "product_handle": handle,
            "product_title": new_prod.get("title"),
            "product_url": new_prod.get("product_url"),
            "old_value": {"price": old_price},
            "new_value": {"price": new_price},
            "delta_pct": delta_pct,
            "severity": severity,
        })

    # Flash sale detection: upgrade severity on multiple drops
    if len(price_drops) >= FLASH_SALE_COUNT:
        avg_drop = sum(price_drops) / len(price_drops)
        if avg_drop >= FLASH_SALE_AVG_PCT:
            for c in changes:
                if c["change_type"] == "price_change" and (c["delta_pct"] or 0) < 0:
                    c["severity"] = "critical"

    # Discount start/end (compare_at changes)
    old_disc_pct = (old_snap.get("discounts") or {}).get("discounted_pct", 0) or 0
    new_disc_pct = (new_snap.get("discounts") or {}).get("discounted_pct", 0) or 0
    delta_disc = new_disc_pct - old_disc_pct
    if abs(delta_disc) >= 10:
        change_type = "discount_start" if delta_disc > 0 else "discount_end"
        changes.append({
            "change_type": change_type,
            "product_handle": None,
            "product_title": None,
            "product_url": None,
            "old_value": {"discounted_pct": old_disc_pct},
            "new_value": {"discounted_pct": new_disc_pct},
            "delta_pct": round(delta_disc, 2),
            "severity": "warning" if delta_disc > 0 else "info",
        })

    return changes


@celery.task(name="app.tasks.detect_changes.detect_changes")
def detect_changes(competitor_id: str, snapshot_id: str) -> dict:
    db = get_supabase()

    # Get the two most recent snapshots
    snaps = db.table("scan_snapshots")\
        .select("id, snapshot_data, scanned_at")\
        .eq("competitor_id", competitor_id)\
        .order("scanned_at", desc=True)\
        .limit(2)\
        .execute()

    if not snaps.data or len(snaps.data) < 2:
        return {"status": "no_previous_snapshot"}

    new_snap_data = snaps.data[0]["snapshot_data"]
    old_snap_data = snaps.data[1]["snapshot_data"]

    changes = _detect(old_snap_data, new_snap_data)
    if not changes:
        return {"status": "no_changes"}

    now = datetime.now(timezone.utc).isoformat()
    rows = [{**c, "competitor_id": competitor_id, "detected_at": now} for c in changes]
    db.table("change_events").insert(rows).execute()

    change_ids = [r.get("id") for r in (db.table("change_events")
        .select("id")
        .eq("competitor_id", competitor_id)
        .order("detected_at", desc=True)
        .limit(len(rows))
        .execute().data or [])]

    # Trigger alert if user has alerts enabled
    if change_ids:
        from app.tasks.alerts import send_change_alert
        comp = db.table("competitors").select("user_id").eq("id", competitor_id).single().execute()
        if comp.data:
            send_change_alert.apply_async(
                args=[comp.data["user_id"], competitor_id, change_ids],
                queue="priority",
            )

    return {"status": "ok", "changes": len(rows)}
