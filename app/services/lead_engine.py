"""
Internal Lead Discovery Engine — growth tooling, never customer-facing.

Answers one question: "If I only have time to contact 20 businesses today,
which 20 give StoreScout the highest probability of creating value and
starting meaningful conversations?"

Everything here builds on intelligence StoreScout already has:
  · verified stores, market context, and the competitor neighborhood come
    from shopify_store_index (zero new store requests)
  · every scoring reason is stored, so the model stays auditable
  · outcomes (customer / lost / never_contact) feed back into scoring via a
    simple per-category adjustment — the architecture seam for learning,
    deliberately NOT machine learning yet
  · outreach angles are grounded in computed findings only — the generator
    is instructed to never invent observations, and it only ever sees facts
    this module derived from real index data
"""
from __future__ import annotations

import logging
import statistics
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

QUALIFICATION_BASE = 50


# ── Research (index-only — no network) ─────────────────────────────────────

def research_prospect(db, store: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lightweight pre-outreach research from the store index alone.
    Returns {competitors: [{domain, brand_name, ...}], findings: [str],
             market: {...}, competitors_found: int}.
    Every finding is computed from real rows — nothing speculative.
    """
    domain = store["domain"]
    category = store.get("category")
    findings: List[str] = []
    competitors: List[dict] = []
    market: Dict[str, Any] = {}

    if category and category != "Other":
        try:
            res = db.table("shopify_store_index")\
                .select("domain, brand_name, subcategory, business_stage, pricing_tier, median_price, promo_rate, product_count")\
                .eq("status", "verified")\
                .eq("category", category)\
                .neq("domain", domain)\
                .order("verification_confidence", desc=True)\
                .limit(12)\
                .execute()
            competitors = res.data or []
        except Exception as exc:
            logger.debug("lead research peer query failed for %s: %s", domain, exc)

    n = len(competitors)
    if n:
        findings.append(f"{n} verified Shopify competitor{'s' if n != 1 else ''} in {category} already in our index")

        # Peer pricing landscape
        peer_medians = [c["median_price"] for c in competitors if c.get("median_price")]
        own_median = store.get("median_price")
        if peer_medians:
            peer_mid = round(statistics.median(peer_medians), 2)
            market["peer_median_price"] = peer_mid
            if own_median and peer_mid:
                diff_pct = (own_median - peer_mid) / peer_mid * 100
                if abs(diff_pct) >= 20:
                    findings.append(
                        f"Their median price (${own_median:.0f}) sits {abs(diff_pct):.0f}% "
                        f"{'above' if diff_pct > 0 else 'below'} the {category} peer median (${peer_mid:.0f})"
                    )

        # Peer promo behavior
        promo_peers = [c for c in competitors if (c.get("promo_rate") or 0) >= 20]
        if len(promo_peers) >= 2:
            names = ", ".join((c.get("brand_name") or c["domain"]) for c in promo_peers[:3])
            findings.append(
                f"{len(promo_peers)} of {n} competitors are running significant promotions right now (e.g. {names})"
            )
        peer_promos = [c["promo_rate"] for c in competitors if c.get("promo_rate") is not None]
        own_promo = store.get("promo_rate")
        if peer_promos and own_promo is not None:
            avg_peer = sum(peer_promos) / len(peer_promos)
            market["peer_avg_promo_rate"] = round(avg_peer, 1)
            if avg_peer - own_promo >= 15:
                findings.append(
                    f"Competitors discount {avg_peer:.0f}% of their catalogs on average vs their {own_promo:.0f}% — visible pricing pressure in the niche"
                )

        # Closest peer — same subcategory + stage where possible
        same_sub = [c for c in competitors if c.get("subcategory") == store.get("subcategory")]
        closest = same_sub[0] if same_sub else competitors[0]
        market["closest_peer"] = closest.get("brand_name") or closest["domain"]
        findings.append(
            f"Closest tracked peer: {market['closest_peer']}"
            + (f" ({closest.get('business_stage')} stage, similar market)" if closest.get("business_stage") else "")
        )

    # Own-store facts worth referencing
    if store.get("product_count"):
        market["catalog_size"] = store["product_count"]
    if store.get("promo_rate") is not None:
        market["own_promo_rate"] = store["promo_rate"]

    return {
        "competitors": [
            {"domain": c["domain"], "brand_name": c.get("brand_name"),
             "business_stage": c.get("business_stage"), "pricing_tier": c.get("pricing_tier")}
            for c in competitors
        ],
        "findings": findings,
        "market": market,
        "competitors_found": n,
    }


# ── Learning seam ──────────────────────────────────────────────────────────

def category_outcome_adjustment(db, category: Optional[str]) -> Tuple[int, Optional[str]]:
    """
    Outcome feedback without ML: categories that produced customers get a
    small boost; categories full of lost/never-contact leads get dampened.
    Bounded at ±10 so heuristics stay in charge. Returns (adjustment, reason).
    """
    if not category:
        return 0, None
    try:
        res = db.table("lead_prospects")\
            .select("outreach_status")\
            .eq("category", category)\
            .in_("outreach_status", ["customer", "trial_started", "lost", "never_contact"])\
            .limit(200)\
            .execute()
        good = sum(1 for r in (res.data or []) if r["outreach_status"] in ("customer", "trial_started"))
        bad = sum(1 for r in (res.data or []) if r["outreach_status"] in ("lost", "never_contact"))
        adj = max(-10, min(10, good * 5 - bad * 2))
        if adj > 0:
            return adj, f"{category} has already produced {good} customer{'s' if good != 1 else ''}/trial{'s' if good != 1 else ''}"
        if adj < 0:
            return adj, f"{category} outreach has underperformed so far ({bad} lost/never-contact)"
    except Exception as exc:
        logger.debug("outcome adjustment skipped for %s: %s", category, exc)
    return 0, None


# ── Qualification + lead score ─────────────────────────────────────────────

def qualify_and_score(db, store: Dict[str, Any], research: Dict[str, Any]) -> Dict[str, Any]:
    """
    Qualification: would StoreScout genuinely help this business?
    Lead score: qualification + outreach-opportunity strength + outcome
    feedback. Every signal is recorded in reasons/disqualifiers.
    """
    reasons: List[str] = []
    disqualifiers: List[str] = []
    score = QUALIFICATION_BASE

    conf = store.get("verification_confidence") or 0
    if conf >= 80:
        score += 5
        reasons.append("Strongly verified Shopify storefront")
    elif conf < 60:
        score -= 10
        disqualifiers.append("Weak Shopify verification")

    stage = store.get("business_stage")
    if stage == "growing":
        score += 15
        reasons.append("Growing brand — StoreScout's sweet spot")
    elif stage == "startup":
        score += 10
        reasons.append("Startup actively finding its market")
    elif stage == "established":
        score += 5
        reasons.append("Established independent brand")
    elif stage == "enterprise":
        score -= 30
        disqualifiers.append("Enterprise-scale — unlikely to buy a lean competitor tool")

    pc = store.get("product_count")
    if pc is None:
        score -= 15
        disqualifiers.append("Catalog couldn't be sampled — StoreScout may not analyze it well")
    elif pc < 10:
        score -= 25
        disqualifiers.append(f"Very small catalog ({pc} products) — likely inactive or under construction")
    elif pc <= 800:
        score += 10
        reasons.append(f"Active, analyzable catalog ({pc} products)")

    if (store.get("promo_rate") or 0) > 0:
        score += 5
        reasons.append("Runs promotions — pricing is a live concern for them")

    n = research.get("competitors_found", 0)
    if n >= 5:
        score += 20
        reasons.append(f"Excellent competitor ecosystem — {n} verified rivals already indexed")
    elif n >= 3:
        score += 12
        reasons.append(f"Clear competitive market — {n} verified rivals indexed")
    elif n >= 1:
        score += 5
        reasons.append(f"{n} verified competitor{'s' if n != 1 else ''} indexed")
    else:
        score -= 20
        disqualifiers.append("No verified competitors in the index yet — the demo would feel empty")

    if store.get("category") and store["category"] != "Other":
        score += 5
        reasons.append(f"Clear category fit ({store['category']})")
    if store.get("pricing_tier"):
        score += 3
        reasons.append(f"{store['pricing_tier'].capitalize()} pricing tier — comparable peers exist")

    qualification = max(0, min(100, score))

    # Lead score: qualification + how strong the conversation starter is
    lead = qualification
    n_findings = len(research.get("findings") or [])
    if n_findings >= 3:
        lead += 8
        reasons.append("Multiple concrete market observations to open with")
    elif n_findings >= 1:
        lead += 4

    adj, adj_reason = category_outcome_adjustment(db, store.get("category"))
    lead += adj
    if adj_reason:
        (reasons if adj > 0 else disqualifiers).append(adj_reason)

    return {
        "qualification_score": qualification,
        "lead_score": max(0, min(100, lead)),
        "score_reasons": reasons,
        "disqualifiers": disqualifiers,
    }


# ── Outreach generation (grounded — findings in, no inventions) ────────────

def generate_outreach(store: Dict[str, Any], research: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """One genuinely interesting conversation starter + a short personal
    email draft. The model only sees findings we computed from real data and
    is instructed to use nothing else. Returns {angle, subject, email} or None."""
    import json as _json
    import anthropic
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.anthropic_api_key:
        return None

    brand = store.get("brand_name") or store["domain"]
    findings = research.get("findings") or []
    facts = "\n".join(f"- {f}" for f in findings) or "- (no notable market findings — write a soft, honest curiosity opener with NO specific claims)"

    prompt = f"""You are writing internal outreach material for StoreScout, a Shopify competitor-intelligence tool. The recipient runs {brand} ({store['domain']}), a {store.get('business_stage') or 'DTC'} {store.get('category') or 'ecommerce'} brand.

VERIFIED OBSERVATIONS (the ONLY facts you may reference — never invent, never embellish, never add numbers that aren't here):
{facts}

Write:
1. angle — one sentence: the single most interesting conversation starter from the observations.
2. subject — a short, personal, lowercase-friendly email subject (under 8 words, no clickbait, no "quick question").
3. email — 60-110 words. Personal, curious, written by a founder ({settings.lead_outreach_sender_name} from StoreScout) who genuinely looked at their market. Reference at most TWO observations. End with a soft ask (worth a look? / want me to send what we found?). No feature lists, no pricing, no "I hope this finds you well", no hype words. Sign off with just "{settings.lead_outreach_sender_name}".

Return ONLY valid JSON, no markdown fences:
{{"angle": "...", "subject": "...", "email": "..."}}"""

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = _json.loads(text)
        if parsed.get("angle") and parsed.get("email"):
            return {
                "angle": str(parsed["angle"])[:300],
                "subject": str(parsed.get("subject") or "")[:120],
                "email": str(parsed["email"])[:2000],
            }
    except Exception as exc:
        logger.warning("outreach generation failed for %s: %s", store["domain"], exc)
    return None
