from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import anthropic

from .celery_app import celery
from app.core.config import get_settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a Shopify ecommerce strategist. You analyze competitor catalog data extracted from public Shopify product endpoints. Metrics come from pricing analysis (median, min/max, p25/p75), discount analysis (% discounted, median discount depth), launch timeline (monthly velocity, acceleration), and vendor/tag analysis. Be specific about numbers. Be direct — no filler sentences. Refer to the store by its domain name, not "the store" or "this competitor." Keep responses under 6 sentences."""


def _format_snapshot(snap: dict, hostname: str) -> str:
    d = snap.get("snapshot_data") or snap
    catalog = d.get("catalog") or {}
    pricing = d.get("pricing") or {}
    discounts = d.get("discounts") or {}
    launch = d.get("launch_timeline") or {}
    pos = d.get("positioning") or {}
    launch_counts = launch.get("launch_counts") or {}

    lines = [
        f"Domain: {hostname}",
        f"Products: {catalog.get('total_products', '?')}",
        f"Median price: ${pricing.get('median', '?')}",
        f"Promo rate: {discounts.get('discounted_pct', '?')}% of catalog discounted",
        f"Median discount: {discounts.get('median_discount_pct', '?')}%",
        f"New (30d): {launch_counts.get('30d', {}).get('count', '?')} products",
        f"Launch velocity (30d): {(launch.get('velocity') or {}).get('last_30d', '?')} products/month",
        f"Market position: {(pos.get('market_position') or {}).get('label', '?')}",
        f"Promo intensity: {(pos.get('promo_intensity') or {}).get('label', '?')}",
    ]
    return "\n".join(lines)


def _format_changes(changes: list) -> str:
    if not changes:
        return "No significant changes detected."
    rows = []
    for c in changes[:15]:
        title = c.get("product_title") or c.get("change_type", "").replace("_", " ").title()
        ctype = c.get("change_type", "")
        old_v = c.get("old_value") or {}
        new_v = c.get("new_value") or {}
        if ctype == "price_change":
            delta = c.get("delta_pct", 0) or 0
            rows.append(f"- Price change: {title}: ${old_v.get('price','?')} → ${new_v.get('price','?')} ({delta:+.1f}%)")
        elif ctype == "new_product":
            price = new_v.get("price_min", "")
            rows.append(f"- New product: {title}" + (f" (${price})" if price else ""))
        elif ctype == "discount_start":
            rows.append(f"- Discount campaign started: {old_v.get('discounted_pct',0):.0f}% → {new_v.get('discounted_pct',0):.0f}% of catalog")
        elif ctype == "discount_end":
            rows.append(f"- Discount campaign ended")
        else:
            rows.append(f"- {ctype.replace('_',' ').title()}: {title}")
    return "\n".join(rows)


@celery.task(name="app.tasks.ai_summaries.generate_weekly_summary")
def generate_weekly_summary(competitor_id: str, summary_type: str = "weekly") -> dict:
    settings = get_settings()
    db = get_supabase()

    competitor = db.table("competitors").select("hostname, user_id").eq("id", competitor_id).single().execute()
    if not competitor.data:
        return {"status": "not_found"}

    hostname = competitor.data["hostname"]
    user_id = competitor.data["user_id"]

    # Check user tier — AI summaries are Pro+
    user = db.table("user_profiles").select("tier").eq("id", user_id).single().execute()
    tier = (user.data or {}).get("tier", "free")
    if tier == "free" and summary_type != "onboarding":
        return {"status": "tier_restricted"}

    # Get recent snapshots (last 7 days for weekly, or just latest for onboarding)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    snaps_query = db.table("scan_snapshots")\
        .select("snapshot_data, scanned_at")\
        .eq("competitor_id", competitor_id)\
        .order("scanned_at", desc=True)
    if summary_type == "weekly":
        snaps_query = snaps_query.gte("scanned_at", cutoff)
    snaps = snaps_query.limit(7).execute()

    if not snaps.data:
        return {"status": "no_snapshots"}

    latest = snaps.data[0]
    current_state = _format_snapshot(latest, hostname)

    # Recent changes
    changes_result = db.table("change_events")\
        .select("*")\
        .eq("competitor_id", competitor_id)\
        .gte("detected_at", cutoff)\
        .order("severity", desc=True)\
        .limit(20)\
        .execute()
    changes_text = _format_changes(changes_result.data or [])

    # Comparison vs oldest snapshot in window
    comparison = ""
    if len(snaps.data) >= 2:
        oldest = snaps.data[-1]
        old_snap = oldest.get("snapshot_data") or {}
        new_snap = latest.get("snapshot_data") or {}
        old_median = (old_snap.get("pricing") or {}).get("median")
        new_median = (new_snap.get("pricing") or {}).get("median")
        old_disc = (old_snap.get("discounts") or {}).get("discounted_pct")
        new_disc = (new_snap.get("discounts") or {}).get("discounted_pct")
        old_count = (old_snap.get("catalog") or {}).get("total_products")
        new_count = (new_snap.get("catalog") or {}).get("total_products")
        comparison_lines = []
        if old_median and new_median:
            comparison_lines.append(f"Median price: ${old_median} → ${new_median}")
        if old_disc is not None and new_disc is not None:
            comparison_lines.append(f"Promo rate: {old_disc}% → {new_disc}%")
        if old_count and new_count:
            comparison_lines.append(f"Product count: {old_count} → {new_count}")
        comparison = "\n".join(comparison_lines) if comparison_lines else "No comparison data."

    prompt = f"""Here is the {"weekly" if summary_type == "weekly" else "initial"} data for {hostname}:

CURRENT STATE:
{current_state}

CHANGES THIS {"WEEK" if summary_type == "weekly" else "SCAN"}:
{changes_text}

{"WEEK-OVER-WEEK COMPARISON:" + chr(10) + comparison if comparison else ""}

{"Write a 4-6 sentence strategic summary: (1) the most significant change or pattern, (2) what it likely signals about their strategy, (3) one specific action the reader could consider." if summary_type == "weekly" else "Write 3 specific things you notice about this store — each in 1-2 sentences. Focus on what's actionable for a competitor."}"""

    model = "claude-sonnet-4-6" if summary_type == "onboarding" else "claude-haiku-4-5-20251001"

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model=model,
            max_tokens=400 if summary_type == "onboarding" else 500,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        summary_text = message.content[0].text
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
    except Exception as exc:
        logger.error(f"Claude API failed: {exc}")
        return {"status": "error", "reason": str(exc)}

    db.table("ai_summaries").insert({
        "competitor_id": competitor_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "summary_text": summary_text,
        "summary_type": summary_type,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }).execute()

    return {"status": "ok", "tokens": input_tokens + output_tokens}
