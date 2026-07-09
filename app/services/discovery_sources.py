"""
Discovery sources — Stage 1 of the index pipeline. A source's ONLY job is to
surface candidate Shopify domains; it never verifies, classifies, or scans.
Every source is resumable (persists a cursor) and pluggable behind a common
interface, so new sources (theme demos, app showcases, partner directories,
user submissions) drop in without touching the pipeline.

Discovery Source #1 is the Shop App. Shopify's own consumer app is a curated
feed of real, active Shopify merchants — a far higher-quality starting point
than scraping the open web, which is why verification success should climb.

IMPORTANT: the live Shop App fetch must go through the web process (the
worker's IP is blocked), and shop.app has no stable public discovery API.
ShopAppSource is written to consume whatever domains the web-side fetcher
returns and to DEGRADE GRACEFULLY (return nothing, advance no cursor) when
the feed is unavailable — it never fabricates domains.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Protocol, Tuple

logger = logging.getLogger(__name__)


class DiscoverySource(Protocol):
    name: str
    def fetch(self, cursor: Optional[dict], limit: int) -> Tuple[List[str], Optional[dict]]:
        """Return (candidate_domains, next_cursor). An empty list with the
        SAME cursor means 'nothing new right now' — the pipeline will retry
        later without losing its place."""
        ...


class ShopAppSource:
    """Discovery Source #1 — Shopify's Shop App merchant feed."""
    name = "shop_app"

    def fetch(self, cursor: Optional[dict], limit: int) -> Tuple[List[str], Optional[dict]]:
        from app.core.config import get_settings
        from app.services.store_index import normalize_domain
        settings = get_settings()

        # The live crawl is delegated to the web process (worker IP is blocked).
        # It walks the Shop App storefronts sitemap, resolves each store page to
        # the merchant's real domain, and returns them plus an advanced cursor.
        # The web side is polite (paced, small batches) to respect shop.app's
        # rate limit, so allow it plenty of time.
        try:
            import httpx
            resp = httpx.post(
                f"{settings.api_internal_url}/api/v1/internal/shop-app-page",
                headers={"x-internal-token": settings.internal_secret},
                json={"cursor": cursor or {}, "limit": limit},
                timeout=120.0,
            )
            if resp.status_code != 200:
                logger.info("shop_app: fetcher returned %s — holding cursor", resp.status_code)
                return [], cursor
            body = resp.json()
            raw = body.get("domains", []) or []
            # The web side owns cursor advancement (child sitemap + offset); trust
            # the returned cursor so the crawl resumes exactly where it stopped.
            next_cursor = body.get("cursor") or cursor
        except Exception as exc:
            logger.info("shop_app: fetch unavailable (%s) — holding cursor", exc)
            return [], cursor

        domains = []
        seen = set()
        for d in raw:
            nd = normalize_domain(d)
            if nd and "." in nd and nd not in seen:
                seen.add(nd)
                domains.append(nd)

        return domains, next_cursor


# Registry — future sources register here; the pipeline iterates enabled ones.
_SOURCES: Dict[str, DiscoverySource] = {
    ShopAppSource.name: ShopAppSource(),
}


def get_source(name: str) -> Optional[DiscoverySource]:
    return _SOURCES.get(name)


def all_sources() -> List[DiscoverySource]:
    return list(_SOURCES.values())
