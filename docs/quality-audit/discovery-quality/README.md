# Discovery quality at fixed V2 supply

Decision: **B. Continue Discovery-quality work.** Do not expand the manifest. The smallest local correction reduces noise and preserves useful results, but does not yet deliver several useful competitors per business.

This branch is based on the unchanged V2 release `f2ae2e8ebdba902eead2aa376e845da530259c4e`. No V2 pipeline, classifier, confidence threshold, retrieval SQL/caps, ranking weights, SQLite schema, worker activation, production service or customer-facing code deployment was changed. The local Discovery implementation changes only two files. The worker remains disabled; this cycle made no Render/API calls, merchant requests, paid AI calls or database mutations.

## Complete diagnosis

The original V2-only result lists contain **60 case/mode/domain pairs across 18 distinct stores**. The combined lists contain 55 V2 placements. [Placement audit](placement-audit.json) accounts for all **115 occurrences**, including channels, original query/context, rank, score, matched tokens, intent families, label and classification concerns. To avoid counting the same pair twice, primary-cause totals below use the 60 unique pairs (both input modes). Eleven are useful; 49 are weak/wrong. These are mutually exclusive primary explanations; secondary classification/ranking contributions are recorded alongside each placement.

| Primary explanation | Unique pairs |
|---|---:|
| Beauty/skincare versus color-makeup subtype confusion | 16 |
| Accessory/core-product or product-text collision | 7 |
| Audience from one product combined with another product | 3 |
| Food preparation/use-case mismatch (dog bakery versus freeze-dried/raw) | 6 |
| Detached type label versus observed catalog composition | 5 |
| Audience/subcategory mismatch | 2 |
| Price or business-model mismatch | 3 |
| Legitimate adjacent seller with weak business fit | 7 |
| Useful supported matches | 11 |
| Total | 60 |

Exact causes established by code and saved traces:

1. **Per-item noun interpretation leaks.** The prior accessory exclusion recognized singular bag/dress forms inconsistently. Cosmetic bags passed as makeup; quilt-themed laundry containers passed as bedding. The store-wide family union then authorized unrelated results.
2. **Types and titles were interchangeable.** A detached Bedding type authorized a merchant whose sampled titles are overwhelmingly tiles, despite no supporting bedding title. The schema does not link each type to a specific title or preserve category frequency.
3. **Audience evidence was joined across unrelated products.** A baby gift description plus generic Lotion type could pass a baby-skincare query. Neither proves a baby lotion exists.
4. **Intent used the normalized union of description, category and profile notes.** The endpoint did not supply original query text to the intent checker. Incidental notes could change requested families or demographics. Raw query context is now passed explicitly; existing scoring keywords remain unchanged.
5. **Classification confidence is not primary-business confidence.** The classifier counts weighted dictionary hits and their margin. Unmatched products do not supply a true composition denominator; repeated accessory/theme/artist words can beat the limited vocabulary at high confidence. Longer-phrase handling helps only when the phrase exists in that dictionary. This explains high-confidence wrong/overbroad labels without proving stores are unusable.
6. **Scoring still rewards token overlap.** Existing relevance compares flattened product tokens, broad category and inferred audience/price. It cannot establish formulation, food preparation, materials or business-model equivalence. Weak adjacent matches can remain highly ranked even after hard contradictions are filtered.

No observed failure was attributable to a literal numeric price token collision. Price/business-model mismatches in the audit instead lack sufficiently precise comparable positioning. These are not evidence for changing price thresholds.

## Review of all 54 eligible stores

Every record is in [eligible-store-audit.json](eligible-store-audit.json), with category/confidence, subcategory, structured context, description, product types/titles, catalog observation, manually described niche and evidence limitations.

| Catalog review | Stores |
|---|---:|
| Category/subcategory broadly supported | 29 |
| Subcategory inconsistent or unsupported | 8 |
| Primary category too broad or mixed catalog poorly represented | 14 |
| Clearly mismatched primary category | 3 |
| Total | 54 |

The three clear primary mismatches are:
- meadow-nest.com: Beauty/Cosmetics at confidence 94 despite poultry supplies and cosmetic storage bags.
- kpopnw.com: Kids Apparel despite music albums/lightsticks/photocards.
- us.thesomewhereco.com: Food/Snacks despite lunch bags, snack containers and picnic goods.

Eight subcategory concerns and fourteen composition concerns are individually explained in the audit. Examples include men's apparel labeled Womenswear, adult merino apparel summarized as Kids Apparel, and musical strings/picks summarized by their merchandise clothing.

These are **classification concerns, not 25 invalid stores**. All 54 have saved readable product evidence and could be relevant to an appropriate query. None is globally blacklisted or removed from the fixed 88-store input. Raising the unchanged confidence threshold would not reliably remove confidence-94/100 mistakes and would discard legitimate evidence.

Metadata availability: all 54 have product titles; 2 lack product types; 9 lack descriptions. All have generated target/price labels, but those are coarse inferred labels, not verified age/use-case or comparable price positioning. All 54 lack a dedicated business-model field. Product types are distinct labels, not reliable sales/inventory shares. Captured titles are a bounded sample, not a full-catalog distribution.

Both classification and matching contribute. The first intervention is query-specific product evidence because it removes wrong recommendations without rewriting the proven V2 classifier or inventing business attributes.

## Smallest retained implementation

Application changes:

- `app/api/v1/competitors.py`: passes the original requested description as `sells` into intent matching. Structured profile keywords still inform existing scores; they cannot silently redefine the primary requested product.
- `app/services/product_intent.py`: handles plural accessory/color collisions, distinguishes non-bed uses of sheets/quilts, requires supporting sampled titles when titles exist, and links requested child audience to the same product item. Adds inspectable title-support counts and specific rejection reasons. Existing metadata/type-only and unrecognized-intent fallback behavior is preserved.

No store names, URLs, benchmark case IDs or judgment labels enter application logic. No category/confidence mutation, acquisition change, new database field, new model or ranking-weight tuning.

The independent tests cover fictional catalogs, singular/plural accessories, real complete products in mixed catalogs, title/type disagreement, child/adult cross-product mistakes, sparse legacy fallback, and endpoint behavior with unrelated profile notes. BB/CC creams, eyeshadow and tinted mineral sunscreen remain recognized as complete cosmetic products.

A stricter sun-care/color-makeup separation was tried and **discarded**: the saved titles do not always include tint/formulation evidence that the independent reference judgments establish. Rejecting all unspecified sunscreens removed an already-useful competitor from multiple queries. No merchant exception was added and no judgment changed to conceal that regression. Sun-care adjacency remains a documented limitation.

The retained title gate is conservative: proprietary names or an incomplete recent-product sample may miss a legitimate type shown elsewhere. Type-only rows retain fallback, but full item-level type/title/attribute association is a better future solution. This patch is a local candidate, not approval to deploy it.

## Fixed-supply results

The original 34-row existing snapshot, 54-row V2 snapshot, combined 88 rows and evaluation clock were copied byte-for-byte. Original pilot benchmarks and SQLite were not overwritten. [Comparison pack](benchmark-comparison.json) includes all aggregates, labels, cases, reference stages and niches.

**Description-only, all 25 businesses:**

| Metric | Original existing 34 | Original combined 88 | Improved combined 88 |
|---|---:|---:|---:|
| P@5 | 10.4% | 14.4% | 14.4% |
| P@10 | 5.2% | 7.2% | 7.6% |
| Known-reference recall | 4.0% | 4.0% | 4.0% |
| Useful-result rate | 50.0% | 36.7% | 48.7% |
| Obviously-wrong rate | 19.2% | 16.3% | 7.7% |
| Useful / returned | 13/26 | 18/49 | 19/39 |
| Obviously wrong / returned | 5/26 | 8/49 | 3/39 |
| Searches with ≥3 useful top-five | 0/25 | 0/25 | 0/25 |

**Structured-profile, all 25 businesses:**

| Metric | Original existing 34 | Original combined 88 | Improved combined 88 |
|---|---:|---:|---:|
| P@5 | 10.4% | 14.4% | 14.4% |
| P@10 | 5.2% | 7.2% | 8.0% |
| Known-reference recall | 4.0% | 4.0% | 4.0% |
| Useful-result rate | 61.9% | 35.3% | 51.3% |
| Obviously-wrong rate | 14.3% | 17.6% | 5.1% |
| Useful / returned | 13/21 | 18/51 | 20/39 |
| Obviously wrong / returned | 3/21 | 9/51 | 2/39 |
| Searches with ≥3 useful top-five | 0/25 | 0/25 | 0/25 |

The patch removes 5/8 wrong description-only placements and 7/9 structured wrong placements, while preserving every previously useful returned competitor. No case loses P@5. Additional useful results fill lower ranks, so P@10 improves slightly without increasing list volume. There is no supply increase or ranking treatment.

The frozen 24-core-case and holdout/control splits are included in the JSON. P@k remains padded; the index targets at most eight results. All 150 replay calls across three supplies and two modes completed without errors. Eight newly exposed case/mode/domain placements were explicitly adjudicated from retained product evidence; no unknown labels remain. Existing labels/reference sets remain unchanged; additional labels are one-analyst reviews, not a new blinded panel.

**Per-query changes:** [complete 50-row before/after CSV](per-query-changes.csv) and [ordered lists with added/removed results and labels](per-query-changes.json).

- Description-only: wrong counts improve for Tower 28, Saie, Pipette, Quince and ColourPop; Quince gains a second useful result below the top five.
- Structured: wrong counts improve for Tower 28, Saie, Pipette, Babo, Quince, Parachute and ColourPop; Quince gains two useful lower-rank results.
- All other query P@5/useful/wrong counts are preserved; the CSV also records changes in weak-result counts/order.
- Mechanical keyboard coverage remains absent. Several outdoor and baby/sleepwear queries remain empty or unhelpful.
- Only two of the 50 frozen reference relationships are present in the 88-store eligible supply. Their recall is preserved; absent references cannot be recovered by rearranging these rows.

## Tests, integrity and remaining limits

- Targeted product-relationship, bounded-cycle and core-quality suites: **94 passed**.
- Full local backend suite: **458 passed, 9 skipped, 11 existing deprecation warnings**. The skips are Linux-specific tests on this Windows environment; no new Linux image/push was run. Prior Linux V2 validation belongs to the unchanged pipeline release, not this new Discovery candidate.
- New independent regression cases: **29** in `tests/test_discovery_product_relationships.py`.
- `git diff --check` passed.
- Supply/clock byte equality, original SQLite hash, complete labels, no useful-result losses and no per-query P@5 loss asserted by `tests/evaluations/discovery_quality_comparison.py`.
- Raw pilot SQLite SHA-256 remains `6c5b00b34188892f87cba9a6a7b6ede520c4d237d547f14264236e10538c5a26`.
- Classification and pipeline source are unchanged; `index_v2/`, V2 startup scripts, lifecycle, hold, retry, lease, canonicalization and confidence rules are untouched.

The test suite is offline with network/client guards. Benchmark replay uses saved SQL retrieval channels with unchanged predicates, no database/network writes and the original query classification. New query-context behavior is exercised through the actual endpoint.

## Recommendation and next evidence needed

**B. Continue Discovery-quality work; do not expand by 500 yet.**

This correction is worthwhile, but the improved combined list is still only about half useful, P@5 is 14.4%, and zero searches offer three useful top-five choices. Sixteen original V2 beauty subtype pairs and several material/preparation/business-fit mismatches cannot be resolved reliably from current flattened metadata.

Next bounded work should retain product-level association and explicit provenance for the attributes that matter: product purpose (product versus container/accessory), audience attached to that product, cosmetic function/formulation, and preparation/material when stated. First test extraction against saved evidence and independent cases; keep unknown values unknown. Do not add a broad schema or infer missing attributes from merchant identity. Catalog-composition and primary-category calibration also need a separate fixed-supply experiment before any classifier change is adopted.

There is a real supply ceiling for absent keyboard/reference competitors, so matching alone cannot meet all benchmark goals. Nevertheless, current matching/classification uncertainty is the next intervention: adding more rows under the same weak semantics risks scaling the remaining noise. No production rollout or expansion is authorized by this report.

Reproduction uses the retained pilot artifacts: run `tests/evaluations/discovery_quality_audit.py`; copy the original snapshots/clock/retrieval channels into a separate output directory; apply only `new-placement-judgments.json` as additional labels; run `tests/evaluations/index_v2_benchmark.py` there; then run `tests/evaluations/discovery_quality_comparison.py`. Never rerun into the original pilot directory.

