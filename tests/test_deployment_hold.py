"""No production services: exercise actual task/web/database interlocks."""
import asyncio
import importlib
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from app.core import index_hold as hold
from app.services import index_lease, scheduler_status, verification_delivery
from test_production_readiness import RedisModel


@pytest.mark.parametrize("value", [None, "", "true", "False", "0", "false ", "unknown"])
def test_unknown_or_enabled_state_fails_closed(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("STORE_INDEX_DEPLOYMENT_HOLD", raising=False)
    else:
        monkeypatch.setenv("STORE_INDEX_DEPLOYMENT_HOLD", value)
    with pytest.raises(hold.IndexDeploymentHeld):
        hold.require_index_writes()


def test_unreadable_state_fails_closed(monkeypatch):
    monkeypatch.setattr(hold, "os", SimpleNamespace(environ=Mock(get=Mock(side_effect=OSError))))
    assert hold.index_writes_held()


@pytest.mark.parametrize("table", sorted(hold.INDEX_TABLES))
@pytest.mark.parametrize("operation", ["insert", "upsert", "update", "delete"])
def test_all_index_mutations_checked_again_at_execute(monkeypatch, table, operation):
    query = Mock()
    getattr(query, operation).return_value = query
    query.eq.return_value = query
    query.select.return_value = query
    db = hold.GuardedDatabase(Mock(table=Mock(return_value=query)))
    pending = getattr(db.table(table), operation)({}).eq("domain", "example.test").select("*")
    monkeypatch.setenv("STORE_INDEX_DEPLOYMENT_HOLD", "true")
    with pytest.raises(hold.IndexDeploymentHeld):
        pending.execute()
    query.execute.assert_not_called()
    monkeypatch.setenv("STORE_INDEX_DEPLOYMENT_HOLD", "false")
    pending.execute()
    query.execute.assert_called_once()


def test_reads_and_unrelated_writes_still_work_when_held(monkeypatch):
    monkeypatch.delenv("STORE_INDEX_DEPLOYMENT_HOLD")
    query = Mock()
    query.select.return_value = query
    query.update.return_value = query
    raw = Mock(table=Mock(return_value=query))
    raw.schema.return_value = raw
    db = hold.GuardedDatabase(raw)
    db.schema("public").from_("shopify_store_index").select("*").execute()
    db.table("scan_snapshots").update({}).execute()
    assert query.execute.call_count == 2
    with pytest.raises(hold.IndexDeploymentHeld):
        db.schema("public").table("shopify_store_index").delete()


@pytest.mark.parametrize("name", [
    "stage_discovery", "stage_resolution", "stage_verification", "stage_knowledge",
    "generate_niche_candidates", "generate_related_candidates", "generate_candidates_rotating",
    "discover_shopify_stores_daily", "verification_canary_wave",
])
def test_all_worker_tasks_and_publication_are_held(monkeypatch, name):
    from app.tasks import store_index
    task = getattr(store_index, name)
    monkeypatch.setenv("STORE_INDEX_DEPLOYMENT_HOLD", "true")
    assert task(force=True)["status"] == "deployment_hold"
    with pytest.raises(hold.IndexDeploymentHeld): task.delay()
    with pytest.raises(hold.IndexDeploymentHeld): task.retry(countdown=30)


def test_beat_suppresses_only_index_entries_and_resumes(monkeypatch):
    from app.tasks.index_hold import HeldIndexScheduler, PersistentScheduler
    from app.tasks.celery_app import celery
    scheduler = HeldIndexScheduler(app=celery, lazy=True)
    reserve = Mock()
    monkeypatch.setattr(scheduler, "reserve", reserve)
    publish = Mock(return_value="sent")
    monkeypatch.setattr(PersistentScheduler, "apply_async", publish)
    monkeypatch.setenv("STORE_INDEX_DEPLOYMENT_HOLD", "true")
    for item in celery.conf.beat_schedule.values():
        entry = SimpleNamespace(task=item["task"])
        result = scheduler.apply_async(entry)
        assert result is None if ".store_index." in item["task"] else result == "sent"
    assert reserve.call_count == 5
    monkeypatch.setenv("STORE_INDEX_DEPLOYMENT_HOLD", "false")
    assert scheduler.apply_async(SimpleNamespace(task="app.tasks.store_index.stage_verification")) == "sent"


def test_hold_stops_renewals_but_releases_and_new_run_recovers(monkeypatch):
    model = RedisModel()
    monkeypatch.setattr(index_lease, "coordination_redis", lambda: model)
    dispatch, record = Mock(), Mock()
    monkeypatch.setattr(scheduler_status, "record_dispatch", dispatch)
    monkeypatch.setattr(scheduler_status, "record_run", record)
    @scheduler_status.scheduled_index_task("stage_verification")
    def task(flip=False):
        if flip: monkeypatch.setenv("STORE_INDEX_DEPLOYMENT_HOLD", "true")
        return {"status": "ok", "processed": 1}
    assert task(flip=True)["status"] == "deployment_hold"
    assert not model.rows
    record.assert_not_called()
    assert task()["status"] == "deployment_hold"
    assert dispatch.call_count == 1
    monkeypatch.setenv("STORE_INDEX_DEPLOYMENT_HOLD", "false")
    assert task()["status"] == "ok"
    assert not model.rows
    lease = index_lease.acquire_stage("stage_verification", 30)
    monkeypatch.setenv("STORE_INDEX_DEPLOYMENT_HOLD", "true")
    assert not lease.renew()
    lease.release()
    assert not model.rows


def test_retry_rechecks_hold_before_second_delegated_request(monkeypatch):
    requests = []
    def handler(request):
        requests.append(request)
        monkeypatch.setenv("STORE_INDEX_DEPLOYMENT_HOLD", "true")
        raise httpx.ConnectError("offline", request=request)
    monkeypatch.setattr(verification_delivery, "RETRY_DELAY_S", 0)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await verification_delivery.deliver("https://offline.invalid/verify", {"domain":"example.test"}, {}, client=client)
    with pytest.raises(hold.IndexDeploymentHeld): asyncio.run(run())
    assert len(requests) == 1


@pytest.mark.parametrize("module,name,args", [
    ("app.services.store_index", "verify_and_store", (None, "example.test", "test")),
    ("app.services.store_index", "run_knowledge", (None, {})),
    ("app.services.store_index", "upsert_index_row", (None, "example.test", {})),
    ("app.services.store_index", "record_competitor_edge", (None, "test", "example.test", "test")),
    ("app.services.store_index", "index_store_pass", ("example.test",)),
    ("app.services.verification_canary", "verify_canary", ({}, SimpleNamespace(store_index_canary_enabled=True), None)),
    ("app.api.v1.internal", "internal_store_index_verify", ({},)),
    ("app.api.v1.internal", "internal_store_index_process", ({},)),
    ("app.api.v1.internal", "internal_shop_app_resolve", ({},)),
])
def test_direct_paths_stop_before_credentials_fetch_or_writes(monkeypatch, module, name, args):
    monkeypatch.setenv("STORE_INDEX_DEPLOYMENT_HOLD", "true")
    with pytest.raises(hold.IndexDeploymentHeld): getattr(importlib.import_module(module), name)(*args)


def test_http_hold_is_explicit_maintenance_response(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setenv("STORE_INDEX_DEPLOYMENT_HOLD", "true")
    response = TestClient(app).post("/api/v1/internal/store-index/verify", json={"domain":"example.test"}, headers={"x-internal-token":"offline"})
    assert response.status_code == 503
    assert response.json()["code"] == "deployment_hold"


def test_abandoned_row_claim_is_retryable_after_hold_and_expiry(monkeypatch):
    from datetime import datetime, timedelta
    from test_verification_lifecycle import MemoryDB, row, NOW
    from app.services import store_index
    clock = [NOW]
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None): return clock[0]
    monkeypatch.setattr(store_index, "datetime", Clock)
    db = MemoryDB([row()])
    previous, token = store_index._claim_verification(db, "linen.test", "test", None)
    monkeypatch.setenv("STORE_INDEX_DEPLOYMENT_HOLD", "true")
    with pytest.raises(hold.IndexDeploymentHeld):
        store_index._finish_verification(db, "linen.test", token, {"status":"verified"})
    assert db.rows['linen.test']['status'] == 'discovered'
    monkeypatch.setenv("STORE_INDEX_DEPLOYMENT_HOLD", "false")
    assert store_index._claim_verification(db, "linen.test", "test", None) is None
    clock[0] += timedelta(minutes=6)
    replacement = store_index._claim_verification(db, "linen.test", "test", None)
    assert replacement and replacement[1] != token


def test_index_config_cannot_override_hold(monkeypatch):
    from app.services.runtime_config import set_config
    monkeypatch.setenv("STORE_INDEX_DEPLOYMENT_HOLD", "true")
    with pytest.raises(hold.IndexDeploymentHeld): set_config({'shopify_index_enabled':True})
