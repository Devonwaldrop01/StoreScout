from __future__ import annotations
from celery import Celery
from celery.schedules import crontab
import ssl
import sys
import os

# Make sure app package is importable from worker process
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.core.config import get_settings

settings = get_settings()

celery = Celery(
    "storescout",
    broker=settings.redis_url,
    backend=None,
    include=[
        "app.tasks.scan",
        "app.tasks.detect_changes",
        "app.tasks.alerts",
        "app.tasks.ai_summaries",
        "app.tasks.playbook_ai",
        "app.tasks.drip",
        "app.tasks.scheduler",
        "app.tasks.store_index",
        "app.tasks.lead_engine",
    ],
)

_ssl_config = {"ssl_cert_reqs": ssl.CERT_NONE} if settings.redis_url.startswith("rediss://") else None

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Reduce Redis request volume — default polling is ~1/s which burns Upstash free tier fast.
    # At 5s interval, two worker processes use ~35K requests/day for polling vs ~175K at default.
    broker_transport_options={"polling_interval": 5},
    # Don't store task results — no backend is wired so results go nowhere (not read by the app).
    task_ignore_result=True,
    result_expires=1800,
    # Heartbeats every 2s (default) = ~86K Redis commands/day per worker.
    # 5-minute heartbeat + no task-state events cuts this to ~288/day per worker.
    worker_heartbeat=300,
    worker_send_task_events=False,
    task_send_sent_event=False,
    **({"broker_use_ssl": _ssl_config, "redis_backend_use_ssl": _ssl_config} if _ssl_config else {}),
    task_routes={
        "app.tasks.alerts.*": {"queue": "priority"},
        "app.tasks.scan.manual_rescan": {"queue": "priority"},
        "app.tasks.*": {"queue": "default"},
    },
    beat_schedule={
        "recover-stuck-scans": {
            "task": "app.tasks.scheduler.recover_stuck_scans",
            "schedule": crontab(minute="*/10"),
        },
        "enqueue-due-scans": {
            "task": "app.tasks.scheduler.enqueue_due_scans",
            "schedule": crontab(minute="*/15"),
        },
        "send-weekly-digests": {
            "task": "app.tasks.scheduler.send_weekly_digests_batch",
            "schedule": crontab(hour=7, minute=0, day_of_week="monday"),
        },
        "generate-ai-summaries": {
            "task": "app.tasks.scheduler.generate_ai_summaries_batch",
            "schedule": crontab(hour=2, minute=0),
        },
        # Store-index discovery — the task itself no-ops unless
        # SHOPIFY_INDEX_ENABLED=true, so this entry is safe to ship dormant.
        "discover-shopify-stores-daily": {
            "task": "app.tasks.store_index.discover_shopify_stores_daily",
            "schedule": crontab(hour=4, minute=30),
        },
        # Lead discovery runs after the index refresh so it sees the freshest
        # verified stores. No-ops unless LEAD_ENGINE_ENABLED=true.
        "discover-leads-daily": {
            "task": "app.tasks.lead_engine.discover_leads_daily",
            "schedule": crontab(hour=5, minute=30),
        },
    },
)
