"""Store Index Worker-Run accounting + single-flight correctness.

Diagnosis (see docs/DIAGNOSIS_WORKER_RUNS.md): the impossible 'processed=0 while
verified+rejected>0' rows came from `record_run` mapping — stage_verification /
stage_knowledge returned no `processed` key, so processed defaulted to 0 while
verified/rejected came through. The staged tasks also had no single-flight lock
(only the legacy daily task did), so a manual run could overlap a scheduled one.
"""
import app.services.scheduler_status as ss


# ── record_run column semantics ────────────────────────────────────────────

class _CapturingDB:
    def __init__(self):
        self.rows = []
    def table(self, _name):
        return self
    def insert(self, row):
        self.rows.append(row)
        return self
    def execute(self):
        class _R:  # noqa
            data = None
        return _R()


def _record(monkeypatch, result, **kw):
    db = _CapturingDB()
    monkeypatch.setattr(ss, "get_supabase", lambda: db, raising=False)
    import app.core.database as dbmod
    monkeypatch.setattr(dbmod, "get_supabase", lambda: db)
    ss.record_run("stage_verification", result, **kw)
    return db.rows[-1] if db.rows else None


def test_40_attempted_38_verified_2_rejected(monkeypatch):
    row = _record(monkeypatch, {"status": "ok", "processed": 40, "verified": 38,
                                "rejected": 2, "failed": 0, "reverified": 0})
    assert row["processed"] == 40
    assert row["verified"] == 38 and row["rejected"] == 2
    assert row["trigger"] == "scheduled:stage_verification"


def test_processed_never_zero_when_outcomes_exist(monkeypatch):
    # the historical bug: no explicit processed key → must derive from outcomes
    row = _record(monkeypatch, {"status": "ok", "verified": 37, "rejected": 3, "failed": 0})
    assert row["processed"] == 40  # 37 + 3 + 0, never 0


def test_partial_failure_counted_in_processed(monkeypatch):
    row = _record(monkeypatch, {"status": "ok", "verified": 30, "rejected": 5, "failed": 5})
    assert row["processed"] == 40
    assert row["failed"] == 5


def test_reverified_distinct_from_new_verified(monkeypatch):
    row = _record(monkeypatch, {"status": "ok", "processed": 10, "verified": 6,
                                "rejected": 1, "failed": 0, "reverified": 3})
    assert row["verified"] == 6 and row["reverified"] == 3
    assert row["processed"] == 10  # explicit wins, and ≥ 6+1+0+3

def test_manual_trigger_and_task_id_provenance(monkeypatch):
    row = _record(monkeypatch, {"status": "ok", "verified": 1, "rejected": 0, "failed": 0},
                  trigger="manual", task_id="abcdef1234567890")
    assert row["trigger"] == "manual:stage_verification"
    assert "task=abcdef123456" in row["notes"]


def test_empty_batch_records_zeroes_without_crash(monkeypatch):
    row = _record(monkeypatch, {"status": "ok", "processed": 0, "verified": 0,
                                "rejected": 0, "failed": 0, "note": "queue_empty"})
    assert row["processed"] == 0 and row["verified"] == 0
    assert "queue_empty" in row["notes"]


# ── single-flight lock via the decorator ───────────────────────────────────

class _FakeRedis:
    def __init__(self, store):
        self.store = store
    def set(self, key, _v, nx=False, ex=None):
        if nx and key in self.store:
            return False
        self.store[key] = "1"
        return True
    def delete(self, key):
        self.store.pop(key, None)


def test_overlapping_run_is_skipped_and_records_nothing(monkeypatch):
    shared = {}
    monkeypatch.setattr(ss, "_acquire_single_flight",
                        lambda stage, ttl: (_FakeRedis(shared) if _FakeRedis(shared).set(f"lock:index:{stage}", "1", nx=True) else None))
    # Simpler: drive the real helper against a fake redis client.
    import types
    fake_mod = types.SimpleNamespace(from_url=lambda *a, **k: _FakeRedis(shared))
    monkeypatch.setitem(__import__("sys").modules, "redis", fake_mod)

    records = []
    monkeypatch.setattr(ss, "record_run", lambda *a, **k: records.append((a, k)))
    monkeypatch.setattr(ss, "record_dispatch", lambda *a, **k: None)

    calls = {"n": 0}

    @ss.scheduled_index_task("stage_verification")
    def _task(limit_override=None, force=False):
        calls["n"] += 1
        return {"status": "ok", "processed": 5, "verified": 5, "rejected": 0, "failed": 0}

    # First acquires the lock and runs; while it "holds" the lock (we don't
    # release between calls here because we simulate concurrency by pre-locking):
    shared["lock:index:stage_verification"] = "1"  # someone else holds it
    out = _task()
    assert out["status"] == "skipped_lock"
    assert calls["n"] == 0            # body never ran
    assert records == []              # NO run record for a skipped run


def test_one_execution_writes_exactly_one_record(monkeypatch):
    shared = {}
    import types
    fake_mod = types.SimpleNamespace(from_url=lambda *a, **k: _FakeRedis(shared))
    monkeypatch.setitem(__import__("sys").modules, "redis", fake_mod)
    records = []
    monkeypatch.setattr(ss, "record_run", lambda *a, **k: records.append((a, k)))
    monkeypatch.setattr(ss, "record_dispatch", lambda *a, **k: None)

    @ss.scheduled_index_task("stage_verification")
    def _task(limit_override=None, force=False):
        return {"status": "ok", "processed": 5, "verified": 5, "rejected": 0, "failed": 0}

    _task()
    assert len(records) == 1                          # exactly one record
    assert "lock:index:stage_verification" not in shared  # lock released in finally
    # a forced (manual) run is tagged as such
    records.clear()
    _task(force=True)
    assert records[0][1]["trigger"] == "manual"


def test_skipped_status_writes_no_record(monkeypatch):
    # a task that returns skipped_lock itself (or disabled) must not be recorded
    shared = {}
    import types
    monkeypatch.setitem(__import__("sys").modules, "redis",
                        types.SimpleNamespace(from_url=lambda *a, **k: _FakeRedis(shared)))
    records = []
    monkeypatch.setattr(ss, "record_run", lambda *a, **k: records.append(1))
    monkeypatch.setattr(ss, "record_dispatch", lambda *a, **k: None)

    @ss.scheduled_index_task("stage_knowledge")
    def _task(limit_override=None, force=False):
        return {"status": "disabled"}

    _task()
    assert records == []
