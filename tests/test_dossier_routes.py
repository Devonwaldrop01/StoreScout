"""Dossier route resilience — required routes convert unexpected failures into a
clean, retryable 503 (never a raw 500) while preserving intentional 4xx and
ownership; the distinction between schema-mismatch and upstream failure is
surfaced. Uses a fake Supabase client (no DB/network)."""
import pytest
from fastapi import HTTPException

from app.core.obs import guarded_required
import app.api.v1.competitors as comp


# ── The decorator itself ──────────────────────────────────────────────────────

def test_guarded_required_db_failure_is_clean_503():
    @guarded_required("GET /thing")
    def route(user_id=None, competitor_id=None):
        raise RuntimeError("connection refused to db host 10.0.0.5")
    with pytest.raises(HTTPException) as exc:
        route(user_id="u1", competitor_id="c1")
    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "upstream_unavailable"
    assert "ref" in exc.value.detail
    assert "10.0.0.5" not in str(exc.value.detail["message"])  # no internal leak


def test_guarded_required_schema_mismatch_is_labeled():
    @guarded_required("GET /thing")
    def route(user_id=None):
        raise Exception('column competitors.brand_decode does not exist')
    with pytest.raises(HTTPException) as exc:
        route(user_id="u1")
    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "schema_mismatch"


def test_guarded_required_preserves_intentional_4xx():
    @guarded_required("GET /thing")
    def route(user_id=None):
        raise HTTPException(status_code=404, detail="No snapshots yet")
    with pytest.raises(HTTPException) as exc:
        route(user_id="u1")
    assert exc.value.status_code == 404   # intentional empty stays a 404, not a 503


def test_guarded_required_success_passthrough():
    @guarded_required("GET /thing")
    def route(user_id=None):
        return {"data": {"ok": True}}
    assert route(user_id="u1") == {"data": {"ok": True}}


# ── get_latest_snapshot end to end (fake db) ─────────────────────────────────

class _Q:
    def __init__(self, data=None, raises=None):
        self._data, self._raises = data, raises
    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def execute(self):
        if self._raises: raise self._raises
        return type("R", (), {"data": self._data})()

class _DB:
    def __init__(self, q): self._q = q
    def table(self, *a, **k): return self._q


def _patch(monkeypatch, db, owner_ok=True):
    monkeypatch.setattr(comp, "get_supabase", lambda: db)
    def owner(db_, cid, uid):
        if not owner_ok:
            raise HTTPException(status_code=404, detail="Not found")
    monkeypatch.setattr(comp, "_assert_owner", owner)


def test_latest_snapshot_new_competitor_one_snapshot(monkeypatch):
    _patch(monkeypatch, _DB(_Q(data=[{"id": "s1", "scanned_at": "2026-07-11", "product_count": 10}])))
    out = comp.get_latest_snapshot(competitor_id="c1", user_id="u1")
    assert out["data"]["id"] == "s1"


def test_latest_snapshot_no_snapshot_is_404(monkeypatch):
    _patch(monkeypatch, _DB(_Q(data=[])))
    with pytest.raises(HTTPException) as exc:
        comp.get_latest_snapshot(competitor_id="c1", user_id="u1")
    assert exc.value.status_code == 404   # valid "no data yet", not a 500


def test_latest_snapshot_db_failure_is_503(monkeypatch):
    _patch(monkeypatch, _DB(_Q(raises=RuntimeError("db unavailable"))))
    with pytest.raises(HTTPException) as exc:
        comp.get_latest_snapshot(competitor_id="c1", user_id="u1")
    assert exc.value.status_code == 503   # clean upstream failure, not raw 500


def test_latest_snapshot_cross_user_is_404(monkeypatch):
    _patch(monkeypatch, _DB(_Q(data=[{"id": "s1"}])), owner_ok=False)
    with pytest.raises(HTTPException) as exc:
        comp.get_latest_snapshot(competitor_id="c1", user_id="attacker")
    assert exc.value.status_code == 404   # ownership preserved (safe denial)
