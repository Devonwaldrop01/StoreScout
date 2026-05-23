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
    backend=settings.redis_url,
    include=[
        "app.tasks.scan",
        "app.tasks.detect_changes",
        "app.tasks.alerts",
        "app.tasks.ai_summaries",
        "app.tasks.drip",
        "app.tasks.scheduler",
    ],
)

_ssl_config = {"ssl_cert_reqs": ssl.CERT_NONE} if settings.redis_url.startswith("rediss://") else None

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    **({"broker_use_ssl": _ssl_config, "redis_backend_use_ssl": _ssl_config} if _ssl_config else {}),
    task_routes={
        "app.tasks.alerts.*": {"queue": "priority"},
        "app.tasks.scan.manual_rescan": {"queue": "priority"},
        "app.tasks.*": {"queue": "default"},
    },
    beat_schedule={
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
    },
)
