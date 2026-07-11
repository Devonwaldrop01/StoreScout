"""
Scheduler visibility for the staged index pipeline.

Two durable signals, both grounded in real events (never process-deployment):

  - a DISPATCH HEARTBEAT written at the start of every scheduled staged task
    (even when the pipeline is gated off), so an operator can tell "Beat is
    alive and dispatching" from "Beat is down" — persisted via runtime_config
    (app_config, migration 012), so it survives worker restarts.
  - a RUN RECORD written to `store_index_runs` whenever a staged task actually
    processes work, so the admin "Worker Runs" panel reflects real *scheduled*
    activity (previously only the unscheduled legacy task wrote run rows).

`scheduler_status` assembles an evidence-only view: the configured schedule (read
from the live Celery beat_schedule), the last recorded dispatch (+ per task),
the last/last-scheduled/last-failed run from the run table, and whether the
pipeline is enabled. It never claims health from mere deployment — "looks stale"
is derived from the age of a *recorded* heartbeat against the most frequent
task's cadence.
"""
from __future__ import annotations

import functools
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("storescout.scheduler")

_LAST_DISPATCH = "scheduler_last_dispatch"
_STAGES = ["stage_discovery", "stage_resolution", "stage_verification", "stage_knowledge"]

# The most frequent staged task (resolution) runs every 12 min, so a live Beat
# records a heartbeat at least that often. Past this window with no dispatch, the
# scheduler is probably not running — an evidence-based inference, not fabricated.
_STALE_AFTER_S = 20 * 60


def _hb_key(task: str) -> str:
    return f"scheduler_dispatch_{task}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_dispatch(stage: str) -> None:
    """Persist that Beat dispatched `stage` just now. Guarded — visibility must
    never break the task."""
    try:
        from app.services.runtime_config import set_config
        now = _now_iso()
        set_config({_LAST_DISPATCH: now, _hb_key(stage): now})
    except Exception as exc:
        logger.debug("dispatch heartbeat skipped (%s): %s", stage, exc)


def record_run(stage: str, result: Dict[str, Any]) -> None:
    """Insert a durable run record for a scheduled staged task. Maps the task's
    result dict onto the store_index_runs columns. Guarded."""
    try:
        from app.core.database import get_supabase
        db = get_supabase()

        def _n(*keys) -> int:
            for k in keys:
                v = result.get(k)
                if isinstance(v, (int, float)):
                    return int(v)
            return 0

        row = {
            "trigger": f"scheduled:{stage}",
            "processed": _n("processed", "resolved", "queued", "classified", "discovered"),
            "verified": _n("verified"),
            "rejected": _n("rejected"),
            "failed": _n("failed"),
            "duplicates": _n("duplicates"),
            "source_counts": result.get("by_source") if isinstance(result.get("by_source"), dict) else None,
            "notes": str(result.get("note") or result.get("status") or "ok")[:200],
        }
        db.table("store_index_runs").insert(row).execute()
    except Exception as exc:
        logger.debug("run record skipped (%s): %s", stage, exc)


def scheduled_index_task(stage: str) -> Callable:
    """Decorator (apply UNDER @celery.task) that records a dispatch heartbeat
    before the task runs and a run record after it actually processes work
    (status == 'ok'). Preserves the task's signature and return value."""
    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any):
            record_dispatch(stage)
            result = fn(*args, **kwargs)
            try:
                if isinstance(result, dict) and result.get("status") == "ok":
                    record_run(stage, result)
            except Exception:
                pass
            return result
        return wrapper
    return deco


def _age_seconds(iso: Optional[str]) -> Optional[float]:
    if not iso:
        return None
    try:
        t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - t).total_seconds()
    except Exception:
        return None


def scheduler_status(db) -> Dict[str, Any]:
    """Evidence-only scheduler status. Reads the configured beat_schedule, the
    recorded dispatch heartbeats, and the run table. Never infers health from
    deployment alone."""
    from app.services.runtime_config import get_config
    from app.core.config import get_settings
    settings = get_settings()

    enabled = bool(get_config("shopify_index_enabled", settings.shopify_index_enabled))

    scheduled_tasks: List[Dict[str, Any]] = []
    try:
        from app.tasks.celery_app import celery
        for name, entry in (celery.conf.beat_schedule or {}).items():
            scheduled_tasks.append({
                "name": name,
                "task": entry.get("task"),
                "schedule": str(entry.get("schedule")),
            })
    except Exception as exc:
        logger.debug("beat_schedule read failed: %s", exc)

    last_dispatch = get_config(_LAST_DISPATCH, None)
    per_task = {s: get_config(_hb_key(s), None) for s in _STAGES}

    runs: List[Dict[str, Any]] = []
    try:
        r = db.table("store_index_runs").select("*").order("ran_at", desc=True).limit(20).execute()
        runs = r.data or []
    except Exception as exc:
        logger.debug("store_index_runs read failed: %s", exc)

    last_run = runs[0]["ran_at"] if runs else None
    last_scheduled_run = next((x["ran_at"] for x in runs if str(x.get("trigger") or "").startswith("scheduled:")), None)
    last_failed_run = next((x["ran_at"] for x in runs if (x.get("failed") or 0) > 0), None)

    age = _age_seconds(last_dispatch)
    looks_stale = last_dispatch is None or (age is not None and age > _STALE_AFTER_S)

    return {
        "pipeline_enabled": enabled,
        "scheduler_configured": len(scheduled_tasks) > 0,
        "scheduled_tasks": scheduled_tasks,
        "last_dispatch": last_dispatch,
        "last_dispatch_age_seconds": int(age) if age is not None else None,
        "dispatch_looks_stale": looks_stale,
        "stale_threshold_seconds": _STALE_AFTER_S,
        "per_task_last_dispatch": per_task,
        "last_run": last_run,
        "last_scheduled_run": last_scheduled_run,
        "last_failed_run": last_failed_run,
        "queue": "default",
        "worker_consumes": ["default", "priority"],
    }
