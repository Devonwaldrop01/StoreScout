# Core quality audit — 2026-09-05

This source/evaluation pass extends local launch repair commit `70af98e`.
It makes no production/database/provider changes and authorizes no outreach.
The complete product and feature report is the separately saved
`StoreScout-State-and-First-Customer-Plan.md`.

## Reproduce the new regressions

Use the project's existing Python environment, with no real provider keys:

```sh
ANTHROPIC_API_KEY='' .venv/bin/python -m pytest -q tests/test_core_quality.py
```

The new file has 34 hermetic checks including parameterized cases. The earlier
related discovery/DNA/watchlist/claims tests were also exercised where touched;
72 targeted checks passed in total, not a new full-suite certification.
Frontend TypeScript passed. No repeat full build or live payment test was run.

## Evaluation artifacts

- `tests/evaluations/discovery_baseline.json`: before-change score/order on eight
  synthetic adversarial pools, captured at `70af98e`.
- `tests/evaluations/discovery_after.json`: same pools and human-supplied labels
  after the product-evidence scorer.
- `tests/evaluations/discovery_cases.py`: inputs, labels, pinned original scorer.
- `tests/evaluations/discovery_wording_holdout.json`: three additional wording
  challenges added after implementation; all still miss the supplied intended
  substitute. These failures are retained, not tuned away.
- `tests/evaluations/actual_catalog_playbook.json`: new deterministic candidate
  from the previously collected real, partial Allbirds sample, replayed at its
  observation time. No new fetch or invented historical event.

Platform verification is eligibility, not relevance. The initial benchmark
intentionally gives weak candidates higher platform confidence. Its improvement
is not live production precision, and each pool contains only two direct
substitutes. Overall discovery remains **Weak** until real index sampling and
independent relevance review are possible.

## Operational evidence still needed

`index-health-readonly.sql` contains unexecuted SELECT queries for the existing
schema. `feature-route-inventory.json` records source handler/page/job coverage,
not runtime success. Confirm schema availability and authorization before using
production credentials. No secrets belong in audit results.

## Material limits

- New minimum-price variant identity protects future snapshot pairs; non-minimum
  variant prices are not monitored, and older pairs without IDs remain uncertain.
- AI Playbook can order known candidate IDs only; no rich model strategy or
  private integration facts are used in this new engine. Public/manual context
  stays useful; structured provider adapters remain recommended work.
- Currency, catalog identity/coverage, queue/snapshot leases, outbox delivery,
  actual DB security and billing lifecycle remain launch gates.
- Keep local work unpushed until the owner approves any deployment consequences.
