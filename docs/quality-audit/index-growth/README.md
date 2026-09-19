# Existing-supply growth: measured findings and local fixes

Measured 19 September 2026. Production SELECTs, historical Render metrics and offline replay only. No deployment, production mutation, merchant traffic, paid AI, acquisition, migration, service restart, canary or observer work occurred. Existing release pins and benchmark files are unchanged.

Branch: `codex/index-supply-growth-2026-09-19`, based on `26d20ae4b3cbbac0191552211fe999af6a32d62c`. This is a new local development branch, not a replacement for any approved release. Its commit is provided in the task completion message / `git rev-parse HEAD`.

## 1. The bottleneck is conversion and renewal, not raw acquisition

The legacy queue head is stuck on aliases. All **100 oldest pending verification rows** are `www.` domains. All 100 already have stripped-domain counterparts: **78 verified, 22 failed/rejected**. The legacy batch selects the original rows, strips `www.`, and persists the outcome against the stripped domain, leaving the original pending rows at the head. Across the index there are **9,731 pending www rows**, including **138 with existing stripped-domain counterparts**. This explains repeated apparent successful runs without draining the pending set. It does not prove every historical attempt failed for this reason. See [exact queue-head query](legacy-queue-head.json) and [canonical-domain census](canonical-domains.json).

The reviewed lifecycle already preserves the selected hostname and uses owned claims, retry times, fair scheduling and renewals. Re-implementing that work would add no value. Those changes are absent from the live legacy schema/runtime, and Worker/Beat are currently inert under the established maintenance state.

The 30-day run table reports **147,100 processed / 59,690 verified outcomes**, yet only 411 rows currently have verified status. These are executions/outcomes, not 59,690 distinct stores. The old comment claiming every scheduled verification was new was false for the alias case. There were also 13,988 classification attempts and 110,520 resolution attempts. Counters are not a historical unique-store funnel. [Run query/results](runs.json).

### Exact census

Database read timestamp: **2026-09-19 21:16:05 UTC**. These are separate SELECT snapshots, not an exported transaction spanning every query.

| Funnel/state | Exact count | Meaning |
|---|---:|---|
| Raw discovered references | 298,633 | Queue records, not unique active merchants |
| Unresolved references | 260,458 | No nonempty resolved domain |
| Queue pending / failed / resolved statuses | 180,397 / 80,148 / 38,088 | 87 failed refs nevertheless retain a domain |
| References with a domain | 38,175 | Distinct domains: **38,166** |
| All index rows / distinct exact domains | 40,010 / 40,010 | Includes other acquisition sources |
| Discovered-domain backlog | 37,877 | Index status, not queue's resolved-status count |
| Candidate backlog | 1,323 | Total pending verification outcome: **39,200** |
| No recorded verification timestamp | 39,190 | 37,867 discovered + 1,323 candidate; not proof no request ever ran |
| With some recorded verification timestamp | 820 | Includes failures and ten still-discovered rows |
| Failed / rejected index status | 61 / 338 | Legacy reasons do not support reliable lifecycle subdivision |
| Verified | 411 | Historical status flag |
| Verified but unclassified | 0 | `knowledge_at IS NULL` |
| Verified and classification recorded | 411 | Not equivalent to Discovery eligibility |
| Classified below confidence 55 | 55 | Missing confidence: 0 |
| Verified older than 60 days | 320 | Renewal backlog |
| Fresh, readable, verification confidence >=60 | 78 | Exact successful-catalog signal and 60-day gate |
| Above plus classification confidence >=55 | **34** | Current snapshot under the reviewed Discovery gates |

The live legacy endpoint is not claimed to return exactly 34: this is the reviewed lifecycle applied offline to the live snapshot. A 411-store "usable" baseline would misstate the product-quality gate. Of the 91 timestamp-fresh verified rows, 13 fail the readable-catalog/verification floor; another 44 of the remaining 78 fail the classification floor. The low-confidence and stale sets overlap.

Verified classification distribution: **55 below55; 7 at55–69; 67 at70–84; 282 at85–100**. Last recorded verification: September11 15:17:55 UTC; last classification: September11 15:20:45 UTC. [Census](funnel.json), [confidence](confidence.json), [schema](schema.json), [queue](queue.json).

**Not reconstructible exactly in production yet:** retry-due, active/pending claim, temporarily unreachable, blocked, no-readable-catalog and non-Shopify lifecycle counts. The six reviewed lifecycle columns are absent. They must be reported as unknown, not zero or fabricated from status labels. The 39,200 pending-status rows are measurable, but active attempts cannot be inferred from them.

Legacy reason evidence: 61 failed=`unreachable_or_dns`; rejected includes209 combined below-threshold/catalog-locked, 47 confidence0, 30 dead-domain, 20 invalid-storefront, 18 not-Shopify, 3 no-products and21 other below-threshold cases. Nine currently verified rows retain conflicting rejection reasons (six invalid-storefront, three dead-domain). These are historical labels, not newly established truth. [Complete reasons](reasons.json).

## 2. Local implementation and measured effect

**Classification persistence:** `stage_knowledge` selected no `updated_at`, while the reviewed `run_knowledge` compare-and-set requires that version. Its writes therefore targeted a null timestamp and returned superseded for ordinary stored rows. Added the version to both full and fallback projections; did not weaken ownership or signature checks. This is a newly found defect in the prepared release, not an explanation invented for old production classifications.

Projection-aware replay of **36 retained, successfully verified real catalogs** through the actual batch and no-key classification/DNA paths:

| Measure | Before | After |
|---|---:|---:|
| Attempted | 36 | 36 |
| Persisted classifications | 0 | 36 |
| Confidence >=55 / usable classification | 0 | 20 (55.6%) |
| Below threshold | No new persisted results | 16 (44.4%) |
| CPU + in-memory batch wall time | 0.98s | 0.95s |

This measures persistence and free heuristic computation, not production DB latency, paid-model accuracy, or new network verification yield. Five catalogs score0; four score54; seven score1–53. The weak cases include missing English taxonomy vocabulary (laser levels, floats, vehicle accessories, collectibles), non-English product types, mixed assortments, and scant/ambiguous product signals. Lowering the threshold would promote unsupported matches. The classification quality itself was not retuned.

**Protection handling:** homepage/cart/catalog challenge, 401/403/429, password and unavailable responses end the pass before subsequent endpoints. Longer valid `Retry-After` values extend the existing lifecycle cooldown; malformed values retain policy defaults. Catalogs already obtained are not discarded merely because the final optional collections request is rate-limited. No transport fingerprint, bypass, concurrency or confidence change.

Offline replay of the previous248-store response sequence suppresses **417 of768 logical calls (54.3%)**, leaving351; none of its24 successful catalogs loses eligibility from an earlier protection stop. This is avoided-request evidence, not a demonstrated increase in merchant access. The later96-store harness already stopped after protection, so no additional recorded calls are suppressed there. One response body from that capture is unavailable; its status metadata remains available. This replay counts190 recorded entries including uncertain operations, while the prior187-call completed-outcome summary used a narrower denominator. [Measurements](offline-measurements.json).

**Admin truthfulness:** enabled configuration is no longer labeled "Worker running daily". The API/UI distinguish disabled pipeline, process-local deployment hold, recent recorded task activity and inactive/unknown state; they display last successful recorded run, verification/classification dates, backlog and last-hour outcome throughput. Unknown reads stay unknown, not zero. An API process cannot attest that an external Render worker is alive/inert; the UI explicitly says so. No new worker telemetry or remote-control commands were introduced. Historical classified totals no longer say "user-facing".

Changed implementation: `app/tasks/store_index.py`, `app/services/store_index.py`, `app/services/index_operations.py`, `app/api/v1/store_index.py`, `frontend/app/admin/store-index/page.tsx`, `frontend/lib/indexOperations.ts`. Regression tests cover selected row-version persistence/fallback and stale writes, early endpoint stops, optional final taxonomy failure, Retry-After, and truthful/unknown operational state.

Validation: **393 backend tests passed; 48 frontend tests passed; TypeScript passed**. Fifteen new backend cases and two frontend cases; existing hold/lease/lifecycle/semantic tests remain passing. Dependency deprecation warnings remain. Tests used local Windows Python/Node; this branch has not been packaged into a newly approved Linux release image.

## 3. Throughput and resource limits

Defaults retained:100verification slots every15minutes;100classification slots every20minutes;3merchant domains concurrently (cap4); Celery process concurrency2. Ideal schedule ceilings are **9,600 verification attempts/day and7,200 classification attempts/day**, shared by retries and renewals. Two Celery processes do not double either stage because leases prevent overlap. Four lifecycle lanes share verification capacity; unresolved references need not be acquired again.

Those are ceilings, not measured sustainable rates. In the prior45-domain uninterrupted window,45attempts/30.665s=**88.0/min**,17successfulcatalogs=**33.3/min**, followed by a stall elsewhere in the sample. This cannot be extrapolated to24hours. At3concurrent deliveries,100operations each taking60s occupy about34minutes; a125s connection-failure path takes about71minutes, skipping scheduled overlapping runs. Approximate schedule ceilings then fall to3,200/day and1,920/day respectively before other load. Merchant read timeouts and unknown outcomes are not successful stores.

Prior access evidence is transport/egress dependent:

| Capture | Assigned / determinate | Successful verification | Blocking / temporary | Free classification pass |
|---|---:|---:|---:|---:|
| Earlier controlled HTTPX |248/248|24 (9.7%)|211blocked (85.1%);7temporary;5no-catalog;1unavailable|Earlier bounded classifier result19/24; do not conflate with new36sample |
| Later HTTPX arm |49/40|36 (90% determinate;73.5% of assigned)|1blocked;3temporary;9unknown|20/36 (55.6%) |
| Native curl without impersonation |47/41|0|37blocked;1temporary;3no-catalog;6unknown|None |

The deployed merchant path is the existing curl-cffi configured transport; worker HTTPX calls delegate to Web. Neither local HTTPX nor native curl without the deployed configuration establishes Render merchant yield. No new merchant request or transport evasion was performed. The favorable assigned-sample combined usable yield is20/49=40.8%; adverse combined planning sensitivity24/248×20/36=5.38% mixes samples and is explicitly a model, not an observed joint rate. Zero yield remains possible if production transport is blocked. HTTPX completed outcomes used138logicalrequests/36catalogs=3.83; earlier controlled768/24=32.0. Redirect wire requests add to logical endpoint counts.

Retries retain exponential cooldown: temporary failures start1hour; blocked/password/no-catalog/unavailable24hours; capped7days plus deterministic jitter; definitive terminal states30days. `Retry-After` can require longer. Reverification is due after53days, with60-day Discovery freshness expiry. Retry budget does not imply retries recover a store.

Historical Render samples, September11 12:00–16:00 UTC at600s resolution:

| Service | Sampled memory | Sampled max CPU | Interpretation |
|---|---:|---:|---|
| Web |177.3–509.4MiB /512MiB|0.0868core|Very little headroom at peak; decline is not proof of an OOM |
| Worker1 |455.3–471.2MiB /512MiB|0.0168core|Concurrency2 consumes most RAM; no basis to raise it |
| Beat |91.2MiB /512MiB|0.000066core|No resource-upgrade evidence;21samples, instance count0–1 |

These are sampled history, not an idle-vs-batch experiment or proof of no restarts/OOM. Files `*-memory-history.json` retain raw metric metadata. Recommend measuring a bounded restored workload at concurrency1 versus2 before any capacity purchase; do not change settings now. Diagnose Web response/catalog retention before buying capacity. Beat has no demonstrated upgrade need.

Load budget: roughly3DBoperations per existing-domain verification (read, conditional claim, conditional finish), plus1perclassification and batch-selection/run/heartbeat writes; extra operations for missing domains or uncertain delivery. Domain pacing contributes about2Rediscommands/attempt; stage ownership adds about1renewal/dispatch plus acquisition/release and timed heartbeats. At9,600attempts/day this is order30kRediscommands/day excluding Celery/AI/customer traffic, not a measured Redis total. At the planning37,877-domain scenario, core verification/classification is roughly191,660DBoperations plus overhead over the run, not per day. Payload size, query latency and Redis tail latency remain canary measurements. No production load test was run.

Free classification costs$0 and CPU is fast in memory. Production currently chooses AI when a key exists; no paid execution is authorized by this report. Classification plus uncached DNA can make two model calls, with220+500output-token limits. At an illustrative2,000combinedinputtokens and720outputtokens, standard Haiku4.5 pricing gives$0.0056/pair before retries. Actual prompts, latency and bills were not measured. Source: [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing), checked September19 ($1/$5 per million input/output). Paid pair latency5/15/30s would make100-row serial batches last8.3/25/50minutes: scheduled throughput roughly7,200/3,600/2,400classifications/day absent other contention. Paid AI is a possible next bottleneck, not a proven requirement for every store.

## 4. Expansion scenarios, with explicit assumptions

[Executable capacity model](../../../tests/evaluations/index_growth_capacity.py) and [full scenario data](capacity-scenarios.json). Planning illustration:40%verification success ×60%classification pass=24%newusable per distinct domain;0.5additionalverificationattempts/domain; one extra classification attempt for low-confidence rows, with no recovery yield credited. These are assumptions between incompatible observed samples, not a forecast or confidence interval.

| Distinct domains processed | Raw verification attempt budget | Verified first pass | New usable first pass | Classification attempt budget | Capacity-equivalent days at50–100% of schedule |
|---:|---:|---:|---:|---:|---:|
|1,000|1,500|400|240|560|0.16–0.31|
|5,000|7,500|2,000|1,200|2,800|0.78–1.56|
|10,000|15,000|4,000|2,400|5,600|1.56–3.12|
|25,000|37,500|10,000|6,000|14,000|3.91–7.81|
|37,877|56,816|15,151|9,090|21,212|5.92–11.84|

Calendar completion is longer if cooldowns, low-confidence daily retries, lease skips or stalls dominate. A24hour retry cannot finish in0.16days. The last column measures slot consumption, not a hard wall-clock completion bound. First-pass-only capacity for37,877 is3.95–7.89days at these assumed utilizations. Sustainable production throughput remains unmeasured; current inert pipeline throughput is zero.

For37,877domains the adverse sensitivity yields~2,036usable; planning~9,090; favorable~15,460. None supports a claim of25kusable from this backlog. Counts can also include true hostname aliases, so unique-business yield may be lower. No identity merging is performed without evidence.

Targets starting at the actual34eligible snapshot, without credit for stale-store recovery:

| Total usable target | Distinct domains needed (planning) | Verification attempt budget | Capacity-equivalent days | Fits37,877backlog? |
|---:|---:|---:|---:|---|
|1,000|4,025|6,038|0.63–1.26|Yes, conditionally |
|5,000|20,692|31,038|3.23–6.47|Yes, conditionally |
|10,000|41,525|62,288|6.49–12.98|No under planning yield; favorable needs~24,417 |
|25,000|104,025|156,038|16.25–32.51|No; even favorable needs~61,167 |

Reverify the320stale stores in the preserved renewal lane, measure new verified→usable yield, then progressively consume existing resolved domains. If more domains are needed, resolve the260,458existing unresolved references rather than acquire another candidate dump. Resolution itself has historical failures and duplicates; its7,200/day default reference-attempt ceiling is not7,200newdomains/day. Larger targets are not asserted achieved.

## 5. Discovery supply experiment — unchanged retrieval/ranking

The original25-business panel/reference judgments and baseline are untouched. Tables report24core businesses; the off-platform control remains separately recorded. P@10 uses10slots although this endpoint returns at most8. Newly encountered27result placements were explicitly adjudicated against captured public product evidence, in [new judgments](new-judgments.json). Single-analyst supplemental judgments are not a new independent blind panel. Previously unknown labels remain unknown.

| State / description-only | Eligible supply | P@5 | P@10 | Reference recall | Useful-result rate | Wrong-result rate | >=3useful top5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original audit |403fresh/catalog baseline|28.3%|15.8%|4.2%|25.7%|38.5%|7/24 |
| Reviewed frozen replay |384|30.83%|17.08%|4.17%|49.40%|14.46%|7/24 |
| Controlled captured supply |365|29.17%|16.25%|4.17%|48.75%|12.50%|5/24 |
| Expanded captured supply |384|30.83%|17.50%|4.17%|47.73%|13.64%|5/24 |
| September19production snapshot, reviewed gates |34|9.17%|4.58%|4.17%|47.83%|21.74%|0/24 |

| Structured profile | P@5 | P@10 | Useful rate | Wrong rate | >=3useful top5 |
|---|---:|---:|---:|---:|---:|
| Frozen |33.33%|18.33%|47.83%|11.96%|8/24 |
| Controlled365 |31.67%|17.08%|45.56%|10.00%|6/24 |
| Expanded384 |32.50%|18.33%|44.90%|11.22%|6/24 |
| Current34 |9.17%|4.58%|61.11%|16.67%|0/24 |

Reference recall is2/48 in every state/mode. **100/100 frozen and controlled result lists remain identical to the prior reviewed implementation**. Controlled→expanded uses the same cutoff and same code; only measured catalog/classification outcomes change. Frozen384 and expanded384 are different memberships, not interchangeable samples. Current34 is a later production snapshot, not a controlled growth treatment. Its export includes only411verified rows; missing reference records mean absent from that export, not necessarily absent from the full production index.

The19net eligible additions improve skin-tint/SPF results (three description-mode cases each gain one useful top5 result). They also introduce adult intimate-care products into three infant-skincare cases, and a broad skincare retailer displaces a more useful top5 result in the ColourPop case (P@5 1.0→0.8 in both modes). Zero-result core searches decrease5→2, but zero-useful searches stay9description/8structured. This is a concrete example of why zero-result reduction alone is insufficient. Hiking and keyboard niches remain catastrophic. Current34 has15/24zero-result and18/24zero-useful cases. [Case/niche deltas](niche-results.json).

Discovery remains Weak. There is no measured1k/5k/10k/25ksupply checkpoint. No fake stores, retrospective freshness changes or invented relevance labels were used to reach one. The replay tooling can measure the next real snapshots; it must not extrapolate P@5 linearly from index size. Next quality work should address these general product-intent failures after sustainable supply is measured, not alter rankings to hide the coverage experiment.

## 6. Smallest practical restoration path — not executed

The minimal in-place route still needs the reviewed lifecycle schema and a reviewed verifier runtime; simply restoring Worker/Beat would call the legacy Web verifier and repeat the alias problem. This branch's classification projection fix is also required before releasing knowledge work. Production's AI-primary path needs an explicit cost/free-mode decision before unattended classification.

Reuse the already validated maintenance entrypoints, pins, Redis/lease work and fail-closed hold. Do not redesign the observer or add another fence. For the existing shared table, the unresolved legacy Web completion risk has not vanished: a hidden request executor can still write later. Render support's pending answer or a separately approved change in accepted migration/cutover risk is needed before following that in-place production plan. No fixed wait or quiet queue is substituted as proof.

The concrete smallest next production action in that plan is an **approved Web ingress-containment/maintenance cutover**, followed by the reviewed lifecycle migration and new exact release deployment under hold, then a separately approved bounded verification/classification sample. It is not a Worker Resume toggle. Until the legacy-work risk is resolved or explicitly accepted, this report does not authorize that action or claim deployment readiness.

An alternative can restart isolated index processing without using the legacy Web route: run the reviewed verifier/classifier in an index-only process against a **separate lifecycle table/schema with credentials unable to write the legacy index/customer tables**, seeded from a read-only backlog snapshot. Reuse the lifecycle module through an explicit table adapter, keep acquisition off, and use a private read-only shadow Discovery endpoint for the same benchmark. This avoids changing the old Web/table while it may still contain work. It requires a new additive schema/role, small runner/adapter, isolated queue/configuration and a separately reviewed release; it has NOT been implemented or validated here. Starting a new worker against the same table with a direct verifier alone does not solve mixed-writer safety. Publishing shadow results into the existing customer API remains a separate approved cutover.

Recommendation: use that isolated shadow option if support cannot promptly clear the existing shared-table cutover; do not spend another session on observer attachment. It adds deployment work but separates index progress from the unresolved legacy executor. Neither option requires broader raw acquisition, frontend redesign, plan upgrades or relaxing evidence standards.

What can wait: new acquisition, paid classification tuning, ranking changes, higher concurrency, paid plan upgrades, legacy UI cleanup and broad telemetry. What cannot: compatible schema/runtime, owned claims and fail-closed holds, an explicit paid-AI policy, no mixed unguarded writers to the target table, and a measured small batch before continuous growth. Canary execution remains disabled and separately authorized.

## Reproduction and evidence

`tests/evaluations/index_growth_retrieval.mjs` executes the retained75PostgreSQL retrieval channels in local PGlite; `index_growth_benchmark.py` replays the unchanged endpoint; `index_growth_measure.py` uses captured catalog rows plus response evidence with network and paid-AI calls forbidden; `index_growth_capacity.py` emits all scenario assumptions. Use Python `-X utf8` on Windows. The local sibling `storescout-phase1` holds prior captures/PGlite/venv; [input hashes](provenance.json) identify exact source artifacts. New artifacts live here and `outputs/index-growth`; prior artifacts were not overwritten. Stored replay summaries omit full request/response payloads; current index export contains public merchant classification/catalog fields only.

Commands: `node tests/evaluations/index_growth_retrieval.mjs`; run `python -X utf8 tests/evaluations/index_growth_benchmark.py VARIANT` for frozen/controlled/expanded/current; then the measurement and capacity scripts. Full backend `python -X utf8 -m pytest -q`; frontend `npm test -- --reporter=dot` and `npx tsc --noEmit`. No production credentials are needed by these offline commands.
