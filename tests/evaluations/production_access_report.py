"""Package bounded public-access evidence without new requests or baseline edits."""
import hashlib,json,statistics
from collections import Counter
from datetime import datetime,timedelta
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from app.services.discovery_quality import is_recent_verified,is_classification_usable
OUT=ROOT/'outputs/production-access';DEST=ROOT/'docs/quality-audit/phase1/production-access'
DEST.mkdir(parents=True,exist_ok=True)
load=lambda p:json.loads(p.read_text(encoding='utf8'))
save=lambda n,d:(DEST/n).write_text(json.dumps(d,indent=2),encoding='utf8')
records=load(OUT/'outcomes.json');plan=load(OUT/'manifest.json');timing=load(OUT/'timing.json')
clock=datetime.fromisoformat(timing['finished_at'])
known=[r for r in records if r['result']['outcome']!='delivery_unknown']
verified=[r for r in known if r['result']['outcome']=='verified']
assert len(records)==96 and len(known)==81 and len(verified)==36
stats={}
for transport in ['httpx','native_curl']:
    assigned=[r for r in records if r['transport']==transport]
    observed=[r for r in assigned if r['result']['outcome']!='delivery_unknown']
    success=[r for r in observed if r['result']['outcome']=='verified']
    stats[transport]={'assigned':len(assigned),'determinate':len(observed),'unknown':len(assigned)-len(observed),
        'http_response':sum(any(q.get('status') for q in r['requests']) for r in observed),
        'any_2xx':sum(any(q.get('status') and 200<=q['status']<300 for q in r['requests']) for r in observed),
        'verified':len(success),'blocked':sum(r['result'].get('reason')=='blocked' for r in observed),
        'temporary':sum(r['result'].get('reason')=='temporarily_unreachable' for r in observed),
        'no_catalog':sum(r['result'].get('reason')=='no_readable_catalog' for r in observed),
        'logical_requests':sum(len(r['requests']) for r in observed),
        'wire_attempts_including_redirects':sum(len(q['hops']) for r in observed for q in r['requests']),
        'classification_pass':sum(r.get('classification',{}).get('confidence',0)>=55 for r in success),
        'classified_usable':sum(r['classified_usable'] for r in success)}
by={r['domain']:r for r in records}
window=[by[r['domain']] for r in plan['sample'][45:90]]
assert all(r['seconds'] is not None and 'offline_adapter_repair' not in r for r in window)
start=min(datetime.fromisoformat(r['verified_row']['updated_at'])-timedelta(seconds=r['seconds']) for r in window)
end=max(datetime.fromisoformat(r['verified_row']['updated_at']) for r in window)
seconds=(end-start).total_seconds()
window_stats={'stores':45,'seconds':seconds,'verified':sum(r['result']['outcome']=='verified' for r in window),
    'start':start.isoformat(),'end':end.isoformat(),
    'interpretation':'Completed uninterrupted window only. Excludes stalled final chunk; not sustained production throughput.'}
supply={}
for name,path in [('before',ROOT/'outputs/bounded-cycle/index-after.json'),('after',OUT/'index-after.json')]:
    rows=load(path)
    supply[name]={'total':len(rows),'verified_status':sum(r.get('status')=='verified' for r in rows),
        'fresh_readable':sum(is_recent_verified(r,now=clock) for r in rows),
        'classified_usable':sum(is_recent_verified(r,now=clock) and is_classification_usable(r,now=clock) for r in rows)}
protected=load(ROOT/'docs/quality-audit/phase1/controlled-validation/measurements.json')
source=ROOT/'docs/quality-audit/real-world/evidence'
for n,d in protected['protected_hashes'].items():assert hashlib.sha256((source/n).read_bytes()).hexdigest()==d
assert hashlib.sha256(next((ROOT/'docs/quality-audit').rglob('reference-panel.json')).read_bytes()).hexdigest()==protected['reference_panel_sha256']
previous=load(ROOT/'outputs/controlled-validation/outcomes.json')
old429=[q for r in previous for q in r['requests'] if q.get('status')==429 and q.get('body_file')]
prefixes=Counter((ROOT/'outputs/controlled-validation/raw'/q['body_file']).read_bytes()[:1500] for q in old429)
assert len(old429)==420 and len(prefixes)==1
bench={v:load(OUT/f'benchmark/{v}/evidence/benchmark-metrics.json')['summary'] for v in ['frozen','controlled']}
save('measurements.json',{'clock':clock.isoformat(),'transport':stats,'supply':supply,'completed_window':window_stats,
    'classification_completed':len(verified),'classification_pass':20,'classification_seconds':timing['classification_seconds'],
    'classification_median_seconds':statistics.median(r['classification_seconds'] for r in verified),
    'same_run_network_retries':0,'local_immediate_repeat_skips':81,
    'suppressed_requests_after_protection':sum(len(r['suppressed_after_protection']) for r in records),
    'prior_cooldowns':load(OUT/'previous-cooldowns.json'),'benchmark_summaries':bench,
    'production_deployed_commit_verified':False,'production_network_reproduced':False,
    'protected_hashes':protected['protected_hashes'],'reference_panel_sha256':protected['reference_panel_sha256']})
save('sample-manifest.json',plan)
save('outcome-ledger.json',[{k:r.get(k) for k in ['domain','transport','status','result','requests','suppressed_after_protection',
    'seconds','immediate_repeat','classification','classification_seconds','classified_usable','offline_adapter_repair']}
    | {'next_verification_at':r['verified_row'].get('next_verification_at')} for r in records])
save('validation-limitations.json',{'adapter_repair':load(OUT/'adapter-repair.json'),
    'streaming_interruption':load(OUT/'streaming-interruption.json'),'final_interruption':load(OUT/'final-interruption.json'),
    'render':'Connector lists one workspace but requires explicit workspace confirmation before service reads. Question remains pending; no service details or logs accessed.'})
report='''# Bounded production-like access validation

**Verdict: usable supply can be produced locally, but sustainable production capacity is not established. Do not start broad acquisition or rollout.** Completed 2026-09-06 with public GETs and local records only. No production data/configuration changes, push, deployment, paid AI, challenge solving, proxy rotation or broad acquisition.

## Fidelity and remaining access gate

Repository inspection shows that the Celery worker delegates verification to the **web service** through `/api/v1/internal/store-index/verify`. The web service performs merchant GETs. Worker-to-web HTTPX delivery has a 60-second timeout, one delivery retry after five seconds; this is distinct from retrying a merchant. Comments attribute worker-IP blocking to the reason for this routing, but comments are not a current controlled IP experiment.

The shared requirements pin curl-cffi 0.15.0 and HTTPX 0.28.1. The normal code selects curl-cffi when available, with Chrome 120 impersonation and matching User-Agent; HTTPX is the fallback. Local curl-cffi 0.15.0 imports successfully. To obey the no-bypass constraint, the validation used native curl **without impersonation**, plus an HTTPX comparison arm, retaining the existing explicit User-Agent/Accept headers. No alternative fingerprints or challenge cookies were tried. The omitted impersonation is a material difference from the repository configuration, not evidence of exact production parity. [curl-cffi documentation](https://curl-cffi.readthedocs.io/en/stable/index.html) describes this transport capability.

Code defaults: 100 rows per verification run, at most 200 with an override; concurrency three, capped at four; chunks of 15 at the default; verification every 15 minutes, knowledge every 20 minutes. `render.yaml` specifies one Celery process, while the Dockerfile fallback command specifies two, so the deployed command must be checked. Runtime configuration can override batch/enabled settings. The shared Redis limiter is called once per domain pass and fails open if Redis is unavailable; it is not a strict per-request limiter.

This validation used concurrency three, one batch of 96 split into 15-row chunks, sequential per-store endpoints and an additional one-second same-host gap. Public redirects were bounded and checked for public destinations. It stopped further network requests after protection responses. The normal endpoint order remains homepage, cart marker, products sample of at most 250, and collections only after a readable catalog. Response status, safe diagnostic headers and decoded public bodies were retained; cart tokens/cookies were not retained.

**Actual deployed commit, effective settings, service command, Linux runtime, Redis behavior, web-service egress and live logs remain unverified.** The Render connector requires the owner to confirm a workspace before service reads; “Devon's workspace” is the sole listed workspace, and the confirmation question remains pending. No production verification endpoint was invoked because it writes production records. The network comparison ran locally on Windows, not from Render. Exact production/network-identity attribution is therefore not possible in this cycle.

## Sample and interruptions

The seeded manifest selects 96 existing, due records from 37,866 eligible index rows, excluding all 248 previously sampled hostnames and their www aliases. Status allocation: 87 discovered, three candidate, two failed, two rejected, two verified. These are existing indexed stores, not new acquisition. The small rare-state strata are diagnostic, not precise independent estimates.

HTTPX received 49 assigned stores and native curl 47. **81 stores have determinate outcomes; 15 remain unresolved or unstarted.** Eleven were conservatively reserved from an interrupted streaming-adapter chunk; three later in-flight HTTPX requests lacked final outcomes when stopped; one had not started. None was re-requested. Unknowns are not merchant failures and are not silently removed from the manifest. Reported observed rates below use the 40/41 determinate records, with assigned-denominator lower bounds also shown.

An initial measurement-wrapper defect forwarded Content-Encoding after decoding, causing double decompression. Sixteen saved HTTPX observations were repaired entirely offline. Their home/product bytes support the resulting verification, but discarded cart bodies and unrequested collections cannot be reconstructed; no positive cart evidence was invented. Original error records remain preserved. The wrapper now strips representation headers and has a gzip regression test.

The curl streaming adapter stalled; it was replaced for untouched domains with the synchronous method used by production. Later HTTPX requests also remained unresolved past expected request durations. Their precise cause was not established. Per-operation timeouts are not demonstrated end-to-end deadlines in this local harness. Pauses, repairs and interruptions make whole-run throughput unsuitable as a production capacity estimate.

## Measured access and classification

| Measure | HTTPX | Native curl, no impersonation |
|---|---:|---:|
| Assigned records | 49 | 47 |
| Determinate outcomes | 40 | 41 |
| Unresolved / unstarted | 9 | 6 |
| Any HTTP response | 37/40 (92.5%) | 40/41 (97.6%) |
| Any successful 2xx response | 36/40 (90.0%) | 3/41 (7.3%) |
| Readable, successfully verified catalog | 36/40 (90.0%) | 0/41 (0%) |
| Verification lower bound across all assigned | 36/49 (73.5%) | 0/47 (0%) |
| Blocked/challenged | 1/40 (2.5%) | 37/41 (90.2%) |
| Temporary failure | 3/40 (7.5%) | 1/41 (2.4%) |
| No readable catalog | 0 | 3/41 (7.3%) |
| Logical requests, determinate records | 138 | 49 |
| Wire attempts including redirects, determinate records | 133 | 48 |
| Logical requests per successful catalog | 3.83 | Undefined: zero successes |
| Classification completion | 36/36 | No verified inputs |
| Classification passes floor 55 | 20/36 (55.6%) | Not measurable |
| Verified → usable classified | 20/36 (55.6%) | Not measurable |

Logical endpoint attempts include DNS failures before a wire request, explaining why the wire count can be smaller. Across the 81 determinate records, 187 logical requests produced 36 verified catalogs: **5.19 requests per success**. This excludes unknown request totals from the interrupted chunk, so it is not an exact whole-run ratio. At least 184 wire attempts are documented across all records, including three unresolved attempts. The 15 unknowns prevent a clean population estimate or full transport-effect attribution.

All 36 verified catalogs completed free classification in **1.846 seconds total**, median **0.052 seconds**; 20 passed and 16 remained uncertain. These are confidence-gate passes, not independently adjudicated category accuracy. The improved classifier was unchanged. Unfamiliar products, mixed assortments and sparse evidence still limit this sample; the prior 79.2% result on 24 different successful catalogs did not generalize to a universal yield. No paid model was called, and no paid latency was measured.

## Throughput and retries

A completed, uninterrupted 45-store window took **30.665 seconds**, producing **17 verified catalogs**: approximately 88.0 attempted stores/minute and **33.3 successful catalogs/minute during that short window**. It used three concurrent tasks and includes quick blocked responses. The subsequent chunk stalled, so these are burst measurements, not sustainable capacity. The scheduler's 100-per-15-minute default also bounds long-run dispatch independently of short-window HTTP speed. No valid end-to-end production throughput estimate can be supplied from this run.

All 81 determinate outcomes were immediately passed back through the local claim/scheduling logic: **81/81 skipped with zero network requests**. The old 248-record sample had 241 records still not due and seven temporary failures due; none was re-fetched. This preserved the old blocked-store cooldowns. In this run, 76 later endpoint calls were suppressed after protection responses. No same-run network retry or challenge solving occurred. The captured new responses had no Retry-After value. Blocked outcomes schedule at least 24 hours plus deterministic jitter, temporary failures at least one hour, with exponential backoff capped at seven days; successful verification renews after 53 days. Multi-day retry recovery is not measured.

## Comparison with the earlier HTTPX fallback

The previous 248-store run had 24 verified catalogs (9.7%), 211 blocked (85.1%), seven temporary failures (2.8%), five unreadable catalogs and one unavailable storefront. It used 768 logical / 809 wire attempts, or 32 logical requests per success. It continued to the catalog after challenged homepages and had no explicit same-host gap inside the pass.

The retained evidence contains **420 captured 429 pages with one identical first-1,500-byte challenge prefix**, titled “Verifying your connection.” Homepage 429s numbered 207 and product 429s 210; cart responses were 200 on 234 stores. That is strong evidence of selective access/challenge handling rather than 85% dead domains or a blanket lack of Shopify catalogs. The earlier capture did not retain the diagnostic response headers needed to identify every challenge source or infer an IP reputation score.

The new native-curl arm repeatedly received 403 plus `cf-mitigated: challenge`; HTTPX mostly read public catalogs. The large contrast under one local schedule makes transport-dependent protection a strong local association. It does **not** explain by itself why the earlier HTTPX run was blocked: the stores, date, pacing, early-stop behavior and possibly network path differed, and no paired within-store experiment was performed after a challenge. No protected store was retried with another transport.

| Possible limitation | What the evidence supports |
|---|---|
| Transport implementation | Strong local association; native curl without impersonation was challenge-heavy. Exact deployed TLS behavior remains untested. Streaming-wrapper stalls also contaminated part of this validation. |
| Network identity / IP reputation | Material unresolved variable because production egress was not reproduced. No direct comparison or reputation measurement. |
| Request pacing | Previous homepage challenges often occurred on the first request. Local same-host gaps and low concurrency did not eliminate native-curl challenges; pacing alone is not established as the cause. |
| Endpoint selection | Public products access remains necessary for trusted verification. The old cart-200/catalog-429 split shows a cart marker cannot substitute for a readable catalog. Stop-after-protection reduces wasted requests. |
| Shopify / CDN challenge behavior | Directly observed challenge pages and new Cloudflare challenge headers; exact merchant/platform policy and triggering signal remain unknown. |
| Application logic | Empty-result error was local and fixed. The repository pass continues after early protection responses, while this harness stops; production Redis pacing and reliable end-to-end deadlines remain validation gaps. Classification completion is fast but usable yield is incomplete. |

The principal demonstrated local constraint is **transport-sensitive access protection**, with network identity unresolved. The exact dominant cause of the earlier 85% blocked result and deployed capacity cannot be isolated honestly from these data.

## Local supply and preserved benchmarks

| Local index measure, same current cutoff | Before | After |
|---|---:|---:|
| Total existing index rows | 38,221 | 38,221 |
| Verified status | 404 | 439 |
| Fresh readable verified | 377 | 412 |
| Classified usable | 365 | 384 |

Twenty newly usable classified records are offset by one previously usable record losing eligibility, yielding **+19 net**. Thirty-six newly verified discovered records are offset by one failed renewal, yielding +35 verified. Unresolved records retain their prior local state rather than receiving invented merchant classifications. This new index is an isolated artifact; no production records were changed, and its new discovery results have not been benchmarked or claimed as relevant improvements.

Both preserved frozen and controlled benchmark states were replayed after the empty-state fix: **100/100 case/mode result lists retained their exact ordered domains**. All precision, relevance, known-reference recall and niche results remain unchanged from the bounded-cycle report. Empty-result HTTP errors fall from five to zero in each mode/state. Actual provider authentication/rate-limit/failure responses remain errors; an unavailable index without a functioning alternative returns 503. Empty searches do not trigger new acquisition jobs. Original baseline hashes and reference-panel hash remain unchanged.

## Files, checks and stop point

Application change: `app/api/v1/competitors.py` only in this cycle. Regression tests: `tests/test_access_validation.py`, including empty searches, preserved real errors, index outage handling, no acquisition side effect and decoded gzip responses. **267 tests passed** with nine existing warnings; targeted checks and both preserved benchmark replays passed. Existing classification/semantic filters and ranking were preserved.

Validation tools: `production_access_validation.py`, `access_response.py`, `access_empty_benchmark.py`, `production_access_report.py` under `tests/evaluations/`. Artifacts beside this report contain the manifest, every recorded outcome/request, exact metrics and unresolved limitations. Raw public bodies, original interrupted records and the isolated new index remain under `outputs/production-access/`. Running `--finalize` performs no network requests; completed records are cached. Do not treat cached finalization timing as fresh throughput.

**Stop here; larger growth is not yet supported by sufficient evidence.** Local public access can feed the improved lifecycle and produce classified supply, but the incomplete sample, divergent transports, unmeasured deployed network identity, unresolved request deadlines and 55.6% classification pass rate do not establish sustainable capacity. The next prerequisite is read-only confirmation of the actual deployed web-service transport/settings/logs, then a separately authorized bounded run from an appropriate non-production write environment with production-like egress and durable per-attempt instrumentation. Do not use impersonation changes, proxy rotation or repeated challenged requests to force yield. No rollout, broader acquisition or paid classification experiment is initiated by this report.
'''
(DEST/'RESULTS.md').write_text(report,encoding='utf8')
print(json.dumps({'report':str(DEST/'RESULTS.md'),'transport':stats,'supply':supply}))
