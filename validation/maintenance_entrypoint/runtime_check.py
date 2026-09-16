"""Held application assertions, exclusively on an isolated fake-service network."""
import json
import os
import ssl
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
from app.core.config import get_settings
from app.core import index_hold
from app.core.redis_connection import coordination_redis
from app.tasks.celery_app import celery
from app.tasks.index_hold import HeldIndexScheduler, PersistentScheduler
from app.tasks import store_index

settings = get_settings()
assert settings.supabase_url == "http://dbsink:8080"
assert not settings.anthropic_api_key and not settings.store_index_canary_enabled
assert index_hold.index_writes_held()
tasks = ["stage_discovery", "stage_resolution", "stage_verification", "stage_knowledge",
         "generate_niche_candidates", "generate_related_candidates", "generate_candidates_rotating",
         "discover_shopify_stores_daily", "verification_canary_wave"]
for value in (None, "true", "", "unknown", "False", "false "):
    if value is None:
        os.environ.pop("STORE_INDEX_DEPLOYMENT_HOLD", None)
    else:
        os.environ["STORE_INDEX_DEPLOYMENT_HOLD"] = value
    assert index_hold.index_writes_held()
    for name in tasks:
        task = getattr(store_index, name)
        assert task(force=True)["status"] == "deployment_hold", name
        for action in (lambda: task.delay(force=True), lambda: task.retry(countdown=1)):
            try:
                action()
            except index_hold.IndexDeploymentHeld:
                pass
            else:
                raise AssertionError("held task published or retried: " + name)
os.environ["STORE_INDEX_DEPLOYMENT_HOLD"] = "true"
for table in index_hold.INDEX_TABLES:
    for method in ("insert", "upsert", "update", "delete"):
        raw = Mock()
        try:
            getattr(index_hold.GuardedDatabase(raw).table(table), method)({}).execute()
        except index_hold.IndexDeploymentHeld:
            pass
        else:
            raise AssertionError("held DB mutation permitted")
        getattr(raw.table.return_value, method).assert_not_called()

scheduler = HeldIndexScheduler(app=celery, lazy=True)
scheduler.reserve = Mock()
with patch.object(PersistentScheduler, "apply_async", side_effect=AssertionError("index task published")):
    for spec in celery.conf.beat_schedule.values():
        if spec["task"].startswith("app.tasks.store_index."):
            assert scheduler.apply_async(SimpleNamespace(task=spec["task"])) is None
assert scheduler.reserve.call_count == 5

connection = coordination_redis()
assert connection.ping()
actual = connection.connection_pool.get_connection()
try:
    assert actual._sock.context.verify_mode == ssl.CERT_REQUIRED
    assert actual._sock.context.check_hostname
finally:
    connection.connection_pool.release(actual)

reply = None
for _ in range(20):
    reply = celery.control.inspect(timeout=1).stats()
    if reply:
        break
    time.sleep(0.5)
assert reply, "worker did not become ready"
assert all(v["pool"]["max-concurrency"] == 2 and len(v["pool"]["processes"]) == 2 for v in reply.values())
with httpx.Client(timeout=4) as client:
    for _ in range(20):
        try:
            assert client.get("http://web:10000/").status_code == 200
            break
        except httpx.TransportError:
            time.sleep(0.5)
    else:
        raise AssertionError("web not ready")
    response = client.post("http://web:10000/api/v1/internal/store-index/verify",
                           json={"domain": "never-fetch.invalid"},
                           headers={"x-internal-token": "offline-test"})
    assert response.status_code == 503 and response.json()["code"] == "deployment_hold"

# Simulate pre-existing deliveries: bypass producer wrappers deliberately, but
# delivery must still be held by the real running worker. Broker is disposable.
ids = []
for name in tasks:
    ids.append(celery.send_task("app.tasks.store_index." + name,
                               kwargs={"force": True}).id)
print(json.dumps({"held_states": 6, "direct_tasks_per_state": len(tasks),
                  "beat_entries_suppressed": 5, "database_mutation_guards": 20,
                  "web": "healthy/held", "worker_processes": 2,
                  "tls": "CERT_REQUIRED+hostname", "delivery_ids": ids}))
