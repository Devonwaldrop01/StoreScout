"""Offline Phase 1 measurement. Run: python -X utf8 tests/evaluations/verification_phase1.py

Does not change frozen evidence. No HTTP, production database, queues or models.
The observation rehearsal is NOT a replay of missing raw catalog bodies.
"""
import asyncio
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SOURCE = ROOT / 'docs/quality-audit/real-world'
OUT = ROOT / 'outputs/phase1/after'
OUT.mkdir(parents=True, exist_ok=True)
shutil.copytree(SOURCE/'evidence', OUT/'evidence', dirs_exist_ok=True)
os.chdir(OUT)
# Create the Windows event-loop self-pipe BEFORE the preserved harness blocks
# all socket connections. Reuse it; the network guard remains in force.
loop = asyncio.new_event_loop()
asyncio.run = lambda coro: loop.run_until_complete(coro)
runpy.run_path(str(SOURCE/'evidence/replay.py'))
loop.close()
load = lambda p: json.loads(p.read_text(encoding='utf8'))
original = load(SOURCE/'evidence/replay-results.json')
after = load(OUT/'evidence/replay-results.json')
parity = all(a['returned_domains'] == b['returned_domains'] and a['error'] == b['error']
             for a,b in zip(original, after)) and len(after) == len(original) == 50
assert parity, 'Changed results need fresh labels; do not apply saved ranks blindly'
runpy.run_path(str(SOURCE/'evidence/measure.py'))
from app.services.verification_lifecycle import classify_probe, successful_fields, retry_fields, due_at, plan_verification, timestamp
from app.services.discovery_quality import is_recent_verified

snapshot = load(SOURCE/'evidence/index-snapshot.json')
bydomain = {r['domain']:r for r in snapshot}
clock = datetime.fromisoformat('2026-09-05T20:44:23.705755+00:00')
evidence = load(SOURCE/'evidence/public-evidence-compact.json')
reference_domains = {r['index_domain'] for c in original for r in c['references']
                     if r['stage'] == 'not_verified'}
records=[]
for item in evidence:
    domain=item['domain']
    row=bydomain.get(domain) or bydomain.get('www.'+domain)
    if not row: continue
    observation=item['observations'][-1]
    now=timestamp(observation['checked_at'])
    h=observation['checks'].get('home',{}); p=observation['checks'].get('products',{})
    state=None
    if h.get('password_signal') or p.get('password_signal'): state='password_protected'
    elif h.get('challenge_signal') or p.get('challenge_signal') or p.get('status') in (401,403,429): state='blocked'
    elif h.get('status') == 402 or p.get('status') == 402: state='storefront_unavailable'
    elif p.get('error') or (p.get('status') or 0)>=500: state='temporarily_unreachable'
    readable = bool(p.get('readable_catalog') and (p.get('observed_product_count') or 0)>0 and not state)
    if not readable and not state: state='no_readable_catalog'
    markers=h.get('shopify_markers') or p.get('shopify_markers') or []
    # This is the documented producer's successful observation, not invented
    # product IDs, variant IDs, or a reconstructed HTTP response.
    obs={"version":1,"state":"readable","observed_at":now.isoformat(),
         "source":"frozen_audit_observation","sample_count":p.get('observed_product_count'),
         "signature":hashlib.sha256(json.dumps(p.get('product_examples'),sort_keys=True).encode()).hexdigest()} if readable else None
    result={"reachable":bool(h.get('status') or p.get('status')), "monitorable":readable,
            "confidence":min(100,55*readable+25*bool(markers)), "access_state":state,
            "signals":["Shopify CDN detected"] if markers else [], "catalog_observation":obs}
    state=classify_probe(result)
    projected=deepcopy(row)
    if state=='verified_shopify': projected.update(successful_fields(obs,result['confidence'],result['signals']))
    else: projected.update(retry_fields(row,state,now))
    records.append({"domain":row['domain'],"before_status":row['status'],"after_state":state,
                    "eligible_after":is_recent_verified(projected,now=now),
                    "observed_at":now.isoformat(),"reference":row['domain'] in reference_domains,
                    "raw_validator_measured":False})

renewal=[r for r in snapshot if r['status']=='verified' and due_at(r)<=clock]
remaining=deepcopy(renewal); batches=[]
while remaining:
    batch=plan_verification(remaining,clock,100)
    assert batch
    domains=[r['domain'] for r in batch]
    batches.append(domains)
    remaining=[r for r in remaining if r['domain'] not in domains]
assert sum(map(len,batches))==len({d for b in batches for d in b})==320
reference_outcomes=[r for r in records if r['reference']]
missing=sorted(reference_domains-{r['domain'] for r in reference_outcomes})
summary={
    "frozen_benchmark_parity":parity,"case_modes":len(after),
    "benchmark_verdict":"Weak; no production supply was changed",
    "observation_rehearsal":{"records":len(records),"states":dict(Counter(r['after_state'] for r in records)),
        "accepted_observations":sum(r['eligible_after'] for r in records),
        "unverified_reference_outcomes":reference_outcomes,"missing_reference_observations":missing,
        "limitation":"Saved checks omit raw IDs/variants. This measures typed observation transitions, not raw HTTP validation or live throughput."},
    "renewal_plan":{"total":len(renewal),"deduplicated":True,"max_batch":100,"batches":batches,
        "limitation":"Local plan only. Mixed-lane processing reserves capacity for backlog/retries; these standalone renewal batches are not a production duration estimate."},
    "oldest_backlog_age_days":max((clock-timestamp(r['created_at'])).total_seconds()/86400
                                  for r in snapshot if r['status'] in ('discovered','candidate') and timestamp(r.get('created_at'))),
    "protected_evidence_sha256":{str(p.relative_to(SOURCE)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [SOURCE/'reference-panel.json',SOURCE/'evidence/index-snapshot.json',SOURCE/'evidence/relevance-labels.json']},
    "reference_panel_lf_sha256":hashlib.sha256((SOURCE/'reference-panel.json').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
    "partitions":{"evaluation_families":["specialty coffee","mechanical keyboards"],
                  "note":"Whole families reserved for subsequent phases; all were already inspected in the prior audit. No relevance tuning in Phase 1."}
}
(OUT/'phase1-measurements.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
(OUT/'observation-outcomes.json').write_text(json.dumps(records,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in summary.items() if k not in ('renewal_plan','observation_rehearsal')},indent=2))
print('Renewal:',len(renewal),'Reference accepted:',sum(r['eligible_after'] for r in reference_outcomes),'/',len(reference_domains))
