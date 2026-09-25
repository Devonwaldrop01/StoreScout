"""Offline characterization of the approved release, not new runtime behavior."""
from datetime import datetime,timezone,timedelta
import json
from types import SimpleNamespace
import pytest
from test_index_v2 import store,manifest,executor
from index_v2.compute import retry_time
from index_v2.store import Store
from index_v2.worker import process_job
from app.services.store_index import _protection_result,probe_store_catalog

NOW=datetime(2026,9,25,13,0,tzinfo=timezone.utc)

def response(status,headers=None,body='',data=None):
    return SimpleNamespace(status_code=status,headers=headers or {},text=body,json=lambda:data)

@pytest.mark.parametrize('status',[401,403,429])
def test_access_labels_are_retryable_not_terminal(status):
    r=_protection_result(response(status),{},NOW)
    assert r['access_state']=='blocked'
    due=retry_time({'canonical':'fixture.example','attempts':1},r['access_state'],now=NOW)
    assert NOW.timestamp()+86400<=due<=NOW.timestamp()+87000

@pytest.mark.parametrize('header',['172800','Sun, 27 Sep 2026 13:00:00 GMT'])
def test_long_retry_after_is_not_clipped(header):
    r=_protection_result(response(429,{'retry-after':header}),{},NOW)
    assert retry_time({'canonical':'fixture.example','attempts':1},'blocked',r['retry_after_at'],NOW)==(NOW+timedelta(days=2)).timestamp()

def test_short_retry_after_does_not_shorten_daily_cooldown():
    r=_protection_result(response(429,{'retry-after':'60'}),{},NOW)
    assert retry_time({'canonical':'fixture.example','attempts':1},'blocked',r['retry_after_at'],NOW)>=NOW.timestamp()+86400

def test_challenge_without_429_is_blocked():
    assert _protection_result(response(200,{'cf-mitigated':'challenge'}),{},NOW)['access_state']=='blocked'

def limited(payload,renew,stop):
    assert payload['stage']=='verify'
    return {'state':'blocked','retry_after_at':None,'requests':[{'status':429,'path':'/'}]}

def test_isolated_limit_then_healthy_preserves_reservation_and_retry_on_restart(store):
    key=store.seed(manifest(('a.example','b.example')))
    job=store.claim(key);process_job(store,job,limited)
    before=dict(store.db.execute("select * from jobs_v2 where canonical='a.example'").fetchone())
    assert before['state']=='failed' and before['next_due']>store.clock()
    store.test_clock[0]+=11
    process_job(store,store.claim(key),executor)
    assert store.summary()['eligible']==1 and store.summary()['reserved_requests']==16
    assert store.summary()['stopped_batches']=={}
    reopened=Store(store.path,clock=store.clock)
    try:
        assert dict(reopened.db.execute("select * from jobs_v2 where canonical='a.example'").fetchone())==before
        assert reopened.claim(key) is None
    finally:reopened.close()

def test_unrelated_429_cluster_pauses_and_restart_cannot_claim(store):
    key=store.seed(manifest(tuple(f's{i:02}.example' for i in range(22))))
    for i in range(20):
        process_job(store,store.claim(key),limited if i>=13 else executor);store.test_clock[0]+=11
    assert store.summary()['stopped_batches'][key]=='access_failure_rate'
    assert store.summary()['reserved_requests']==160
    reopened=Store(store.path,clock=store.clock)
    try:assert reopened.claim(key) is None
    finally:reopened.close()

def test_repeated_one_merchant_keeps_three_attempt_cap_and_all_reservations(store,monkeypatch):
    import index_v2.compute as compute
    original=compute.retry_time
    monkeypatch.setattr(compute,'retry_time',lambda job,state,advised=None:original(job,state,advised,datetime.fromtimestamp(store.clock(),timezone.utc)))
    key=store.seed(manifest(('one.example',)))
    for attempt in range(1,4):
        process_job(store,store.claim(key),limited)
        due=store.db.execute('select next_due from jobs_v2').fetchone()[0]
        assert due>=store.clock()+86400*2**(attempt-1)
        store.test_clock[0]=due+1
    assert store.claim(key) is None
    assert store.summary()['attempts']==3 and store.summary()['reserved_requests']==24

def test_second_transport_call_after_429_never_sends_network(monkeypatch):
    from index_v2.transport import Transport
    t=Transport('fixture.example');t.stop_state='blocked'
    def forbidden(*args,**kwargs):raise AssertionError('Network attempted after protection')
    monkeypatch.setattr('socket.getaddrinfo',forbidden)
    with pytest.raises(RuntimeError,match='Previous protection'):
        t.get(None,'https://fixture.example/products.json?limit=250')
    assert t.requests==[]

def test_optional_collections_429_drops_retry_after_from_probe():
    """Confirmed existing gap: keep readable catalog, but lose optional protection signal."""
    product={'id':1,'handle':'sample','title':'Sample','variants':[{'id':2,'price':'10'}]}
    calls=[]
    class Client:
        def __enter__(self):return self
        def __exit__(self,*args):pass
    def get(client,url,timeout=12):
        calls.append(url)
        if '/cart.js' in url:return response(200,{'content-type':'application/json'},data={'token':'fixture','currency':'USD'})
        if '/products.json' in url:return response(200,{'content-type':'application/json'},data={'products':[product]})
        if '/collections.json' in url:return response(429,{'retry-after':'172800'})
        return response(200,body='<html>cdn.shopify.com Shopify.theme shop_pay</html>')
    probe=probe_store_catalog('fixture.example',make_client=Client,get_response=get,pace=lambda *a:None)
    assert probe['monitorable'] and probe['access_state'] is None
    assert probe.get('retry_after_at') is None and len(calls)==4

def test_verified_wire_429_is_not_counted_by_existing_gate(store):
    """The gate counts outcomes, not response events, including optional 429s."""
    def successful_with_optional_429(payload,renew,stop):
        result=executor(payload,renew,stop)
        if payload['stage']=='verify':result['requests']=[{'status':429,'path':'/collections.json'}]
        return result
    key=store.seed(manifest(tuple(f's{i:02}.example' for i in range(20))))
    for _ in range(20):
        process_job(store,store.claim(key),successful_with_optional_429);store.test_clock[0]+=11
    assert store.summary()['stopped_batches']=={}
    assert store.summary()['reserved_requests']==160
