from __future__ import annotations
import logging
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from app.core.auth import get_current_user_id, get_effective_user_id
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
        netloc = parsed.netloc.rstrip("/")
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return f"https://{netloc}"


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
def list_competitors(user_id: str = Depends(get_effective_user_id)):
    db = get_supabase()
    result = db.table("competitors").select("*").eq("user_id", user_id).eq("is_my_store", False).order("created_at", desc=True).execute()
    return {"data": result.data or []}


@router.post("", status_code=status.HTTP_201_CREATED)
def add_competitor(body: AddCompetitorRequest, user_id: str = Depends(get_effective_user_id)):
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

    existing = db.table("competitors").select("id").eq("user_id", user_id).eq("is_active", True).eq("is_my_store", False).execute()
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

    # Validate the URL is actually a Shopify store before creating the row.
    # This surfaces the failure immediately instead of after a 60s scan attempt.
    try:
        from app.services.fetch import check_store
        probe = check_store(body.store_url)
        if not probe.get("ok"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "not_shopify",
                    "message": "This doesn't appear to be a Shopify store. Check the URL and try again.",
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Probe network error — allow the add and let the scan fail gracefully
        logger.warning("check_store probe failed for %s: %s", body.store_url, exc)

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


# Curated fallback: well-known Shopify stores shown when there's no tag/vendor data to
# match against (new users, fresh competitors with no scan yet).
_CURATED_STORES = [
    {"hostname": "gymshark.com",       "category": "Apparel",  "tag": "Fitness apparel"},
    {"hostname": "allbirds.com",       "category": "Apparel",  "tag": "Sustainable footwear"},
    {"hostname": "fashionnova.com",    "category": "Apparel",  "tag": "Fast fashion"},
    {"hostname": "chubbiesshorts.com", "category": "Apparel",  "tag": "Men's shorts"},
    {"hostname": "vuori.com",          "category": "Apparel",  "tag": "Performance apparel"},
    {"hostname": "kyliecosmetics.com", "category": "Beauty",   "tag": "Makeup"},
    {"hostname": "colourpop.com",      "category": "Beauty",   "tag": "Affordable cosmetics"},
    {"hostname": "fentybeauty.com",    "category": "Beauty",   "tag": "Inclusive beauty"},
    {"hostname": "iliabeauty.com",     "category": "Beauty",   "tag": "Clean beauty"},
    {"hostname": "brooklinen.com",     "category": "Home",     "tag": "Luxury bedding"},
    {"hostname": "parachutehome.com",  "category": "Home",     "tag": "Home essentials"},
    {"hostname": "ruggable.com",       "category": "Home",     "tag": "Washable rugs"},
    {"hostname": "pourri.com",         "category": "Home",     "tag": "Lifestyle & wellness"},
    {"hostname": "bombas.com",         "category": "Apparel",  "tag": "Socks & basics"},
    {"hostname": "mvmtwatches.com",    "category": "Accessories","tag": "Minimalist watches"},
    {"hostname": "puravidabracelets.com","category": "Accessories","tag": "Bracelets & jewelry"},
    {"hostname": "tentree.com",        "category": "Apparel",  "tag": "Sustainable fashion"},
    {"hostname": "skims.com",          "category": "Apparel",  "tag": "Shapewear"},
]


# IMPORTANT: /discover must be registered before /{competitor_id} so FastAPI doesn't
# try to parse the literal string "discover" as a UUID competitor_id.
@router.get("/discover")
def discover_similar(user_id: str = Depends(get_effective_user_id)):
    """
    Suggest similar Shopify stores to track based on tag/vendor overlap
    with the user's currently tracked competitors. Falls back to curated
    popular stores for new users or when no tag data is available.
    """
    db = get_supabase()

    # User's current competitors
    user_comps = db.table("competitors")\
        .select("id, hostname")\
        .eq("user_id", user_id)\
        .eq("is_active", True)\
        .eq("is_my_store", False)\
        .execute()

    tracked_hostnames = {c["hostname"] for c in (user_comps.data or [])}
    tracked_ids = [c["id"] for c in (user_comps.data or [])]

    def _curated_fallback() -> list:
        return [
            {
                "hostname": s["hostname"],
                "competitor_id": s["hostname"],  # no DB id — frontend uses hostname for dedup
                "score": 0,
                "match_reasons": [s["tag"]],
                "product_count": None,
                "median_price": None,
                "market_position": None,
                "is_curated": True,
                "category": s["category"],
            }
            for s in _CURATED_STORES
            if s["hostname"] not in tracked_hostnames
        ][:6]

    # No tracked competitors — return curated list
    if not tracked_ids:
        return {"data": {"suggestions": _curated_fallback()}}

    # Aggregate top tags + vendors across all user's competitors
    agg_tags: Counter = Counter()
    agg_vendors: Counter = Counter()
    for comp_id in tracked_ids:
        data = _latest_snapshot_data(db, comp_id)
        if not data:
            continue
        for t in (data.get("tag_analysis") or {}).get("top_tags", [])[:10]:
            agg_tags[str(t.get("tag", ""))] += t.get("count", 1)
        for v in (data.get("vendor_analysis") or {}).get("top_vendors", [])[:5]:
            agg_vendors[str(v.get("vendor", "")).lower()] += v.get("count", 1)

    top_tags = {t for t, _ in agg_tags.most_common(15)}
    top_vendors = {v for v, _ in agg_vendors.most_common(8)}

    if not top_tags and not top_vendors:
        return {"data": {"suggestions": _curated_fallback()}}

    # Pull recent snapshots from other competitors (across all users)
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    recent = db.table("scan_snapshots")\
        .select("competitor_id, snapshot_data, scanned_at")\
        .gte("scanned_at", thirty_days_ago)\
        .order("scanned_at", desc=True)\
        .limit(400)\
        .execute()

    # Deduplicate: keep only the latest snapshot per competitor_id
    seen: dict[str, dict] = {}
    for snap in (recent.data or []):
        cid = snap["competitor_id"]
        if cid in tracked_ids or cid in seen:
            continue
        snap_data = snap.get("snapshot_data") or {}
        hostname = snap_data.get("hostname") or ""
        if hostname and hostname not in tracked_hostnames:
            seen[cid] = snap_data

    # Score each candidate by tag + vendor overlap
    scored = []
    for cid, data in seen.items():
        hostname = data.get("hostname") or ""
        if not hostname:
            continue

        cand_tags = {str(t.get("tag", "")) for t in (data.get("tag_analysis") or {}).get("top_tags", [])[:10]}
        cand_vendors = {str(v.get("vendor", "")).lower() for v in (data.get("vendor_analysis") or {}).get("top_vendors", [])[:5]}

        tag_matches = top_tags & cand_tags
        vendor_matches = top_vendors & cand_vendors
        score = len(tag_matches) * 2 + len(vendor_matches) * 3
        if score == 0:
            continue

        # Build readable match reasons: vendor matches first (more specific)
        reasons = [f"vendor: {v}" for v in sorted(vendor_matches)[:2]]
        reasons += [t for t in sorted(tag_matches)[:3] if t not in (r.split(": ")[-1] for r in reasons)]

        pricing = data.get("pricing") or {}
        pos = (data.get("positioning") or {}).get("market_position") or {}
        market_pos = pos.get("label") if isinstance(pos, dict) else None

        scored.append({
            "hostname": hostname,
            "competitor_id": cid,
            "score": score,
            "match_reasons": reasons[:4],
            "product_count": (data.get("catalog") or {}).get("total_products"),
            "median_price": pricing.get("median"),
            "market_position": market_pos,
            "is_curated": False,
            "category": None,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:6]
    # If no tag-matched candidates found in the DB, fall back to curated list
    if not top:
        return {"data": {"suggestions": _curated_fallback()}}
    return {"data": {"suggestions": top}}


@router.get("/{competitor_id}")
def get_competitor(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    """Fetch a single competitor record (no snapshot data)."""
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    result = db.table("competitors")\
        .select("*")\
        .eq("id", competitor_id)\
        .maybe_single()\
        .execute()
    if not result or not result.data:
        raise HTTPException(status_code=404, detail="Not found")
    return {"data": result.data}


@router.patch("/{competitor_id}")
def update_competitor(
    competitor_id: str,
    body: UpdateCompetitorRequest,
    user_id: str = Depends(get_effective_user_id),
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
def manual_rescan(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)

    competitor = db.table("competitors").select("scan_status").eq("id", competitor_id).single().execute()
    if (competitor.data or {}).get("scan_status") == "scanning":
        raise HTTPException(status_code=409, detail="Scan already in progress")

    # Redis-based cooldown — 60s between rescans per competitor (non-fatal if Redis unavailable)
    try:
        import redis as redis_lib
        r = redis_lib.from_url(get_settings().redis_url, socket_connect_timeout=1)
        rl_key = f"ratelimit:rescan:{competitor_id}"
        if r.exists(rl_key):
            raise HTTPException(status_code=429, detail="Rescan cooldown active — please wait 60 seconds")
        r.set(rl_key, "1", ex=60)
    except HTTPException:
        raise
    except Exception:
        pass  # Redis unavailable — allow the rescan

    from app.tasks.scan import manual_rescan as _rescan
    _rescan.apply_async(args=[competitor_id], queue="priority")
    return {"status": "queued"}


@router.get("/{competitor_id}/snapshots/latest")
def get_latest_snapshot(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
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
    user_id: str = Depends(get_effective_user_id),
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
    user_id: str = Depends(get_effective_user_id),
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
def get_ai_summary(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
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
        from app.tasks.ai_summaries import generate_weekly_summary
        generate_weekly_summary.delay(competitor_id, "weekly")
        return {"data": None, "status": "generating"}
    return {"data": result.data[0], "status": "ok"}


@router.post("/{competitor_id}/ai-summary/regenerate")
def regenerate_ai_summary(competitor_id: str, user_id: str = Depends(get_current_user_id)):
    """Trigger a fresh AI summary generation on demand (Pro/Agency only)."""
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)

    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    tier = (user.data or {}).get("tier", "free") if user else "free"
    if tier == "free":
        raise HTTPException(status_code=402, detail={"code": "ai_summary_locked"})

    from app.tasks.ai_summaries import generate_weekly_summary
    generate_weekly_summary.delay(competitor_id, "weekly")
    return {"status": "triggered"}


@router.get("/{competitor_id}/winning-products")
def get_winning_products(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
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
def get_gaps(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
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
def get_store_profile(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
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


@router.get("/{competitor_id}/comparison")
def get_comparison(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    """
    Head-to-head: the user's own store vs this competitor. Requires the user to
    have set their store. Free tier sees the diagnosis (verdicts + insights);
    action items and the match strategy are Pro.
    """
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    tier = _user_tier(db, user_id)

    # Find the user's own store
    my = db.table("competitors")\
        .select("id, hostname")\
        .eq("user_id", user_id)\
        .eq("is_my_store", True)\
        .maybe_single()\
        .execute()
    if not my or not my.data:
        return {"data": {"has_store": False}}

    my_data = _latest_snapshot_data(db, my.data["id"])
    their_data = _latest_snapshot_data(db, competitor_id)
    if not my_data:
        return {"data": {"has_store": True, "ready": False, "reason": "my_store_scanning"}}
    if not their_data:
        return {"data": {"has_store": True, "ready": False, "reason": "competitor_scanning"}}

    their = db.table("competitors").select("hostname").eq("id", competitor_id).single().execute()
    their_hostname = (their.data or {}).get("hostname", "them")

    from app.services.insights import compare_stores
    result = compare_stores(my_data, their_data, my.data["hostname"], their_hostname)
    result["ready"] = True

    # Tier gate: free sees diagnosis, Pro gets prescription
    if tier == "free":
        for d in result.get("dimensions", []):
            d["action"] = None
            d["action_locked"] = True
        ms = result.get("match_strategy") or {}
        result["match_strategy"] = {
            "is_newcomer": ms.get("is_newcomer", False),
            "narrative": None,
            "match_these": [],
            "own_these": [],
            "locked": True,
        }
        result["locked"] = True
    else:
        result["locked"] = False

    result["tier"] = tier
    return {"data": result}


@router.get("/{competitor_id}/quick-wins")
def get_quick_wins(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    """
    Rule-based action cards from the latest snapshot.
    Free tier: 1 card visible + locked_count.  Pro/Agency: all cards.
    """
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    tier = _user_tier(db, user_id)

    data = _latest_snapshot_data(db, competitor_id)
    if not data:
        return {"data": {"wins": [], "locked": False, "locked_count": 0, "tier": tier}}

    from app.services.insights import compute_quick_wins
    wins = compute_quick_wins(data)

    if not wins:
        return {"data": {"wins": [], "locked": False, "locked_count": 0, "tier": tier}}

    if tier == "free":
        return {"data": {
            "wins": wins[:1],
            "locked": True,
            "locked_count": max(0, len(wins) - 1),
            "tier": tier,
        }}

    return {"data": {"wins": wins, "locked": False, "locked_count": 0, "tier": tier}}


@router.get("/{competitor_id}/price-history")
def get_price_history(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    """
    Time-series of median_price and promo_rate across scans.
    Free: last 2 data points + locked flag.  Pro: 90 days.  Agency: unlimited.
    """
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    tier = _user_tier(db, user_id)
    now = datetime.now(timezone.utc)

    if tier == "free":
        result = db.table("scan_snapshots")\
            .select("scanned_at, median_price, promo_rate, product_count")\
            .eq("competitor_id", competitor_id)\
            .order("scanned_at", desc=True)\
            .limit(2)\
            .execute()
        points = list(reversed(result.data or []))
        total = db.table("scan_snapshots").select("id", count="exact")\
            .eq("competitor_id", competitor_id).execute()
        total_count = total.count or len(points)
        return {"data": {
            "points": points,
            "locked": True,
            "locked_count": max(0, total_count - 2),
            "tier": tier,
        }}

    query = db.table("scan_snapshots")\
        .select("scanned_at, median_price, promo_rate, product_count")\
        .eq("competitor_id", competitor_id)\
        .order("scanned_at", desc=False)\
        .limit(365)

    if tier == "pro":
        cutoff = (now - timedelta(days=90)).isoformat()
        query = query.gte("scanned_at", cutoff)

    result = query.execute()
    return {"data": {
        "points": result.data or [],
        "locked": False,
        "locked_count": 0,
        "tier": tier,
    }}


@router.get("/{competitor_id}/brief")
def get_brief(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    """Latest Intelligence Brief for this competitor (available to all tiers)."""
    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)

    result = db.table("ai_summaries")\
        .select("*")\
        .eq("competitor_id", competitor_id)\
        .eq("summary_type", "brief")\
        .order("generated_at", desc=True)\
        .limit(1)\
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="No brief available yet")
    return {"data": result.data[0]}


@router.get("/{competitor_id}/export/products.csv")
def export_products_csv(competitor_id: str, user_id: str = Depends(get_effective_user_id)):
    """Download a CSV of the competitor's latest product catalog. Pro/Agency only."""
    import csv, io
    from fastapi.responses import Response

    db = get_supabase()
    _assert_owner(db, competitor_id, user_id)
    tier = _user_tier(db, user_id)
    if tier == "free":
        raise HTTPException(status_code=403, detail={"code": "upgrade_required", "message": "CSV export requires Pro or Agency plan"})

    result = db.table("scan_snapshots")\
        .select("snapshot_data, scanned_at")\
        .eq("competitor_id", competitor_id)\
        .order("scanned_at", desc=True)\
        .limit(1)\
        .execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="No snapshot found")

    data = result.data[0].get("snapshot_data") or {}
    hostname = data.get("hostname") or competitor_id
    product_index = data.get("_product_index") or {}

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["title", "handle", "url", "price", "compare_at", "discount_pct", "available"],
        extrasaction="ignore",
    )
    writer.writeheader()
    for handle, p in product_index.items():
        price = p.get("price_min") or 0
        ca = p.get("compare_at_min")
        disc = round((ca - price) / ca * 100, 1) if ca and ca > price else ""
        writer.writerow({
            "title": p.get("title") or "",
            "handle": handle,
            "url": p.get("product_url") or "",
            "price": price,
            "compare_at": ca or "",
            "discount_pct": disc,
            "available": p.get("available", True),
        })

    safe_hostname = hostname.replace(".", "_").replace("/", "_")
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe_hostname}_products.csv"'},
    )


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
