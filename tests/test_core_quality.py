from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
import pytest
from app.services.discovery_quality import relevance, is_recent_verified
from app.services.action_candidates import build_candidates, prioritise_candidates, pct
from app.services.playbook_intelligence import _normalize_pct

NOW = datetime(2026,9,5,15,tzinfo=timezone.utc)
STAMP = NOW.isoformat()

def row(**snap):
    return {'competitor_id':'c1','hostname':'review.test','snap':{'scanned_at':STAMP,'product_count':10,**snap}}

def test_eight_niches_direct_substitutes_beat_platform_confidence():
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).parent/'evaluations'))
    from discovery_cases import cases
    for name,user,pool in cases():
        ranked = sorted(pool,key=lambda r:relevance(r,user)['score'],reverse=True)
        assert [r['label'] for r in ranked[:2]] == [3,3], name


def test_observed_products_beat_misleading_dna():
    user = {'dna_keywords':['reusable','cloth','diapers'], 'category':'Kids & Baby'}
    actual = {'product_titles':['reusable cloth diapers'],'category':'Fashion'}
    misleading = {'product_titles':['wooden bookshelf'],'dna_keywords':['reusable','cloth','diapers'],'category':'Kids & Baby'}
    assert relevance(actual,user)['score'] > relevance(misleading,user)['score']
    assert not relevance(misleading,user)['matched_terms']


def test_unknown_metadata_is_not_product_evidence():
    r = relevance({'category':'Footwear'},{'category':'Footwear','dna_keywords':['running','shoe']})
    assert not r['matched_terms'] and not r['product_evidence']


@pytest.mark.parametrize('age,status,signals,expected',[(0,'verified',['Product catalog accessible'],True),(61,'verified',['Product catalog accessible'],False),(1,'verified',['Storefront responds (bot-protected)'],False),(1,'rejected',['Product catalog accessible'],False)])
def test_platform_cache_requires_fresh_readable_catalog(age,status,signals,expected):
    r={'status':status,'last_verified_at':(NOW-timedelta(days=age)).isoformat(),'verification_confidence':100,'verification_signals':signals}
    assert is_recent_verified(r,now=NOW) is expected


@pytest.mark.parametrize('value,expected',[(50,.5),(1,.01),(.5,.005)])
def test_percent_units_are_explicit(value,expected):
    assert _normalize_pct(value)==expected
    p=build_candidates([row(promo_rate=value)],now=NOW)[0]
    assert f'{value:g}%' in p['what_happened']
    assert '5000%' not in p['what_happened']


def test_invalid_percent_is_unknown():
    assert pct(float('nan')) is None
    assert pct(110) is None
    assert pct(None) is None


def test_no_integrations_has_action_risk_evidence_and_missing_data():
    p=build_candidates([row(promo_rate=50)],business={'sells':'ceramic tableware'},now=NOW)[0]
    assert 'ceramic tableware' in p['why_it_matters']
    assert p['execution_paths'] and p['avoid'] and p['additional_data'] and p['fact_ids']
    assert p['decision']=='Investigate' and p['confidence']=='estimated'
    assert 'partial or unknown' in p['evidence'][1]


def test_stale_snapshot_cannot_produce_current_promotion_advice():
    p=build_candidates([row(promo_rate=90,scanned_at='2026-01-01T00:00:00+00:00')],now=NOW)[0]
    assert p['fact_confidence']=='stale' and 'Refresh' in p['title']
    assert '90%' not in p['what_happened']


def test_actual_event_contract_and_own_catalog_overlap_prioritise_review():
    event={'id':'ev1','competitor_id':'c1','change_type':'price_change','product_title':'Linen travel shirt','detected_at':STAMP,'old_value':{'price':50},'new_value':{'price':40}}
    own={'scanned_at':STAMP,'snapshot_data':{'_product_index':{'linen':{'title':'Linen travel shirt'}}}}
    p=build_candidates([row()],[event],own_snap=own,now=NOW)[0]
    assert p['fact_ids']==['change:ev1'] and p['priority_label']=='high'
    assert 'not confirmed equivalents' in p['why_it_matters']
    assert 'variant change' in p['avoid']


def test_ai_cannot_fabricate_facts_actions_ids_or_raise_priority():
    p=build_candidates([row()],now=NOW)
    got=prioritise_candidates(p,[{'candidate_id':p[0]['id'],'what_happened':'Revenue fell 99%','priority':'high'}, {'candidate_id':'invented'}])
    assert got==p


def test_successful_ai_task_persists_result_usage_and_grounded_candidates(monkeypatch):
    import app.tasks.playbook_ai as task
    import app.services.action_candidates as engine
    candidates=build_candidates([row(promo_rate=50)],now=NOW)
    inserted=[]
    class Query:
        def __init__(self,table): self.table=table;self.payload=None
        def __getattr__(self,name): return lambda *a,**k:self
        def insert(self,payload): self.payload=payload;return self
        def execute(self):
            if self.payload: inserted.append(self.payload)
            data=[{'id':'c1','hostname':'review.test','is_my_store':False}] if self.table=='competitors' else []
            return SimpleNamespace(data=data)
    monkeypatch.setattr(task,'get_supabase',lambda:SimpleNamespace(table=lambda name:Query(name)))
    monkeypatch.setattr(task._redis_lib,'from_url',lambda *a,**k:SimpleNamespace(exists=lambda key:False,setex=lambda *a:None))
    monkeypatch.setattr(engine,'load_context',lambda *a:candidates)
    monkeypatch.setattr(task,'call_claude',lambda *a,**k:SimpleNamespace(ok=True,text='{"recommendations": [{"candidate_id": "invented"}]}',truncated=False,input_tokens=100,output_tokens=20))
    monkeypatch.setattr(task,'_aijob_clear',lambda *a:None)
    assert task.generate_ai_playbook.run('user1')['status']=='ok'
    assert inserted[0]['input_tokens']==100 and inserted[0]['output_tokens']==20
    import json
    assert json.loads(inserted[0]['summary_text'])['plays']==candidates


def test_index_lookup_failure_does_not_attempt_insert():
    from app.services.store_index import upsert_index_row
    class Query:
        def __getattr__(self,name):
            assert name!='insert'
            return lambda *a,**k:self
        def execute(self): raise RuntimeError('database unavailable')
    with pytest.raises(RuntimeError):
        upsert_index_row(SimpleNamespace(table=lambda _:Query()),'real.test',{'status':'candidate'})


def test_missing_availability_does_not_create_stockout():
    from app.services.normalize import normalize_product
    from app.tasks.detect_changes import _detect
    before=normalize_product({'handle':'shirt','variants':[{'price':'20','available':True}]},'https://review.test')
    after=normalize_product({'handle':'shirt','variants':[{'price':'20'}]},'https://review.test')
    assert after['available'] is None
    assert not _detect({'_product_index':{'shirt':before}}, {'_product_index':{'shirt':after}})


@pytest.mark.parametrize('catalog',[[],{},[{'title':'not a product'}]])
def test_index_does_not_verify_empty_or_malformed_catalog(monkeypatch,catalog):
    import app.services.store_index as idx
    class Client:
        def __enter__(self): return self
        def __exit__(self,*a): pass
    monkeypatch.setattr(idx,'_make_client',lambda:Client())
    def get(client,url,**kwargs):
        isproducts='products.json' in url
        return SimpleNamespace(status_code=200,headers={'content-type':'application/json' if isproducts else 'text/html'},text='cdn.shopify.com Shopify.theme shop-pay',url=url,json=lambda:{'products':catalog})
    monkeypatch.setattr(idx,'_get',get)
    # The rate limiter is best-effort; avoid Redis even for the local probe.
    import app.services.fetch as fetch
    monkeypatch.setattr(idx,'_enforce_domain_rate_limit',lambda *a:None)
    result=idx.index_store_pass('catalog.test')
    assert not result['monitorable']
    assert 'Product catalog accessible' not in result['signals']


def test_shopify_redaction_requires_configured_verification_secret(monkeypatch):
    import asyncio
    import app.api.v1.shopify_app as mod
    from fastapi import HTTPException
    monkeypatch.setattr(mod,'get_settings',lambda:SimpleNamespace(shopify_api_secret=''))
    with pytest.raises(HTTPException) as err:
        asyncio.run(mod.shop_redact(None))
    assert err.value.status_code==503


def test_hub_does_not_claim_full_intelligence_for_empty_account():
    from app.services.integration_catalog import build_hub
    hub=build_hub([])
    assert next(d for d in hub['intelligence'] if d['key']=='competitor')['pct']==0
    assert all(e['status']!='connected' for e in hub['integrations'])


def test_discovery_serves_index_without_anthropic_and_without_graph_writes(monkeypatch):
    import asyncio
    import app.api.v1.competitors as route
    import app.services.store_index as idx
    from app.core.config import get_settings
    settings=get_settings().model_copy(update={'anthropic_api_key':''})
    now=datetime.now(timezone.utc).isoformat()
    class Query:
        def __init__(self,table): self.table=table
        def __getattr__(self,name):
            assert name not in ('insert','upsert','update')
            return lambda *a,**k:self
        def execute(self):
            data=[]
            if self.table=='user_profiles': data={'tier':'pro'}
            if self.table=='business_profiles': data={'sells':'linen shirts','target_customer':'adult travellers','price_range':'mid'}
            if self.table=='shopify_store_index':
                data=[{'domain':'linen.test','category':'Fashion','category_confidence':90,'status':'verified','last_verified_at':now,'verification_confidence':70,'verification_signals':['Product catalog accessible'],'product_titles':['Linen travel shirts'],'product_types':['Shirts'],'target_customer':'adult travellers','pricing_tier':'mid-market'}]
            return SimpleNamespace(data=data)
    monkeypatch.setattr(route,'get_supabase',lambda:SimpleNamespace(table=lambda name:Query(name)))
    monkeypatch.setattr(route,'get_settings',lambda:settings)
    monkeypatch.setattr(idx,'classify_store_v2',lambda **k:{'category':'Fashion','confidence':90})
    monkeypatch.setattr(idx,'graph_neighbors',lambda *a,**k:{})
    result=asyncio.run(route.discover_ai(route.DiscoverAIRequest(description='linen travel shirts'),user_id='user1'))
    assert result['data']['suggestions'][0]['domain']=='linen.test'
    assert result['data']['suggestions'][0]['relevance']['product_evidence']


def test_single_homepage_keyword_cannot_be_high_confidence_classification():
    from app.services.store_index import classify_store_v2
    assert classify_store_v2(description='ceramic')['confidence'] < 55


def test_brand_decode_percent_prompt_uses_recorded_units(monkeypatch):
    import app.services.ai as ai
    from app.services.brand_decode import generate_brand_decode
    seen=[]
    def call(*args,**kwargs):
        seen.append(args[1]);return SimpleNamespace(ok=False)
    monkeypatch.setattr(ai,'call_claude',call)
    generate_brand_decode({'hostname':'review.test','promo_rate':50})
    assert '50% of catalog discounted' in seen[0] and '5000%' not in seen[0]


def test_removing_cheapest_variant_is_not_a_price_increase():
    from app.services.normalize import normalize_product
    from app.tasks.detect_changes import _detect
    old=normalize_product({'id':1,'handle':'shirt','variants':[{'id':10,'price':10,'available':True},{'id':11,'price':20,'available':True}]},'https://review.test')
    new=normalize_product({'id':1,'handle':'shirt','variants':[{'id':11,'price':20,'available':True}]},'https://review.test')
    assert not _detect({'_product_index':{'shirt':old}}, {'_product_index':{'shirt':new}})


def test_same_minimum_variant_repricing_is_still_detected():
    from app.tasks.detect_changes import _detect
    old={'_product_index':{'shirt':{'price_min':20,'price_min_variant_ids':['v1']}}}
    new={'_product_index':{'shirt':{'price_min':15,'price_min_variant_ids':['v1']}}}
    events=_detect(old,new)
    assert events[0]['change_type']=='price_change' and events[0]['delta_pct']==-25


def test_known_product_handle_rename_is_not_addition_and_removal():
    from app.tasks.detect_changes import _detect
    old={'catalog_complete':True,'_product_index':{'old-handle':{'id':1,'price_min':10}}}
    new={'catalog_complete':True,'_product_index':{'new-handle':{'id':1,'price_min':10}}}
    assert not _detect(old,new)


def test_confirmed_concurrent_index_insert_preserves_verified_row():
    from app.services.store_index import upsert_index_row
    reads=0
    class Query:
        def __init__(self): self.inserting=False
        def __getattr__(self,name): return lambda *a,**k:self
        def insert(self,payload): self.inserting=True;return self
        def update(self,payload): raise AssertionError('verified row must not be downgraded')
        def execute(self):
            nonlocal reads
            if self.inserting: raise RuntimeError('23505 duplicate domain')
            reads+=1
            return SimpleNamespace(data=None if reads==1 else {'id':'existing','status':'verified'})
    assert upsert_index_row(SimpleNamespace(table=lambda _:Query()),'shop.test',{'status':'candidate','category':'Fashion'})=='skipped'


@pytest.mark.parametrize('cached_user,cached_cid,stamp,accepted',[
    ('u','c1','2001-01-01T00:00:00+00:00',False),
    ('other','c1','current',False),
    ('u','deleted','current',False),
    ('u','c1','current',True),
])
def test_playbook_cache_checks_owner_competitor_and_fact_freshness(monkeypatch,cached_user,cached_cid,stamp,accepted):
    import json
    import app.api.v1.playbook as route
    import app.services.action_candidates as engine
    import app.services.ai_job as jobs
    if stamp=='current': stamp=datetime.now(timezone.utc).isoformat()
    class Query:
        def __init__(self,table): self.table=table
        def __getattr__(self,name): return lambda *a,**k:self
        def execute(self):
            data={'tier':'pro'} if self.table=='user_profiles' else [{'id':'c1','hostname':'real.test'}]
            if self.table=='ai_summaries':
                data={'summary_text':json.dumps({'user_id':cached_user,'engine_version':1,'plays':[{'id':'cached','competitor_id':cached_cid,'observed_at':stamp,'priority':10}]})}
            return SimpleNamespace(data=data)
    monkeypatch.setattr(route,'get_supabase',lambda:SimpleNamespace(table=lambda name:Query(name)))
    monkeypatch.setattr(jobs,'read_phase',lambda *a:('failed',0))
    monkeypatch.setattr(jobs,'decide_ai_action',lambda **k:('unavailable','none'))
    monkeypatch.setattr(engine,'load_context',lambda *a:[{'id':'fallback','priority':1}])
    result=route._build_playbook('u')
    assert result['ai_source'] is accepted
    assert result['plays'][0]['id']==('cached' if accepted else 'fallback')
