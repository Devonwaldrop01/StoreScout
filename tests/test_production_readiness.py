"""Offline failure-injection checks for multi-process verification safety."""
import asyncio
import ssl
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from app.core.redis_connection import secure_redis_url
from app.services import index_lease as leases, scheduler_status as scheduler
from app.services import verification_delivery as delivery


class RedisModel:
    """Atomic NX/expiry/Lua behavior with a controllable server clock."""
    def __init__(self):
        self.rows, self.now, self.fail = {}, 0, False
        self.mutex = threading.Lock()
    def live(self, key):
        row = self.rows.get(key)
        if row and row[1] <= self.now:
            self.rows.pop(key)
        return self.rows.get(key)
    def set(self, key, token, *, nx, ex):
        with self.mutex:
            if self.fail: raise ConnectionError("offline")
            if self.live(key): return False
            self.rows[key] = (token, self.now + ex)
            return True
    def eval(self, script, count, key, token, *args):
        with self.mutex:
            if self.fail: raise ConnectionError("offline")
            row = self.live(key)
            if not row or row[0] != token: return 0
            if "'del'" in script: self.rows.pop(key)
            else: self.rows[key] = (token, self.now + args[0])
            return 1
    def close(self): pass


@pytest.fixture
def redis_model(monkeypatch):
    model = RedisModel()
    monkeypatch.setattr(leases, "coordination_redis", lambda: model)
    monkeypatch.setattr(scheduler, "record_dispatch", lambda *a: None)
    monkeypatch.setattr(scheduler, "record_run", lambda *a, **k: None)
    return model


def test_acquisition_is_exclusive_and_release_allows_next_owner(redis_model):
    first = leases.acquire_stage("stage_verification", 30)
    assert first and leases.acquire_stage("stage_verification", 30) is None
    first.release()
    second = leases.acquire_stage("stage_verification", 30)
    assert second.token != first.token
    second.release()


def test_expiry_old_owner_cannot_release_or_renew_new_owner(redis_model):
    first = leases.acquire_stage("stage_verification", 30)
    redis_model.now = 31
    second = leases.acquire_stage("stage_verification", 30)
    assert not first.renew()
    first.release()
    assert leases.acquire_stage("stage_verification", 30) is None
    second.require()
    second.release()


def test_renewal_keeps_a_long_batch_exclusive(redis_model):
    first = leases.acquire_stage("stage_verification", 30)
    redis_model.now = 20
    first.require()
    redis_model.now = 35
    assert leases.acquire_stage("stage_verification", 30) is None
    first.release()


def test_elapsed_local_lease_cannot_be_revived(redis_model, monkeypatch):
    first = leases.acquire_stage("stage_verification", 30)
    monkeypatch.setattr(leases.time, "monotonic", lambda: first.valid_until + 1)
    assert not first.renew()
    first.release()


def test_redis_failure_refuses_batch_even_when_forced(redis_model):
    redis_model.fail = True
    @scheduler.scheduled_index_task("stage_verification")
    def task(**kwargs): raise AssertionError("must not execute")
    assert task(force=True)["status"] == "lock_unavailable"


def test_renewal_failure_stops_further_work(redis_model):
    first = leases.acquire_stage("stage_verification", 30)
    redis_model.fail = True
    with pytest.raises(leases.LeaseLost): first.require()
    redis_model.fail = False
    with pytest.raises(leases.LeaseLost): first.require()
    first.release()


def test_two_actual_threads_cannot_enter_the_same_batch(redis_model):
    entered, finish = threading.Event(), threading.Event()
    calls = []
    @scheduler.scheduled_index_task("stage_verification")
    def task():
        calls.append(1)
        entered.set()
        assert finish.wait(3)
        return {"status": "ok", "processed": 1}
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(task)
        try:
            assert entered.wait(3)
            assert pool.submit(task).result(timeout=3)["status"] == "skipped_lock"
            assert len(calls) == 1
        finally:
            finish.set()
        assert first.result(timeout=3)["status"] == "ok"
    assert not redis_model.rows


def test_verification_executor_stops_queued_domains_after_lease_loss(redis_model, monkeypatch):
    import app.tasks.store_index as tasks
    from test_candidate_supply import _FakeDB
    rows = [{"domain": "one.test", "status": "candidate"},
            {"domain": "two.test", "status": "candidate"}]
    monkeypatch.setattr(tasks, "get_supabase", lambda: _FakeDB(rows, {}))
    monkeypatch.setattr(tasks, "get_settings", lambda: SimpleNamespace(
        shopify_index_enabled=True, shopify_index_verify_batch=2, shopify_index_concurrency=1))
    monkeypatch.setattr("app.services.runtime_config.get_config", lambda k, d=None: d)
    calls = []
    def verify(domain, *args):
        calls.append(domain)
        redis_model.fail = True
        return {"outcome": "verified"}
    monkeypatch.setattr(tasks, "_verify_via_web", verify)
    holder = leases.acquire_stage("stage_verification", 30)
    context = leases.current_lease.set(holder)
    try:
        with pytest.raises(leases.LeaseLost):
            tasks.stage_verification.__wrapped__.__wrapped__(force=True)
        assert len(calls) == 1
    finally:
        redis_model.fail = False
        leases.current_lease.reset(context)
        holder.release()


@pytest.mark.parametrize("flag", ["CERT_NONE", "none", "CERT_REQUIRED", "required", "optional"])
def test_tls_url_requires_certificate_and_hostname_validation(flag):
    import redis
    url = secure_redis_url(f"rediss://test:password@redis.example:6380/1?ssl_cert_reqs={flag}&ssl_check_hostname=false&socket_timeout=3")
    query = parse_qs(urlsplit(url).query)
    assert query["ssl_cert_reqs"] == ["required"]
    assert query["ssl_check_hostname"] == ["true"]
    assert query["socket_timeout"] == ["3"]
    client = redis.from_url(url)
    pool = client.connection_pool
    connection = pool.connection_class(**pool.connection_kwargs)
    assert connection.cert_reqs == ssl.CERT_REQUIRED
    assert connection.check_hostname is True
    client.close()


def test_plain_redis_url_and_celery_defaults():
    assert secure_redis_url("redis://localhost:6379/0") == "redis://localhost:6379/0"
    from app.tasks.celery_app import celery
    assert celery.conf.broker_transport_options["polling_interval"] == 5
    assert celery.conf.beat_schedule["index-stage-verification"]["schedule"].minute == {0, 15, 30, 45}


def run_delivery(handler):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await delivery.deliver("https://web.test/verify", {"domain": "shop.test"}, {}, client=client)
    return asyncio.run(run())


def test_delivery_success():
    assert run_delivery(lambda r: httpx.Response(200, json={"outcome": "verified"}))["outcome"] == "verified"


def test_slow_drip_hits_wall_deadline_without_duplicate_post(monkeypatch):
    monkeypatch.setattr(delivery, "ATTEMPT_DEADLINE_S", .03)
    calls = []
    class Drip(httpx.AsyncByteStream):
        async def __aiter__(self):
            while True:
                await asyncio.sleep(.005)
                yield b" "
        async def aclose(self): calls.append("closed")
    def handler(request):
        calls.append("post")
        return httpx.Response(200, stream=Drip())
    assert run_delivery(handler)["reason"] == "web_unreachable"
    assert calls == ["post", "closed"]


def test_connect_failure_retries_but_read_timeout_does_not(monkeypatch):
    monkeypatch.setattr(delivery, "RETRY_DELAY_S", 0)
    for error, expected in [(httpx.ConnectError, 2), (httpx.ReadTimeout, 1)]:
        calls = []
        def handler(request):
            calls.append(1)
            raise error("injected", request=request)
        assert run_delivery(handler)["reason"] == "web_unreachable"
        assert len(calls) == expected


@pytest.mark.parametrize("status", [429, 500, 503])
def test_server_error_does_not_replay_possibly_committed_request(status):
    calls = []
    def handler(request):
        calls.append(1)
        return httpx.Response(status)
    assert run_delivery(handler)["reason"] == "web_unreachable"
    assert len(calls) == 1


def test_total_deadline_includes_retry_delay(monkeypatch):
    monkeypatch.setattr(delivery, "TOTAL_DEADLINE_S", .02)
    monkeypatch.setattr(delivery, "RETRY_DELAY_S", 10)
    def handler(request): raise httpx.ConnectError("injected", request=request)
    assert run_delivery(handler)["reason"] == "web_unreachable"


def test_response_size_is_bounded(monkeypatch):
    monkeypatch.setattr(delivery, "MAX_RESPONSE_BYTES", 10)
    assert run_delivery(lambda r: httpx.Response(200, content=b" " * 11))["reason"] == "web_unreachable"


def test_real_postgrest_client_emits_ignore_duplicate_and_cas_filters():
    from postgrest import SyncPostgrestClient
    from app.services.store_index import upsert_index_row, _finish_verification
    requests = []
    def handler(request):
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[])
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        db = SyncPostgrestClient("https://db.test/rest/v1", http_client=http)
        assert upsert_index_row(db, "shop.test", {"status": "candidate"}) == "skipped"
        insert = requests[-1]
        assert insert.method == "POST"
        assert insert.url.params["on_conflict"] == "domain"
        assert "resolution=ignore-duplicates" in insert.headers["Prefer"]
        assert not _finish_verification(db, "shop.test", "old-token", {"status": "verified"})
        update = requests[-1]
        assert update.method == "PATCH"
        assert update.url.params["verification_token"] == "eq.old-token"
        assert update.url.params["next_verification_at"].startswith("gt.")
