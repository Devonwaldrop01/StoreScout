import re
import base64
import logging

import httpx
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response

from app.core.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

_DOMAIN_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)+$")

_CACHE_HEADERS = "public, max-age=604800"  # 7 days


def _redis_client():
    try:
        import redis as redis_lib
        return redis_lib.from_url(get_settings().redis_url, socket_connect_timeout=1)
    except Exception:
        return None


async def _fetch_favicon(domain: str) -> tuple[bytes, str] | None:
    sources = [
        f"https://icons.duckduckgo.com/ip3/{domain}.ico",
        f"https://www.google.com/s2/favicons?domain={domain}&sz=64",
    ]
    async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
        for url in sources:
            try:
                resp = await client.get(url)
                if resp.status_code == 200 and resp.content:
                    ct = resp.headers.get("content-type", "image/x-icon").split(";")[0].strip()
                    return resp.content, ct
            except Exception as exc:
                logger.debug("favicon fetch failed for %s from %s: %s", domain, url, exc)
    return None


@router.get("/favicon")
async def get_favicon(domain: str = Query(...)):
    if not _DOMAIN_RE.match(domain) or "/" in domain or " " in domain:
        raise HTTPException(status_code=400, detail="Invalid domain")

    cache_key = f"favicon:{domain}"

    # Try Redis cache first
    r = _redis_client()
    if r:
        try:
            cached = r.get(cache_key)
            if cached:
                parts = cached.decode().split("|", 1)
                ct = parts[0] if len(parts) == 2 else "image/x-icon"
                data = base64.b64decode(parts[1] if len(parts) == 2 else parts[0])
                return Response(content=data, media_type=ct, headers={"Cache-Control": _CACHE_HEADERS})
        except Exception as exc:
            logger.debug("favicon redis read error: %s", exc)

    result = await _fetch_favicon(domain)
    if result is None:
        raise HTTPException(status_code=404, detail="Favicon not found")

    data, ct = result

    # Cache in Redis (7-day TTL)
    if r:
        try:
            payload = f"{ct}|{base64.b64encode(data).decode()}"
            r.setex(cache_key, 7 * 24 * 60 * 60, payload)
        except Exception as exc:
            logger.debug("favicon redis write error: %s", exc)

    return Response(content=data, media_type=ct, headers={"Cache-Control": _CACHE_HEADERS})
