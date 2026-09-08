import asyncio
from types import SimpleNamespace
import pytest


def test_captured_gzip_response_is_not_decompressed_twice():
    import gzip,httpx
    from evaluations.access_response import decoded_response
    body=b'{"products":[]}'
    wire=httpx.Response(200,headers={'content-encoding':'gzip','content-type':'application/json'},content=gzip.compress(body))
    captured=decoded_response(wire.status_code,wire.headers,wire.content,'https://offline.test/products.json')
    assert captured.json()=={'products':[]}
    assert 'content-encoding' not in captured.headers


@pytest.mark.parametrize('provider', ['disabled','empty','authentication','rate_limit','failure','index_failure'])
def test_empty_discovery_is_valid_without_hiding_provider_failures(monkeypatch, provider):
    import httpx
    import anthropic
    import app.api.v1.competitors as route
    import app.services.store_index as index
    from app.core.config import Settings
    settings=Settings(_env_file=None,anthropic_api_key='' if provider in ('disabled','index_failure') else 'offline-test')
    class Query:
        def __init__(self,table): self.table=table
        def __getattr__(self,name):
            assert name not in ('insert','upsert','update')
            return lambda *a,**k:self
        def execute(self):
            if provider=='index_failure' and self.table=='shopify_store_index':
                raise RuntimeError('offline database unavailable')
            return SimpleNamespace(data={'tier':'pro'} if self.table=='user_profiles' else [])
    response=httpx.Response(401,request=httpx.Request('POST','https://offline.test'))
    def create(**kwargs):
        if provider=='authentication': raise anthropic.AuthenticationError('offline',response=response,body={})
        if provider=='rate_limit': raise anthropic.RateLimitError('offline',response=response,body={})
        if provider=='failure': raise RuntimeError('offline provider unavailable')
        assert provider=='empty'
        return SimpleNamespace(content=[SimpleNamespace(text='{"suggestions":[]}')])
    monkeypatch.setattr(anthropic,'Anthropic',lambda **kw:SimpleNamespace(messages=SimpleNamespace(create=create)))
    monkeypatch.setattr(route,'get_supabase',lambda:SimpleNamespace(table=lambda t:Query(t)))
    monkeypatch.setattr(route,'get_settings',lambda:settings)
    monkeypatch.setattr(index,'graph_neighbors',lambda *a,**kw:{})
    import app.tasks.store_index as tasks
    monkeypatch.setattr(tasks.generate_niche_candidates,'delay',lambda *a,**kw:pytest.fail('empty search must not start new acquisition'))
    call=route.discover_ai(route.DiscoverAIRequest(description='ultralight backpacking tents'),user_id='offline')
    if provider in ('disabled','empty'):
        result=asyncio.run(call)
        assert result['data']['suggestions']==[]
        assert result['data']['relevant_non_shopify']==[]
    else:
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as error: asyncio.run(call)
        assert error.value.status_code==({'rate_limit':429,'index_failure':503}.get(provider,500))
