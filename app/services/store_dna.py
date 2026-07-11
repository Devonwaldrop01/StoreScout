"""
Store DNA — a semantic business profile for a verified indexed store.

Tracked competitors get a full Brand Decode (Sonnet, expensive). Indexed stores
only ever get a ≤4-request light pass, so their DNA is built from the signals
already on the row — product titles/types, collections, pricing, homepage
message — with ONE cheap Haiku call, cached by an input signature so it never
re-runs unless the store's picture actually changes.

Two jobs:
  1. generate_store_dna(ctx) — the readable profile (summary, what they sell,
     audience, price positioning, personality, differentiators) PLUS a flat,
     normalized keyword set that is the machine-comparable layer.
  2. dna_match_score(a, b) — a 0-100 direct-competitor similarity between two
     stores (or a store and a user profile), driven mostly by keyword overlap
     with category / price-tier / audience agreement on top. This is what turns
     "same category" into "actually competes with you".
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Filler words that carry no distinguishing signal — stripped from keyword sets
# so overlap reflects real product/brand similarity, not shared boilerplate.
_STOP = {
    "the", "and", "for", "with", "your", "our", "shop", "store", "collection",
    "collections", "product", "products", "new", "best", "sale", "free",
    "shipping", "home", "all", "official", "premium", "quality", "brand",
    "online", "buy", "get", "made", "you", "from", "that", "this", "are",
}

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9\-]+")


def normalize_keywords(values: Any, limit: int = 24) -> List[str]:
    """Flatten arbitrary text/lists into a deduped, lowercased tag set — the
    common shape both DNA generation and matching compare against."""
    out: List[str] = []
    seen: set = set()

    def _add(token: str) -> None:
        token = token.strip().lower()
        if not token or token in _STOP or len(token) < 3:
            return
        if token not in seen:
            seen.add(token)
            out.append(token)

    def _walk(v: Any) -> None:
        if v is None:
            return
        if isinstance(v, (list, tuple)):
            for x in v:
                _walk(x)
        elif isinstance(v, dict):
            for x in (v.get("title"), v.get("detail"), v.get("name")):
                _walk(x)
        else:
            for m in _WORD_RE.findall(str(v).lower()):
                _add(m)

    _walk(values)
    return out[:limit]


def dna_signature(ctx: Dict[str, Any]) -> str:
    """Stable hash of the inputs — regenerate DNA only when they change."""
    keys = [
        ctx.get("category"), ctx.get("subcategory"), ctx.get("pricing_tier"),
        round(ctx.get("median_price") or 0), ctx.get("product_count"),
        sorted([str(x).lower() for x in (ctx.get("product_types") or [])][:20]),
        sorted([str(x).lower() for x in (ctx.get("product_titles") or [])][:30]),
        (ctx.get("homepage_message") or ctx.get("description") or "")[:200],
    ]
    raw = json.dumps(keys, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _fallback_dna(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """A grounded, no-AI profile so the index still gets a usable DNA (and a
    keyword set for matching) when Anthropic is unavailable or errors."""
    cat = ctx.get("category") or "General"
    sub = ctx.get("subcategory")
    tier = ctx.get("pricing_tier")
    sells = ", ".join([str(x) for x in (ctx.get("product_types") or [])][:4]) or (sub or cat)
    tier_phrase = {
        "budget": "value / entry pricing", "mid-market": "mid-market pricing",
        "premium": "premium pricing", "luxury": "luxury pricing",
    }.get(tier or "", "pricing not established")
    keywords = normalize_keywords([
        cat, sub, ctx.get("product_types"), ctx.get("brand_keywords"),
        ctx.get("product_titles"), ctx.get("collections"),
    ])
    return {
        "summary": f"A {sub or cat} store"
                   + (f" competing on {tier_phrase.split(' / ')[0]}." if tier else "."),
        "sells": sells,
        "audience": ctx.get("target_customer") or "general online shoppers",
        "price_positioning": tier_phrase,
        "personality": [],
        "differentiators": [],
        "keywords": keywords,
        "method": "heuristic",
    }


def generate_store_dna(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    ctx: {brand_name, domain, category, subcategory, pricing_tier, median_price,
          product_count, product_types[], product_titles[], collections[],
          brand_keywords[], target_customer, homepage_message, description}

    Returns a Store DNA dict (always includes a non-empty `keywords` list for
    matching) or None only if there is truly nothing to reason over.
    """
    titles = [str(t) for t in (ctx.get("product_titles") or [])][:30]
    ptypes = [str(t) for t in (ctx.get("product_types") or [])][:20]
    colls = [str(c.get("title") if isinstance(c, dict) else c or "")
             for c in (ctx.get("collections") or [])][:20]
    msg = (ctx.get("homepage_message") or ctx.get("description") or "").strip()
    if not (titles or ptypes or colls or msg):
        return None  # nothing to profile

    from app.core.config import get_settings
    from app.services.ai import UNTRUSTED_DATA_NOTE, call_claude, parse_json
    if not get_settings().anthropic_api_key:
        return _fallback_dna(ctx)

    money = []
    if ctx.get("median_price"):
        money.append(f"median price ${ctx['median_price']:.0f}")
    if ctx.get("product_count"):
        money.append(f"~{ctx['product_count']} products")
    if ctx.get("pricing_tier"):
        money.append(f"{ctx['pricing_tier']} tier")

    payload = (
        f"STORE: {ctx.get('brand_name') or ctx.get('domain') or '(unknown)'}\n"
        f"CATEGORY: {ctx.get('category') or 'unknown'}"
        f"{' · ' + ctx['subcategory'] if ctx.get('subcategory') else ''}\n"
        f"COMMERCIALS: {', '.join(money) or 'unknown'}\n"
        f"HOMEPAGE MESSAGE: {msg[:250] or '(none)'}\n"
        f"PRODUCT TYPES: {', '.join(ptypes) or '(none)'}\n"
        f"COLLECTIONS: {', '.join(colls) or '(none)'}\n"
        f"PRODUCT TITLES (the ground truth):\n"
        + "\n".join(f"  · {t}" for t in titles[:30])
    )

    prompt = f"""You profile Shopify stores so a store owner can tell whether a business is a REAL direct competitor. Base everything ONLY on the signals below — never invent products, numbers, or claims. Judge by the actual product titles and types.

{UNTRUSTED_DATA_NOTE}

{payload}

Write a tight Store DNA. Return ONLY JSON:
{{
  "summary": "<one sentence: what kind of business this actually is — what they sell and how they position>",
  "sells": "<the concrete product focus in a short phrase, e.g. 'minimalist gold-plated everyday jewelry'>",
  "audience": "<who they serve — the specific customer, not 'everyone'>",
  "price_positioning": "<value | mid-market | premium | luxury — plus a 3-5 word reason>",
  "personality": ["<2-4 brand-personality traits: e.g. minimalist, playful, technical, sustainable, luxury, streetwear>"],
  "differentiators": ["<2-3 things that would make this store distinct from same-category rivals; empty if none are evident>"],
  "keywords": ["<8-14 lowercase tags a matcher can use to find direct competitors: product nouns, style/material, niche, audience — NOT generic words like 'shop' or 'quality'>"]
}}"""

    res = call_claude(
        "store_dna", prompt,
        model="claude-haiku-4-5-20251001", max_tokens=500,
        entity=ctx.get("domain"),
    )
    if not res.ok:
        return _fallback_dna(ctx)
    p = parse_json(res.text)
    if not isinstance(p, dict) or not p.get("summary"):
        return _fallback_dna(ctx)
    # AI keywords are the primary matching layer; enrich with the store's own
    # product types so overlap never depends on the model alone.
    kws = normalize_keywords([
        p.get("keywords"), ctx.get("product_types"),
        ctx.get("subcategory"), ctx.get("brand_keywords"),
    ])
    return {
        "summary": str(p["summary"])[:280],
        "sells": str(p.get("sells") or "")[:160],
        "audience": str(p.get("audience") or "")[:160],
        "price_positioning": str(p.get("price_positioning") or "")[:120],
        "personality": [str(x)[:40].lower() for x in (p.get("personality") or [])][:5],
        "differentiators": [str(x)[:160] for x in (p.get("differentiators") or [])][:4],
        "keywords": kws,
        "method": "ai",
    }


# ── Direct-competitor matching ─────────────────────────────────────────────

_TIER_ORDER = ["budget", "mid-market", "premium", "luxury"]


def _keywords_of(row: Dict[str, Any]) -> List[str]:
    """Best available keyword set for a row — prefers stored dna_keywords, then
    the DNA blob, then falls back to category/brand-keyword/product-type text so
    matching still works on rows that have no DNA yet."""
    kws = row.get("dna_keywords")
    if not kws and isinstance(row.get("store_dna"), dict):
        kws = row["store_dna"].get("keywords")
    if kws:
        return normalize_keywords(kws)
    return normalize_keywords([
        row.get("category"), row.get("subcategory"),
        row.get("brand_keywords"), row.get("product_types"),
    ])


def dna_match_score(a: Dict[str, Any], b: Dict[str, Any]) -> int:
    """
    0-100 direct-competitor similarity between two stores (b may be a user
    profile: {category, subcategory, pricing_tier, dna_keywords/keywords}).

    Weighting: keyword overlap dominates (a real competitor sells similar
    things), with category agreement, price-tier proximity and audience overlap
    layered on. Designed to separate a TRUE rival from a mere same-category store.
    """
    ka, kb = set(_keywords_of(a)), set(_keywords_of(b))
    score = 0.0

    # Keyword overlap (Jaccard-ish, but rewarded by absolute count too) — up to 55.
    if ka and kb:
        inter = len(ka & kb)
        union = len(ka | kb) or 1
        score += min(40.0, (inter / union) * 80.0)   # proportion
        score += min(15.0, inter * 3.0)               # absolute shared tags

    # Same classified category is the backbone of "direct" — up to 25.
    ca, cb = (a.get("category") or "").lower(), (b.get("category") or "").lower()
    if ca and ca == cb:
        score += 18
        sa = (a.get("subcategory") or "").lower()
        sb = (b.get("subcategory") or "").lower()
        if sa and sa == sb:
            score += 7

    # Price-tier proximity — competitors usually play in the same price lane. ±.
    ta, tb = a.get("pricing_tier"), b.get("pricing_tier")
    if ta and tb:
        try:
            gap = abs(_TIER_ORDER.index(ta) - _TIER_ORDER.index(tb))
            score += (2 - gap) * 6 if gap <= 2 else 0   # same tier +12, one apart +6
        except ValueError:
            pass

    # Audience overlap — small nudge when both describe the same buyer. Up to 8.
    aud_a = normalize_keywords(a.get("target_customer")
                               or (a.get("store_dna") or {}).get("audience"))
    aud_b = normalize_keywords(b.get("target_customer")
                               or (b.get("store_dna") or {}).get("audience"))
    if aud_a and aud_b and (set(aud_a) & set(aud_b)):
        score += 8

    return int(max(0, min(100, round(score))))
