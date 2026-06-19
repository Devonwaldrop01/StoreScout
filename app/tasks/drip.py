from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import resend

from .celery_app import celery
from app.core.config import get_settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

# ── helpers ───────────────────────────────────────────────────────────────────

def _resolve_email(db, user_id: str) -> Optional[str]:
    user = db.table("user_profiles").select("email").eq("id", user_id).maybe_single().execute()
    email = ((user.data or {}).get("email") or "").strip()
    if not email:
        try:
            auth_user = db.auth.admin.get_user_by_id(user_id)
            email = (auth_user.user.email or "").strip() if auth_user.user else ""
        except Exception as exc:
            logger.warning("Could not fetch auth email for user %s: %s", user_id, exc)
    return email or None


def _has_sent(db, user_id: str, drip_type: str) -> bool:
    try:
        result = db.table("drip_log").select("id")\
            .eq("user_id", user_id).eq("drip_type", drip_type).limit(1).execute()
        return bool(result.data)
    except Exception:
        return False


def _record_sent(db, user_id: str, drip_type: str) -> None:
    try:
        db.table("drip_log").insert({"user_id": user_id, "drip_type": drip_type}).execute()
    except Exception:
        pass  # UNIQUE violation = already recorded, fine


def _send(settings, to: str, subject: str, html: str) -> None:
    resend.api_key = settings.resend_api_key
    resend.Emails.send({"from": settings.resend_from, "to": to, "subject": subject, "html": html})


# ── HTML primitives ───────────────────────────────────────────────────────────

_OPEN = (
    "<!DOCTYPE html><html><head><meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width,initial-scale=1'></head>"
    "<body style='margin:0;padding:0;background:#060d18;"
    "font-family:-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif'>"
    "<div style='max-width:560px;margin:0 auto;padding:32px 16px'>"
    "<div style='margin-bottom:20px'>"
    "<span style='color:#3b82f6;font-weight:700;font-size:16px;letter-spacing:-.3px'>StoreScout</span>"
    "</div>"
)

_CLOSE = (
    "<p style='color:#1e3a5f;font-size:11px;text-align:center;margin-top:28px'>"
    "StoreScout &nbsp;·&nbsp; "
    "<a href='{settings_url}' style='color:#1e3a5f'>Manage notifications</a>"
    "</p></div></body></html>"
)


def _cta(text: str, url: str) -> str:
    return (
        f"<a href='{url}' style='display:inline-block;background:#3b82f6;color:#ffffff;"
        f"padding:13px 24px;border-radius:10px;text-decoration:none;"
        f"font-weight:700;font-size:14px;margin-top:16px'>{text}</a>"
    )


def _card(content: str) -> str:
    return (
        f"<div style='background:#0e1d35;border:1px solid #1e3a5f;border-radius:12px;"
        f"padding:20px 24px;margin-bottom:16px'>{content}</div>"
    )


def _pill(label: str, value: str) -> str:
    return (
        f"<span style='display:inline-block;background:#071526;border:1px solid #1e3a5f;"
        f"color:#c8d8f0;border-radius:8px;padding:6px 14px;margin:0 6px 8px 0;font-size:13px'>"
        f"<strong style='color:#eef3fa'>{value}</strong> {label}</span>"
    )


def _check_row(label: str, sub: str) -> str:
    return (
        f"<tr>"
        f"<td style='padding:7px 0;border-bottom:1px solid #1e3a5f;color:#c8d8f0;font-size:13px'>"
        f"<span style='color:#22c55e;margin-right:8px'>✓</span>{label}</td>"
        f"<td style='padding:7px 0;border-bottom:1px solid #1e3a5f;color:#6b7fa3;"
        f"font-size:12px;text-align:right'>{sub}</td>"
        f"</tr>"
    )


# ── email builders ────────────────────────────────────────────────────────────

def _d0_html(hostname: str, competitor_id: str, snapshot_data: dict, settings) -> str:
    pricing   = snapshot_data.get("pricing") or {}
    catalog   = snapshot_data.get("catalog") or {}
    discounts = snapshot_data.get("discounts") or {}
    takeaways = (snapshot_data.get("takeaways") or [])[:2]

    pills = ""
    if catalog.get("total_products"):
        pills += _pill("products", str(catalog["total_products"]))
    if pricing.get("median"):
        pills += _pill("median price", f"${pricing['median']:.0f}")
    if discounts.get("discounted_pct") is not None:
        pills += _pill("running promos", f"{discounts['discounted_pct']:.0f}%")

    takeaway_html = ""
    if takeaways:
        items = "".join(
            f"<li style='margin-bottom:6px;color:#c8d8f0;font-size:13px;line-height:1.5'>{t}</li>"
            for t in takeaways
        )
        takeaway_html = (
            f"<div style='border-top:1px solid #1e3a5f;padding-top:14px;margin-top:14px'>"
            f"<p style='color:#6b7fa3;font-size:11px;text-transform:uppercase;letter-spacing:.05em;"
            f"margin:0 0 8px'>Key observations</p>"
            f"<ul style='padding-left:16px;margin:0'>{items}</ul></div>"
        )

    dashboard_url = f"{settings.public_base_url}/dashboard/{competitor_id}"
    upgrade_url   = f"{settings.public_base_url}/settings?upgrade=1"

    body = (
        f"<h1 style='color:#eef3fa;font-size:20px;font-weight:700;margin:0 0 6px'>"
        f"Your first scan is ready 👀</h1>"
        f"<p style='color:#6b7fa3;font-size:14px;margin:0 0 20px'>"
        f"We finished scanning <strong style='color:#c8d8f0'>{hostname}</strong>. "
        f"Here's the snapshot:</p>"
        + _card(f"<div style='margin-bottom:4px'>{pills}</div>{takeaway_html}")
        + _cta("See full dashboard →", dashboard_url)
        + f"<p style='color:#3a5068;font-size:12px;margin:18px 0 0'>"
        f"Free plan: 1 competitor, weekly scans. &nbsp;"
        f"<a href='{upgrade_url}' style='color:#60a5fa;text-decoration:none'>"
        f"Upgrade to Pro</a> for daily scans + price-change alerts.</p>"
    )
    return _OPEN + body + _CLOSE.format(settings_url=f"{settings.public_base_url}/settings")


def _d1_html(hostname: str, competitor_id: str, settings) -> str:
    upgrade_url   = f"{settings.public_base_url}/settings?upgrade=1"
    dashboard_url = f"{settings.public_base_url}/dashboard/{competitor_id}"

    rows = "".join(_check_row(label, sub) for label, sub in [
        ("Track up to 10 competitors",           "vs 1 on free"),
        ("Daily automatic scans",                "vs weekly"),
        ("Price-change alerts within 15 min",    "email + Slack"),
        ("90 days of price history",             "charts + trends"),
        ("AI weekly digest every Monday",        "Claude-powered"),
    ])

    body = (
        f"<h1 style='color:#eef3fa;font-size:20px;font-weight:700;margin:0 0 6px'>"
        f"Most operators track 3–5 competitors</h1>"
        f"<p style='color:#6b7fa3;font-size:14px;margin:0 0 20px'>"
        f"You're watching <strong style='color:#c8d8f0'>{hostname}</strong>. "
        f"Upgrade to Pro to add up to 10 stores and get alerted the moment anything changes.</p>"
        + _card(f"<table style='width:100%;border-collapse:collapse'>{rows}</table>")
        + _cta("Upgrade to Pro — $29/month →", upgrade_url)
        + f"<p style='color:#3a5068;font-size:12px;margin:18px 0 0'>"
        f"<a href='{dashboard_url}' style='color:#60a5fa;text-decoration:none'>"
        f"Keep exploring your free dashboard →</a></p>"
    )
    return _OPEN + body + _CLOSE.format(settings_url=f"{settings.public_base_url}/settings")


def _d3_html(hostname: str, competitor_id: str, changes: list, settings) -> str:
    upgrade_url = f"{settings.public_base_url}/settings?upgrade=1"

    if changes:
        rows = ""
        for c in changes[:4]:
            ct    = c.get("change_type", "")
            title = (c.get("product_title") or ct.replace("_", " ").title())[:52]
            delta = c.get("delta_pct") or 0
            icon  = "↓" if (ct == "price_change" and delta < 0) else "+" if ct == "new_product" else "·"
            rows += (
                f"<tr>"
                f"<td style='padding:8px 0;border-bottom:1px solid #1e3a5f;"
                f"color:#c8d8f0;font-size:13px'>"
                f"<span style='color:#60a5fa;font-weight:700;margin-right:8px'>{icon}</span>{title}</td>"
                f"<td style='padding:8px 0;border-bottom:1px solid #1e3a5f;color:#6b7fa3;"
                f"font-size:12px;text-align:right;filter:blur(4px)'>$XX.XX</td></tr>"
            )
        changes_block = (
            _card(f"<table style='width:100%;border-collapse:collapse'>{rows}</table>")
            + f"<p style='color:#6b7fa3;font-size:12px;margin:-8px 0 16px;text-align:center'>"
            f"↑ {len(changes)} change{'s' if len(changes) != 1 else ''} detected — "
            f"upgrade to see exact prices</p>"
        )
    else:
        changes_block = _card(
            f"<p style='color:#6b7fa3;font-size:13px;text-align:center;margin:0'>"
            f"No changes detected at {hostname} yet.</p>"
        )

    body = (
        f"<h1 style='color:#eef3fa;font-size:20px;font-weight:700;margin:0 0 6px'>"
        f"What's changed at {hostname}?</h1>"
        f"<p style='color:#6b7fa3;font-size:14px;margin:0 0 20px'>"
        f"Pro users get alerted within 15 minutes of any price change, new launch, or discount. "
        f"Here's a preview of what they see:</p>"
        + changes_block
        + _cta("Start getting alerts — $29/month →", upgrade_url)
    )
    return _OPEN + body + _CLOSE.format(settings_url=f"{settings.public_base_url}/settings")


def _d7_html(hostname: str, competitor_id: str, snapshot_data: dict, changes: list, settings) -> str:
    upgrade_url   = f"{settings.public_base_url}/settings?upgrade=1"
    dashboard_url = f"{settings.public_base_url}/dashboard/{competitor_id}"
    pricing   = snapshot_data.get("pricing") or {}
    catalog   = snapshot_data.get("catalog") or {}
    discounts = snapshot_data.get("discounts") or {}

    pills = ""
    if catalog.get("total_products"):
        pills += _pill("products", str(catalog["total_products"]))
    if pricing.get("median"):
        pills += _pill("median price", f"${pricing['median']:.0f}")
    if discounts.get("discounted_pct") is not None:
        pills += _pill("promo rate", f"{discounts['discounted_pct']:.0f}%")

    changes_line = (
        f"<p style='color:#c8d8f0;font-size:13px;margin:14px 0 0'>"
        f"<strong>{len(changes)}</strong> change{'s' if len(changes) != 1 else ''} "
        f"detected this week — Pro users were alerted in real time.</p>"
    ) if changes else ""

    body = (
        f"<h1 style='color:#eef3fa;font-size:20px;font-weight:700;margin:0 0 6px'>"
        f"Week 1 snapshot: {hostname}</h1>"
        f"<p style='color:#6b7fa3;font-size:14px;margin:0 0 20px'>"
        f"You've been tracking {hostname} for a week. Here's where things stand:</p>"
        + _card(f"<div>{pills}</div>{changes_line}")
        + f"<p style='color:#6b7fa3;font-size:14px;margin:0 0 16px'>"
        f"Pro users get this every Monday, plus daily scans and real-time alerts.</p>"
        + _cta("Upgrade to Pro — $29/month →", upgrade_url)
        + f"<p style='color:#3a5068;font-size:12px;margin:18px 0 0'>"
        f"<a href='{dashboard_url}' style='color:#60a5fa;text-decoration:none'>"
        f"View your dashboard →</a></p>"
    )
    return _OPEN + body + _CLOSE.format(settings_url=f"{settings.public_base_url}/settings")


def _d14_html(hostname: str, competitor_id: str, snapshot_data: dict, settings) -> str:
    upgrade_url   = f"{settings.public_base_url}/settings?upgrade=1"
    dashboard_url = f"{settings.public_base_url}/dashboard/{competitor_id}"
    takeaways     = (snapshot_data.get("takeaways") or [])[:3]

    if not takeaways:
        takeaways = [
            f"{hostname} has been consistently updating their catalog.",
            "Pricing and promotional patterns are becoming clearer.",
            "With 2 weeks of data, trend signals are now detectable.",
        ]

    observations = "".join(
        f"<div style='display:flex;gap:14px;margin-bottom:14px;align-items:flex-start'>"
        f"<span style='color:#3b82f6;font-weight:700;font-size:20px;line-height:1;flex-shrink:0'>"
        f"0{i + 1}</span>"
        f"<p style='color:#c8d8f0;font-size:13px;line-height:1.6;margin:2px 0 0'>{t}</p></div>"
        for i, t in enumerate(takeaways)
    )

    body = (
        f"<h1 style='color:#eef3fa;font-size:20px;font-weight:700;margin:0 0 6px'>"
        f"3 things we noticed about {hostname}</h1>"
        f"<p style='color:#6b7fa3;font-size:14px;margin:0 0 20px'>"
        f"Two weeks in. Here's what the data shows:</p>"
        + _card(observations)
        + f"<p style='color:#6b7fa3;font-size:14px;margin:0 0 16px'>"
        f"Pro users get a deeper AI analysis every week: pricing strategy signals, "
        f"launch velocity trends, and specific actions to consider.</p>"
        + _cta("Get weekly AI insights — $29/month →", upgrade_url)
        + f"<p style='color:#3a5068;font-size:12px;margin:18px 0 0'>"
        f"<a href='{dashboard_url}' style='color:#60a5fa;text-decoration:none'>"
        f"View your dashboard →</a></p>"
    )
    return _OPEN + body + _CLOSE.format(settings_url=f"{settings.public_base_url}/settings")


# ── tasks ─────────────────────────────────────────────────────────────────────

@celery.task(name="app.tasks.drip.send_drip_d0")
def send_drip_d0(user_id: str, competitor_id: str) -> dict:
    """Day 0 (+5 min) — first scan complete. Fires for all tiers."""
    from datetime import timezone
    settings = get_settings()
    db = get_supabase()

    if _has_sent(db, user_id, "d0"):
        return {"status": "already_sent"}

    # Skip if the AI brief batch email was already sent this hour (better, more detailed email)
    hour_key = f"first_scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H')}"
    recent_brief_email = db.table("drip_log").select("id")\
        .eq("user_id", user_id).eq("drip_type", hour_key).limit(1).execute()
    if recent_brief_email.data:
        _record_sent(db, user_id, "d0")  # mark as done so it won't retry
        return {"status": "brief_email_handled_d0_skipped"}

    email = _resolve_email(db, user_id)
    if not email:
        return {"status": "no_email"}

    comp = db.table("competitors").select("hostname").eq("id", competitor_id).maybe_single().execute()
    hostname = (comp.data or {}).get("hostname") or competitor_id

    snap = db.table("scan_snapshots")\
        .select("snapshot_data")\
        .eq("competitor_id", competitor_id)\
        .order("scanned_at", desc=True)\
        .limit(1)\
        .execute()
    snapshot_data = ((snap.data or [{}])[0]).get("snapshot_data") or {}

    html = _d0_html(hostname, competitor_id, snapshot_data, settings)
    try:
        _send(settings, email, f"Your first scan is ready — here's what we found on {hostname}", html)
        _record_sent(db, user_id, "d0")
        return {"status": "sent"}
    except Exception as exc:
        logger.error("Drip d0 failed: %s", exc)
        return {"status": "error", "reason": str(exc)}


@celery.task(name="app.tasks.drip.send_drip_d1")
def send_drip_d1(user_id: str, competitor_id: str) -> dict:
    """Day 1 — add second competitor nudge. Free tier only."""
    settings = get_settings()
    db = get_supabase()

    if _has_sent(db, user_id, "d1"):
        return {"status": "already_sent"}

    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    if (user.data or {}).get("tier", "free") != "free":
        return {"status": "skipped_upgraded"}

    email = _resolve_email(db, user_id)
    if not email:
        return {"status": "no_email"}

    comp = db.table("competitors").select("hostname").eq("id", competitor_id).maybe_single().execute()
    hostname = (comp.data or {}).get("hostname") or competitor_id

    html = _d1_html(hostname, competitor_id, settings)
    try:
        _send(settings, email, f"Pro tip: track a second competitor alongside {hostname}", html)
        _record_sent(db, user_id, "d1")
        return {"status": "sent"}
    except Exception as exc:
        logger.error("Drip d1 failed: %s", exc)
        return {"status": "error", "reason": str(exc)}


@celery.task(name="app.tasks.drip.send_drip_d3")
def send_drip_d3(user_id: str, competitor_id: str) -> dict:
    """Day 3 — change-detection teaser with blurred prices. Free tier only."""
    settings = get_settings()
    db = get_supabase()

    if _has_sent(db, user_id, "d3"):
        return {"status": "already_sent"}

    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    if (user.data or {}).get("tier", "free") != "free":
        return {"status": "skipped_upgraded"}

    email = _resolve_email(db, user_id)
    if not email:
        return {"status": "no_email"}

    comp = db.table("competitors").select("hostname").eq("id", competitor_id).maybe_single().execute()
    hostname = (comp.data or {}).get("hostname") or competitor_id

    three_days_ago = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    changes_res = db.table("change_events")\
        .select("change_type, product_title, delta_pct")\
        .eq("competitor_id", competitor_id)\
        .gte("detected_at", three_days_ago)\
        .order("severity", desc=True)\
        .limit(5)\
        .execute()

    html = _d3_html(hostname, competitor_id, changes_res.data or [], settings)
    try:
        _send(settings, email, f"Did {hostname} change anything this week?", html)
        _record_sent(db, user_id, "d3")
        return {"status": "sent"}
    except Exception as exc:
        logger.error("Drip d3 failed: %s", exc)
        return {"status": "error", "reason": str(exc)}


@celery.task(name="app.tasks.drip.send_drip_d7")
def send_drip_d7(user_id: str, competitor_id: str) -> dict:
    """Day 7 — mini-digest with snapshot stats. Free tier only."""
    settings = get_settings()
    db = get_supabase()

    if _has_sent(db, user_id, "d7"):
        return {"status": "already_sent"}

    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    if (user.data or {}).get("tier", "free") != "free":
        return {"status": "skipped_upgraded"}

    email = _resolve_email(db, user_id)
    if not email:
        return {"status": "no_email"}

    comp = db.table("competitors").select("hostname").eq("id", competitor_id).maybe_single().execute()
    hostname = (comp.data or {}).get("hostname") or competitor_id

    snap = db.table("scan_snapshots")\
        .select("snapshot_data")\
        .eq("competitor_id", competitor_id)\
        .order("scanned_at", desc=True)\
        .limit(1)\
        .execute()
    snapshot_data = ((snap.data or [{}])[0]).get("snapshot_data") or {}

    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    changes_res = db.table("change_events")\
        .select("id")\
        .eq("competitor_id", competitor_id)\
        .gte("detected_at", week_ago)\
        .execute()

    html = _d7_html(hostname, competitor_id, snapshot_data, changes_res.data or [], settings)
    try:
        _send(settings, email, f"Week 1 snapshot: what's happening at {hostname}", html)
        _record_sent(db, user_id, "d7")
        return {"status": "sent"}
    except Exception as exc:
        logger.error("Drip d7 failed: %s", exc)
        return {"status": "error", "reason": str(exc)}


@celery.task(name="app.tasks.drip.send_drip_d14")
def send_drip_d14(user_id: str, competitor_id: str) -> dict:
    """Day 14 — 3 data-driven observations + social proof. Free tier only."""
    settings = get_settings()
    db = get_supabase()

    if _has_sent(db, user_id, "d14"):
        return {"status": "already_sent"}

    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    if (user.data or {}).get("tier", "free") != "free":
        return {"status": "skipped_upgraded"}

    email = _resolve_email(db, user_id)
    if not email:
        return {"status": "no_email"}

    comp = db.table("competitors").select("hostname").eq("id", competitor_id).maybe_single().execute()
    hostname = (comp.data or {}).get("hostname") or competitor_id

    snap = db.table("scan_snapshots")\
        .select("snapshot_data")\
        .eq("competitor_id", competitor_id)\
        .order("scanned_at", desc=True)\
        .limit(1)\
        .execute()
    snapshot_data = ((snap.data or [{}])[0]).get("snapshot_data") or {}

    html = _d14_html(hostname, competitor_id, snapshot_data, settings)
    try:
        _send(settings, email, f"3 things we noticed about {hostname} (2-week update)", html)
        _record_sent(db, user_id, "d14")
        return {"status": "sent"}
    except Exception as exc:
        logger.error("Drip d14 failed: %s", exc)
        return {"status": "error", "reason": str(exc)}


# ── sequence scheduler ────────────────────────────────────────────────────────

def schedule_drip_sequence(user_id: str, competitor_id: str) -> None:
    """Enqueue the full D0–D14 sequence after a first scan completes."""
    DAY = 86_400  # seconds
    send_drip_d0.apply_async(args=[user_id, competitor_id], countdown=300)           # +5 min
    send_drip_d1.apply_async(args=[user_id, competitor_id], countdown=DAY)           # +24h
    send_drip_d3.apply_async(args=[user_id, competitor_id], countdown=3 * DAY)       # +72h
    send_drip_d7.apply_async(args=[user_id, competitor_id], countdown=7 * DAY)       # +7d
    send_drip_d14.apply_async(args=[user_id, competitor_id], countdown=14 * DAY)     # +14d
