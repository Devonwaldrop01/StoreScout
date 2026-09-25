# 500-domain expansion — STOPPED INCOMPLETE

September 25, 2026 UTC. **The stop policy fired on domain 9. No automatic retry or expansion is authorized by this report.** The isolated V2 service is disabled and the batch remains paused. This is not a completed 500-store experiment.

## Identity and unbiased selection

- V2 application: `f2ae2e8ebdba902eead2aa376e845da530259c4e`, unchanged.
- Discovery-quality/evaluation baseline: `34b550436ca8a4bf670e17123dcdd26d03ede750`, unchanged.
- Registry image: `ghcr.io/devonwaldrop01/storescout-index-v2@sha256:9c88545592aebe38db653c4d9ffd0cad02dda767fce5e06872096d42d676f385`.
- Validated image content ID: `sha256:5d64ab78d3f73a96978f4cd2910c306247aec1382e40e676d33418b4b1232a38`.
- Existing isolated worker: `srv-dap3qh2jnfac73aedmr0`, command `./scripts/store_index_v2.py`, one instance, existing 1-GB `/var/data` disk.
- [Manifest](manifest-500.json): exactly 500 additional canonical domains. Batch digest **`53a05af3f1551a12a79ade3768e011cd559e5857b847a0e4782efa54d3696c37`**; file SHA-256 `0da48df0a394a6a520947c14ae02d3c4510841da501874d8fd4d0ea1d4f325db`.
- [Selection receipt](selection.json): first 500 remaining entries in the original 4,500 manifest order, excluding the original 100 and every existing V2 job, canonical-deduplicated. No benchmark, merchant category or relevance criterion was used. The source positions and source hash are retained.
- Manifest frozen locally in commit `51b4b05` before activation. No branch was pushed. Membership order is the source selection order; the unchanged worker processes available first attempts alphabetically.
- Concurrency 1; 10-second minimum start gap; 8 requests/attempt; 3 attempts/domain; 1,500-attempt and 12,000-request ceilings. Same 90-second child deadline, 180-second lease and 400-MiB memory limit. Manifest expiry unchanged from the source: September 26 23:59:59 UTC. JSON `enabled` remains false; runtime authorization used only the new manifest digest and enable flag.

Before import, all 363 retained source-file hashes matched the image inventory. Runtime isolation checks found no prohibited legacy credentials. All 100 prior identities were accounted for, with 102 attempts and no active leases. The pre-expansion SQLite backup hash exactly matches the original pilot backup. Import was idempotent and left the 100 pilot jobs unchanged. No paid infrastructure was created or upgraded; existing recurring rate remains $7.25/month. No paid AI was used.

## Trigger and containment

- Activation deployment: `dep-daquh7jncjis73ben9f0`, live at **03:21:22 UTC**, exact registry digest above.
- Active instance: `srv-dap3qh2jnfac73aedmr0-z9fdg`.
- Ninth verification: **`5to9vibe.com`**, claimed **03:23:19.450 UTC**.
- At **03:24:49.531 UTC**, the supervisor persisted `supervisor_stopped_child_timeout` and batch `stopped_reason=child_timeout`. Runtime traceback confirms the 90-second guard in `index_v2/worker.py:71` raised `ChildFailed: child_timeout` during **verification**, before classification.
- Render recorded **one automatic process restart** at **03:24:51.053 UTC**. The persisted pause prevented another claim: attempts stayed at nine through the restart and shutdown.
- The monitor detected the pause at **03:25:02.901 UTC**. V2 enable was saved as false at **03:25:22 UTC**; disabling deployment `dep-daquj8nlot8c73dpcj20` used the same image.
- New instance `srv-dap3qh2jnfac73aedmr0-btkl5` logged **`STORE_INDEX_V2 disabled; no jobs or application initialized`** at **03:25:36.537 UTC** and became live at 03:25:37 UTC.
- Final read-only check at **03:31:12 UTC** confirmed disabled, nine attempts, 30 recorded requests, unchanged pilot counts and the same pause. The new instance process tree contains disabled PID 1 and inspection/SSH processes; no verification/classification child was present.

The **trigger is confirmed**, but the underlying cause of the long verification is not. There is no retained ninth-child result or child stderr to identify DNS, transport, parsing, remote delay or CPU contribution. Do not call it a Shopify block, silently extend its deadline, change request protections, or skip the store and resume.

The supervisor did not commit a false result. One expired owner row remains in `verifying` for the terminated attempt, with lease expiry **03:27:39.731 UTC**. It is a retained accounting marker, not evidence of a still-running child. We did **not** clear that row, reset attempts, refund requests, clear the batch pause or replay the store. These actions require a separately reviewed recovery decision.

## Partial funnel — not a final batch yield

| Measure | Observed |
|---|---:|
| Imported canonical domains | 500 |
| Unique first attempts | 9 |
| First attempts with completed outcomes | 8 |
| Unattempted | 491 |
| Retry attempts | 0 |
| Verified readable | 7 |
| Temporarily unreachable | 1 |
| Verification timeout, outcome unknown | 1 |
| Recorded blocked / unavailable / unreadable / ambiguous / other | 0 each |
| Classifications attempted / saved | 7 / 7 |
| Eligible additions | 4 |
| Below confidence 55 | 3 |
| Partial eligible / attempted | 4/9 = 44.4% |
| Completed classifications eligible | 4/7 = 57.1% |
| Final 500-domain eligible yield | **Unavailable** |

Zero recorded failures in a category does not classify the unknown timeout. `12ozboxing.com` has the recorded temporary failure and retained retry time; `5to9vibe.com` has the unknown timeout. The original pilot's pending retries were not executed.

Confidence values: **0, 41, 54, 55, 90, 90, 100**; mean 61.43, median 55. Bins: 0 = 1; 1–54 = 2; 55–69 = 1; 70–84 = 0; 85–100 = 3. No threshold or classifier change.

## Requests, resources and persistence

| Measure | Interrupted expansion | Completed 100-store pilot |
|---|---:|---:|
| Eligible yield | Not established; 4/9 partial | 54% |
| Requests per verified catalog | **4.29–5.43 bounded range**, not exact | 4.11 |
| Completed domains/hour through stop | 138.1, tiny interrupted sample | 318.4 first-pass |
| Observed cgroup peak | 132.11 MiB | 121.61 MiB |
| Unexpected process restarts | **1** | 0 |

- **30 requests are recorded** for the eight completed attempts: 28 HTTP 200, one 302, one failed request with no HTTP status. The unfinished child returned no wire ledger. Its full **8-request reservation remains charged**. Total actual requests are therefore bounded at **30–38**, not proven exactly 30. All nine attempts retain **72 reserved requests**, within 12,000.
- No known per-attempt/request-cap violation; one unfinished attempt lacks exact wire accounting and is explicitly retained as unknown. No unknown request count was treated as zero.
- Execution from first claim to protection stop: **208.56 seconds**. Through disabled startup: **255.56 seconds**. Interrupted eight-completion throughput cannot validate capacity for 500 stores or update the pilot's 318/hour assumption.
- Saved pre-restart cgroup peak: **138,526,720 bytes**. The final old-cgroup peak was lost when the container restarted, so this is the maximum **observed** peak, not a guaranteed whole-run maximum. No OOM event was observed; the traceback specifically identifies the deadline exception.
- Render's two active-instance CPU samples were **0.285 and 0.357 cores**, mean 0.321. Cgroup sampling recorded at least 53.41 CPU-seconds before restart and CPU throttling on the existing 0.5-CPU plan. These observations do not establish CPU as the timeout cause and do not justify a paid upgrade.
- Consistent SQLite snapshot grew **884,736 bytes** (2,326,528 → 3,211,264), including new manifest/jobs/provenance and collected records. Maximum observed live files including WAL and pre-run backup: 9,683,035 bytes. After retaining the stopped backup, live files total 11,549,419 bytes. These are not pure catalog-payload growth measurements.
- Integrity and foreign-key checks passed. **Zero duplicate canonical jobs or stale completion events**. Exactly one retained expired owner/unresolved verification; no false clean-accounting claim.
- Every original pilot row remains unchanged across all seven tables: 100 index rows, 100 jobs, 100 provenance rows, 102 attempts, 96 classifications, 498 events and its batch record.

## Supply, benchmark and decision

The partial inventory contains **58 V2 eligible + 34 original eligible = 92 combined eligible stores**, with current eligibility and canonical deduplication checked offline. The original 88 supply and all frozen judgments remain unchanged.

**No expanded benchmark or new ceiling was run.** The user required the comparison only after batch completion; this batch failed its stop gate after nine domains. Existing controls remain:

- Original fixed 88, improved matching: P@5 14.4%; P@10 7.6% description / 8.0% structured; useful rate 48.7% / 51.3%; wrong rate 7.7% / 5.1%; reference recall 4%; three-useful searches 0/25.
- Original 88-store ceiling: P@5 17.6%, P@10 8.8%, three-useful searches 1/25; useful availability 13 zero / 5 one / 6 two / 1 three-plus.
- These are **prior results, not measurements of the new 92-store partial supply**.

**A/B/C decision deferred.** Nine attempted domains cannot establish source quality, sustained eligibility yield, relevance improvement or the path to ~1,000 eligible stores. The previous 54%-yield extrapolation is neither confirmed nor disproved; operational stability has failed in this expansion. Do not proceed toward ~1,000 eligible, alter matching/classification, or change acquisition based on this tiny partial sample.

Smallest next step: separately authorize a bounded isolated diagnosis of the ninth verification's 90-second failure using the exact image and retained evidence, then review a recovery/accounting procedure before resuming this same manifest. No timeout increase, protection weakening, skipped domain, new source manifest or application change was made here.

## Evidence and reproduction

- [Machine-readable reconciliation](stopped-audit.json), including each attempted domain, timestamps, outcomes, reservations and artifact hashes.
- [Raw stopped SQLite](../../../../outputs/index-v2-expansion-500/expansion-stopped-20260925.sqlite), SHA-256 **`f1cbc18c960532f2a9e9186613bbe3192175dd38fbcda685906ab5ad3f3a28f9`**; consistent copy also retained on the isolated persistent disk.
- [Complete runtime logs](../../../../outputs/index-v2-expansion-500/render-runtime-logs.json), [resource metrics](../../../../outputs/index-v2-expansion-500/render-metrics.json), [monitor samples](../../../../outputs/index-v2-expansion-500/monitor.jsonl), [final disabled state](../../../../outputs/index-v2-expansion-500/final-disabled.json).
- [Preflight](../../../../outputs/index-v2-expansion-500/preflight.json), [seed receipt](../../../../outputs/index-v2-expansion-500/seed-receipt.json), [backup/process receipt](../../../../outputs/index-v2-expansion-500/stopped-backup-receipt.json).

Run `python -X utf8 tests/evaluations/index_v2_expansion_500_audit.py` to reproduce read-only reconciliation against immutable local snapshots. Assertions verify unchanged pilot rows, manifest membership/digest, all nine attempts, completed request ledgers, classifications, event accounting, fail-closed pause, disabled state and artifact hashes. No network, pipeline invocation or benchmark is performed by that script.

Read-only before/after Render service metadata checks confirm legacy Web, Worker 1 and Beat configuration is unchanged. No legacy credentials, Redis/Celery connection, Supabase write path, customer data, migration or customer-facing Discovery change was introduced. No V2 application or matching code changed. Only the isolated worker's approved activation/disable flags, manifest import and V2 data/evidence changed.

**Stopped with V2 disabled; no further expansion or recovery performed.**
