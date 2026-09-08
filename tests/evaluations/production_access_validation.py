"""Bounded public-read comparison. No production writes or paid classification.

Native curl-cffi deliberately disables Chrome impersonation: no challenge solving,
fingerprint switching, proxies or attempts after a protection response. This is
the closest non-bypass transport comparison, not exact deployed TLS parity.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json,random,sys,threading,time
from pathlib import Path
from urllib.parse import urljoin,urlsplit

sys.path.insert(0,str(Path(__file__).parent))
import controlled_catalog_validation as h
import httpx
from access_response import decoded_response, SAFE_HEADERS
from curl_cffi.requests import Session
from app.services.discovery_quality import is_classification_usable,is_recent_verified

OUT=h.ROOT/'outputs/production-access'
OUT.mkdir(parents=True,exist_ok=True)
for folder in ['raw','records']: (OUT/folder).mkdir(exist_ok=True)
local=threading.local()
save=lambda p,data:p.write_text(json.dumps(data,indent=2),encoding='utf8')
load=h.load
SEED=202609061101
NOW=datetime.now(timezone.utc)
prior=load(h.ROOT/'outputs/controlled-validation/outcomes.json')
excluded={r['domain'].removeprefix('www.') for r in prior}
baseline=load(h.ROOT/'outputs/bounded-cycle/index-after.json')
eligible=[r for r in baseline if r['domain'].removeprefix('www.') not in excluded
          and r.get('status') in {'candidate','discovered','failed','rejected','verified'}
          and h.index.lifecycle.due_at(r)<=NOW]

def manifest():
    target=OUT/'manifest.json'
    if target.exists():return load(target)
    rng=random.Random(SEED)
    strata=defaultdict(list)
    for r in eligible:strata[r['status']].append(r)
    # Proportionate allocation with at least two per existing lifecycle lane.
    allocations={s:max(2,round(96*len(rs)/len(eligible))) for s,rs in strata.items()}
    while sum(allocations.values())!=96:
        s=max(allocations,key=lambda s:allocations[s] if sum(allocations.values())>96 else len(strata[s])/allocations[s])
        allocations[s]+= -1 if sum(allocations.values())>96 else 1
    selected=[]
    for status,rs in sorted(strata.items()):
        sample=rng.sample(sorted(rs,key=lambda r:r['domain']),allocations[status])
        for i,r in enumerate(sample):
            selected.append({'domain':r['domain'],'status':status,'transport':'native_curl' if i%2 else 'httpx',
                'population':len(rs),'stratum_sample':len(sample)})
    rng.shuffle(selected)
    data={'seed':SEED,'created_at':NOW.isoformat(),'population':len(eligible),
          'strata':{s:len(rs) for s,rs in strata.items()},'sample':selected,
          'concurrency':3,'batch_limit':100,'chunks':15,'per_host_gap_seconds':1,
          'max_domains':96,'max_logical_endpoints_per_domain':4,'max_redirects':5,
          'no_impersonation':True,'no_proxy_rotation':True,'no_same_run_network_retries':True,
          'excluded_previous_domains':len(excluded),'headers':h.index._headers(),
          'limitation':'Windows/local egress, not Render web-service egress; native curl omits deployed impersonation.'}
    save(target,data);return data

class Client:
    def __enter__(self):
        self.inner=(Session(headers=h.index._headers(),impersonate=None,trust_env=True)
                    if local.transport=='native_curl' else httpx.Client(headers=h.index._headers(),follow_redirects=False))
        return self
    def __exit__(self,*a):self.inner.close()

def measured_get(client,url,timeout=12):
    if getattr(local,'protection',None) is not None:
        local.suppressed.append(url)
        return local.protection
    entry={'url':url,'hops':[]};local.requests.append(entry);started=time.perf_counter()
    try:
        for hop_number in range(6):
            h.allowed(url)
            host=urlsplit(url).hostname
            remaining=1-(time.monotonic()-local.last_sent.get(host,-10))
            if remaining>0:time.sleep(remaining)
            local.last_sent[host]=time.monotonic()
            hop={'url':url};entry['hops'].append(hop)
            save(OUT/'records'/(hashlib.sha256(local.domain.encode()).hexdigest()+'.inflight'),
                 {'domain':local.domain,'transport':local.transport,'started_at':datetime.now(timezone.utc).isoformat(),
                  'requests':local.requests})
            if local.transport=='native_curl':
                # Match production's synchronous get; streaming adapter stalled
                # on this Windows runtime. Never retry its unresolved domains.
                response=client.inner.get(url,timeout=timeout,allow_redirects=False)
                status=response.status_code;headers=dict(response.headers);body=response.content
                if len(body)>8*1024*1024:raise ValueError('body_limit')
            else:
                with client.inner.stream('GET',url,timeout=timeout) as response:
                    status=response.status_code;headers=dict(response.headers);body=bytearray()
                    for part in response.iter_bytes():
                        body.extend(part)
                        if len(body)>8*1024*1024:raise ValueError('body_limit')
            headers={k.lower():v for k,v in headers.items()}
            hop.update(status=status,headers={k:headers[k] for k in SAFE_HEADERS if k in headers})
            lower=bytes(body[:400000]).lower()
            protected=(status in (401,403,429,430) or b'cf-chl-' in lower or b'challenge-platform' in lower
                       or b'verifying your connection' in lower or b'shopify-section-main-password' in lower)
            if status in (301,302,303,307,308) and headers.get('location') and not protected:
                if hop_number==5:raise ValueError('redirect_limit')
                url=urljoin(url,headers['location']);continue
            entry.update(status=status,bytes=len(body),final_url=url,headers=hop['headers'],protected=protected)
            if '/cart.js' not in entry['url']:
                filename=hashlib.sha256(entry['url'].encode()).hexdigest()+'.body'
                (OUT/'raw'/filename).write_bytes(body);entry['body_file']=filename
                entry['sha256']=hashlib.sha256(body).hexdigest()
            # Both clients already decoded the wire representation. Forwarding
            # Content-Encoding here would decompress the decoded body twice.
            result=decoded_response(status,headers,body,url)
            if protected:local.protection=result
            return result
    except Exception as exc:
        entry['error']=type(exc).__name__+': '+str(exc)[:200];raise
    finally:entry['seconds']=time.perf_counter()-started

def verify(item):
    domain=item['domain'];path=OUT/'records'/(hashlib.sha256(domain.encode()).hexdigest()+'.json')
    if path.exists():return load(path)
    local.domain=domain;local.transport=item['transport'];local.requests=[];local.suppressed=[];local.last_sent={};local.protection=None
    row=next(r for r in baseline if r['domain']==domain);db=h.MemoryDB([deepcopy(row)])
    started=time.perf_counter()
    result=h.index.verify_and_store(db,domain,'bounded_access_validation',force=False)
    record={**item,'result':result,'requests':local.requests,'suppressed_after_protection':local.suppressed,
            'seconds':time.perf_counter()-started,'verified_row':deepcopy(db.rows[domain])}
    # Scheduling repeat is a local call only; the claim must prevent any HTTP.
    count=len(local.requests)
    record['immediate_repeat']=h.index.verify_and_store(db,domain,'bounded_access_validation',force=False)
    assert len(local.requests)==count and record['immediate_repeat']['outcome']=='skipped'
    save(path,record)
    return record

def main():
    args=argparse.ArgumentParser();args.add_argument('--fetch',action='store_true');args.add_argument('--finalize',action='store_true');options=args.parse_args()
    plan=manifest()
    save(OUT/'previous-cooldowns.json',{'at':NOW.isoformat(),
        'due':sum(h.index.lifecycle.due_at(r['after_row'])<=NOW for r in prior),
        'not_due':sum(h.index.lifecycle.due_at(r['after_row'])>NOW for r in prior),
        'network_retries_performed':0})
    if not options.fetch and not options.finalize:print(json.dumps({k:v for k,v in plan.items() if k!='sample'}));return
    # Global ceiling: no future additions or accidental broad rerun.
    assert len(plan['sample'])==96 and len({x['domain'] for x in plan['sample']})==96
    h.index._make_client=Client;h.index._get=measured_get;h.index._enforce_domain_rate_limit=lambda d:None
    cached_domains={load(p)['domain'] for p in (OUT/'records').glob('*.json')}
    if options.finalize:
        assert cached_domains=={r['domain'] for r in plan['sample']}, 'Offline finalization requires every domain accounted for'
        h.index._get=h.deny
    records=[];batches=[];started=time.perf_counter()
    for offset in range(0,96,15):
        tick=time.perf_counter()
        with ThreadPoolExecutor(max_workers=3) as pool:
            for r in pool.map(verify,plan['sample'][offset:offset+15]):
                records.append(r)
                print(json.dumps({'completed':len(records),'transport':r['transport'],'outcome':r['result'].get('reason',r['result']['outcome'])}),flush=True)
        batches.append({'stores':len(plan['sample'][offset:offset+15]),'seconds':time.perf_counter()-tick})
    verification_seconds=time.perf_counter()-started
    db=h.MemoryDB(deepcopy(baseline))
    for r in records:
        d=r['domain'];db.rows[d]=deepcopy(r['verified_row'])
        if r['result']['outcome']=='verified':
            tick=time.perf_counter()
            try:r['classification']=h.index.run_knowledge(db,deepcopy(db.rows[d]))
            except Exception as exc:r['classification']={'error':type(exc).__name__+': '+str(exc)}
            r['classification_seconds']=time.perf_counter()-tick
        r['after_row']=deepcopy(db.rows[d])
        r['classified_usable']=is_recent_verified(db.rows[d]) and is_classification_usable(db.rows[d])
    save(OUT/'outcomes.json',records);save(OUT/'index-after.json',list(db.rows.values()))
    save(OUT/'timing.json',{'verification_wall_seconds':verification_seconds,'chunks':batches,
         'cached_domains_at_start':sorted(cached_domains),'fresh_network_domains':96-len(cached_domains),
         'finished_at':datetime.now(timezone.utc).isoformat(),'classification_seconds':sum(r.get('classification_seconds',0) for r in records)})
    print('COMPLETE',len(records),flush=True)

if __name__=='__main__':main()
