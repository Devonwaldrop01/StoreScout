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
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("storescout.api")

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
    return ref


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
