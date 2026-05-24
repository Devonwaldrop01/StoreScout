from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from typing import Optional
import requests as _requests
from functools import lru_cache
from jose import jwt, JWTError, ExpiredSignatureError
from jose import jwk as _jwk
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


def _auth_via_api_key(raw_key: str) -> str:
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    from app.core.database import get_supabase
    db = get_supabase()
    row = db.table("api_keys").select("id, user_id")\
        .eq("key_hash", key_hash)\
        .is_("revoked_at", "null")\
        .maybe_single()\
        .execute()
    if not row or not row.data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked API key")
    try:
        from datetime import datetime, timezone
        db.table("api_keys").update({"last_used_at": datetime.now(timezone.utc).isoformat()})\
            .eq("id", row.data["id"]).execute()
    except Exception:
        pass
    return row.data["user_id"]


@lru_cache(maxsize=1)
def _get_jwks(supabase_url: str) -> dict:
    """Fetch and cache Supabase JWKS (refreshed on process restart)."""
    try:
        resp = _requests.get(
            f"{supabase_url}/auth/v1/.well-known/jwks.json", timeout=10
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {"keys": []}


def _decode_token(token: str, settings) -> dict:
    """Verify JWT — tries JWKS (RS256/EdDSA) first, falls back to HS256."""
    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "HS256")

    if alg != "HS256":
        # New Supabase JWT Signing Keys (RS256 / EdDSA)
        jwks = _get_jwks(settings.supabase_url)
        kid = header.get("kid")
        for key_data in jwks.get("keys", []):
            if kid is None or key_data.get("kid") == kid:
                key = _jwk.construct(key_data)
                return jwt.decode(
                    token, key, algorithms=[alg],
                    options={"verify_aud": False},
                )
        raise JWTError("No matching JWKS key found")

    # Legacy HS256 with Supabase JWT secret
    return jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=["HS256"],
        options={"verify_aud": False},
    )


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> str:
    settings = get_settings()
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    if credentials.credentials.startswith("sk_live_"):
        return _auth_via_api_key(credentials.credentials)
    try:
        payload = _decode_token(credentials.credentials, settings)
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return user_id
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_effective_user_id(user_id: str = Depends(get_current_user_id)) -> str:
    """For active team members: return the owner's user_id so they share competitor access."""
    from app.core.database import get_supabase
    db = get_supabase()
    try:
        member = db.table("team_members")\
            .select("owner_id")\
            .eq("member_id", user_id)\
            .eq("status", "active")\
            .maybe_single()\
            .execute()
        if member and member.data:
            return member.data["owner_id"]
    except Exception:
        pass
    return user_id


def maybe_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[str]:
    if not credentials:
        return None
    try:
        return get_current_user_id(credentials)
    except HTTPException:
        return None
