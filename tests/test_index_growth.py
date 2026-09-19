from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
import pytest
from app.services import store_index as index
from app.services.index_operations import activity_state, operational_evidence
from test_verification_lifecycle import MemoryDB, Query, row, success, NOW, PRODUCTS, frozen


class SelectedQuery(Query):
    """PostgREST projection is significant: do not return unselected CAS fields."""
    def select(self, columns, **kwargs):
        self.columns = columns
        return self
    def or_(self, *args): return self
    def order(self, *args, **kwargs): return self
    def limit(self, *args): return self
    def execute(self):
        result = super().execute()
        if self.payload is None and getattr(self, 'columns', '*') != '*':
            result.data = [{k.strip(): r.get(k.strip()) for k in self.columns.split(',')} for r in result.data]
        return result


class SelectedDB(MemoryDB):
    def table(self, name):
        assert name == 'shopify_store_index'
        return SelectedQuery(self)


@pytest.mark.parametrize('fallback', [False, True])
def test_real_classification_batch_persists_and_preserves_cas(monkeypatch, fallback):
    from app.tasks import store_index as tasks
    import app.services.runtime_config as runtime
    import app.services.store_dna as dna
    record = row(status='verified', knowledge_at=None, verification_token=None,
                 catalog_observation=success()['catalog_observation'], product_titles=['Linen sheet'] * 4)
    db = SelectedDB([record])
    monkeypatch.setattr(tasks, 'get_supabase', lambda: db)
    monkeypatch.setattr(runtime, 'get_config', lambda key, default=None: default)
    monkeypatch.setattr(index, 'classify_store_ai', lambda **k: None)
    monkeypatch.setattr(dna, 'generate_store_dna', lambda *a: None)
    original = SelectedQuery.select
    def select(self, columns, **kwargs):
        if fallback and 'product_titles' in columns:
            raise RuntimeError('missing product_titles')
        return original(self, columns, **kwargs)
    monkeypatch.setattr(SelectedQuery, 'select', select)
    result = tasks.stage_knowledge.run.__wrapped__(force=True)
    assert result['classified'] == 1  # before fix: every selected row was superseded
    stale = deepcopy(record)
    assert index.run_knowledge(db, stale)['status'] == 'superseded'


@pytest.mark.parametrize('status,body', [(429,''),(403,''),(200,'<title>Verifying your connection</title>'),(200,'<form action="/password">')])
def test_no_more_endpoints_after_homepage_protection(monkeypatch, status, body):
    calls = []
    class Client:
        def __enter__(self): return self
        def __exit__(self, *a): pass
    monkeypatch.setattr(index, '_make_client', Client)
    monkeypatch.setattr(index, '_enforce_domain_rate_limit', lambda *a: None)
    def get(client, url, **kw):
        calls.append(url)
        return SimpleNamespace(status_code=status, text=body, headers={})
    monkeypatch.setattr(index, '_get', get)
    result = index.index_store_pass('example.test')
    assert len(calls) == 1 and not result['monitorable']
    assert result['access_state'] in ('blocked','password_protected')


def test_retry_after_extends_cooldown_without_promoting_store(frozen, monkeypatch):
    from email.utils import format_datetime
    future = NOW+timedelta(days=4)
    response = SimpleNamespace(status_code=429, text='', headers={'retry-after':format_datetime(future)})
    outcome = index._protection_result(response, {}, NOW)
    monkeypatch.setattr(index, 'index_store_pass', lambda d: outcome)
    db=MemoryDB([row()])
    result=index.verify_and_store(db,'linen.test','test')
    assert result['reason']=='blocked'
    assert db.rows['linen.test']['next_verification_at']==future.isoformat()
    assert db.rows['linen.test']['status']=='failed'


def test_truthful_status_not_enable_flag():
    assert activity_state(True,False,None,NOW)=='inactive_or_unknown'
    assert activity_state(True,True,NOW.isoformat(),NOW)=='deployment_hold'
    assert activity_state(False,False,NOW.isoformat(),NOW)=='disabled'
    assert activity_state(True,False,(NOW-timedelta(days=1)).isoformat(),NOW)=='inactive_or_unknown'
    assert activity_state(True,False,NOW.isoformat(),NOW)=='recent_activity'
    assert activity_state(True,False,(NOW+timedelta(days=1)).isoformat(),NOW)=='inactive_or_unknown'


def test_missing_operational_data_is_unknown_not_zero():
    class MissingDB:
        def table(self,*args): raise RuntimeError('read unavailable')
    out=operational_evidence(MissingDB(),enabled=True,held=False,last_dispatch=None,now=NOW)
    assert out['throughput'] is None and out['last_successful_run'] is None
    assert out['live_worker_confirmed'] is False


@pytest.mark.parametrize('header,expected', [('345600', NOW+timedelta(days=4)), ('invalid', None), ('-2', None)])
def test_retry_after_seconds_and_malformed_values(header, expected):
    response=SimpleNamespace(status_code=429,text='',headers={'retry-after':header})
    result=index._protection_result(response,{},NOW)
    assert result['retry_after_at']==(expected.isoformat() if expected else None)


@pytest.mark.parametrize('protected_endpoint', ['cart.js','products.json','collections.json'])
def test_protection_stops_remaining_endpoints_without_discarding_prior_catalog(monkeypatch, protected_endpoint):
    calls=[]
    class Response:
        status_code=200
        headers={'content-type':'application/json'}
        text='Shopify cdn.shopify.com'
        def json(self): return {'products':PRODUCTS, 'items':[], 'collections':[]}
    class Client:
        def __enter__(self): return self
        def __exit__(self,*a): pass
    def get(client,url,**kwargs):
        calls.append(url)
        return SimpleNamespace(status_code=429,text='',headers={}) if protected_endpoint in url else Response()
    monkeypatch.setattr(index,'_make_client',Client)
    monkeypatch.setattr(index,'_enforce_domain_rate_limit',lambda *a:None)
    monkeypatch.setattr(index,'_get',get)
    result=index.index_store_pass('example.test')
    assert len(calls)=={'cart.js':2,'products.json':3,'collections.json':4}[protected_endpoint]
    assert result['monitorable']==(protected_endpoint=='collections.json')
