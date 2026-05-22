from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.core.config import get_settings
from app.core.database import get_supabase

router = APIRouter(prefix="/user", tags=["user"])


class UpdatePrefsRequest(BaseModel):
    email_price_changes: Optional[bool] = None
    email_new_products: Optional[bool] = None
    email_discount_changes: Optional[bool] = None
    email_weekly_digest: Optional[bool] = None
    digest_day: Optional[str] = None


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
    }.get(tier, {"max_competitors": 1, "scan_hours": 168, "history_days": 0, "ai_digest": False})

    return {
        "data": {
            **user.data,
            "limits": limits,
        }
    }


@router.get("/notification-prefs")
def get_prefs(user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    result = db.table("notification_prefs").select("*").eq("user_id", user_id).maybe_single().execute()
    defaults = {
        "user_id": user_id,
        "email_price_changes": True,
        "email_new_products": True,
        "email_discount_changes": False,
        "email_weekly_digest": True,
        "digest_day": "monday",
    }
    return {"data": result.data or defaults}


@router.put("/notification-prefs")
def update_prefs(body: UpdatePrefsRequest, user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")

    # Upsert
    db.table("notification_prefs").upsert({"user_id": user_id, **updates}).execute()
    return {"status": "ok"}


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

    db.table("notification_prefs").insert({
        "user_id": user_id,
        "email_price_changes": True,
        "email_new_products": True,
        "email_discount_changes": False,
        "email_weekly_digest": True,
        "digest_day": "monday",
    }).execute()

    return {"status": "created"}
