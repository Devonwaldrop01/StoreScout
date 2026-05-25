from __future__ import annotations
import logging
import time
import traceback
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# curl_cffi impersonates Chrome's exact TLS fingerprint (JA3/JA4), bypassing
# Cloudflare Bot Management challenges that block Python's default TLS stack.
# Falls back to httpx for environments where curl_cffi can't be installed.
try:
    from curl_cffi.requests import Session as CurlSession
    _USE_CURL_CFFI = True
except ImportError:
    import httpx
    _USE_CURL_CFFI = False

logger = logging.getLogger(__name__)

# Chrome 120 UA — consistent with the impersonate="chrome120" TLS fingerprint.
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

IMPERSONATE = "chrome120"


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

    logger.info("[FETCH START] store_url=%r max_products=%r backend=%s ua=%r",
                store_url, max_products,
                "curl_cffi/" + IMPERSONATE if _USE_CURL_CFFI else "httpx",
                DEFAULT_HEADERS["User-Agent"])

    _enforce_domain_rate_limit(hostname)

    page_limit = min(250, max_products) if max_products is not None else 250
    MAX_PAGES = 10
    FETCH_WALL_LIMIT = 180  # seconds — bail out before Celery hard-kills the task

    try:
        if _USE_CURL_CFFI:
            _make_client = lambda: CurlSession(impersonate=IMPERSONATE, headers=_headers())
        else:
            _make_client = lambda: httpx.Client(timeout=25.0, headers=_headers(), follow_redirects=True)

        fetch_start = time.monotonic()
        with _make_client() as client:
            for page in range(1, MAX_PAGES + 1):
                if time.monotonic() - fetch_start > FETCH_WALL_LIMIT:
                    logger.warning(
                        "[FETCH TRUNCATED] store_url=%r hit %ds wall limit after %d products on page %d",
                        store_url, FETCH_WALL_LIMIT, len(products), page,
                    )
                    break
                url = f"{store_url.rstrip('/')}/products.json?limit={page_limit}&page={page}"
                logger.info("[FETCH REQUEST] page=%d url=%r", page, url)

                t0 = time.monotonic()
                try:
                    if _USE_CURL_CFFI:
                        r = client.get(url, timeout=25, allow_redirects=True)
                    else:
                        r = client.get(url)
                    elapsed_ms = int((time.monotonic() - t0) * 1000)
                except Exception as exc:
                    elapsed_ms = int((time.monotonic() - t0) * 1000)
                    exc_type = type(exc).__name__
                    category = "TIMEOUT" if "timeout" in exc_type.lower() or "timeout" in str(exc).lower() else "CONNECTION_ERROR"
                    logger.error(
                        "[FETCH %s] page=%d url=%r elapsed_ms=%d exc=%s\n%s",
                        category, page, url, elapsed_ms, exc, traceback.format_exc(),
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


def fetch_extended_data(store_url: str) -> Dict[str, Any]:
    """
    Fetch supplementary public Shopify endpoints: collections, pages, blogs, articles.
    All requests are non-fatal — partial results are returned on any failure.
    Called after the main products fetch so the domain rate-limit key is already set.
    """
    base = store_url.rstrip("/")
    hostname = urlparse(store_url).netloc
    result: Dict[str, Any] = {
        "collections": [],
        "pages": [],
        "blogs": [],
        "articles": [],
        "meta": {"collections_ok": False, "pages_ok": False, "blogs_ok": False, "articles_ok": False},
    }

    def _get_json(client, url: str, list_key: str):
        time.sleep(1.5)  # polite inter-request gap on same domain
        try:
            if _USE_CURL_CFFI:
                r = client.get(url, timeout=15, allow_redirects=True)
            else:
                r = client.get(url)
            if r.status_code == 200 and "application/json" in r.headers.get("content-type", ""):
                data = r.json()
                items = data.get(list_key, [])
                logger.info("[EXT_FETCH] %s: %d items", list_key, len(items))
                return True, items
            logger.info("[EXT_FETCH] %s: status=%d (skipped)", list_key, r.status_code)
        except Exception as exc:
            logger.warning("[EXT_FETCH] %s failed (non-fatal): %s", list_key, exc)
        return False, []

    if _USE_CURL_CFFI:
        _make_client = lambda: CurlSession(impersonate=IMPERSONATE, headers=_headers())
    else:
        _make_client = lambda: httpx.Client(timeout=15.0, headers=_headers(), follow_redirects=True)

    with _make_client() as client:
        ok, items = _get_json(client, f"{base}/collections.json?limit=250", "collections")
        result["collections"] = items
        result["meta"]["collections_ok"] = ok

        ok, items = _get_json(client, f"{base}/pages.json?limit=250", "pages")
        result["pages"] = items
        result["meta"]["pages_ok"] = ok

        ok, items = _get_json(client, f"{base}/blogs.json", "blogs")
        result["blogs"] = items
        result["meta"]["blogs_ok"] = ok

        if result["blogs"]:
            blog_id = result["blogs"][0].get("id")
            if blog_id:
                ok, items = _get_json(client, f"{base}/blogs/{blog_id}/articles.json?limit=10", "articles")
                result["articles"] = items
                result["meta"]["articles_ok"] = ok

    return result


def check_store(store_url: str) -> Dict[str, Any]:
    """Probe whether a URL is an accessible Shopify store. Returns {ok, base_url} or {ok: False, error}."""
    candidates = []
    parsed = urlparse(store_url)
    hostname = parsed.netloc or parsed.path.strip("/")

    if hostname.startswith("www."):
        candidates = [f"https://{hostname}", f"https://{hostname[4:]}"]
    else:
        candidates = [f"https://{hostname}", f"https://www.{hostname}"]

    if _USE_CURL_CFFI:
        _make_probe_client = lambda: CurlSession(impersonate=IMPERSONATE, headers=_headers())
    else:
        _make_probe_client = lambda: httpx.Client(timeout=15.0, headers=_headers(), follow_redirects=True)

    with _make_probe_client() as client:
        for candidate in candidates:
            try:
                if _USE_CURL_CFFI:
                    r = client.get(f"{candidate}/products.json?limit=1", timeout=15, allow_redirects=True)
                else:
                    r = client.get(f"{candidate}/products.json?limit=1")
                status = r.status_code
                ct = r.headers.get("content-type", "")
                if status == 200 and "application/json" in ct:
                    data = r.json()
                    if "products" in data:
                        final = str(r.url) if hasattr(r, "url") else candidate
                        return {"ok": True, "base_url": final.split("/products.json")[0]}
                elif status == 403:
                    # 403 here may mean bot-protection on the probe; the full scan with
                    # curl_cffi TLS impersonation may still succeed.
                    return {"ok": True, "base_url": candidate, "restricted": True}
            except Exception:
                continue

    return {"ok": False, "error": "not_shopify"}
