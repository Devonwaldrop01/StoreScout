"""
Market-level intelligence endpoints — reads that span the whole tracked set
rather than a single competitor.

/market/signals/interpret takes the deterministic cross-competitor Market
Signals the frontend already derived and rewrites them with per-category
nuance grounded in the user's own business — so "three competitors are
discounting" becomes advice specific to *their* category and price lane. One
cheap batched Haiku call; degrades to the deterministic copy on any failure.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_effective_user_id
from app.core.config import get_settings
from app.core.database import get_supabase
from app.core.obs import safe_read
from app.core.ratelimit import check_rate_limit, dedupe_key, single_flight
from app.services.ai import UNTRUSTED_DATA_NOTE, call_claude, parse_json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market", tags=["market"])


class SignalMember(BaseModel):
    hostname: str
    label: Optional[str] = None


class SignalIn(BaseModel):
    id: str
    headline: Optional[str] = None
    what_happened: Optional[str] = None
    competitor_count: int = 0
    members: List[SignalMember] = []


class InterpretRequest(BaseModel):
    signals: List[SignalIn] = []


def _user_market_context(db, user_id: str) -> str:
    """A short description of the user's own business so interpretations land in
    their category and price lane. Best-effort, fully guarded."""
    parts: List[str] = []
    # Their own tracked store → index classification (category + pricing).
    try:
        from app.services.store_index import normalize_domain
        ms = db.table("competitors").select("hostname").eq("user_id", user_id)\
            .eq("is_my_store", True).maybe_single().execute()
        host = ((ms.data if ms else {}) or {}).get("hostname")
        if host:
            r = db.table("shopify_store_index")\
                .select("category, subcategory, pricing_tier, target_customer")\
                .eq("domain", normalize_domain(host)).maybe_single().execute()
            d = (r.data if r else {}) or {}
            if d.get("category"):
                parts.append(f"category: {d['category']}" + (f" · {d['subcategory']}" if d.get("subcategory") else ""))
            if d.get("pricing_tier"):
                parts.append(f"price tier: {d['pricing_tier']}")
            if d.get("target_customer"):
                parts.append(f"customer: {d['target_customer']}")
    except Exception:
        pass
    # Business profile (from onboarding) — what they sell, in their words.
    if not parts:
        try:
            bp = db.table("business_profiles").select("sells, description")\
                .eq("user_id", user_id).maybe_single().execute()
            d = (bp.data if bp else {}) or {}
            if d.get("sells"):
                parts.append(f"sells: {d['sells']}")
            elif d.get("description"):
                parts.append(str(d["description"])[:160])
        except Exception:
            pass
    return " · ".join(parts) if parts else "a Shopify DTC store (category unknown)"


@router.post("/signals/interpret")
@safe_read("POST /market/signals/interpret", {"data": {"interpretations": {}}})
def interpret_signals(body: InterpretRequest, user_id: str = Depends(get_effective_user_id)):
    settings = get_settings()
    # Bound the list server-side (never trust the client) and cap per-user rate.
    signals = (body.signals or [])[:max(1, settings.ai_max_signals)]
    if not signals or not settings.anthropic_api_key:
        return {"data": {"interpretations": {}}}

    allowed, _ = check_rate_limit("ai_interpret", user_id, settings.ai_ratelimit_interpret_per_hour, 3600)
    if not allowed:
        # Friendly degrade — the deterministic copy already renders client-side.
        return {"data": {"interpretations": {}, "rate_limited": True}}

    db = get_supabase()
    ctx = _user_market_context(db, user_id)

    lines = []
    for s in signals:
        who = ", ".join(
            f"{m.hostname}" + (f" ({m.label})" if m.label else "")
            for m in (s.members or [])[:6]
        ) or f"{s.competitor_count} competitors"
        lines.append(
            f'- id "{s.id}": {s.competitor_count} competitors — {s.headline or "market movement"}. '
            f'What we detected: {s.what_happened or "coordinated activity"}. Who moved: {who}.'
        )
    signals_block = "\n".join(lines)

    prompt = f"""You are StoreScout, a competitive-intelligence strategist advising a Shopify store owner. Below are MARKET SIGNALS — moves several of their competitors made at the same time. Rewrite each one so it is specific to THIS owner's business and category, not generic.

{UNTRUSTED_DATA_NOTE}

THE OWNER'S BUSINESS: {ctx}

MARKET SIGNALS (each has an id):
{signals_block}

For EACH signal, write three fields, grounded only in what's stated — never invent numbers or events:
- what_happened: one crisp sentence naming the market condition (not a list of stores).
- why_it_matters: 1-2 sentences on what this condition means for THIS owner's category and price lane specifically — the interpretation a sharp operator would give.
- your_move: one specific, category-aware action the owner should take this week. Concrete, not "run ads" — say what and why.

Talk like a smart operator, no fluff, no "as an AI". Return ONLY JSON:
{{"interpretations": {{"<id>": {{"what_happened": "...", "why_it_matters": "...", "your_move": "..."}}}}}}"""

    # Collapse duplicate simultaneous requests for the same signal set.
    df_key = dedupe_key(user_id, "|".join(sorted(s.id for s in signals)))
    with single_flight("ai_interpret", df_key, ttl_s=30) as fresh:
        if not fresh:
            return {"data": {"interpretations": {}, "in_flight": True}}
        res = call_claude(
            "market_interpret", prompt,
            model="claude-haiku-4-5-20251001", max_tokens=900,
            user_id=user_id,
        )
    if not res.ok:
        return {"data": {"interpretations": {}}}
    p = parse_json(res.text) or {}
    raw = p.get("interpretations") or {}
    valid_ids = {s.id for s in signals}
    out = {}
    for sid, v in raw.items():
        if sid in valid_ids and isinstance(v, dict) and v.get("why_it_matters"):
            out[sid] = {
                "what_happened": str(v.get("what_happened") or "")[:280],
                "why_it_matters": str(v.get("why_it_matters") or "")[:500],
                "your_move": str(v.get("your_move") or "")[:400],
            }
    return {"data": {"interpretations": out}}
