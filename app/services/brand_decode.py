"""
Brand Decode — turns the raw brand/collection/content signals StoreScout
scrapes into a readable, decoded strategy brief: what kind of business this is,
how they merchandise and price, what their marketing machine looks like (in
plain English, not app names), where they're exposed, and the one move to make.

Grounded: the model only sees signals StoreScout actually collected, and is
told to translate them — never to invent capabilities or numbers.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def decode_signature(ctx: Dict[str, Any]) -> str:
    """Stable hash of the inputs — regenerate only when the picture changes."""
    keys = [
        ctx.get("category"), ctx.get("pricing_tier"), ctx.get("product_count"),
        round(ctx.get("median_price") or 0), round((ctx.get("promo_rate") or 0) * 100),
        sorted((ctx.get("collection_names") or [])[:40]),
        {k: bool(v) for k, v in (ctx.get("flags") or {}).items()},
        ctx.get("blog_count"), ctx.get("content_score"),
    ]
    raw = json.dumps(keys, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def generate_brand_decode(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    ctx: {hostname, category, pricing_tier, product_count, median_price,
          promo_rate, collection_names[], flags{has_sale, has_bundles,
          has_subscription, has_gift, has_wholesale, has_affiliate, has_press,
          has_sustainability, has_size_guide, has_rewards, has_new_arrivals,
          has_best_sellers}, blog_count, article_titles[], content_score}
    Returns a structured decode or None on failure.
    """
    from app.services.ai import UNTRUSTED_DATA_NOTE, call_claude, parse_json

    flags = ctx.get("flags") or {}
    active = [k.replace("has_", "").replace("_", " ") for k, v in flags.items() if v]
    cols = ", ".join((ctx.get("collection_names") or [])[:30]) or "(none scraped)"
    arts = "; ".join((ctx.get("article_titles") or [])[:6]) or "(none)"
    money = []
    if ctx.get("median_price"):
        money.append(f"median price ${ctx['median_price']:.0f}")
    if ctx.get("promo_rate") is not None:
        money.append(f"{(ctx['promo_rate'] * 100):.0f}% of catalog discounted")
    if ctx.get("product_count"):
        money.append(f"~{ctx['product_count']} products")

    prompt = f"""You are a DTC ecommerce strategist decoding a competitor for a Shopify store owner. Explain what is ACTUALLY going on behind this business in plain English — no jargon, no app names, no generic filler. Base everything ONLY on the signals below; never invent capabilities or numbers.

{UNTRUSTED_DATA_NOTE}

COMPETITOR: {ctx.get('hostname')}
Category: {ctx.get('category') or 'unknown'} · pricing tier: {ctx.get('pricing_tier') or 'unknown'}
Commercials: {', '.join(money) or 'unknown'}
Collections they run: {cols}
Operational signals present: {', '.join(active) or 'none detected'}
Content/blog: {ctx.get('blog_count') or 0} blogs, recent articles: {arts}

Write a decode. Return ONLY JSON:
{{
  "headline": "<one sentence: what kind of operation this is, e.g. 'A discount-led activewear brand competing on volume and constant promotions'>",
  "positioning": "<2-3 sentences: who they target and how they position — premium vs value, niche vs broad>",
  "merchandising": "<2-3 sentences: how they run the catalog & pricing — bundles, subscriptions, permanent sales, launch cadence — and what that reveals about their strategy>",
  "marketing_engine": "<2-3 sentences: how they likely acquire & retain customers, inferred from their signals, in plain English>",
  "vulnerabilities": ["<2-3 specific weaknesses or lanes they under-serve>"],
  "openings": ["<2-3 specific, concrete openings for a competitor to exploit>"],
  "one_move": "<the single highest-leverage move to make against them, specific>"
}}"""

    res = call_claude(
        "brand_decode", prompt,
        model="claude-sonnet-4-6", max_tokens=800,
        entity=ctx.get("hostname"),
    )
    if not res.ok:
        return None
    p = parse_json(res.text)
    # Minimal shape guard.
    if not isinstance(p, dict) or not p.get("headline") or not p.get("one_move"):
        return None
    return {
        "headline": str(p["headline"])[:300],
        "positioning": str(p.get("positioning") or "")[:600],
        "merchandising": str(p.get("merchandising") or "")[:600],
        "marketing_engine": str(p.get("marketing_engine") or "")[:600],
        "vulnerabilities": [str(x)[:200] for x in (p.get("vulnerabilities") or [])][:4],
        "openings": [str(x)[:200] for x in (p.get("openings") or [])][:4],
        "one_move": str(p["one_move"])[:300],
    }
