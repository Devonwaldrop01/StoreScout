from copy import deepcopy
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from index_v2.identity import canonical,prepare,validate,digest
from index_v2.store import Store,LostLease
from index_v2.compute import classify,verified_row,retry_time
from index_v2.worker import process_job,execute_child,assert_isolated_env,child_environment,ChildFailed
from app.services.verification_lifecycle import successful_catalog

NOW=datetime.now(timezone.utc)


def manifest(domains=('example.com',),**kwargs):
    m=prepare([{'domain':d,'source':'legacy','id':str(i)} for i,d in enumerate(domains)],
        batch_size=len(domains),expires_at=(NOW+timedelta(days=7)).isoformat(),source_sha256='a'*64)
    m.update(kwargs);return m


@pytest.fixture
def store(tmp_path):
    path=tmp_path/'v2.sqlite';Store.initialize(path)
    clock=[NOW.timestamp()]
    db=Store(path,clock=lambda:clock[0]);db.test_clock=clock
    yield db
    db.close()


def catalog(domain='example.com'):
    products=[{'id':1,'handle':'linen','title':'Linen Sheet','product_type':'Bedding','variants':[{'id':2,'price':'50'}]}]
    result={'confidence':90,'monitorable':True,'reachable':True,'signals':['Shopify CDN detected'],
        'catalog_observation':successful_catalog(products,NOW,'index_v2'),
        'profile':{'product_count':1,'product_types':['Bedding'],'product_titles':['Linen sheet','Cotton bedding'],'brand_name':'Home','meta_description':'Bedding'}}
    return verified_row(domain,result)


def executor(payload,renew,stop):
    renew()
    if payload['stage']=='verify': return {'state':'verified_shopify','row':catalog(payload['canonical']),'requests':[]}
    return classify(payload['row'])


@pytest.mark.parametrize('host',['WWW.Example.com','https://www.example.com/path','example.com.','https://EXAMPLE.com'])
def test_canonical_before_queue(host): assert canonical(host)=='example.com'


@pytest.mark.parametrize('host',['https://user:pass@example.com','127.0.0.1','http://example.com:123','a..com','file:///etc/passwd'])
def test_bad_identity_rejected(host):
    with pytest.raises(ValueError): canonical(host)


def test_exact_legacy_head_failure_cannot_repeat(store):
    domains=[f'www.store{i}.com' for i in range(100)]+[f'store{i}.com' for i in range(100)]
    m=manifest(domains);key=store.seed(m)
    assert len(m['entries'])==100
    assert store.seed(m)==key
    assert store.db.execute('SELECT count(*) FROM jobs_v2').fetchone()[0]==100
    assert store.db.execute('SELECT count(*) FROM provenance_v2').fetchone()[0]==200
    for _ in range(100):
        job=store.claim(key);assert job and not job['canonical'].startswith('www.')
        process_job(store,job,executor);store.test_clock[0]+=11
    store.seed(m)
    assert store.summary()['eligible']==100 and store.summary()['attempts']==100
    assert store.claim(key) is None


def test_explicit_conflicting_shop_evidence_is_quarantined():
    with pytest.raises(ValueError,match='Conflicting'):
        prepare([{'domain':'www.example.com','distinct_storefront_evidence':{'shop_id':'different'}}],
            batch_size=1,expires_at=NOW.isoformat(),source_sha256='a'*64)


def test_second_owner_and_stale_completion_refused(store):
    key=store.seed(manifest());job=store.claim(key)
    assert store.claim(key) is None
    store.test_clock[0]+=181
    with pytest.raises(LostLease): store.renew(job)
    with pytest.raises(LostLease): store.complete(job,reason='ambiguous')
    assert store.claim(key) is None
    assert store.db.execute('SELECT outcome FROM store_verification_v2').fetchone()[0]=='interrupted_unknown'
    store.test_clock[0]+=3601
    replacement=store.claim(key);assert replacement['owner']!=job['owner']
    with pytest.raises(LostLease): store.complete(job,reason='ambiguous')


def test_two_connections_cannot_overlap(store):
    key=store.seed(manifest(('a.com','b.com')))
    def claim(_):
        db=Store(store.path)
        try: return db.claim(key)
        finally: db.close()
    with ThreadPoolExecutor(2) as pool: jobs=list(pool.map(claim,range(2)))
    assert sum(j is not None for j in jobs)==1


def test_verification_checkpoint_survives_restart_without_refetch(store):
    key=store.seed(manifest());job=store.claim(key)
    store.transition(job,'verifying');store.verified(job,catalog(),{'state':'verified_shopify'})
    store.transition(job,'classifying');store.test_clock[0]+=181
    db=Store(store.path,clock=store.clock)
    try:
        resumed=db.claim(key);assert resumed['state']=='verified'
        seen=[]
        def classify_only(payload,*args):
            seen.append(payload['stage']);assert payload['stage']=='classify'
            return classify(payload['row'])
        process_job(db,resumed,classify_only)
        assert seen==['classify'] and db.summary()['attempts']==1
        assert db.summary()['classification_saved']==1 and db.summary()['eligible']==1
    finally: db.close()


def test_completion_is_idempotent_and_claim_required(store):
    key=store.seed(manifest());job=store.claim(key)
    with pytest.raises(ValueError): store.complete(job,row=catalog(),eligible=True)
    store.transition(job,'verifying');store.verified(job,catalog(),{})
    store.transition(job,'classifying');result=classify(catalog())
    assert store.complete(job,**result) is True
    assert store.complete(job,**result) is False
    with pytest.raises(LostLease): store.complete(job,reason='different')


def test_budget_expiry_and_resume_import_do_not_reset_limits(store):
    key=store.seed(manifest(('a.com','b.com'),attempt_cap=1,request_cap=8))
    job=store.claim(key);store.transition(job,'verifying')
    store.complete(job,reason='blocked',retry_at=store.clock()+86400)
    store.test_clock[0]+=86401
    assert store.claim(key) is None
    assert store.summary()['reserved_requests']==8
    assert store.summary()['attempts']==1


def test_future_expiry_and_mismatched_manifest_rejected(store):
    m=manifest();m['expires_at']=(NOW-timedelta(seconds=1)).isoformat()
    assert store.claim(store.seed(m)) is None
    m=manifest();m['entries'][0]['canonical']='www.example.com'
    with pytest.raises(ValueError): store.seed(m)


def test_low_confidence_saved_without_manufacturing_eligibility(store):
    key=store.seed(manifest());job=store.claim(key)
    row=catalog();row.update(product_types=[],product_titles=[],brand_name='',description='',homepage_message='')
    def weak(payload,*args): return {'state':'verified_shopify','row':row,'requests':[]} if payload['stage']=='verify' else classify(payload['row'])
    process_job(store,job,weak)
    assert store.summary()['classification_saved']==1 and store.summary()['eligible']==0
    assert store.db.execute('SELECT confidence,exclusion FROM store_classification_v2').fetchone()[:]==(0,'classification_below_55')


def test_deadline_failure_pauses_and_never_reports_success(store):
    key=store.seed(manifest());job=store.claim(key)
    def timeout(*args): raise ChildFailed('child_timeout')
    with pytest.raises(ChildFailed): process_job(store,job,timeout)
    assert store.db.execute('SELECT stopped_reason FROM batches').fetchone()[0]=='child_timeout'
    assert store.claim(key) is None and store.summary()['eligible']==0


def test_bad_result_pauses(store):
    key=store.seed(manifest());job=store.claim(key)
    def bad(*args): return {'state':'verified_shopify','row':catalog('other.com')}
    with pytest.raises(ChildFailed): process_job(store,job,bad)
    assert store.summary()['eligible']==0


def test_credential_isolation_and_paid_disabled(monkeypatch):
    with pytest.raises(ValueError): assert_isolated_env({'REDIS_URL':'not-exposed'})
    assert_isolated_env({})
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY','not-exposed')
    assert 'SUPABASE_SERVICE_ROLE_KEY' not in child_environment()
    assert child_environment()['STORE_INDEX_DEPLOYMENT_HOLD']=='true'
    import app.services.store_index as legacy
    monkeypatch.setattr(legacy,'classify_store_ai',lambda **k:pytest.fail('Paid classification'))
    import app.services.store_dna as dna
    monkeypatch.setattr(dna,'generate_store_dna',lambda *a:pytest.fail('Paid DNA'))
    assert classify(catalog())['eligible']


def test_real_classification_child_no_application_lifecycle_or_writes():
    calls=[]
    result=execute_child({'stage':'classify','row':catalog()},lambda:calls.append('renew'),lambda:False)
    assert result['eligible'] and calls==['renew']


def test_expected_supervisor_identity_is_not_inherited(monkeypatch):
    import os
    monkeypatch.setenv('INDEX_V2_SUPERVISOR_PID','incorrect')
    assert child_environment()['INDEX_V2_SUPERVISOR_PID']==str(os.getpid())


def test_real_classification_persists_and_reopens(store):
    key=store.seed(manifest());job=store.claim(key)
    store.transition(job,'verifying');store.verified(job,catalog(),{})
    store.test_clock[0]+=181
    job=store.claim(key)
    process_job(store,job)
    reopened=Store(store.path,clock=store.clock)
    try:
        assert reopened.summary()['eligible']==1
        assert reopened.summary()['classification_saved']==1
        assert reopened.rows(eligible_only=True)[0]['category_confidence']==90
        assert reopened.claim(key) is None
    finally: reopened.close()


def test_retry_after_preserves_policy():
    job={'canonical':'example.com','attempts':1}
    assert retry_time(job,'blocked',(NOW+timedelta(days=4)).isoformat(),NOW)==(NOW+timedelta(days=4)).timestamp()


def test_export_is_readonly_and_deduplicates(store,tmp_path):
    key=store.seed(manifest());process_job(store,store.claim(key),executor)
    legacy=tmp_path/'legacy.json';legacy.write_text(json.dumps([catalog('www.example.com')]))
    original=legacy.read_bytes()
    from index_v2.experiment import export
    sets=export(store,tmp_path/'experiment',legacy,now=NOW+timedelta(seconds=5))
    assert len(sets['combined'])==1 and legacy.read_bytes()==original
    assert store.summary()['eligible']==1
    backup=tmp_path/'backup.sqlite';store.backup(backup)
    db=Store(backup)
    try: assert db.summary()==store.summary()
    finally: db.close()


def test_new_batch_cannot_reset_existing_ownership(store):
    key=store.seed(manifest());job=store.claim(key)
    second=manifest(target_eligible=500);store.seed(second)
    assert store.db.execute('SELECT owner FROM jobs_v2').fetchone()[0]==job['owner']


def test_nonpublic_dns_and_outside_alias_redirect_are_rejected(monkeypatch):
    from index_v2.transport import Transport
    import socket
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(0,0,0,'',('127.0.0.1',443))])
    transport=Transport('example.com')
    with pytest.raises(ValueError,match='Nonpublic'): transport.get(None,'https://example.com/')
    with pytest.raises(ValueError,match='Unapproved'): Transport('example.com').get(None,'https://other.com/')


def test_export_respects_withdrawn_eligibility(store,tmp_path):
    key=store.seed(manifest());process_job(store,store.claim(key),executor)
    store.db.execute("UPDATE store_index_v2 SET eligible=0,exclusion='reverification_pending'")
    from index_v2.experiment import export
    assert len(store.rows())==1
    assert export(store,tmp_path/'withdrawn',now=NOW)['v2']==[]


def test_transport_tls_pinning_and_protection_stops(monkeypatch):
    from index_v2.transport import Transport
    from curl_cffi import CurlOpt
    from types import SimpleNamespace
    import socket,curl_cffi.requests
    calls=[]
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(0,0,0,'',('8.8.8.8',443))])
    class Session:
        def __init__(self,**kwargs):
            assert kwargs['verify'] is True and kwargs['trust_env'] is False
            assert kwargs['curl_options'][CurlOpt.RESOLVE]==['example.com:443:8.8.8.8']
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def get(self,url,**kwargs):
            assert kwargs['allow_redirects'] is False and kwargs['verify'] is True
            assert kwargs['discard_cookies'] is True
            kwargs['content_callback'](b'Too many requests')
            calls.append(url)
            return SimpleNamespace(status_code=429,headers={'retry-after':'600'},text='Too many requests')
    monkeypatch.setattr(curl_cffi.requests,'Session',Session)
    transport=Transport('example.com')
    assert transport.get(None,'https://example.com/').status_code==429
    with pytest.raises(RuntimeError,match='stopped'): transport.get(None,'https://example.com/products.json')
    assert len(calls)==1 and transport.stop_state=='blocked'


def test_redirect_loop_stops_at_wire_budget(monkeypatch):
    from index_v2.transport import Transport
    from types import SimpleNamespace
    import socket,curl_cffi.requests
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(0,0,0,'',('8.8.8.8',443))])
    monkeypatch.setattr('index_v2.transport.time.sleep',lambda _:None)
    class Session:
        def __init__(self,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def get(self,url,**kwargs):
            return SimpleNamespace(status_code=302,headers={'location':'/loop'},text='')
    monkeypatch.setattr(curl_cffi.requests,'Session',Session)
    transport=Transport('example.com')
    with pytest.raises(TimeoutError,match='budget'): transport.get(None,'https://example.com/')
    assert len(transport.requests)==8


def test_oversized_child_input_fails_before_launch(monkeypatch):
    monkeypatch.setattr('index_v2.worker.subprocess.Popen',lambda *a,**k:pytest.fail('Must not launch'))
    with pytest.raises(ChildFailed,match='input'): execute_child({'data':'x'*(2*1024*1024)},lambda:None,lambda:False)


def test_child_stopped_before_dispatch_leaves_no_process():
    with pytest.raises(ChildFailed,match='shutdown'):
        execute_child({'stage':'classify','row':catalog()},lambda:None,lambda:True)


def test_every_catalog_endpoint_uses_only_injected_transport(monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace
    import app.services.store_index as legacy
    calls=[]
    monkeypatch.setattr(legacy,'_get',lambda *a,**k:pytest.fail('Legacy transport bypass'))
    monkeypatch.setattr(legacy,'_enforce_domain_rate_limit',lambda *a:pytest.fail('Legacy Redis'))
    monkeypatch.setenv('STORE_INDEX_DEPLOYMENT_HOLD','true')
    def get(client,url,**kwargs):
        calls.append(url)
        data={'token':'public-cart-marker','currency':'USD'} if '/cart.js' in url else {
            'products':[{'id':1,'handle':'linen','title':'Linen sheet','product_type':'Bedding','variants':[{'id':1,'price':'40'}]}]
        } if '/products.json' in url else {'collections':[]}
        return SimpleNamespace(status_code=200,headers={'content-type':'application/json'},
            text='<title>Bedding Store</title>cdn.shopify.com Shopify.theme',json=lambda:data)
    result=legacy.probe_store_catalog('example.com',make_client=lambda:nullcontext(None),get_response=get,pace=lambda *a:None)
    assert result['monitorable'] and result['confidence']==100
    assert len(calls)==4 and '/products.json' in calls[2] and '/collections.json' in calls[3]
    row=verified_row('example.com',result)
    assert row['currency']=='USD' and 'contact_email' not in row


def test_aggregate_metrics_does_not_print_catalog_or_domain(store):
    key=store.seed(manifest());process_job(store,store.claim(key),executor)
    report=store.metrics()
    assert report['verification_outcomes']=={'verified':1}
    assert report['classification_saved']==1 and report['classification_pass_rate']==1
    assert report['verified_to_eligible_yield']==1 and 'example.com' not in json.dumps(report)


def test_switching_manifest_preserves_global_start_spacing(store):
    first=store.seed(manifest(('a.com',)));process_job(store,store.claim(first),executor)
    second=store.seed(manifest(('b.com',)))
    assert store.claim(second) is None
    store.test_clock[0]+=10
    assert store.claim(second)['canonical']=='b.com'
