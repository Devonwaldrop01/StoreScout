from copy import deepcopy
from datetime import timedelta
import pytest
from app.services.product_intent import product_intent_check
from app.services import store_index as index
from app.services.discovery_quality import is_classification_usable
from test_verification_lifecycle import NOW, row, success, MemoryDB

@pytest.mark.parametrize('query,products,allowed',[
 ('mechanical keyboards',['Infant stroller low profile model'],False),
 ('mechanical keyboards',['Silicone keyboard cover'],False),
 ('mechanical keyboards',['Silicone keyboard cover','Wireless mechanical keyboard'],True),
 ('keyboard covers',['Silicone keyboard cover'],True),
 ('skin tint and complexion makeup',['Window tint film'],False),
 ('tinted moisturizer and everyday makeup',['Girls dress in cream and beauty rose'],False),
 ('skin tint',['Tinted mineral sunscreen'],True),
 ('bamboo pajamas and clothing for children',['Graphic tee','Kids bicycle','Skateboard'],False),
 ('bamboo pajamas and clothing for children',['Kids bamboo pajama set'],True),
 ('bamboo pajamas for children',['Women silk pajamas','Baby blue blouse'],False),
 ('fragrance-free baby skincare',['Adult facial lotion','Baby Blender makeup brush'],False),
 ('we sell clothing and bedding',['Denim jeans'],True),
 ('handmade ceramic planters',['Ceramic planter'],True),
 ('everyday makeup',['Matte lipstick','Pressed face powder'],True),
 ('clothing, home essentials, bags and jewelry',['Leather handbag'],True),
 ('freeze-dried dog treats',['Beef bully stick','Dog chew'],True),
 ('specialty coffee subscriptions',['Adjustable coffee table'],False),
 ('bedding and sheets',['Vinyl sticker sheet'],False),
 ('everyday makeup',['Blush pink dress','Cream blush wall art canvas'],False),
 ('everyday makeup',['Cream blush refill'],True),
])
def test_product_intent_not_incidental_words(query,products,allowed):
    assert product_intent_check({'product_titles':products},{'sells':query})['supported']==allowed

@pytest.mark.parametrize('types,titles,category',[
 (['Jeans','Shirts'],['Straight jeans','Cotton shirt'],'Fashion'),
 (['Stencils','Cardstock'],['Embossing folder','Craft stamp'],'Arts & Crafts'),
 (['Phone Case','Screen Protector'],['Headphone case'],'Tech Accessories'),
 ([],['Linen handkerchief','Cotton handkerchief','Silk handkerchief'],'Accessories'),
])
def test_observed_nouns_override_misleading_metadata(types,titles,category):
    result=index.classify_store_v2(description='Baby skin care and toys',product_types=types,
        product_titles=titles,allow_ai=False)
    assert result['category']==category and result['confidence']>=55

def legacy(**changes):
    return row(status='verified',category='Home & Living',subcategory='Bedding',category_confidence=90,
        knowledge_at=(NOW-timedelta(days=2)).isoformat(),last_verified_at=(NOW-timedelta(days=2)).isoformat(),
        verification_confidence=90,verification_signals=['Product catalog accessible'],**changes)

def test_first_signature_provisional_and_no_unbounded_extension():
    before=legacy(); fields={**index.lifecycle.successful_fields(success()['catalog_observation']),
        'product_titles':['Linen sheet','Cotton sheet'],'product_types':['Bedding']}
    transition=index.classification_transition(before,fields)
    assert transition['catalog_observation']['classification_state']=='provisional'
    current={**before,**fields,**transition}
    assert is_classification_usable(current,now=NOW)
    assert not is_classification_usable(current,now=NOW+timedelta(days=8))
    fresh=deepcopy(fields); fresh['catalog_observation']['observed_at']=(NOW+timedelta(days=3)).isoformat()
    renewed=index.classification_transition(current,fresh)
    assert renewed['catalog_observation']['classification_valid_until']==transition['catalog_observation']['classification_valid_until']

def test_fresh_contradiction_does_not_keep_legacy_claim():
    fields={**index.lifecycle.successful_fields(success()['catalog_observation']),
        'product_types':['Brakes','Motors'],'product_titles':['Replacement brake','Motor assembly']}
    transition=index.classification_transition(legacy(),fields)
    assert transition['catalog_observation']['classification_state']=='pending'
    assert transition['category'] is None

def test_low_replacement_retains_provisional_then_good_replacement_commits(monkeypatch):
    class Clock:
        @staticmethod
        def now(tz=None):return NOW
    monkeypatch.setattr(index,'datetime',Clock)
    import app.services.discovery_quality as quality
    monkeypatch.setattr(quality,'datetime',Clock)
    fields={**index.lifecycle.successful_fields(success()['catalog_observation']),'product_titles':['Linen sheet']}
    current={**legacy(),**fields,**index.classification_transition(legacy(),fields)}
    db=MemoryDB([current])
    result={'category':'Other','subcategory':'General','confidence':0,'evidence':[]}
    monkeypatch.setattr(index,'classify_store_ai',lambda **kw:result)
    monkeypatch.setattr('app.services.store_dna.generate_store_dna',lambda *a:None)
    index.run_knowledge(db,current)
    saved=db.rows[current['domain']]
    assert saved['category']=='Home & Living' and saved['category_confidence']==90
    assert saved['knowledge_at'] is None and saved['catalog_observation']['classification_retry_at']
    result.update(category='Home & Living',subcategory='Bedding',confidence=85)
    index.run_knowledge(db,deepcopy(saved))
    assert db.rows[current['domain']]['catalog_observation']['classification_state']=='current'
    assert db.rows[current['domain']]['knowledge_at']

def test_jsonb_any_term_request_is_containment_not_array_overlap():
    import httpx,json
    from supabase import create_client,ClientOptions
    requests=[]
    db=create_client('https://offline.test','test-key',options=ClientOptions(httpx_client=httpx.Client(
        transport=httpx.MockTransport(lambda req:(requests.append(req) or httpx.Response(200,json=[]))))))
    db.table('shopify_store_index').select('*').or_(','.join('dna_keywords.cs.'+json.dumps([t]) for t in ['keyboard','low-profile'])).execute()
    assert requests[0].url.params['or']=='(dna_keywords.cs.["keyboard"],dna_keywords.cs.["low-profile"])'

def test_endpoint_keyword_only_context_still_enforces_intent():
    assert not product_intent_check({'product_titles':['Stroller low-profile model']},
        {'dna_keywords':['mechanical','keyboards','models']})['supported']

def test_two_titles_remain_below_existing_sparse_evidence_floor():
    assert index.classify_store_v2(product_titles=['Linen handkerchief','Cotton handkerchief'],allow_ai=False)['confidence']==54

def test_query_only_classification_preserves_category_retrieval():
    r=index.classify_store_v2(description='We sell freeze-dried single-protein dog treats.',allow_ai=False)
    assert r['category']=='Pets' and r['confidence']>=45
