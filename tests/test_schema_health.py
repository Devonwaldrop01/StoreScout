"""Migration health — the pure summarizer and the missing-detection probe."""
from app.services.schema_health import summarize, probe, LATEST_EXPECTED_MIGRATION


def _check(required, state, migration="022", column="store_dna"):
    return {"migration": migration, "feature": "F", "table": "t", "column": column,
            "required": required, "state": state}


def test_all_present_is_healthy():
    r = summarize([_check(False, "present"), _check(True, "present", migration="001", column=None)])
    assert r["status"] == "healthy"
    assert r["latest_expected_migration"] == LATEST_EXPECTED_MIGRATION
    assert r["missing_required"] == [] and r["missing_optional"] == []


def test_optional_missing_is_degraded_and_named():
    r = summarize([_check(False, "missing")])
    assert r["status"] == "degraded"
    assert len(r["missing_optional"]) == 1
    assert r["missing_optional"][0]["column"] == "store_dna"


def test_required_missing_is_unhealthy():
    r = summarize([_check(True, "missing", migration="001", column=None)])
    assert r["status"] == "unhealthy"
    assert len(r["missing_required"]) == 1


def test_all_db_error_is_db_unavailable():
    r = summarize([_check(True, "db_error", migration="001", column=None)])
    assert r["status"] == "db_unavailable"


class _RaisingQuery:
    def __init__(self, exc):
        self._exc = exc

    def select(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        raise self._exc


class _OkQuery(_RaisingQuery):
    def __init__(self):
        pass

    def execute(self):
        return type("R", (), {"data": []})()


class _DB:
    def __init__(self, q):
        self._q = q

    def table(self, *a, **k):
        return self._q


def test_probe_detects_missing_column():
    db = _DB(_RaisingQuery(Exception('column "store_dna" does not exist')))
    assert probe(db, "shopify_store_index", "store_dna") == "missing"


def test_probe_detects_missing_relation():
    db = _DB(_RaisingQuery(Exception('relation "intent_signals" does not exist')))
    assert probe(db, "intent_signals", None) == "missing"


def test_probe_other_error_is_db_error():
    db = _DB(_RaisingQuery(Exception("connection refused")))
    assert probe(db, "competitors", None) == "db_error"


def test_probe_present():
    assert probe(_DB(_OkQuery()), "competitors", None) == "present"
