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


def record_run(stage: str, result: Dict[str, Any], *,
               trigger: str = "scheduled", task_id: Optional[str] = None) -> None:
    """Insert exactly ONE durable run record for a staged task execution.

    Column semantics (one run = one execution of `stage`):
      · processed  — UNIQUE candidates ATTEMPTED this run. Equals the sum of the
                     terminal outcomes (verified + rejected + failed [+ reverified]).
                     Never 0 while any outcome is > 0.
      · verified   — candidates moved discovered → verified this run (NEW; the
                     stages only ever read the 'discovered' queue, so a staged
                     `verified` is always a first-time verification).
      · reverified — an already-verified store re-checked (staged pipeline: 0;
                     only the Store Inspector / legacy daily task re-verify).
      · rejected / failed — terminal negative outcomes.
      · duplicates — candidates skipped as already-present.
    `trigger` is 'scheduled:<stage>' or 'manual:<stage>'; the Celery task id is
    stored in notes for provenance. Guarded — visibility never breaks the task.
    """
    try:
        from app.core.database import get_supabase
        db = get_supabase()

        def _n(*keys) -> int:
            for k in keys:
                v = result.get(k)
                if isinstance(v, (int, float)):
                    return int(v)
            return 0

        verified = _n("verified")
        rejected = _n("rejected")
        failed = _n("failed")
        reverified = _n("reverified", "re_verified")
        duplicates = _n("duplicates")
        # processed = unique attempts. Prefer an explicit count from the task;
        # otherwise derive it from the outcomes so it can never be 0 while
        # outcomes exist (the historical "processed=0, verified=37" bug).
        explicit = _n("processed", "attempted", "resolved", "queued", "classified", "discovered")
        derived = verified + rejected + failed + reverified
        processed = max(explicit, derived)

        note = str(result.get("note") or result.get("status") or "ok")[:160]
        if task_id:
            note = f"{note} · task={task_id[:12]}"

        row = {
            "trigger": f"{trigger}:{stage}",
            "processed": processed,
            "verified": verified,
            "rejected": rejected,
            "failed": failed,
            "reverified": reverified,
            "duplicates": duplicates,
            "source_counts": result.get("by_source") if isinstance(result.get("by_source"), dict) else None,
            "notes": note,
        }
        try:
            db.table("store_index_runs").insert(row).execute()
        except Exception as col_exc:
            # `reverified` shipped in migration 008; if an older schema lacks it,
            # retry without it rather than lose the whole record.
            if "reverified" in str(col_exc).lower():
                row.pop("reverified", None)
                db.table("store_index_runs").insert(row).execute()
            else:
                raise
    except Exception as exc:
        logger.debug("run record skipped (%s): %s", stage, exc)


def _acquire_single_flight(stage: str, ttl_s: int) -> Optional[Any]:
    """Best-effort Redis single-flight lock for a staged task. Returns a redis
    client holding the lock (release via _release_single_flight), or None if the
    lock is already held (another run in progress). If Redis is unavailable we
    fail OPEN (return a sentinel) so the pipeline still runs — the worker is
    concurrency-1 today, the lock is defense-in-depth for when it scales."""
    try:
        import redis as _redis
        from app.core.config import get_settings
        r = _redis.from_url(get_settings().redis_url, socket_connect_timeout=2)
        if r.set(f"lock:index:{stage}", "1", nx=True, ex=ttl_s):
            return r
        return None  # held → skip
    except Exception as exc:
        logger.warning("single-flight lock unavailable for %s (%s) — running without lock", stage, exc)
        return _NO_REDIS  # fail open


_NO_REDIS = object()


def _release_single_flight(stage: str, holder: Any) -> None:
    if holder is None or holder is _NO_REDIS:
        return
    try:
        holder.delete(f"lock:index:{stage}")
    except Exception:
        pass


# Per-stage lock TTL (safety net if the worker dies mid-run); released in
# `finally` so back-to-back scheduled runs are never blocked by a stale lock.
_LOCK_TTL_S = {"stage_verification": 1500, "stage_resolution": 900,
               "stage_knowledge": 900, "stage_discovery": 1200}


def scheduled_index_task(stage: str) -> Callable:
    """Decorator (apply UNDER @celery.task) that:
      1. records a dispatch heartbeat before the task runs,
      2. holds a single-flight lock so a manual and a scheduled run (or two
         dispatches) of the same stage can never process concurrently, and
      3. writes exactly one run record after the task actually processes work
         (status == 'ok'). A skipped (lock-held) run writes NO record.
    Preserves the task's signature and return value."""
    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any):
            record_dispatch(stage)
            holder = _acquire_single_flight(stage, _LOCK_TTL_S.get(stage, 900))
            if holder is None:
                logger.info("%s: single-flight lock held — skipping overlapping run", stage)
                return {"status": "skipped_lock", "note": "another run in progress"}
            # Provenance: a forced run is a manual/admin invocation; a plain Beat
            # dispatch runs with force=False.
            force = kwargs.get("force")
            if force is None and len(args) >= 2:
                force = args[1]
            trigger = "manual" if force else "scheduled"
            task_id = None
            try:
                from app.tasks.celery_app import celery as _celery
                req = getattr(_celery, "current_task", None)
                task_id = getattr(getattr(req, "request", None), "id", None)
            except Exception:
                pass
            try:
                result = fn(*args, **kwargs)
                try:
                    if isinstance(result, dict) and result.get("status") == "ok":
                        record_run(stage, result, trigger=trigger, task_id=task_id)
                except Exception:
                    pass
                return result
            finally:
                _release_single_flight(stage, holder)
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
