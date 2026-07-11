"""Dossier endpoint resilience — optional intelligence degrades to a typed empty
result instead of a 500, while ownership/authorization is preserved."""
import pytest
from fastapi import HTTPException

import app.api.v1.competitors as comp


def test_quick_wins_degrades_on_corrupt_snapshot(monkeypatch):
    # A non-dict snapshot payload would make compute_quick_wins raise; @safe_read
    # must turn that into a typed-empty result flagged as an error, not a 500.
    monkeypatch.setattr(comp, "get_supabase", lambda: object())
    monkeypatch.setattr(comp, "_assert_owner", lambda db, cid, uid: None)
    monkeypatch.setattr(comp, "_user_tier", lambda db, uid: "free")
    monkeypatch.setattr(comp, "_latest_snapshot_data", lambda db, cid: "corrupt-not-a-dict")

    out = comp.get_quick_wins(competitor_id="c1", user_id="u1")
    assert out["data"]["wins"] == []
    assert out.get("error") is True          # failure-empty, distinguishable from legit-empty
    assert "ref" in out


def test_quick_wins_legit_empty_is_not_flagged_error(monkeypatch):
    monkeypatch.setattr(comp, "get_supabase", lambda: object())
    monkeypatch.setattr(comp, "_assert_owner", lambda db, cid, uid: None)
    monkeypatch.setattr(comp, "_user_tier", lambda db, uid: "free")
    monkeypatch.setattr(comp, "_latest_snapshot_data", lambda db, cid: None)  # no snapshot yet

    out = comp.get_quick_wins(competitor_id="c1", user_id="u1")
    assert out["data"]["wins"] == []
    assert "error" not in out                 # legitimately empty, not a failure


def test_quick_wins_preserves_ownership_404(monkeypatch):
    monkeypatch.setattr(comp, "get_supabase", lambda: object())

    def deny(db, cid, uid):
        raise HTTPException(status_code=404, detail="Not found")

    monkeypatch.setattr(comp, "_assert_owner", deny)
    with pytest.raises(HTTPException) as exc:
        comp.get_quick_wins(competitor_id="c1", user_id="attacker")
    assert exc.value.status_code == 404       # cross-user access still blocked
