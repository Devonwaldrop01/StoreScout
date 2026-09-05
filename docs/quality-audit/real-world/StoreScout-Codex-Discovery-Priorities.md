# StoreScout: measured Codex discovery priorities

5 September 2026. Preserve `ff555bb2842a05f55dcc83403bfef80bc7eb17cf`. This addendum supersedes the measurement blocker and priority order in the existing implementation specifications; their detailed behavior and regression constraints remain applicable. No application implementation or production processing is authorized by the completion of this measurement.

The measured local release candidate remains **Weak**: core P@5 28.3%, P@10 15.8%, three-useful coverage 7/24, wrong results 57/148. Structured notes leave P@5 unchanged and increase wrong-result rate to 41.3%. Sixty percent of the original 50 reference relationships are absent, 32% unverified, 4% catalog-gated and 4% returned. These are first-blocker counts, not independent treatment-effect estimates.

## 1. Restore usable supply through verification and renewal

**Expected impact:** highest on known-competitor recall and breadth. The real index contains 37,411 unprocessed records; 156/177 sampled discovered stores already expose readable catalogs. Eight distinct known-reference brands exist unverified and currently expose catalogs. Acquiring more domain names alone will not make those businesses discoverable. Another 320 verified records approach the 60-day cutoff within seven days of the frozen baseline.

**Root cause:** domain collection, catalog verification and usable evidence are not the same pipeline outcome. Exact free-text catalog-signal requirements disagree with tracked-store ingestion, excluding 23 otherwise verified records, including Parachute. Recent verification does not renew old product knowledge.

**Components:** `app/services/store_index.py`, `app/tasks/store_index.py`, `app/services/discovery_sources.py`, catalog ingestion from tracked scans, verification contract in `app/services/discovery_quality.py` and `app/api/v1/competitors.py`, index schema and Celery scheduling definitions. Design locally; do not activate production schedules or migrations.

**Desired behavior:**

- Make existing backlog processing bounded, retryable, idempotent and observable by status, queue age, attempt outcome and successful catalog count. Allocate fairly across age/source/category gaps; prevent repeated easy-category processing from starving unclassified stores. Separate collection from verification throughput.
- Unify a typed, dated successful-catalog observation across tracked and discovered ingestion. Platform markers or a high verification score alone do not prove monitorability. Retain explicit unavailable/password/challenge/empty states and last successful evidence on a failed retry.
- Plan renewal volume from the measured cohort, with rate/cost limits. Observe attempted and successful revalidation separately; do not silently extend successful evidence timestamps.
- After measuring existing-backlog yield, target remaining product-family supply gaps. Do not seed the evaluation references or use business-specific allowlists to manufacture benchmark gains.

**Regression risks:** retry storms, external request costs, reintroducing blocked storefronts, recording an attempted scan as success, losing prior successful facts on transient errors, and improving nominal verified totals without useful product coverage.

**Tests and benchmark cases:** isolated queue/worker tests for retries, idempotency, fair progress, and renewal; typed evidence parity for tracked versus discovered ingestion; HTTP 402, challenge, password, empty and changed catalog fixtures. Cases: all three bamboo businesses, Tubby Todd, ILIA, Gossamer Gear, Counter Culture, Brooklinen/Parachute. No fixture may substitute benchmark brand identity for successful evidence.

**Measurable acceptance:** every replay-known present reference has an auditable processing/eligibility outcome; all eight currently readable unverified reference brands pass the same generic local verification contract when fed their saved successful observations, or expose an explicit defensible rejection. Parachute’s successful-catalog fixture is eligible while marker-only and stale fixtures remain ineligible. All 320 approaching-expiry records have a deduplicated, bounded renewal plan in a local dry run. Report backlog age and successful catalogs per attempt separately. Any production throughput target requires an approved worker/rate budget; do not promise index-wide processing duration from the sample.

## 2. Retrieve and compare actual products before tuning numeric rank weights

**Expected impact:** highest on wrong-result rate and recovery of useful stores already in the eligible index. This combines the prior shared-product-concepts and substitute-versus-modifier specifications. Supply work cannot fix a paddleboard returned for a keyboard.

**Root cause:** retrieval does not directly search observed product titles/types. JSONB DNA is queried with an unsupported overlap operator, disabling that channel. Flat terms admit shared modifiers, packaging words and category words as product matches. Nonempty but uninformative observed fields can suppress richer contextual evidence. Ranking and filtering inherit these problems.

**Components:** `app/api/v1/competitors.py`, `app/services/discovery_quality.py`, `app/services/store_dna.py`, classification helpers in `app/services/store_index.py`; a small versioned product-concept/evidence adapter; optional local schema/query changes supported by read-only query plans.

**Desired behavior:**

- Use compatible JSONB predicates or a deliberately migrated typed representation; preserve OR-overlap semantics and null/empty behavior. Verify against real PostgreSQL, not only mocked arrays. Inspect existing indexes/query plans before selecting a migration. Keep failures observable rather than silently dropping a channel.
- Retrieve from observed product titles/types and normalized product concepts in addition to category and lexical context. Keep channel ranks/provenance and merge compatible rich fields. Broad or incorrect category labels must not be the only route to a product.
- Represent product head, form, material/process, use case and audience separately. Require defensible product substitution for strong fit. Modifier-only matches (`printed`, `ultralight`, `low-profile`, `tint`, `pack`, `roast`) cannot alone establish fit. Category tokens added by inference are not independent product evidence.
- Treat `PHYSICAL`, opaque names and absent materials as weak observed evidence. Combine sufficiently supported DNA/description context with observations, preserving provenance; do not blindly let any nonempty product list disable informative context. Contradictory current catalog evidence must win over stale narrative.
- Normalize conservative spelling/plural/phrase variants and French coffee terms with explicit tests. Do not equate all baby products with baby skincare, all bags with ultralight packs, or all pet treats with freeze-dried dog treats. Price and shipping remain unknown until comparable evidence exists.
- Keep related competitors with explicit limitations; do not pad empty results with unsupported matches. Tune weights only after a paired trace identifies residual rank-order errors.

**Regression risks:** substitutes confused with complements, baby/adult or dog/cat intent widened, special materials/processes ignored, broad retailers displacing close specialists, expensive unbounded database predicates, and global keyword changes affecting other features.

**Tests and benchmark cases:** real-schema JSONB integration tests for nonempty/null/empty values; HyperX mechanical keyboards visible despite Audio category and generic description; Babysprouts opaque titles plus bamboo sleep evidence; Terra Moons `PHYSICAL` plus eyeshadow evidence; Parachute catalog contract; Lheureux accent/language fixtures. Negative cases: trading-card packs for Durston, denim for Zpacks, Hydrus for NuPhy, window tint for ILIA, car parts for Birdie Bean, meat/hot sauce for coffee. Preserve observed versus inferred evidence provenance and own/tracked exclusions.

**Measurable acceptance:** zero DNA operator failures in replay; HyperX reaches the candidate union for Keychron and EPOMAKER from generic product evidence; supported Babysprouts and Terra Moons evidence survives meaningful-product filtering. The named unrelated hard negatives do not reach top five. Eligible-and-present independently useful retrieval recall ≥90%, with the denominator and per-channel misses published; the current 2/2 reference denominator is insufficient on its own, so report the separately identified diagnostic candidates too without adding them to known-reference recall. Meet global and niche gates below; do not claim success solely from these targeted fixtures.

## 3. Revalidate product identity, improve classification and establish canonical evidence

**Expected impact:** prevents incorrect/stale facts from defeating improved retrieval and restores trustworthy category coverage. Four of 46 reviewed verified stores had clearly wrong broad categories despite high confidence. A high-confidence bedding domain now sells hobby acrylic sheets. There are 138 www/non-www collision groups, but no measured returned-duplicate problem.

**Root cause:** platform verification, product classification and domain identity age independently; heuristic confidence is not calibrated truth. Exact-domain uniqueness is not canonical merchant identity.

**Components:** `app/services/store_index.py`, `app/tasks/store_index.py`, `app/services/discovery_sources.py`, catalog evidence schema, canonical/domain normalization and discovery filtering. Continue the lifecycle details in the prior specification.

**Desired behavior:** record successful platform/catalog checks separately from classification time, version and source signature. Reclassify on meaningful catalog/identity change; allow multiple supported product families for broad stores. A failed request must not rewrite historic facts as current. Treat confidence as a heuristic with source evidence and an unknown state. Establish canonical aliases from redirects/shop/catalog evidence; preserve regional stores with materially different catalogs or currencies.

**Regression risks:** category churn, erasing valid broad-catalog products, merging distinct regional storefronts, treating bot protection as dead, and silently trusting stale DNA after a storefront changes.

**Tests and benchmark cases:** Fashion Nova, Spigen, Kinugawa Turbo and Benchmark Abrasives broad-category fixtures; smile-cleanworks.com changed-identity case; synthetic regional aliases plus measured www collision fixtures; transient 403/502 and password responses. Bedding and keyboard cases must expose the distinction between correct product retrieval and broad taxonomy.

**Measurable acceptance:** the four reviewed category contradictions have correct or explicitly uncertain outcomes from generic evidence, and changed storefront fixtures invalidate stale product claims before discovery. No fixture refreshes classification merely because access succeeded. Every proposed alias merge has evidence and no unrelated regional catalogs merge. Re-review the fixed 46-row sample and publish a confusion table/unknown rate, not a fabricated probability calibration. Canonical collision cleanup is subordinate to supply/product-fit work because no returned duplicate loss was measured.

## 4. Preserve intent and identity, then make sparse results honest

**Expected impact:** improves robustness and recovery without assuming richer profiles solve quality. Current structured notes do not improve core P@5. Little Sleepies fails with HTTP 500 when no evidence-qualified result survives; Tower 28 can return itself with empty own-store context.

**Root cause:** profile notes and inferred categories join product tokens without a clear intent contract; own-store identity may be absent; zero qualified results are treated as a generic endpoint failure.

**Components:** onboarding/business-profile and competitors-page components from the existing route inventory; `app/api/v1/competitors.py`; `app/services/discovery_quality.py`. Do not redo the source inventory.

**Desired behavior:** retain explicit product focus, distinguish facts from broad brand notes, and support optional normalized own-domain identity without requiring OAuth or guessing from brand-like words. Preserve the original typed input. Return an explicit recoverable insufficient-evidence outcome when no qualified candidates exist, with manual review/add and clear access/context limitations. Maintain one fit/evidence contract for graph/index/AI paths when those paths are implemented; paid AI remains unmeasured. Fit explanation UI stays deferred until supporting evidence is demonstrated. Preserve the existing quota-on-failure requirements rather than reopening completed billing work.

**Regression risks:** silently changing Quince’s broad versus bedding intent, overexcluding unrelated stores with similar names, mandatory integration friction, and rewarding sparse outputs by hiding the missing-result denominator.

**Tests and benchmark cases:** description versus existing structured input paired replay; Quince focus-change and selected paraphrases as separate diagnostics; Tower 28 with and without explicit own-domain context; Little Sleepies recoverable empty-state behavior; no unsupported audience, efficacy, currency or shipping claims.

**Measurable acceptance:** original input survives failure, the no-qualified-results path is explicit and does not produce the current generic HTTP 500, own-domain context prevents self recommendations, and missing identity remains reported. Structured mode must meet the same product-quality gates with no niche P@5 loss >0.10 and no case losing more than one useful top-five result without review. Website enrichment and paid AI must be labelled and evaluated separately.

## Deferred work and reasons

Per-channel newest-200 truncation and first-eight lexical-term truncation caused **zero measured losses** in this panel: largest actual channel was 118 and primary queries used at most eight terms. Keep deterministic tie-breaking and cap-boundary regression cases, but do not prioritize an expanded candidate limit as the cure for this baseline. Semantic/embedding infrastructure, new explanation UI, integrations, broad regional expansion and calibrated probabilities need additional measured benefit/cost evidence. New raw-domain acquisition follows backlog yield and targeted coverage gaps; it is not eliminated, because 60% of known-reference relationships are absent.

## Required release comparison

Keep the saved reference panel, original query strings and frozen source/index snapshots. Report both input modes and Stewart separately. Retain every returned and rejected candidate with its evidence and stage, and use the unchanged label rubric. Public observations captured now must not overwrite the original database baseline.

The existing gate remains: core description-only macro P@5 ≥60%; ≥80% of searches with at least three distinct useful top-five competitors; ≤10% wrong and ≤5% unknown returned placements; each multi-case niche at least two-thirds passing three-useful coverage; independently useful eligible-present retrieval recall ≥90%. Publish P@10 and P@8, strong-only precision, known-reference coverage/recall, all case regressions, both input modes and family-weighted means. These are early pilot gates, not proof of market-wide quality.

The panel has now been inspected during diagnosis. Do not call any of it an untouched blind holdout. Freeze whole-family tuning/evaluation partitions before implementation, preserve the saved protocol, and obtain independent relevance adjudication before declaring Acceptable. Do not redefine reference truth, add business-specific exceptions, or report projected gains as measurements. This task does not authorize a new replacement panel, paid AI runs, production processing, migrations or deployment.
