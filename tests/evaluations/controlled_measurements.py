"""Offline measured rates, lifecycle invariants, and benchmark comparison."""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tests'),str(Path(__file__).parent)]
import controlled_catalog_validation as harness
from app.services import verification_lifecycle as policy, store_index as index, store_dna
from app.services.discovery_quality import is_recent_verified
from test_verification_lifecycle import MemoryDB
OUT=harness.OUT; SOURCE=harness.SOURCE; load=harness.load; save=harness.save
records=load(OUT/'outcomes.json'); before=load(SOURCE/'index-snapshot.json')
meta=load(OUT/'run-metadata.json'); now=datetime.fromisoformat(meta['finished_at'])
sample=[r for r in records if r['sample']]; success=[r for r in records if r['result']['outcome']=='verified']
weights={r['domain']:r for r in load(SOURCE/'health-sample.json')}
def state(r): return r['verified_row']['verification_state']
def interval(k,n):
    z=1.95996398454; p=k/n; a=1+z*z/n
    mid=(p+z*z/(2*n))/a; half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/a
    return [max(0,mid-half),min(1,mid+half)]
def rates(rs):
    counts=Counter(state(r) for r in rs)
    return {s:{'n':counts[s],'rate':counts[s]/len(rs)} for s in sorted(policy.STATES)}
N=sum(w['weight'] for w in weights.values())
weighted={s:sum(weights[r['domain']]['weight'] for r in sample if state(r)==s)/N for s in sorted(policy.STATES)}
# Conservative sampling-only concentration bound for the fixed probability
# sample, without pretending singleton strata support a variance estimate.
bound=math.sqrt(math.log(40)/2*sum(w['weight']**2 for w in weights.values() if w['n']<w['N']))/N
requests=[q for r in records for q in r['requests']]
times=[r['classification_seconds'] for r in success]
signatures=[]
for r in success:
    request=next(q for q in r['requests'] if '/products.json?' in q['url'])
    raw=(OUT/'raw'/request['body_file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==request['sha256']
    observation=policy.successful_catalog(json.loads(raw)['products'],now,'offline_identity_check')
    assert observation['signature']==r['after_row']['catalog_observation']['signature']
    signatures.append(r['domain'])
# Every state is still in cooldown; a normal scheduled call must skip HTTP.
index._get=harness.deny
db=MemoryDB([r['after_row'] for r in records])
skips=[index.verify_and_store(db,r['domain'],'controlled_cooldown_check') for r in records]
assert all(r['outcome']=='skipped' for r in skips)
# Count entry into each optional model path with the actual free fallback;
# constructors remain forbidden and keys blank. No fabricated AI result.
calls=Counter()
for owner,name in ((index,'classify_store_ai'),(index,'_ai_classify_tiebreak'),(store_dna,'generate_store_dna')):
    original=getattr(owner,name)
    def wrapper(*a,_original=original,_name=name,**k):
        calls[_name]+=1
        return _original(*a,**k)
    setattr(owner,name,wrapper)
for r in success:
    local=MemoryDB([r['verified_row']])
    result=index.run_knowledge(local,deepcopy(r['verified_row']))
    assert result==r['classification']
    assert local.rows[r['domain']]['store_dna']['method']=='heuristic'

def supply(rows):
    usable=[r for r in rows if is_recent_verified(r,now=now)]
    return {'verified_status':sum(r['status']=='verified' for r in rows),'fresh_readable_verified':len(usable),
      'classified_usable':sum(r.get('category_confidence') is None or r['category_confidence']>=55 for r in usable)}
comparison={v:{'supply':supply(load(OUT/v/'evidence/index-snapshot.json')),
    'benchmark':load(OUT/v/'evidence/benchmark-metrics.json')['summary']} for v in ['before','after','sample_only','successes_only']}
ordinal={d:i for i,d in enumerate(harness.domains)}
blocks=[]
for start in range(0,240,40):
    group=[r for r in sample if start<=ordinal[r['domain']]<start+40]
    blocks.append({'sample_positions':[start+1,start+len(group)],'states':dict(Counter(state(r) for r in group))})
strata=defaultdict(list)
for r in sample:strata[r['before_status']].append(r)
summary={
 'clock':now.isoformat(),'stores':len(records),'probability_sample':len(sample),'diagnostic_controls':len(harness.controls),
 'control_overlap_sample':len(set(harness.controls)&set(weights)),
 'sample_rates':rates(sample),'all_rates':rates(records),'population_weighted_observed_rates':weighted,
 'sampling_only_95_bound_halfwidth':bound,
 'uncertainty_note':'Weighted rates describe this transport/access window, not stable merchant or production yield. Challenge rates changed over run order. Singleton strata prevent ordinary design-variance estimates. Bound covers sampling only, not access bias.',
 'status_strata':{k:{'n':len(v),'verified':sum(state(r)=='verified_shopify' for r in v)} for k,v in strata.items()},
 'time_blocks':blocks,
 'http':{'logical_requests':len(requests),'wire_requests_including_redirects':sum(len(q['hops']) for q in requests),
    'logical_per_verified_catalog':len(requests)/len(success),
    'wire_per_verified_catalog':sum(len(q['hops']) for q in requests)/len(success),
    'dns_or_transport_errors':dict(Counter(q.get('error','').split(':')[0] for q in requests if q.get('error'))),
    'final_statuses':dict(Counter(str(q.get('status')) for q in requests)),
    'batches':meta['batches'],'active_seconds':sum(b['seconds'] for b in meta['batches']),
    'active_verified_catalogs_per_minute':len(success)*60/sum(b['seconds'] for b in meta['batches']),
    'note':'No 15-minute scheduler pauses or web-worker handoff measured; rapid blocked responses inflate raw attempt throughput. HTTPX is the supported fallback transport, not curl browser impersonation.'},
 'classification':{'attempts':len(success),'completed':sum('error' not in r.get('classification',{}) for r in success),
    'failed':sum('error' in r.get('classification',{}) for r in success),
    'above_floor':sum(r.get('classification',{}).get('confidence',0)>=55 for r in success),
    'above_floor_yield':sum(r.get('classification',{}).get('confidence',0)>=55 for r in success)/len(success),
    'conditional_95_wilson_descriptive':interval(sum(r.get('classification',{}).get('confidence',0)>=55 for r in success),len(success)),
    'new_above_floor_domains':[r['domain'] for r in success if r['before_status']!='verified' and r['classification'].get('confidence',0)>=55],
    'seconds_total':sum(times),'seconds_median':statistics.median(times),'seconds_max':max(times),
    'optional_ai_path_entries':dict(calls),'paid_calls':0,'heuristic_dna_completed':len(success),'ai_dna_completed':0,
    'prior_signatures':sum(r['prior_signature'] for r in success),
    'prior_classifications':sum(r['prior_classification'] for r in success),
    'legacy_classifications_invalidated':sum(r['classification_invalidated'] for r in success),
    'actual_changed_signature_rate':None,
    'identical_raw_signature_checks':len(signatures),
    'note':'All successful inputs lacked prior versioned signatures. Initial invalidation is measured; actual temporal catalog-change frequency and paid-model latency/quality are not.'},
 'cooldown_skips_without_http':len(skips),'comparison':comparison,
 'new_entries_adjudicated':dict(Counter(r['variant'] for r in load(OUT/'entry-adjudications.json'))),
 'protected_hashes':{name:hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() for name in ['index-snapshot.json','relevance-labels.json','health-sample.json']},
 'reference_panel_sha256':hashlib.sha256((SOURCE.parent/'reference-panel.json').read_bytes()).hexdigest(),
}
save(OUT/'measurements.json',summary)
print(json.dumps({k:v for k,v in summary.items() if k not in ('comparison','protected_hashes','sample_rates','all_rates')},indent=2))
