# Fixed 88-store relevance ceiling

**Decision: B — request approval for a bounded 500-domain expansion. Do not run it yet.**

Coverage is the larger constraint. Perfect retrieval/filtering/ranking of the evidenced useful stores raises P@5 from 14.4% to only **17.6%** and searches with three useful top-five results from 0/25 to **1/25**. Twenty-four queries cannot meet that three-result standard with this supply. There is a real but localized Quince matching problem; another general ranking pass cannot resolve the other niches.

This conclusion supersedes the previous report's recommendation to continue matching work: that report judged returned placements; this analysis judges the full query-by-supply matrix. It does **not** declare Discovery acceptable or predict that arbitrary new stores will be relevant.

## Scope, evidence and label limits

- Analysis starts at `8bdc0ef6881107c713a28e1d6f6e3ab1f1056e4f` on `codex/discovery-quality-fixed-supply-2026-09-24`.
- The original 34 plus V2 54 records remain exactly 88; the combined snapshot is byte-identical to the original pilot export. Frozen 25 queries, both input modes, clock, classification threshold and application logic remain unchanged.
- All **2,200 query/store pairs** are adjudicated: **22 useful, 173 adjacent, 2,005 irrelevant under the retained evidence**. Ninety-four pairs reuse existing adjudications; their useful/not-useful decisions are preserved. All 88 records have a reviewed catalog description and retained complete sampled titles/types/metadata in [catalog evidence](catalog-evidence.json).
- [Full relevance matrix](relevance-matrix.json) contains every pair, label, rationale, provenance and prior judgments. Ratings 2–3 count as useful under the frozen protocol; rating 1 is adjacent, never credited. Own-business matches never count as competitors.
- This is an **evidence-conditioned ceiling**, not a claim to know the entire live catalog of every merchant. Titles are bounded samples, product types are not item-associated and demographics/materials/price are often unproven. We made no new merchant/network requests. Adjacent records are not promoted because a missing attribute *might* exist. Whole-catalog uncertainty cannot honestly be turned into an exact real-world upper bound.
- Two new useful **partial** Quince comparisons are Pomp and Circumstance and Worth & Gray. Their adult apparel/accessory evidence is judged on the same basis as the preserved Wilkins & Olander label. Affordable price parity and home/bedding equivalence are not claimed. Both judgments are single-analyst, not a fresh blind panel.
- Sensitivity: downgrading **both** new partial judgments to adjacent lowers the P@5 ceiling to **16.0%**, P@10 to **8.0%**; the three-useful ceiling stays **1/25**. The coverage decision therefore does not depend on those additions.

## Achievable ceiling

P@k uses the original padded denominator: `sum(min(k, useful_available_per_query)) / (25*k)`. No list-length denominator inflation. All useful availability counts are at most five, so the application's existing eight-result cap does not further reduce the perfect-supply P@10 ceiling.

| Metric | Current description | Current structured | Perfect fixed-supply ceiling |
|---|---:|---:|---:|
| P@5 | 14.4% | 14.4% | **17.6%** |
| P@10 | 7.6% | 8.0% | **8.8%** |
| Searches with at least 3 useful top-five | 0/25 | 0/25 | **1/25 (4%)** |
| Known-reference recall | 4% | 4% | **4%** |

**Ranking alone** over candidates already surviving all gates has a P@5 ceiling of **16.8%** in either mode. Recovering the one useful filtered store would raise it to 17.6%. This is an oracle calculation, not an implemented or rerun improved ranking system.

| Useful stores available for a query | Queries | Share |
|---|---:|---:|
| 0 | 13 | 52% |
| 1 | 5 | 20% |
| 2 | 6 | 24% |
| 3+ | 1 | 4% |

There are **55 missing useful query/store slots** to supply three useful competitors to every query (not 55 necessarily distinct merchants). Of the current 57-slot deficit relative to that target, 55 are supply shortfall and only two can be recovered by better ordering for Quince. Independently, **48/50 known-reference relationships are absent** from the eligible snapshot. References are an incomplete market panel; they are not the only stores eligible to receive useful labels.

## Per-query availability and actual retrieval

Top10 below means actual returned top10 (the endpoint returns at most eight), not the diagnostic uncapped list. D = description-only; S = structured profile. All useful available domains, including misses, are in [per-query.json](per-query.json) and [CSV](per-query.csv).

| Business | Useful available | D top5 / top10 | S top5 / top10 |
|---|---:|---:|---:|
| Durston | 0 | 0 / 0 | 0 / 0 |
| Zpacks | 0 | 0 / 0 | 0 / 0 |
| Gossamer Gear | 0 | 0 / 0 | 0 / 0 |
| ILIA | 2 | 2 / 2 | 2 / 2 |
| Tower 28 | 1 | 1 / 1 | 1 / 1 |
| Saie | 2 | 2 / 2 | 2 / 2 |
| Pipette | 0 | 0 / 0 | 0 / 0 |
| Tubby Todd | 0 | 0 / 0 | 0 / 0 |
| Babo Botanicals | 0 | 0 / 0 | 0 / 0 |
| Onyx Coffee Lab | 1 | 1 / 1 | 1 / 1 |
| Counter Culture | 1 | 1 / 1 | 1 / 1 |
| Verve | 1 | 1 / 1 | 1 / 1 |
| Little Sleepies | 0 | 0 / 0 | 0 / 0 |
| Kyte Baby | 0 | 0 / 0 | 0 / 0 |
| Birdie Bean | 0 | 0 / 0 | 0 / 0 |
| PureBites | 2 | 2 / 2 | 2 / 2 |
| Stewart | 2 | 2 / 2 | 2 / 2 |
| Stella & Chewy's | 2 | 2 / 2 | 2 / 2 |
| Quince | 5 | 1 / 2 | 1 / 3 |
| Brooklinen | 1 | 1 / 1 | 1 / 1 |
| Parachute | 0 | 0 / 0 | 0 / 0 |
| Keychron | 0 | 0 / 0 | 0 / 0 |
| NuPhy | 0 | 0 / 0 | 0 / 0 |
| EPOMAKER | 0 | 0 / 0 | 0 / 0 |
| ColourPop | 2 | 2 / 2 | 2 / 2 |

Useful domain sets:

- ILIA, Saie, ColourPop: `peachandlily.com`, `tower28beauty.com`. Tower 28 query: only Peach & Lily, excluding self.
- Coffee queries: only `madcapcoffee.com`.
- Dog-treat queries: `fetchyourpetneeds.ie`, `redbarn.com`; preserved useful partial labels, not assertions of identical processing or manufacturer/reseller positioning.
- Brooklinen: `amorcustomgifts.com`; personalized quilts/duvets are a partial competitor, not evidence of linen-material equivalence for Parachute.
- Quince: `thezerano.com`, `arlingtontx.clothesmentor.com`, `wilkinsandolander.com`, `shoppandcboutique.com`, `shopworthandgray.com`.

No hidden useful store was credited from a broad category alone. In particular: infant formula is not baby lotion; adult merino base layers are not bamboo infant sleep bags; a Smart Keyboard type in a phone-case shop is not a mechanical-keyboard catalog; coffee tables are not coffee beans; a bath towel name without material or assortment evidence is not proof of linen bedding competition.

## Candidate generation versus filtering versus ranking

Counts below are **useful case/store misses from top5 per mode**, not aggregate counts double-counting the same store across modes.

| Stage | Description | Structured |
|---|---:|---:|
| Never entered candidate set | **0** | **0** |
| Entered, then filtered | **1** | **1** |
| Survived, scored too low without near tie | **0** | **3** |
| Survived, near-tied with nonuseful result | **3** | **0** |
| Total useful misses from top5 | **4** | **4** |

All four are Quince stores. In description mode the three ranking misses also have score gaps of at most **0.10 points** versus one or more top-five adjacent results. This descriptive near-tie definition does not assert that a tie-break change alone would put all three into the top five. The displaced results are **adjacent label-1 merchants, not clearly wrong label-0 merchants**. In structured mode none of the three has that near tie; the added query notes substantially favor other candidates.

| Useful Quince store | Description actual / uncapped survivor rank | Structured actual / uncapped survivor rank | Cause |
|---|---|---|---|
| Arlington Clothes Mentor | 8 / 8 | 6 / 6 | Ranked below top5 |
| Wilkins & Olander | not returned / 13 | 7 / 7 | Ranked below top5; description hits cap |
| Pomp and Circumstance | not returned / 11 | not returned / 18 | Ranked below top5 and top8 cap |
| Worth & Gray | not returned / filtered | not returned / filtered | `no_matched_product_terms`, score 0 |

Worth & Gray already enters candidate generation through saved metadata. Product titles say shirts, tops, jeans and sweaters, while Quince's general query says clothing/home/bags/jewelry. The current exact-token overlap does not establish that general-to-specific relationship. Its intent gate passes and its classification is supported; this is query/product vocabulary matching, not a wrong category or title-support rejection.

The generic scorer rewards token count and density; e.g. description-only Quince puts licensed merchandise and baby clothing ahead of useful general adult apparel. The existing ranking defect is real but **isolated to one query** in the useful-store audit. No ranking change is made here.

[Useful-miss traces](useful-misses.json) retain all scores, exclusions, candidate/pre-filter ranks, actual return ranks and competing scores.

## Positions 6–20

The endpoint stops at eight results. It would be incorrect to pretend it actually returned positions 9–20. [Near-miss evidence](near-misses.json) therefore records both:

1. Actual **pre-filter candidate** ranks 6–20, including rejected stores.
2. Diagnostic **post-filter, uncapped** ranks 6–20, retaining the exact same score ordering and filter decisions, lifting only the presentation cap for inspection.

Only Quince has useful survivors in positions 6–20: three in either mode. Pomp and Circumstance is candidate rank 23 in structured mode but survivor rank 18 after exclusions; inspecting only raw candidate ranks 6–20 would miss it. All other queries have no useful candidate lurking below top5. This is not a repeated cross-niche ranking problem.

## Classification contribution

Only the previously flagged **8 subcategory, 14 mixed-catalog and 3 primary-category** V2 records were revisited. [Classification contribution](classification-contribution.json) records each one, its defect, useful pairs and missed useful pairs.

**Zero of these 25 records has a demonstrated useful pair for the 25 frozen businesses; zero useful benchmark misses is attributable to those defects.** They are adjacent or irrelevant here even when their actual products are judged independently of the wrong label. Correcting music albums from Kids Apparel, poultry supplies from Cosmetics or lunch bags from Snacks will improve general data quality and prevent noise; it cannot create a keyboard, baby lotion or ultralight tent seller in this snapshot.

This is an intersection-based relevance conclusion, not a claim that classifiers are generally accurate or that defects never matter for other queries. No category repair/counterfactual database mutation was performed. The useful Quince stores have supported classifications.

## Next bounded action and uncertainty

**Recommend B: a separately approved 500-domain isolated V2 batch**, preserving all existing verification/confidence/protection gates and fixed benchmark comparisons. Do not expand or enable the worker as part of this task.

At the observed **54/100 eligible** yield, 500 new canonical domains have a point estimate of **270 additional eligible stores**. A Wilson 95% interval for the underlying pilot yield is **44.3%–63.4%**, corresponding to **221–317 expected eligible stores** out of 500 if the next sample and conditions are comparable. Rounded planning range: approximately **220–320**. This is sampling uncertainty for the yield estimate, not a guaranteed future-count interval. Candidate-selection bias, transport changes, duplicate overlap and different category composition could produce a wider real range.

Eligibility is not relevance. Expansion should use predeclared, broadly diverse business cohorts with preserved raw evidence, not hand-pick named benchmark competitors or promise all 270 help these queries. Report cohort composition and useful yield separately. Keep the frozen benchmark evaluation-only and keep this fixed-supply analysis as the control. No paid AI, production integration, ranking tuning or lowered confidence gate is required to test the coverage hypothesis.

## Reproduction and validation

Run from the repository root with the retained local pilot artifacts present:

```text
python -X utf8 tests/evaluations/fixed_supply_ceiling.py
python -m pytest tests/test_fixed_supply_ceiling_analysis.py -q
```

The analysis blocks network connection functions and reads saved JSON/SQLite bytes only. It does not query SQLite or write the original evidence. Application `relevance()` outputs are re-evaluated and asserted identical for every saved candidate; no endpoint/AI call is needed. All **132 recorded SQL-channel memberships** across both modes are reproduced locally and asserted equal to the retained PostgreSQL retrieval evidence. The actual result list is asserted equal to the first eight unchanged survivors in every run.

Integrity checks cover the complete 2,200-pair matrix, label continuity, 50 query/mode traces, consistent denominators, one failure stage per miss, actual versus uncapped ranks, the 25-store classification intersection, original supply byte equality and raw SQLite SHA-256 `6c5b00b34188892f87cba9a6a7b6ede520c4d237d547f14264236e10538c5a26`. Full input hashes are in [summary.json](summary.json).

Local validation: **5 analysis accounting tests passed**; full backend suite **463 passed, 9 skipped, 11 existing deprecation warnings**. The nine skips are Linux-specific on this Windows host. No new Linux image or validation workflow was needed or run for this analysis-only change. `git diff --check` passed.

No application code, V2 code, confidence threshold, supply, original benchmark label file, pipeline activation, production configuration or production data changed. Worker state was untouched. No push or deployment was performed.
