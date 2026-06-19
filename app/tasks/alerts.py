from __future__ import annotations
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import requests
import resend

from .celery_app import celery
from app.core.config import get_settings
from app.core.database import get_supabase
from app.services.action_templates import action_for_change as _action_for_change_tmpl

logger = logging.getLogger(__name__)

ALERT_COOLDOWN_HOURS = 4

_SEVERITY_STYLES = {
    "critical": ("#f87171", "rgba(248,113,113,.15)", "CRITICAL"),
    "warning":  ("#facc15", "rgba(250,204,21,.15)",  "WARNING"),
    "info":     ("#60a5fa", "rgba(96,165,250,.15)",   "INFO"),
}

_CHANGE_TYPE_PREF = {
    "price_change":        "email_price_changes",
    "bulk_price_change":   "email_price_changes",
    "new_product":         "email_new_products",
    "bulk_new_products":   "email_new_products",
    "product_removed":     "email_new_products",
    "bulk_removal":        "email_new_products",
    "discount_start":      "email_discount_changes",
    "discount_end":        "email_discount_changes",
    "availability_change": "email_price_changes",
}

_BULK_TYPES = {"bulk_price_change", "bulk_new_products", "bulk_removal"}


def _effective_count(c: dict) -> int:
    """Return the number of products this change event represents."""
    if c.get("change_type") in _BULK_TYPES:
        cnt = (c.get("old_value") or {}).get("count")
        return cnt if isinstance(cnt, int) and cnt > 0 else 1
    return 1


def _interpret_changes(hostname: str, change_list: list, settings) -> Optional[str]:
    """1-2 sentence Claude Haiku interpretation of a batch of changes. Non-fatal if it fails."""
    try:
        import anthropic
        price_drop_events = [c for c in change_list
                             if c["change_type"] in ("price_change", "bulk_price_change")
                             and (c.get("delta_pct") or 0) < 0]
        n_price_drops = sum(_effective_count(c) for c in price_drop_events)
        n_new = sum(_effective_count(c) for c in change_list
                    if c["change_type"] in ("new_product", "bulk_new_products"))
        critical = any(c["severity"] == "critical" for c in change_list)

        lines = []
        if critical and price_drop_events:
            avg_drop = sum(abs(c.get("delta_pct") or 0) for c in price_drop_events) / len(price_drop_events)
            lines.append(f"Flash sale: {n_price_drops} products dropped avg {avg_drop:.0f}%")
        elif price_drop_events:
            avg_drop = sum(abs(c.get("delta_pct") or 0) for c in price_drop_events) / len(price_drop_events)
            lines.append(f"{n_price_drops} price drops averaging -{avg_drop:.0f}%")
        if n_new:
            lines.append(f"{n_new} new products launched")
        for c in change_list[:3]:
            ct = c.get("change_type", "")
            if ct == "price_change":
                ov = c.get("old_value") or {}
                nv = c.get("new_value") or {}
                lines.append(f"  - {(c.get('product_title') or '?')[:40]}: "
                              f"${ov.get('price','?')} → ${nv.get('price','?')}")
            elif ct == "bulk_price_change":
                ov = c.get("old_value") or {}
                count = ov.get("count", "several")
                sample = ov.get("sample") or []
                first = (sample[0].get("title") or "")[:30] if sample else ""
                lines.append(f"  - {count} products repriced" + (f" (e.g. {first})" if first else ""))
            elif ct == "bulk_new_products":
                count = (c.get("old_value") or {}).get("count", "several")
                lines.append(f"  - {count} new products added")
            elif ct == "bulk_removal":
                count = (c.get("old_value") or {}).get("count", "several")
                lines.append(f"  - {count} products removed from catalog")

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


def _action_for_email(change_list: list, hostname: str) -> Optional[str]:
    """Pick the highest-priority change and return an action recommendation."""
    if not change_list:
        return None
    ranked = sorted(
        change_list,
        key=lambda c: (
            {"critical": 0, "warning": 1, "info": 2}.get(c.get("severity", "info"), 2),
            -abs(c.get("delta_pct") or 0),
        ),
    )
    return _action_for_change_tmpl(ranked[0], hostname)


def _build_alert_html(hostname: str, subject: str, n: int, change_list: list,
                      interpretation: Optional[str], dashboard_url: str, settings) -> str:
    sev = "info"
    if any(c["severity"] == "critical" for c in change_list):
        sev = "critical"
    elif any(c["severity"] == "warning" for c in change_list):
        sev = "warning"
    sev_color, sev_bg, sev_label = _SEVERITY_STYLES[sev]

    rows_html = ""
    for c in change_list[:10]:
        c_sev = c.get("severity", "info")
        c_color = _SEVERITY_STYLES.get(c_sev, _SEVERITY_STYLES["info"])[0]
        ct = c["change_type"]
        ov = c.get("old_value") or {}
        nv = c.get("new_value") or {}

        if ct == "bulk_price_change":
            count = ov.get("count", "several")
            sample = ov.get("sample") or []
            sample_names = [s.get("title") or s.get("handle") or "" for s in sample[:3]]
            icon, title = "~", f"{count} products repriced"
            detail = " · ".join(n[:25] for n in sample_names if n) or ""
        elif ct == "bulk_new_products":
            count = ov.get("count", "several")
            sample = ov.get("sample") or []
            sample_names = [s.get("title") or s.get("handle") or "" for s in sample[:3]]
            icon, title = "+", f"{count} new products"
            detail = " · ".join(n[:25] for n in sample_names if n) or ""
        elif ct == "bulk_removal":
            count = ov.get("count", "several")
            sample = ov.get("sample") or []
            sample_names = [s.get("title") or s.get("handle") or "" for s in sample[:3]]
            icon, title = "−", f"{count} products removed"
            detail = " · ".join(n[:25] for n in sample_names if n) or ""
        elif ct == "price_change":
            icon = "↓" if (c.get("delta_pct") or 0) < 0 else "↑"
            title = (c.get("product_title") or ct.replace("_", " ").title())[:55]
            delta = c.get("delta_pct") or 0
            detail = f"${ov.get('price','?')} → ${nv.get('price','?')} ({delta:+.0f}%)"
        elif ct == "new_product":
            icon = "+"
            title = (c.get("product_title") or ct.replace("_", " ").title())[:55]
            p = nv.get("price_min")
            detail = f"${p}" if p else ""
        elif ct in ("discount_start", "discount_end"):
            icon = "Sale" if ct == "discount_start" else "↑"
            title = (c.get("product_title") or ct.replace("_", " ").title())[:55]
            detail = f"{ov.get('discounted_pct',0):.0f}% → {nv.get('discounted_pct',0):.0f}% of catalog"
        else:
            _fallback = {"product_removed": "−", "availability_change": "Stock"}
            icon = _fallback.get(ct, "·")
            title = (c.get("product_title") or ct.replace("_", " ").title())[:55]
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
            f"<div style='background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.2);"
            f"border-left:3px solid #22c55e;border-radius:8px;padding:14px 16px;margin-bottom:20px'>"
            f"<div style='font-size:10px;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:.05em;color:#22c55e;margin-bottom:6px'>What this likely means</div>"
            f"<p style='color:#c8d8f0;font-size:13px;line-height:1.5;margin:0'>{interpretation}</p>"
            f"</div>"
        )

    your_move = _action_for_email(change_list, hostname)
    your_move_block = ""
    if your_move:
        your_move_block = (
            f"<div style='background:rgba(96,165,250,.08);border-left:3px solid #60a5fa;"
            f"border-radius:8px;padding:14px 16px;margin-bottom:20px'>"
            f"<div style='font-size:10px;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:.05em;color:#60a5fa;margin-bottom:6px'>▶ Your Move</div>"
            f"<p style='color:#c8d8f0;font-size:13px;line-height:1.5;margin:0'>{your_move}</p>"
            f"</div>"
        )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#060d18;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<div style="max-width:560px;margin:0 auto;padding:32px 16px">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
    <span style="color:#3b82f6;font-weight:700;font-size:16px">StoreScout</span>
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
  {your_move_block}
  <a href="{dashboard_url}"
     style="display:block;background:#3b82f6;color:#ffffff;text-decoration:none;
            text-align:center;padding:14px 24px;border-radius:12px;font-weight:700;font-size:15px">
    View full dashboard →
  </a>
  <p style="color:#2a3a4a;font-size:11px;text-align:center;margin-top:24px">
    StoreScout &nbsp;·&nbsp;
    <a href="{settings.public_base_url}/settings" style="color:#2a3a4a">Manage notifications</a>
  </p>
</div>
</body></html>"""


def _send_slack_webhook(url: str, hostname: str, subject: str, change_list: list,
                        interpretation: Optional[str], dashboard_url: str, severity: str) -> None:
    """Post a Slack Block Kit message to an incoming webhook URL. Non-fatal."""
    sev_emoji = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(severity, "ℹ️")

    change_lines = []
    for c in change_list[:5]:
        ct = c.get("change_type", "")
        title = (c.get("product_title") or ct.replace("_", " ").title())[:50]
        ov = c.get("old_value") or {}
        nv = c.get("new_value") or {}
        delta = c.get("delta_pct")
        if ct == "price_change" and delta is not None:
            change_lines.append(f"• *{title}*: ${ov.get('price','?')} → ${nv.get('price','?')} ({delta:+.0f}%)")
        elif ct == "new_product":
            price = nv.get("price_min")
            change_lines.append(f"• *{title}*: New product{f' · ${price}' if price else ''}")
        elif ct in ("discount_start", "discount_end"):
            change_lines.append(f"• *{title}*: {ov.get('discounted_pct',0):.0f}% → {nv.get('discounted_pct',0):.0f}% of catalog discounted")
        else:
            change_lines.append(f"• *{title}*")

    if len(change_list) > 5:
        change_lines.append(f"_…and {len(change_list) - 5} more_")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{sev_emoji} {subject}", "emoji": True},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(change_lines) or "_No details_"},
        },
    ]
    if interpretation:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*What this likely means:*\n{interpretation}"},
        })
    blocks.append({
        "type": "actions",
        "elements": [{
            "type": "button",
            "text": {"type": "plain_text", "text": "View Dashboard", "emoji": True},
            "url": dashboard_url,
            "style": "primary",
        }],
    })

    try:
        resp = requests.post(url, json={"text": subject, "blocks": blocks}, timeout=10)
        if not resp.ok:
            logger.warning("Slack webhook returned %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning("Slack webhook failed (non-fatal): %s", exc)


def _send_generic_webhook(url: str, hostname: str, competitor_id: str,
                          change_list: list, severity: str, dashboard_url: str) -> None:
    """POST a clean JSON payload to a user-configured webhook URL. Non-fatal."""
    def _format_change(c: dict) -> dict:
        ct = c.get("change_type", "")
        ov = c.get("old_value") or {}
        nv = c.get("new_value") or {}
        return {
            "type": ct,
            "severity": c.get("severity", "info"),
            "product": c.get("product_title") or ct,
            "product_url": c.get("product_url"),
            "old_price": ov.get("price"),
            "new_price": nv.get("price"),
            "delta_pct": c.get("delta_pct"),
        }

    payload = {
        "event": "competitor_alert",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": hostname,
        "competitor_id": competitor_id,
        "severity": severity,
        "changes_count": len(change_list),
        "dashboard_url": dashboard_url,
        "changes": [_format_change(c) for c in change_list[:20]],
    }

    try:
        resp = requests.post(url, json=payload, timeout=10,
                             headers={"Content-Type": "application/json", "User-Agent": "StoreScout/1.0"})
        if not resp.ok:
            logger.warning("Generic webhook returned %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning("Generic webhook failed (non-fatal): %s", exc)


def _resolve_email(db, user_id: str) -> Optional[str]:
    """Return the user's email, falling back to Auth admin API if user_profiles.email is blank."""
    user = db.table("user_profiles").select("email, tier").eq("id", user_id).maybe_single().execute()
    email = (((user and user.data) or {}).get("email") or "").strip()
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
    if not (user and user.data) or user.data.get("tier", "free") == "free":
        return {"status": "no_alerts_free_tier"}

    email = _resolve_email(db, user_id)
    if not email:
        logger.error("No email found for user %s — cannot send alert", user_id)
        return {"status": "no_email"}

    prefs = db.table("notification_prefs").select("*").eq("user_id", user_id).maybe_single().execute()
    prefs_data = (prefs and prefs.data) or {}

    competitor = db.table("competitors").select("hostname, store_url").eq("id", competitor_id).maybe_single().execute()
    if not (competitor and competitor.data):
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

    # Filter change list by per-type notification preferences
    change_list = [
        c for c in change_list
        if prefs_data.get(_CHANGE_TYPE_PREF.get(c.get("change_type", ""), "email_price_changes"), True)
    ]
    if not change_list:
        return {"status": "all_change_types_disabled"}

    # Build subject using effective counts (bulk rows represent many products)
    n = len(change_list)
    n_effective = sum(_effective_count(c) for c in change_list)
    critical = [c for c in change_list if c["severity"] == "critical"]
    if critical:
        subject = f"Flash sale detected at {hostname} — {n_effective} price changes"
    else:
        price_events = [c for c in change_list if c["change_type"] in ("price_change", "bulk_price_change")]
        new_events = [c for c in change_list if c["change_type"] in ("new_product", "bulk_new_products")]
        n_prices = sum(_effective_count(c) for c in price_events)
        n_new = sum(_effective_count(c) for c in new_events)
        if price_events and new_events:
            subject = f"{hostname} — {n_prices} price changes + {n_new} new products"
        elif price_events:
            subject = f"Price change detected at {hostname} ({n_prices} products)"
        elif new_events:
            subject = f"{hostname} launched {n_new} new product{'s' if n_new > 1 else ''}"
        else:
            subject = f"Competitor update at {hostname} ({n_effective} changes)"

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

        # Fire webhooks (non-fatal, run after marking to avoid duplicate emails on retry)
        overall_severity = "critical" if any(c["severity"] == "critical" for c in change_list) \
            else "warning" if any(c["severity"] == "warning" for c in change_list) else "info"

        if prefs_data.get("slack_enabled") and prefs_data.get("slack_webhook_url"):
            _send_slack_webhook(
                prefs_data["slack_webhook_url"], hostname, subject,
                change_list, interpretation, dashboard_url, overall_severity,
            )
        if prefs_data.get("webhook_enabled") and prefs_data.get("webhook_url"):
            _send_generic_webhook(
                prefs_data["webhook_url"], hostname, competitor_id,
                change_list, overall_severity, dashboard_url,
            )

        return {"status": "sent"}
    except Exception as exc:
        logger.error("Alert email failed (attempt %d): %s", self.request.retries + 1, exc)
        # Exponential backoff: 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# ── Batched alert flush ───────────────────────────────────────────────────────

def _build_multi_alert_html(sections: list, settings) -> tuple:
    """Build (subject, html) for a combined multi-competitor alert email.

    sections: list of (comp_id, hostname, change_list) tuples.
    """
    n_comps = len(sections)
    overall_sev = "info"
    for _, _, chlist in sections:
        if any(c["severity"] == "critical" for c in chlist):
            overall_sev = "critical"
            break
        if any(c["severity"] == "warning" for c in chlist):
            overall_sev = "warning"
    sev_color, sev_bg, sev_label = _SEVERITY_STYLES[overall_sev]
    total_changes = sum(sum(_effective_count(c) for c in chlist) for _, _, chlist in sections)

    hostnames = [h for _, h, _ in sections]
    if n_comps == 2:
        subject = f"{hostnames[0]} + {hostnames[1]} — {total_changes} changes detected"
    else:
        subject = f"{n_comps} competitors — {total_changes} changes detected"

    sections_html = ""
    for i, (comp_id, hostname, change_list) in enumerate(sections):
        dashboard_url = f"{settings.public_base_url}/dashboard/{comp_id}"
        n_eff = sum(_effective_count(c) for c in change_list)
        interp = _interpret_changes(hostname, change_list, settings)
        your_move = _action_for_email(change_list, hostname)

        rows_html = ""
        for c in change_list[:5]:
            c_sev = c.get("severity", "info")
            c_color = _SEVERITY_STYLES.get(c_sev, _SEVERITY_STYLES["info"])[0]
            ct = c["change_type"]
            ov = c.get("old_value") or {}
            nv = c.get("new_value") or {}
            if ct == "bulk_price_change":
                count = ov.get("count", "several")
                icon, title, detail = "~", f"{count} products repriced", ""
            elif ct == "bulk_new_products":
                count = ov.get("count", "several")
                icon, title, detail = "+", f"{count} new products", ""
            elif ct == "bulk_removal":
                count = ov.get("count", "several")
                icon, title, detail = "−", f"{count} products removed", ""
            elif ct == "price_change":
                icon = "↓" if (c.get("delta_pct") or 0) < 0 else "↑"
                title = (c.get("product_title") or ct.replace("_", " ").title())[:50]
                delta = c.get("delta_pct") or 0
                detail = f"${ov.get('price','?')} → ${nv.get('price','?')} ({delta:+.0f}%)"
            elif ct == "new_product":
                icon = "+"
                title = (c.get("product_title") or "New Product")[:50]
                p = nv.get("price_min")
                detail = f"${p}" if p else ""
            else:
                icon = "·"
                title = (c.get("product_title") or ct.replace("_", " ").title())[:50]
                detail = ""
            rows_html += (
                f"<tr>"
                f"<td style='padding:6px 0;border-bottom:1px solid #1e3a5f'>"
                f"<span style='color:{c_color};font-weight:700;font-size:12px;margin-right:8px'>{icon}</span>"
                f"<span style='color:#c8d8f0;font-size:13px'>{title}</span></td>"
                f"<td style='padding:6px 0;border-bottom:1px solid #1e3a5f;color:#8aa0b8;"
                f"font-size:12px;text-align:right'>{detail}</td>"
                f"</tr>"
            )

        interp_snippet = (
            f"<p style='color:#8aa0b8;font-size:12px;font-style:italic;margin:10px 0 6px;line-height:1.5'>{interp}</p>"
            if interp else ""
        )
        move_snippet = (
            f"<p style='color:#60a5fa;font-size:12px;margin:6px 0 0;line-height:1.5'>"
            f"<strong>▶</strong> {your_move}</p>"
            if your_move else ""
        )
        divider = (
            "<div style='border-top:1px solid #1e3a5f;margin:20px 0'></div>"
            if i < n_comps - 1 else ""
        )

        sections_html += (
            f"<div>"
            f"<div style='display:flex;justify-content:space-between;align-items:baseline;margin-bottom:10px'>"
            f"<span style='color:#eef3fa;font-size:15px;font-weight:700'>{hostname}</span>"
            f"<span style='color:#6b7fa3;font-size:12px'>{n_eff} change{'s' if n_eff != 1 else ''}</span>"
            f"</div>"
            f"<div style='background:#0e1d35;border:1px solid #1e3a5f;border-radius:10px;padding:12px 16px;margin-bottom:10px'>"
            f"<table style='width:100%;border-collapse:collapse'>{rows_html}</table>"
            f"</div>"
            f"{interp_snippet}{move_snippet}"
            f"<a href='{dashboard_url}' style='display:inline-block;color:#60a5fa;font-size:13px;"
            f"font-weight:600;text-decoration:none;margin-top:10px'>View {hostname} →</a>"
            f"{divider}"
            f"</div>"
        )

    all_url = f"{settings.public_base_url}/competitors"
    settings_url = f"{settings.public_base_url}/settings"
    html = (
        f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'></head>"
        f"<body style='margin:0;padding:0;background:#060d18;"
        f"font-family:-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif'>"
        f"<div style='max-width:560px;margin:0 auto;padding:32px 16px'>"
        f"<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:16px'>"
        f"<span style='color:#3b82f6;font-weight:700;font-size:16px'>StoreScout</span>"
        f"<span style='background:{sev_bg};color:{sev_color};border:1px solid {sev_color}40;"
        f"padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700'>{sev_label}</span>"
        f"</div>"
        f"<h1 style='color:#eef3fa;font-size:20px;font-weight:700;margin:0 0 6px;line-height:1.3'>"
        f"{n_comps} competitors had activity</h1>"
        f"<p style='color:#6b7fa3;font-size:13px;margin:0 0 24px'>"
        f"{total_changes} total change{'s' if total_changes != 1 else ''} in the last 30 minutes</p>"
        f"{sections_html}"
        f"<a href='{all_url}' style='display:block;background:#3b82f6;color:#ffffff;"
        f"text-decoration:none;text-align:center;padding:14px 24px;border-radius:12px;"
        f"font-weight:700;font-size:15px;margin-top:24px'>View all dashboards →</a>"
        f"<p style='color:#2a3a4a;font-size:11px;text-align:center;margin-top:24px'>"
        f"StoreScout &nbsp;·&nbsp;"
        f"<a href='{settings_url}' style='color:#2a3a4a'>Manage notifications</a></p>"
        f"</div></body></html>"
    )
    return subject, html


def _send_free_alert_email(db, user_id: str, email: str, competitor_ids: list,
                           changes_by_comp: dict, settings) -> dict:
    """Send a simplified weekly change summary to free-tier users.

    Shows change counts per competitor (no product detail) and teases the upgrade.
    """
    # Count changes per competitor and collect all IDs to mark as sent
    rows_html = ""
    all_change_ids: list = []
    total = 0
    for comp_id in competitor_ids:
        change_ids = changes_by_comp.get(comp_id) or []
        if not change_ids:
            continue
        comp = db.table("competitors").select("hostname").eq("id", comp_id).maybe_single().execute()
        hostname = (comp.data or {}).get("hostname", comp_id) if comp else comp_id
        n = len(change_ids)
        total += n
        all_change_ids.extend(change_ids)
        rows_html += (
            f"<tr>"
            f"<td style='padding:8px 0;border-bottom:1px solid #1e3a5f;color:#c8d8f0;font-size:13px'>"
            f"<span style='color:#60a5fa;margin-right:8px'>◉</span>{hostname}</td>"
            f"<td style='padding:8px 0;border-bottom:1px solid #1e3a5f;color:#6b7fa3;"
            f"font-size:12px;text-align:right'>{n} change{'s' if n != 1 else ''}</td>"
            f"</tr>"
        )

    if not rows_html:
        return {"status": "no_changes"}

    competitors_url = f"{settings.public_base_url}/competitors"
    upgrade_url = f"{settings.public_base_url}/settings?upgrade=1"
    settings_url = f"{settings.public_base_url}/settings"
    n_comps = len([c for c in competitor_ids if changes_by_comp.get(c)])

    subject = f"Activity at your tracked store — {total} change{'s' if total != 1 else ''} this week"

    html = (
        f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'></head>"
        f"<body style='margin:0;padding:0;background:#060d18;"
        f"font-family:-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif'>"
        f"<div style='max-width:560px;margin:0 auto;padding:32px 16px'>"
        f"<div style='margin-bottom:20px'>"
        f"<span style='color:#3b82f6;font-weight:700;font-size:16px;letter-spacing:-.3px'>StoreScout</span>"
        f"</div>"
        f"<h1 style='color:#eef3fa;font-size:20px;font-weight:700;margin:0 0 6px'>"
        f"Your weekly scan is complete</h1>"
        f"<p style='color:#6b7fa3;font-size:14px;margin:0 0 20px'>"
        f"We detected {total} change{'s' if total != 1 else ''} across your "
        f"{n_comps} tracked competitor{'s' if n_comps != 1 else ''} this week.</p>"
        f"<div style='background:#0e1d35;border:1px solid #1e3a5f;border-radius:12px;"
        f"padding:16px 20px;margin-bottom:20px'>"
        f"<table style='width:100%;border-collapse:collapse'>{rows_html}</table>"
        f"</div>"
        f"<div style='background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.2);"
        f"border-left:3px solid #3b82f6;border-radius:8px;padding:14px 16px;margin-bottom:20px'>"
        f"<div style='font-size:10px;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:.05em;color:#60a5fa;margin-bottom:6px'>Upgrade to Pro</div>"
        f"<p style='color:#c8d8f0;font-size:13px;line-height:1.5;margin:0 0 10px'>"
        f"Get alerted within 15 minutes of any price change, new launch, or discount — "
        f"plus daily scans so you never miss a move.</p>"
        f"<a href='{upgrade_url}' style='display:inline-block;background:#3b82f6;color:#ffffff;"
        f"padding:9px 18px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px'>"
        f"Get real-time alerts — $29/month →</a>"
        f"</div>"
        f"<a href='{competitors_url}' style='display:block;background:#0e1d35;color:#c8d8f0;"
        f"text-decoration:none;text-align:center;padding:12px 24px;border-radius:12px;"
        f"font-weight:600;font-size:14px;border:1px solid #1e3a5f'>View your dashboard →</a>"
        f"<p style='color:#1e3a5f;font-size:11px;text-align:center;margin-top:24px'>"
        f"StoreScout &nbsp;·&nbsp;"
        f"<a href='{settings_url}' style='color:#1e3a5f'>Manage notifications</a>"
        f"</p>"
        f"</div></body></html>"
    )

    try:
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.resend_from,
            "to": email,
            "subject": subject,
            "html": html,
        })
        # Mark as alerted so detect_changes doesn't try again for 7 days
        if all_change_ids:
            db.table("change_events").update({"alert_sent": True}).in_("id", all_change_ids).execute()
        logger.info("Free weekly alert sent to %s (%d changes, %d competitors)", email, total, n_comps)
        return {"status": "sent", "competitors": n_comps, "changes": total}
    except Exception as exc:
        logger.error("Free weekly alert failed for %s: %s", email, exc)
        return {"status": "error", "reason": str(exc)}


@celery.task(name="app.tasks.alerts.flush_alert_batch", queue="priority",
             bind=True, max_retries=2)
def flush_alert_batch(self, user_id: str) -> dict:
    """Flush the 30-minute alert batch for a user.

    Reads all accumulated competitor IDs + change IDs from Redis, then sends one
    combined email (Pro/Agency) or one simplified weekly teaser (free tier).
    """
    settings = get_settings()
    db = get_supabase()

    try:
        import redis as _r
        r = _r.from_url(settings.redis_url, socket_connect_timeout=2)
    except Exception as exc:
        logger.error("flush_alert_batch: Redis unavailable for user %s: %s", user_id, exc)
        return {"status": "redis_unavailable"}

    batch_key = f"alert_batch:{user_id}"
    sched_key = f"alert_batch_sched:{user_id}"
    raw_ids = r.smembers(batch_key) or set()
    competitor_ids = [x.decode() for x in raw_ids]

    if not competitor_ids:
        return {"status": "nothing_pending"}

    # Collect change IDs per competitor, then atomically wipe Redis state
    changes_by_comp: dict = {}
    pipe = r.pipeline()
    for cid in competitor_ids:
        comp_key = f"alert_batch_changes:{user_id}:{cid}"
        changes_by_comp[cid] = [x.decode() for x in (r.smembers(comp_key) or [])]
        pipe.delete(comp_key)
    pipe.delete(batch_key)
    pipe.delete(sched_key)
    pipe.execute()

    # Resolve tier and email
    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    tier = (user.data or {}).get("tier", "free")
    email = _resolve_email(db, user_id)
    if not email:
        logger.error("flush_alert_batch: no email for user %s", user_id)
        return {"status": "no_email"}

    # ── Free tier: simplified weekly teaser (max once per 7 days via Redis TTL) ─
    if tier == "free":
        free_key = f"free_alert_sent:{user_id}"
        if r.exists(free_key):
            return {"status": "free_cooldown"}
        r.setex(free_key, 7 * 24 * 3600, "1")
        return _send_free_alert_email(db, user_id, email, competitor_ids, changes_by_comp, settings)

    # ── Pro/Agency: collect eligible changes and send one combined email ──────
    prefs = db.table("notification_prefs").select("*").eq("user_id", user_id).maybe_single().execute()
    prefs_data = (prefs and prefs.data) or {}

    sections: list = []   # (comp_id, hostname, change_list)
    all_alert_ids: list = []

    for comp_id in competitor_ids:
        change_ids = changes_by_comp.get(comp_id) or []
        if not change_ids:
            continue
        if _within_cooldown(db, user_id, comp_id):
            logger.info("flush_alert_batch: %s in cooldown, skipping", comp_id)
            continue
        comp = db.table("competitors").select("hostname").eq("id", comp_id).maybe_single().execute()
        if not (comp and comp.data):
            continue
        hostname = comp.data["hostname"]
        changes = (
            db.table("change_events").select("*")
            .in_("id", change_ids)
            .order("severity", desc=True)
            .execute()
        )
        change_list = [
            c for c in (changes.data or [])
            if prefs_data.get(
                _CHANGE_TYPE_PREF.get(c.get("change_type", ""), "email_price_changes"), True
            )
        ]
        if change_list:
            sections.append((comp_id, hostname, change_list))
            all_alert_ids.extend(c["id"] for c in change_list)

    if not sections:
        return {"status": "no_eligible_changes"}

    try:
        if len(sections) == 1:
            comp_id, hostname, change_list = sections[0]
            n = len(change_list)
            n_eff = sum(_effective_count(c) for c in change_list)
            critical = [c for c in change_list if c["severity"] == "critical"]
            price_ev = [c for c in change_list if c["change_type"] in ("price_change", "bulk_price_change")]
            new_ev   = [c for c in change_list if c["change_type"] in ("new_product", "bulk_new_products")]
            if critical:
                subject = f"Flash sale at {hostname} — {n_eff} price changes"
            elif price_ev and new_ev:
                n_p = sum(_effective_count(c) for c in price_ev)
                n_n = sum(_effective_count(c) for c in new_ev)
                subject = f"{hostname} — {n_p} price changes + {n_n} new products"
            elif price_ev:
                n_p = sum(_effective_count(c) for c in price_ev)
                subject = f"Price change at {hostname} ({n_p} products)"
            elif new_ev:
                n_n = sum(_effective_count(c) for c in new_ev)
                subject = f"{hostname} launched {n_n} new product{'s' if n_n != 1 else ''}"
            else:
                subject = f"Competitor update at {hostname} ({n_eff} changes)"
            interp = _interpret_changes(hostname, change_list, settings)
            dashboard_url = f"{settings.public_base_url}/dashboard/{comp_id}"
            html = _build_alert_html(hostname, subject, n, change_list, interp, dashboard_url, settings)
        else:
            subject, html = _build_multi_alert_html(sections, settings)

        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.resend_from,
            "to": email,
            "subject": subject,
            "html": html,
        })
        db.table("change_events").update({"alert_sent": True}).in_("id", all_alert_ids).execute()
        logger.info(
            "flush_alert_batch: sent to %s covering %d competitor(s) (%d change IDs)",
            email, len(sections), len(all_alert_ids),
        )
        return {"status": "sent", "competitors": len(sections)}
    except Exception as exc:
        logger.error("flush_alert_batch failed (attempt %d): %s", self.request.retries + 1, exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# ── Weekly digest ─────────────────────────────────────────────────────────────

def _change_icon(change_type: str, delta_pct: float) -> str:
    return {
        "price_change":      "↓" if delta_pct < 0 else "↑",
        "bulk_price_change": "~",
        "new_product":       "＋",
        "bulk_new_products": "＋",
        "product_removed":   "−",
        "bulk_removal":      "−",
        "discount_start":    "Sale",
        "discount_end":      "Sale ended",
        "availability_change": "Stock",
    }.get(change_type, "·")


def _format_change_row(c: dict) -> str:
    ctype = c.get("change_type", "")
    old_v = c.get("old_value") or {}
    new_v = c.get("new_value") or {}
    delta = c.get("delta_pct") or 0
    icon = _change_icon(ctype, delta)

    if ctype == "price_change":
        title = (c.get("product_title") or "Product")[:60]
        detail = f"${old_v.get('price','?')} → ${new_v.get('price','?')} ({delta:+.1f}%)"
    elif ctype == "new_product":
        title = (c.get("product_title") or "New Product")[:60]
        p = new_v.get("price_min")
        detail = f"${p}" if p else "New"
    elif ctype in ("discount_start", "discount_end"):
        title = (c.get("product_title") or ctype.replace("_", " ").title())[:60]
        detail = f"{old_v.get('discounted_pct',0):.0f}% → {new_v.get('discounted_pct',0):.0f}% of catalog"
    elif ctype == "bulk_price_change":
        count = old_v.get("count", "several")
        title = f"{count} products repriced"
        detail = f"avg {delta:+.1f}%" if delta else ""
    elif ctype == "bulk_new_products":
        count = old_v.get("count", "several")
        title = f"{count} new products"
        sample = old_v.get("sample") or []
        detail = (sample[0].get("title") or "")[:40] if sample else ""
    elif ctype == "bulk_removal":
        count = old_v.get("count", "several")
        title = f"{count} products removed"
        sample = old_v.get("sample") or []
        detail = (sample[0].get("title") or "")[:40] if sample else ""
    else:
        title = (c.get("product_title") or ctype.replace("_", " ").title())[:60]
        detail = ""

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
        f"<div style='border-bottom:2px solid #3b82f6;padding-bottom:8px;margin-bottom:16px;"
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
        f"<a href='{dashboard_url}' style='display:inline-block;background:#3b82f6;color:#ffffff;"
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
    if not ((prefs and prefs.data) or {}).get("email_weekly_digest", True):
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
        <span style="color:#3b82f6;font-weight:700;font-size:16px">StoreScout</span>
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
    "signal": ("#22c55e", "rgba(34,197,94,0.12)", "Most notable signal"),
    "opportunity": ("#60a5fa", "rgba(96,165,250,0.12)", "Your opening"),
    "watch": ("#facc15", "rgba(250,204,21,0.12)", "Watch this"),
    "action": ("#4ade80", "rgba(74,222,128,0.12)", "Your move"),
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


def _build_multi_first_scan_html(ready_comps: list, briefs_by_comp: dict, settings) -> tuple:
    """Build subject + HTML for a combined first-scan email covering 2+ competitors."""
    import json as _json

    n = len(ready_comps)
    subject = f"{n} competitor scans ready — here’s what we found"

    comp_sections = []
    for i, comp in enumerate(ready_comps):
        comp_id = comp["id"]
        hostname = comp.get("hostname", comp_id)
        product_count = comp.get("product_count") or 0
        dashboard_url = f"{settings.public_base_url}/dashboard/{comp_id}"

        # Parse cards from brief
        cards = []
        brief_row = briefs_by_comp.get(comp_id)
        if brief_row:
            try:
                brief_data = _json.loads(brief_row["summary_text"])
                cards = brief_data.get("cards", [])
            except Exception:
                cards = []

        # Pick best card: type "signal" first, else first card
        best_card = None
        for card in cards:
            if card.get("type") == "signal":
                best_card = card
                break
        if best_card is None and cards:
            best_card = cards[0]

        product_label = (
            f"<span style='color:#6b7fa3;font-size:13px;margin-left:10px'>"
            f"{product_count:,} products</span>"
            if product_count else ""
        )

        card_html = _build_brief_card_html(best_card) if best_card else ""

        divider = (
            "<div style='border-top:1px solid #0e1d35;margin:20px 0'></div>"
            if i < n - 1 else ""
        )

        comp_sections.append(
            f"<div>"
            f"<div style='margin-bottom:12px'>"
            f"<span style='color:#eef3fa;font-size:15px;font-weight:700'>{hostname}</span>"
            f"{product_label}"
            f"</div>"
            f"{card_html}"
            f"<a href='{dashboard_url}' style='display:inline-block;background:#1e3a5f;"
            f"color:#60a5fa;padding:7px 14px;border-radius:8px;font-size:13px;"
            f"font-weight:600;text-decoration:none'>View {hostname} →</a>"
            f"</div>"
            f"{divider}"
        )

    sections_html = "\n".join(comp_sections)
    settings_url = f"{settings.public_base_url}/settings"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#060d18;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
  <div style="max-width:560px;margin:0 auto;padding:32px 16px">

    <div style="margin-bottom:28px">
      <div style="color:#3b82f6;font-weight:700;font-size:18px;margin-bottom:16px">StoreScout</div>
      <h1 style="color:#eef3fa;font-size:22px;font-weight:700;margin:0 0 8px;line-height:1.3">
        Your {n} competitor scans are ready
      </h1>
      <p style="color:#6b7fa3;font-size:13px;margin:0">Here's the top finding from each</p>
    </div>

    {sections_html}

    <p style="color:#3a5068;font-size:11px;text-align:center;margin-top:24px">
      StoreScout &nbsp;·&nbsp;
      <a href="{settings_url}" style="color:#3a5068">Manage notifications</a>
    </p>
  </div>
</body></html>"""

    return subject, html


@celery.task(name="app.tasks.alerts.send_first_scan_email", queue="priority",
             bind=True, max_retries=3)
def send_first_scan_email(self, competitor_id: str) -> dict:
    """
    Fires 10 minutes after a competitor's first scan brief is generated.
    Batches all ready competitors for the same user into a single email (one per hour).
    """
    import json as _json

    settings = get_settings()
    db = get_supabase()

    # Resolve user_id from this competitor
    comp = db.table("competitors")\
        .select("hostname, user_id, is_my_store, product_count")\
        .eq("id", competitor_id)\
        .maybe_single()\
        .execute()
    if not comp or not comp.data or comp.data.get("is_my_store"):
        return {"status": "skipped"}

    user_id = comp.data["user_id"]

    email = _resolve_email(db, user_id)
    if not email:
        return {"status": "no_email"}

    # Hourly rate-limit: at most one batch email per user per hour
    hour_key = f"first_scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H')}"
    try:
        db.table("drip_log").insert({"user_id": user_id, "drip_type": hour_key}).execute()
    except Exception:
        # Unique constraint violation — another concurrent task already claimed this slot
        return {"status": "race_condition_skip"}

    # Gather ALL ready competitors for this user
    comps_res = db.table("competitors")\
        .select("id, hostname, product_count")\
        .eq("user_id", user_id)\
        .eq("is_my_store", False)\
        .eq("is_active", True)\
        .eq("scan_status", "done")\
        .execute()
    comps = comps_res.data or []

    if not comps:
        return {"status": "no_ready_competitors"}

    comp_ids = [c["id"] for c in comps]

    # Fetch briefs for all of them
    briefs_res = db.table("ai_summaries")\
        .select("competitor_id, summary_text")\
        .in_("competitor_id", comp_ids)\
        .eq("summary_type", "brief")\
        .order("generated_at", desc=True)\
        .execute()

    # Build a dict keyed by competitor_id (latest brief per competitor)
    briefs_by_comp: dict = {}
    for row in (briefs_res.data or []):
        cid = row["competitor_id"]
        if cid not in briefs_by_comp:
            briefs_by_comp[cid] = row

    # Only include competitors that have a brief ready
    ready_comps = [c for c in comps if c["id"] in briefs_by_comp]

    if not ready_comps:
        return {"status": "no_briefs_ready"}

    if len(ready_comps) == 1:
        # Single-competitor email — existing dark design
        sole = ready_comps[0]
        hostname = sole["hostname"]
        product_count = sole.get("product_count") or 0
        dashboard_url = f"{settings.public_base_url}/dashboard/{sole['id']}"

        try:
            brief_data = _json.loads(briefs_by_comp[sole["id"]]["summary_text"])
            cards = brief_data.get("cards", [])
        except Exception:
            cards = []

        if not cards:
            return {"status": "empty_cards"}

        cards_html = "".join(_build_brief_card_html(c) for c in cards[:4])
        product_label = f"{product_count:,} products analyzed · " if product_count else ""

        if product_count > 0:
            subject = f"Your first scan of {hostname} is ready — {product_count:,} products analyzed"
        else:
            subject = f"Your first scan of {hostname} is ready"

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#060d18;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
  <div style="max-width:560px;margin:0 auto;padding:32px 16px">

    <div style="margin-bottom:28px">
      <div style="color:#3b82f6;font-weight:700;font-size:18px;margin-bottom:16px">StoreScout</div>
      <h1 style="color:#eef3fa;font-size:22px;font-weight:700;margin:0 0 8px;line-height:1.3">
        Your first scan of {hostname} is ready
      </h1>
      <p style="color:#6b7fa3;font-size:13px;margin:0">{product_label}here's what stood out</p>
    </div>

    {cards_html}

    <a href="{dashboard_url}"
       style="display:block;background:#3b82f6;color:#ffffff;text-decoration:none;
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

    else:
        # Multi-competitor batch email
        subject, html = _build_multi_first_scan_html(ready_comps, briefs_by_comp, settings)

    try:
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.resend_from,
            "to": email,
            "subject": subject,
            "html": html,
        })
        logger.info(
            "First-scan batch email sent to %s covering %d competitor(s)",
            email, len(ready_comps),
        )
        return {"status": "sent", "competitors": len(ready_comps)}
    except Exception as exc:
        logger.error("First-scan email failed (attempt %d): %s", self.request.retries + 1, exc)
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
