"""
Observability helpers — structured logging, a redacting centralized
error-reporter, and a decorator that turns unexpected exceptions into a
graceful, logged JSON error instead of a raw 500.

`report_error` is the single place failures are recorded across the highest-risk
shared paths (safe_read, the Anthropic layer, the store-index pipeline,
schema/migration fallbacks, background tasks). It:
  - logs a structured, greppable record (operation, user_id, entity, exception
    class, concise message, and whether we degraded to a fallback),
  - redacts secrets (keys, bearer tokens) and truncates hard so full prompts /
    scraped page bodies never land in logs,
  - de-duplicates identical errors within a short window to avoid log storms,
  - forwards to an external monitor (Sentry) if one is installed — but stays
    dependency-free and ready for one if not.

Read endpoints wrapped with @safe_read never crash a page: they report the
error and return an empty default shape carrying `error: True` so callers can
tell "empty because it failed" from "legitimately empty".
"""
from __future__ import annotations

import functools
import logging
import os
import re
import time
import uuid
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger("storescout.api")

# In-process ring buffer of recent failures for the admin error summary. This is
# a launch-time convenience (no new paid dependency), NOT a replacement for
# external monitoring: it is per-process and cleared on restart. See the
# observability docs for wiring Sentry.
_RECENT_MAX = 300
_recent_errors: Deque[Dict[str, Any]] = deque(maxlen=_RECENT_MAX)

# ── Redaction ───────────────────────────────────────────────────────────────
# Belt-and-suspenders: even though we only ever pass concise messages here, scrub
# anything that looks like a credential before it can reach a log line or Sentry.
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),                 # anthropic / openai keys
    re.compile(r"sk_live_[A-Za-z0-9]{8,}"),               # our API keys / stripe
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{8,}"),      # auth headers
    re.compile(r"eyJ[A-Za-z0-9._\-]{20,}"),               # JWTs
    re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)\"?\s*[:=]\s*\"?[^\s\"',)]+"),
]
_MAX_MSG = 300


def redact(text: Any) -> str:
    """Scrub credential-shaped substrings and hard-truncate. Never raises."""
    try:
        s = str(text)
    except Exception:
        return "<unstringable>"
    for pat in _SECRET_PATTERNS:
        s = pat.sub("[redacted]", s)
    return s[:_MAX_MSG]


def log_event(level: str, msg: str, **fields: Any) -> None:
    """Emit a structured log line. Fields (user_id, competitor_id, route,
    job_id, error, …) are appended as key=value for grep-ability in logs."""
    parts = [msg] + [f"{k}={v}" for k, v in fields.items() if v is not None]
    getattr(logger, level, logger.info)(" ".join(str(p) for p in parts))


# ── Centralized error reporting ───────────────────────────────────────────────

# External monitor hook. Left None so the module stays dependency-free; if
# `sentry_sdk` is installed AND SENTRY_DSN is set it is used automatically.
_ERROR_SINK: Optional[Callable[[BaseException, Dict[str, Any]], None]] = None

_DEDUP_WINDOW_S = 60.0
_dedup_seen: Dict[str, float] = {}


def set_error_sink(sink: Optional[Callable[[BaseException, Dict[str, Any]], None]]) -> None:
    """Register an external error sink (tests, or a custom forwarder)."""
    global _ERROR_SINK
    _ERROR_SINK = sink


def _maybe_sentry(exc: BaseException, context: Dict[str, Any]) -> None:
    if _ERROR_SINK is not None:
        try:
            _ERROR_SINK(exc, context)
        except Exception:
            pass
        return
    if not os.environ.get("SENTRY_DSN"):
        return
    try:
        import sentry_sdk  # optional; only used if the app installs it
        with sentry_sdk.push_scope() as scope:
            for k, v in context.items():
                if k in ("operation", "degraded", "exc_class"):
                    scope.set_tag(k, v)
                else:
                    scope.set_extra(k, v)
            sentry_sdk.capture_exception(exc)
    except Exception:
        pass


def report_error(
    operation: str,
    exc: BaseException,
    *,
    user_id: Optional[str] = None,
    entity: Optional[str] = None,
    degraded: bool = True,
    level: str = "error",
    **extra: Any,
) -> str:
    """
    Record a failure once, safely. Returns a short ref id that can be surfaced to
    the caller (never the raw error). `operation` is the route/task/feature name,
    `entity` a competitor/store/domain identifier, `degraded` whether we fell
    back to a safe default. Extra fields are redacted key=value context.

    De-dups identical (operation, exc-class, message) errors within a short
    window: the first logs at `level`, repeats log at debug so a broken
    dependency can't flood the logs.
    """
    ref = uuid.uuid4().hex[:8]
    exc_class = type(exc).__name__
    msg = redact(exc)

    key = f"{operation}|{exc_class}|{msg[:80]}"
    now = time.monotonic()
    last = _dedup_seen.get(key)
    _dedup_seen[key] = now
    # opportunistic cleanup so the map can't grow unbounded
    if len(_dedup_seen) > 512:
        for k, t in list(_dedup_seen.items()):
            if now - t > _DEDUP_WINDOW_S:
                _dedup_seen.pop(k, None)
    effective_level = "debug" if (last is not None and now - last < _DEDUP_WINDOW_S) else level

    fields: Dict[str, Any] = {
        "operation": operation, "exc_class": exc_class, "error": msg,
        "user_id": user_id, "entity": entity, "degraded": degraded, "ref": ref,
    }
    for k, v in extra.items():
        fields[k] = redact(v) if isinstance(v, str) else v

    log_event(effective_level, f"[{operation}] {exc_class}", **fields)
    _maybe_sentry(exc, {k: v for k, v in fields.items() if v is not None})
    try:
        _recent_errors.append({
            "operation": operation, "exc_class": exc_class, "message": msg,
            "degraded": degraded, "ref": ref, "ts": time.time(),
        })
    except Exception:
        pass
    return ref


def recent_error_summary(limit: int = 50) -> List[Dict[str, Any]]:
    """Grouped view of recent in-process failures for the admin summary. Groups
    by (operation, exc_class) with a count, last-seen time, latest ref, and a
    redacted sample message — never row data or secrets. Newest first."""
    groups: Dict[tuple, Dict[str, Any]] = {}
    for r in list(_recent_errors):
        key = (r["operation"], r["exc_class"])
        g = groups.get(key)
        if g is None:
            g = groups[key] = {
                "operation": r["operation"], "exc_class": r["exc_class"],
                "count": 0, "last_seen": 0.0, "last_ref": None,
                "sample": r["message"], "degraded": bool(r["degraded"]),
            }
        g["count"] += 1
        if r["ts"] >= g["last_seen"]:
            g["last_seen"] = r["ts"]
            g["last_ref"] = r["ref"]
            g["sample"] = r["message"]
            g["degraded"] = bool(r["degraded"])
    out = sorted(groups.values(), key=lambda x: x["last_seen"], reverse=True)
    for g in out:
        g["last_seen_iso"] = _iso(g.pop("last_seen"))
    return out[:limit]


def _iso(ts: float) -> str:
    from datetime import datetime, timezone
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return ""


def safe_read(route: str, default: Callable[[], Dict[str, Any]] | Dict[str, Any]):
    """
    Decorator for GET endpoints whose failure should degrade gracefully.
    On an unhandled exception: report a structured error (with any
    user_id/competitor_id present in kwargs) and return the default shape plus
    `error: True` + a `ref`, so the frontend shows an empty/loading state (never
    a raw 500) and callers can distinguish failure-empty from legitimate-empty.

    HTTPExceptions are re-raised untouched — intentional 4xx stay 4xx.
    """
    from fastapi import HTTPException

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any):
            try:
                return fn(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as exc:
                ref = report_error(
                    route, exc,
                    user_id=kwargs.get("user_id"),
                    entity=kwargs.get("competitor_id") or kwargs.get("domain"),
                    degraded=True,
                )
                d = default() if callable(default) else default
                return {**d, "error": True, "ref": ref}
        return wrapper
    return decorator


_SCHEMA_MISS_RE = re.compile(r"(?i)does not exist|could not find the")


def guarded_required(route: str):
    """
    Decorator for REQUIRED endpoints (core data the page can't render without).
    Unlike @safe_read (which degrades to an empty 200), this preserves the
    endpoint's intentional 4xx (404/402/…) but converts any UNEXPECTED exception
    into a clean, structured error the frontend can retry — never a raw 500 with
    a leaked traceback. Distinguishes a schema/migration mismatch (503
    schema_mismatch) from an upstream dependency failure (503 upstream_unavailable),
    and logs both via report_error.
    """
    from fastapi import HTTPException

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any):
            try:
                return fn(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as exc:
                is_schema = bool(_SCHEMA_MISS_RE.search(str(exc)))
                code = "schema_mismatch" if is_schema else "upstream_unavailable"
                ref = report_error(
                    route, exc,
                    user_id=kwargs.get("user_id"),
                    entity=kwargs.get("competitor_id") or kwargs.get("domain"),
                    degraded=False, failure=code,
                )
                raise HTTPException(status_code=503, detail={
                    "code": code, "ref": ref,
                    "message": "This data is temporarily unavailable. Please retry in a moment.",
                })
        return wrapper
    return decorator
