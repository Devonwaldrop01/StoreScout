"""
Integration catalog — the ecosystem StoreScout can learn from.

This is the source of truth for the Integrations Hub. Every integration is
framed as "here's what StoreScout learns and what gets smarter" — not "connect
an API". Each entry declares which intelligence DIMENSIONS it feeds, so the hub
can render a live intelligence map that shows what the product already
understands and what connecting the next tool would unlock.

Connection state is layered on at request time from the user's real
integrations; the catalog itself is static and dependency-free.
"""
from __future__ import annotations

from typing import Any, Dict, List

# The five dimensions of business understanding the map visualizes.
DIMENSIONS = ["competitor", "business", "marketing", "customer", "operational"]
DIMENSION_LABELS = {
    "competitor": "Competitor Intelligence",
    "business": "Business Intelligence",
    "marketing": "Marketing Intelligence",
    "customer": "Customer Intelligence",
    "operational": "Operational Intelligence",
}

# Categories (ordered) — the hub's tabs.
CATEGORIES = [
    ("store", "Store Platform"),
    ("email", "Email Marketing"),
    ("ads", "Paid Advertising"),
    ("analytics", "Analytics"),
    ("reviews", "Reviews & Social Proof"),
    ("sms", "SMS Marketing"),
    ("loyalty", "Loyalty & Rewards"),
    ("support", "Customer Support"),
    ("subscriptions", "Subscriptions"),
    ("shipping", "Shipping & Fulfillment"),
    ("finance", "Accounting & Finance"),
    ("ai", "AI & Productivity"),
]


def _i(id, name, category, dims, learns, gets_better, capabilities, status="available"):
    return {
        "id": id, "name": name, "category": category,
        "dimensions": dims,                 # which intelligence dimensions it feeds
        "learns": learns,                   # what StoreScout learns
        "gets_better": gets_better,         # how recommendations improve
        "capabilities": capabilities,       # new capabilities unlocked
        "status": status,                   # available | connected | coming_soon (overridden at runtime)
    }


# id → catalog entry. `status` here is the DEFAULT; real state is layered in.
CATALOG: List[Dict[str, Any]] = [
    # ── Store platform ──
    _i("shopify", "Shopify", "store", ["business"],
       ["Your catalog, pricing, and collections", "Your orders and product performance", "Your inventory levels"],
       "Recommendations compare their catalog to YOURS — assortment gaps, products to defend, pricing openings become specific to your business.",
       ["Personalized Playbooks", "Catalog gap detection", "Price-opportunity scoring"], status="available"),
    _i("woocommerce", "WooCommerce", "store", ["business"],
       ["Your catalog and pricing"], "Same business-level personalization for non-Shopify stores.",
       ["Personalized Playbooks"], status="coming_soon"),
    _i("bigcommerce", "BigCommerce", "store", ["business"],
       ["Your catalog and pricing"], "Business-level personalization for BigCommerce.",
       ["Personalized Playbooks"], status="coming_soon"),
    # ── Email ──
    _i("klaviyo", "Klaviyo", "email", ["marketing", "customer"],
       ["Your segments and list size", "Campaign and flow performance", "Repeat-purchase behavior"],
       "Playbook execution becomes exact — the right segment, subject lines, estimated audience, and timing instead of 'email your customers'.",
       ["Segment-level execution", "Draft campaigns", "Retention insights"], status="available"),
    _i("omnisend", "Omnisend", "email", ["marketing"],
       ["Segments and campaign performance"], "Personalized email execution paths.",
       ["Segment-level execution"], status="coming_soon"),
    _i("mailchimp", "Mailchimp", "email", ["marketing"],
       ["Audiences and campaign metrics"], "Email execution tied to your real audiences.",
       ["Audience-level execution"], status="coming_soon"),
    _i("brevo", "Brevo", "email", ["marketing"],
       ["Contacts and campaign metrics"], "Email execution tied to your lists.",
       ["List-level execution"], status="coming_soon"),
    # ── Ads ──
    _i("meta_ads", "Meta Ads", "ads", ["marketing"],
       ["Ad spend, ROAS, and audiences", "Which creatives convert"],
       "StoreScout can tie competitor moves to your acquisition costs and recommend where to shift budget.",
       ["Spend-aware recommendations", "Creative angles from competitor moves"], status="coming_soon"),
    _i("google_ads", "Google Ads", "ads", ["marketing"],
       ["Search spend and keyword performance"], "Recommendations reference the terms you actually bid on.",
       ["Keyword-aware recommendations"], status="coming_soon"),
    _i("tiktok_ads", "TikTok Ads", "ads", ["marketing"],
       ["Spend and creative performance"], "Social acquisition tied to competitor trends.",
       ["Trend-aware recommendations"], status="coming_soon"),
    _i("pinterest_ads", "Pinterest Ads", "ads", ["marketing"],
       ["Spend and performance"], "Visual-discovery acquisition insight.",
       ["Channel-aware recommendations"], status="coming_soon"),
    # ── Analytics ──
    _i("ga4", "Google Analytics 4", "analytics", ["marketing", "business"],
       ["Traffic sources and volume", "Landing pages and bounce", "Conversion funnels"],
       "Playbooks become tied to REAL traffic — StoreScout can spot competitor moves that correlate with changes in your own traffic.",
       ["Traffic-correlated insights", "Better predictions", "Funnel-aware recommendations"], status="available"),
    _i("gsc", "Google Search Console", "analytics", ["marketing"],
       ["Search queries and rankings", "Impressions and CTR"],
       "SEO recommendations reference the queries you already rank (or nearly rank) for.",
       ["SEO opportunity detection", "Query-level content ideas"], status="available"),
    _i("clarity", "Microsoft Clarity", "analytics", ["customer"],
       ["Session recordings and heatmaps"], "UX-level recommendations grounded in real behavior.",
       ["Behavior-aware CX advice"], status="coming_soon"),
    _i("hotjar", "Hotjar", "analytics", ["customer"],
       ["Heatmaps and feedback"], "Conversion advice grounded in on-site behavior.",
       ["Behavior-aware CX advice"], status="coming_soon"),
    # ── Reviews ──
    _i("judgeme", "Judge.me", "reviews", ["customer"],
       ["Review volume and sentiment", "Which products delight or disappoint"],
       "Product-strategy and defense recommendations weigh what customers actually say.",
       ["Sentiment-aware product strategy"], status="coming_soon"),
    _i("loox", "Loox", "reviews", ["customer"],
       ["Photo reviews and ratings"], "Social-proof-aware merchandising advice.",
       ["Sentiment-aware recommendations"], status="coming_soon"),
    _i("yotpo", "Yotpo", "reviews", ["customer"],
       ["Reviews, ratings, and UGC"], "Customer-voice-informed product strategy.",
       ["Sentiment-aware recommendations"], status="coming_soon"),
    _i("stamped", "Stamped.io", "reviews", ["customer"],
       ["Reviews and loyalty signals"], "Customer-voice-informed recommendations.",
       ["Sentiment-aware recommendations"], status="coming_soon"),
    # ── SMS ──
    _i("postscript", "Postscript", "sms", ["marketing"],
       ["SMS subscribers and campaign performance"], "SMS execution paths tied to your real list.",
       ["Segment-level SMS execution"], status="coming_soon"),
    _i("attentive", "Attentive", "sms", ["marketing"],
       ["SMS audience and performance"], "SMS execution tied to your audience.",
       ["Segment-level SMS execution"], status="coming_soon"),
    # ── Loyalty ──
    _i("smile", "Smile.io", "loyalty", ["customer"],
       ["Loyalty membership and redemption"], "Retention recommendations tied to your loyalty program.",
       ["Loyalty-aware retention advice"], status="coming_soon"),
    _i("loyaltylion", "LoyaltyLion", "loyalty", ["customer"],
       ["Loyalty and referral activity"], "Retention advice grounded in real loyalty data.",
       ["Loyalty-aware retention advice"], status="coming_soon"),
    # ── Support ──
    _i("gorgias", "Gorgias", "support", ["customer"],
       ["Support volume and common issues"], "CX and product recommendations weigh real support themes.",
       ["Issue-aware CX advice"], status="coming_soon"),
    _i("zendesk", "Zendesk", "support", ["customer"],
       ["Ticket volume and themes"], "CX recommendations grounded in support data.",
       ["Issue-aware CX advice"], status="coming_soon"),
    # ── Subscriptions ──
    _i("recharge", "Recharge", "subscriptions", ["customer", "business"],
       ["Subscription revenue and churn", "Recurring product mix"],
       "Retention and AOV recommendations account for your recurring revenue base.",
       ["Churn-aware retention advice", "LTV-aware recommendations"], status="coming_soon"),
    # ── Shipping ──
    _i("shipstation", "ShipStation", "shipping", ["operational"],
       ["Fulfillment speed and shipping cost"], "Operational recommendations weigh your fulfillment economics.",
       ["Fulfillment-aware advice"], status="coming_soon"),
    _i("shipbob", "ShipBob", "shipping", ["operational"],
       ["Fulfillment and inventory distribution"], "Inventory and ops advice grounded in fulfillment data.",
       ["Fulfillment-aware advice"], status="coming_soon"),
    # ── Finance ──
    _i("quickbooks", "QuickBooks", "finance", ["operational", "business"],
       ["Margins and cost of goods"], "Pricing and margin recommendations use your REAL margins, not estimates.",
       ["Margin-aware pricing advice"], status="coming_soon"),
    _i("xero", "Xero", "finance", ["operational", "business"],
       ["Margins and financials"], "Margin-aware pricing and profitability advice.",
       ["Margin-aware pricing advice"], status="coming_soon"),
    # ── AI & productivity ──
    _i("slack", "Slack", "ai", ["operational"],
       ["Where your team works"], "Push StoreScout alerts and briefs into your team's flow.",
       ["Alerts in Slack"], status="coming_soon"),
    _i("notion", "Notion", "ai", ["operational"],
       ["Your docs workspace"], "Export playbooks and briefs to your workspace.",
       ["Playbook export"], status="coming_soon"),
]

CATALOG_BY_ID = {e["id"]: e for e in CATALOG}


def build_hub(connected_ids: List[str]) -> Dict[str, Any]:
    """Layer the user's real connection state onto the catalog and compute the
    intelligence map. `connected_ids` are integration ids the user has wired."""
    connected = set(connected_ids)
    items = []
    for e in CATALOG:
        entry = dict(e)
        if e["id"] in connected:
            entry["status"] = "connected"
        items.append(entry)

    # Intelligence map: each dimension's fill reflects how much feeds it.
    # Competitor is always full (StoreScout's base capability from scanning).
    dim_feeders: Dict[str, List[dict]] = {d: [] for d in DIMENSIONS}
    for e in CATALOG:
        for d in e["dimensions"]:
            dim_feeders[d].append(e)

    intelligence: List[Dict[str, Any]] = []
    for d in DIMENSIONS:
        if d == "competitor":
            pct = 100
            connected_here = 1
            total_here = 1
        else:
            feeders = dim_feeders[d]
            total_here = len(feeders)
            connected_here = sum(1 for f in feeders if f["id"] in connected)
            # A single strong connection already lights the dimension meaningfully.
            pct = 0 if total_here == 0 else min(100, round(100 * connected_here / total_here))
            if connected_here and pct < 20:
                pct = 20
        intelligence.append({
            "key": d, "label": DIMENSION_LABELS[d],
            "pct": pct, "connected": connected_here, "total": total_here,
        })

    categories = [{"key": k, "label": label,
                   "count": sum(1 for e in CATALOG if e["category"] == k)} for k, label in CATEGORIES]

    return {
        "categories": categories,
        "integrations": items,
        "intelligence": intelligence,
        "connected_count": len(connected),
    }
