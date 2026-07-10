"""
Intent-signal engine (Phase 2 of the Lead Engine — internal growth tooling).

Captures people publicly describing StoreScout-shaped pain and scores how
strong that buying intent is. The live fetch of public discussions runs on the
web process (worker IPs are blocked), mirroring the store-index pattern.

Design notes / honesty:
  · Reddit's public JSON search is the one intent source reachable without a
    paid API. Posters are usually anonymous, so a contactable email is the
    exception — most signals are "engage in the thread", and only those where a
    store domain is extractable become outbound leads.
  · Every signal keeps the exact quote + permalink, so nothing is fabricated.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Subreddits where Shopify/DTC operators discuss competitive pain.
INTENT_CHANNELS = [
    "shopify", "ecommerce", "EntrepreneurRideAlong", "smallbusiness",
    "dropship", "Entrepreneur", "shopifystore",
]

# Search phrases that map to what StoreScout actually does.
INTENT_QUERIES = [
    "track competitor prices",
    "monitor competitors",
    "competitor price tracking",
    "competitor monitoring tool",
    "keep up with competitors",
    "competitor dropped price",
    "spy on competitor store",
    "how do competitors",
    "competitive analysis shopify",
]

# Cheap pre-filter so we only spend AI scoring on plausible posts.
_INTENT_HINTS = re.compile(
    r"competitor|compete|competing|price track|price monitor|monitor.*price|"
    r"undercut|what.*competitors|track.*store|scrape.*price|price war",
    re.I,
)

_DOMAIN_RE = re.compile(r"\b([a-z0-9][a-z0-9\-]{1,}\.(?:com|co|io|shop|store|myshopify\.com))\b", re.I)
_DOMAIN_SKIP = ("reddit.com", "redd.it", "imgur", "youtube", "youtu.be", "google.com",
                "shopify.com", "amazon.com", "example.com", "gmail.com", "facebook.com",
                "instagram.com", "tiktok.com", "wikipedia.org")


def extract_domain(text: str) -> Optional[str]:
    """Best-effort store domain from a post — the poster's own store if they
    linked it. Skips platforms/socials. Returns None when nothing usable."""
    for m in _DOMAIN_RE.finditer(text or ""):
        d = m.group(1).lower()
        if any(s in d for s in _DOMAIN_SKIP):
            continue
        return d
    return None


def score_intent(title: str, body: str) -> Dict[str, Any]:
    """AI relevance: is this someone who'd want competitor price/product
    monitoring for their store? Returns {score 0-100, reason}. Falls back to a
    keyword heuristic without an API key."""
    text = f"{title}\n{body}"[:1500]
    if not _INTENT_HINTS.search(text):
        return {"score": 0, "reason": "no competitive-intent keywords"}

    try:
        from app.core.config import get_settings
        settings = get_settings()
        if not settings.anthropic_api_key:
            # Heuristic: keyword present → moderate score.
            return {"score": 55, "reason": "keyword match (no AI scoring configured)"}
        import json as _json
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        prompt = f"""StoreScout monitors competitor prices/products for Shopify DTC brands. Read this forum post and judge whether the author is a store owner who would want competitor price/product monitoring — i.e. a real sales lead.

POST:
{text}

Return ONLY JSON: {{"score": <0-100 buying-intent>, "reason": "<= 12 words"}}. Score high only if they clearly run a store AND want competitor tracking. A generic mention scores low."""
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=80,
            messages=[{"role": "user", "content": prompt}],
        )
        t = msg.content[0].text.strip()
        if t.startswith("```"):
            t = t.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        p = _json.loads(t)
        return {"score": max(0, min(100, int(p.get("score") or 0))), "reason": str(p.get("reason") or "")[:120]}
    except Exception as exc:
        logger.debug("score_intent failed: %s", exc)
        return {"score": 50, "reason": "keyword match (scoring error)"}


def fetch_reddit_via_web(limit_per_query: int = 15) -> List[Dict[str, Any]]:
    """Ask the web process to search Reddit's public JSON for our intent phrases
    (worker IPs are blocked). Returns raw post dicts; [] on any failure."""
    from app.core.config import get_settings
    settings = get_settings()
    try:
        import httpx
        resp = httpx.post(
            f"{settings.api_internal_url}/api/v1/internal/reddit-search",
            headers={"x-internal-token": settings.internal_secret},
            json={"channels": INTENT_CHANNELS, "queries": INTENT_QUERIES, "limit": limit_per_query},
            timeout=120.0,
        )
        if resp.status_code != 200:
            logger.info("reddit-search returned HTTP %s", resp.status_code)
            return []
        return resp.json().get("posts", []) or []
    except Exception as exc:
        logger.info("reddit-search unavailable: %s", exc)
        return []
