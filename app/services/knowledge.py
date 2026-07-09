"""
The StoreScout brain — business knowledge organized by category.

Integrations are not APIs to StoreScout; they are knowledge sources. The
product never asks "what integrations does this user have?" — it asks
"what do I currently know about this business?". This module is the single
answer to that question:

  · build_business_knowledge(user_id) — the full picture: per-source
    connection state, what StoreScout understands from each, what
    connecting would unlock (phrased as outcomes, never as APIs), a
    Business Understanding score (how well StoreScout knows the business —
    NOT a business health score), and the recommendation depth tier.
  · build_ai_context(user_id) — the adaptive prompt context every AI task
    should use. Depth follows knowledge: no sources → strategic advice;
    +store → operational (real products/pricing); +Klaviyo → customer
    segments; +GA4/GSC → traffic and search intelligence.

Future sources plug into the same categories — the recommendation engine
depends on knowledge, not on specific providers.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Understanding-score weights: how much each source teaches StoreScout.
# Sums to 100 when everything is connected and history has accumulated.
_WEIGHTS = {
    "competitors": 20,   # Competitor Intelligence — tracking at least one rival
    "my_store": 20,      # Store Intelligence — public catalog of their own store
    "shopify_admin": 15, # Store Intelligence (private) — true inventory + discounts
    "ga4": 15,           # Marketing Intelligence — traffic + conversion
    "gsc": 10,           # Search Intelligence — queries + rankings
    "klaviyo": 15,       # Customer Intelligence — segments + email
    "history": 5,        # Historical Intelligence — scan depth over time
}


def build_business_knowledge(user_id: str) -> Dict[str, Any]:
    from app.core.database import get_supabase
    db = get_supabase()

    # ── Gather raw connection state (each guarded — a missing table or a
    # failed call reads as "not connected", never a crash) ────────────────
    competitors_n = 0
    scans_n = 0
    try:
        comp = db.table("competitors").select("id", count="exact")\
            .eq("user_id", user_id).eq("is_active", True).eq("is_my_store", False).execute()
        competitors_n = comp.count or 0
    except Exception:
        pass

    my_store: Optional[dict] = None
    my_snap: Optional[dict] = None
    try:
        ms = db.table("competitors").select("id, hostname, product_count")\
            .eq("user_id", user_id).eq("is_my_store", True).maybe_single().execute()
        my_store = ms.data if ms else None
        if my_store:
            snap = db.table("scan_snapshots").select("median_price, promo_rate, product_count")\
                .eq("competitor_id", my_store["id"]).order("scanned_at", desc=True).limit(1).execute()
            my_snap = (snap.data or [None])[0]
    except Exception:
        pass

    shopify_admin = False
    shopify_shop = None
    try:
        sc = db.table("shopify_connections").select("shop, updated_at")\
            .eq("user_id", user_id).is_("uninstalled_at", "null").maybe_single().execute()
        if sc and sc.data:
            shopify_admin = True
            shopify_shop = sc.data.get("shop")
    except Exception:
        pass

    integ: dict = {}
    try:
        row = db.table("user_integrations").select("*").eq("user_id", user_id).maybe_single().execute()
        integ = (row.data or {}) if row else {}
    except Exception:
        pass
    ga4 = bool(integ.get("google_access_token") and integ.get("google_ga4_property_id"))
    gsc = bool(integ.get("google_access_token") and integ.get("google_gsc_site_url"))
    klaviyo = bool(integ.get("klaviyo_api_key"))

    try:
        if competitors_n:
            ids = db.table("competitors").select("id").eq("user_id", user_id)\
                .eq("is_active", True).eq("is_my_store", False).execute()
            comp_ids = [c["id"] for c in (ids.data or [])]
            if comp_ids:
                sn = db.table("scan_snapshots").select("id", count="exact")\
                    .in_("competitor_id", comp_ids).execute()
                scans_n = sn.count or 0
    except Exception:
        pass

    # ── Score ──────────────────────────────────────────────────────────────
    score = 0
    if competitors_n:
        score += _WEIGHTS["competitors"]
    if my_store:
        score += _WEIGHTS["my_store"]
    if shopify_admin:
        score += _WEIGHTS["shopify_admin"]
    if ga4:
        score += _WEIGHTS["ga4"]
    if gsc:
        score += _WEIGHTS["gsc"]
    if klaviyo:
        score += _WEIGHTS["klaviyo"]
    if scans_n >= 7:
        score += _WEIGHTS["history"]
    elif scans_n >= 2:
        score += 2

    # ── Depth tier — how personal recommendations can get ─────────────────
    if (my_store or shopify_admin) and klaviyo and (ga4 or gsc):
        depth_tier = "full"          # traffic/SEO-aware, segment-aware, operational
    elif (my_store or shopify_admin) and klaviyo:
        depth_tier = "customer"      # segments, audiences, lifecycle timing
    elif my_store or shopify_admin:
        depth_tier = "operational"   # references real products/inventory/pricing
    else:
        depth_tier = "strategic"     # market-level advice, honest about limits

    # ── Per-source panels (outcome copy, never API copy) ──────────────────
    def _store_facts() -> List[str]:
        facts = []
        if my_store:
            facts.append("Products & catalog")
            if my_snap and my_snap.get("median_price") is not None:
                facts.append("Pricing")
            if my_snap and my_snap.get("promo_rate") is not None:
                facts.append("Promotions")
        if shopify_admin:
            facts.extend(["True inventory levels", "Active discount rules"])
        return facts

    sources = [
        {
            "key": "store",
            "name": "Your store",
            "category": "Store Intelligence",
            "connected": bool(my_store or shopify_admin),
            "detail": shopify_shop or (my_store or {}).get("hostname"),
            "understands": _store_facts(),
            "unlocks": [
                "Personalized competitor comparisons",
                "Recommendations that reference YOUR products and inventory",
                "Pricing advice anchored to your actual price points",
            ],
        },
        {
            "key": "ga4",
            "name": "Google Analytics",
            "category": "Marketing Intelligence",
            "connected": ga4,
            "detail": integ.get("google_ga4_property_id"),
            "understands": ["Traffic", "Conversion signals", "Landing pages"] if ga4 else [],
            "unlocks": [
                "See how competitor moves affect your traffic",
                "Recommendations weighted by what actually converts for you",
            ],
        },
        {
            "key": "gsc",
            "name": "Search Console",
            "category": "Search Intelligence",
            "connected": gsc,
            "detail": integ.get("google_gsc_site_url"),
            "understands": ["Search queries", "Rankings", "Click-through"] if gsc else [],
            "unlocks": [
                "Spot search demand competitors are capturing before you",
                "SEO plays tied to real query data",
            ],
        },
        {
            "key": "klaviyo",
            "name": "Klaviyo",
            "category": "Customer Intelligence",
            "connected": klaviyo,
            "detail": None,
            "understands": ["Audience size", "Email program"] if klaviyo else [],
            "unlocks": [
                "Campaign timing that counters competitor promos",
                "Plays that name the segment to email and when",
            ],
        },
    ]

    understood: List[str] = []
    if competitors_n:
        understood.append(f"Competitors ({competitors_n} tracked)")
    for s in sources:
        if s["connected"]:
            understood.extend(s["understands"])
    if scans_n >= 2:
        understood.append(f"History ({scans_n} scans)")

    missing = [
        {"name": s["name"], "unlock": s["unlocks"][0]}
        for s in sources if not s["connected"]
    ]
    if not competitors_n:
        missing.insert(0, {"name": "Competitors", "unlock": "Track a rival to start building competitive intelligence"})

    return {
        "understanding_score": min(100, score),
        "depth_tier": depth_tier,
        "sources": sources,
        "understood": understood,
        "missing": missing,
        "competitors_tracked": competitors_n,
        "scan_history": scans_n,
    }


def build_ai_context(user_id: str) -> str:
    """
    The adaptive prompt context — recommendations deepen with knowledge.
    Reuses the per-provider context builders and states the depth tier
    explicitly so the model knows HOW personal it may get (and instructs it
    to stay strategic + honest when knowledge is thin).
    """
    parts: List[str] = []
    try:
        from app.api.v1.integrations import get_klaviyo_context, get_google_context, get_shopify_context
        for fn in (get_shopify_context, get_klaviyo_context, get_google_context):
            try:
                ctx = fn(user_id)
                if ctx:
                    parts.append(ctx)
            except Exception as exc:
                logger.debug("knowledge context builder %s failed: %s", getattr(fn, "__name__", "?"), exc)
    except Exception:
        pass

    try:
        knowledge = build_business_knowledge(user_id)
        tier = knowledge["depth_tier"]
    except Exception:
        tier = "strategic"

    guidance = {
        "strategic": "No client business data is connected — keep recommendations strategic and educational; never invent client specifics, and note once that connecting their store sharpens advice.",
        "operational": "Client store data is connected — make recommendations operational: reference their actual catalog, pricing, and inventory.",
        "customer": "Client store + email platform are connected — include customer segments, audiences, and campaign timing in recommendations.",
        "full": "Client store, email, and web analytics are connected — recommendations may reference traffic impact, landing pages, SEO opportunities, and segments.",
    }[tier]

    # The onboarding business profile — what they told us they sell, who
    # they serve, and what they came here to do. Makes recommendations speak
    # to their actual business even before any integration is connected.
    try:
        from app.core.database import get_supabase
        prof = get_supabase().table("business_profiles").select(
            "category, price_range, target_customer, primary_goal, sells"
        ).eq("user_id", user_id).maybe_single().execute()
        p = (prof and prof.data) or {}
        bits = []
        if p.get("category"):
            bits.append(f"sells {p['category']}")
        if p.get("price_range"):
            bits.append(f"{p['price_range']} pricing")
        if p.get("target_customer"):
            bits.append(f"targets {p['target_customer']}")
        if p.get("sells"):
            bits.append(p["sells"][:160])
        goal_map = {
            "pricing": "Their priority is PRICE MONITORING — lead with pricing moves and margin plays.",
            "gaps": "Their priority is PRODUCT GAPS — lead with catalog openings and what to add.",
            "launches": "Their priority is LAUNCHES — lead with new-product signals and timing.",
            "plays": "Their priority is ADS/EMAIL PLAYS — lead with campaign and messaging angles.",
            "monitoring": "Their priority is general monitoring — keep it broad.",
        }
        if bits:
            parts.insert(0, "CLIENT BUSINESS: " + ", ".join(bits) + ".")
        if p.get("primary_goal") in goal_map:
            parts.insert(0, goal_map[p["primary_goal"]])
    except Exception as exc:
        logger.debug("business profile context skipped: %s", exc)

    header = f"KNOWLEDGE DEPTH: {tier}. {guidance}"
    return "\n".join([header] + parts) if parts else header
