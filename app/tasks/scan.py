from __future__ import annotations
import logging
from datetime import datetime, timezone

import httpx

from .celery_app import celery
from app.core.config import get_settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=3, default_retry_delay=30, name="app.tasks.scan.scan_competitor")
def scan_competitor(self, competitor_id: str) -> dict:
    db = get_supabase()
    settings = get_settings()

    db.table("competitors").update({
        "scan_status": "scanning",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", competitor_id).execute()

    try:
        # Delegate the actual Shopify fetch to the web service (different IP, not blocked)
        resp = httpx.post(
            f"{settings.api_internal_url}/api/v1/internal/scan/{competitor_id}",
            headers={"x-internal-token": settings.internal_secret},
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") == "ok" and data.get("snapshot_id"):
            from app.tasks.detect_changes import detect_changes
            from app.tasks.ai_summaries import generate_brief
            detect_changes.delay(competitor_id, data["snapshot_id"])
            generate_brief.delay(competitor_id, data["snapshot_id"])

        return data

    except Exception as exc:
        logger.error("Scan failed for %s: %s", competitor_id, exc)
        err_str = str(exc)
        retry_count = self.request.retries
        if retry_count >= self.max_retries:
            db.table("competitors").update({
                "scan_status": "error",
                "error_message": err_str[:500],
            }).eq("id", competitor_id).execute()
        else:
            db.table("competitors").update({"scan_status": "pending"}).eq("id", competitor_id).execute()
            raise self.retry(exc=exc, countdown=30 * (2 ** retry_count))
        return {"status": "error", "reason": err_str}


@celery.task(name="app.tasks.scan.manual_rescan")
def manual_rescan(competitor_id: str) -> dict:
    """Triggered by user — goes to priority queue."""
    return scan_competitor(competitor_id)
