> **Measured resume update — 5 September 2026:** Supabase read/query access now works; the index census and 25-business real-data replay are completed. Earlier blocked-access statements below are historical. Discovery remains **Weak**. Commit `ff555bb` and the original reference panel are preserved. No application or production records/configuration were changed.

# StoreScout — Real-world Discovery Benchmark Preparation

Recorded 2026-09-05. Baseline code: `ff555bb2842a05f55dcc83403bfef80bc7eb17cf`.

**Discovery remains Weak. No real-index quality improvement or real-world accuracy metric has been established in this pass.** The production index is inaccessible from the currently connected tools. Supabase was successfully connected during this pass and installation is confirmed, but no Supabase database-query tools are exposed in the active session. No production data, services, prices or billing were changed; no outreach or model requests were sent. The completed application audit, fixes, Playbook work, prospect research and test suite were not repeated.

## What is ready

An independently researched reference panel contains **25 real businesses, eight niche groups and two provisional known competitors per business**. Twenty-four cases are core cases; Stewart is a separately reported platform-uncertainty control. The references were selected from official public offerings before seeing any StoreScout output. They are an analyst's product-fit judgments, not customer feedback or an exhaustive competitor market map. Related brands within groups are correlated; 25 businesses must not be presented as 25 independent market segments.

A reference-panel JSON, baseline source hashes, read-only export queries, feature-coverage mapping and precise engineering specifications are saved in `docs/quality-audit/real-world/`. No fabricated store-index rows were created. Returned results, pipeline traces and metrics are null, not zero. The earlier synthetic benchmark remains unchanged and is not reused as evidence of real-world accuracy.

## Independent reference panel

Each business name links to the official page reviewed. Reference links point to independently reviewed official offerings. “Strong” means plausible competition for the stated product/use case, not equal prices, proven audience identity or verified Shopify access. Partial relationships require a visible limitation when scored useful. All platform/catalog-access checks are still pending.

| Business / test focus | Independent reference competitors | Evidence and caveat |
| --- | --- | --- |
| [Durston](https://durstongear.com/) — We sell ultralight backpacking tents and packs for long-distance hikers. | [Zpacks](https://zpacks.com/collections/tents), [Gossamer Gear](https://www.gossamergear.com/) | Premium ultralight tents, packs and trekking poles; X-Mid and X-Dome lines. |
| [Zpacks](https://zpacks.com/collections/tents) — We sell ultralight two-person backpacking tents. | [Durston](https://durstongear.com/), [Gossamer Gear](https://www.gossamergear.com/) | Ultralight backpacking tents; Duplex family includes two-person shelters. |
| [Gossamer Gear](https://www.gossamergear.com/) — We sell lightweight hiking backpacks and shelters. | [Durston](https://durstongear.com/), [Zpacks](https://zpacks.com/collections/tents) | Framed and frameless hiking packs; The One, The Two and other shelters. |
| [ILIA](https://iliabeauty.com/products/super-serum-skin-tint-spf-40-tinted-moisturizer) — We sell light-coverage skin tint with mineral SPF for adults. | [Tower 28](https://www.tower28beauty.com/), [Saie](https://saiehello.com/) | Super Serum Skin Tint supplies light coverage and mineral SPF; fragrance-free positioning. |
| [Tower 28](https://www.tower28beauty.com/) — We sell tinted sunscreen and everyday complexion makeup. | [ILIA](https://iliabeauty.com/products/super-serum-skin-tint-spf-40-tinted-moisturizer), [Saie](https://saiehello.com/) | SunnyDays tinted SPF 30 plus makeup and skincare. |
| [Saie](https://saiehello.com/) — We sell tinted moisturizer with SPF and everyday makeup. | [ILIA](https://iliabeauty.com/products/super-serum-skin-tint-spf-40-tinted-moisturizer), [Tower 28](https://www.tower28beauty.com/) | Slip Tint tinted moisturizer SPF 35; complexion, cheek, lip and eye makeup. |
| [Pipette](https://www.pipettebaby.com/collections/soothing) — We sell fragrance-free baby lotion for sensitive skin. | [Tubby Todd](https://tubbytodd.com/products/all-over-ointment), [Babo Botanicals](https://www.babobotanicals.com/collections/sensitive-baby-skin-care) | Fragrance-free baby skin products including eczema lotion; product availability is separate. |
| [Tubby Todd](https://tubbytodd.com/products/all-over-ointment) — We sell fragrance-free ointment and skin care for babies. | [Pipette](https://www.pipettebaby.com/collections/soothing), [Babo Botanicals](https://www.babobotanicals.com/collections/sensitive-baby-skin-care) | All Over Ointment has a fragrance-free option positioned for sensitive/eczema-prone skin. |
| [Babo Botanicals](https://www.babobotanicals.com/collections/sensitive-baby-skin-care) — We sell fragrance-free sensitive baby skin care. | [Pipette](https://www.pipettebaby.com/collections/soothing), [Tubby Todd](https://tubbytodd.com/products/all-over-ointment) | Sensitive Baby collection includes fragrance-free wash/lotion/balm; broader family assortment. |
| [Onyx Coffee Lab](https://onyxcoffeelab.com/) — We roast specialty coffee for home brewers and sell subscriptions. | [Counter Culture](https://counterculturecoffee.com/), [Verve](https://www.vervecoffee.com/) | Retail single origins, blends and subscriptions alongside tea/chocolate/equipment and wholesale. |
| [Counter Culture](https://counterculturecoffee.com/) — We sell specialty coffee beans and recurring home deliveries. | [Onyx Coffee Lab](https://onyxcoffeelab.com/), [Verve](https://www.vervecoffee.com/) | Single origins, year-round blends and recurring coffee delivery; named blends and office packs. |
| [Verve](https://www.vervecoffee.com/) — We sell freshly roasted specialty coffee and subscriptions. | [Onyx Coffee Lab](https://onyxcoffeelab.com/), [Counter Culture](https://counterculturecoffee.com/) | Fresh roasted coffee sold online, including Roaster's Choice subscriptions. |
| [Little Sleepies](https://littlesleepies.com/) — We sell bamboo pajamas for babies and matching families. | [Kyte Baby](https://kytebaby.com/), [Birdie Bean](https://birdiebean.com/) | Bamboo pajamas and daywear for babies, kids and adults; matching family positioning. Sleep bags, pajamas and adult matching sets must be scored separately. |
| [Kyte Baby](https://kytebaby.com/) — We sell bamboo baby sleep bags and sleepwear. | [Little Sleepies](https://littlesleepies.com/), [Birdie Bean](https://birdiebean.com/) | Bamboo sleep bag specialist with broader sleepwear; sleep bags are not interchangeable with pajamas. Sleep bags, pajamas and adult matching sets must be scored separately. |
| [Birdie Bean](https://birdiebean.com/) — We sell printed bamboo pajamas and clothing for children. | [Little Sleepies](https://littlesleepies.com/), [Kyte Baby](https://kytebaby.com/) | Bamboo kids clothing, original prints and family matching. Sleep bags, pajamas and adult matching sets must be scored separately. |
| [PureBites](https://purebites.com/) — We sell freeze-dried single-protein dog treats. | [Stewart](https://stewartpet.com/), [Stella & Chewy's](https://www.stellaandchewys.com/collections/freeze-dried-raw-dog-treats) | Chicken/beef/salmon freeze-dried dog treats alongside distinct cat treats, food and toppers. |
| [Stewart](https://stewartpet.com/) — We sell freeze-dried raw dog treats and toppers. | [PureBites](https://purebites.com/), [Stella & Chewy's](https://www.stellaandchewys.com/collections/freeze-dried-raw-dog-treats) | Freeze-dried dog treats, toppers and foods; homepage contains WordPress assets, Shopify monitorability unknown. Keep as a separate control, not a confirmed monitorable Shopify store. |
| [Stella & Chewy's](https://www.stellaandchewys.com/collections/freeze-dried-raw-dog-treats) — We sell freeze-dried raw training treats for dogs. | [PureBites](https://purebites.com/), [Stewart](https://stewartpet.com/) | Freeze-dried raw dog treats; limited-ingredient and training use supported by related official collections. |
| [Quince](https://www.quince.com/) — We sell affordable clothing, home essentials, bedding, bags and jewelry. | [Brooklinen](https://www.brooklinen.com/), [Parachute](https://parachutehome.com/) | Broad clothing/home/baby/travel/accessories retailer, low-price positioning; linen sheets explicitly offered. Both references cover bedding only; neither stands in for the entire multi-category business. |
| [Brooklinen](https://www.brooklinen.com/) — We sell bedding, sheets and comforters directly to consumers. | [Quince](https://www.quince.com/), [Parachute](https://parachutehome.com/) | Bedding, sheets and comforters; independent homepage evidence, product-specific linen validation still required. |
| [Parachute](https://parachutehome.com/) — We sell linen bedding and bath linens for the home. | [Quince](https://www.quince.com/), [Brooklinen](https://www.brooklinen.com/) | Bedding and bath; linen sheets and duvet covers shown. |
| [Keychron](https://www.keychron.com/) — We sell customizable mechanical keyboards for Mac and Windows. | [NuPhy](https://nuphy.com/collections/low-profile-keyboards), [EPOMAKER](https://epomaker.com/collections/low-profile-keyboard) | Custom mechanical keyboards for Mac/Windows plus broader accessories. |
| [NuPhy](https://nuphy.com/collections/low-profile-keyboards) — We sell low-profile wireless mechanical keyboards. | [Keychron](https://www.keychron.com/), [EPOMAKER](https://epomaker.com/collections/low-profile-keyboard) | Low-profile mechanical keyboards; search-source crawl about two months old, current availability unverified. |
| [EPOMAKER](https://epomaker.com/collections/low-profile-keyboard) — We sell mechanical keyboards including low-profile models. | [Keychron](https://www.keychron.com/), [NuPhy](https://nuphy.com/collections/low-profile-keyboards) | Mechanical keyboard retailer with a dedicated low-profile collection. |
| [ColourPop](https://colourpop.com/collections/face) — We sell affordable eye palettes, lip products and face makeup. | [e.l.f.](https://www.elfcosmetics.com/), [Revolution Beauty](https://www.revolutionbeauty.com/) | Makeup across face, eyes and lips; multiple low-priced items and collections. |

Public pages were reviewed on September 5, 2026; search crawl times differ. NuPhy's retrieved evidence was roughly two months old. Price/audience positioning is not fully adjudicated for this panel; category-level price labels must not be treated as equivalent-unit price research. Mainstream/value makeup is included through ColourPop and its references; Quince supplies a value-positioned broad retailer, while specialist tent brands supply narrow technical products. This panel is predominantly English-language and US-facing. Geography and non-English coverage remain limitations.

## New real-world observations, separate from StoreScout results

* [Drop](https://drop.com/) currently presents Corsair gaming collaborations and sends visitors to related brands. That is a lifecycle/canonical-identity test, not proof that a historical keyboard listing still has a monitorable catalog.
* [Stewart](https://stewartpet.com/) describes relevant freeze-dried dog products but serves a homepage containing WordPress assets. This is not conclusive proof against Shopify commerce elsewhere; classify product relevance and platform evidence independently.
* [Value Pet Supplies](https://www.valuepetsupplies.com/) emphasizes wholesale/bulk natural chews. A wholesale link or bulk offer must not automatically mean wholesale-only or irrelevant: inspect who can buy and pack/unit economics.
* [Earthbath's fragrance-free shampoo](https://earthbath.com/products/hypoallergenic-shampoo-groomer) is for pets/groomers. Matching “fragrance free” and “sensitive skin” would not make it a relevant infant-skincare competitor.
* [Quince](https://www.quince.com/) spans clothing, home, travel and other categories. A bedding specialist can be useful for its bedding business while missing most of its overall assortment. Query focus is part of the ground truth.
* [Gossamer Gear](https://www.gossamergear.com/) names shelters “The One” and “The Two.” Product-title words alone can be weak evidence even on a real, relevant store; collection/type and surrounding facts matter.

## Real index health: unknown, not inferred

| Requested measurement | Current status | Evidence required |
| --- | --- | --- |
| Total stores; status/category/niche distribution | Not measured | Complete read-only census |
| Active/reachable and verified Shopify rates | Not measured | Weighted independent stratified checks; pipeline flags alone are insufficient |
| Duplicates/canonical-domain issues | Not measured | Exact-domain census plus redirect/shop/catalog evidence |
| Stale or future-dated records | Not measured | Verification/knowledge timestamp distributions |
| Parked/dead/password/wholesale-only/non-Shopify | Not measured | Independent access-state labels, with uncertainty preserved |
| Classification coverage/confidence | Not measured | Null/low-confidence/category distribution and human-labelled sample |
| Missing metadata | Not measured | Field-level missing/null/empty counts and sampled evidence depth |
| Freshness/update history | Not measured | Existing timestamps and history where available; latest timestamps cannot reconstruct history |

The earlier source audit establishes possible weaknesses in retrieval, normalization/ranking and refresh logic. It does **not** establish the real-world contribution of index coverage versus those weaknesses. No index expansion or ranking-weight changes are justified by a nonexistent census. The next run must assign every known miss to a stage before prioritizing engineering.

## Three wording failures: broader diagnosis

| Prior held-out wording | What the failure actually tests | Safe general rule |
| --- | --- | --- |
| Unscented skin repair balm → fragrance-free eczema moisturizer; brush wins lexical overlap | Fragrance wording plus product form/use case; original direct-equivalence label is under-specified | Normalize genuine wording variants, but require evidence for audience/form/use-case fit. Unscented is not a universal clinical or formulation equivalent of fragrance-free; balm is not automatically an eczema treatment. |
| Hiking shelter → ultralight backpacking tent; backpack wins | Product head and substitute relation, with modifiers shared by accessories | A backpacking tent is a possible shelter subtype; a hiking backpack is not a shelter. Retrieve supported product concepts before ranking. |
| Raw dog treats → freeze-dried chicken reward bites; storage jar wins | Species/use-case/process and accessory relation | “Reward bites” may mean treats when product evidence supports it. Chicken alone does not establish dogs, and freeze-dried alone does not establish raw. A container is not the edible product. |

These are diagnostic interpretations of the saved failures, not rerun results. The literal eight-term metadata retrieval can discard alternatives before the ranker sees them; the ranker's flat sets can then reward shared modifiers instead of substitutes. Both stages need the same evidence-backed product understanding. Scope-limited normalization is preferable to special cases named after these fixtures, and the reference labels themselves must be reviewed rather than making the implementation satisfy an unjustified label.

## Baseline and acceptance protocol

Freeze the actual index snapshot, schema, source hashes, clock, settings and reference labels. Replay ff555bb locally with paid AI, HTTP verification, queues and all writes disabled. Preserve exact retrieval predicates/projections/caps/fallbacks and record which stage loses each known competitor. The local code is not the currently deployed revision; report those separately. Do not call the live discovery endpoint under read-only authorization.

Measure padded P@5/P@10, strong-only precision, useful/returned rate, wrong/returned rate, unknown-label rate, known-reference recall, eligible-present retrieval recall and searches with three useful top-five results. Report every case and niche. The index path returns at most eight, so index-only P@10 cannot exceed 0.8. Do not make small result sets look strong by changing denominators. Reference recall is partial-market recall; independently judge useful returned brands outside the known set.

**Proposed early pilot gate:** P@5 ≥0.60; ≥80% of core searches have three useful top-five competitors; wrong-result rate ≤10%; unknown labels ≤5%; no multi-case niche has fewer than two-thirds of its cases meeting the three-useful standard. Preserve whole-family holdouts and reject material niche regressions. These thresholds are a proposed operational standard, not measured achievements or proof of customer acceptance. A second blind label review and user selection task should corroborate them.

No top results, false positives or misses from the real StoreScout index can yet be reported. Filling those columns with synthetic or researcher-created rows would invalidate the requested baseline.

## Implementation order

1. **Measurement prerequisite:** refresh the session to expose the connected Supabase query tools; export and reconcile the public index; independently label access and relevance; faithful local replay.
2. **P1:** fix demonstrated candidate loss using shared product concepts, observed product title/type retrieval, stable bounded retrieval and field-preserving merge. No blind weight tuning.
3. **P1:** distinguish substitutes from accessories; represent explicit audience constraints and comparable product prices only where observed. Unknown stays unknown.
4. **P1:** add a measurable renewal/classification lifecycle and evidence-based canonical identity only if census confirms the need. Production changes require separate approval.
5. **P1:** align description/profile/focus handling and all candidate pathways, then assess explanation evidence and the choose/add workflow. No explanation UI added yet.
6. **P2:** broader semantic infrastructure, new integrations and index growth require demonstrated residual misses and a cost/benefit case.

The repository specification gives affected files, constraints, regression risks, evaluation cases and acceptance criteria for each item. Existing application functionality and commit ff555bb are preserved.

## Complete feature audit verification

The saved report contains **58 feature groups** covering purpose, implementation, usefulness/next action, no-integration and integrated behavior, flaws, already-made changes, remaining work and disposition/priority. Its existing inventory covers 137 route-decorated handlers, 21 frontend pages and 32 jobs, including internal/admin/legacy code. A new coverage map ties each recorded frontend page to its report group. This confirms coverage of the prior source audit; it does not certify live functionality. No new integrations, Playbook changes or repeated tests were undertaken.

## Exact resume point

Supabase connection is confirmed. The active callable tool registry still contains no Supabase tools after connection, so database execution remains blocked. Resume in a fresh turn to refresh access; once query tools are exposed, start with schema and read-only census/export, using the saved queries; do not repeat public reference research, the full source audit or ff555bb tests. Populate actual schema/threshold/snapshot information in a new baseline-run record; preserve the pinned source and reference manifest. Then independently inspect sampled domains and all returned results, execute the replay and calculate metrics. Stop before any production mutation or paid AI request. Discovery remains **Weak / real-world quality unmeasured** until that work produces evidence.

Local documentation checkpoint: `11c1205`, direct child of preserved `ff555bb`. Application source hashes remain unchanged. Artifact integrity checks passed; no application tests were rerun. No push or deployment.


## Real-data measurement completed, 5 September 2026

The index contains 38,221 records: 36,088 discovered, 1,323 candidate, 426 verified, 323 rejected and 61 failed. At the frozen clock, 403 pass the default freshness/catalog gate, or 392 with category confidence ≥55. The 240-domain stratified public sample found readable catalogs for 156/177 discovered stores. A backlog-processing and evidence-lifecycle problem is now demonstrated; unknown/unprocessed is not equivalent to dead.

The untouched local `ff555bb` release candidate was replayed through the original endpoint against real PostgreSQL candidate captures, with production writes and paid calls prohibited. The primary 24-case result excludes the prepared Stewart control: P@5 28.3%, P@10 15.8%, known-reference recall 2/48, useful/returned 38/148 (25.7%), wrong/returned 57/148 (38.5%), unknown 3/148, and three-useful top-five coverage 7/24 (29.2%). Structured notes leave core P@5 and three-useful coverage unchanged. These are source-default local release-candidate measurements, not a live production or AI-assisted benchmark. Relevance is single-analyst, not independently blinded; geographic and price equivalence remain unestablished.

Of 50 original reference relationships including the control, 30 are absent, 16 unverified, two catalog-gated and two returned. Stronger candidates also disappear in retrieval/filtering: HyperX product fields are not searched; the JSONB DNA-overlap query fails; Babysprouts and Terra Moons lose meaningful product evidence. Shared modifiers produce wrong matches. No measured query hits the 200-candidate or first-eight-term cap. Classification and semantic freshness errors are real.

Measured priority order: (1) existing supply verification, renewal and catalog evidence parity; (2) product-based retrieval and substitute/meaning checks; (3) semantic freshness, classification and evidence-based canonical identity; (4) explicit product focus/identity and recoverable sparse-result flows. Numeric weight tuning, larger candidate caps and new explanation UI do not lead this plan.

Complete measurements and all 25 individual case results: `StoreScout-Real-Index-and-Discovery-Results.md`. Codex-ready root causes, components, desired behavior, regression risks, tests, cases and acceptance criteria: `StoreScout-Codex-Discovery-Priorities.md`. Reproducible snapshots, query captures, labels, traces and census data: `StoreScout-Discovery-Evidence.zip`. These measured deliverables supersede earlier null benchmark numbers. The original public catalog sample, prospect work, outreach drafts, source audit and existing tests were not repeated.

The next task is implementation in an isolated local branch, preserving the frozen comparison. No production processing, deployment, paid AI, outreach or configuration changes were authorized. The original panel is now inspected and cannot be described as an untouched blind holdout. Independent adjudication and the existing release gates remain necessary before declaring Acceptable.
