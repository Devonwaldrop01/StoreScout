from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from typing import List

import resend

from .celery_app import celery
from app.core.config import get_settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

# Max 1 alert email per user per competitor per N hours
ALERT_COOLDOWN_HOURS = 4


def _within_cooldown(db, user_id: str, competitor_id: str) -> bool:
    """Return True if an alert email was already sent for this competitor within the cooldown window."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=ALERT_COOLDOWN_HOURS)).isoformat()
    result = db.table("change_events")\
        .select("id")\
        .eq("competitor_id", competitor_id)\
        .eq("alert_sent", True)\
        .gte("detected_at", cutoff)\
        .limit(1)\
        .execute()
    return bool(result.data)


@celery.task(name="app.tasks.alerts.send_change_alert", queue="priority")
def send_change_alert(user_id: str, competitor_id: str, change_ids: List[str]) -> dict:
    settings = get_settings()
    db = get_supabase()

    if _within_cooldown(db, user_id, competitor_id):
        return {"status": "cooldown"}

    # Fetch user prefs and email
    user = db.table("user_profiles").select("email, tier").eq("id", user_id).maybe_single().execute()
    if not user.data or user.data.get("tier", "free") == "free":
        return {"status": "no_alerts_free_tier"}

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

    # Build HTML email body
    change_rows = ""
    for c in change_list[:10]:
        icon = {"price_change": "📉" if (c.get("delta_pct") or 0) < 0 else "📈",
                "new_product": "🆕",
                "product_removed": "🗑️",
                "discount_start": "🏷️",
                "discount_end": "✅",
                "availability_change": "📦"}.get(c["change_type"], "•")
        title = c.get("product_title") or c["change_type"].replace("_", " ").title()
        old_v = c.get("old_value") or {}
        new_v = c.get("new_value") or {}
        detail = ""
        if c["change_type"] == "price_change":
            delta = c.get("delta_pct", 0) or 0
            detail = f"${old_v.get('price', '?')} → ${new_v.get('price', '?')} ({delta:+.1f}%)"
        elif c["change_type"] == "new_product":
            price = (new_v.get("price_min") or "")
            detail = f"${price}" if price else ""
        elif c["change_type"] in ("discount_start", "discount_end"):
            detail = f"{old_v.get('discounted_pct', 0):.0f}% → {new_v.get('discounted_pct', 0):.0f}% of catalog discounted"
        change_rows += f"<tr><td style='padding:8px 0;border-bottom:1px solid #eee'>{icon} {title}</td><td style='padding:8px 0;border-bottom:1px solid #eee;color:#666'>{detail}</td></tr>"

    dashboard_url = f"{settings.public_base_url}/dashboard/{competitor_id}"
    email_html = f"""
<div style="font-family:sans-serif;max-width:560px;margin:0 auto">
  <div style="background:#0a1628;padding:24px 32px;border-radius:12px 12px 0 0">
    <h2 style="color:#a3f000;margin:0;font-size:18px">StoreScout Alert</h2>
  </div>
  <div style="background:#fff;padding:32px;border:1px solid #eee;border-top:none;border-radius:0 0 12px 12px">
    <h3 style="margin:0 0 8px">{subject}</h3>
    <p style="color:#666;margin:0 0 24px">We detected {n} change{'s' if n > 1 else ''} at <strong>{hostname}</strong></p>
    <table style="width:100%;border-collapse:collapse">{change_rows}</table>
    <div style="margin-top:24px">
      <a href="{dashboard_url}" style="background:#a3f000;color:#0a1628;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">
        View full dashboard →
      </a>
    </div>
    <p style="color:#999;font-size:12px;margin-top:24px">
      <a href="{settings.public_base_url}/settings" style="color:#999">Manage notification preferences</a>
    </p>
  </div>
</div>
"""

    try:
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.resend_from,
            "to": user.data["email"],
            "subject": subject,
            "html": email_html,
        })

        # Mark changes as alerted — this is also what _within_cooldown checks
        db.table("change_events").update({"alert_sent": True}).in_("id", change_ids).execute()

        return {"status": "sent"}
    except Exception as exc:
        logger.error(f"Alert email failed: {exc}")
        return {"status": "error", "reason": str(exc)}
