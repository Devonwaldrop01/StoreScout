# Discovery evaluation protocol

> Preserved from the independent preparation report. No ground truth or acceptance threshold changed. The measured run used 25 cases in two modes; single-analyst review, alternate phrasing, and paid/live paths have the limitations stated in the measured results.

## Baseline and acceptance protocol

Freeze the actual index snapshot, schema, source hashes, clock, settings and reference labels. Replay ff555bb locally with paid AI, HTTP verification, queues and all writes disabled. Preserve exact retrieval predicates/projections/caps/fallbacks and record which stage loses each known competitor. The local code is not the currently deployed revision; report those separately. Do not call the live discovery endpoint under read-only authorization.

Measure padded P@5/P@10, strong-only precision, useful/returned rate, wrong/returned rate, unknown-label rate, known-reference recall, eligible-present retrieval recall and searches with three useful top-five results. Report every case and niche. The index path returns at most eight, so index-only P@10 cannot exceed 0.8. Do not make small result sets look strong by changing denominators. Reference recall is partial-market recall; independently judge useful returned brands outside the known set.

**Proposed early pilot gate:** P@5 ≥0.60; ≥80% of core searches have three useful top-five competitors; wrong-result rate ≤10%; unknown labels ≤5%; no multi-case niche has fewer than two-thirds of its cases meeting the three-useful standard. Preserve whole-family holdouts and reject material niche regressions. These thresholds are a proposed operational standard, not measured achievements or proof of customer acceptance. A second blind label review and user selection task should corroborate them.

No top results, false positives or misses from the real StoreScout index can yet be reported. Filling those columns with synthetic or researcher-created rows would invalidate the requested baseline.
