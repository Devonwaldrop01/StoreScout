import hashlib
import json
from types import SimpleNamespace
from datetime import timedelta

import httpx
import pytest
from fastapi import HTTPException

from app.services import verification_canary as canary
from app.services import store_index as index
from app.services import index_lease as leases
from test_production_readiness import RedisModel
from test_verification_lifecycle import MemoryDB, row, success, NOW, frozen


@pytest.fixture
def setup_canary(tmp_path, monkeypatch, frozen):
    rows = [row(domain=f"store{i}.test") for i in range(12)]
    manifest = {"version":1, "live_rows_confirmed":True, "expires_at":"2027-01-01T00:00:00+00:00",
                "stores":[{"domain":r["domain"],"expected_updated_at":r["updated_at"]} for r in rows]}
    path = tmp_path/'manifest.json'
    path.write_text(json.dumps(manifest))
    monkeypatch.setattr(canary, "MANIFEST_PATH", path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    settings = SimpleNamespace(store_index_canary_enabled=True,store_index_canary_manifest_sha256=digest)
    class Redis(RedisModel):
        def __init__(self):
            super().__init__()
            self.ledger = {canary.ledger_key(digest):json.dumps({"manifest_sha256":digest,"state":"ready","completed":[]})}
        def get(self, key): return self.ledger.get(key)
        def set(self, key, token, *, nx=False, ex=None, xx=False):
            if xx:
                if key not in self.ledger: return False
                self.ledger[key] = token
                return True
            return super().set(key, token, nx=nx, ex=ex)
    redis = Redis()
    monkeypatch.setattr(leases, "coordination_redis", lambda:redis)
    db = MemoryDB(rows)
    monkeypatch.setattr(index, "index_store_pass", lambda domain:success())
    def call(domain="store0.test", **extra):
        return canary.verify_canary({"domain":domain,"manifest_sha256":digest,**extra}, settings, lambda:db)
    return SimpleNamespace(manifest=manifest,path=path,digest=digest,settings=settings,db=db,redis=redis,call=call)


@pytest.mark.parametrize("change", ["disabled","digest","unconfirmed","expired","duplicates","short"])
def test_manifest_gates_prevent_any_row_write(setup_canary, change):
    s=setup_canary
    if change=="disabled": s.settings.store_index_canary_enabled=False
    elif change=="digest": s.settings.store_index_canary_manifest_sha256="wrong"
    else:
        m=s.manifest
        if change=="unconfirmed": m['live_rows_confirmed']=False
        elif change=="expired": m['expires_at']='2000-01-01T00:00:00+00:00'
        elif change=="duplicates": m['stores'][1]=m['stores'][0]
        else: m['stores'].pop()
        s.path.write_text(json.dumps(m));s.settings.store_index_canary_manifest_sha256=hashlib.sha256(s.path.read_bytes()).hexdigest()
    with pytest.raises((HTTPException,ValueError)): s.call()
    assert all(not r.get('verification_token') and r['status']=='discovered' for r in s.db.rows.values())


@pytest.mark.parametrize('domain',['other.test','www.store0.test','STORE0.test','https://store0.test','store0.test/','store0.test:443'])
def test_aliases_and_outside_domains_are_rejected(setup_canary, domain):
    with pytest.raises(HTTPException) as exc: setup_canary.call(domain)
    assert exc.value.status_code==403


def test_force_or_other_extra_fields_cannot_bypass_manifest(setup_canary):
    with pytest.raises(HTTPException) as exc: setup_canary.call(force=True)
    assert exc.value.status_code==422


def test_stale_or_missing_row_cannot_seed_or_fetch(setup_canary, monkeypatch):
    s=setup_canary
    del s.db.rows['store0.test']
    monkeypatch.setattr(index,'index_store_pass',lambda d:pytest.fail('missing row must not fetch'))
    result=s.call()
    assert result['canary_state']=='stopped'
    assert 'store0.test' not in s.db.rows


def test_modified_row_version_refuses_fetch(setup_canary, monkeypatch):
    s=setup_canary
    s.db.rows['store0.test']['updated_at']=NOW.isoformat()
    monkeypatch.setattr(index,'index_store_pass',lambda d:pytest.fail('stale manifest must not fetch'))
    assert s.call()['outcome']=='skipped'


def test_missing_ledger_is_never_implicitly_armed(setup_canary):
    s=setup_canary;s.redis.ledger.clear()
    with pytest.raises(HTTPException) as exc:s.call()
    assert exc.value.status_code==409 and not s.redis.ledger


def test_order_replay_and_three_store_checkpoint(setup_canary):
    s=setup_canary
    with pytest.raises(HTTPException):s.call('store1.test')
    assert s.call()['canary_state']=='ready'
    with pytest.raises(HTTPException):s.call()
    assert s.call('store1.test')['canary_state']=='ready'
    assert s.call('store2.test')['canary_state']=='checkpoint'
    with pytest.raises(HTTPException):s.call('store3.test')
    assert sum(r['status']=='verified' for r in s.db.rows.values())==3


def test_readable_catalog_absence_is_measured_without_stopping_sample(setup_canary, monkeypatch):
    s=setup_canary
    monkeypatch.setattr(index,'index_store_pass',lambda d:{'access_state':'no_readable_catalog','reachable':True,'monitorable':False})
    result=s.call()
    assert result['reason']=='no_readable_catalog' and result['canary_state']=='ready'
    assert s.call('store1.test')['reason']=='no_readable_catalog'


def test_db_version_prevents_replay_even_if_ledger_is_reset(setup_canary):
    s=setup_canary
    assert s.call()['outcome']=='verified'
    s.redis.ledger[canary.ledger_key(s.digest)]=json.dumps({'manifest_sha256':s.digest,'state':'ready','completed':[]})
    assert s.call()['outcome']=='skipped'


def test_crash_leaves_inflight_ledger_and_prevents_retry(setup_canary, monkeypatch):
    s=setup_canary
    monkeypatch.setattr(index,'verify_and_store',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('crash')))
    with pytest.raises(RuntimeError):s.call()
    with pytest.raises(HTTPException):s.call()
    assert json.loads(s.redis.ledger[canary.ledger_key(s.digest)])['state']=='inflight'


@pytest.mark.parametrize('status,body',[(403,b'denied'),(429,b'limit'),(200,b'cf-chl-challenge'),(200,b'shopify-section-main-password'),(302,b'')])
def test_probe_stops_after_protection_or_redirect(status,body):
    guard=canary.ProbeGuard('store.test');calls=[]
    def get(url,**kw):
        calls.append((url,kw));return httpx.Response(status,content=body,headers={'location':'https://other.test/'})
    client=SimpleNamespace(get=get)
    guard.get(client,'https://store.test/',12,True)
    with pytest.raises(RuntimeError):guard.get(client,'https://store.test/cart.js',8,True)
    assert len(calls)==1 and calls[0][1]['allow_redirects'] is False
    assert guard.stop_reason


def test_probe_cannot_fetch_extra_hosts_or_repeat_endpoints():
    calls=[]
    client=SimpleNamespace(get=lambda url,**kw:(calls.append((url,kw)) or httpx.Response(200,content=b'{}')))
    guard=canary.ProbeGuard('store.test')
    for path in ['/','/cart.js','/products.json?limit=250','/collections.json?limit=50']:
        guard.get(client,'https://store.test'+path,12,False)
    with pytest.raises(RuntimeError):guard.get(client,'https://store.test/',12,False)
    assert len(calls)==4 and all(x[1]['follow_redirects'] is False for x in calls)
    for url in ['http://store.test/','https://other.test/','https://store.test:443/','https://store.test/admin']:
        with pytest.raises(RuntimeError):canary.ProbeGuard('store.test').get(client,url,12,True)
    assert len(calls)==4


def test_canary_protection_survives_probe_exception_handling(monkeypatch):
    guard=canary.ProbeGuard('store.test');calls=[]
    class Client:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def get(self,url,**kw):
            calls.append(url);return httpx.Response(403,content=b'protected')
    monkeypatch.setattr(index,'_make_client',lambda:Client())
    monkeypatch.setattr(index,'_enforce_domain_rate_limit',lambda d:None)
    context=canary.probe_context.set(guard)
    try:result=index.index_store_pass('store.test')
    finally:canary.probe_context.reset(context)
    assert len(calls)==1 and result['access_state']=='blocked' and not result['monitorable']


def test_packaged_manifest_is_exactly_twelve_and_non_runnable():
    from app.core.config import Settings
    manifest,digest=canary.load_manifest(Settings(_env_file=None),require_enabled=False)
    assert len(manifest['stores'])==12
    assert Settings(_env_file=None).store_index_canary_enabled is False
    with pytest.raises(HTTPException):canary.load_manifest(Settings(_env_file=None))


def test_worker_canary_has_no_schedule_and_is_disabled_by_default(monkeypatch):
    from app.tasks import store_index as tasks
    monkeypatch.setattr(tasks,'get_settings',lambda:SimpleNamespace(store_index_canary_enabled=False))
    assert tasks.verification_canary_wave.run()['status']=='disabled'
    assert all(entry.get('task')!='app.tasks.store_index.verification_canary_wave' for entry in tasks.celery.conf.beat_schedule.values())


def test_worker_stops_on_unknown_delivery(setup_canary, monkeypatch):
    from app.tasks import store_index as tasks
    from app.services import verification_delivery as delivery
    s=setup_canary;s.settings.api_internal_url='https://web.test';s.settings.internal_secret='offline'
    monkeypatch.setattr(tasks,'get_settings',lambda:s.settings)
    calls=[]
    async def send(url,payload,headers):
        calls.append(payload)
        return {'domain':payload['domain'],'outcome':'failed','reason':'web_unreachable'}
    monkeypatch.setattr(delivery,'deliver',send)
    result=tasks.verification_canary_wave.run()
    assert result['status']=='stopped' and len(calls)==1
