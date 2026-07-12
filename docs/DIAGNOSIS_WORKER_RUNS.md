# Diagnosis — Store Index "Worker Runs" behavior

**Scope:** the staged index pipeline (`stage_discovery → stage_resolution →
stage_verification → stage_knowledge`) and the `store_index_runs` history shown
on the admin Index Operations page. Diagnosed on `main` @ `026298c`.

**Verdict: the pipeline is NOT broken and no data was corrupted.** The DB
status totals are accurate; the confusion is a **run-record accounting/display
bug** plus a **missing single-flight lock** that makes the run list ambiguous
(and would become unsafe if throughput were scaled without the lock).

## Writers to `store_index_runs`

1. `app/services/scheduler_status.py::record_run` — called by the
   `@scheduled_index_task(stage)` decorator after each staged task returns
   `status == "ok"`. **One execution → at most one row.**
2. `app/tasks/store_index.py::discover_shopify_stores_daily` (legacy, **no longer
   scheduled**; only fires from the admin `POST /run` button). It already holds a
   Redis lock (`lock:store_index_daily`).

No other writer exists. Reads: `scheduler_status`, `admin_brief`, and the admin
stats/ops endpoints.

## Root cause of `processed = 0` while `verified + rejected > 0`

`record_run` derived `processed` from the first present of
`processed|resolved|queued|classified|discovered`. **`stage_verification`
returned only `{verified, rejected, failed}`** (and `stage_knowledge` only
`{classified}`), so none of those keys existed → `processed` fell to its `0`
default while `verified`/`rejected` were written from their own keys. This is
**#1 (accounting/display only)** — not double processing, not a broken worker.

## The "two runs ~17s apart" and count reconciliation

- **Beat instances:** render.yaml defines exactly one `storescout-scheduler`
  (`celery beat`) service → **not #3.** (Owner: keep that service at 1 instance.)
- **Cadence:** `stage_verification` is scheduled at `:15,:45` (30 min apart), so
  two runs 17 s apart is not the schedule — it is a **manual `/run-stage`
  (force=True) overlapping a scheduled tick → #4**, made possible by **#5 (no
  single-flight lock on the staged tasks).**
- **Same candidates twice (#6):** the worker runs `--concurrency=1` on a single
  service, so today the two runs execute **serially** — the second drains the
  *next* batch from the large `discovered` backlog (~3,344 = 3,582 resolved −
  238 verified), **not the same rows.** So under the current config no store was
  processed twice. This is fragile: raising worker concurrency or adding a
  second `default`-consuming worker (the lever for more verified/day) **would**
  enable overlap and double-processing. The lock added here closes that before
  any scale-up.
- **Re-verification counted as new (#7):** no. The staged tasks only ever read
  `status='discovered'`, so a staged `verified` is always a first-time
  verification (`reverified = 0`). Re-verification exists only in the Store
  Inspector re-run and the legacy daily task.
- **Timezone (#8):** no. `ran_at`, `last_verified_at`, and the "today" boundary
  are all UTC ISO; the comparison is correct.
- **Reconciliation:** `verified_today` was computed by counting unique verified
  rows within a **capped 5,000-row sample** — accurate now, but it under-counts
  once the index exceeds 5,000 rows, and it measures *unique stores* while a run
  row's `verified` measures *this run's batch outcomes*. Those are different
  quantities and never line up 1:1. Combined with `processed=0`, the panel
  looked inconsistent. **No corruption** — status `COUNT`s (`3582/238/238`) and
  `added_today` (exact) are correct.

## `stage_knowledge` all-zeros — expected

`stage_knowledge` reads `verified AND knowledge_at IS NULL`. When `classified ==
verified` (238 == 238), that queue is empty → `{processed:0, classified:0}` → an
all-zero row. **Expected, not a fault** — it means every verified store is
already classified.

## Corrected Worker-Run semantics (one run = one execution)

| Column | Meaning |
|---|---|
| `processed` | UNIQUE candidates **attempted** this run. `= verified + rejected + failed + reverified`; never 0 while any outcome > 0. |
| `verified` | discovered → verified this run (**new**; staged pipeline only). |
| `reverified` | already-verified store re-checked (staged = 0). |
| `rejected` / `failed` | terminal negative outcomes. |
| `duplicates` | candidates skipped as already-present. |
| `trigger` | `scheduled:<stage>` or `manual:<stage>`. |
| `notes` | status/note + `task=<celery id>` for provenance. |

## Fixes applied

1. `stage_verification` / `stage_knowledge` now return an explicit
   `processed` (= attempted) and `reverified`; `record_run` also **derives**
   `processed` from outcomes as a floor, so the impossible state cannot recur.
2. **Single-flight Redis lock** in `@scheduled_index_task` (`lock:index:<stage>`,
   per-stage TTL, released in `finally`). Overlapping runs return `skipped_lock`
   and write **no** record. Fails open if Redis is down (worker is concurrency-1
   today). Makes it safe to raise throughput later.
3. Run records carry the real `trigger` (scheduled vs manual) and the Celery
   `task_id`; a skipped/disabled run writes nothing → one execution ≤ one row.
4. `verified_today` is now an **exact** DB count, correct past 5,000 rows.

## Answering "can we verify more stores/day?"

Yes — and it is now **safe** to. The throughput levers (do **not** change here;
recommended as a follow-up once the lock is confirmed in prod):
- raise `shopify_index_verify_batch` (currently small) and/or the `:15,:45`
  cadence — the backlog is ~3,344, so verification is throughput-bound, not
  candidate-bound;
- feed more candidates: `stage_discovery` + `generate_niche_candidates` /
  `generate_related_candidates`;
- only then consider worker concurrency > 1 — **the lock is the prerequisite.**
Cadence/concurrency are intentionally unchanged in this PR per the "don't change
cadence unless unsafe duplication is proven" instruction.
