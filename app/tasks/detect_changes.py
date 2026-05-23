from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .celery_app import celery
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

# Price move smaller than this % is noise
PRICE_CHANGE_THRESHOLD_PCT = 3.0
# Flash sale: N+ products each dropping >= this %
FLASH_SALE_MIN_PRODUCTS = 5
FLASH_SALE_MIN_AVG_DROP_PCT = 20.0
# Catalog-level discount rate swing that counts as a campaign start/end
DISCOUNT_RATE_SWING_PCT = 10.0


def _product_index(snapshot_data: dict) -> Dict[str, dict]:
    """
    Return the full handle → product dict stored by the scan pipeline.
    Falls back to the old lists-based approach for snapshots taken before
    the _product_index field was added.
    """
    idx = snapshot_data.get("_product_index")
    if idx and isinstance(idx, dict):
        return idx

    # Legacy fallback: rebuild from the top-N lists stored in snapshot_data
    products: Dict[str, dict] = {}
    lists = snapshot_data.get("lists") or {}
    for section in ("recently_updated", "newest_products", "top_expensive", "top_discounts"):
        for p in lists.get(section) or []:
            handle = p.get("handle")
            if handle:
                products[handle] = p
    return products


def _detect(old_snap: dict, new_snap: dict) -> List[dict]:
    old_products = _product_index(old_snap)
    new_products = _product_index(new_snap)
    changes: List[dict] = []

    # ── New products ────────────────────────────────────────────────────────
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

    # ── Removed products ────────────────────────────────────────────────────
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

    # ── Price changes ────────────────────────────────────────────────────────
    price_drops: List[float] = []
    for handle, new_prod in new_products.items():
        old_prod = old_products.get(handle)
        if not old_prod:
            continue
        old_price = old_prod.get("price_min")
        new_price = new_prod.get("price_min")
        if old_price is None or new_price is None or old_price == 0:
            continue
        if old_price == new_price:
            continue
        delta_pct = round((new_price - old_price) / old_price * 100, 2)
        if abs(delta_pct) < PRICE_CHANGE_THRESHOLD_PCT:
            continue
        severity = "warning" if delta_pct <= -10 else "info"
        if delta_pct <= -10:
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

    # Flash sale: upgrade severity when many products drop sharply at once
    if len(price_drops) >= FLASH_SALE_MIN_PRODUCTS:
        avg_drop = sum(price_drops) / len(price_drops)
        if avg_drop >= FLASH_SALE_MIN_AVG_DROP_PCT:
            for c in changes:
                if c["change_type"] == "price_change" and (c["delta_pct"] or 0) < 0:
                    c["severity"] = "critical"

    # ── Availability changes ─────────────────────────────────────────────────
    for handle, new_prod in new_products.items():
        old_prod = old_products.get(handle)
        if not old_prod:
            continue
        old_avail = old_prod.get("available")
        new_avail = new_prod.get("available")
        if old_avail is None or new_avail is None or old_avail == new_avail:
            continue
        changes.append({
            "change_type": "availability_change",
            "product_handle": handle,
            "product_title": new_prod.get("title"),
            "product_url": new_prod.get("product_url"),
            "old_value": {"available": old_avail},
            "new_value": {"available": new_avail},
            "delta_pct": None,
            "severity": "warning" if not new_avail else "info",
        })

    # ── Catalog-level discount campaign start/end ────────────────────────────
    old_disc_pct = (old_snap.get("discounts") or {}).get("discounted_pct", 0) or 0
    new_disc_pct = (new_snap.get("discounts") or {}).get("discounted_pct", 0) or 0
    delta_disc = new_disc_pct - old_disc_pct
    if abs(delta_disc) >= DISCOUNT_RATE_SWING_PCT:
        changes.append({
            "change_type": "discount_start" if delta_disc > 0 else "discount_end",
            "product_handle": None,
            "product_title": None,
            "product_url": None,
            "old_value": {"discounted_pct": round(old_disc_pct, 1)},
            "new_value": {"discounted_pct": round(new_disc_pct, 1)},
            "delta_pct": round(delta_disc, 2),
            "severity": "warning" if delta_disc > 0 else "info",
        })

    return changes


@celery.task(name="app.tasks.detect_changes.detect_changes")
def detect_changes(competitor_id: str, snapshot_id: str) -> dict:
    db = get_supabase()
    logger.info("[DETECT %s] starting for snapshot %s", competitor_id, snapshot_id)

    snaps = db.table("scan_snapshots")\
        .select("id, snapshot_data, scanned_at")\
        .eq("competitor_id", competitor_id)\
        .order("scanned_at", desc=True)\
        .limit(2)\
        .execute()

    if not snaps.data or len(snaps.data) < 2:
        logger.info("[DETECT %s] only %d snapshot(s) — skipping diff", competitor_id, len(snaps.data or []))
        return {"status": "no_previous_snapshot"}

    new_snap_data = snaps.data[0]["snapshot_data"]
    old_snap_data = snaps.data[1]["snapshot_data"]

    old_count = len(_product_index(old_snap_data))
    new_count = len(_product_index(new_snap_data))
    logger.info("[DETECT %s] old=%d products new=%d products", competitor_id, old_count, new_count)

    changes = _detect(old_snap_data, new_snap_data)
    logger.info("[DETECT %s] found %d change(s)", competitor_id, len(changes))

    if not changes:
        return {"status": "no_changes"}

    now = datetime.now(timezone.utc).isoformat()
    rows = [{**c, "competitor_id": competitor_id, "detected_at": now} for c in changes]

    insert_result = db.table("change_events").insert(rows).execute()
    inserted_ids = [r["id"] for r in (insert_result.data or []) if r.get("id")]
    logger.info("[DETECT %s] inserted %d change_events", competitor_id, len(inserted_ids))

    if inserted_ids:
        comp = db.table("competitors").select("user_id, is_my_store").eq("id", competitor_id).maybe_single().execute()
        # Don't email users about changes to their own store — only competitors.
        if comp and comp.data and not comp.data.get("is_my_store"):
            from app.tasks.alerts import send_change_alert
            send_change_alert.apply_async(
                args=[comp.data["user_id"], competitor_id, inserted_ids],
                queue="priority",
            )

    return {"status": "ok", "changes": len(rows), "inserted": len(inserted_ids)}
