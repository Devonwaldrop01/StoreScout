from __future__ import annotations
import logging
from datetime import datetime, timezone

from .celery_app import celery
from app.core.database import get_supabase

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.scheduler.enqueue_due_scans")
def enqueue_due_scans() -> dict:
    """Runs every 15 minutes. Finds competitors whose next_scan_at is past due and enqueues them."""
    db = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    result = db.table("competitors")\
        .select("id")\
        .eq("is_active", True)\
        .neq("scan_status", "scanning")\
        .lte("next_scan_at", now)\
        .execute()

    competitors = result.data or []
    from app.tasks.scan import scan_competitor
    for comp in competitors:
        scan_competitor.apply_async(args=[comp["id"]], queue="default")

    return {"enqueued": len(competitors)}


@celery.task(name="app.tasks.scheduler.send_weekly_digests_batch")
def send_weekly_digests_batch() -> dict:
    """Runs Monday 7am UTC. Sends weekly digest to all Pro/Agency users."""
    from app.tasks.alerts import send_weekly_digest_email
    db = get_supabase()

    users = db.table("user_profiles")\
        .select("id, email")\
        .in_("tier", ["pro", "agency"])\
        .eq("subscription_status", "active")\
        .execute()

    sent = 0
    for user in (users.data or []):
        prefs = db.table("notification_prefs")\
            .select("email_weekly_digest")\
            .eq("user_id", user["id"])\
            .maybe_single()\
            .execute()
        if (prefs.data or {}).get("email_weekly_digest", True):
            send_weekly_digest_email.delay(user["id"])
            sent += 1

    return {"sent": sent}


@celery.task(name="app.tasks.scheduler.generate_ai_summaries_batch")
def generate_ai_summaries_batch() -> dict:
    """Runs daily 2am UTC. Generates AI summaries for competitors due for weekly update."""
    from app.tasks.ai_summaries import generate_weekly_summary
    from datetime import timedelta

    db = get_supabase()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=6)).isoformat()

    # Find Pro/Agency competitors that haven't had a summary generated in 7 days
    result = db.rpc("competitors_needing_ai_summary", {"cutoff": cutoff}).execute()
    count = 0
    for row in (result.data or []):
        generate_weekly_summary.delay(row["competitor_id"], "weekly")
        count += 1

    return {"generated": count}
