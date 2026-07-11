"""
Server-side abuse controls for interactive AI endpoints.

Two primitives, both Redis-backed and FAIL-OPEN (if Redis is briefly
unavailable they allow the request rather than lock everyone out):

  - `check_rate_limit` — a fixed-window per-user counter (INCR + EXPIRE).
  - `single_flight`    — a short-lived lock (SET NX EX) that collapses duplicate
    simultaneous requests for the same logical input.

These run server-side on purpose: the frontend disabling a button is not a
control. Limits are configurable via settings/env.
"""
from __future__ import annotations

import hashlib
import logging
from contextlib import contextmanager
from typing import Iterator, Tuple

from app.core.config import get_settings

logger = logging.getLogger("storescout.ratelimit")


def _redis():
    import redis as _r
    return _r.from_url(get_settings().redis_url, socket_connect_timeout=1)


def check_rate_limit(bucket: str, identity: str, limit: int, window_s: int) -> Tuple[bool, int]:
    """
    Fixed-window limiter. Returns (allowed, retry_after_s). At most `limit`
    requests per `window_s` per (bucket, identity). Fail-open: any Redis error
    returns (True, 0) so a Redis blip never hard-blocks users.
    """
    if limit <= 0:
        return True, 0
    try:
        r = _redis()
        # Bucket the key by window so it self-expires and resets cleanly.
        import time
        window_id = int(time.time()) // window_s
        key = f"rl:{bucket}:{identity}:{window_id}"
        n = r.incr(key)
        if n == 1:
            r.expire(key, window_s)
        if n > limit:
            ttl = r.ttl(key)
            return False, (ttl if isinstance(ttl, int) and ttl > 0 else window_s)
        return True, 0
    except Exception as exc:
        logger.warning("rate_limit fail-open (%s): %s", bucket, exc)
        return True, 0


def dedupe_key(*parts: str) -> str:
    """Stable short hash of the logical-input parts, for single_flight keys."""
    raw = "|".join(p or "" for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


@contextmanager
def single_flight(bucket: str, key: str, ttl_s: int = 30) -> Iterator[bool]:
    """
    Context manager that yields True if THIS caller acquired the lock for
    (bucket, key), False if an identical request is already in flight. Releases
    on exit. Fail-open: yields True if Redis is unavailable.

        with single_flight("ask", dedupe_key(user_id, question)) as fresh:
            if not fresh:
                return friendly_degraded_response()
            ... do the expensive work ...
    """
    lock_key = f"sf:{bucket}:{key}"
    acquired = True
    r = None
    try:
        r = _redis()
        acquired = bool(r.set(lock_key, "1", nx=True, ex=ttl_s))
    except Exception as exc:
        logger.warning("single_flight fail-open (%s): %s", bucket, exc)
        acquired = True
        r = None
    try:
        yield acquired
    finally:
        if acquired and r is not None:
            try:
                r.delete(lock_key)
            except Exception:
                pass
