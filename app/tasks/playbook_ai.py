from __future__ import annotations
import json
import logging
import re
from datetime import datetime, timezone, timedelta

import anthropic
import redis as _redis_lib

from .celery_app import celery
from app.core.config import get_settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a Shopify competitive intelligence advisor. Turn real competitor data into specific, executable plays.

Platforms you know: Meta Ads Manager, Google Shopping, Klaviyo, Shopify admin, TikTok Ads.

Great plays have all three: (1) exact navigation paths a complete beginner can follow step-by-step, (2) dollar budgets with a scale trigger, (3) specific product names, categories, or search terms from the data.

Step structure — every play's 3 steps must follow this format:
• Step 1: platform name + exact menu path + the action to take ("In Meta Ads Manager → Campaigns → + Create → choose Traffic objective → proceed to Ad Set")
• Step 2: the specific content to create — exact headline copy, search term to use, product handle, or Klaviyo segment name (use product names from the data)
• Step 3: budget + scale trigger ("Start $15/day → scale to $50/day once CTR exceeds 1.8% after 4 days" or "Spend 30 min this week → measure with [specific metric]")

Meta Ads: Campaigns → Ad Set → Detailed Targeting → type brand name or product category as Interest. Cannot target followers directly. Audience size 500K–2M is ideal."""

_SECTION_PRIORITY = {"act_now": 95, "right_now": 75, "this_week": 55}
_FRESHNESS_HOURS = 23


def _extract_json(text: str) -> dict:
    """Parse JSON from Claude output, handling markdown fences and trailing content."""
    # Strip markdown code fences (``` or ```json)
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip()
    cleaned = re.sub(r"\s*```", "", cleaned).strip()

    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find the first { and use raw_decode so trailing text after } is ignored
    start = cleaned.find("{")
    if start != -1:
        try:
            obj, _ = json.JSONDecoder().raw_decode(cleaned, start)
            return obj
        except json.JSONDecodeError:
            pass

    # Last resort: regex-extract the outermost {...} block
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
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


def _competitor_trend(db, competitor_id: str) -> str | None:
    """Summarize a competitor's last-90-day trajectory from stored snapshots +
    discount-campaign cadence. Returns a one-line string or None (needs >= 3 scans)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    try:
        snaps = (
            db.table("scan_snapshots")
            .select("scanned_at, median_price, promo_rate, product_count")
            .eq("competitor_id", competitor_id)
            .gte("scanned_at", cutoff)
            .order("scanned_at", desc=False)
            .execute()
        )
    except Exception:
        return None
    rows = snaps.data or []
    if len(rows) < 3:
        return None

    first, last = rows[0], rows[-1]
    parts: list[str] = []

    fm, lm = first.get("median_price"), last.get("median_price")
    if fm and lm and float(fm) > 0:
        pct = (float(lm) - float(fm)) / float(fm) * 100
        if abs(pct) >= 3:
            parts.append(f"median ${float(fm):.0f}→${float(lm):.0f} ({pct:+.0f}%)")

    fp, lp = first.get("promo_rate"), last.get("promo_rate")
    if fp is not None and lp is not None and abs(float(lp) - float(fp)) >= 5:
        parts.append(f"promo {float(fp):.0f}%→{float(lp):.0f}%")

    fc, lc = first.get("product_count"), last.get("product_count")
    if fc and lc and int(lc) - int(fc) != 0:
        parts.append(f"catalog {int(fc)}→{int(lc)} ({int(lc) - int(fc):+d})")

    # Discount-campaign cadence — the seasonality insight users pay for
    try:
        ev = (
            db.table("change_events")
            .select("detected_at")
            .eq("competitor_id", competitor_id)
            .eq("change_type", "discount_start")
            .gte("detected_at", cutoff)
            .order("detected_at", desc=False)
            .execute()
        )
        dates = [
            datetime.fromisoformat(e["detected_at"].replace("Z", "+00:00"))
            for e in (ev.data or []) if e.get("detected_at")
        ]
        if len(dates) >= 2:
            intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
            avg = sum(intervals) / len(intervals) if intervals else 0
            if avg > 0:
                parts.append(f"runs sales ~every {int(round(avg))}d ({len(dates)} in 90d)")
    except Exception:
        pass

    return "  90d trend: " + " | ".join(parts) if parts else None


@celery.task(name="app.tasks.playbook_ai.generate_ai_playbook")
def generate_ai_playbook(user_id: str) -> dict:
    settings = get_settings()

    # Rate-limit: prevent re-enqueue storm when generation fails
    _rkey = f"playbook_gen:{user_id}"
    try:
        _r = _redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
        if _r.exists(_rkey):
            logger.info("generate_ai_playbook: rate-limited for %s, skipping", user_id)
            return {"status": "rate_limited"}
        _r.setex(_rkey, 900, "1")  # 15-minute cooldown
    except Exception as _re:
        logger.debug("generate_ai_playbook: redis rate-limit unavailable: %s", _re)

    db = get_supabase()

    comps_res = (
        db.table("competitors")
        .select("id, hostname, is_my_store")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .eq("scan_status", "done")
        .order("created_at", desc=False)  # deterministic ordering for comp_ids[0]
        .execute()
    )
    all_comps = comps_res.data or []
    my_store_comp = next((c for c in all_comps if c.get("is_my_store")), None)
    competitors = [c for c in all_comps if not c.get("is_my_store")]
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

    # Read last playbook to avoid repeating the same types/sections/competitors
    last_themes_str = ""
    try:
        last_pb = (
            db.table("ai_summaries")
            .select("summary_text")
            .in_("competitor_id", comp_ids)
            .eq("summary_type", "playbook")
            .order("generated_at", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        if last_pb and last_pb.data:
            lp_data = json.loads(last_pb.data.get("summary_text") or "{}")
            lp_plays = lp_data.get("plays") or []
            if lp_plays:
                lp_types    = sorted({p.get("type", "")    for p in lp_plays if p.get("type")})
                lp_sections = sorted({p.get("section", "") for p in lp_plays if p.get("section")})
                lp_hosts    = sorted({p.get("hostname", "") for p in lp_plays if p.get("hostname") and p.get("hostname") != "multiple"})
                last_themes_str = (
                    "\nDIVERSITY REQUIREMENT — last playbook covered these (do NOT repeat them):\n"
                    f"  Types used: {', '.join(lp_types) or 'none'}\n"
                    f"  Sections used: {', '.join(lp_sections) or 'none'}\n"
                    f"  Competitors featured: {', '.join(lp_hosts[:4]) or 'none'}\n"
                    "  This time: choose DIFFERENT play types, rotate to sections not used last time, "
                    "and spotlight competitors not featured in the last batch.\n"
                )
    except Exception as _lpe:
        logger.debug("generate_ai_playbook: last-themes read failed: %s", _lpe)

    # Build user's own store context (if available) — makes plays specific to their situation
    my_store_section = ""
    if my_store_comp:
        snap_res = (
            db.table("scan_snapshots")
            .select("product_count, median_price, promo_rate, new_30d, snapshot_data")
            .eq("competitor_id", my_store_comp["id"])
            .order("scanned_at", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        if snap_res.data:
            my_store_section = (
                "YOUR STORE (the user's own Shopify store — use these numbers to make every play "
                "specific to their situation: reference their prices, categories, and products by name "
                "when writing email copy or ad headlines):\n"
                + _format_competitor_block(my_store_comp, snap_res.data)
                + "\n"
            )

    # Adaptive knowledge context — depth follows what StoreScout knows about
    # this business (strategic → operational → customer → full).
    try:
        from app.services.knowledge import build_ai_context
        knowledge_ctx = build_ai_context(user_id)
        if knowledge_ctx:
            if my_store_section:
                my_store_section = my_store_section.rstrip() + "\n  " + knowledge_ctx.replace("\n", "\n  ") + "\n"
            else:
                my_store_section = "YOUR BUSINESS (what StoreScout knows):\n  " + knowledge_ctx.replace("\n", "\n  ") + "\n"
    except Exception as _e:
        logger.debug("Knowledge enrichment skipped: %s", _e)

    # Optional public competitor ad-intelligence (inert unless a token is set)
    try:
        from app.api.v1.integrations import get_competitor_ads_context
    except Exception:
        get_competitor_ads_context = None  # type: ignore

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
        block = _format_competitor_block(comp, snap_res.data)
        trend = _competitor_trend(db, comp["id"])
        if trend:
            block += "\n" + trend
        if get_competitor_ads_context:
            try:
                ads = get_competitor_ads_context(comp["hostname"])
                if ads:
                    block += "\n  " + ads
            except Exception:
                pass
        comp_blocks.append(block)

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

    # Adapt the per-play competitor rule to how many competitors the user actually has —
    # forcing "a different competitor per play" is impossible for a 1-competitor free user.
    n_comp = len(competitors)
    if n_comp >= 3:
        diversity_rule = "- Each play must spotlight a DIFFERENT competitor — do not feature the same hostname twice"
    elif n_comp == 2:
        diversity_rule = "- Spread the plays across both competitors; feature one twice only if its data clearly warrants it"
    else:
        diversity_rule = "- There is ONE competitor — make each play a DIFFERENT angle (e.g. pricing, catalog/positioning, timing); do not repeat the same move three times"

    my_store_prompt = (
        f"{my_store_section}\n" if my_store_section else ""
    )
    my_store_instruction = (
        "You have the user's own store data above. Write email copy and ad headlines AS IF you are "
        "their copywriter — use their actual price points, categories, and products by name. "
        "The contrast between their store and the competitor's move is the story.\n\n"
        if my_store_section else ""
    )

    prompt = f"""Analyze this Shopify competitor intelligence and generate exactly 3 plays for a store owner.
{last_themes_str}
{my_store_prompt}COMPETITOR DATA:
{chr(10).join(comp_blocks)}

RECENT ALERTS (last 7 days — critical/warning only):
{changes_section}

{my_store_instruction}Return ONLY valid JSON — no markdown, no preamble, no explanation after the closing brace:
{{
  "plays": [
    {{
      "section": "act_now|right_now|this_week",
      "headline": "6-10 words with a specific number from the data",
      "action": "1 sentence max 40 words — platform name + product or category + one concrete action with budget or timeframe",
      "deadline": "right now|today|within 48h|this week",
      "type": "pricing|catalog|positioning|discounts|alert",
      "tab": "overview|pricing|launches|discounts|changes",
      "competitor_hostname": "exact hostname or 'multiple'",
      "detail": {{
        "steps": [
          "Step 1: [Platform → exact menu path] — [action to take]",
          "Step 2: [exact content to create — headline copy, search term, or product name from the data]",
          "Step 3: Budget $[X]/day — scale to $[Y]/day when [metric > threshold after N days] OR [time-based: spend 30 min + track with metric]"
        ],
        "why": "1 sentence on why this window exists right now",
        "outcome": "1 sentence measurable result with a number (e.g. '10-20% CTR lift within 5 days')",
        "competitor_metrics": "the exact data point from the competitor data that validates this play"
      }},
      "draft_asset": null
    }}
  ]
}}

Rules:
- act_now: competitor doing something RIGHT NOW, <48h window — only if recent alerts exist above
- right_now: current state reveals an opportunity, act in 2-3 days
- this_week: strategic gap or trend (7 days)
- No recent alerts = no act_now plays
- Steps must follow the exact 3-step format above — Step 1 always has platform + nav path, Step 3 always has budget + scale trigger
{diversity_rule}
- Vary the channel across the 3 plays — do NOT make every play a paid-ads play. Include at least one email/Klaviyo, Shopify merchandising, or organic/SEO move. Recommend paid ads only when the data clearly supports it.
- For each act_now and right_now play, replace "draft_asset": null with a ready-to-paste asset object:
    email -> {{"type":"email","label":"<what it is>","subject":"<subject line>","body_opening":"<2-3 sentences ready to send>","headlines":[],"ad_body":null}}
    ad    -> {{"type":"ad","label":"<what it is>","headlines":["<=30 chars","<=30 chars","<=30 chars"],"ad_body":"<1-2 sentences>","subject":null,"body_opening":null}}
  this_week plays keep "draft_asset": null
- If the data includes a "90d trend" or competitor ad activity, use it: cite the seasonality/cadence or their ad momentum in the play's why/competitor_metrics
- Output exactly 3 plays, no more, no less"""

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text.strip()
        if message.stop_reason == "max_tokens":
            logger.warning("generate_ai_playbook: response truncated at max_tokens for %s", user_id)

        try:
            parsed = _extract_json(raw_text)
        except (ValueError, json.JSONDecodeError) as exc:
            logger.error("generate_ai_playbook: bad JSON from Claude for %s: %s — raw: %r", user_id, exc, raw_text[:500])
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

            draft_raw = p.get("draft_asset") or {}
            da_type = draft_raw.get("type", "none")
            draft_asset = (
                {
                    "type": da_type,
                    "label": draft_raw.get("label") or "",
                    "subject": draft_raw.get("subject"),
                    "body_opening": draft_raw.get("body_opening"),
                    "headlines": draft_raw.get("headlines") or [],
                    "ad_body": draft_raw.get("ad_body"),
                }
                if da_type in ("email", "ad")
                else None
            )

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
                "draft_asset": draft_asset,
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
