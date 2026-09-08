"""Regression tests run with in-memory records and recorded/fake HTTP only."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from app.services import verification_lifecycle as policy
from app.services import store_index as index
from app.services.discovery_quality import is_recent_verified

NOW = datetime(2026, 9, 5, 21, tzinfo=timezone.utc)
PRODUCTS = [{"id": 1, "handle": "linen", "title": "Linen Sheet", "product_type": "Bedding",
             "variants": [{"id": 2, "price": "50"}]}]


class MemoryDB:
    def __init__(self, rows):
        self.rows = {r["domain"]: deepcopy(r) for r in rows}
    def table(self, name):
        assert name == "shopify_store_index"
        return Query(self)


class Query:
    def __init__(self, db):
        self.db, self.filters, self.payload, self.single = db, [], None, False
    def select(self, *_): return self
    def maybe_single(self): self.single = True; return self
    def eq(self, key, value):
        self.filters.append(lambda r: ((r.get('catalog_observation') or {}).get('signature') if key=='catalog_observation->>signature' else r.get(key)) == value)
        return self
    def is_(self, key, value): assert value == "null"; return self.eq(key, None)
    def gt(self, key, value):
        self.filters.append(lambda r: r.get(key) is not None and r[key] > value)
        return self
    def upsert(self, payload, *, on_conflict, ignore_duplicates):
        assert on_conflict == "domain" and ignore_duplicates
        self.inserted = payload["domain"] not in self.db.rows
        if self.inserted:
            self.db.rows[payload["domain"]] = deepcopy(payload)
        self.filters.append(lambda r: self.inserted and r["domain"] == payload["domain"])
        return self
    def update(self, payload): self.payload = payload; return self
    def insert(self, payload):
        self.db.rows[payload["domain"]] = deepcopy(payload)
        return self
    def execute(self):
        rows = [r for r in self.db.rows.values() if all(f(r) for f in self.filters)]
        if self.payload is not None:
            for row in rows: row.update(deepcopy(self.payload))
        return SimpleNamespace(data=deepcopy(rows[0] if rows and self.single else None if self.single else rows))


@pytest.fixture
def frozen(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None): return NOW
    monkeypatch.setattr(index, "datetime", Clock)
    monkeypatch.setattr("app.core.config.get_settings", lambda: SimpleNamespace(shopify_index_min_confidence=60))


def row(**extra):
    return {"domain": "linen.test", "status": "discovered", "created_at": (NOW-timedelta(days=70)).isoformat(),
            "updated_at": (NOW-timedelta(days=5)).isoformat(), **extra}


def success(products=None):
    obs = policy.successful_catalog(products or PRODUCTS, NOW, "index_probe")
    return {"reachable": True, "monitorable": True, "confidence": 80, "signals": ["Shopify CDN detected"],
            "profile": {"product_count": 1, "product_titles": ["Linen Sheet"]}, "catalog_observation": obs}


def test_expired_owner_cannot_commit_even_before_replacement_claim(frozen):
    db = MemoryDB([row(verification_token="old", next_verification_at=(NOW-timedelta(seconds=1)).isoformat())])
    assert not index._finish_verification(db, "linen.test", "old", {"status": "verified"})
    assert db.rows["linen.test"]["status"] == "discovered"


def test_concurrent_verifier_does_not_fetch_claimed_domain(frozen, monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    db = MemoryDB([row()])
    entered, finish = threading.Event(), threading.Event()
    calls = []
    def fetch(domain):
        calls.append(domain)
        entered.set()
        assert finish.wait(3)
        return success()
    monkeypatch.setattr(index, "index_store_pass", fetch)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(index.verify_and_store, db, "linen.test", "test")
        try:
            assert entered.wait(3)
            second = pool.submit(index.verify_and_store, db, "linen.test", "test", force=True).result(timeout=3)
            assert second["reason"] == "not_due_or_claimed"
            assert calls == ["linen.test"]
        finally:
            finish.set()
        assert first.result(timeout=3)["outcome"] == "verified"


def test_stale_upsert_cannot_overwrite_a_new_claim(frozen, monkeypatch):
    db = MemoryDB([row()])
    original_update = Query.update
    def race(self, payload):
        db.rows["linen.test"].update(verification_token="new-owner", updated_at=NOW.isoformat())
        return original_update(self, payload)
    monkeypatch.setattr(Query, "update", race)
    observation = policy.successful_catalog(PRODUCTS, NOW, "tracked_scan")
    assert index.upsert_index_row(db, "linen.test", policy.successful_fields(observation)) == "skipped"
    assert db.rows["linen.test"]["verification_token"] == "new-owner"
    assert db.rows["linen.test"]["status"] == "discovered"


def test_www_candidate_seed_preserves_canonical_claim(frozen, monkeypatch):
    db = MemoryDB([row(verification_token="current", next_verification_at=(NOW+timedelta(minutes=4)).isoformat())])
    monkeypatch.setattr(index, "index_store_pass", lambda d: pytest.fail("already leased"))
    assert index.verify_and_store(db, "www.linen.test", "test")["outcome"] == "skipped"
    assert len(db.rows) == 1 and db.rows["linen.test"]["verification_token"] == "current"


def test_missing_migration_refuses_verification_before_catalog_access(frozen, monkeypatch):
    db = MemoryDB([row()])
    def missing(self, payload):
        raise RuntimeError("column verification_token does not exist")
    monkeypatch.setattr(Query, "update", missing)
    monkeypatch.setattr(index, "index_store_pass", lambda d: pytest.fail("schema not ready"))
    with pytest.raises(RuntimeError, match="verification_token"):
        index.verify_and_store(db, "linen.test", "test")


@pytest.mark.parametrize("source", ["tracked_scan", "index_probe"])
def test_successful_catalog_parity(source):
    fields = policy.successful_fields(policy.successful_catalog(PRODUCTS, NOW, source))
    assert is_recent_verified(fields, now=NOW)
    assert not is_recent_verified(fields, now=NOW+timedelta(days=61))
    assert not is_recent_verified(fields, now=NOW-timedelta(seconds=1))
    fields["verification_state"] = "blocked"
    assert not is_recent_verified(fields, now=NOW)


@pytest.mark.parametrize("products", [[], {}, [{"id": 1, "handle": "x", "variants": []}],
                                      [{"id": 1, "handle": "x", "variants": ["bad"]}],
                                      [{"id": 1, "handle": "x", "variants": [{}]}]])
def test_malformed_catalog_cannot_promote(products):
    with pytest.raises(ValueError): policy.successful_catalog(products, NOW, "tracked_scan")


def test_legacy_markers_and_attempt_time_never_make_success():
    legacy = row(status="verified", verification_confidence=100, last_verified_at=NOW.isoformat(),
                 verification_signals=["Actively scanned by StoreScout"])
    assert not is_recent_verified(legacy, now=NOW)
    legacy.update(policy.successful_fields(policy.successful_catalog(PRODUCTS, NOW-timedelta(days=61), "tracked_scan")))
    legacy["last_verified_at"] = NOW.isoformat()
    assert not is_recent_verified(legacy, now=NOW)


@pytest.mark.parametrize("state", sorted(policy.STATES - {"verified_shopify"}))
def test_failure_preserves_success_and_schedules_retry(state, frozen, monkeypatch):
    old = policy.successful_fields(policy.successful_catalog(PRODUCTS, NOW-timedelta(days=54), "tracked_scan"))
    db = MemoryDB([row(**old, knowledge_at="old-knowledge")])
    monkeypatch.setattr(index, "index_store_pass", lambda d: {"access_state": state, "reachable": state != "temporarily_unreachable",
        "signals": ["Shopify CDN detected"] if state == "probable_shopify" else []})
    result = index.verify_and_store(db, "linen.test", "test")
    actual = db.rows["linen.test"]
    assert result["outcome"] == ("rejected" if state in policy.TERMINAL else "failed")
    assert actual["catalog_observation"] == old["catalog_observation"]
    assert actual["last_verified_at"] == old["last_verified_at"]
    assert actual["knowledge_at"] == "old-knowledge"
    assert policy.timestamp(actual["next_verification_at"]) > NOW
    assert not is_recent_verified(actual, now=NOW)


def test_duplicate_delivery_and_racing_tracked_success(frozen, monkeypatch):
    db = MemoryDB([row()]); calls=[]
    def probe(domain): calls.append(domain); return success()
    monkeypatch.setattr(index, "index_store_pass", probe)
    assert index.verify_and_store(db, "linen.test", "test")["outcome"] == "verified"
    assert index.verify_and_store(db, "linen.test", "test")["outcome"] == "skipped"
    assert len(calls) == 1
    db = MemoryDB([row()])
    def race(domain):
        db.rows[domain].update(policy.successful_fields(policy.successful_catalog(PRODUCTS, NOW, "tracked_scan")))
        return {"reachable": False}
    monkeypatch.setattr(index, "index_store_pass", race)
    assert index.verify_and_store(db, "linen.test", "test")["outcome"] == "skipped"
    assert db.rows["linen.test"]["status"] == "verified"


def test_claim_is_exclusive_and_recovers_after_lease(frozen):
    db = MemoryDB([row()])
    first = index._claim_verification(db, "linen.test", "test", None)
    assert first and not index._claim_verification(db, "linen.test", "test", None)
    db.rows["linen.test"]["next_verification_at"] = (NOW-timedelta(seconds=1)).isoformat()
    second = index._claim_verification(db, "linen.test", "test", None)
    assert second and second[1] != first[1]
    assert not index._finish_verification(db, "linen.test", first[1], {"status": "failed"})


def test_manual_reverify_bypasses_freshness_but_not_active_claim(frozen):
    fields=policy.successful_fields(policy.successful_catalog(PRODUCTS,NOW,'tracked_scan'))
    db=MemoryDB([row(**fields)])
    assert not index._claim_verification(db,'linen.test','test',None)
    assert index._claim_verification(db,'linen.test','test',None,force=True)
    assert not index._claim_verification(db,'linen.test','test',None,force=True)


def test_stale_knowledge_cannot_overwrite_new_catalog(frozen,monkeypatch):
    fields=policy.successful_fields(policy.successful_catalog(PRODUCTS,NOW,'tracked_scan'))
    old=row(**fields)
    db=MemoryDB([old]); db.rows['linen.test']['catalog_observation']['signature']='new-signature'
    monkeypatch.setattr(index,'classify_store_ai',lambda **kw:{'category':'Home','subcategory':'Bedding','confidence':80})
    monkeypatch.setattr('app.services.store_dna.generate_store_dna',lambda *a,**kw:None)
    assert index.run_knowledge(db,old)['status']=='superseded'
    assert 'knowledge_at' not in db.rows['linen.test']


def test_knowledge_updates_exact_hostname_when_signature_matches(frozen,monkeypatch):
    fields=policy.successful_fields(policy.successful_catalog(PRODUCTS,NOW,'tracked_scan'))
    original=row(domain='www.linen.test',**fields)
    db=MemoryDB([original,row()])
    monkeypatch.setattr(index,'classify_store_ai',lambda **kw:{'category':'Home','subcategory':'Bedding','confidence':80})
    monkeypatch.setattr('app.services.store_dna.generate_store_dna',lambda *a,**kw:None)
    assert index.run_knowledge(db,original)['confidence']==80
    assert db.rows['www.linen.test']['category_confidence']==80
    assert 'category_confidence' not in db.rows['linen.test']


def test_renewal_preserves_unchanged_knowledge_and_invalidates_changed(frozen, monkeypatch):
    old = policy.successful_fields(policy.successful_catalog(PRODUCTS, NOW-timedelta(days=54), "index_probe"))
    for changed in [False, True]:
        db = MemoryDB([row(**old, knowledge_at="classification-date")])
        new = deepcopy(PRODUCTS)
        if changed: new[0]["title"] = "Acrylic Hobby Sheets"
        monkeypatch.setattr(index, "index_store_pass", lambda d: success(new))
        out = index.verify_and_store(db, "linen.test", "test")
        assert out["reverified"] is True
        assert db.rows["linen.test"]["knowledge_at"] == (None if changed else "classification-date")
        if changed: assert db.rows["linen.test"]["category_confidence"] == 0


def test_existing_www_row_is_processed_without_alias_merge(frozen, monkeypatch):
    db = MemoryDB([row(domain="www.linen.test"), row(domain="linen.test")])
    calls=[]
    monkeypatch.setattr(index, "index_store_pass", lambda d: calls.append(d) or success())
    assert index.verify_and_store(db,"www.linen.test","test")["outcome"] == "verified"
    assert calls == ["www.linen.test"]
    assert db.rows["linen.test"]["status"] == "discovered"


def test_missing_lifecycle_schema_fails_before_network(frozen, monkeypatch):
    db=MemoryDB([row()])
    original=Query.update
    def missing(self,payload):
        if "verification_token" in payload: raise RuntimeError('column verification_token does not exist')
        return original(self,payload)
    monkeypatch.setattr(Query,"update",missing)
    monkeypatch.setattr(index,"index_store_pass",lambda d: pytest.fail('must not probe without a durable claim'))
    with pytest.raises(RuntimeError,match='verification_token'):
        index.verify_and_store(db,'linen.test','test')


def test_tracked_scan_does_not_age_unchanged_knowledge(frozen):
    observation=policy.successful_catalog(PRODUCTS,NOW,'tracked_scan')
    old=policy.successful_fields(observation)
    db=MemoryDB([row(**old,knowledge_at='original',category_confidence=85)])
    index.upsert_index_row(db,'linen.test',{**policy.successful_fields(observation),'knowledge_at':None,'category_confidence':0})
    assert db.rows['linen.test']['knowledge_at']=='original'
    assert db.rows['linen.test']['category_confidence']==85


def test_real_catalog_probe_promotes_but_marker_only_never_does(frozen,monkeypatch):
    class Client:
        def __enter__(self): return self
        def __exit__(self,*a): pass
    monkeypatch.setattr(index,'_make_client',Client)
    monkeypatch.setattr(index,'_enforce_domain_rate_limit',lambda *a:None)
    for products in [PRODUCTS,[]]:
        def get(c,u,**kw):
            return SimpleNamespace(status_code=200,text='cdn.shopify.com Shopify.theme',
                headers={'content-type':'application/json'}, json=lambda:{'products':products,'collections':[]})
        monkeypatch.setattr(index,'_get',get)
        db=MemoryDB([row()])
        result=index.verify_and_store(db,'linen.test','test')
        assert result['outcome']==('verified' if products else 'failed')
        assert is_recent_verified(db.rows['linen.test'],now=NOW)==bool(products)


def test_ui_candidate_upsert_does_not_overwrite_existing_records():
    # Validate the real PostgREST request, including ignore-conflicts semantics.
    import httpx
    from supabase import create_client, ClientOptions
    captured=[]
    def handler(request):
        captured.append(request)
        return httpx.Response(201,json=[])
    db=create_client('https://offline.test','local-test-key', options=ClientOptions(httpx_client=httpx.Client(transport=httpx.MockTransport(handler))))
    db.table('shopify_store_index').upsert([{'domain':'linen.test','status':'candidate'}],on_conflict='domain',ignore_duplicates=True).execute()
    assert 'resolution=ignore-duplicates' in captured[0].headers['prefer']


def test_retry_backoff_bounded_and_due_lanes_do_not_starve():
    rows = [row(domain=f"{s}.test", status=s) for s in ["discovered", "candidate", "failed", "verified"]]
    selected = [policy.plan_verification(rows, NOW+timedelta(minutes=15*i), 1)[0]["status"] for i in range(4)]
    assert set(selected) == {"discovered", "candidate", "failed", "verified"}
    assert len(policy.plan_verification(rows+rows, NOW, 200)) == 4
    current = row()
    last=0
    for _ in range(15):
        current.update(policy.retry_fields(current, "temporarily_unreachable", NOW))
        hours = (policy.timestamp(current["next_verification_at"])-NOW).total_seconds()/3600
        assert last <= hours <= 168.167
        last=hours
    assert not policy.plan_verification([current], NOW, 100)


@pytest.mark.parametrize("status,body,state", [(402,"","storefront_unavailable"), (403,"","blocked"),
    (429,"","blocked"), (502,"","temporarily_unreachable"), (200,'<form action="/password">',"password_protected"),
    (200,'<script src="/cdn-cgi/challenge-platform/">',"blocked")])
def test_http_outcomes_are_not_non_shopify(status, body, state, frozen, monkeypatch):
    class Client:
        def __enter__(self): return self
        def __exit__(self, *a): pass
    monkeypatch.setattr(index, "_make_client", Client)
    monkeypatch.setattr(index, "_enforce_domain_rate_limit", lambda *a: None)
    monkeypatch.setattr(index, "_get", lambda c,u,**kw: SimpleNamespace(status_code=status,
        text=body, headers={"content-type":"text/html"}, json=lambda: {}))
    result=index.index_store_pass("linen.test")
    assert policy.classify_probe(result) == state
    assert not result["monitorable"]
