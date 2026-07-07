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


@celery.task(name="app.tasks.ai_summaries.generate_brief")
def generate_brief(competitor_id: str, snapshot_id: str) -> dict:
    """
    Generate a 3-card Intelligence Brief after every scan.
    Uses Sonnet for the first scan (high-stakes first impression), Haiku for rescans.
    JSON output: {"cards": [{"type": "signal"|"opportunity"|"watch", "headline": str, "body": str}]}
    """
    import json as _json
    import re as _re

    settings = get_settings()
    db = get_supabase()

    comp = db.table("competitors")\
        .select("hostname, user_id, is_my_store")\
        .eq("id", competitor_id)\
        .maybe_single()\
        .execute()
    if not comp or not comp.data:
        return {"status": "not_found"}
    if comp.data.get("is_my_store"):
        return {"status": "skipped_my_store"}

    hostname = comp.data["hostname"]

    snap = db.table("scan_snapshots")\
        .select("snapshot_data")\
        .eq("id", snapshot_id)\
        .maybe_single()\
        .execute()
    if not snap or not snap.data:
        return {"status": "no_snapshot"}

    snap_data = snap.data.get("snapshot_data") or {}

    snap_count = db.table("scan_snapshots")\
        .select("id", count="exact")\
        .eq("competitor_id", competitor_id)\
        .execute()
    is_first_scan = (snap_count.count or 0) == 1

    current_state = _format_snapshot({"snapshot_data": snap_data}, hostname)

    # The digest fields (threat_level / highlights / one_move) power the free
    # Scout Brief — a 30-second "what happened" readout. The cards power the
    # first-scan email and shared reports. The deep strategist analysis lives
    # in generate_pro_analysis (summary_type="pro"), NOT here — free and pro
    # must answer different questions, not the same question at two lengths.
    prompt = f"""Analyze this Shopify competitor store and return ONLY valid JSON — no markdown, no preamble, no explanation.

Output this exact structure:
{{
  "threat_level": "high" | "medium" | "low",
  "highlights": ["...", "...", "..."],
  "one_move": "...",
  "cards": [
    {{"type": "signal", "headline": "...", "body": "..."}},
    {{"type": "opportunity", "headline": "...", "body": "..."}},
    {{"type": "watch", "headline": "...", "body": "..."}},
    {{"type": "action", "headline": "...", "body": "..."}}
  ]
}}

Rules:
- threat_level: how dangerous this store's current posture is to a similar merchant right now (aggressive discounting/launch pace = high; dormant = low)
- highlights: 3-4 factual bullets, each 6 words or fewer, each containing a number from the data (e.g. "312 products", "18% of catalog discounted", "4 launches this month")
- one_move: ONE sentence, starts with a verb, the single highest-priority action for a competing merchant. No reasoning, no hedging.
- headline: 4-8 words, must include at least one specific number from the data
- body: 1-2 sentences, specific and actionable
- signal: most notable thing about this store right now (pricing, discount rate, launch pace)
- opportunity: the clearest gap or opening a competitor could exploit
- watch: a trend or signal that bears monitoring
- action: the single most important thing to do in the next 7 days — start with a verb (Launch, Reprice, Push, Email, Test), include a concrete timeframe (today / this week / within 48 hours)

Store data:
{current_state}"""

    model = "claude-sonnet-4-6" if is_first_scan else "claude-haiku-4-5-20251001"

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model=model,
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text.strip()

        # Validate JSON — extract if wrapped in markdown fences
        try:
            _json.loads(raw_text)
        except _json.JSONDecodeError:
            m = _re.search(r'\{.*\}', raw_text, _re.DOTALL)
            if m:
                raw_text = m.group()
                _json.loads(raw_text)  # re-validate
            else:
                logger.error("generate_brief: Claude did not return valid JSON: %r", raw_text[:200])
                return {"status": "error", "reason": "invalid_json"}

    except Exception as exc:
        logger.error("generate_brief Claude API failed for %s: %s", competitor_id, exc)
        return {"status": "error", "reason": str(exc)}

    db.table("ai_summaries").insert({
        "competitor_id": competitor_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "summary_text": raw_text,
        "summary_type": "brief",
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }).execute()

    if is_first_scan:
        try:
            from app.tasks.alerts import send_first_scan_email
            send_first_scan_email.apply_async(args=[competitor_id], countdown=600)
        except Exception as exc:
            logger.warning("Could not enqueue first-scan email for %s: %s", competitor_id, exc)

    return {"status": "ok", "is_first_scan": is_first_scan}


_PRO_SYSTEM_PROMPT = """You are a senior ecommerce strategist reviewing everything StoreScout knows about a competitor for a paying client who runs a Shopify store. You do not summarize — you interpret. Every conclusion must trace back to the observed data, every prediction carries a confidence estimate, and every section answers: what does this mean, why should the client care, and what should they do. Never invent numbers. When client store context is provided, personalize the business-impact section to their actual catalog, inventory, and pricing. Refer to stores by domain name."""


@celery.task(name="app.tasks.ai_summaries.generate_pro_analysis")
def generate_pro_analysis(competitor_id: str) -> dict:
    """
    The Intelligence Pro strategist report (Pro/Agency only).

    Deliberately a different product from the free Scout Brief: the brief says
    WHAT happened since the last scan; this interprets what the competitor's
    behavior MEANS, predicts their next moves with confidence scores, and
    evaluates the impact on the client's own business. Context is much richer
    than the brief: 30 days of snapshot history, change events, launch
    cadence, and the client's own store data when connected.

    Output JSON (summary_type="pro"):
    {"threat": {"level", "score", "why"},
     "momentum": {"state", "evidence": []},
     "interpretation": str,
     "predictions": [{"move", "confidence", "basis"}],
     "impact": {"opportunities": [], "risks": [], "posture"},
     "evidence": [],
     "confidence_basis": []}
    """
    import json as _json
    import re as _re

    settings = get_settings()
    db = get_supabase()

    comp = db.table("competitors")\
        .select("hostname, user_id, is_my_store")\
        .eq("id", competitor_id)\
        .maybe_single()\
        .execute()
    if not comp or not comp.data:
        return {"status": "not_found"}
    if comp.data.get("is_my_store"):
        return {"status": "skipped_my_store"}

    hostname = comp.data["hostname"]
    user_id = comp.data["user_id"]

    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    tier = ((user and user.data) or {}).get("tier", "free")
    if tier == "free":
        return {"status": "tier_restricted"}

    # ── 30 days of snapshot history → momentum series ────────────────────
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    snaps = db.table("scan_snapshots")\
        .select("snapshot_data, scanned_at")\
        .eq("competitor_id", competitor_id)\
        .gte("scanned_at", cutoff)\
        .order("scanned_at", desc=True)\
        .limit(12)\
        .execute()
    if not snaps.data:
        # Young competitor — fall back to whatever exists
        snaps = db.table("scan_snapshots")\
            .select("snapshot_data, scanned_at")\
            .eq("competitor_id", competitor_id)\
            .order("scanned_at", desc=True)\
            .limit(3)\
            .execute()
    if not snaps.data:
        return {"status": "no_snapshots"}

    latest = snaps.data[0]
    current_state = _format_snapshot(latest, hostname)

    history_lines = []
    for s in reversed(snaps.data):
        d = s.get("snapshot_data") or {}
        date = (s.get("scanned_at") or "")[:10]
        cat = (d.get("catalog") or {}).get("total_products", "?")
        med = (d.get("pricing") or {}).get("median", "?")
        promo = (d.get("discounts") or {}).get("discounted_pct", "?")
        history_lines.append(f"{date}: {cat} products, median ${med}, {promo}% discounted")
    history_text = "\n".join(history_lines) if len(history_lines) > 1 else "Only one scan so far — history builds from here."

    # Launch cadence from the latest snapshot
    launch = (latest.get("snapshot_data") or {}).get("launch_timeline") or {}
    velocity = launch.get("velocity") or {}
    counts = launch.get("launch_counts") or {}
    cadence_text = (
        f"Launches: {counts.get('30d', {}).get('count', '?')} in 30d, "
        f"{counts.get('90d', {}).get('count', '?')} in 90d; "
        f"velocity {velocity.get('last_30d', '?')}/mo vs {velocity.get('prev_30d', velocity.get('last_90d', '?'))} prior"
    )

    # Change events (30d)
    changes_result = db.table("change_events")\
        .select("*")\
        .eq("competitor_id", competitor_id)\
        .gte("detected_at", cutoff)\
        .order("detected_at", desc=True)\
        .limit(30)\
        .execute()
    changes_text = _format_changes(changes_result.data or [])

    # ── Client store context (personalizes the impact section) ───────────
    my_store_text = ""
    try:
        mine = db.table("competitors").select("id, hostname")\
            .eq("user_id", user_id).eq("is_my_store", True).maybe_single().execute()
        if mine and mine.data:
            my_snap = db.table("scan_snapshots")\
                .select("snapshot_data")\
                .eq("competitor_id", mine.data["id"])\
                .order("scanned_at", desc=True)\
                .limit(1)\
                .execute()
            if my_snap.data:
                my_store_text = _format_snapshot(my_snap.data[0], mine.data["hostname"])
    except Exception as exc:
        logger.debug("pro-analysis my-store context failed: %s", exc)
    try:
        from app.api.v1.integrations import get_shopify_context
        admin_ctx = get_shopify_context(user_id)
        if admin_ctx:
            my_store_text = (my_store_text + "\n" + admin_ctx).strip()
    except Exception as exc:
        logger.debug("pro-analysis shopify admin context failed: %s", exc)

    prompt = f"""Competitor under review: {hostname}

CURRENT STATE:
{current_state}

SCAN HISTORY (oldest → newest):
{history_text}

LAUNCH CADENCE:
{cadence_text}

CHANGES DETECTED (last 30 days):
{changes_text}

{"CLIENT'S OWN STORE:" + chr(10) + my_store_text if my_store_text else "CLIENT'S OWN STORE: not connected — keep the impact section strategic rather than operational, and note once that connecting their store sharpens these recommendations."}

Return ONLY valid JSON — no markdown, no code fences:
{{
  "threat": {{"level": "high"|"medium"|"low", "score": <0-100>, "why": "1-2 sentences on why this competitor is/isn't dangerous right now"}},
  "momentum": {{"state": "accelerating"|"stable"|"slowing", "evidence": ["2-3 short factual observations from the history"]}},
  "interpretation": "2-3 sentences: what this behavior likely means as a business strategy (e.g. 'no launches in 30 days suggests prioritizing profitability over expansion')",
  "predictions": [
    {{"move": "specific next move, e.g. 'Launch a seasonal collection'", "confidence": <0-100>, "basis": "the observed pattern this rests on"}}
  ],
  "impact": {{
    "opportunities": ["1-3 openings the client can exploit, each with the evidence inline"],
    "risks": ["1-2 threats to the client's position"],
    "posture": "one sentence: should the client push now, hold, or defend — and why"
  }},
  "evidence": ["4-6 short factual data points underpinning this analysis, each with a number"],
  "confidence_basis": ["which data streams informed this: e.g. 'catalog history (12 scans)', 'pricing history', 'launch cadence'"]
}}

Rules:
- 2-4 predictions, each grounded in an observed pattern — no generic guesses
- confidence scores must reflect data depth: thin history caps confidence at 60
- if the client's store context is present, opportunities/risks must reference their actual products, inventory, or pricing"""

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1600,
            system=_PRO_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text.strip()
        try:
            _json.loads(raw_text)
        except _json.JSONDecodeError:
            m = _re.search(r'\{.*\}', raw_text, _re.DOTALL)
            if m:
                raw_text = m.group()
                _json.loads(raw_text)
            else:
                logger.error("generate_pro_analysis: invalid JSON: %r", raw_text[:200])
                return {"status": "error", "reason": "invalid_json"}
    except Exception as exc:
        logger.error("generate_pro_analysis Claude API failed for %s: %s", competitor_id, exc)
        return {"status": "error", "reason": str(exc)}

    db.table("ai_summaries").insert({
        "competitor_id": competitor_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "claude-sonnet-4-6",
        "summary_text": raw_text,
        "summary_type": "pro",
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }).execute()

    return {"status": "ok"}
