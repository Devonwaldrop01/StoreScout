from __future__ import annotations
import json
import logging
import re
from datetime import datetime, timezone, timedelta

import anthropic

from .celery_app import celery
from app.core.config import get_settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a combat-ready Shopify competitive intelligence advisor. You take real competitor data and turn it into specific, 30-minute executable plays.

You know these platforms cold: Meta Ads Manager, Google Shopping, Klaviyo, Shopify admin, Alibaba, Google Analytics, TikTok Ads.

What makes a great play:
- SPECIFIC: "Go to Meta Ads Manager → Ad Sets → duplicate your best CPA ad set" not "run some ads"
- NUMBERS: dollar amounts ($10/day budget), timeframes (5-day test), success thresholds (>15% CTR lift)
- CATEGORY-AWARE: when you see product categories or tags, name them in the steps
- PRODUCT-SPECIFIC: when you see product titles, use them in your copy examples and ad suggestions
- CROSS-COMPETITOR: patterns across 2+ competitors are the highest-value output

What makes a bad play (never do these):
- "Consider adjusting your pricing strategy" — too vague
- "Monitor their social media" — not an action
- "[their main product category]" — placeholder text, not a real instruction
- Generic platform advice with no specific feature paths or budget

Your goal: each play should feel like advice from a friend who works at the competitor."""

_SECTION_PRIORITY = {"act_now": 95, "right_now": 75, "this_week": 55}
_FRESHNESS_HOURS = 23


def _extract_json(text: str) -> dict:
    """Parse JSON from Claude output, handling markdown fences gracefully."""
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip()
    cleaned = re.sub(r"\s*```", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Find the first complete JSON object
    start = cleaned.find("{")
    if start != -1:
        try:
            return json.loads(cleaned[start:])
        except json.JSONDecodeError:
            pass
    raise ValueError("No valid JSON found in Claude response")


def _format_competitor_block(comp: dict, snap: dict) -> str:
    """Build a rich per-competitor context string for Claude."""
    sd = snap.get("snapshot_data") or {}
    pricing = sd.get("pricing") or {}
    discounts = sd.get("discounts") or {}
    positioning = sd.get("positioning") or {}
    launch = sd.get("launch_timeline") or {}
    tag_analysis = sd.get("tag_analysis") or {}
    vendor_analysis = sd.get("vendor_analysis") or {}
    lists = sd.get("lists") or {}

    # Promo rate — stored as 0-100 percentage from internal scan endpoint
    promo_raw = snap.get("promo_rate")
    promo_pct = float(promo_raw) if promo_raw is not None else float(discounts.get("discounted_pct") or 0)

    median = float(snap.get("median_price") or pricing.get("median") or 0)
    p25 = float(pricing.get("p25") or 0)
    p75 = float(pricing.get("p75") or 0)
    new_30d = int(snap.get("new_30d") or 0)
    avg_disc = float(discounts.get("avg_discount_pct") or discounts.get("median_discount_pct") or 0)
    max_disc = float(discounts.get("max_discount_pct") or 0)
    market_pos = (positioning.get("market_position") or {}).get("label", "mid-market")
    vel = float((launch.get("velocity") or {}).get("last_30d") or 0)
    total = int(snap.get("product_count") or (sd.get("catalog") or {}).get("total_products") or 0)
    in_stock_pct = float((sd.get("catalog") or {}).get("in_stock_pct") or 0)

    # Product intelligence — the data that makes plays specific
    top_tags = [
        t["tag"] for t in (tag_analysis.get("top_tags") or [])[:8] if t.get("tag")
    ]
    top_vendors = [
        v["vendor"] for v in (vendor_analysis.get("top_vendors") or [])[:4] if v.get("vendor")
    ]
    newest = [
        f"\"{p['title']}\" (${p.get('price_min', 0):.0f})"
        for p in (lists.get("newest_products") or [])[:5]
        if p.get("title")
    ]
    top_discounted = [
        f"\"{p['title']}\" ({p.get('discount_pct', 0):.0f}% off, was ${p.get('compare_at_min', 0):.0f})"
        for p in (lists.get("top_discounts") or [])[:4]
        if p.get("title")
    ]
    top_priced = [
        f"\"{p['title']}\" (${p.get('price_min', 0):.0f})"
        for p in (lists.get("top_expensive") or [])[:3]
        if p.get("title")
    ]

    lines = [
        f"{comp['hostname']}: {total} products | median ${median:.0f} (p25 ${p25:.0f} / p75 ${p75:.0f}) | "
        f"{promo_pct:.0f}% on sale (avg {avg_disc:.0f}% off, max {max_disc:.0f}% off) | "
        f"{new_30d} new in 30d | launch rate: {vel:.1f}/month | position: {market_pos} | "
        f"in-stock: {in_stock_pct:.0f}%"
    ]
    if top_tags:
        lines.append(f"  Product categories/tags: {', '.join(top_tags)}")
    if top_vendors:
        lines.append(f"  Brands/vendors: {', '.join(top_vendors)}")
    if newest:
        lines.append(f"  Recent launches: {', '.join(newest)}")
    if top_discounted:
        lines.append(f"  Currently discounted: {', '.join(top_discounted)}")
    if top_priced:
        lines.append(f"  Most expensive: {', '.join(top_priced)}")

    return "\n".join(lines)


@celery.task(name="app.tasks.playbook_ai.generate_ai_playbook")
def generate_ai_playbook(user_id: str) -> dict:
    settings = get_settings()
    db = get_supabase()

    comps_res = (
        db.table("competitors")
        .select("id, hostname")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .eq("scan_status", "done")
        .order("created_at", desc=False)  # deterministic ordering for comp_ids[0]
        .execute()
    )
    competitors = [c for c in (comps_res.data or []) if not c.get("is_my_store")]
    if not competitors:
        return {"status": "no_competitors"}

    comp_ids = [c["id"] for c in competitors]
    comp_map = {c["hostname"]: c["id"] for c in competitors}

    # Skip if a fresh playbook already exists (non-atomic but low-cost race)
    cutoff_fresh = (datetime.now(timezone.utc) - timedelta(hours=_FRESHNESS_HOURS)).isoformat()
    existing = (
        db.table("ai_summaries")
        .select("generated_at")
        .in_("competitor_id", comp_ids)
        .eq("summary_type", "playbook")
        .gte("generated_at", cutoff_fresh)
        .limit(1)
        .execute()
    )
    if existing.data:
        return {"status": "fresh_exists"}

    # Build rich per-competitor blocks
    comp_blocks: list[str] = []
    for comp in competitors:
        snap_res = (
            db.table("scan_snapshots")
            .select("product_count, median_price, promo_rate, new_30d, snapshot_data")
            .eq("competitor_id", comp["id"])
            .order("scanned_at", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        if not snap_res.data:
            continue
        comp_blocks.append(_format_competitor_block(comp, snap_res.data))

    if not comp_blocks:
        return {"status": "no_snapshot_data"}

    # Recent critical/warning change events with product titles
    event_cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    changes_res = (
        db.table("change_events")
        .select("change_type, severity, delta_pct, product_title, old_value, new_value, competitor_id, detected_at")
        .in_("competitor_id", comp_ids)
        .gte("detected_at", event_cutoff)
        .in_("severity", ["critical", "warning"])
        .order("detected_at", desc=True)
        .limit(25)
        .execute()
    )
    comp_id_to_host = {c["id"]: c["hostname"] for c in competitors}
    change_lines: list[str] = []
    for c in (changes_res.data or []):
        host = comp_id_to_host.get(c["competitor_id"], "?")
        ctype = c.get("change_type", "").replace("_", " ")
        delta = c.get("delta_pct")
        title = (c.get("product_title") or "")[:40]
        old_v = c.get("old_value") or {}
        new_v = c.get("new_value") or {}
        old_price = old_v.get("price") or old_v.get("discounted_pct")
        new_price = new_v.get("price") or new_v.get("discounted_pct")
        delta_str = f" ({delta:+.0f}%)" if delta is not None else ""
        price_str = f" ${old_price}→${new_price}" if old_price and new_price else ""
        title_str = f' "{title}"' if title else ""
        change_lines.append(f"- {host} — {ctype}{title_str}{price_str}{delta_str} [{c.get('severity')}]")

    changes_section = (
        "\n".join(change_lines)
        if change_lines
        else "No critical or warning changes detected in the last 7 days."
    )

    prompt = f"""Analyze this Shopify competitor intelligence and generate 5-8 plays for a store owner who is competing against these brands.

COMPETITOR DATA:
{chr(10).join(comp_blocks)}

RECENT ALERTS (last 7 days — critical/warning only):
{changes_section}

Return ONLY valid JSON — no markdown fences, no preamble, no explanation:
{{
  "plays": [
    {{
      "section": "act_now|right_now|this_week",
      "headline": "6-12 words — include a specific number from the data and name the competitor or category",
      "action": "2-3 sentences — name a specific platform, name a product or category from the data, give one concrete next step with a budget or timeframe",
      "deadline": "right now|today|within 48h|this week",
      "type": "pricing|catalog|positioning|discounts|alert",
      "tab": "overview|pricing|launches|discounts|changes",
      "competitor_hostname": "exact hostname from the data above, or 'multiple' for cross-competitor plays",
      "detail": {{
        "steps": [
          "Open [exact platform name] → [specific path or feature]",
          "... 5-7 more steps, each naming exact platforms/features, dollar amounts, and measurable criteria ...",
          "Measure [specific metric] after [timeframe] — success looks like [threshold]"
        ],
        "why": "1-2 sentences: what is happening at this competitor RIGHT NOW and why that creates a window for the user",
        "outcome": "1 sentence: specific measurable result if the play works (e.g. 'A CTR lift >15% confirms the angle works — save this ad set and reuse it every time they run a sale')",
        "competitor_metrics": "paste the exact data point(s) from above that make this play valid"
      }}
    }}
  ]
}}

Section rules:
- act_now: competitor is doing something RIGHT NOW creating a < 48h window — ONLY generate if there are actual recent alerts above
- right_now: current competitor state reveals an opportunity to act in the next 2-3 days
- this_week: strategic gap or compounding trend where every day of delay costs something
- If there are no recent alerts, generate only right_now and this_week plays

Quality checklist for each play before you output it:
- Does the headline name a specific number from the data? ✓/✗
- Do the steps name a specific platform path? ✓/✗
- Is there a dollar amount or time window in at least one step? ✓/✗
- Is there a measurable success criterion in the outcome? ✓/✗
- If any answer is ✗, rewrite the play before including it"""

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text.strip()

        try:
            parsed = _extract_json(raw_text)
        except (ValueError, json.JSONDecodeError) as exc:
            logger.error("generate_ai_playbook: bad JSON from Claude for %s: %s — raw: %r", user_id, exc, raw_text[:300])
            return {"status": "error", "reason": "invalid_json"}

        plays = parsed.get("plays") or []
        normalised: list[dict] = []
        for i, p in enumerate(plays):
            section = p.get("section", "this_week")
            host = p.get("competitor_hostname", "")
            detail = p.get("detail") or {}

            if host and host != "multiple":
                comp_id = comp_map.get(host) or comp_ids[0]
                display_hostname = host
                competitors_row = [{"hostname": host, "metric": detail.get("competitor_metrics", "")}]
            else:
                # Cross-competitor play — no single dashboard to deep-link to
                comp_id = ""  # empty so frontend hides the "View in dashboard" button
                display_hostname = f"{len(competitors)} competitors"
                competitors_row = [
                    {"hostname": c["hostname"], "metric": ""}
                    for c in competitors[:4]
                ]

            normalised.append({
                "id": f"ai-{section}-{i}",
                "section": section,
                "priority": _SECTION_PRIORITY.get(section, 55) - i,
                "competitor_id": comp_id,
                "hostname": display_hostname,
                "headline": p.get("headline", ""),
                "action": p.get("action", ""),
                "deadline": p.get("deadline", "this week"),
                "type": p.get("type", "positioning"),
                "source": "ai",
                "tab": p.get("tab", "overview"),
                "detail": {
                    "steps": detail.get("steps") or [],
                    "why": detail.get("why", ""),
                    "outcome": detail.get("outcome", ""),
                    "competitors": competitors_row,
                },
            })

        db.table("ai_summaries").insert({
            "competitor_id": comp_ids[0],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model": "claude-sonnet-4-6",
            "summary_text": json.dumps({"plays": normalised, "user_id": user_id}),
            "summary_type": "playbook",
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        }).execute()

        return {"status": "ok", "play_count": len(normalised)}

    except Exception as exc:
        logger.error("generate_ai_playbook failed for user %s: %s", user_id, exc)
        return {"status": "error", "reason": str(exc)}
