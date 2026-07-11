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


# ── Regression: migration-014 false positive ──────────────────────────────────
# business_profiles is keyed by user_id (migration 014) and has NO `id` column.
# The old probe selected `id` for table-existence checks, so an applied 014
# reported as "missing". The probe must test existence via `select("*")`.

class _ColumnAwareQuery:
    """Mimics PostgREST: selecting a non-existent column raises 'does not exist',
    but `select("*")` on an existing table succeeds."""
    def __init__(self, existing_columns):
        self._existing = set(existing_columns)
        self._sel = "*"

    def select(self, sel="*", *a, **k):
        self._sel = sel
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self._sel != "*" and self._sel not in self._existing:
            raise Exception(f'column business_profiles.{self._sel} does not exist')
        return type("R", (), {"data": []})()


def test_probe_table_without_id_column_is_present():
    # business_profiles: PK user_id, columns user_id/category/... but NO `id`.
    db = _DB(_ColumnAwareQuery({"user_id", "category", "sells"}))
    # table-existence check (column=None) must recognize it as present
    assert probe(db, "business_profiles", None) == "present"
    # a real column check still works
    assert probe(db, "business_profiles", "sells") == "present"
    # a genuinely missing column is still detected
    assert probe(db, "business_profiles", "does_not_exist") == "missing"


def test_migration_014_recognized_on_evolved_schema():
    # Full check-row for migration 014 as summarized after the fixed probe runs.
    from app.services.schema_health import summarize
    results = [{"migration": "014", "feature": "Business profiles",
                "table": "business_profiles", "column": None,
                "required": False, "state": "present"}]
    assert summarize(results)["status"] == "healthy"
    assert summarize(results)["missing_optional"] == []
