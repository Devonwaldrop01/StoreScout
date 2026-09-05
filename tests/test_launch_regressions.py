"""Regression cases for customer-visible billing and catalog failures; no network."""
import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.services.normalize import normalize_product
from app.services.analyze import analyze_products
from app.services import fetch
from app.tasks.detect_changes import _detect
from app.api.v1 import webhooks, internal, billing


def product(variants, **kw):
    return normalize_product(dict(id=1, handle='example', title='Example', variants=variants, **kw), 'https://example.com')


def test_separate_variant_minima_never_invent_discount():
    p = product([{'price': '10'}, {'price': '100', 'compare_at_price': '100'}])
    assert p['discount_pct_min'] is None
    result = analyze_products([p])
    assert result['discounts']['discounted_pct'] == 0
    assert result['lists']['top_discounts'] == []


@pytest.mark.parametrize('bad', ['oops', 'NaN', 'Infinity', '-1', None])
def test_bad_price_does_not_crash_or_pollute_analysis(bad):
    p = product([{'price': bad}, {'price': '20', 'compare_at_price': '25'}])
    assert p['price_min'] == 20
    assert p['discount_pct_min'] == 20
    assert analyze_products([p])['discounts']['discounted_pct'] == 100


def test_free_variant_can_have_real_markdown():
    p = product([{'price': '0', 'compare_at_price': '10'}])
    assert p['discount_pct_min'] == 100


def test_missing_dates_do_not_crash_sort():
    a = product([{'price': '10'}])
    b = product([{'price': '20'}], created_at='2026-01-01T00:00:00Z', updated_at='2026-01-01T00:00:00Z')
    assert analyze_products([a, b])['catalog']['total_products'] == 2


def setup_fetch(monkeypatch, pages):
    client = MagicMock()
    client.__enter__.return_value = client
    client.get.side_effect = pages
    monkeypatch.setattr(fetch, '_USE_CURL_CFFI', True)
    monkeypatch.setattr(fetch, 'CurlSession', lambda **kw: client)
    monkeypatch.setattr(fetch, '_enforce_domain_rate_limit', lambda host: None)
    return client


def response(products=None, status=200):
    return SimpleNamespace(status_code=status, headers={'content-type':'application/json'},
                           url='https://example.com/products.json', text='{}',
                           json=lambda: {'products': products})


def test_later_page_failure_cannot_become_successful_partial_list(monkeypatch):
    setup_fetch(monkeypatch, [response([{'id':1}]), response(status=503)])
    with pytest.raises(fetch.CatalogFetchError):
        fetch.fetch_products_shopify('https://example.com')


def test_cap_reports_incomplete_and_exhaustion_reports_complete(monkeypatch):
    setup_fetch(monkeypatch, [response([{'id':1}])])
    capped = fetch.fetch_products_shopify('https://example.com', max_products=1)
    assert capped == [{'id':1}] and not capped.complete and capped.reason == 'product_limit'
    setup_fetch(monkeypatch, [response([{'id':1}]), response([])])
    full = fetch.fetch_products_shopify('https://example.com')
    assert full.complete and full.reason == 'exhausted'


def snapshot(products, complete=True):
    return {'_product_index': products, 'catalog_complete': complete,
            'catalog_truncated': not complete}


@pytest.mark.parametrize('old_complete,new_complete', [(False, True),(True,False),(False,False)])
def test_partial_snapshots_cannot_assert_catalog_changes(old_complete, new_complete):
    old = snapshot({'a':{'price_min':20}}, old_complete)
    new = snapshot({'b':{'price_min':10}}, new_complete)
    old['discounts'] = {'discounted_pct':0}
    new['discounts'] = {'discounted_pct':100}
    assert _detect(old,new) == []


def test_complete_snapshots_still_detect_removal_and_new_product():
    events = _detect(snapshot({'a':{}}), snapshot({'b':{}}))
    assert {e['change_type'] for e in events} == {'product_removed','new_product'}


def test_partial_snapshots_still_detect_observed_price_change():
    events = _detect(snapshot({'a':{'price_min':20}},False), snapshot({'a':{'price_min':10}},False))
    assert events[0]['change_type'] == 'price_change'


def test_legacy_top_lists_are_not_complete_catalogs():
    assert _detect({'lists':{'newest_products':[{'handle':'a'}]}}, {'lists':{}}) == []


@pytest.mark.parametrize('secret', ['', 'dev-internal-secret'])
def test_internal_auth_rejects_unconfigured_or_default_secret(monkeypatch,secret):
    monkeypatch.setattr(internal, 'get_settings', lambda: SimpleNamespace(internal_secret=secret))
    with pytest.raises(HTTPException) as err:
        internal._require_internal(secret)
    assert err.value.status_code == 403


def test_webhook_database_failure_is_retryable_and_then_succeeds(monkeypatch):
    app = FastAPI(); app.include_router(webhooks.router)
    monkeypatch.setattr(webhooks.stripe.Webhook, 'construct_event', lambda *a: {'type':'checkout.session.completed','data':{'object':{}}})
    monkeypatch.setattr(webhooks, 'get_supabase', lambda: object())
    handler = MagicMock(side_effect=[RuntimeError('private database detail'), None])
    monkeypatch.setattr(webhooks, '_handle_event', handler)
    client=TestClient(app)
    failed=client.post('/webhooks/stripe-subscriptions', content=b'{}')
    assert failed.status_code == 503 and 'private database detail' not in failed.text
    assert client.post('/webhooks/stripe-subscriptions',content=b'{}').json() == {'received':True}


def test_webhook_invalid_signature_rejected_before_db(monkeypatch):
    app=FastAPI(); app.include_router(webhooks.router)
    monkeypatch.setattr(webhooks.stripe.Webhook,'construct_event',MagicMock(side_effect=ValueError()))
    db=MagicMock();monkeypatch.setattr(webhooks,'get_supabase',db)
    assert TestClient(app).post('/webhooks/stripe-subscriptions',content=b'{}').status_code == 400
    db.assert_not_called()


def test_existing_subscription_cannot_start_another_checkout(monkeypatch):
    monkeypatch.setattr(billing,'get_settings',lambda:SimpleNamespace(stripe_secret_key='',stripe_pro_price_id='price_test'))
    monkeypatch.setattr(billing,'get_supabase',lambda:object())
    monkeypatch.setattr(billing,'_get_user_email',lambda *a:'test@example.com')
    monkeypatch.setattr(billing,'_get_or_create_stripe_customer',lambda *a:'cus_test')
    monkeypatch.setattr(billing.stripe.Subscription,'list',lambda **kw:{'data':[{'status':'active'}]})
    create=MagicMock();monkeypatch.setattr(billing.stripe.checkout.Session,'create',create)
    with pytest.raises(HTTPException) as err:
        billing.create_checkout(billing.CheckoutRequest(plan='pro'),'user')
    assert err.value.status_code == 409
    create.assert_not_called()


def test_scan_does_full_fetch_even_with_an_unchanged_first_product(monkeypatch):
    db=MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data={
        'store_url':'https://example.com','hostname':'example.com','user_profiles':{'tier':'pro'}}
    monkeypatch.setattr(internal,'_require_internal',lambda token:None)
    monkeypatch.setattr(internal,'get_supabase',lambda:db)
    monkeypatch.setattr(internal,'get_settings',lambda:SimpleNamespace(scan_max_products=1500))
    fetcher=MagicMock(side_effect=fetch.CatalogFetchError('offline failure'))
    monkeypatch.setattr(internal,'fetch_products_shopify',fetcher)
    result=internal.internal_scan('competitor','test')
    fetcher.assert_called_once_with('https://example.com',max_products=1500)
    assert result['status']=='error'


def test_public_report_uses_matching_snapshot_brief_only(monkeypatch):
    import json
    from app.api.v1 import reports
    db=MagicMock()
    snaps=MagicMock(); briefs=MagicMock()
    db.table.side_effect=lambda name: snaps if name=='scan_snapshots' else briefs
    snaps.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data={
        'id':'old','competitor_id':'c','scanned_at':'2026-01-01','snapshot_data':{}}
    result=briefs.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value
    result.data=[{'summary_text':json.dumps({'_snapshot_id':'new','cards':[]})},
                 {'summary_text':json.dumps({'cards':[{'body':'Unbound legacy brief'}]})}]
    monkeypatch.setattr(reports,'get_supabase',lambda:db)
    assert reports.get_public_report('old')['data']['ai_brief'] is None
    result.data.append({'summary_text':json.dumps({'_snapshot_id':'old','cards':[]})})
    assert reports.get_public_report('old')['data']['ai_brief']['_snapshot_id']=='old'
