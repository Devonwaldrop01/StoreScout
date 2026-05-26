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

_SYSTEM_PROMPT = (
    "You are a Shopify ecommerce strategist. You analyze competitor catalog data and generate "
    "specific, executable competitive plays for store owners. Be direct and actionable. "
    "Include platform names, dollar budgets, and timeframes. Never give generic advice."
)

_SECTION_PRIORITY = {"act_now": 95, "right_now": 75, "this_week": 55}
_FRESHNESS_HOURS = 23


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
        .execute()
    )
    competitors = [c for c in (comps_res.data or []) if not c.get("is_my_store")]
    if not competitors:
        return {"status": "no_competitors"}

    comp_ids = [c["id"] for c in competitors]
    comp_map = {c["hostname"]: c["id"] for c in competitors}

    # Skip if a fresh playbook already exists
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

    # Build per-competitor summary lines
    comp_lines: list[str] = []
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
        snap = snap_res.data
        sd = snap.get("snapshot_data") or {}
        pricing = sd.get("pricing") or {}
        discounts = sd.get("discounts") or {}
        positioning = sd.get("positioning") or {}
        launch = sd.get("launch_timeline") or {}

        promo_raw = snap.get("promo_rate")
        promo_f = float(promo_raw) if promo_raw is not None else float(discounts.get("discounted_pct") or 0)
        promo_str = f"{promo_f:.0f}%" if promo_f > 1.0 else f"{promo_f * 100:.0f}%"

        median = float(snap.get("median_price") or pricing.get("median") or 0)
        p25 = float(pricing.get("p25") or 0)
        p75 = float(pricing.get("p75") or 0)
        new_30d = int(snap.get("new_30d") or 0)
        avg_disc = float(discounts.get("avg_discount_pct") or discounts.get("median_discount_pct") or 0)
        market_pos = (positioning.get("market_position") or {}).get("label", "mid-market")
        vel = float((launch.get("velocity") or {}).get("last_30d") or 0)
        total = int(snap.get("product_count") or (sd.get("catalog") or {}).get("total_products") or 0)

        comp_lines.append(
            f"- {comp['hostname']}: {total} products, "
            f"median ${median:.0f} (p25 ${p25:.0f} / p75 ${p75:.0f}), "
            f"{promo_str} on sale (avg {avg_disc:.0f}% off), "
            f"{new_30d} new products in 30d, "
            f"position: {market_pos}, "
            f"launch rate: {vel:.1f} products/month"
        )

    if not comp_lines:
        return {"status": "no_snapshot_data"}

    # Recent critical/warning change events
    event_cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    changes_res = (
        db.table("change_events")
        .select("change_type, severity, delta_pct, product_title, competitor_id")
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
        title = (c.get("product_title") or "")[:35]
        delta_str = f" ({delta:+.0f}%)" if delta else ""
        title_str = f": {title}" if title else ""
        change_lines.append(f"- {host} — {ctype}{title_str}{delta_str} [{c.get('severity')}]")

    changes_section = (
        "\n".join(change_lines)
        if change_lines
        else "No critical or warning changes in the last 7 days."
    )

    prompt = f"""Analyze this Shopify competitor intelligence and generate 5-8 actionable plays for a store owner.

COMPETITOR DATA:
{chr(10).join(comp_lines)}

RECENT ALERTS (last 7 days — critical/warning only):
{changes_section}

Return ONLY valid JSON, no markdown, no preamble:
{{
  "plays": [
    {{
      "section": "act_now|right_now|this_week",
      "headline": "punchy 6-12 word title with at least one specific number from the data",
      "action": "2-3 sentences — name a specific platform and give one concrete next step",
      "deadline": "right now|today|within 48h|this week",
      "type": "pricing|catalog|positioning|discounts|alert",
      "tab": "overview|pricing|launches|discounts|changes",
      "competitor_hostname": "exact hostname from the data, or 'multiple' for cross-competitor plays",
      "detail": {{
        "steps": ["step 1 — name platform explicitly (e.g. Meta Ads Manager, Google Shopping, Klaviyo)", "step 2", ...],
        "why": "1-2 sentences on why this play is valid right now",
        "outcome": "1 sentence describing measurable success",
        "competitor_metrics": "the specific data point(s) that make this play valid"
      }}
    }}
  ]
}}

Rules:
- act_now: competitor is doing something RIGHT NOW creating a < 48h window (requires a recent critical/warning alert)
- right_now: current competitor state reveals an opportunity to act in 2-3 days
- this_week: strategic gap or compounding trend (7 days to act)
- Only generate act_now plays if there are actual recent alerts above — do not fabricate urgency
- Name specific platforms in every step: Meta Ads Manager, Google Shopping, Klaviyo, Shopify admin, Alibaba, Google Analytics
- Include concrete numbers: $10/day budget, 5-day test, >15% CTR threshold
- Cross-competitor patterns (2+ competitors) get higher priority than single-store observations
- Start every step with a verb: Open, Go to, Search, Create, Duplicate, Set, Send, Run, Check"""

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2500,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text.strip()

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if m:
                parsed = json.loads(m.group())
            else:
                logger.error("generate_ai_playbook: bad JSON from Claude: %r", raw_text[:200])
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
                comp_id = comp_ids[0]
                display_hostname = f"{len(competitors)} competitors"
                competitors_row = [{"hostname": c["hostname"], "metric": ""} for c in competitors[:4]]

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
