"""
Finite job state for background AI generation (Playbook).

The Playbook previously re-dispatched generation on every poll and reported a
per-request "generating" boolean, so a failing/never-persisting job showed
"AI analysis in progress" forever with duplicate dispatches. This adds a real,
Redis-backed job state with a timeout, so the UI resolves to a FINITE state:

    not_requested | queued | generating | ready | failed | timed_out | unavailable

`decide_ai_action` is a PURE function (unit-tested without Redis) that maps
(fresh-result?, active-job?, job-age, timeout) → (state, should_dispatch),
deduping concurrent generations and turning a stuck job into `timed_out` instead
of an infinite banner. Redis is used only as a shared single-flight marker and
degrades safely (fail-open) if unavailable.
"""
from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

logger = logging.getLogger("storescout.ai_job")

_ACTIVE_STATES = ("queued", "generating")


def decide_ai_action(
    has_fresh_result: bool,
    job_active: bool,
    job_age_s: Optional[float],
    timeout_s: int,
) -> Tuple[str, bool]:
    """
    Pure decision. Returns (state, should_dispatch).
      - a fresh result → ('ready', False)
      - an active job within timeout → ('generating', False)  [dedup: don't re-dispatch]
      - an active job past timeout → ('timed_out', False)     [stop the banner; offer retry]
      - no active job and no result → ('generating', True)    [dispatch exactly one]
    """
    if has_fresh_result:
        return ("ready", False)
    if job_active:
        if job_age_s is not None and job_age_s > timeout_s:
            return ("timed_out", False)
        return ("generating", False)
    return ("generating", True)


# ── Redis-backed single-flight job marker (fail-open) ─────────────────────────

def _key(kind: str, owner: str) -> str:
    return f"aijob:{kind}:{owner}"


def get_job(kind: str, owner: str) -> Tuple[bool, Optional[float]]:
    """Return (active, age_seconds). Fail-open: on Redis error, (False, None) so
    the caller falls back to dispatching."""
    try:
        import redis as _redis
        from app.core.config import get_settings
        r = _redis.from_url(get_settings().redis_url, socket_connect_timeout=1)
        val = r.get(_key(kind, owner))
        if not val:
            return (False, None)
        started = float(val)
        return (True, max(0.0, time.time() - started))
    except Exception:
        return (False, None)


def start_job(kind: str, owner: str, ttl_s: int) -> None:
    """Mark a job active (records start time). TTL a little over the timeout so a
    dead job auto-clears. Fail-open."""
    try:
        import redis as _redis
        from app.core.config import get_settings
        r = _redis.from_url(get_settings().redis_url, socket_connect_timeout=1)
        r.set(_key(kind, owner), str(time.time()), ex=ttl_s)
    except Exception:
        pass


def clear_job(kind: str, owner: str) -> None:
    """Clear the job marker (on success, or to allow a retry). Fail-open."""
    try:
        import redis as _redis
        from app.core.config import get_settings
        r = _redis.from_url(get_settings().redis_url, socket_connect_timeout=1)
        r.delete(_key(kind, owner))
    except Exception:
        pass
