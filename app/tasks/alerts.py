from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import resend

from .celery_app import celery
from app.core.config import get_settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

ALERT_COOLDOWN_HOURS = 4

_SEVERITY_STYLES = {
    "critical": ("#f87171", "rgba(248,113,113,.15)", "CRITICAL"),
    "warning":  ("#facc15", "rgba(250,204,21,.15)",  "WARNING"),
    "info":     ("#60a5fa", "rgba(96,165,250,.15)",   "INFO"),
}


def _interpret_changes(hostname: str, change_list: list, settings) -> Optional[str]:
    """1-2 sentence Claude Haiku interpretation of a batch of changes. Non-fatal if it fails."""
    try:
        import anthropic
        price_drops = [c for c in change_list if c["change_type"] == "price_change"
                       and (c.get("delta_pct") or 0) < 0]
        new_products = [c for c in change_list if c["change_type"] == "new_product"]
        critical = any(c["severity"] == "critical" for c in change_list)

        lines = []
        if critical and price_drops:
            avg_drop = sum(abs(c.get("delta_pct") or 0) for c in price_drops) / len(price_drops)
            lines.append(f"Flash sale: {len(price_drops)} products dropped avg {avg_drop:.0f}%")
        elif price_drops:
            avg_drop = sum(abs(c.get("delta_pct") or 0) for c in price_drops) / len(price_drops)
            lines.append(f"{len(price_drops)} price drops averaging -{avg_drop:.0f}%")
        if new_products:
            lines.append(f"{len(new_products)} new products launched")
        for c in change_list[:3]:
            if c["change_type"] == "price_change":
                ov = c.get("old_value") or {}
                nv = c.get("new_value") or {}
                lines.append(f"  - {(c.get('product_title') or '?')[:40]}: "
                              f"${ov.get('price','?')} → ${nv.get('price','?')}")

        prompt = (
            f"Shopify competitor intelligence. {hostname} just triggered alerts.\n\n"
            f"Changes:\n" + "\n".join(lines) + "\n\n"
            "Write 1-2 sentences: what does this pattern likely signal about their strategy? "
            "Be specific, direct, no filler."
        )
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:
        logger.warning("Alert interpretation failed (non-fatal): %s", exc)
        return None


def _build_alert_html(hostname: str, subject: str, n: int, change_list: list,
                      interpretation: Optional[str], dashboard_url: str, settings) -> str:
    sev = "info"
    if any(c["severity"] == "critical" for c in change_list):
        sev = "critical"
    elif any(c["severity"] == "warning" for c in change_list):
        sev = "warning"
    sev_color, sev_bg, sev_label = _SEVERITY_STYLES[sev]

    _icon = {"price_change_down": "↓", "price_change_up": "↑",
             "new_product": "+", "product_removed": "−",
             "discount_start": "Sale", "discount_end": "↑", "availability_change": "Stock"}

    rows_html = ""
    for c in change_list[:10]:
        c_sev = c.get("severity", "info")
        c_color = _SEVERITY_STYLES.get(c_sev, _SEVERITY_STYLES["info"])[0]
        ct = c["change_type"]
        if ct == "price_change":
            icon = "↓" if (c.get("delta_pct") or 0) < 0 else "↑"
        else:
            icon = _icon.get(ct, "·")
        title = (c.get("product_title") or ct.replace("_", " ").title())[:55]
        ov = c.get("old_value") or {}
        nv = c.get("new_value") or {}
        if ct == "price_change":
            delta = c.get("delta_pct") or 0
            detail = f"${ov.get('price','?')} → ${nv.get('price','?')} ({delta:+.0f}%)"
        elif ct == "new_product":
            p = nv.get("price_min")
            detail = f"${p}" if p else ""
        elif ct in ("discount_start", "discount_end"):
            detail = f"{ov.get('discounted_pct',0):.0f}% → {nv.get('discounted_pct',0):.0f}% of catalog"
        else:
            detail = ""
        rows_html += (
            f"<tr>"
            f"<td style='padding:8px 0;border-bottom:1px solid #1e3a5f'>"
            f"<span style='color:{c_color};font-weight:700;font-size:12px;margin-right:8px'>{icon}</span>"
            f"<span style='color:#c8d8f0;font-size:13px'>{title}</span></td>"
            f"<td style='padding:8px 0;border-bottom:1px solid #1e3a5f;color:#8aa0b8;"
            f"font-size:12px;text-align:right'>{detail}</td>"
            f"</tr>"
        )

    interp_block = ""
    if interpretation:
        interp_block = (
            f"<div style='background:rgba(163,240,0,.08);border:1px solid rgba(163,240,0,.2);"
            f"border-left:3px solid #a3f000;border-radius:8px;padding:14px 16px;margin-bottom:20px'>"
            f"<div style='font-size:10px;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:.05em;color:#a3f000;margin-bottom:6px'>What this likely means</div>"
            f"<p style='color:#c8d8f0;font-size:13px;line-height:1.5;margin:0'>{interpretation}</p>"
            f"</div>"
        )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#060d18;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<div style="max-width:560px;margin:0 auto;padding:32px 16px">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
    <span style="color:#a3f000;font-weight:700;font-size:16px">StoreScout</span>
    <span style="background:{sev_bg};color:{sev_color};border:1px solid {sev_color}40;
           padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700">{sev_label}</span>
  </div>
  <h1 style="color:#eef3fa;font-size:20px;font-weight:700;margin:0 0 6px;line-height:1.3">{subject}</h1>
  <p style="color:#6b7fa3;font-size:13px;margin:0 0 20px">
    {n} change{'s' if n != 1 else ''} detected at {hostname}
  </p>
  {interp_block}
  <div style="background:#0e1d35;border:1px solid #1e3a5f;border-radius:12px;padding:16px 20px;margin-bottom:20px">
    <table style="width:100%;border-collapse:collapse">{rows_html}</table>
  </div>
  <a href="{dashboard_url}"
     style="display:block;background:#a3f000;color:#060d18;text-decoration:none;
            text-align:center;padding:14px 24px;border-radius:12px;font-weight:700;font-size:15px">
    View full dashboard →
  </a>
  <p style="color:#2a3a4a;font-size:11px;text-align:center;margin-top:24px">
    StoreScout &nbsp;·&nbsp;
    <a href="{settings.public_base_url}/settings" style="color:#2a3a4a">Manage notifications</a>
  </p>
</div>
</body></html>"""


def _resolve_email(db, user_id: str) -> Optional[str]:
    """Return the user's email, falling back to Auth admin API if user_profiles.email is blank."""
    user = db.table("user_profiles").select("email, tier").eq("id", user_id).maybe_single().execute()
    email = ((user.data or {}).get("email") or "").strip()
    if not email:
        try:
            auth_user = db.auth.admin.get_user_by_id(user_id)
            email = (auth_user.user.email or "").strip() if auth_user.user else ""
        except Exception as exc:
            logger.warning("Could not fetch auth email for user %s: %s", user_id, exc)
    return email or None


def _within_cooldown(db, user_id: str, competitor_id: str) -> bool:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=ALERT_COOLDOWN_HOURS)).isoformat()
    result = db.table("change_events")\
        .select("id")\
        .eq("competitor_id", competitor_id)\
        .eq("alert_sent", True)\
        .gte("detected_at", cutoff)\
        .limit(1)\
        .execute()
    return bool(result.data)


@celery.task(name="app.tasks.alerts.send_change_alert", queue="priority",
             bind=True, max_retries=3)
def send_change_alert(self, user_id: str, competitor_id: str, change_ids: List[str]) -> dict:
    settings = get_settings()
    db = get_supabase()

    if _within_cooldown(db, user_id, competitor_id):
        return {"status": "cooldown"}

    # Fetch user prefs and tier
    user = db.table("user_profiles").select("email, tier").eq("id", user_id).maybe_single().execute()
    if not user.data or user.data.get("tier", "free") == "free":
        return {"status": "no_alerts_free_tier"}

    email = _resolve_email(db, user_id)
    if not email:
        logger.error("No email found for user %s — cannot send alert", user_id)
        return {"status": "no_email"}

    prefs = db.table("notification_prefs").select("*").eq("user_id", user_id).maybe_single().execute()
    prefs_data = prefs.data or {}
    if not prefs_data.get("email_price_changes", True):
        return {"status": "alerts_disabled"}

    competitor = db.table("competitors").select("hostname, store_url").eq("id", competitor_id).maybe_single().execute()
    if not competitor.data:
        return {"status": "competitor_not_found"}

    hostname = competitor.data["hostname"]

    # Fetch the actual changes
    changes = db.table("change_events").select("*")\
        .in_("id", change_ids)\
        .order("severity", desc=True)\
        .execute()
    change_list = changes.data or []
    if not change_list:
        return {"status": "no_changes"}

    # Build subject
    n = len(change_list)
    critical = [c for c in change_list if c["severity"] == "critical"]
    if critical:
        subject = f"Flash sale detected at {hostname} — {n} price changes"
    else:
        price_changes = [c for c in change_list if c["change_type"] == "price_change"]
        new_products = [c for c in change_list if c["change_type"] == "new_product"]
        if price_changes and new_products:
            subject = f"{hostname} — {len(price_changes)} price changes + {len(new_products)} new products"
        elif price_changes:
            subject = f"Price change detected at {hostname} ({len(price_changes)} products)"
        elif new_products:
            subject = f"{hostname} launched {len(new_products)} new product{'s' if len(new_products) > 1 else ''}"
        else:
            subject = f"Competitor update at {hostname} ({n} changes)"

    dashboard_url = f"{settings.public_base_url}/dashboard/{competitor_id}"
    interpretation = _interpret_changes(hostname, change_list, settings)
    email_html = _build_alert_html(hostname, subject, n, change_list,
                                   interpretation, dashboard_url, settings)

    try:
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.resend_from,
            "to": email,
            "subject": subject,
            "html": email_html,
        })

        # Mark changes as alerted — this is also what _within_cooldown checks
        db.table("change_events").update({"alert_sent": True}).in_("id", change_ids).execute()

        return {"status": "sent"}
    except Exception as exc:
        logger.error("Alert email failed (attempt %d): %s", self.request.retries + 1, exc)
        # Exponential backoff: 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# ── Weekly digest ─────────────────────────────────────────────────────────────

def _change_icon(change_type: str, delta_pct: float) -> str:
    return {
        "price_change": "↓" if delta_pct < 0 else "↑",
        "new_product": "＋",
        "product_removed": "−",
        "discount_start": "Sale",
        "discount_end": "Sale ended",
        "availability_change": "Stock",
    }.get(change_type, "·")


def _format_change_row(c: dict) -> str:
    title = (c.get("product_title") or c.get("change_type", "").replace("_", " ").title())[:60]
    ctype = c.get("change_type", "")
    old_v = c.get("old_value") or {}
    new_v = c.get("new_value") or {}
    delta = c.get("delta_pct") or 0
    icon = _change_icon(ctype, delta)

    if ctype == "price_change":
        detail = f"${old_v.get('price','?')} → ${new_v.get('price','?')} ({delta:+.1f}%)"
    elif ctype == "new_product":
        p = new_v.get("price_min")
        detail = f"${p}" if p else "New"
    elif ctype in ("discount_start", "discount_end"):
        detail = f"{old_v.get('discounted_pct',0):.0f}% → {new_v.get('discounted_pct',0):.0f}% of catalog"
    else:
        detail = ctype.replace("_", " ").title()

    return (
        f"<tr>"
        f"<td style='padding:6px 8px 6px 0;color:#555;font-size:13px;border-bottom:1px solid #f0f0f0'>"
        f"<span style='background:#f5f5f5;padding:2px 6px;border-radius:4px;font-size:11px;margin-right:6px'>{icon}</span>"
        f"{title}</td>"
        f"<td style='padding:6px 0;color:#888;font-size:12px;border-bottom:1px solid #f0f0f0;text-align:right'>{detail}</td>"
        f"</tr>"
    )


def _stat_pill(label: str, value: str) -> str:
    return (
        f"<span style='display:inline-block;background:#f5f5f5;border-radius:6px;"
        f"padding:4px 10px;margin:0 4px 6px 0;font-size:12px;color:#555'>"
        f"<strong style='color:#222'>{value}</strong> {label}</span>"
    )


def _build_competitor_block(competitor: dict, summary: Optional[dict],
                             changes: list, settings) -> str:
    hostname = competitor["hostname"]
    comp_id = competitor["id"]
    dashboard_url = f"{settings.public_base_url}/dashboard/{comp_id}"
    week_changes = len(changes)

    # Header row
    header = (
        f"<div style='border-bottom:2px solid #a3f000;padding-bottom:8px;margin-bottom:16px;"
        f"display:flex;justify-content:space-between;align-items:baseline'>"
        f"<span style='font-size:15px;font-weight:700;color:#111'>{hostname}</span>"
        f"<span style='font-size:12px;color:#888'>{week_changes} change{'s' if week_changes != 1 else ''} this week</span>"
        f"</div>"
    )

    # AI summary or stats fallback
    if summary and summary.get("summary_text"):
        body = (
            f"<p style='font-size:13px;color:#444;line-height:1.6;margin:0 0 16px'>"
            f"{summary['summary_text']}</p>"
        )
    else:
        snap = competitor.get("_snap") or {}
        pills = ""
        if snap.get("product_count"):
            pills += _stat_pill("products", str(snap["product_count"]))
        if snap.get("median_price"):
            pills += _stat_pill("median price", f"${snap['median_price']:.0f}")
        if snap.get("promo_rate") is not None:
            pills += _stat_pill("discounted", f"{snap['promo_rate']:.0f}%")
        body = (
            f"<p style='font-size:12px;color:#888;margin:0 0 8px'>AI summary generating — here's a snapshot:</p>"
            f"<div style='margin-bottom:16px'>{pills}</div>"
            if pills else
            f"<p style='font-size:12px;color:#888;margin:0 0 16px'>First scan complete. AI summary will appear next week.</p>"
        )

    # Change rows (top 3)
    change_html = ""
    if changes:
        rows = "".join(_format_change_row(c) for c in changes[:3])
        change_html = (
            f"<table style='width:100%;border-collapse:collapse;margin-bottom:16px'>"
            f"{rows}"
            f"</table>"
        )

    cta = (
        f"<a href='{dashboard_url}' style='display:inline-block;background:#a3f000;color:#0a1628;"
        f"padding:8px 18px;border-radius:6px;text-decoration:none;font-weight:600;font-size:13px'>"
        f"View dashboard →</a>"
    )

    return (
        f"<div style='background:#fff;border:1px solid #e8e8e8;border-radius:10px;"
        f"padding:20px;margin-bottom:20px'>"
        f"{header}{body}{change_html}{cta}"
        f"</div>"
    )


@celery.task(name="app.tasks.alerts.send_weekly_digest_email")
def send_weekly_digest_email(user_id: str) -> dict:
    """
    Send the Monday morning weekly digest to one Pro/Agency user.
    Aggregates AI summaries + top changes for all their tracked competitors.
    """
    settings = get_settings()
    db = get_supabase()

    # Resolve email
    email = _resolve_email(db, user_id)
    if not email:
        logger.warning("No email for user %s — skipping digest", user_id)
        return {"status": "no_email"}

    # Check digest pref
    prefs = db.table("notification_prefs").select("email_weekly_digest").eq("user_id", user_id).maybe_single().execute()
    if not (prefs.data or {}).get("email_weekly_digest", True):
        return {"status": "digest_disabled"}

    # Get all active competitors (not my_store)
    comps = db.table("competitors")\
        .select("id, hostname, product_count, last_scanned_at")\
        .eq("user_id", user_id)\
        .eq("is_my_store", False)\
        .eq("is_active", True)\
        .eq("scan_status", "done")\
        .order("created_at")\
        .execute()
    competitors = comps.data or []
    if not competitors:
        return {"status": "no_competitors"}

    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    competitor_blocks = []
    total_changes = 0

    for comp in competitors:
        comp_id = comp["id"]

        # Latest AI summary
        summary_res = db.table("ai_summaries")\
            .select("summary_text, generated_at")\
            .eq("competitor_id", comp_id)\
            .order("generated_at", desc=True)\
            .limit(1)\
            .execute()
        summary = (summary_res.data or [None])[0]

        # Top changes this week by severity
        changes_res = db.table("change_events")\
            .select("*")\
            .eq("competitor_id", comp_id)\
            .gte("detected_at", week_ago)\
            .order("severity", desc=True)\
            .limit(3)\
            .execute()
        changes = changes_res.data or []
        total_changes += len(changes)

        # Attach latest snapshot stats for fallback display
        snap_res = db.table("scan_snapshots")\
            .select("product_count, median_price, promo_rate")\
            .eq("competitor_id", comp_id)\
            .order("scanned_at", desc=True)\
            .limit(1)\
            .execute()
        comp["_snap"] = (snap_res.data or [{}])[0]

        competitor_blocks.append(_build_competitor_block(comp, summary, changes, settings))

    if not competitor_blocks:
        return {"status": "no_data"}

    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=7)).strftime("%b %-d")
    week_end = now.strftime("%b %-d, %Y")
    date_range = f"{week_start}–{week_end}"
    n_comps = len(competitor_blocks)

    # Subject: highlight the most active competitor if possible
    if n_comps == 1:
        subject = f"{competitors[0]['hostname']} — your weekly digest"
    elif total_changes > 0:
        subject = f"Weekly digest: {total_changes} change{'s' if total_changes != 1 else ''} across {n_comps} competitors"
    else:
        subject = f"Your weekly StoreScout digest — {date_range}"

    blocks_html = "\n".join(competitor_blocks)
    settings_url = f"{settings.public_base_url}/settings"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
  <div style="max-width:580px;margin:32px auto;padding:0 16px 32px">

    <!-- Header -->
    <div style="background:#0a1628;padding:24px 28px;border-radius:12px 12px 0 0">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="color:#a3f000;font-weight:700;font-size:16px">StoreScout</span>
        <span style="color:#6b7fa3;font-size:12px">Weekly digest</span>
      </div>
      <p style="color:#c8d8f0;font-size:22px;font-weight:700;margin:12px 0 0">{date_range}</p>
    </div>

    <!-- Body -->
    <div style="background:#f9f9f9;padding:24px 28px;border:1px solid #e0e0e0;border-top:none;border-radius:0 0 12px 12px">
      <p style="color:#555;font-size:13px;margin:0 0 20px">
        Tracking <strong>{n_comps} competitor{'s' if n_comps != 1 else ''}</strong> ·
        <strong>{total_changes} change{'s' if total_changes != 1 else ''}</strong> detected this week
      </p>

      {blocks_html}

      <!-- Footer -->
      <p style="text-align:center;color:#aaa;font-size:11px;margin-top:8px">
        <a href="{settings_url}" style="color:#aaa">Manage notifications</a>
        &nbsp;·&nbsp;
        <a href="{settings_url}" style="color:#aaa">StoreScout settings</a>
      </p>
    </div>
  </div>
</body></html>"""

    try:
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.resend_from,
            "to": email,
            "subject": subject,
            "html": html,
        })
        logger.info("Weekly digest sent to %s (%d competitors, %d changes)", email, n_comps, total_changes)
        return {"status": "sent", "competitors": n_comps, "changes": total_changes}
    except Exception as exc:
        logger.error("Weekly digest failed for user %s: %s", user_id, exc)
        return {"status": "error", "reason": str(exc)}


# ── First-scan email ──────────────────────────────────────────────────────────

_CARD_COLORS = {
    "signal": ("#a3f000", "rgba(163,240,0,0.12)", "Most notable signal"),
    "opportunity": ("#60a5fa", "rgba(96,165,250,0.12)", "Your opening"),
    "watch": ("#facc15", "rgba(250,204,21,0.12)", "Watch this"),
}


def _build_brief_card_html(card: dict) -> str:
    ctype = card.get("type", "signal")
    color, bg, label = _CARD_COLORS.get(ctype, _CARD_COLORS["signal"])
    headline = card.get("headline", "")
    body = card.get("body", "")
    return (
        f"<div style='background:{bg};border:1px solid {color}30;border-left:3px solid {color};"
        f"border-radius:12px;padding:16px 18px;margin-bottom:12px'>"
        f"<div style='font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;"
        f"color:{color};margin-bottom:6px'>{label}</div>"
        f"<div style='font-size:14px;font-weight:600;color:#eef3fa;margin-bottom:6px'>{headline}</div>"
        f"<div style='font-size:13px;color:#8aa0b8;line-height:1.5'>{body}</div>"
        f"</div>"
    )


@celery.task(name="app.tasks.alerts.send_first_scan_email", queue="priority",
             bind=True, max_retries=3)
def send_first_scan_email(self, competitor_id: str) -> dict:
    """
    Fires once, 2+ minutes after a competitor's first scan completes.
    Sends the 3-card Intelligence Brief via email.
    """
    import json as _json

    settings = get_settings()
    db = get_supabase()

    comp = db.table("competitors")\
        .select("hostname, user_id, is_my_store, product_count")\
        .eq("id", competitor_id)\
        .maybe_single()\
        .execute()
    if not comp or not comp.data or comp.data.get("is_my_store"):
        return {"status": "skipped"}

    hostname = comp.data["hostname"]
    user_id = comp.data["user_id"]
    product_count = comp.data.get("product_count") or 0

    email = _resolve_email(db, user_id)
    if not email:
        return {"status": "no_email"}

    # Fetch the brief
    brief_res = db.table("ai_summaries")\
        .select("summary_text")\
        .eq("competitor_id", competitor_id)\
        .eq("summary_type", "brief")\
        .order("generated_at", desc=True)\
        .limit(1)\
        .execute()

    if not brief_res.data:
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=30 * (2 ** self.request.retries))
        return {"status": "no_brief_after_retries"}

    try:
        brief_data = _json.loads(brief_res.data[0]["summary_text"])
        cards = brief_data.get("cards", [])
    except Exception:
        cards = []

    if not cards:
        return {"status": "empty_cards"}

    cards_html = "".join(_build_brief_card_html(c) for c in cards[:3])
    dashboard_url = f"{settings.public_base_url}/dashboard/{competitor_id}"
    product_label = f"{product_count:,} products analyzed · " if product_count else ""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#060d18;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
  <div style="max-width:560px;margin:0 auto;padding:32px 16px">

    <div style="margin-bottom:28px">
      <div style="color:#a3f000;font-weight:700;font-size:18px;margin-bottom:16px">StoreScout</div>
      <h1 style="color:#eef3fa;font-size:22px;font-weight:700;margin:0 0 8px;line-height:1.3">
        Your first scan of {hostname} is ready
      </h1>
      <p style="color:#6b7fa3;font-size:13px;margin:0">{product_label}here's what stood out</p>
    </div>

    {cards_html}

    <a href="{dashboard_url}"
       style="display:block;background:#a3f000;color:#060d18;text-decoration:none;
              text-align:center;padding:14px 24px;border-radius:12px;
              font-weight:700;font-size:15px;margin-top:24px">
      View full analysis →
    </a>

    <p style="color:#2a3a4a;font-size:11px;text-align:center;margin-top:24px">
      StoreScout &nbsp;·&nbsp;
      <a href="{settings.public_base_url}/settings" style="color:#2a3a4a">Manage notifications</a>
    </p>
  </div>
</body></html>"""

    try:
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.resend_from,
            "to": email,
            "subject": f"Your first scan of {hostname} is ready",
            "html": html,
        })
        logger.info("First-scan email sent to %s for competitor %s", email, competitor_id)
        return {"status": "sent"}
    except Exception as exc:
        logger.error("First-scan email failed (attempt %d): %s", self.request.retries + 1, exc)
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
