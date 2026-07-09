from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.core.config import get_settings
from app.core.database import get_supabase
from app.core.obs import safe_read

router = APIRouter(prefix="/user", tags=["user"])


class BusinessProfileRequest(BaseModel):
    category: Optional[str] = None
    price_range: Optional[str] = None
    target_customer: Optional[str] = None
    primary_goal: Optional[str] = None
    sells: Optional[str] = None
    own_store_url: Optional[str] = None


@router.get("/business-profile")
@safe_read("GET /business-profile", {"data": None})
def get_business_profile(user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    res = db.table("business_profiles").select("*").eq("user_id", user_id).maybe_single().execute()
    return {"data": (res.data if res else None)}


@router.put("/business-profile")
def update_business_profile(body: BusinessProfileRequest, user_id: str = Depends(get_current_user_id)):
    from datetime import datetime, timezone
    db = get_supabase()
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        return {"status": "noop"}
    fields["user_id"] = user_id
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        db.table("business_profiles").upsert(fields, on_conflict="user_id").execute()
    except Exception as exc:
        # Table missing (pre-migration) — don't block onboarding
        import logging
        logging.getLogger(__name__).warning("business profile upsert failed for %s: %s", user_id, exc)
        return {"status": "unavailable"}
    return {"status": "ok"}


class UpdatePrefsRequest(BaseModel):
    email_price_changes: Optional[bool] = None
    email_new_products: Optional[bool] = None
    email_discount_changes: Optional[bool] = None
    email_weekly_digest: Optional[bool] = None
    digest_day: Optional[str] = None
    notification_level: Optional[str] = None   # critical_only | daily | weekly | quiet
    digest_hour: Optional[int] = None          # 0-23 UTC
    slack_webhook_url: Optional[str] = None
    slack_enabled: Optional[bool] = None
    webhook_url: Optional[str] = None
    webhook_enabled: Optional[bool] = None


@router.get("/subscription")
def get_subscription(user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    settings = get_settings()
    user = db.table("user_profiles").select("*").eq("id", user_id).maybe_single().execute()
    if not user or not user.data:
        raise HTTPException(404, "User not found")

    tier = user.data.get("tier", "free")
    limits = {
        "free": {"max_competitors": settings.free_max_competitors, "scan_hours": settings.free_scan_interval_hours, "history_days": 0, "ai_digest": False},
        "pro": {"max_competitors": settings.pro_max_competitors, "scan_hours": settings.pro_scan_interval_hours, "history_days": 90, "ai_digest": True},
        "agency": {"max_competitors": settings.agency_max_competitors, "scan_hours": settings.agency_scan_interval_hours, "history_days": 3650, "ai_digest": True},
        "developer": {"max_competitors": 50, "scan_hours": 12, "history_days": 3650, "ai_digest": True},
    }.get(tier, {"max_competitors": 1, "scan_hours": 168, "history_days": 0, "ai_digest": False})

    return {
        "data": {
            **user.data,
            "limits": limits,
        }
    }


@router.get("/notification-prefs")
def get_prefs(user_id: str = Depends(get_current_user_id)):
    defaults = {
        "user_id": user_id,
        "email_price_changes": True,
        "email_new_products": True,
        "email_discount_changes": False,
        "email_weekly_digest": True,
        "digest_day": "monday",
    }
    try:
        db = get_supabase()
        result = db.table("notification_prefs").select("*").eq("user_id", user_id).maybe_single().execute()
        return {"data": result.data or defaults}
    except Exception:
        return {"data": defaults}


@router.put("/notification-prefs")
def update_prefs(body: UpdatePrefsRequest, user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")

    # Upsert
    db.table("notification_prefs").upsert({"user_id": user_id, **updates}).execute()
    return {"status": "ok"}


@router.post("/test-webhook")
def test_webhook(body: dict, user_id: str = Depends(get_current_user_id)):
    """
    Send a sample payload to the user's configured Slack or generic webhook.
    body: { "type": "slack" | "generic" }
    """
    import requests as req

    db = get_supabase()
    prefs = db.table("notification_prefs").select("slack_webhook_url,webhook_url").eq("user_id", user_id).maybe_single().execute()
    prefs_data = prefs.data or {}
    settings = get_settings()

    webhook_type = body.get("type", "generic")
    sample_dashboard = f"{settings.public_base_url}/dashboard"

    if webhook_type == "slack":
        url = prefs_data.get("slack_webhook_url") or ""
        if not url:
            raise HTTPException(400, "No Slack webhook URL configured")
        payload = {
            "text": "✅ StoreScout test — your Slack integration is working!",
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": "✅ StoreScout Slack Integration", "emoji": True}},
                {"type": "section", "text": {"type": "mrkdwn", "text": "This is a test alert from *StoreScout*.\n\nWhen your competitors change prices or launch products, alerts will appear here automatically."}},
                {"type": "actions", "elements": [{"type": "button", "text": {"type": "plain_text", "text": "View Dashboard"}, "url": sample_dashboard, "style": "primary"}]},
            ],
        }
    else:
        url = prefs_data.get("webhook_url") or ""
        if not url:
            raise HTTPException(400, "No webhook URL configured")
        payload = {
            "event": "test",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "message": "StoreScout webhook integration is working correctly.",
            "dashboard_url": sample_dashboard,
        }

    try:
        resp = req.post(url, json=payload, timeout=10, headers={"User-Agent": "StoreScout/1.0"})
        if resp.ok:
            return {"status": "ok", "http_status": resp.status_code}
        return {"status": "error", "http_status": resp.status_code, "detail": resp.text[:200]}
    except Exception as exc:
        raise HTTPException(502, f"Webhook request failed: {exc}")


@router.post("/provision")
def provision_user(user_id: str = Depends(get_current_user_id)):
    """Called by the frontend after Supabase auth signup to create user_profiles row."""
    db = get_supabase()
    settings = get_settings()

    # Get email from Supabase Auth admin API
    try:
        auth_user = db.auth.admin.get_user_by_id(user_id)
        email = auth_user.user.email if auth_user.user else ""
    except Exception:
        email = ""

    existing = db.table("user_profiles").select("id").eq("id", user_id).maybe_single().execute()
    if existing.data:
        return {"status": "exists"}

    db.table("user_profiles").insert({
        "id": user_id,
        "email": email,
        "tier": "free",
        "max_competitors": settings.free_max_competitors,
        "scan_interval_hours": settings.free_scan_interval_hours,
        "subscription_status": "inactive",
    }).execute()

    try:
        db.table("notification_prefs").insert({
            "user_id": user_id,
            "email_price_changes": True,
            "email_new_products": True,
            "email_discount_changes": False,
            "email_weekly_digest": True,
            "digest_day": "monday",
        }).execute()
    except Exception:
        pass  # table may not have been migrated yet; non-fatal

    return {"status": "created"}
