"""Read-only operational evidence. An enable flag is never proof of a live worker."""
from datetime import datetime, timedelta, timezone
from app.services.verification_lifecycle import timestamp


def activity_state(enabled, held, last_dispatch, now):
    if held:
        return "deployment_hold"
    if not enabled:
        return "disabled"
    stamp = timestamp(last_dispatch)
    if stamp and timedelta(0) <= now - stamp <= timedelta(minutes=20):
        return "recent_activity"
    return "inactive_or_unknown"


def operational_evidence(db, *, enabled, held, last_dispatch, now=None):
    now = now or datetime.now(timezone.utc)
    def latest(table, column, **filters):
        try:
            q = db.table(table).select(column).not_.is_(column, "null")
            for key, value in filters.items():
                q = q.eq(key, value)
            rows = q.order(column, desc=True).limit(1).execute().data or []
            return rows[0].get(column) if rows else None
        except Exception:
            return None
    last_success = None
    try:
        rows = db.table("store_index_runs").select("ran_at").eq("failed", 0).gt("processed", 0).order("ran_at", desc=True).limit(1).execute().data or []
        last_success = rows[0]["ran_at"] if rows else None
    except Exception:
        pass
    throughput = None
    try:
        rows = db.table("store_index_runs").select("processed, verified, reverified").eq("trigger", "scheduled:stage_verification").gte("ran_at", (now-timedelta(hours=1)).isoformat()).order("ran_at").limit(1000).execute().data
        if rows is not None and len(rows) < 1000:
            throughput = {"window_minutes": 60, "attempts": sum(r.get("processed") or 0 for r in rows),
                          "successful_catalogs": sum((r.get("verified") or 0)+(r.get("reverified") or 0) for r in rows),
                          "basis": "recorded scheduled outcomes; not unique new stores"}
    except Exception:
        pass
    return {"enabled": enabled, "state": activity_state(enabled, held, last_dispatch, now),
            "live_worker_confirmed": False, "hold_scope": "this API process",
            "last_dispatch": last_dispatch, "last_successful_run": last_success,
            "last_verification": latest("shopify_store_index", "last_verified_at"),
            "last_classification": latest("shopify_store_index", "knowledge_at"),
            "throughput": throughput}
