from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from app.core.auth import get_current_user_id
from app.core.config import get_settings
from app.core.database import get_supabase

router = APIRouter(prefix="/competitors", tags=["competitors"])


class AddCompetitorRequest(BaseModel):
    store_url: str
    display_name: Optional[str] = None

    @field_validator("store_url")
    @classmethod
    def normalize_url(cls, v: str) -> str:
        v = v.strip().lower()
        if not v.startswith("http"):
            v = "https://" + v
        parsed = urlparse(v)
        return f"https://{parsed.netloc.rstrip('/')}"


class UpdateCompetitorRequest(BaseModel):
    display_name: Optional[str] = None
    is_active: Optional[bool] = None


def _tier_limits(tier: str) -> dict:
    s = get_settings()
    return {
        "free": {"max_competitors": s.free_max_competitors, "scan_hours": s.free_scan_interval_hours},
        "pro": {"max_competitors": s.pro_max_competitors, "scan_hours": s.pro_scan_interval_hours},
        "agency": {"max_competitors": s.agency_max_competitors, "scan_hours": s.agency_scan_interval_hours},
    }.get(tier, {"max_competitors": 1, "scan_hours": 168})


@router.get("")
def list_competitors(user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    result = db.table("competitors").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return {"data": result.data or []}


@router.post("", status_code=status.HTTP_201_CREATED)
def add_competitor(body: AddCompetitorRequest, user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    settings = get_settings()

    # Check tier limits — auto-provision if profile missing (handles users who skipped onboarding)
    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    if not user or not user.data:
        try:
            db.table("user_profiles").insert({
                "id": user_id,
                "email": "",
                "tier": "free",
                "max_competitors": settings.free_max_competitors,
                "scan_interval_hours": settings.free_scan_interval_hours,
                "subscription_status": "inactive",
            }).execute()
        except Exception:
            pass  # already exists (race condition) or RLS blocked — fall through with free defaults
    tier = (user.data or {}).get("tier", "free") if user else "free"
    limits = _tier_limits(tier)

    existing = db.table("competitors").select("id").eq("user_id", user_id).eq("is_active", True).execute()
    if len(existing.data or []) >= limits["max_competitors"]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "competitor_limit_reached",
                "tier": tier,
                "limit": limits["max_competitors"],
                "upgrade_url": f"{settings.public_base_url}/settings/billing",
            },
        )

    # Check for duplicate
    dupe = db.table("competitors").select("id").eq("user_id", user_id).eq("store_url", body.store_url).execute()
    if dupe.data:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Competitor already tracked")

    hostname = urlparse(body.store_url).netloc
    now = datetime.now(timezone.utc)

    row = db.table("competitors").insert({
        "user_id": user_id,
        "store_url": body.store_url,
        "hostname": hostname,
        "display_name": body.display_name,
        "scan_status": "pending",
        "next_scan_at": now.isoformat(),
    }).execute()

    competitor_id = row.data[0]["id"]

    # Trigger immediate scan — non-fatal if Celery is unreachable
    try:
        from app.tasks.scan import scan_competitor
        scan_competitor.delay(competitor_id)
    except Exception as exc:
        logger.warning("Could not enqueue initial scan for %s: %s", competitor_id, exc)

    return {"data": row.data[0]}


@router.patch("/{competitor_id}")
def update_competitor(
    competitor_id: str,
    body: UpdateCompetitorRequest,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = db.table("competitors").update(updates).eq("id", competitor_id).execute()
    return {"data": result.data[0] if result.data else {}}


@router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_competitor(competitor_id: str, user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    db.table("competitors").delete().eq("id", competitor_id).execute()


@router.post("/{competitor_id}/rescan")
def manual_rescan(competitor_id: str, user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)

    competitor = db.table("competitors").select("scan_status").eq("id", competitor_id).single().execute()
    if (competitor.data or {}).get("scan_status") == "scanning":
        raise HTTPException(status_code=409, detail="Scan already in progress")

    from app.tasks.scan import manual_rescan as _rescan
    _rescan.apply_async(args=[competitor_id], queue="priority")
    return {"status": "queued"}


@router.get("/{competitor_id}/snapshots/latest")
def get_latest_snapshot(competitor_id: str, user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    result = db.table("scan_snapshots")\
        .select("id, scanned_at, product_count, median_price, promo_rate, new_30d, snapshot_data")\
        .eq("competitor_id", competitor_id)\
        .order("scanned_at", desc=True)\
        .limit(1)\
        .execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="No snapshots yet")
    return {"data": result.data[0]}


@router.get("/{competitor_id}/snapshots")
def list_snapshots(
    competitor_id: str,
    limit: int = 30,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)

    # History is a paid feature
    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    tier = (user.data or {}).get("tier", "free") if user else "free"
    if tier == "free":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"code": "history_locked", "upgrade_url": "/settings/billing"},
        )

    settings = get_settings()
    cutoff_days = 90 if tier == "pro" else 9999
    cutoff = (datetime.now(timezone.utc) - timedelta(days=cutoff_days)).isoformat()

    result = db.table("scan_snapshots")\
        .select("id, scanned_at, product_count, median_price, promo_rate, new_30d")\
        .eq("competitor_id", competitor_id)\
        .gte("scanned_at", cutoff)\
        .order("scanned_at", desc=True)\
        .limit(limit)\
        .execute()
    return {"data": result.data or []}


@router.get("/{competitor_id}/changes")
def get_changes(
    competitor_id: str,
    limit: int = 50,
    change_type: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)

    query = db.table("change_events")\
        .select("*")\
        .eq("competitor_id", competitor_id)\
        .order("detected_at", desc=True)\
        .limit(limit)
    if change_type:
        query = query.eq("change_type", change_type)
    result = query.execute()
    return {"data": result.data or []}


@router.get("/{competitor_id}/ai-summary")
def get_ai_summary(competitor_id: str, user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)

    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    tier = (user.data or {}).get("tier", "free") if user else "free"
    if tier == "free":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"code": "ai_summary_locked"},
        )

    result = db.table("ai_summaries")\
        .select("*")\
        .eq("competitor_id", competitor_id)\
        .order("generated_at", desc=True)\
        .limit(1)\
        .execute()
    if not result.data:
        # Trigger async generation and return 202
        from app.tasks.ai_summaries import generate_weekly_summary
        generate_weekly_summary.delay(competitor_id, "weekly")
        raise HTTPException(status_code=202, detail="Summary being generated — check back in 30 seconds")
    return {"data": result.data[0]}


@router.get("/{competitor_id}/winning-products")
def get_winning_products(competitor_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Winning-product analysis. Free tier sees the #1 product (score visible, the
    'why' locked) plus a locked count. Pro/Agency see the full ranked list,
    signal breakdowns, reasons, and the newest-products list.
    """
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    tier = _user_tier(db, user_id)

    data = _latest_snapshot_data(db, competitor_id)
    wp = (data.get("winning_products") or {}) if data else {}
    products = wp.get("products") or []
    newest = wp.get("newest") or []

    if not products:
        return {"data": {"products": [], "newest": [], "locked": tier == "free", "locked_count": 0, "tier": tier}}

    if tier == "free":
        top = products[0]
        teaser = {
            "title": top.get("title"),
            "product_url": top.get("product_url"),
            "price_min": top.get("price_min"),
            "image": top.get("image"),
            "score": top.get("score"),
            # 'why' is locked
            "reason": None,
            "signal_tags": [],
            "locked": True,
        }
        return {
            "data": {
                "products": [teaser],
                "newest": [],
                "locked": True,
                "locked_count": max(0, len(products) - 1),
                "tier": tier,
            }
        }

    return {
        "data": {
            "products": products,
            "newest": newest,
            "locked": False,
            "locked_count": 0,
            "tier": tier,
        }
    }


@router.get("/{competitor_id}/gaps")
def get_gaps(competitor_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Gap analysis. Free tier sees the top 2 gap titles (detail locked) plus a
    locked count. Pro/Agency see every gap with full detail and metrics.
    """
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    tier = _user_tier(db, user_id)

    data = _latest_snapshot_data(db, competitor_id)
    ga = (data.get("gap_analysis") or {}) if data else {}
    gaps = ga.get("gaps") or []

    if not gaps:
        return {"data": {"gaps": [], "locked": tier == "free", "locked_count": 0, "tier": tier}}

    if tier == "free":
        teasers = [{
            "type": g.get("type"),
            "title": g.get("title"),
            "detail": None,  # locked
            "opportunity": g.get("opportunity"),
            "locked": True,
        } for g in gaps[:2]]
        return {
            "data": {
                "gaps": teasers,
                "locked": True,
                "locked_count": max(0, len(gaps) - 2),
                "tier": tier,
            }
        }

    return {"data": {"gaps": gaps, "locked": False, "locked_count": 0, "tier": tier}}


@router.get("/{competitor_id}/store-profile")
def get_store_profile(competitor_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Brand intelligence from extended scraping (collections, pages, blogs).
    Free tier: top-level signals only (collection count, key boolean flags).
    Pro/Agency: full collection names, all brand signals, content intelligence.
    """
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    tier = _user_tier(db, user_id)

    data = _latest_snapshot_data(db, competitor_id)
    profile = (data.get("store_profile") or {}) if data else {}

    col = profile.get("collection_intel") or {}
    brand = profile.get("brand_signals") or {}
    content = profile.get("content_intel") or {}

    # Free tier: surface key signals, lock the details
    if tier == "free":
        return {
            "data": {
                "collection_count": col.get("count", 0),
                "has_sale_collection": col.get("has_sale", False),
                "has_new_arrivals": col.get("has_new_arrivals", False),
                "has_best_sellers": col.get("has_best_sellers", False),
                "has_blog": content.get("blog_count", 0) > 0,
                "has_wholesale": brand.get("has_wholesale", False),
                "content_investment_score": content.get("content_investment_score"),
                "locked": True,
                "tier": tier,
            }
        }

    return {
        "data": {
            "collection_intel": col,
            "brand_signals": brand,
            "content_intel": content,
            "locked": False,
            "tier": tier,
        }
    }


def _user_tier(db, user_id: str) -> str:
    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    return (user.data or {}).get("tier", "free") if user else "free"


def _latest_snapshot_data(db, competitor_id: str) -> Optional[dict]:
    result = db.table("scan_snapshots")\
        .select("snapshot_data")\
        .eq("competitor_id", competitor_id)\
        .order("scanned_at", desc=True)\
        .limit(1)\
        .execute()
    if not result.data:
        return None
    return result.data[0].get("snapshot_data") or {}


def _assert_owner(db, competitor_id: str, user_id: str):
    result = db.table("competitors").select("user_id").eq("id", competitor_id).maybe_single().execute()
    if not result or not result.data or result.data["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Not found")
