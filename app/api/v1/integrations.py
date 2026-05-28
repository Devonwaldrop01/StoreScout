from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.core.database import get_supabase

router = APIRouter(prefix="/integrations", tags=["integrations"])
logger = logging.getLogger(__name__)

_KLAVIYO_BASE = "https://a.klaviyo.com/api"
_KLAVIYO_REVISION = "2024-02-15"


def _klaviyo_headers(api_key: str) -> dict:
    return {"Authorization": f"Klaviyo-API-Key {api_key}", "revision": _KLAVIYO_REVISION}


def _mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return "****"
    return key[:6] + "****" + key[-4:]


def _get_integration_row(user_id: str) -> dict:
    db = get_supabase()
    result = db.table("user_integrations").select("*").eq("user_id", user_id).maybe_single().execute()
    return result.data or {}


# ── GET /integrations ──────────────────────────────────────────────────────────

@router.get("")
def get_integrations(user_id: str = Depends(get_current_user_id)):
    """Return integration status for the current user (keys masked)."""
    row = _get_integration_row(user_id)
    klaviyo_key = row.get("klaviyo_api_key") or ""
    return {
        "data": {
            "klaviyo": {
                "connected": bool(klaviyo_key),
                "key_preview": _mask_key(klaviyo_key) if klaviyo_key else None,
            }
        }
    }


# ── Klaviyo ────────────────────────────────────────────────────────────────────

class KlaviyoKeyRequest(BaseModel):
    api_key: str


@router.put("/klaviyo")
def save_klaviyo_key(body: KlaviyoKeyRequest, user_id: str = Depends(get_current_user_id)):
    """Store a Klaviyo private API key for this user."""
    key = body.api_key.strip()
    if not key:
        raise HTTPException(400, "api_key is required")

    db = get_supabase()
    db.table("user_integrations").upsert({
        "user_id": user_id,
        "klaviyo_api_key": key,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id").execute()

    return {"data": {"connected": True, "key_preview": _mask_key(key)}}


@router.delete("/klaviyo", status_code=204)
def remove_klaviyo_key(user_id: str = Depends(get_current_user_id)):
    """Remove Klaviyo key for this user."""
    db = get_supabase()
    db.table("user_integrations").update({
        "klaviyo_api_key": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("user_id", user_id).execute()


@router.post("/klaviyo/test")
def test_klaviyo(user_id: str = Depends(get_current_user_id)):
    """Test the stored Klaviyo key — returns list count and total profiles."""
    row = _get_integration_row(user_id)
    api_key = row.get("klaviyo_api_key") or ""
    if not api_key:
        raise HTTPException(400, "No Klaviyo key saved")

    try:
        resp = httpx.get(
            f"{_KLAVIYO_BASE}/lists/",
            headers=_klaviyo_headers(api_key),
            params={"page[size]": 100},
            timeout=10.0,
        )
        resp.raise_for_status()
        lists_data = resp.json().get("data", [])
        list_count = len(lists_data)
        total_profiles = sum(
            (item.get("attributes", {}).get("profile_count") or 0)
            for item in lists_data
        )
        return {
            "status": "ok",
            "list_count": list_count,
            "total_profiles": total_profiles,
            "lists": [
                {
                    "name": item.get("attributes", {}).get("name", ""),
                    "profile_count": item.get("attributes", {}).get("profile_count") or 0,
                }
                for item in lists_data[:5]
            ],
        }
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            raise HTTPException(401, "Invalid Klaviyo API key")
        raise HTTPException(502, f"Klaviyo API error: {exc.response.status_code}")
    except Exception as exc:
        logger.error("Klaviyo test failed for user %s: %s", user_id, exc)
        raise HTTPException(502, "Could not reach Klaviyo API")


# ── Helper used by playbook_ai.py ─────────────────────────────────────────────

def get_klaviyo_context(user_id: str) -> Optional[str]:
    """Fetch Klaviyo list data and return a one-line context string for the AI prompt.
    Returns None if no key or API call fails."""
    row = _get_integration_row(user_id)
    api_key = row.get("klaviyo_api_key") or ""
    if not api_key:
        return None

    try:
        resp = httpx.get(
            f"{_KLAVIYO_BASE}/lists/",
            headers=_klaviyo_headers(api_key),
            params={"page[size]": 100},
            timeout=8.0,
        )
        resp.raise_for_status()
        lists_data = resp.json().get("data", [])
        if not lists_data:
            return None

        total_profiles = sum(
            (item.get("attributes", {}).get("profile_count") or 0)
            for item in lists_data
        )
        list_count = len(lists_data)
        largest = max(lists_data, key=lambda x: x.get("attributes", {}).get("profile_count") or 0)
        largest_name = largest.get("attributes", {}).get("name", "")
        largest_count = largest.get("attributes", {}).get("profile_count") or 0

        parts = [f"Email list: {total_profiles:,} subscribers across {list_count} list{'s' if list_count != 1 else ''}"]
        if largest_name and list_count > 1:
            parts.append(f"largest list: \"{largest_name}\" ({largest_count:,} subscribers)")
        return " · ".join(parts)
    except Exception as exc:
        logger.debug("Klaviyo context fetch failed for user %s: %s", user_id, exc)
        return None
