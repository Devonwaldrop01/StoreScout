"""
Finite job state for background AI generation (Playbook).

Design goals (verified by tests):
  - a plain GET never re-dispatches generation; only the FIRST request with no
    job dispatches, and only the explicit regenerate endpoint retries after that.
  - a stuck/failed job resolves to a FINITE terminal state (timed_out/failed),
    persisted so it survives page reloads — never an indefinite "generating".
  - Anthropic auth/credit failures mark the job failed fast (the task calls
    mark_failed); the timeout is the fallback if the task dies without reporting.
  - the terminal marker has a TTL, so a failure can never permanently block
    future attempts, yet repeated polling won't restart a storm of dispatches.

State machine (persisted in Redis, fail-open):
  none    → no job. A GET dispatches exactly one, moving to `active`.
  active  → a job started at T. Within timeout → 'generating'. Past timeout →
            'timed_out' and promoted to `failed` (persisted).
  failed  → terminal. GET reports failed/timed_out and does NOT re-dispatch.
            Cleared by regenerate, or auto-expires after _FAILED_TTL_S.

Redis is only a shared marker; if it's unavailable, reads return `none` (fail
open to a single dispatch) so the feature still works without it.
"""
from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

logger = logging.getLogger("storescout.ai_job")

_FAILED_TTL_S = 3600  # a terminal failure self-heals after an hour (never permanent)


def _started_key(kind: str, owner: str) -> str:
    return f"aijob:{kind}:{owner}:started"


def _failed_key(kind: str, owner: str) -> str:
    return f"aijob:{kind}:{owner}:failed"


def _redis():
    import redis as _redis_lib
    from app.core.config import get_settings
    return _redis_lib.from_url(get_settings().redis_url, socket_connect_timeout=1)


# ── Pure decision (unit-tested without Redis) ─────────────────────────────────

def decide_ai_action(
    has_fresh_result: bool,
    phase: str,
    age_s: Optional[float],
    timeout_s: int,
) -> Tuple[str, str]:
    """
    Returns (state, action).
      state  ∈ ready | generating | timed_out | failed
      action ∈ none | dispatch | mark_failed
    Rules:
      - fresh result → ('ready', 'none')
      - phase 'failed' → ('failed', 'none')          # GET must NOT re-dispatch
      - phase 'active' within timeout → ('generating', 'none')  # dedup
      - phase 'active' past timeout → ('timed_out', 'mark_failed')  # persist terminal
      - phase 'none' → ('generating', 'dispatch')    # first request only
    """
    if has_fresh_result:
        return ("ready", "none")
    if phase == "failed":
        return ("failed", "none")
    if phase == "active":
        if age_s is not None and age_s > timeout_s:
            return ("timed_out", "mark_failed")
        return ("generating", "none")
    return ("generating", "dispatch")


# ── Redis-backed persisted phase (fail-open) ──────────────────────────────────

def read_phase(kind: str, owner: str) -> Tuple[str, Optional[float]]:
    """Return (phase, age_seconds). Fail-open: Redis error → ('none', None)."""
    try:
        r = _redis()
        if r.get(_failed_key(kind, owner)):
            return ("failed", None)
        started = r.get(_started_key(kind, owner))
        if started:
            return ("active", max(0.0, time.time() - float(started)))
        return ("none", None)
    except Exception:
        return ("none", None)


def mark_started(kind: str, owner: str, ttl_s: int) -> None:
    """Mark active (records start). Clears any prior failed marker. Fail-open."""
    try:
        r = _redis()
        r.delete(_failed_key(kind, owner))
        r.set(_started_key(kind, owner), str(time.time()), ex=ttl_s)
    except Exception:
        pass


def mark_failed(kind: str, owner: str) -> None:
    """Promote to the terminal failed state (TTL so it self-heals). Fail-open."""
    try:
        r = _redis()
        r.delete(_started_key(kind, owner))
        r.set(_failed_key(kind, owner), "1", ex=_FAILED_TTL_S)
    except Exception:
        pass


def clear_job(kind: str, owner: str) -> None:
    """Clear all markers (on success, or to allow an explicit retry). Fail-open."""
    try:
        r = _redis()
        r.delete(_started_key(kind, owner))
        r.delete(_failed_key(kind, owner))
    except Exception:
        pass
