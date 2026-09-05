# Direct-access discovery evidence

Run offline utilities from `docs/quality-audit/real-world/` so relative `evidence/` paths resolve:

```sh
python3 evidence/analyze_census.py
python3 evidence/measure.py
```

These recompute the exact census and metrics from saved data, without network or database access. They rewrite generated summaries, so use a disposable copy for verification. `replay.py` and `prepare_replay.py` now locate their containing repository instead of a transient workspace path; this is the only change to their execution logic. The originals remain byte-for-byte in `../StoreScout-Discovery-Evidence.zip` and their hashes are in `ARCHIVE-MEMBER-SHA256.json`. Use the project’s Python dependencies to run the original endpoint replay. All application files must match `measured-manifest.json` for an original-baseline claim; a later code revision is a new comparison.

Canonical unchanged reference data: `../reference-panel.json`. Historical source baseline: `../baseline-manifest.json`. The duplicate copies in the archive need not be repeated here. The ZIP’s original README refers to its own historical paths/layout; this README describes the repository layout.

- `index-snapshot.json`: 38,221 allowlisted public business/catalog rows in original PostgreSQL export order. No contacts/customer profiles/credentials. Missing top-level null keys are restored by the adapter.
- `census-initial.json`, `export-end.json`, `export-projection.txt`, `census-analysis.json`: schema/census/export provenance, reconciled timestamp hash, full distributions and duplicate candidates. Multi-transaction pagination was not atomic.
- `retrieval-readonly.sql`, `retrieval-postgres.json`: actual PostgreSQL predicates and captured candidate order. JSONB DNA overlap error is reproduced, not silently fixed.
- `replay-results.json`: all 25 cases in two modes, interpretation/context, per-channel candidates, exclusions, rank scores and original responses. No live endpoint/paid AI was invoked.
- `relevance-labels.json`, `benchmark-metrics.json`, `case-metrics.csv`: all 331 returned placements and 50 case/mode measurements. Single-analyst relevance labels, with useful-partial/unknown caveats. The original references were not changed from output.
- `health-sample.json`, `public-health-summary.json`, `classification-review.json`: sample weights/strata, estimates/uncertainty and category review.
- `public-evidence-compact.json`: all 353 observed domains with dated factual HTTP/redirect/catalog/platform flags and bounded product examples. Population health rates can be recomputed from these flags and sample weights; raw text is not necessary for that arithmetic.

The public-check, label-review and health-summary scripts preserve original methodology; some require the intentionally excluded temporary raw observation bodies. Do not run them as if they could regenerate the original web content. Saved factual observations and finalized judgments are the evidence. A fresh website check changes the observation date and requires separate labeling. No private-network targets, password bypass or bot-challenge bypass was used.

`measured-manifest.json` identifies the frozen original run. `HANDOFF-SHA256.json` records current repository evidence bytes, including the path-only utility adaptations, separately from original archive hashes. The newer documentation commit must not be substituted for the original application baseline. Source-default thresholds were used; deployed environment overrides, alternate phrasing, paid AI and authenticated graph/tracked histories remain unmeasured.
