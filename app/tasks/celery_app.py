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
        # ── Three-stage Competitive Intelligence Index ──────────────────────
        # DISCOVERY → VERIFICATION → KNOWLEDGE, staggered on the SAME worker so
        # no new Render process is needed. Each task no-ops unless
        # SHOPIFY_INDEX_ENABLED=true and is chunked + resumable, so these are
        # safe to ship dormant. Discovery surfaces candidates a few times a day;
        # verification (the only stage that fetches storefronts) drains the
        # queue every 30 min; knowledge classifies from stored data (no network)
        # on the off-half-hour.
        # DISCOVERY bulk-harvests raw refs into the queue (cheap) a few times a
        # day. RESOLUTION drains the queue into real domains (rate-limited).
        # VERIFICATION and KNOWLEDGE finish the funnel. All staggered on the one
        # worker; each no-ops unless SHOPIFY_INDEX_ENABLED.
        # Cadence raised to drain the discovered→verified backlog faster (index
        # coverage). Safe: @scheduled_index_task holds a single-flight lock, so a
        # run that overruns its slot is skipped (never overlaps). Each stage
        # no-ops cheaply on an empty queue, so higher frequency idles safely once
        # the backlog is drained.
        "index-stage-discovery": {
            "task": "app.tasks.store_index.stage_discovery",
            "schedule": crontab(minute=10, hour="*/4"),
        },
        # Resolution is the rate-limited bottleneck — run it often so it keeps a
        # steady stream flowing (each run self-throttles with backoff).
        "index-stage-resolution": {
            "task": "app.tasks.store_index.stage_resolution",
            "schedule": crontab(minute="*/12"),
        },
        "index-stage-verification": {
            "task": "app.tasks.store_index.stage_verification",
            "schedule": crontab(minute="*/15"),
        },
        "index-stage-knowledge": {
            "task": "app.tasks.store_index.stage_knowledge",
            "schedule": crontab(minute="*/20"),
        },
        # BREADTH: rotate through the full niche list generating candidates so the
        # index can cover almost any store a user describes. A few niches per run,
        # a few times a day — cheap (Haiku) and gated by SHOPIFY_INDEX_ENABLED.
        "index-generate-candidates": {
            "task": "app.tasks.store_index.generate_candidates_rotating",
            "schedule": crontab(minute=40, hour="*/6"),
        },
        # Legacy combined discovery pass — kept for admin manual test runs but
        # no longer scheduled (superseded by the three staged tasks above).
        # Lead discovery runs after the index refresh so it sees the freshest
        # verified stores. No-ops unless LEAD_ENGINE_ENABLED=true.
        "discover-leads-daily": {
            "task": "app.tasks.lead_engine.discover_leads_daily",
            "schedule": crontab(hour=5, minute=30),
        },
        # Intent-signal scan — inbound buying-intent from public discussions.
        # No-ops unless INTENT_ENGINE_ENABLED. Twice a day, off-peak.
        "scan-intent-signals": {
            "task": "app.tasks.lead_engine.scan_intent_signals",
            "schedule": crontab(hour="6,18", minute=15),
        },
        # Daily Intelligence Brief dispatcher — hourly; each user's brief
        # fires at their configured digest hour (default 08:00 UTC).
        "send-daily-briefs": {
            "task": "app.tasks.scheduler.send_daily_briefs_batch",
            "schedule": crontab(minute=5),
        },
    },
)
