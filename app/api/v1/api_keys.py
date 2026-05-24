from __future__ import annotations
import hashlib
import secrets
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.core.database import get_supabase

router = APIRouter(prefix="/api-keys", tags=["api-keys"])
logger = logging.getLogger(__name__)
MAX_KEYS = 5


class CreateKeyRequest(BaseModel):
    name: str = "API key"


def _assert_paid(db, user_id: str) -> None:
    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    tier = (user.data or {}).get("tier", "free")
    if tier not in ("pro", "agency", "developer"):
        raise HTTPException(403, "API keys require a Pro or higher plan")


@router.get("")
def list_keys(user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    _assert_paid(db, user_id)
    result = db.table("api_keys")\
        .select("id, name, key_prefix, last_used_at, created_at")\
        .eq("user_id", user_id)\
        .is_("revoked_at", "null")\
        .order("created_at")\
        .execute()
    return {"data": result.data or []}


@router.post("")
def create_key(body: CreateKeyRequest, user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    _assert_paid(db, user_id)

    count = db.table("api_keys")\
        .select("id", count="exact")\
        .eq("user_id", user_id)\
        .is_("revoked_at", "null")\
        .execute()
    if (count.count or 0) >= MAX_KEYS:
        raise HTTPException(400, f"Maximum of {MAX_KEYS} active API keys allowed. Revoke one to create a new one.")

    name = (body.name or "API key").strip()[:60]
    raw = "sk_live_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    key_prefix = raw[:16]  # "sk_live_" + first 8 random chars

    db.table("api_keys").insert({
        "user_id": user_id,
        "name": name,
        "key_hash": key_hash,
        "key_prefix": key_prefix,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    # plaintext key returned once — never stored
    return {"data": {"key": raw, "key_prefix": key_prefix, "name": name}}


@router.delete("/{key_id}", status_code=204)
def revoke_key(key_id: str, user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    row = db.table("api_keys")\
        .select("id")\
        .eq("id", key_id)\
        .eq("user_id", user_id)\
        .maybe_single()\
        .execute()
    if not row or not row.data:
        raise HTTPException(404, "API key not found")
    db.table("api_keys").update({
        "revoked_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", key_id).execute()
