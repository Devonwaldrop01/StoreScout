"""Security — a user must not reach another user's competitor. Proves the
ownership guard behind every /competitors/{id}/... endpoint (incl. Ask
StoreScout) returns 404 on a mismatch, using a fake DB (no real database)."""
import pytest
from fastapi import HTTPException

from app.api.v1.competitors import _assert_owner


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, data):
        self._data = data

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        return _Resp(self._data)


class _DB:
    def __init__(self, data):
        self._data = data

    def table(self, *a, **k):
        return _Query(self._data)


def test_other_users_competitor_is_404():
    db = _DB({"user_id": "owner-A"})
    with pytest.raises(HTTPException) as exc:
        _assert_owner(db, "comp-1", "attacker-B")
    assert exc.value.status_code == 404


def test_missing_competitor_is_404():
    db = _DB(None)
    with pytest.raises(HTTPException) as exc:
        _assert_owner(db, "comp-1", "owner-A")
    assert exc.value.status_code == 404


def test_owner_can_access_own_competitor():
    db = _DB({"user_id": "owner-A"})
    # must not raise
    _assert_owner(db, "comp-1", "owner-A")
