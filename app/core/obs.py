"""
Observability helpers — structured logging + a decorator that turns
unexpected exceptions into a graceful, logged JSON error instead of a raw
500. Read endpoints wrapped with @safe_read never crash a page: they log a
structured record (route, user_id, competitor_id, error) and return an empty
default shape the frontend can render.
"""
from __future__ import annotations

import functools
import logging
import uuid
from typing import Any, Callable, Dict

logger = logging.getLogger("storescout.api")


def log_event(level: str, msg: str, **fields: Any) -> None:
    """Emit a structured log line. Fields (user_id, competitor_id, route,
    job_id, error, …) are appended as key=value for grep-ability in Render logs."""
    parts = [msg] + [f"{k}={v}" for k, v in fields.items() if v is not None]
    getattr(logger, level, logger.info)(" ".join(str(p) for p in parts))


def safe_read(route: str, default: Callable[[], Dict[str, Any]] | Dict[str, Any]):
    """
    Decorator for GET endpoints whose failure should degrade gracefully.
    On an unhandled exception: assign a job_id, log a structured error with
    any user_id/competitor_id present in kwargs, and return the default shape
    (so the frontend shows an empty/loading state, never a raw 500).

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
                job_id = uuid.uuid4().hex[:8]
                log_event(
                    "error", f"[{route}] unhandled error",
                    route=route,
                    user_id=kwargs.get("user_id"),
                    competitor_id=kwargs.get("competitor_id"),
                    job_id=job_id,
                    error=repr(exc)[:300],
                )
                d = default() if callable(default) else default
                return {**d, "error": True, "ref": job_id}
        return wrapper
    return decorator
