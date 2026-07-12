"""Account provisioning — idempotent, concurrency-safe, structured failures.
Uses a tiny fake Supabase client (no DB/network)."""
import pytest
from fastapi import HTTPException

import app.api.v1.user as user_mod
from app.api.v1.user import provision_user


class _Result:
    def __init__(self, data):
        self.data = data


class _Table:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self._op = None
        self._filter = {}

    def select(self, *a, **k):
        self._op = ("select",)
        return self

    def eq(self, col, val):
        self._filter[col] = val
        return self

    def limit(self, *a, **k):
        return self

    def maybe_single(self):
        return self

    def insert(self, payload):
        self._op = ("insert", payload)
        return self

    def execute(self):
        if self._op[0] == "select":
            if self.name == "user_profiles" and self.db.lookup_error:
                raise self.db.lookup_error
            rows = [r for r in self.db.tables.get(self.name, []) if all(r.get(k) == v for k, v in self._filter.items())]
            return _Result(rows)
        # insert
        payload = self._op[1]
        if self.name == "user_profiles":
            if self.db.insert_error:
                raise self.db.insert_error
            if any(r.get("id") == payload.get("id") for r in self.db.tables.setdefault("user_profiles", [])):
                raise Exception("duplicate key value violates unique constraint")
            self.db.tables["user_profiles"].append(payload)
        elif self.name == "notification_prefs":
            if self.db.prefs_error:
                raise self.db.prefs_error
            if any(r.get("user_id") == payload.get("user_id") for r in self.db.tables.setdefault("notification_prefs", [])):
                raise Exception("duplicate key value violates unique constraint")
            self.db.tables["notification_prefs"].append(payload)
        return _Result([payload])


class _Auth:
    def __init__(self, email, raises):
        self._email = email
        self._raises = raises

    class _Admin:
        def __init__(self, outer):
            self.outer = outer

        def get_user_by_id(self, uid):
            if self.outer._raises:
                raise Exception("auth unavailable")
            return type("U", (), {"user": type("X", (), {"email": self.outer._email})()})()

    @property
    def admin(self):
        return _Auth._Admin(self)


class FakeDB:
    def __init__(self, existing=None, lookup_error=None, insert_error=None, prefs_error=None,
                 email="new@example.com", auth_raises=False):
        self.tables = {"user_profiles": list(existing or []), "notification_prefs": []}
        self.lookup_error = lookup_error
        self.insert_error = insert_error
        self.prefs_error = prefs_error
        self.auth = _Auth(email, auth_raises)

    def table(self, name):
        return _Table(self, name)


@pytest.fixture(autouse=True)
def _patch_db(monkeypatch):
    # Each test sets monkeypatch target via _use()
    yield


def _use(monkeypatch, db):
    monkeypatch.setattr(user_mod, "get_supabase", lambda: db)


def test_new_user_is_created(monkeypatch):
    db = FakeDB()
    _use(monkeypatch, db)
    out = provision_user(user_id="u1")
    assert out["status"] == "created" and out["provisioned"] is True
    assert any(r["id"] == "u1" for r in db.tables["user_profiles"])
    assert any(r["user_id"] == "u1" for r in db.tables["notification_prefs"])


def test_already_provisioned_user(monkeypatch):
    db = FakeDB(existing=[{"id": "u1", "tier": "pro"}], email="x@y.com")
    _use(monkeypatch, db)
    out = provision_user(user_id="u1")
    assert out["status"] == "exists" and out["provisioned"] is True
    # existing row untouched (tier preserved)
    assert db.tables["user_profiles"] == [{"id": "u1", "tier": "pro"}]


def test_partial_provision_repairs_prefs(monkeypatch):
    # profile exists but prefs missing (a prior partial provision)
    db = FakeDB(existing=[{"id": "u1", "tier": "free"}])
    _use(monkeypatch, db)
    out = provision_user(user_id="u1")
    assert out["status"] == "exists"
    assert any(r["user_id"] == "u1" for r in db.tables["notification_prefs"])


def test_duplicate_concurrent_insert_is_success(monkeypatch):
    # existence check passes (empty), then insert races a concurrent create
    db = FakeDB(insert_error=Exception("duplicate key value violates unique constraint (23505)"))
    _use(monkeypatch, db)
    out = provision_user(user_id="u1")
    assert out["status"] == "exists" and out["provisioned"] is True  # not a 500


def test_missing_email_still_provisions(monkeypatch):
    db = FakeDB(auth_raises=True)  # auth lookup fails → email ""
    _use(monkeypatch, db)
    out = provision_user(user_id="u1")
    assert out["provisioned"] is True
    assert db.tables["user_profiles"][0]["email"] == ""


def test_database_lookup_failure_returns_structured_500(monkeypatch):
    db = FakeDB(lookup_error=Exception("connection refused"))
    _use(monkeypatch, db)
    with pytest.raises(HTTPException) as exc:
        provision_user(user_id="u1")
    assert exc.value.status_code == 500
    assert exc.value.detail["code"] == "provision_failed"
    assert "ref" in exc.value.detail
    # never leaks the raw error to the client
    assert "connection refused" not in str(exc.value.detail["message"])


def test_insert_failure_returns_structured_500(monkeypatch):
    db = FakeDB(insert_error=Exception("permission denied for table user_profiles"))
    _use(monkeypatch, db)
    with pytest.raises(HTTPException) as exc:
        provision_user(user_id="u1")
    assert exc.value.status_code == 500
    assert exc.value.detail["code"] == "provision_failed"


def test_retry_after_partial_prefs_failure(monkeypatch):
    # first call: profile created, prefs insert fails (non-duplicate) → non-fatal
    db = FakeDB(prefs_error=Exception("relation notification_prefs does not exist"))
    _use(monkeypatch, db)
    first = provision_user(user_id="u1")
    assert first["status"] == "created" and first["provisioned"] is True
    assert db.tables["notification_prefs"] == []  # prefs failed, but provisioning succeeded
    # retry after the prefs table is available
    db.prefs_error = None
    second = provision_user(user_id="u1")
    assert second["status"] == "exists"
    assert any(r["user_id"] == "u1" for r in db.tables["notification_prefs"])


def test_authenticated_user_without_profile_is_provisioned(monkeypatch):
    # authed (we have a user_id) but no application profile row yet
    db = FakeDB(existing=[])
    _use(monkeypatch, db)
    out = provision_user(user_id="brand-new")
    assert out["status"] == "created"
