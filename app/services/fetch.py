from __future__ import annotations
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

# Single static Chrome User-Agent. Must stay consistent with httpx's TLS
# fingerprint — randomizing across Safari/Firefox UAs creates a UA/TLS
# mismatch that WAFs flag as a bot and 403.
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def _headers() -> dict:
    return dict(DEFAULT_HEADERS)


def _enforce_domain_rate_limit(hostname: str) -> None:
    """Enforce a brief gap between requests to the same domain using Redis if available."""
    try:
        from app.core.config import get_settings
        import redis as redis_lib
        r = redis_lib.from_url(get_settings().redis_url, socket_connect_timeout=1)
        key = f"ratelimit:domain:{hostname}"
        if r.exists(key):
            time.sleep(1)  # Brief wait — scheduler won't send same domain twice quickly
        r.set(key, "1", ex=10)
    except Exception:
        pass  # Redis unavailable — skip rate limiting


def fetch_products_shopify(store_url: str, max_products: Optional[int] = None) -> List[Dict[str, Any]]:
    products: List[Dict[str, Any]] = []
    hostname = urlparse(store_url).netloc

    _enforce_domain_rate_limit(hostname)

    # Match the proven-working PDF version: limit=250, 10 pages.
    page_limit = min(250, max_products) if max_products is not None else 250
    MAX_PAGES = 10

    with httpx.Client(timeout=25.0, headers=_headers(), follow_redirects=True) as client:
        for page in range(1, MAX_PAGES + 1):
            url = f"{store_url.rstrip('/')}/products.json?limit={page_limit}&page={page}"
            r = client.get(url)
            ct = r.headers.get("content-type", "")
            if "application/json" not in ct:
                break
            if r.status_code == 429:
                time.sleep(min(int(r.headers.get("retry-after", "10")), 30))
                break
            if r.status_code in (403, 404) or r.status_code != 200:
                break

            data = r.json()
            batch = data.get("products", [])
            if not batch:
                break

            products.extend(batch)

            if max_products is not None and len(products) >= max_products:
                break

    return products[:max_products] if max_products else products


def check_store(store_url: str) -> Dict[str, Any]:
    """Probe whether a URL is an accessible Shopify store. Returns {ok, base_url} or {ok: False, error}."""
    candidates = []
    parsed = urlparse(store_url)
    hostname = parsed.netloc or parsed.path.strip("/")

    if hostname.startswith("www."):
        candidates = [f"https://{hostname}", f"https://{hostname[4:]}"]
    else:
        candidates = [f"https://{hostname}", f"https://www.{hostname}"]

    headers = _headers()
    with httpx.Client(timeout=15.0, headers=headers, follow_redirects=True) as client:
        for candidate in candidates:
            try:
                r = client.get(f"{candidate}/products.json?limit=1")
                if r.status_code == 200 and "application/json" in r.headers.get("content-type", ""):
                    data = r.json()
                    if "products" in data:
                        return {"ok": True, "base_url": str(r.url).split("/products.json")[0]}
                elif r.status_code == 403:
                    # 403 from /products.json is characteristic of a Shopify store with
                    # bot-protection on the probe endpoint. The actual scan (with full
                    # headers and pagination) may still succeed. Allow the user to add it.
                    return {"ok": True, "base_url": candidate, "restricted": True}
            except Exception:
                continue

    return {"ok": False, "error": "not_shopify"}
