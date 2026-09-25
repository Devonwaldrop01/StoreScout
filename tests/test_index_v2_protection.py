"""Synthetic fixtures only; no merchant requests or production credentials."""
from datetime import datetime,timezone
import io
import json
import sys
from types import SimpleNamespace
import pytest
from test_index_v2 import store,manifest,executor,catalog
from index_v2.store import Store
from index_v2.worker import process_job,ChildFailed
from index_v2.protection import observed,validated,journal
from index_v2.canary import arm,validate,load


def event(role='/collections.json',status=429):
    return observed(role,status,.05,100,{'access_state':'blocked','retry_after_at':'2030-01-01T00:00:00+00:00'})


def limited_success(payload,renew,stop):
    result=executor(payload,renew,stop)
    if payload['stage']=='verify': result['protection_events']=[event()]
    return result


def spec_for(store,key):
    from index_v2.identity import digest
    return {'batch':key,'domains':[e['canonical'] for e in store.manifest(key)['entries']][:10],
            'max_attempts':10,'max_reserved_requests':80,
            'baseline_attempts':{r['attempt_id']:digest(dict(r)) for r in store.db.execute('select * from store_verification_v2')}}


def setup_canary(store):
    key=store.seed(manifest(tuple(f'c{i:02}.example' for i in range(12))))
    store.pause(key,'access_failure_rate');spec=spec_for(store,key)
    assert arm(store,spec);assert not arm(store,spec)
    store.canary=spec
    return key,spec


@pytest.mark.parametrize('path,status',[('/',429),('/products.json',429),('/collections.json',429),('/',403),('/',200)])
def test_real_transport_and_child_path_protection(monkeypatch,tmp_path,path,status):
    import index_v2.child as child
    # Other backend tests import app.main; a real child starts a fresh interpreter.
    for name in ('app.main','app.tasks.celery_app','app.core.database'):
        monkeypatch.delitem(sys.modules,name,raising=False)
    calls=[]
    class Session:
        def __init__(self,**kwargs): pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def get(self,url,**kwargs):
            from urllib.parse import urlsplit
            role=urlsplit(url).path;calls.append(role)
            if role==path:
                headers={'retry-after':'172800','cf-mitigated':'challenge','set-cookie':'NEVER_SAVE_SECRET'}
                body=b'challenge';code=status
            else:
                headers={'content-type':'application/json'};code=200
                data={'token':'fixture','currency':'USD'} if role=='/cart.js' else {'products':[{'id':1,'handle':'sample','title':'Linen Sheet','variants':[{'id':2,'price':'10'}]}]}
                body=json.dumps(data).encode() if role!='/' else b'<html>cdn.shopify.com Shopify.theme shop_pay</html>'
            kwargs['content_callback'](body)
            return SimpleNamespace(status_code=code,headers=headers,text=body.decode(),json=lambda:json.loads(body))
    monkeypatch.setattr('curl_cffi.requests.Session',Session)
    monkeypatch.setattr('socket.getaddrinfo',lambda *a,**k:[(None,None,None,None,('8.8.8.8',443))])
    monkeypatch.setattr('time.sleep',lambda *a:None)
    monkeypatch.setattr(child,'limits',lambda:None)
    monkeypatch.setenv('INDEX_V2_PROTECTION_JOURNAL',str(tmp_path/'events.json'))
    monkeypatch.setattr(sys,'stdin',SimpleNamespace(buffer=io.BytesIO(json.dumps({'stage':'verify','canonical':'fixture.example','fetch_host':'fixture.example'}).encode())))
    output=io.StringIO();monkeypatch.setattr(sys,'stdout',output)
    finders=list(sys.meta_path)
    try:child.main()
    finally:sys.meta_path[:]=finders
    result=json.loads(output.getvalue())
    assert calls[-1]==path and calls.count(path)==1
    assert result['state']==('verified_shopify' if path=='/collections.json' else 'blocked')
    e=result['protection_events'][0]
    assert e['required']==(path!='/collections.json') and e['status']==status
    assert datetime.fromisoformat(result['retry_after_at'])>=datetime.fromisoformat(e['retry_after_at'])
    if path=='/collections.json': assert result['retry_after_at']==e['retry_after_at']
    assert datetime.fromisoformat(e['retry_after_at']).timestamp()>datetime.now(timezone.utc).timestamp()+172790
    assert json.loads((tmp_path/'events.json').read_text())==result['protection_events']
    assert 'NEVER_SAVE_SECRET' not in output.getvalue()


def test_success_with_protection_persists_and_restarts(store):
    key=store.seed(manifest());process_job(store,store.claim(key),limited_success)
    assert store.summary()['eligible']==1
    r=json.loads(store.db.execute('select result_json from store_verification_v2').fetchone()[0])
    assert r['protection_events'][0]['verification_succeeded'] is True
    assert r['protection_events'][0]['contributes_to_protection_gate'] is True
    reopened=Store(store.path)
    try:assert json.loads(reopened.db.execute('select result_json from store_verification_v2').fetchone()[0])==r
    finally:reopened.close()


@pytest.mark.parametrize('protected,paused',[(6,False),(7,True)])
def test_exact_30_percent_denominator_counts_attempt_once(store,protected,paused):
    key=store.seed(manifest(tuple(f's{i:02}.example' for i in range(20))))
    for i in range(20):
        process_job(store,store.claim(key),limited_success if i<protected else executor)
        store.test_clock[0]+=11
    assert bool(store.summary()['stopped_batches'])==paused
    assert store.summary()['eligible']==20


def test_canary_ten_domains_80_units_manifest_order_and_restart(store):
    key,spec=setup_canary(store);seen=[]
    for i in range(10):
        db=Store(store.path,clock=store.clock,canary=spec)
        try:
            job=db.claim(key);seen.append(job['canonical']);process_job(db,job,executor)
        finally:db.close()
        store.test_clock[0]+=11
    assert seen==spec['domains']
    assert store.claim(key) is None and store.claim(key) is None
    assert store.summary()['attempts']==10 and store.summary()['reserved_requests']==80
    assert store.summary()['stopped_batches'][key]=='access_failure_rate'
    assert store.db.execute("select count(*) from jobs_v2 where attempts=0").fetchone()[0]==2
    with pytest.raises(ValueError):validate(store,spec,arming=True)


def test_canary_unarmed_and_wrong_scope_fail_closed(store):
    key=store.seed(manifest(tuple(f'c{i:02}.example' for i in range(10))))
    store.pause(key,'access_failure_rate');store.canary=spec_for(store,key)
    assert store.claim(key) is None
    store.canary['max_attempts']=11
    with pytest.raises(ValueError):arm(store,store.canary)


def test_first_optional_protection_holds_valid_catalog_without_classifying(store):
    key,spec=setup_canary(store);job=store.claim(key);stages=[]
    def run(payload,renew,stop):
        stages.append(payload['stage']);return limited_success(payload,renew,stop)
    process_job(store,job,run)
    assert stages==['verify'] and store.summary()['classification_attempted']==0
    assert store.db.execute('select owner from jobs_v2 where canonical=?',(job['canonical'],)).fetchone()[0] is None
    assert store.db.execute('select state from jobs_v2 where canonical=?',(job['canonical'],)).fetchone()[0]=='verified'
    reopened=Store(store.path,clock=store.clock,canary=spec)
    try:assert reopened.claim(key) is None and reopened.canary_stopped()
    finally:reopened.close()


def test_journal_event_survives_timeout_and_reservations_not_refunded(store):
    key,spec=setup_canary(store);job=store.claim(key)
    def timeout(payload,renew,stop):
        renew.protection([event('/')])
        exc=ChildFailed('child_timeout');exc.termination_confirmed=True;raise exc
    process_job(store,job,timeout)
    row=store.db.execute('select * from store_verification_v2').fetchone()
    assert row['outcome']=='child_timeout' and row['reserved_requests']==8
    assert json.loads(row['result_json'])['protection_events'][0]['verification_succeeded'] is False
    assert store.claim(key) is None


def test_no_canary_retry_or_scope_escape(store):
    key,spec=setup_canary(store)
    def failed(*args):return {'state':'temporarily_unreachable','requests':[]}
    first=store.claim(key);process_job(store,first,failed)
    store.test_clock[0]+=11
    second=store.claim(key);assert second['canonical']==spec['domains'][1]
    assert second['canonical']!=first['canonical']


def test_frozen_spec_and_sensitive_metadata_rejected():
    spec=load();assert len(spec['domains'])==10 and len(spec['baseline_attempts'])==131
    with pytest.raises(ValueError):validated([dict(event(),headers={'authorization':'secret'})])
    with pytest.raises(ValueError):validated([dict(event(),seconds=float('nan'))])


@pytest.mark.skipif(sys.platform!='linux',reason='Real supervised Linux child/journal')
def test_supervisor_collects_journal_before_child_exit(store,monkeypatch):
    import index_v2.worker as worker
    real=worker.subprocess.Popen
    def launch(argv,**kwargs):
        code='from index_v2.child import limits; limits(); from index_v2.protection import journal; import json,sys,time; journal(json.loads(sys.stdin.read())); time.sleep(.4); sys.exit(7)'
        # Replace only the isolated test child's input/argv, retaining actual supervisor.
        kwargs['stdin']=None
        code=code.replace('json.loads(sys.stdin.read())',repr([event('/')]))
        return real([sys.executable,'-c',code],**kwargs)
    monkeypatch.setattr(worker.subprocess,'Popen',launch)
    key,spec=setup_canary(store);job=store.claim(key)
    with pytest.raises(ChildFailed,match='child_exit_7'):process_job(store,job,worker.execute_child)
    r=json.loads(store.db.execute('select result_json from store_verification_v2').fetchone()[0])
    assert r['protection_events'][0]['verification_succeeded'] is None
    assert store.canary_stopped() and store.summary()['reserved_requests']==8
