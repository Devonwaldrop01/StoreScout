# Discovery: real-world measurement and implementation specifications

Checkpoint: 2026-09-05. Preserve `ff555bb2842a05f55dcc83403bfef80bc7eb17cf`.
No application changes, production queries, model calls or old tests were performed in this pass.
`reference-panel.json` is independent research preparation, **not a completed benchmark**.
All metrics remain null until a real index export and faithful replay are available.

## P0 measurement prerequisite — read-only index snapshot and replay

**Blocker:** Supabase was successfully connected during this pass, and plugin discovery confirms it is installed. However, the active session exposes no Supabase project-listing or SQL-query tool; both tool metadata and callable-name discovery were checked after connection. No production index snapshot is present. Existing Render access does not supply database read access. Do not expose Render secrets or call production `POST /competitors/discover-ai`: it consumes quota, writes index/graph state, may enqueue jobs and invokes paid AI.

**Components:** `docs/quality-audit/index-health-readonly.sql`, `real-world/index-export-readonly.sql`, `app/api/v1/competitors.py::discover_ai`, `app/services/discovery_quality.py`, `app/services/store_dna.py`, `app/services/store_index.py`, settings.

**Desired behavior:** use a database-enforced read-only transaction/role where available, record schema, actual nonsecret index settings, transaction timestamp and all public index rows. Export only catalog/business fields listed in the companion query. No customer profiles, user IDs, credentials, contacts or private integrations. Stable domain ordering, complete pagination, row count reconciliation and a hash are required. If a stable transactional export is unavailable, record start/end times and detect concurrent row changes rather than claiming an atomic snapshot.

Replay the current endpoint against a faithful local query adapter, not a scorer-only fixture. Preserve Postgres `ILIKE` and array-overlap behavior, descending timestamp ordering (including nulls and ties), limits, projections, schema fallback, deduplication, category classification, input normalization, default settings, freshness gates and final exclusions. Stub every mutation to raise if invoked; disable model, verifier, queue and outbound HTTP before imports/calls. Extracting a pure orchestration seam is permitted locally only after output parity is demonstrated against the frozen code on the same snapshot. Never silently replace missing columns with invented evidence.

Run two separately named baselines: (a) description-only, empty profile/graph/tracked set, index-only; (b) explicit structured business input from independently researched facts. A public website URL alone does not mean the endpoint crawls that website. Do not populate production with benchmark merchants. Production's last known revision differs from ff555bb; this is a proposed local release baseline, not proof of live behavior. Paid-AI-assisted discovery remains separately unmeasured unless a previously saved response exists or permission is granted for an isolated paid run.

**Trace per request:** literal query → category and confidence → normalized retrieval terms → ranking context and truncation → rows returned by each channel, query errors and schema fallback → dedup/projection selection → eligibility exclusions → ranking components → top eight index results → final displayed list. Save every known reference's status: absent from snapshot / ineligible / not retrieved / retrieved but projected evidence lost / ranked below cutoff / excluded as own/tracked/rejected. Preserve null versus missing versus empty values.

**Regression risks:** a Python simulation that differs from Postgres can manufacture gains; changing the clock alone can eliminate stores; local defaults may differ from configured thresholds; rows tied at limit 200 are nondeterministic without a tie-break; refreshed evidence must not overwrite baseline evidence.

**Acceptance:** export count reconciles exactly, all hashes pinned, 25 cases have explicit execution status and stage traces, all top-ten returned domains have blind evidence labels or an explicit unknown label. Zero database mutations, paid calls, queue submissions or external verifier calls during replay. A blocked case is not a zero-result case. Reconcile legacy schema fallback separately.

## Index health protocol (execute only after access)

Report census denominators separately: all rows, pipeline-verified rows, fresh monitorable-eligible rows, classified rows, and rows actually returned by discovery. A pipeline `verified` flag is not an independently verified Shopify rate.

Measure missing/null/empty title/type/DNA/description/category/audience/price/currency fields; category and niche distribution; confidence histogram and uncalibrated/null confidence rate; verification and knowledge age buckets (0–7, 8–30, 31–60, >60 days, missing, future); source distribution where recorded; exact normalized duplicates. Latest timestamps show last recorded work, not a complete update history. If no observation history exists, say so.

Select an independently reproducible stratified sample of up to 240 domains across category × status × age, including failed and unclassified strata, seeded by a recorded hash. Retain inclusion probabilities and weight estimates by population stratum size; an equal-five-per-category sample is not an unbiased overall active-rate estimate. Inspect all benchmark top-ten results and known references separately as a deliberately selected relevance sample, not a population sample. If fewer than 240 rows exist, inspect the census. Report count and uncertainty per stratum; zero checked means unknown. Retry timeouts once in a later observation window before calling a domain dead.

Public checks should distinguish DNS/TLS/HTTP failure, bot challenge, accessible storefront, Shopify evidence, readable nonempty catalog, password page, domain-for-sale/parking, trade-only purchase restrictions, and redirected/rebranded domains. A 403 is inaccessible, not proof of non-Shopify. A wholesale link is not wholesale-only. A WordPress marketing frontend may coexist with Shopify commerce. Preserve final domain and canonical hints, compare catalog/shop identity before merging; regional storefronts may share a brand and still differ in currency/catalog. Do not bypass passwords/challenges or modify index statuses.

Rate-limit public checks, bound body size/time/redirects and reject private-network destinations at every hop. Use approved read-only network surfaces. Save observations locally without feeding results into production.

## Metrics and proposed Acceptable gate

Labels: 3 strong competitor for stated product/use case; 2 useful partial competitor with an explicit limitation; 1 weak/adjacent; 0 obviously wrong; unknown insufficient evidence. Reference labels in the panel are provisional analyst judgments, not merchant endorsements. Independently label shuffled returned domains without source/score/rank shown, then restore rank. Adjudicate ambiguous cases before issuing a quality verdict. Platform eligibility is a separate label.

* P@5 and P@10: number labelled ≥2 divided by 5 or 10, respectively, padding missing ranks with zero. Also report strong-only precision (label 3). The index currently targets eight, so index-only P@10 has a maximum of 0.8; publish P@8 as a diagnostic rather than hiding this cap.
* Useful-result rate: useful / returned, alongside returned counts; never let returning one good result look equivalent to returning five.
* Obviously-wrong rate: label 0 / returned, plus percentage of searches with a wrong top-five result. Report unknown-label rate separately; unknown is neither proved wrong nor useful.
* Known-competitor recall@10: matching known references / independently known references. Also show eligible-and-present recall and retrieval recall to separate coverage, verification and retrieval. This partial reference set cannot measure complete market recall.
* Three-useful coverage: searches with ≥3 distinct useful canonical competitors in top five / all executed searches; errors and empty outputs count as failures. Report blocked requests separately and withhold launch conclusions if any required case is blocked.
* Report per case, niche and difficulty slice, plus family-weighted macro averages. Related brands in a trio are correlated: split/hold out whole families, not one query from each trio. Do not tune on all cases; reserve at least two whole families for final evaluation. Alternate wording is a paired robustness diagnostic, not an extra independent business. Quince's focus change is a different intent, not a paraphrase.

**Proposed decision criteria, not achieved measurements:** core description-only macro P@5 ≥0.60, at least 80% of cases with three useful top-five competitors, ≤10% obviously wrong returned results and ≤5% unknown labels; every multi-case niche has at least two-thirds of cases with three useful top-five competitors. No individual case loses more than one useful top-five result without review; no niche's macro P@5 drops >0.10. At least 90% retrieval recall among independently useful, eligible, present references. Review all remaining top-five wrong results and holdout families before declaring Acceptable. Price/audience hard-negative cases must be included in this review. These are early pilot gates, not statistical proof of market-wide quality; confirm with real users. The Stewart platform-uncertainty control is reported separately, leaving 24 core cases.

## P1 — product concepts shared by understanding and retrieval

**Root cause:** index retrieval uses first eight literal normalized description terms against category/subcategory/description/brand and exact DNA array overlap. Product title/type text is ranked later but is not directly searched by those lexical retrieval predicates. Per-channel newest-200 truncation can discard relevant older rows. Ranking aliases cannot rescue candidates that never reach ranking.

**Files:** `app/api/v1/competitors.py`, `app/services/store_dna.py`, `app/services/discovery_quality.py`, classification helpers in `app/services/store_index.py`; a small versioned product-concept module and migration only if evidence demonstrates need.

**Desired behavior:** represent product head, form, use case, material/process, audience, exclusions and optional price constraints separately with provenance. Derive from explicit user wording and observed product evidence. Match the same normalized concepts on both sides. Begin with auditable, broadly valid taxonomy/spelling relations and multiword phrase handling, not domain-specific exceptions or embedding infrastructure. Unknown concepts remain unknown. Preserve original text and version mappings. Do not infer dog from chicken alone, raw from any treat, tent from every shelter, or eczema efficacy from a generic balm.

Retrieve independently from normalized product concepts/title/type evidence, category and lexical metadata; combine with stable tie-breaking and bounded deterministic pagination. Avoid a hard newest-200 popularity/freshness ceiling swallowing the long tail. Only add a database search index/migration after a read-only query plan on realistic size demonstrates need; local migration design does not authorize production application. Preserve original channel ranks/provenance. Merge richest compatible fields for duplicate retrieval hits instead of letting a lean category projection erase full metadata. Consolidate schema fallback so a missing DNA column does not lose all observed product evidence.

**Regression risks:** expansion confuses complements with substitutes, changes medical/cosmetic intent, broadens pet species, or makes general stores dominate. Large unbounded OR queries threaten latency. Alias changes affect non-discovery users of `normalize_keywords`.

**Cases:** shelter/tent versus backpack; raw meat treats versus storage jars and cat treats; unscented balm versus scented cosmetics and baby/adult care; wearable blanket versus pajamas; keyboard versus keycap; whimsical coffee blend titles; broad Quince profile versus its bedding focus; relevant row beyond position 200; incomplete metadata and schema fallback.

**Acceptance:** baseline frozen first; eligible-known retrieval recall ≥90%; per-niche gates above; no audience/species contradiction introduced by expansion; traces show concept evidence and losses at each cap. Evaluate originals and paraphrases with family holdout. Do not claim improvement from a two-row hand-built example.

## P1 — distinguish substitutes from shared modifiers before tuning rank

**Root cause:** flat token sets treat a product head, adjective and accessory mention alike. Fractional query coverage dominates; audience only adds positive overlap and does not represent explicit incompatibility. Price tiers may derive from mixed product prices. Nonempty overlap is the final product-fit gate. Ranker-only fixes cannot address retrieval loss.

**Files:** `app/services/discovery_quality.py`, discovery response assembly; normalized evidence adapter from the preceding spec.

**Desired behavior:** explicit substitute / related / accessory / unknown relations based on observed product forms and use cases. Require matching product intent for strong fit; preserve related fits with limitations. Apply negative audience/geography/price constraints only when both sides have reliable evidence. Compare matched-product price bands in the same currency/unit/pack size and time window; never use store-wide median to conclude parity. Missing price or audience must remain unknown. Do not use verification score as a relevance score or confidence probability.

**Regression risks:** overly strict form matches hide legitimate substitutes; broad catalogs get unfairly penalized for breadth; price gaps can be commercially relevant even when not direct equivalents. Inferred audience is not an explicit hard constraint.

**Acceptance:** reduce baseline wrong-result rate while meeting every niche gate; separately reduce accessory-only and incompatible-audience top-five results; show measured price positioning only for validated comparable samples. No new numerical weights before stage-error analysis. Keep the previous scorer available for paired comparison.

## P1 — lifecycle evidence and stale classification

**Root cause:** a freshness gate exists, but the prior audit found no scheduled continuous revalidation path for all verified stores. Exact-domain uniqueness is not canonical identity; historical platform verification and classification can outlive the storefront. Confidence is heuristic, not calibrated against human labels.

**Files:** `app/services/store_index.py`, `app/tasks/store_index.py`, `app/services/discovery_sources.py`, Celery schedule, index migrations.

**Desired behavior:** independent fields for last attempted probe, last successful catalog observation, platform evidence, access state and classification version/time/source signature. Failed retries retain prior facts with age; they do not manufacture a new successful timestamp or permanently mark a bot challenge non-Shopify. Reclassify only when meaningful product evidence changes or a version changes. Canonical aliases require redirect/shop/catalog evidence; regional aliases remain separate when inventory/currency differs. Queue failures must remain retryable instead of advancing cursors on failed inserts.

**Constraints:** do not blindly grow the index, delete records or schedule paid/infrastructure work. First derive coverage gaps and renewal volume from the real census; document cost and get approval for production changes.

**Acceptance:** every stale eligible record has an observable renewal path, access failures cannot overwrite fresh successful evidence, and duplicate/canonical cases have provenance. Stratified independent valid/catalog-access rates and classification confusion tables improve versus the same frozen sample. No numeric improvement can be promised before baseline.

## P1 — end-to-end interpretation, consistency and empty states

**Root cause:** submitted description, optional profile and own-store category can disagree. Keyword limits and unstructured brand traits can crowd out actual products. Index recommendations and AI proposals do not pass the same evidence ranking. The current displayed reason is often a store summary; verification confidence is not fit confidence.

**Files:** onboarding/profile components, competitors page, `app/api/v1/competitors.py`, `app/services/discovery_quality.py`. Find exact components from the existing route inventory before editing.

**Desired behavior:** preserve typed description and distinguish explicit intent from inferred category. A broad store may need a selected product focus; do not silently decide that its first recognized category is its entire business. Do not add a mandatory integration. Apply one evidence contract and fit gate to index, graph and AI-suggested candidates. An unavailable model should leave honest index-only results, not silently imply complete competitor coverage. Zero/few results should explain insufficient evidence/access versus no competitors; retain user input and offer manual review/add. Fix quota-on-failure separately under billing reliability scope.

**Explanation decision:** no new explanation UI yet. First measure whether top results have attributable product evidence, correct source/date and defensible audience/price facts. `matched_terms` alone does not justify “same audience” or “similar prices.” Prototype evidence snippets only after ≥95% of a reviewed explanation sample is directly supported. Conduct a small task test: can the user accept/reject competitors and state the reason correctly? Record time to three accepted competitors, rejection reasons, empty-result recovery and successful add/first scan. No analytics of raw private descriptions needed.

**Acceptance:** descriptions survive errors; each result's pathway and fit evidence can be audited; no unsupported price/audience claims; first-value workflow works without OAuth. Website-enriched results are labelled as separately available context. Manual competitor validation still must prove catalog access, not rely on recommendation labels.

## P2 — later work only after measurement

Semantic retrieval beyond an auditable concept layer, calibrated probability estimates, broader regional/category coverage, live AI-assisted benchmark runs, new explanation UI and new integrations remain conditional. Propose them with measured misses, cost/latency and holdout benefit; do not build them just to make the product appear sophisticated.
