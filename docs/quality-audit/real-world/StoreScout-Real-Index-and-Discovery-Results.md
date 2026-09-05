# StoreScout: real index health and discovery results

Measured 5 September 2026. **Discovery remains Weak.** Supabase SQL access worked in this conversation. The real index contains 38,221 domain records, but only 426 are pipeline-verified and 403 pass the frozen baseline’s freshness/catalog gate. The prepared 25-business panel was executed against actual PostgreSQL retrieval captures using the unchanged local release candidate. This is not a live production endpoint or paid-AI benchmark.

For the 24 core businesses, description-only Precision@5 is **28.3%**, Precision@10 **15.8%**, and only **7/24 searches (29.2%)** produce three useful top-five competitors. **57/148 returned results (38.5%) are obviously wrong.** The existing Acceptable gate is not met.

## Scope, provenance and limits

The independent reference panel and its original ground truth were preserved: SHA256 `56f9c0a10beef5e2f0d8f588c6a480f489ff1f68c05c1f0b36cfcac98e2f1e2a`. Application baseline `ff555bb2842a05f55dcc83403bfef80bc7eb17cf` and all five recorded source hashes remain unchanged. The repository was at documentation child `11c1205`; this session changes documentation only. Completed audits, synthetic evaluation, implementation work, prospect work and existing tests were not repeated.

All database operations used explicit `BEGIN READ ONLY` transactions. No customer/profile tables, credentials or contacts were exported. Snapshot fields are an allowlist of public catalog/business metadata; nested DNA is limited to keywords and summary. No production records, deployments, configuration, queues, paid models, outreach or payments were changed.

The 38,221-row export used 20 independently paginated transactions, not one atomic transaction. Counts, latest update time and the ordered domain/update-timestamp checksum reconciled at the start and end. No concurrent timestamp changes were detected; this cannot prove content stability if an upstream writer fails to maintain timestamps. Latest recorded update was 2026-08-31 06:02:57.989171 UTC. Snapshot SHA256: `661b34722ab431c63b3f458660cc154a1e0352e9585fee2b994c1a311476f136`. PostgreSQL domain/timestamp MD5: `2f56a53de54cde8c97f359c6b437cd42`.

The replay clock is frozen at **2026-09-05 20:44:23.705755 UTC**. It uses verification minimum 60, category minimum 55 and the source’s 60-day freshness gate. Safe database settings report index enabled, daily verified target 200 and daily candidate limit 150. Production environment threshold overrides were not inspected; these are source-default release-candidate metrics, not proof of deployed settings or production behavior. Previously documented deployment differences were not reinvestigated.

Actual PostgreSQL executed the category and lexical predicates, ordering, projections and per-channel 200 limit. The original endpoint, classifier, eligibility checks, scorer and final rerank ran locally through a read adapter using those captures. Missing/empty data stayed missing/empty. The DNA-overlap channel reproduced the actual JSONB operator error; it was not repaired during baseline. Network/model/verifier/queue/mutation paths were denied during replay; an artificial local pro-tier identity avoided usage writes. Empty graph, tracked-store and own-store context were explicit baseline conditions.

Both required input modes ran for all 25 businesses: description-only; and a structured profile containing the same query in `sells` plus the previously researched official-source summary in `notes`. No new price, audience or category claims were injected. A website URL was not treated as automatic enrichment. Alternate wording/focus variants, authenticated histories, legacy-schema fallback and paid-AI-assisted outputs remain unmeasured. The present production schema did not trigger projection fallback.

Relevance labels use the saved 0–3 rubric: 3 strong, 2 useful partial with a stated limitation, 1 adjacent/weak, 0 wrong, unknown insufficient public evidence. Missing ranks count as zero in P@k. Useful means label ≥2. These are single-analyst judgments following shuffled source review after debugging, not a fully blinded second review or merchant validation. Therefore the scores are provisional; even generous partial-fit credit leaves discovery Weak. All countries are absent and no currency field exists: geographic serviceability and comparable-price claims are not established. Partial retailers, cotton alternatives to bamboo and air-dried alternatives to freeze-dried products retain explicit caveats.

## Exact database census

| State | Rows | Share |
|---|---:|---:|
| discovered | 36,088 | 94.4% |
| candidate | 1,323 | 3.5% |
| verified | 426 | 1.1% |
| rejected | 323 | 0.8% |
| failed | 61 | 0.2% |

Discovered plus candidate backlog: **37,411 (97.9%)**. These are unprocessed records, not established bad stores. Only 403/38,221 (1.05%) pass verified status, minimum verification confidence, age and the exact catalog signal; adding the category floor leaves 392. Among the 426 verified rows, 23 lack the required catalog signal: 19 have only “Actively scanned by StoreScout,” and four have platform markers without the catalog signal. Fourteen have category confidence below 55, with three overlapping those 23. These gates must not be conflated with an independent Shopify or relevance assessment.

There are no exact duplicate domain keys. Normalizing case and leading `www.` finds **138 collision groups, 276 records, 138 excess aliases**. These are candidate identity collisions, not permission to merge. Same-brand names suggest another Vuori pair but do not prove canonical identity. No duplicate canonical aliases appeared in benchmark outputs. Public checks observed cross-host redirects; they do not exhaustively establish canonical-domain collisions across the index.

Historical flags record 61 `unreachable_or_dns`, 18 `dead_domain`, 18 `not_shopify`, 17 `invalid_storefront`, three `no_products`, and 209 conflated below-threshold/catalog-locked failures. They are historical pipeline labels, not present-day census truth. The 23 `sells_wholesale=true` rows do not establish wholesale-only businesses. Current dead, non-Shopify, wholesale-only and commercially active counts cannot be determined exactly from these fields.

### Freshness and classification

At the frozen clock, no verified record is beyond the 60-day verification cutoff. However, **320/426 (75.1%)** were last verified 31–60 days ago; 103 are 0–7 days old and three 8–30 days old. Those 320 cross the cutoff within seven days if not renewed, including eight within 24 hours and four within one hour. These are clock-specific forecasts, not today’s continuing eligible counts. All 426 knowledge timestamps are 31–60 days old. A recent verification timestamp does not prove current product meaning.

Across all records, 37,780 lack category, subcategory and category confidence; only 412 have a non-Other category at confidence ≥55. Among verified rows, 406 do. Confidence is a heuristic, not a calibrated probability. A 46-row verified subsample independently reviewed against current public storefronts found 35 correct broad categories, two partial, four wrong, three unclassified and two unknown. Weighted wrong-category estimate is 11.3%, but small strata prohibit a precise calibration claim. High-confidence errors include Fashion Nova as Jewelry/Watches (95), Spigen as Jewelry/Watches (88), Kinugawa Turbo as Kids & Baby/Toys (89), and Benchmark Abrasives as Outdoors/Water Sports (90).

| Metadata field | Missing among all 38,221 | Missing among verified 426 |
|---|---:|---:|
| description | 37,840 | 49 |
| product_titles | 37,830 | 43 |
| product_types | 37,838 | 49 |
| dna_keywords | 38,009 | 219 |
| category_evidence | 37,791 | 2 |
| target_customer | 37,793 | 2 |
| pricing_tier | 37,793 | 6 |
| country | 38,221 | 426 |
| language | 37,798 | 16 |
| collections | 37,801 | 13 |
| homepage_message | 37,872 | 84 |
| last_verified_at | 37,401 | 0 |
| knowledge_at | 37,788 | 0 |

Category and subcategory histograms, source distribution, confidence histogram and every timestamp bucket are included in `census-analysis.json`. Verified category distribution:

| Stored category | Verified rows |
|---|---:|
| Fashion | 68 |
| Accessories | 36 |
| Toys & Games | 33 |
| Jewelry | 32 |
| Sporting Goods | 27 |
| Beauty | 24 |
| Pets | 24 |
| Kids & Baby | 23 |
| Home & Living | 21 |
| Outdoors | 17 |
| Food & Beverage | 16 |
| Other | 16 |
| Footwear | 13 |
| Fitness Apparel | 12 |
| Electronics & Gadgets | 12 |
| Arts & Crafts | 10 |
| Automotive | 10 |
| Health & Personal Care | 8 |
| Tech Accessories | 7 |
| Books & Media | 7 |
| Supplements | 5 |
| Home Improvement | 3 |
| Adult | 2 |

Stored niches are exceptionally thin: Coffee 2, Bedding 4, Pet Food 2, Camping 4 and Computers 1. Coffee includes an equipment business. These labels measure classification coverage, not true product-market coverage.

## Independent public health checks

A reproducible 240-domain sample covered 59 category × status × verification-age strata. Within-stratum domains were ordered by SHA256 using seed `StoreScout-census-20260905-v1:domain`; allocations and inclusion weights are retained. Public checks additionally covered benchmark results and known references, for **353 unique domains** overall. Only the 240 probability-design observations contribute to population estimates. Observation window: 20:55:20–21:06:30 UTC on 5 September.

| Current public observation | Sample count / 240 | Weighted estimate |
|---|---:|---:|
| Accessible homepage | 208 | 88.2% |
| Readable nonempty public catalog | 201 | 84.6% |
| Shopify markers or compatible catalog evidence | 228 | 95.5% |
| Unknown access | 10 | 3.6% |
| Password page | 1 | 0.5% |
| Parking/domain-sale signal | 1 | 0.5% |
| HTTP 402 storefront unavailable | 2 | 0.5% |
| Bot challenge | 1 | 0.0% |
| Readable empty catalog | 1 | 0.5% |

These categories overlap. An accessible homepage is not proof of an active merchant; platform evidence is not a successful checkout. The weighted nonempty-catalog estimate is 84.6%, with a conservative 95% concentration bound of 74.7–94.5% under the pseudo-random sampling design. This wide bound addresses sampling only, not probe or classification errors; most small strata have one observation. Rare-state estimates are especially uncertain. Do not convert them into exact store counts.

Crucially, **156/177 sampled discovered stores** exposed a nonempty catalog (weighted 88.0% of the discovered stratum). **41/46 sampled verified stores** did so (weighted 91.8%). All eight distinct already-indexed but unverified known-reference brands had current readable catalogs. This supports improving throughput and eligibility before indiscriminately acquiring more domains.

`chito.international` showed a password page; `aether.run` redirected to a domain broker; `glitzpuffs.com` and `tintlab.ca` returned storefront-unavailable HTTP 402. A failed/blocked request remained unknown, not dead or non-Shopify. `babymel.com` returned 502 during relevance review. Direct container DNS failed initially for every attempt, so those infrastructure failures were discarded; managed HTTP plus public DNS resolution was used for the retained observations. Private-network targets were rejected on every redirect. Requests, redirects, time and response size were bounded; no passwords or challenges were bypassed. A truncated large JSON response or a first-50-product sample does not establish absence of a catalog/product. No definitive dead-domain rate is claimed.

## Discovery metrics

Stewart is the original platform-uncertainty control and is excluded from the 24-case primary verdict. P@10 retains the protocol’s denominator of ten even though index-only returns at most eight; P@8 is available per case in the evidence. Errors are counted as failures, not blocked requests.

| Metric, 24 core cases | Description-only | Structured profile | Existing gate |
|---|---:|---:|---:|
| Precision@5 | 28.3% | 28.3% | ≥60% |
| Precision@10 | 15.8% | 17.9% | diagnostic |
| Strong-only Precision@5 | 6.7% | 6.7% | diagnostic |
| Useful / returned | 25.7% | 25.7% | diagnostic |
| Obviously wrong / returned | 38.5% | 41.3% | ≤10% |
| Unknown / returned | 2.0% | 1.8% | ≤5% |
| Searches with ≥3 useful in top five | 29.2% | 29.2% | ≥80% |
| Known-reference recall@10 | 4.2% | 4.2% | report supply separately |
| Searches with a wrong top-five result | 75.0% | 83.3% | review all |

Description-only returned 148 placements: 38 useful, 57 wrong and three unknown. Structured input returned 167: 43 useful, 69 wrong and three unknown. The extra notes did not improve core P@5 or three-useful coverage, and increased wrong results. Little Sleepies produced the original endpoint’s HTTP 500 empty-result error in description-only mode; structured mode returned an adjacent partial competitor instead. No case was blocked by missing database access.

All 25 including Stewart: description-only P@5 28.8%, P@10 16.4%, 7/25 three-useful coverage; structured P@5 29.6%, P@10 18.4%, 8/25 coverage. Stewart alone: P@5 40% description-only versus 60% structured, with three useful partials in eight results; the description-only third partial is outside the top five. Family-balanced core P@5 is 27.9% in both modes.

### By niche, primary description-only mode

| Niche | Cases | P@5 | P@10 | Searches with ≥3 useful top-five |
|---|---:|---:|---:|---:|
| baby skin | 3 | 0.0% | 0.0% | 0/3 |
| bamboo family sleepwear | 3 | 6.7% | 3.3% | 0/3 |
| bedding and broad store | 3 | 40.0% | 30.0% | 1/3 |
| dog freeze dried treats | 2 | 60.0% | 30.0% | 2/2 |
| mechanical keyboards | 3 | 0.0% | 0.0% | 0/3 |
| specialty coffee | 3 | 40.0% | 20.0% | 0/3 |
| tinted complexion | 4 | 70.0% | 37.5% | 4/4 |
| ultralight | 3 | 6.7% | 3.3% | 0/3 |

The dog-treat result is driven entirely by useful partials, including retailers in other countries and a different drying process; strong-only P@5 there is zero. Tinted complexion is the best measured niche, but still contains wrong results. Baby skincare and keyboards produce no useful primary results. The family-specific acceptance rule is not met.

## Quantified root causes

The 25-case panel has 50 known-competitor relationships across 26 distinct reference domains. These are correlated relationships, not 50 independent merchants:

| First limiting stage | Relationships | Share |
|---|---:|---:|
| Absent from real index, including checked www aliases | 30 | 60% |
| Present but unverified | 16 | 32% |
| Verified but rejected by catalog-evidence gate | 2 | 4% |
| Returned | 2 | 4% |

Thus **92% of known-reference relationships fail before a verified candidate can be ranked**, and another 4% fail the catalog contract. In the 24 core cases, counts are 28 absent, 16 unverified, two gated, two returned (2/48 recall). Both returned relationships are the same Tower 28 brand. Eligible-present reference retrieval is 2/2, an inadequate denominator for claiming retrieval quality. This partial reference set cannot establish complete market recall or the percentage of all quality failures caused by each layer.

Stage counts identify the earliest blocker; fixes are not additive. Parachute in the Quince case also lacks product overlap, so repairing its catalog signal alone would not recover it. No counterfactual system was implemented and no numeric uplift is promised.

| Layer | Measured evidence | Diagnosis |
|---|---|---|
| Raw coverage | 30/50 reference relationships absent | Large genuine supply gaps remain |
| Processing / eligible coverage | 16/50 present but unverified; 37,411-record backlog; 156/177 sampled discovered catalogs readable | Existing supply is largely unusable to discovery |
| Catalog contract | 23 verified rows lack exact catalog signal; Parachute rank 3 then excluded for Brooklinen | Historical scanning and monitorable eligibility disagree |
| Retrieval | DNA JSONB overlap errors; HyperX product titles/types unsearched | Good indexed evidence can remain invisible |
| Interpretation / fit | Shared pack, tint, roast, printed and low-profile tokens admit unrelated goods | Product meaning and negative evidence are inadequate |
| Filtering / metadata | Babysprouts and Terra Moons retrieved but zero product overlap | Opaque observed product fields suppress useful contextual evidence |
| Ranking | Babysprouts rank 13 for Kyte Baby; wrong modifier matches survive top five | Scoring and cutoff compound evidence defects |
| Classification / staleness | Four high-confidence broad-category errors in 46 reviewed verified rows; former bedding domain now hobby goods | Current scores and age checks do not guarantee product identity |
| Candidate truncation | Largest actual channel 118/200; all primary retrieval term lists ≤8 | No measured 200-cap or first-eight-term loss in this panel |

The DNA column is JSONB, while the code calls `.overlaps(...)`, requiring an overlap operator absent for `jsonb && text[]` (PostgreSQL error 42883). The channel fails for every replay, but 219/426 verified rows also have no DNA keywords. Repairing the operator is necessary; it cannot create missing evidence.

### Concrete disappearance and entry traces

1. **Keychron / EPOMAKER → HyperX:** mechanical-keyboard intent → weak/no category inference → lexical retrieval searches description/brand/category, not observed titles/types → HyperX’s generic gamer description and Audio category miss the query; DNA is null → never reaches rank. Its frozen observed products include mechanical keyboards, and a diagnostic score using the existing full row would exceed all returned candidates for these two queries. [Official mechanical-keyboard catalog](https://hyperx.com/collections/mechanical-keyboards) confirms a useful candidate, without establishing Mac or low-profile equivalence. This additional diagnostic candidate was not added to reference ground truth.
2. **Little Sleepies / Birdie Bean → Babysprouts:** bamboo sleepwear wording → candidate retrieved → generic names and missing material concepts yield zero matching product terms → excluded. **Kyte Baby:** same domain retrieved, matches only `baby`, score 14.47, pre-filter rank 13 → misses returned eight. [Official bamboo sleep/play romper](https://www.babysprouts.com/) supports revisiting product evidence; it does not justify treating every sleep item as equivalent.
3. **ColourPop → Terra Moons:** Beauty retrieval includes the domain → product type `PHYSICAL` and opaque product names cause observed-field precedence to suppress useful DNA makeup/eyeshadow evidence → score 5, zero terms, excluded at pre-filter rank 19. [Official store](https://terramoonscosmetics.com/) confirms eyeshadow products. This is evidence selection plus filtering, not simply a low weight.
4. **Brooklinen → Parachute:** Home & Living retrieval → `sheet` overlap → pre-filter rank 3, score 14.63 → exact catalog-signal gate rejects it although verification confidence is 100 and recorded product count is 1,500. Current public catalog was readable. Do not bypass the gate with a confidence threshold: unify dated successful-catalog evidence from the two ingestion paths.
5. **Coffee → Lheureux:** a real bean seller is retrieved but French `Café en grains` and accent/token handling lose useful overlap. [Official coffee store](https://lheureuxinc.com/) provides a multilingual diagnostic. Its eligibility for a particular shipping market remains unknown.
6. **Durston:** `pack` admits trading-card booster packs; `ultralight` admits denim. **NuPhy:** `low-profile` admits Hydrus paddleboards. **ILIA:** `tint` admits window tint. **Coffee:** roast/subscription and inferred Food & Beverage tokens admit meat/hot sauce. **Birdie Bean:** `printed` admits car parts. Product heads and modifiers are not distinguished sufficiently before ranking.
7. **Brooklinen / Parachute → smile-cleanworks.com:** a high-confidence bedding classification and sheet matches survive age/fit checks; the current public domain presents Hobby Collective acrylic-sheet goods. A still-within-TTL record has changed commercial meaning.
8. **Tower 28 → itself:** empty own-store context means no explicit identity exclusion, so its own domain ranks first and is labelled wrong. Supplying an optional verified own-domain identity is appropriate; guessing identity from a generic description is not.

## Individual cases and returned-result evidence

Every original query, structured context, channel row order, exclusion, score, returned placement, known-reference stage and public relevance rationale is preserved in the evidence archive. The following primary-case records retain failures rather than only aggregates. Labels below are 3 strong, 2 useful partial, 1 adjacent, 0 wrong, ? unknown.

| Business | Returned | P@5 | P@10 | Useful / wrong / unknown | Known recall | ≥3 top-five |
|---|---:|---:|---:|---:|---:|---|
| Durston | 5 | 0.0% | 0.0% | 0/2/0 | 0/2 | no |
| Zpacks | 1 | 0.0% | 0.0% | 0/1/0 | 0/2 | no |
| Gossamer Gear | 8 | 20.0% | 10.0% | 1/3/0 | 0/2 | no |
| ILIA | 5 | 60.0% | 30.0% | 3/2/0 | 1/2 | yes |
| Tower 28 | 8 | 60.0% | 30.0% | 3/3/0 | 0/2 | yes |
| Saie | 8 | 80.0% | 40.0% | 4/2/0 | 1/2 | yes |
| Pipette | 8 | 0.0% | 0.0% | 0/6/0 | 0/2 | no |
| Tubby Todd | 8 | 0.0% | 0.0% | 0/4/0 | 0/2 | no |
| Babo Botanicals | 8 | 0.0% | 0.0% | 0/2/0 | 0/2 | no |
| Onyx Coffee Lab | 8 | 40.0% | 20.0% | 2/4/0 | 0/2 | no |
| Counter Culture | 6 | 40.0% | 20.0% | 2/2/0 | 0/2 | no |
| Verve | 8 | 40.0% | 20.0% | 2/4/0 | 0/2 | no |
| Little Sleepies | 0 | 0.0% | 0.0% | 0/0/0 | 0/2 | no |
| Kyte Baby | 8 | 20.0% | 10.0% | 1/3/1 | 0/2 | no |
| Birdie Bean | 8 | 0.0% | 0.0% | 0/8/0 | 0/2 | no |
| PureBites | 8 | 60.0% | 30.0% | 3/1/0 | 0/2 | yes |
| Stewart (control) | 8 | 40.0% | 30.0% | 3/1/0 | 0/2 | no |
| Stella & Chewy's | 8 | 60.0% | 30.0% | 3/1/0 | 0/2 | yes |
| Quince | 8 | 60.0% | 60.0% | 6/1/0 | 0/2 | yes |
| Brooklinen | 6 | 40.0% | 20.0% | 2/2/1 | 0/2 | no |
| Parachute | 4 | 20.0% | 10.0% | 1/1/1 | 0/2 | no |
| Keychron | 2 | 0.0% | 0.0% | 0/0/0 | 0/2 | no |
| NuPhy | 3 | 0.0% | 0.0% | 0/2/0 | 0/2 | no |
| EPOMAKER | 4 | 0.0% | 0.0% | 0/2/0 | 0/2 | no |
| ColourPop | 8 | 80.0% | 50.0% | 5/1/0 | 0/2 | yes |

### Durston

Input: We sell ultralight backpacking tents and packs for long-distance hikers.

Known references: zpacks.com: absent from index; gossamergear.com: not verified.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | xopoutdoors.com | 1 | Hunting treestands and hunting packs; hiking shelter and long-distance pack comparability not established. |
| 2 | nomatic.com | 1 | Travel, camera or leather/laptop bags; adjacent carrying function without supported ultralight trail-pack fit. |
| 3 | jamesleather.com | 1 | Travel, camera or leather/laptop bags; adjacent carrying function without supported ultralight trail-pack fit. |
| 4 | roboskillz.com | 0 | Observed trading cards, denim, paddleboards, children school goods, cycling components or industrial abrasives do not satisfy the hiking-pack/shelter query. |
| 5 | blueingreensoho.com | 0 | Observed trading cards, denim, paddleboards, children school goods, cycling components or industrial abrasives do not satisfy the hiking-pack/shelter query. |

### Zpacks

Input: We sell ultralight two-person backpacking tents.

Known references: durstongear.com: absent from index; gossamergear.com: not verified.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | blueingreensoho.com | 0 | Observed trading cards, denim, paddleboards, children school goods, cycling components or industrial abrasives do not satisfy the hiking-pack/shelter query. |

### Gossamer Gear

Input: We sell lightweight hiking backpacks and shelters.

Known references: durstongear.com: absent from index; zpacks.com: absent from index.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | funwaterboard.com | 0 | Observed trading cards, denim, paddleboards, children school goods, cycling components or industrial abrasives do not satisfy the hiking-pack/shelter query. |
| 2 | scouttech.com | 2 | Outdoor retailer with tents and hiking backpacks; useful partial assortment comparison, Canadian retail positioning and product weights need review. |
| 3 | otsurplus.com | 1 | Military surplus packs and shelters are adjacent; heavy/surplus equipment is not established as a lightweight long-distance substitute. |
| 4 | beachinsurf.com.au | 1 | Adjacent surf/hunting/footwear/camping-blanket assortment, without verified lightweight shelter or backpack substitution for this query. |
| 5 | hydrusboardtech.com | 0 | Observed trading cards, denim, paddleboards, children school goods, cycling components or industrial abrasives do not satisfy the hiking-pack/shelter query. |
| 6 | knomo.com | 1 | Travel, camera or leather/laptop bags; adjacent carrying function without supported ultralight trail-pack fit. |
| 7 | bagsandshoes.net | 1 | Adjacent surf/hunting/footwear/camping-blanket assortment, without verified lightweight shelter or backpack substitution for this query. |
| 8 | wildkin.com | 0 | Observed trading cards, denim, paddleboards, children school goods, cycling components or industrial abrasives do not satisfy the hiking-pack/shelter query. |

### ILIA

Input: We sell light-coverage skin tint with mineral SPF for adults.

Known references: tower28beauty.com: returned; saiehello.com: absent from index.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | peachandlily.com | 3 | Official Sun Cover is a lightly tinted mineral SPF product, directly overlapping the stated ILIA use case. |
| 2 | tower28beauty.com | 3 | Independent official evidence supports tinted SPF and complexion makeup; price equivalence is not assumed. |
| 3 | tintstuff.myshopify.com | 0 | Window tint, fashion bags, paddleboards, trading cards, perfume, PPE or deodorant fail the requested complexion/color-makeup use case. |
| 4 | kallureskloset.com | 0 | Window tint, fashion bags, paddleboards, trading cards, perfume, PPE or deodorant fail the requested complexion/color-makeup use case. |
| 5 | gracebeautybox.co.uk | 2 | Official retailer pages list tinted face SPF and CC cream; useful partial product comparison, retailer/UK positioning differs and mineral-only formulation is not established. |

### Tower 28

Input: We sell tinted sunscreen and everyday complexion makeup.

Known references: iliabeauty.com: not verified; saiehello.com: absent from index.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | tower28beauty.com | 0 | Own business returned as its own competitor in the empty-profile description-only scenario; the request supplies no explicit own-domain exclusion. |
| 2 | gracebeautybox.co.uk | 2 | Official retailer pages list tinted face SPF and CC cream; useful partial product comparison, retailer/UK positioning differs and mineral-only formulation is not established. |
| 3 | redaspenlove.com | 2 | Observed face/lip makeup assortment overlaps part of the query; SPF, formulation, full portfolio and price comparability require review. |
| 4 | peachandlily.com | 2 | Official Sun Cover mineral tinted SPF overlaps complexion/suncare; full makeup portfolio or price parity is not assumed. |
| 5 | toppestanas.com | 1 | Professional lash or nail supplies are adjacent beauty products, not evidenced complexion substitutes. |
| 6 | perfumetogo.com | 0 | Window tint, fashion bags, paddleboards, trading cards, perfume, PPE or deodorant fail the requested complexion/color-makeup use case. |
| 7 | queensupplies.com | 1 | Professional lash or nail supplies are adjacent beauty products, not evidenced complexion substitutes. |
| 8 | hydrusboardtech.com | 0 | Window tint, fashion bags, paddleboards, trading cards, perfume, PPE or deodorant fail the requested complexion/color-makeup use case. |

### Saie

Input: We sell tinted moisturizer with SPF and everyday makeup.

Known references: iliabeauty.com: not verified; tower28beauty.com: returned.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | tower28beauty.com | 3 | Independent official evidence supports tinted SPF and complexion makeup; price equivalence is not assumed. |
| 2 | gracebeautybox.co.uk | 2 | Official retailer pages list tinted face SPF and CC cream; useful partial product comparison, retailer/UK positioning differs and mineral-only formulation is not established. |
| 3 | redaspenlove.com | 2 | Observed face/lip makeup assortment overlaps part of the query; SPF, formulation, full portfolio and price comparability require review. |
| 4 | peachandlily.com | 2 | Official Sun Cover mineral tinted SPF overlaps complexion/suncare; full makeup portfolio or price parity is not assumed. |
| 5 | toppestanas.com | 1 | Professional lash or nail supplies are adjacent beauty products, not evidenced complexion substitutes. |
| 6 | perfumetogo.com | 0 | Window tint, fashion bags, paddleboards, trading cards, perfume, PPE or deodorant fail the requested complexion/color-makeup use case. |
| 7 | queensupplies.com | 1 | Professional lash or nail supplies are adjacent beauty products, not evidenced complexion substitutes. |
| 8 | hydrusboardtech.com | 0 | Window tint, fashion bags, paddleboards, trading cards, perfume, PPE or deodorant fail the requested complexion/color-makeup use case. |

### Pipette

Input: We sell fragrance-free baby lotion for sensitive skin.

Known references: tubbytodd.com: not verified; babobotanicals.com: absent from index.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | gracebeautybox.co.uk | 1 | Human skincare/medical-care adjacency, but the observed evidence does not establish fragrance-free infant lotion/ointment suitability; no medical equivalence inferred. |
| 2 | pureborn.com | 1 | Current official storefront sells diapers and calendula-lotion wipes; adjacent baby cleansing, not evidence of a fragrance-free infant lotion/ointment substitute. |
| 3 | apolina-kids.com | 0 | Observed apparel, infant formula, pillows, bags, perfume, wigs, salon supplies or adult deodorant do not perform the stated infant-lotion/ointment function. |
| 4 | hibobbie.com | 0 | Observed apparel, infant formula, pillows, bags, perfume, wigs, salon supplies or adult deodorant do not perform the stated infant-lotion/ointment function. |
| 5 | primary.com | 0 | Observed apparel, infant formula, pillows, bags, perfume, wigs, salon supplies or adult deodorant do not perform the stated infant-lotion/ointment function. |
| 6 | boppy.com | 0 | Observed apparel, infant formula, pillows, bags, perfume, wigs, salon supplies or adult deodorant do not perform the stated infant-lotion/ointment function. |
| 7 | pehr.com | 0 | Observed apparel, infant formula, pillows, bags, perfume, wigs, salon supplies or adult deodorant do not perform the stated infant-lotion/ointment function. |
| 8 | petunia.com | 0 | Observed apparel, infant formula, pillows, bags, perfume, wigs, salon supplies or adult deodorant do not perform the stated infant-lotion/ointment function. |

### Tubby Todd

Input: We sell fragrance-free ointment and skin care for babies.

Known references: pipettebaby.com: absent from index; babobotanicals.com: absent from index.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | gracebeautybox.co.uk | 1 | Human skincare/medical-care adjacency, but the observed evidence does not establish fragrance-free infant lotion/ointment suitability; no medical equivalence inferred. |
| 2 | perfumetogo.com | 0 | Observed apparel, infant formula, pillows, bags, perfume, wigs, salon supplies or adult deodorant do not perform the stated infant-lotion/ointment function. |
| 3 | medicalsupplysurplus.com | 1 | Human skincare/medical-care adjacency, but the observed evidence does not establish fragrance-free infant lotion/ointment suitability; no medical equivalence inferred. |
| 4 | sahajan.com | 1 | Human skincare/medical-care adjacency, but the observed evidence does not establish fragrance-free infant lotion/ointment suitability; no medical equivalence inferred. |
| 5 | chiquel.com | 0 | Observed apparel, infant formula, pillows, bags, perfume, wigs, salon supplies or adult deodorant do not perform the stated infant-lotion/ointment function. |
| 6 | peachandlily.com | 1 | Human skincare/medical-care adjacency, but the observed evidence does not establish fragrance-free infant lotion/ointment suitability; no medical equivalence inferred. |
| 7 | toppestanas.com | 0 | Observed apparel, infant formula, pillows, bags, perfume, wigs, salon supplies or adult deodorant do not perform the stated infant-lotion/ointment function. |
| 8 | queensupplies.com | 0 | Observed apparel, infant formula, pillows, bags, perfume, wigs, salon supplies or adult deodorant do not perform the stated infant-lotion/ointment function. |

### Babo Botanicals

Input: We sell fragrance-free sensitive baby skin care.

Known references: pipettebaby.com: absent from index; tubbytodd.com: not verified.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | perfumetogo.com | 0 | Observed apparel, infant formula, pillows, bags, perfume, wigs, salon supplies or adult deodorant do not perform the stated infant-lotion/ointment function. |
| 2 | gracebeautybox.co.uk | 1 | Human skincare/medical-care adjacency, but the observed evidence does not establish fragrance-free infant lotion/ointment suitability; no medical equivalence inferred. |
| 3 | medicalsupplysurplus.com | 1 | Human skincare/medical-care adjacency, but the observed evidence does not establish fragrance-free infant lotion/ointment suitability; no medical equivalence inferred. |
| 4 | sahajan.com | 1 | Human skincare/medical-care adjacency, but the observed evidence does not establish fragrance-free infant lotion/ointment suitability; no medical equivalence inferred. |
| 5 | dlacosmetics.com | 1 | Human skincare/medical-care adjacency, but the observed evidence does not establish fragrance-free infant lotion/ointment suitability; no medical equivalence inferred. |
| 6 | chiquel.com | 0 | Observed apparel, infant formula, pillows, bags, perfume, wigs, salon supplies or adult deodorant do not perform the stated infant-lotion/ointment function. |
| 7 | tower28beauty.com | 1 | Human skincare/medical-care adjacency, but the observed evidence does not establish fragrance-free infant lotion/ointment suitability; no medical equivalence inferred. |
| 8 | peachandlily.com | 1 | Human skincare/medical-care adjacency, but the observed evidence does not establish fragrance-free infant lotion/ointment suitability; no medical equivalence inferred. |

### Onyx Coffee Lab

Input: We roast specialty coffee for home brewers and sell subscriptions.

Known references: counterculturecoffee.com: not verified; vervecoffee.com: absent from index.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | volcanicacoffee.com | 3 | Official specialty roasted coffee and subscription offerings directly match; no same-price assertion. |
| 2 | madeinnewmexico.com | 2 | Regional retailer carries packaged coffee alongside a broad New Mexico food/gift range; useful coffee-assortment comparison, not equivalent roaster/subscription positioning. |
| 3 | butchershopdirect.com | 0 | Observed meat, hot sauce, prepared salads, nuts, candy or cheese; roast/subscription/food wording is not coffee-product overlap. |
| 4 | heatonist.com | 0 | Observed meat, hot sauce, prepared salads, nuts, candy or cheese; roast/subscription/food wording is not coffee-product overlap. |
| 5 | inspiredgo.ca | 0 | Observed meat, hot sauce, prepared salads, nuts, candy or cheese; roast/subscription/food wording is not coffee-product overlap. |
| 6 | nutspick.co.uk | 0 | Observed meat, hot sauce, prepared salads, nuts, candy or cheese; roast/subscription/food wording is not coffee-product overlap. |
| 7 | ztshpt-cs.myshopify.com | 1 | Drinkware/kitchenware or broad imported groceries are adjacent; no demonstrated specialty-roasted-bean/subscription substitute. |
| 8 | corkcicle.com | 1 | Drinkware/kitchenware or broad imported groceries are adjacent; no demonstrated specialty-roasted-bean/subscription substitute. |

### Counter Culture

Input: We sell specialty coffee beans and recurring home deliveries.

Known references: onyxcoffeelab.com: absent from index; vervecoffee.com: absent from index.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | volcanicacoffee.com | 3 | Official specialty roasted coffee and subscription offerings directly match; no same-price assertion. |
| 2 | madeinnewmexico.com | 2 | Regional retailer carries packaged coffee alongside a broad New Mexico food/gift range; useful coffee-assortment comparison, not equivalent roaster/subscription positioning. |
| 3 | inspiredgo.ca | 0 | Observed meat, hot sauce, prepared salads, nuts, candy or cheese; roast/subscription/food wording is not coffee-product overlap. |
| 4 | butchershopdirect.com | 0 | Observed meat, hot sauce, prepared salads, nuts, candy or cheese; roast/subscription/food wording is not coffee-product overlap. |
| 5 | ztshpt-cs.myshopify.com | 1 | Drinkware/kitchenware or broad imported groceries are adjacent; no demonstrated specialty-roasted-bean/subscription substitute. |
| 6 | corkcicle.com | 1 | Drinkware/kitchenware or broad imported groceries are adjacent; no demonstrated specialty-roasted-bean/subscription substitute. |

### Verve

Input: We sell freshly roasted specialty coffee and subscriptions.

Known references: onyxcoffeelab.com: absent from index; counterculturecoffee.com: not verified.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | volcanicacoffee.com | 3 | Official specialty roasted coffee and subscription offerings directly match; no same-price assertion. |
| 2 | madeinnewmexico.com | 2 | Regional retailer carries packaged coffee alongside a broad New Mexico food/gift range; useful coffee-assortment comparison, not equivalent roaster/subscription positioning. |
| 3 | heatonist.com | 0 | Observed meat, hot sauce, prepared salads, nuts, candy or cheese; roast/subscription/food wording is not coffee-product overlap. |
| 4 | inspiredgo.ca | 0 | Observed meat, hot sauce, prepared salads, nuts, candy or cheese; roast/subscription/food wording is not coffee-product overlap. |
| 5 | butchershopdirect.com | 0 | Observed meat, hot sauce, prepared salads, nuts, candy or cheese; roast/subscription/food wording is not coffee-product overlap. |
| 6 | nutspick.co.uk | 0 | Observed meat, hot sauce, prepared salads, nuts, candy or cheese; roast/subscription/food wording is not coffee-product overlap. |
| 7 | ztshpt-cs.myshopify.com | 1 | Drinkware/kitchenware or broad imported groceries are adjacent; no demonstrated specialty-roasted-bean/subscription substitute. |
| 8 | corkcicle.com | 1 | Drinkware/kitchenware or broad imported groceries are adjacent; no demonstrated specialty-roasted-bean/subscription substitute. |

### Little Sleepies

Input: We sell bamboo pajamas for babies and matching families.

Execution: HTTP 500, Failed to generate suggestions — please try again.

Known references: kytebaby.com: not verified; birdiebean.com: not verified.


### Kyte Baby

Input: We sell bamboo baby sleep bags and sleepwear.

Known references: littlesleepies.com: not verified; birdiebean.com: not verified.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | babymel.com | ? | Current domain checks return 502; historical MORI description alone cannot independently establish the current redirected business or catalog. |
| 2 | primary.com | 2 | Official baby pajamas/sleepwear (and Pehr sleep bags) overlap the sleep use case; cotton/modal differs from bamboo and adult matching is not established. |
| 3 | petunia.com | 0 | Observed diaper bags/formula/diapers, adult apparel/footwear, car parts, merchandise, pet food or everyday-carry goods fail the stated children bamboo sleepwear use case. |
| 4 | wildkin.com | 1 | Adjacent kids bedding/daywear or adult silk sleepwear, without evidenced bamboo infant/family sleepwear substitution. |
| 5 | shop.marigoldmodern.com | 1 | Adjacent kids bedding/daywear or adult silk sleepwear, without evidenced bamboo infant/family sleepwear substitution. |
| 6 | pureborn.com | 0 | Observed diaper bags/formula/diapers, adult apparel/footwear, car parts, merchandise, pet food or everyday-carry goods fail the stated children bamboo sleepwear use case. |
| 7 | apolina-kids.com | 1 | Adjacent kids bedding/daywear or adult silk sleepwear, without evidenced bamboo infant/family sleepwear substitution. |
| 8 | hibobbie.com | 0 | Observed diaper bags/formula/diapers, adult apparel/footwear, car parts, merchandise, pet food or everyday-carry goods fail the stated children bamboo sleepwear use case. |

### Birdie Bean

Input: We sell printed bamboo pajamas and clothing for children.

Known references: littlesleepies.com: not verified; kytebaby.com: not verified.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | accessprive.com | 0 | Observed diaper bags/formula/diapers, adult apparel/footwear, car parts, merchandise, pet food or everyday-carry goods fail the stated children bamboo sleepwear use case. |
| 2 | ryderwear.com | 0 | Observed diaper bags/formula/diapers, adult apparel/footwear, car parts, merchandise, pet food or everyday-carry goods fail the stated children bamboo sleepwear use case. |
| 3 | vessi.com | 0 | Observed diaper bags/formula/diapers, adult apparel/footwear, car parts, merchandise, pet food or everyday-carry goods fail the stated children bamboo sleepwear use case. |
| 4 | cave-london.com | 0 | Observed diaper bags/formula/diapers, adult apparel/footwear, car parts, merchandise, pet food or everyday-carry goods fail the stated children bamboo sleepwear use case. |
| 5 | ctc-performance.co.uk | 0 | Observed diaper bags/formula/diapers, adult apparel/footwear, car parts, merchandise, pet food or everyday-carry goods fail the stated children bamboo sleepwear use case. |
| 6 | asiyathecollection.com | 0 | Observed diaper bags/formula/diapers, adult apparel/footwear, car parts, merchandise, pet food or everyday-carry goods fail the stated children bamboo sleepwear use case. |
| 7 | hansonstreetwear.com | 0 | Observed diaper bags/formula/diapers, adult apparel/footwear, car parts, merchandise, pet food or everyday-carry goods fail the stated children bamboo sleepwear use case. |
| 8 | baukjen.com | 0 | Observed diaper bags/formula/diapers, adult apparel/footwear, car parts, merchandise, pet food or everyday-carry goods fail the stated children bamboo sleepwear use case. |

### PureBites

Input: We sell freeze-dried single-protein dog treats.

Known references: stewartpet.com: absent from index; stellaandchewys.com: absent from index.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | fetchyourpetneeds.ie | 2 | Official stores offer freeze-dried/raw dog treats; useful retailer assortment comparison, but geography and reseller-versus-brand positioning differ. A reseller of the query brand is not a newly discovered competing manufacturer. |
| 2 | petland.ca | 2 | Official stores offer freeze-dried/raw dog treats; useful retailer assortment comparison, but geography and reseller-versus-brand positioning differ. A reseller of the query brand is not a newly discovered competing manufacturer. |
| 3 | wildone.com | 1 | Dog gear, paw-care or refillable enrichment products are adjacent; no evidenced freeze-dried edible dog-treat substitution. |
| 4 | muttluks.com | 1 | Dog gear, paw-care or refillable enrichment products are adjacent; no evidenced freeze-dried edible dog-treat substitution. |
| 5 | redbarn.com | 2 | Official single-meat air-dried training treats overlap rewarding/training use; process differs from freeze-dried raw and ingredient equivalence is not assumed. |
| 6 | ruffwear.com | 1 | Dog gear, paw-care or refillable enrichment products are adjacent; no evidenced freeze-dried edible dog-treat substitution. |
| 7 | freezbone.com | 1 | Dog gear, paw-care or refillable enrichment products are adjacent; no evidenced freeze-dried edible dog-treat substitution. |
| 8 | kensfish.com | 0 | Aquarium supplies or cat toys contradict species/product use. |

### Stewart

Input: We sell freeze-dried raw dog treats and toppers.

Known references: purebites.com: absent from index; stellaandchewys.com: absent from index.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | fetchyourpetneeds.ie | 2 | Official stores offer freeze-dried/raw dog treats; useful retailer assortment comparison, but geography and reseller-versus-brand positioning differ. A reseller of the query brand is not a newly discovered competing manufacturer. |
| 2 | ruffwear.com | 1 | Dog gear, paw-care or refillable enrichment products are adjacent; no evidenced freeze-dried edible dog-treat substitution. |
| 3 | petland.ca | 2 | Official stores offer freeze-dried/raw dog treats; useful retailer assortment comparison, but geography and reseller-versus-brand positioning differ. A reseller of the query brand is not a newly discovered competing manufacturer. |
| 4 | wildone.com | 1 | Dog gear, paw-care or refillable enrichment products are adjacent; no evidenced freeze-dried edible dog-treat substitution. |
| 5 | muttluks.com | 1 | Dog gear, paw-care or refillable enrichment products are adjacent; no evidenced freeze-dried edible dog-treat substitution. |
| 6 | redbarn.com | 2 | Official single-meat air-dried training treats overlap rewarding/training use; process differs from freeze-dried raw and ingredient equivalence is not assumed. |
| 7 | freezbone.com | 1 | Dog gear, paw-care or refillable enrichment products are adjacent; no evidenced freeze-dried edible dog-treat substitution. |
| 8 | kensfish.com | 0 | Aquarium supplies or cat toys contradict species/product use. |

### Stella & Chewy's

Input: We sell freeze-dried raw training treats for dogs.

Known references: purebites.com: absent from index; stewartpet.com: absent from index.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | fetchyourpetneeds.ie | 2 | Official stores offer freeze-dried/raw dog treats; useful retailer assortment comparison, but geography and reseller-versus-brand positioning differ. A reseller of the query brand is not a newly discovered competing manufacturer. |
| 2 | redbarn.com | 2 | Official single-meat air-dried training treats overlap rewarding/training use; process differs from freeze-dried raw and ingredient equivalence is not assumed. |
| 3 | ruffwear.com | 1 | Dog gear, paw-care or refillable enrichment products are adjacent; no evidenced freeze-dried edible dog-treat substitution. |
| 4 | freezbone.com | 1 | Dog gear, paw-care or refillable enrichment products are adjacent; no evidenced freeze-dried edible dog-treat substitution. |
| 5 | petland.ca | 2 | Official stores offer freeze-dried/raw dog treats; useful retailer assortment comparison, but geography and reseller-versus-brand positioning differ. A reseller of the query brand is not a newly discovered competing manufacturer. |
| 6 | dear-paw.com | 0 | Aquarium supplies or cat toys contradict species/product use. |
| 7 | wildone.com | 1 | Dog gear, paw-care or refillable enrichment products are adjacent; no evidenced freeze-dried edible dog-treat substitution. |
| 8 | muttluks.com | 1 | Dog gear, paw-care or refillable enrichment products are adjacent; no evidenced freeze-dried edible dog-treat substitution. |

### Quince

Input: We sell affordable clothing, home essentials, bedding, bags and jewelry.

Known references: brooklinen.com: not verified; parachutehome.com: fresh catalog gate.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | petunia.com | 2 | For Quince only: limited bag/accessory/apparel segment overlap. This does not represent its whole broad business or establish equal price, audience or material. |
| 2 | shopleatherworld.com | 2 | For Quince only: limited bag/accessory/apparel segment overlap. This does not represent its whole broad business or establish equal price, audience or material. |
| 3 | shopelvis.com | 1 | Licensed Elvis merchandise differs materially in purchase motivation from Quince general essentials. |
| 4 | kallureskloset.com | 2 | For Quince only: limited bag/accessory/apparel segment overlap. This does not represent its whole broad business or establish equal price, audience or material. |
| 5 | thebizzbybabs.com | 0 | Sexual-wellness positioning and products do not establish useful competition for Quince everyday apparel/home essentials. |
| 6 | babyletto.com | 2 | Nursery furniture/bedding overlaps a limited part of Quince home/baby assortment; not a whole-business comparator. |
| 7 | robertsonmadison.com | 2 | For Quince only: limited bag/accessory/apparel segment overlap. This does not represent its whole broad business or establish equal price, audience or material. |
| 8 | ryderwear.com | 2 | For Quince only: limited bag/accessory/apparel segment overlap. This does not represent its whole broad business or establish equal price, audience or material. |

### Brooklinen

Input: We sell bedding, sheets and comforters directly to consumers.

Known references: quince.com: absent from index; parachutehome.com: fresh catalog gate.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | rest-ment.com | ? | Bedding navigation persists but the sampled current catalog is dominated by jewelry/storage products and the homepage contains template copy. Actual comparable bedding could not be confidently established from this bounded observation. |
| 2 | madisonpark2010.com | 3 | Official bedding/sheet/comforter assortment overlaps the bedding use case; no sales or price equivalence claimed. |
| 3 | smile-cleanworks.com | 0 | Current hobby supplies, vinyl records, printed signage, denim or cosmetics do not satisfy the bedding/bath-linen query. |
| 4 | wildkin.com | 2 | Children twin/full bedding supplies partial sheet/comforter overlap; audience, designs and material differ. |
| 5 | vintagerecordstore.com | 0 | Current hobby supplies, vinyl records, printed signage, denim or cosmetics do not satisfy the bedding/bath-linen query. |
| 6 | babyletto.com | 1 | Nursery-size bedding/furniture or broader home decor is adjacent; standard-size linen sheet/bath overlap is not established. |

### Parachute

Input: We sell linen bedding and bath linens for the home.

Known references: quince.com: absent from index; brooklinen.com: not verified.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | smile-cleanworks.com | 0 | Current hobby supplies, vinyl records, printed signage, denim or cosmetics do not satisfy the bedding/bath-linen query. |
| 2 | rest-ment.com | ? | Bedding navigation persists but the sampled current catalog is dominated by jewelry/storage products and the homepage contains template copy. Actual comparable bedding could not be confidently established from this bounded observation. |
| 3 | madisonpark2010.com | 2 | Bedding and bath assortment is useful partial overlap; exact linen material comparability remains unverified. |
| 4 | babyletto.com | 1 | Nursery-size bedding/furniture or broader home decor is adjacent; standard-size linen sheet/bath overlap is not established. |

### Keychron

Input: We sell customizable mechanical keyboards for Mac and Windows.

Known references: nuphy.com: absent from index; epomaker.com: absent from index.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | shop.urbanarmorgear.com | 1 | Instrument/equipment covers, keyboard/device cases or broad secondhand electronics are adjacent; no evidenced comparable mechanical keyboard model. |
| 2 | bestampcovers.com | 1 | Instrument/equipment covers, keyboard/device cases or broad secondhand electronics are adjacent; no evidenced comparable mechanical keyboard model. |

### NuPhy

Input: We sell low-profile wireless mechanical keyboards.

Known references: keychron.com: absent from index; epomaker.com: absent from index.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | hydrusboardtech.com | 0 | Observed paddleboards, phone accessories, watches, apparel, sexual-wellness goods or records do not satisfy mechanical-keyboard intent. |
| 2 | warsawwireless.com | 0 | Observed paddleboards, phone accessories, watches, apparel, sexual-wellness goods or records do not satisfy mechanical-keyboard intent. |
| 3 | bestampcovers.com | 1 | Instrument/equipment covers, keyboard/device cases or broad secondhand electronics are adjacent; no evidenced comparable mechanical keyboard model. |

### EPOMAKER

Input: We sell mechanical keyboards including low-profile models.

Known references: keychron.com: absent from index; nuphy.com: absent from index.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | mil-time.com | 0 | Observed paddleboards, phone accessories, watches, apparel, sexual-wellness goods or records do not satisfy mechanical-keyboard intent. |
| 2 | hydrusboardtech.com | 0 | Observed paddleboards, phone accessories, watches, apparel, sexual-wellness goods or records do not satisfy mechanical-keyboard intent. |
| 3 | cashzone.com.au | 1 | Instrument/equipment covers, keyboard/device cases or broad secondhand electronics are adjacent; no evidenced comparable mechanical keyboard model. |
| 4 | bestampcovers.com | 1 | Instrument/equipment covers, keyboard/device cases or broad secondhand electronics are adjacent; no evidenced comparable mechanical keyboard model. |

### ColourPop

Input: We sell affordable eye palettes, lip products and face makeup.

Known references: elfcosmetics.com: absent from index; revolutionbeauty.com: absent from index.

| Rank | Returned domain | Label | Public-evidence rationale |
|---:|---|---:|---|
| 1 | gracebeautybox.co.uk | 2 | Official retailer pages list tinted face SPF and CC cream; useful partial product comparison, retailer/UK positioning differs and mineral-only formulation is not established. |
| 2 | sahajan.com | 1 | Adult facial skincare is adjacent; no evidenced tint or color-makeup substitute for this request. |
| 3 | redaspenlove.com | 3 | Observed eyes, lips and face makeup directly overlaps the stated product portfolio; pricing still requires comparable-product review. |
| 4 | tower28beauty.com | 2 | Useful face/lip makeup overlap; full affordable eye-palette assortment not established. |
| 5 | besamecosmetics.com | 2 | Observed face/lip makeup assortment overlaps part of the query; SPF, formulation, full portfolio and price comparability require review. |
| 6 | peachandlily.com | 2 | Official Sun Cover mineral tinted SPF overlaps complexion/suncare; full makeup portfolio or price parity is not assumed. |
| 7 | queensupplies.com | 1 | Professional lash or nail supplies are adjacent beauty products, not evidenced complexion substitutes. |
| 8 | safetygloves.com | 0 | Window tint, fashion bags, paddleboards, trading cards, perfume, PPE or deodorant fail the requested complexion/color-makeup use case. |

## Handoff and next authorized step

`StoreScout-Codex-Discovery-Priorities.md` records the measured implementation order and acceptance criteria. The previous implementation specifications retain their detailed contracts, with an evidence-based superseding section. Measurement is no longer blocked. Application implementation, production data processing and deployment have not been performed.

The next step is Codex implementation in an isolated local branch against the frozen snapshot. Evaluate changes against this baseline and preserve every failure trace. The existing panel has now been inspected, so it cannot honestly serve as an untouched blind holdout; freeze tuning/evaluation partitions before implementation and require independent adjudication before any Acceptable claim. Do not redefine known references from the algorithm’s output. No production repair or schedule activation is authorized by this report.
