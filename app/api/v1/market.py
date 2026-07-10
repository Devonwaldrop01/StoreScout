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

import json as _json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_effective_user_id
from app.core.config import get_settings
from app.core.database import get_supabase
from app.core.obs import safe_read

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
    signals = (body.signals or [])[:6]
    if not signals or not settings.anthropic_api_key:
        return {"data": {"interpretations": {}}}

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

THE OWNER'S BUSINESS: {ctx}

MARKET SIGNALS (each has an id):
{signals_block}

For EACH signal, write three fields, grounded only in what's stated — never invent numbers or events:
- what_happened: one crisp sentence naming the market condition (not a list of stores).
- why_it_matters: 1-2 sentences on what this condition means for THIS owner's category and price lane specifically — the interpretation a sharp operator would give.
- your_move: one specific, category-aware action the owner should take this week. Concrete, not "run ads" — say what and why.

Talk like a smart operator, no fluff, no "as an AI". Return ONLY JSON:
{{"interpretations": {{"<id>": {{"what_happened": "...", "why_it_matters": "...", "your_move": "..."}}}}}}"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=900,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        p = _json.loads(text)
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
    except Exception as exc:
        logger.warning("market signal interpret failed: %s", exc)
        return {"data": {"interpretations": {}}}
