"""Bounded, opt-in public HTTP measurement. Only the local MemoryDB is writable.

Run with --fetch for the frozen 240-row health sample + indexed reference controls.
No acquisition, credentials, paid models, Supabase, Redis, or production endpoint.
Raw public response bodies are retained in ignored outputs for offline reproduction.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
from pathlib import Path
import socket
import sys
import threading
import time
from urllib.parse import urlsplit, urljoin

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
import app.core.config as config
settings = config.Settings(_env_file=None, anthropic_api_key='', supabase_url='',
    supabase_service_role_key='', redis_url='', shopify_index_min_confidence=60,
    shopify_index_category_min_confidence=55)
config.get_settings = lambda: settings
from app.services import store_index as index
from app.services.discovery_quality import is_recent_verified
from test_verification_lifecycle import MemoryDB
import httpx
import anthropic
class Forbidden(BaseException): pass
def deny(*a, **k): raise Forbidden('External database/model access forbidden')
anthropic.Anthropic = deny
import app.core.database as database
database.get_supabase = deny

SOURCE = ROOT/'docs/quality-audit/real-world/evidence'
OUT = ROOT/'outputs/controlled-validation'
OUT.mkdir(parents=True, exist_ok=True)
load = lambda p: json.loads(p.read_text(encoding='utf8'))
def save(p, data): p.write_text(json.dumps(data, indent=2), encoding='utf8')
rows = load(SOURCE/'index-snapshot.json')
bydomain = {r['domain']: r for r in rows}
sample = load(SOURCE/'health-sample.json')
controls = ['brooklinen.com', 'counterculturecoffee.com', 'iliabeauty.com',
    'birdiebean.com', 'littlesleepies.com', 'kytebaby.com', 'tubbytodd.com',
    'www.gossamergear.com', 'parachutehome.com']
domains = [r['domain'] for r in sample] + [d for d in controls if d not in {r['domain'] for r in sample}]
assert len(domains) == len(set(domains)) and all(d in bydomain for d in domains)
local = threading.local()
dns = {}; dns_lock = threading.Lock()

def allowed(url):
    u = urlsplit(url)
    if u.scheme not in ('https', 'http') or not u.hostname or u.username or u.password or u.port not in (None, 80, 443):
        raise ValueError('unsafe_url')
    host = u.hostname
    with dns_lock: addresses = dns.get(host)
    if addresses is None:
        addresses = {a[4][0] for a in socket.getaddrinfo(host, u.port or 443, type=socket.SOCK_STREAM)}
        with dns_lock: dns[host] = addresses
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
        raise ValueError('non_public_destination')

def measured_get(client, url, timeout=12):
    entry = {'url': url, 'hops': []}; local.requests.append(entry)
    started = time.perf_counter()
    try:
        for _ in range(6):
            allowed(url)
            hop = {'url': url}; entry['hops'].append(hop)
            with client.stream('GET', url, timeout=timeout) as response:
                hop['status'] = response.status_code
                if response.status_code in (301, 302, 303, 307, 308) and response.headers.get('location'):
                    url = urljoin(url, response.headers['location']); continue
                body = bytearray()
                for part in response.iter_bytes():
                    body.extend(part)
                    if len(body) > 8*1024*1024: raise ValueError('body_limit_8MiB')
                entry.update(status=response.status_code, final_url=url, bytes=len(body),
                    content_type=response.headers.get('content-type', ''))
                # No response cookies or cart tokens are retained. Products/home/collections only.
                if '/cart.js' not in entry['url']:
                    filename = hashlib.sha256(entry['url'].encode()).hexdigest()+'.body'
                    (OUT/'raw'/filename).write_bytes(body)
                    entry['body_file'] = filename
                    entry['sha256'] = hashlib.sha256(body).hexdigest()
                return httpx.Response(response.status_code, headers={'content-type':entry['content_type']},
                    content=bytes(body), request=httpx.Request('GET',url))
        raise ValueError('redirect_limit')
    except Exception as exc:
        entry['error'] = type(exc).__name__+': '+str(exc)[:240]
        raise
    finally: entry['seconds'] = time.perf_counter()-started

index._get = measured_get
index._make_client = lambda: httpx.Client(follow_redirects=False, headers=index._headers())
# One attempt per distinct sampled hostname, sequential requests within each host.
# Redis is intentionally replaced by the bounded local executor, never contacted.
index._enforce_domain_rate_limit = lambda domain: None

def verify(domain):
    path = OUT/'records'/(hashlib.sha256(domain.encode()).hexdigest()+'.json')
    if path.exists(): return load(path)
    local.requests = []
    db = MemoryDB([bydomain[domain]])
    start = time.perf_counter(); checked = datetime.now(timezone.utc).isoformat()
    result = index.verify_and_store(db, domain, 'controlled_raw_validation', force=True)
    row = db.rows[domain]
    record = {'domain':domain, 'checked_at':checked, 'before_status':bydomain[domain]['status'],
        'sample':domain in {r['domain'] for r in sample}, 'control':domain in controls,
        'result':result, 'verification_seconds':time.perf_counter()-start,
        'requests':local.requests, 'verified_row':deepcopy(row)}
    save(path, record)
    return record

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    for folder in ('raw','records'): (OUT/folder).mkdir(exist_ok=True)
    save(OUT/'sample-manifest.json', {'sample':sample, 'controls':controls,
        'domains':domains, 'transport':'httpx; production headers; no browser impersonation',
        'concurrency':3, 'batch':100, 'max_logical_requests':len(domains)*4,
        'credentials':'disabled; _env_file=None; no paid AI', 'source_sha256':hashlib.sha256((SOURCE/'index-snapshot.json').read_bytes()).hexdigest()})
    if not args.fetch: return
    records=[]; batches=[]
    for offset in range(0,len(domains),100):
        start=time.perf_counter()
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures=[pool.submit(verify,d) for d in domains[offset:offset+100]]
            for future in as_completed(futures):
                r=future.result(); records.append(r)
                print(json.dumps({'completed':len(records),'domain':r['domain'],'outcome':r['result']['outcome'],'state':r['verified_row'].get('verification_state')}),flush=True)
        batches.append({'stores':len(futures),'seconds':time.perf_counter()-start})
        save(OUT/'batch-timing.json',batches)
    # Classify sequentially as the existing worker does, with paid AI disabled.
    db=MemoryDB(rows)
    for r in records:
        domain=r['domain']; db.rows[domain]=deepcopy(r['verified_row'])
        if r['result']['outcome']=='verified':
            start=time.perf_counter()
            try: r['classification']=index.run_knowledge(db,deepcopy(db.rows[domain]))
            except Exception as exc: r['classification']={'error':type(exc).__name__+': '+str(exc)}
            r['classification_seconds']=time.perf_counter()-start
            old=bydomain[domain]; obs=old.get('catalog_observation') or {}
            r['prior_signature']=bool(obs.get('signature'))
            r['prior_classification']=bool(old.get('category') or old.get('knowledge_at'))
            r['classification_invalidated']=r['prior_classification'] and r['verified_row'].get('knowledge_at') is None and r['verified_row'].get('category') is None
        r['after_row']=deepcopy(db.rows[domain])
    now=datetime.now(timezone.utc)
    save(OUT/'outcomes.json',records)
    save(OUT/'index-after.json',list(db.rows.values()))
    save(OUT/'run-metadata.json', {'finished_at':now.isoformat(),'batches':batches,
        'before_usable':sum(is_recent_verified(r,now=now) for r in rows),
        'after_usable':sum(is_recent_verified(r,now=now) for r in db.rows.values()),
        'before_classified_usable':sum(is_recent_verified(r,now=now) and (r.get('category_confidence') is None or r['category_confidence']>=55) for r in rows),
        'after_classified_usable':sum(is_recent_verified(r,now=now) and (r.get('category_confidence') is None or r['category_confidence']>=55) for r in db.rows.values())})
    print('COMPLETE',len(records),flush=True)

if __name__=='__main__': main()
