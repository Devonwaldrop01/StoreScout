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

# Marketing-tech categories that prove a store SPENDS on growth — the single
# strongest predictor that they'll pay for another growth tool.
_SPEND_POINTS = {
    "paid_ads": 8,          # running Meta/Google/TikTok ads — budget + competitive
    "email_marketing": 6,   # Klaviyo etc. — invests in retention/marketing SaaS
    "sms_marketing": 3,
    "reviews": 3,           # paid reviews app — cares about conversion
    "subscriptions": 3,
    "email_capture": 2,
    "upsell": 2,
    "support": 2,
}


def _tech_category(sig: str) -> Optional[str]:
    for _marker, key_cat in (
        ("klaviyo", "email_marketing"), ("attentive", "sms_marketing"), ("postscript", "sms_marketing"),
        ("meta_pixel", "paid_ads"), ("tiktok_pixel", "paid_ads"), ("google_ads", "paid_ads"),
        ("linkedin_pixel", "paid_ads"), ("gtm", "analytics"),
        ("judgeme", "reviews"), ("yotpo", "reviews"), ("stamped", "reviews"), ("loox", "reviews"),
        ("okendo", "reviews"), ("reviewsio", "reviews"),
        ("recharge", "subscriptions"), ("appstle", "subscriptions"), ("seal", "subscriptions"),
        ("gorgias", "support"), ("intercom", "support"), ("tidio", "support"), ("zendesk", "support"),
        ("privy", "email_capture"), ("justuno", "email_capture"), ("optinmonster", "email_capture"),
        ("rebuy", "upsell"), ("zipify", "upsell"), ("aftersell", "upsell"), ("bold", "upsell"),
    ):
        if sig == _marker:
            return key_cat
    return None


def score_lead_fit(db, store: Dict[str, Any], research: Dict[str, Any]) -> Dict[str, Any]:
    """
    First-principles fit scoring — likelihood to BUY, not "interesting store".
    Weighted 0–100 → Hot / Warm / Cold / Not a Fit, with a per-factor breakdown
    and hard gates. Every factor is recorded so the verdict is auditable.
    """
    breakdown: List[dict] = []
    reasons: List[str] = []
    disqualifiers: List[str] = []
    gated = False

    def add(factor: str, pts: int, note: str):
        breakdown.append({"factor": factor, "points": pts, "note": note})
        if pts > 0:
            reasons.append(note)
        elif pts < 0:
            disqualifiers.append(note)

    # ── Hard gates ────────────────────────────────────────────────────────
    stage = store.get("business_stage")
    pc = store.get("product_count")
    if stage == "enterprise":
        gated = True
        disqualifiers.append("Enterprise-scale — has an in-house team and won't buy a lean tool cold")
    if pc is not None and pc < 5:
        gated = True
        disqualifiers.append(f"Near-empty catalog ({pc}) — inactive or under construction")
    if store.get("sells_wholesale") and not (store.get("promo_rate")):
        disqualifiers.append("Wholesale/B2B posture — competitive-pricing intel matters less")

    # ── Weighted factors ──────────────────────────────────────────────────
    # 1. Spends on marketing/SaaS (22) — strongest buy signal.
    tech = store.get("tech_signals") or []
    cats = {c for c in (_tech_category(t) for t in tech) if c}
    spend = min(22, sum(_SPEND_POINTS.get(c, 0) for c in cats))
    if spend:
        pretty = ", ".join(sorted(cats & set(_SPEND_POINTS)))
        add("marketing_spend", spend, f"Already pays for growth tools ({pretty}) — proven SaaS budget")
    else:
        add("marketing_spend", 0, "No paid marketing stack detected — unproven budget")

    # 2. Maturity fit (20).
    if stage == "growing":
        add("maturity", 20, "Growing brand — budget + competitive urgency, StoreScout's sweet spot")
    elif stage == "established":
        add("maturity", 14, "Established independent brand")
    elif stage == "startup":
        add("maturity", -8, "Very early — limited budget and competitive urgency")
    elif stage == "enterprise":
        add("maturity", -40, "Enterprise scale")

    # 3. Active price competition (14).
    promo = store.get("promo_rate") or 0
    if promo >= 25:
        add("price_competition", 14, f"Aggressive promo cadence ({promo:.0f}%) — pricing is a live battle")
    elif promo >= 10:
        add("price_competition", 9, f"Runs regular promotions ({promo:.0f}%)")
    elif promo > 0:
        add("price_competition", 4, "Some discounting — price-aware")

    # 4. Competitive niche density (14).
    n = research.get("competitors_found", 0)
    if n >= 8:
        add("niche_density", 14, f"Dense niche — {n} verified rivals indexed, instant value to show")
    elif n >= 4:
        add("niche_density", 10, f"Competitive market — {n} verified rivals indexed")
    elif n >= 2:
        add("niche_density", 6, f"{n} verified rivals indexed")
    elif n == 1:
        add("niche_density", 2, "1 verified rival indexed")
    else:
        add("niche_density", -8, "No verified rivals yet — the demo would feel empty")

    # 5. Brand sophistication (12) — set by AI later; neutral placeholder here.
    #    (assess_fit_ai can add up to +12 or flag a downgrade.)

    # 6. DTC purity (8).
    if store.get("sells_wholesale"):
        add("dtc_purity", -6, "Signals wholesale/B2B — mixed model")
    else:
        add("dtc_purity", 8, "Pure DTC — owns its storefront and pricing")

    # 7. International presence (informational, small).
    if store.get("multi_market"):
        add("international", 3, "Multi-market storefront — scaling operation")

    # 8. Contactability (4 + gate on outreach).
    email = store.get("contact_email")
    if email:
        pts = 4 if (store.get("contact_source") == "mailto") else 3
        add("contactability", pts, f"Reachable — {email}")
    else:
        add("contactability", 0, "No contact email found yet — outreach blocked until one is")

    base = 40  # neutral midpoint so the weighted deltas land sensibly
    score = base + sum(b["points"] for b in breakdown)

    # Outcome feedback (bounded) — categories that already produced customers.
    adj, adj_reason = category_outcome_adjustment(db, store.get("category"))
    if adj:
        add("outcome_feedback", adj, adj_reason or "category outcome adjustment")
        score += adj

    score = max(0, min(100, score))

    # ── Tier ──────────────────────────────────────────────────────────────
    if gated:
        tier = "not_a_fit"
        score = min(score, 30)
    elif score >= 75:
        tier = "hot"
    elif score >= 55:
        tier = "warm"
    elif score >= 35:
        tier = "cold"
    else:
        tier = "not_a_fit"

    # No contact caps outreach usefulness — never let it be Hot.
    if not email and tier == "hot":
        tier = "warm"
        disqualifiers.append("Downgraded from Hot: no contact email yet")

    return {
        "fit_score": score,
        "fit_tier": tier,
        "score_breakdown": breakdown,
        "score_reasons": reasons,
        "disqualifiers": disqualifiers,
        # Back-compat with the existing schema/columns:
        "qualification_score": score,
        "lead_score": score,
    }


def assess_fit_ai(store: Dict[str, Any], research: Dict[str, Any]) -> Dict[str, Any]:
    """One individualized verdict: would THIS specific store buy StoreScout?
    Returns {reasoning, sophistication_points (0-12), disqualify: bool}.
    Grounded in real signals; the model may flag a hard disqualifier the
    heuristics missed (e.g. an obvious dropshipper or a giant brand)."""
    import json as _json
    import anthropic
    from app.core.config import get_settings
    settings = get_settings()
    if not settings.anthropic_api_key:
        return {"reasoning": None, "sophistication_points": 5, "disqualify": False}

    tech = ", ".join(store.get("tech_signals") or []) or "none detected"
    facts = "\n".join(f"- {f}" for f in (research.get("findings") or [])) or "- (no market findings)"
    prompt = f"""StoreScout is a competitor price/product intelligence tool for Shopify DTC brands. You are qualifying a lead — judge ONLY likelihood to BUY, not whether they're a nice store.

Store: {store.get('brand_name') or store['domain']} ({store['domain']})
Category: {store.get('category') or '?'} · stage: {store.get('business_stage') or '?'} · ~{store.get('product_count') or '?'} products · median ${store.get('median_price') or '?'} · promo rate {store.get('promo_rate') or 0}%
Marketing/SaaS stack detected: {tech}
Market findings:
{facts}

Return ONLY JSON:
{{"reasoning": "<2-3 sentences: would THIS store realistically buy StoreScout, and why or why not? Be skeptical and specific.>",
  "sophistication": <0-12 integer: brand/operation sophistication & budget signal>,
  "disqualify": <true only if clearly a poor fit: enterprise with its own team, pure dropshipper, dead store, or B2B/wholesale-only>}}"""
    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=280,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        p = _json.loads(text)
        return {
            "reasoning": str(p.get("reasoning") or "")[:600] or None,
            "sophistication_points": max(0, min(12, int(p.get("sophistication") or 0))),
            "disqualify": bool(p.get("disqualify")),
        }
    except Exception as exc:
        logger.debug("assess_fit_ai failed for %s: %s", store.get("domain"), exc)
        return {"reasoning": None, "sophistication_points": 5, "disqualify": False}


# Back-compat shim — old callers used qualify_and_score.
def qualify_and_score(db, store: Dict[str, Any], research: Dict[str, Any]) -> Dict[str, Any]:
    return score_lead_fit(db, store, research)


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
