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

# Favicon CDNs (DuckDuckGo, Google) reject requests without a browser UA → 403.
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}


def _redis_client():
    try:
        import redis as redis_lib
        return redis_lib.from_url(get_settings().redis_url, socket_connect_timeout=1)
    except Exception:
        return None


def _is_valid_image(data: bytes) -> bool:
    """Validate by magic number — guards against corrupt/placeholder/text bodies
    (and stale corrupt cache entries) being served with an image content-type."""
    if not data or len(data) < 70:
        return False
    if data[:8] == b"\x89PNG\r\n\x1a\n":          # PNG
        return True
    if data[:4] == b"\x00\x00\x01\x00":           # ICO
        return True
    if data[:3] == b"GIF":                         # GIF
        return True
    if data[:2] == b"\xff\xd8":                    # JPEG
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":  # WEBP
        return True
    head = data[:256].lstrip().lower()
    if head.startswith(b"<svg") or head.startswith(b"<?xml"):  # SVG
        return True
    return False


async def _fetch_favicon(domain: str) -> tuple[bytes, str] | None:
    # Order: third-party CDNs first (sized, cached), then the store's own
    # favicon as a fallback — a request to the store's own server from our
    # backend is the least likely to be blocked or rejected.
    sources = [
        f"https://icons.duckduckgo.com/ip3/{domain}.ico",
        f"https://www.google.com/s2/favicons?domain={domain}&sz=64",
        f"https://{domain}/favicon.ico",
        f"https://www.{domain}/favicon.ico",
    ]
    async with httpx.AsyncClient(timeout=5.0, follow_redirects=True, headers=_BROWSER_HEADERS) as client:
        for url in sources:
            try:
                resp = await client.get(url)
                ct = resp.headers.get("content-type", "").split(";")[0].strip().lower()
                # Only accept real image payloads — some CDNs return a 200 text
                # body or a 1x1 placeholder. Require an image content-type and
                # a plausible size.
                if resp.status_code == 200 and _is_valid_image(resp.content):
                    return resp.content, ct if ct.startswith("image/") else "image/x-icon"
                logger.info("favicon: %s returned %s (%s, %d bytes) — not a valid image, skipping", url, resp.status_code, ct or "?", len(resp.content))
            except Exception as exc:
                logger.info("favicon: fetch failed for %s: %s", url, exc)
    return None


@router.get("/favicon")
async def get_favicon(domain: str = Query(...)):
    if not _DOMAIN_RE.match(domain) or "/" in domain or " " in domain:
        raise HTTPException(status_code=400, detail="Invalid domain")

    cache_key = f"favicon:{domain}"

    # Try Redis cache first — but only serve it if it's a valid image, so a
    # corrupt entry from an earlier deploy self-heals instead of persisting.
    r = _redis_client()
    if r:
        try:
            cached = r.get(cache_key)
            if cached:
                parts = cached.decode().split("|", 1)
                ct = parts[0] if len(parts) == 2 else "image/x-icon"
                data = base64.b64decode(parts[1] if len(parts) == 2 else parts[0])
                if _is_valid_image(data):
                    return Response(content=data, media_type=ct, headers={"Cache-Control": _CACHE_HEADERS})
                logger.info("favicon: cached entry for %s is not a valid image — refetching", domain)
                r.delete(cache_key)
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
