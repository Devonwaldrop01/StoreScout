from __future__ import annotations
import logging
import time
import traceback
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

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


def _classify_failure(status: int, content_type: str, body_preview: str) -> str:
    """Return a human-readable failure category for logging."""
    if "text/html" in content_type:
        return "HTML_RETURNED_INSTEAD_OF_JSON"
    if status == 403:
        return "AUTH_BLOCKED_403"
    if status == 429:
        return "RATE_LIMITED_429"
    if status == 404:
        return "NOT_FOUND_404"
    if status == 200 and "application/json" not in content_type:
        return f"NON_JSON_CONTENT_TYPE_{content_type!r}"
    if status != 200:
        return f"NON_200_STATUS_{status}"
    return "UNKNOWN"


def fetch_products_shopify(store_url: str, max_products: Optional[int] = None) -> List[Dict[str, Any]]:
    products: List[Dict[str, Any]] = []
    hostname = urlparse(store_url).netloc

    logger.info("[FETCH START] store_url=%r max_products=%r ua=%r",
                store_url, max_products, DEFAULT_HEADERS["User-Agent"])

    _enforce_domain_rate_limit(hostname)

    page_limit = min(250, max_products) if max_products is not None else 250
    MAX_PAGES = 10

    try:
        with httpx.Client(timeout=25.0, headers=_headers(), follow_redirects=True) as client:
            for page in range(1, MAX_PAGES + 1):
                url = f"{store_url.rstrip('/')}/products.json?limit={page_limit}&page={page}"
                logger.info("[FETCH REQUEST] page=%d url=%r", page, url)

                try:
                    t0 = time.monotonic()
                    r = client.get(url)
                    elapsed_ms = int((time.monotonic() - t0) * 1000)
                except httpx.TimeoutException as exc:
                    logger.error(
                        "[FETCH TIMEOUT] page=%d url=%r elapsed_ms=%d exc=%s\n%s",
                        page, url, int((time.monotonic() - t0) * 1000),
                        exc, traceback.format_exc(),
                    )
                    break
                except httpx.ConnectError as exc:
                    logger.error(
                        "[FETCH CONNECT_ERROR] page=%d url=%r exc=%s\n%s",
                        page, url, exc, traceback.format_exc(),
                    )
                    break
                except Exception as exc:
                    logger.error(
                        "[FETCH EXCEPTION] page=%d url=%r exc=%s\n%s",
                        page, url, exc, traceback.format_exc(),
                    )
                    break

                status = r.status_code
                ct = r.headers.get("content-type", "")
                final_url = str(r.url)
                body_preview = r.text[:500]

                logger.info(
                    "[FETCH RESPONSE] page=%d status=%d ct=%r final_url=%r elapsed_ms=%d",
                    page, status, ct, final_url, elapsed_ms,
                )

                if status != 200 or "application/json" not in ct:
                    category = _classify_failure(status, ct, body_preview)
                    logger.warning(
                        "[FETCH FAILURE] page=%d category=%s status=%d ct=%r "
                        "final_url=%r body_preview=%r",
                        page, category, status, ct, final_url, body_preview,
                    )
                    if status == 429:
                        retry_after = int(r.headers.get("retry-after", "10"))
                        logger.info("[FETCH RATE_LIMIT] retry-after=%ds", retry_after)
                        time.sleep(min(retry_after, 30))
                    break

                # JSON parsing
                try:
                    data = r.json()
                except Exception as exc:
                    logger.error(
                        "[FETCH JSON_PARSE_ERROR] page=%d url=%r body_preview=%r exc=%s\n%s",
                        page, url, body_preview, exc, traceback.format_exc(),
                    )
                    break

                batch = data.get("products", [])
                if not isinstance(batch, list):
                    logger.error(
                        "[FETCH BAD_SHAPE] page=%d url=%r 'products' is %s not list, body=%r",
                        page, url, type(batch).__name__, body_preview,
                    )
                    break

                logger.info("[FETCH PAGE_OK] page=%d products_on_page=%d total_so_far=%d",
                            page, len(batch), len(products) + len(batch))

                if not batch:
                    logger.info("[FETCH DONE] no more products at page=%d", page)
                    break

                products.extend(batch)

                if max_products is not None and len(products) >= max_products:
                    products = products[:max_products]
                    break

    except Exception as exc:
        logger.error(
            "[FETCH OUTER_EXCEPTION] store_url=%r exc=%s\n%s",
            store_url, exc, traceback.format_exc(),
        )

    logger.info("[FETCH COMPLETE] store_url=%r total_products=%d", store_url, len(products))
    return products


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
                status = r.status_code
                ct = r.headers.get("content-type", "")
                if status == 200 and "application/json" in ct:
                    data = r.json()
                    if "products" in data:
                        return {"ok": True, "base_url": str(r.url).split("/products.json")[0]}
                elif status == 403:
                    # 403 from /products.json is characteristic of a Shopify store with
                    # bot-protection on the probe endpoint. The actual scan (with full
                    # headers and pagination) may still succeed. Allow the user to add it.
                    return {"ok": True, "base_url": candidate, "restricted": True}
            except Exception:
                continue

    return {"ok": False, "error": "not_shopify"}
