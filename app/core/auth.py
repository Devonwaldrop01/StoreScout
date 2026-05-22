from __future__ import annotations
from typing import Optional
import requests as _requests
from functools import lru_cache
from jose import jwt, JWTError, ExpiredSignatureError
from jose import jwk as _jwk
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


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


def maybe_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[str]:
    if not credentials:
        return None
    try:
        return get_current_user_id(credentials)
    except HTTPException:
        return None
