"""
Runtime configuration — operational knobs an admin can flip from /admin
without redeploying or restarting.

Design: env vars are the DEFAULTS (resolved from Settings); a row in the
app_config table OVERRIDES its env var. Reads are cached for a few seconds so
the daily workers pick up a toggle within one cache window, and writes clear
the cache immediately. Everything degrades to the env defaults if the table
doesn't exist yet (pre-migration) — nothing here can break a worker.

Only the keys in KNOBS are honored; anything else is ignored on read/write.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)

_TTL_SECONDS = 15.0
_cache: Dict[str, Any] | None = None
_cache_at = 0.0

# key → (Settings attribute for the default, coercion type, min, max)
KNOBS: Dict[str, tuple] = {
    "shopify_index_enabled":              ("shopify_index_enabled", bool, None, None),
    "shopify_index_daily_verified_target": ("shopify_index_daily_verified_target", int, 1, 250),
    "shopify_index_daily_candidate_limit": ("shopify_index_daily_candidate_limit", int, 1, 500),
    "lead_engine_enabled":                ("lead_engine_enabled", bool, None, None),
    "lead_engine_daily_target":           ("lead_engine_daily_target", int, 1, 50),
    "lead_engine_min_qualification":      ("lead_engine_min_qualification", int, 0, 100),
}


def _coerce(key: str, raw: Any) -> Any:
    _, typ, lo, hi = KNOBS[key]
    if typ is bool:
        val = raw if isinstance(raw, bool) else str(raw).strip().lower() in ("1", "true", "yes", "on")
    else:
        try:
            val = int(raw)
        except (TypeError, ValueError):
            return None
        if lo is not None:
            val = max(lo, val)
        if hi is not None:
            val = min(hi, val)
    return val


def _defaults() -> Dict[str, Any]:
    from app.core.config import get_settings
    s = get_settings()
    return {key: getattr(s, attr) for key, (attr, *_ ) in KNOBS.items()}


def _load() -> Dict[str, Any]:
    global _cache, _cache_at
    now = time.time()
    if _cache is not None and (now - _cache_at) < _TTL_SECONDS:
        return _cache

    merged = _defaults()
    try:
        from app.core.database import get_supabase
        rows = get_supabase().table("app_config").select("key, value").execute()
        for r in (rows.data or []):
            k = r.get("key")
            if k in KNOBS:
                coerced = _coerce(k, r.get("value"))
                if coerced is not None:
                    merged[k] = coerced
    except Exception as exc:
        logger.debug("runtime config load failed — using env defaults: %s", exc)

    _cache = merged
    _cache_at = now
    return merged


def invalidate() -> None:
    global _cache
    _cache = None


def get_config(key: str, default: Any = None) -> Any:
    """Effective value for one knob (DB override, else env default)."""
    return _load().get(key, default)


def get_all() -> Dict[str, Any]:
    """All effective knob values."""
    return dict(_load())


def set_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert overrides for known keys; returns the new effective config."""
    from app.core.database import get_supabase
    from datetime import datetime, timezone

    db = get_supabase()
    now = datetime.now(timezone.utc).isoformat()
    for key, raw in (updates or {}).items():
        if key not in KNOBS:
            continue
        coerced = _coerce(key, raw)
        if coerced is None:
            continue
        db.table("app_config").upsert(
            {"key": key, "value": coerced, "updated_at": now}, on_conflict="key"
        ).execute()
    invalidate()
    return get_all()
