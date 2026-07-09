from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from app.core.auth import get_current_user_id
from app.core.config import get_settings
from app.core.database import get_supabase
from app.core.obs import safe_read

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/my-store", tags=["my-store"])


class SetMyStoreRequest(BaseModel):
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


@router.get("")
@safe_read("GET /my-store", {"data": None})
def get_my_store(user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    result = db.table("competitors")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("is_my_store", True)\
        .maybe_single()\
        .execute()
    return {"data": (result.data if result else None)}


@router.post("", status_code=status.HTTP_201_CREATED)
def set_my_store(body: SetMyStoreRequest, user_id: str = Depends(get_current_user_id)):
    """Create or replace the user's own store. Reuses the competitor scan pipeline."""
    db = get_supabase()
    settings = get_settings()

    # Ensure profile exists (mirrors add_competitor auto-provision)
    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    if not user or not user.data:
        try:
            db.table("user_profiles").insert({
                "id": user_id, "email": "", "tier": "free",
                "max_competitors": settings.free_max_competitors,
                "scan_interval_hours": settings.free_scan_interval_hours,
                "subscription_status": "inactive",
            }).execute()
        except Exception:
            pass

    hostname = urlparse(body.store_url).netloc
    now = datetime.now(timezone.utc)

    existing = db.table("competitors")\
        .select("id")\
        .eq("user_id", user_id)\
        .eq("is_my_store", True)\
        .maybe_single()\
        .execute()

    if existing and existing.data:
        store_id = existing.data["id"]
        db.table("competitors").update({
            "store_url": body.store_url,
            "hostname": hostname,
            "display_name": body.display_name or hostname,
            "scan_status": "pending",
            "next_scan_at": now.isoformat(),
            "error_message": None,
        }).eq("id", store_id).execute()
    else:
        row = db.table("competitors").insert({
            "user_id": user_id,
            "store_url": body.store_url,
            "hostname": hostname,
            "display_name": body.display_name or hostname,
            "is_my_store": True,
            "scan_status": "pending",
            "next_scan_at": now.isoformat(),
        }).execute()
        store_id = row.data[0]["id"]

    try:
        from app.tasks.scan import scan_competitor
        scan_competitor.apply_async(args=[store_id], queue="priority")
    except Exception as exc:
        logger.warning("Could not enqueue scan for my-store %s: %s", store_id, exc)

    result = db.table("competitors").select("*").eq("id", store_id).single().execute()
    return {"data": result.data}


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_store(user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    db.table("competitors").delete().eq("user_id", user_id).eq("is_my_store", True).execute()
