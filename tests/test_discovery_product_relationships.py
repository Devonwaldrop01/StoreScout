"""Independent product-relationship regressions; no benchmark merchant names."""
import asyncio
from datetime import datetime,timezone
from types import SimpleNamespace
import pytest
from app.services.product_intent import product_intent_check

@pytest.mark.parametrize('products',[
 ['Travel cosmetic bags'],['Foundation brushes'],['Makeup organizers'],
 ['Blush dresses'],['Rose blush cardigans'],['Cosmetic pouches'],
 ['Makeup tools'],['Concealer cases'],['Blush posters'],
])
def test_makeup_accessory_and_color_plurals_are_not_color_products(products):
    assert not product_intent_check({'product_titles':products},{'sells':'face makeup'})['supported']

@pytest.mark.parametrize('product',[
 'Tinted mineral sunscreen','BB cream','CC cream','Eyeshadow palette',
 'Cream blush refill','Matte lipstick',
])
def test_complete_color_products_still_match(product):
    assert product_intent_check({'product_titles':[product]},{'sells':'everyday cosmetics'})['supported']

@pytest.mark.parametrize('product',['Poultry bedding','Quilt laundry hamper','Mask sheets','Coop bedding'])
def test_other_uses_of_bedding_are_not_human_bed_linen(product):
    assert not product_intent_check({'product_titles':[product]},{'sells':'bed sheets'})['supported']

def test_mixed_catalog_preserves_real_product_not_accessory_theme():
    row={'product_titles':['Makeup bags','Liquid foundation']}
    assert product_intent_check(row,{'sells':'makeup'})['supported']

def test_detached_type_cannot_override_observed_product_titles():
    row={'product_types':['Bedding'],'product_titles':['Porcelain floor tiles','Tile adhesive']}
    result=product_intent_check(row,{'sells':'comforters and sheets'})
    assert not result['supported']
    assert result['reason']=='sampled_titles_missing_requested_product_family'

def test_legacy_type_only_fallback_and_unknown_intent_remain():
    assert product_intent_check({'product_types':['Bedding']},{'sells':'bed sheets'})['supported']
    assert product_intent_check({'product_titles':['Indigo vase']},{'sells':'ceramic vases'})['supported']
    assert product_intent_check({}, {'sells':'bed sheets'})['supported']

@pytest.mark.parametrize('titles,expected',[
 (['Adult body lotion','Toddler jacket'],False),
 (['Adult silk sleepwear','Newborn stroller'],False),
 (['Infant soothing lotion','Adult body lotion'],True),
 (['Toddler cotton sleepwear','Adult silk sleepwear'],True),
])
def test_audience_evidence_must_belong_to_requested_product(titles,expected):
    product='lotion' if any('lotion' in t for t in titles) else 'sleepwear'
    result=product_intent_check({'product_titles':titles,'description':'Gifts for new babies'},
                               {'sells':'baby '+product})
    assert result['supported']==expected
    if not expected: assert result['reason']=='requested_audience_not_linked_to_product'

def test_child_type_only_fallback_requires_joint_evidence():
    assert product_intent_check({'product_types':['Baby lotions']},{'sells':'baby skincare'})['supported']
    assert not product_intent_check({'product_types':['Skincare','Baby clothing']},{'sells':'baby skincare'})['supported']

def test_sunscreen_title_does_not_prove_absence_of_tint():
    # Sampling omits formulation attributes. Keep this conservative legacy
    # adjacency; rejecting all unknown formulations damaged known useful recall.
    assert product_intent_check({'product_titles':['Mineral sunscreen']},
                                {'sells':'tinted sunscreen'})['supported']

def test_primary_query_not_profile_keyword_union_drives_endpoint_intent(monkeypatch):
    import app.api.v1.competitors as route
    import app.services.store_index as index
    from app.core.config import get_settings
    now=datetime.now(timezone.utc).isoformat()
    class Query:
        def __init__(self,table):self.table=table
        def __getattr__(self,name):
            assert name not in ('insert','upsert','update','delete','rpc')
            return lambda *a,**k:self
        def execute(self):
            data=[]
            if self.table=='user_profiles':data={'tier':'pro'}
            if self.table=='business_profiles':data={'sells':'baby clothing','notes':'baby clothes and stationery'}
            if self.table=='shopify_store_index':
                data=[{'domain':'fictional-catalog.test','category':'Home & Living',
                 'category_confidence':90,'status':'verified','last_verified_at':now,
                 'verification_confidence':90,'verification_signals':['Product catalog accessible'],
                 'product_titles':['Cotton quilt','Toddler T-shirt'],'product_types':['Bedding']}]
            return SimpleNamespace(data=data)
    monkeypatch.setattr(route,'get_supabase',lambda:SimpleNamespace(table=lambda name:Query(name)))
    monkeypatch.setattr(route,'get_settings',lambda:get_settings().model_copy(update={'anthropic_api_key':''}))
    monkeypatch.setattr(index,'classify_store_v2',lambda **kw:{'category':'Home & Living','confidence':90})
    monkeypatch.setattr(index,'graph_neighbors',lambda *a,**kw:{})
    result=asyncio.run(route.discover_ai(route.DiscoverAIRequest(description='We sell cotton quilts'),user_id='offline'))
    match=result['data']['suggestions'][0]['relevance']['intent']
    assert match['requested_families']==['bedding']
    assert not match['child_audience_required']

