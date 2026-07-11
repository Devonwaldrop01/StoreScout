"""Scheduler visibility — schedule registration, task routing, run recording,
dispatch heartbeat, and evidence-only status assembly."""
import app.services.scheduler_status as sched


# ── Schedule registration + routing (Celery config, no broker) ────────────────

def test_all_four_staged_tasks_are_scheduled():
    from app.tasks.celery_app import celery
    tasks = {v.get("task") for v in (celery.conf.beat_schedule or {}).values()}
    for stage in ["stage_discovery", "stage_resolution", "stage_verification", "stage_knowledge"]:
        assert f"app.tasks.store_index.{stage}" in tasks


def test_index_tasks_route_to_a_consumed_queue():
    # worker consumes -Q default,priority; the catch-all must send index tasks to default
    from app.tasks.celery_app import celery
    routes = celery.conf.task_routes or {}
    assert routes.get("app.tasks.*", {}).get("queue") == "default"


# ── Run recording ─────────────────────────────────────────────────────────────

class _Table:
    def __init__(self, sink):
        self.sink = sink

    def insert(self, row):
        self.sink.append(row)
        return self

    def execute(self):
        return type("R", (), {"data": self.sink})()


class _DB:
    def __init__(self):
        self.rows = []

    def table(self, name):
        assert name == "store_index_runs"
        return _Table(self.rows)


def test_record_run_maps_result_to_run_row(monkeypatch):
    db = _DB()
    monkeypatch.setattr("app.core.database.get_supabase", lambda: db)
    sched.record_run("stage_verification", {"status": "ok", "processed": 40, "verified": 31, "rejected": 9, "failed": 0})
    assert len(db.rows) == 1
    row = db.rows[0]
    assert row["trigger"] == "scheduled:stage_verification"
    assert row["processed"] == 40 and row["verified"] == 31 and row["rejected"] == 9


def test_record_run_is_guarded(monkeypatch):
    def boom():
        raise RuntimeError("db down")
    monkeypatch.setattr("app.core.database.get_supabase", boom)
    # must not raise
    sched.record_run("stage_knowledge", {"status": "ok", "classified": 5})


# ── Dispatch heartbeat ────────────────────────────────────────────────────────

def test_record_dispatch_writes_heartbeat_keys(monkeypatch):
    captured = {}
    monkeypatch.setattr("app.services.runtime_config.set_config", lambda updates: captured.update(updates) or updates)
    sched.record_dispatch("stage_resolution")
    assert "scheduler_last_dispatch" in captured
    assert "scheduler_dispatch_stage_resolution" in captured


# ── Decorator: dispatch before, run after (only on ok) ────────────────────────

def test_scheduled_index_task_records_dispatch_and_run(monkeypatch):
    events = []
    monkeypatch.setattr(sched, "record_dispatch", lambda stage: events.append(("dispatch", stage)))
    monkeypatch.setattr(sched, "record_run", lambda stage, result: events.append(("run", stage, result.get("status"))))

    @sched.scheduled_index_task("stage_discovery")
    def task(force=False):
        return {"status": "ok", "queued": 3}

    out = task()
    assert out == {"status": "ok", "queued": 3}
    assert ("dispatch", "stage_discovery") in events
    assert ("run", "stage_discovery", "ok") in events


def test_scheduled_index_task_disabled_records_dispatch_but_no_run(monkeypatch):
    events = []
    monkeypatch.setattr(sched, "record_dispatch", lambda stage: events.append(("dispatch", stage)))
    monkeypatch.setattr(sched, "record_run", lambda stage, result: events.append(("run", stage)))

    @sched.scheduled_index_task("stage_verification")
    def task(force=False):
        return {"status": "disabled"}

    task()
    # Beat dispatched (heartbeat), but a gated-off task writes no run row
    assert ("dispatch", "stage_verification") in events
    assert not any(e[0] == "run" for e in events)


# ── Evidence-only status assembly ─────────────────────────────────────────────

class _RunsDB:
    def __init__(self, runs):
        self._runs = runs

    def table(self, name):
        outer = self

        class Q:
            def select(self, *a, **k): return self
            def order(self, *a, **k): return self
            def limit(self, *a, **k): return self
            def execute(self): return type("R", (), {"data": outer._runs})()
        return Q()


def test_scheduler_status_reports_evidence(monkeypatch):
    runs = [
        {"ran_at": "2026-07-11T10:00:00+00:00", "trigger": "scheduled:stage_verification", "failed": 0},
        {"ran_at": "2026-07-11T09:00:00+00:00", "trigger": "manual", "failed": 2},
    ]
    cfg = {"shopify_index_enabled": False, "scheduler_last_dispatch": "2026-07-11T10:05:00+00:00"}
    monkeypatch.setattr("app.services.runtime_config.get_config", lambda k, d=None: cfg.get(k, d))
    out = sched.scheduler_status(_RunsDB(runs))
    assert out["scheduler_configured"] is True
    assert out["pipeline_enabled"] is False
    assert out["last_scheduled_run"] == "2026-07-11T10:00:00+00:00"
    assert out["last_failed_run"] == "2026-07-11T09:00:00+00:00"
    assert out["queue"] == "default"


def test_scheduler_status_stale_when_no_dispatch(monkeypatch):
    monkeypatch.setattr("app.services.runtime_config.get_config", lambda k, d=None: (False if k == "shopify_index_enabled" else None))
    out = sched.scheduler_status(_RunsDB([]))
    assert out["last_dispatch"] is None
    assert out["dispatch_looks_stale"] is True   # no heartbeat -> stale, not fabricated-healthy
