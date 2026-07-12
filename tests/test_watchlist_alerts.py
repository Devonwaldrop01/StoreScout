"""Regression for the production 500 on GET /alerts + the recurring
`product_watches` PGRST205 (table not in the PostgREST schema cache).

Root cause: migration 006 (`product_watches`) was not applied to the
production database (or PostgREST's schema cache was stale), so every
watchlist call raised — surfaced in the admin error summary. schema_health
did not validate `product_watches` or `change_events`, so migration-health
could not report the gap. These lock:
  · schema_health now validates both tables (accurate migration-health)
  · watchlist writes degrade to a clean 503 (guarded_required), not a raw 500
  · GET /alerts degrades to an empty, error-flagged list, never a 500
"""
import pytest
from fastapi import HTTPException

from app.services import schema_health


class _PGRST205:
    """A Supabase/PostgREST client stub whose queries raise the real 'schema
    cache' error, exactly like a missing table in production."""
    def table(self, *_a, **_k):
        raise Exception("Could not find the table 'public.product_watches' in the schema cache (PGRST205)")


# ── schema_health now validates the dependencies accurately ────────────────

def test_schema_health_validates_product_watches_and_change_events():
    tables = {(c["migration"], c["table"]) for c in schema_health.CHECKS}
    assert ("006", "product_watches") in tables
    assert ("001", "change_events") in tables


def test_missing_product_watches_reported_as_optional_gap():
    # simulate probe results with product_watches missing
    results = []
    for c in schema_health.CHECKS:
        state = "missing" if c["table"] == "product_watches" else "present"
        results.append({**c, "state": state})
    summary = schema_health.summarize(results)
    missing_optional_tables = [m["table"] for m in summary["missing_optional"]]
    assert "product_watches" in missing_optional_tables
    # optional gap doesn't take the whole app down
    assert summary["status"] != "db_unavailable"


def test_missing_change_events_is_a_required_gap():
    results = []
    for c in schema_health.CHECKS:
        state = "missing" if c["table"] == "change_events" else "present"
        results.append({**c, "state": state})
    summary = schema_health.summarize(results)
    assert "change_events" in [m["table"] for m in summary["missing_required"]]


def test_probe_detects_pgrst205_as_missing():
    assert schema_health.probe(_PGRST205(), "product_watches", None) == "missing"


# ── Endpoints degrade instead of 500 ───────────────────────────────────────

def test_list_alerts_degrades_not_500(monkeypatch):
    import app.api.v1.alerts as alerts_mod
    monkeypatch.setattr(alerts_mod, "get_supabase", lambda: _PGRST205())
    out = alerts_mod.list_alerts(limit=100, user_id="u1")
    assert out["data"] == []
    assert out.get("error") is True and out.get("ref")


def test_list_watches_degrades_not_500(monkeypatch):
    import app.api.v1.watchlist as wl
    monkeypatch.setattr(wl, "get_supabase", lambda: _PGRST205())
    out = wl.list_watches(user_id="u1")
    assert out["data"] == [] and out.get("error") is True


def test_add_watch_returns_clean_503_on_missing_table(monkeypatch):
    import app.api.v1.watchlist as wl
    monkeypatch.setattr(wl, "get_supabase", lambda: _PGRST205())
    body = wl.AddWatchRequest(competitor_id="c1", product_handle="h1")
    with pytest.raises(HTTPException) as ei:
        wl.add_watch(body, user_id="u1")
    assert ei.value.status_code == 503
    assert ei.value.detail["code"] == "schema_mismatch"
    assert ei.value.detail["ref"]
