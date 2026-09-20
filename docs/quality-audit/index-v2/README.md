# Isolated V2 index pipeline — local implementation, production disabled

Prepared September 19, 2026 (measurement September 20 UTC). Branch `codex/index-v2-isolated-2026-09-19`, based exactly on `2bebccd30fb9a95ad9192cc0df6f81e9f28a1ff0`. The final response records the candidate commit. No push, deployment, paid service, production mutation, legacy migration, or canary activation occurred.

Files changed: `index_v2/` contains identity/import, schema, queue/leases, transport, child/supervisor, CLI, metrics and export modules. `app/services/store_index.py` exposes existing catalog/classification computation through pure adapters while retaining the legacy guarded wrappers. `scripts/store_index_v2.py`, the explicit Docker target and LF executable attributes provide startup; `scripts/validate_index_v2_image.sh` and `.github/workflows/index-v2-image.yml` provide the unrun Linux gate. `tests/test_index_v2*.py` cover regression/process behavior; `tests/evaluations/index_v2_*.py` and the optional-input extension to `index_growth_retrieval.mjs` provide measurement and unchanged-ranking replay. This directory holds the bounded source export, disabled manifests, evidence and runbook. No frontend, dependency lock, legacy migration, baseline result, canary manifest, or existing release branch was edited.

## Decision and isolation boundary

Run one standalone Python supervisor with a **separate SQLite database on its own Render persistent disk**. This is the smallest complete isolated store/queue implementation: no Supabase migration, no Redis broker, no Celery, no legacy HTTP verifier, no paid model, and no customer Discovery connection. The database is `/var/data/store-index-v2.sqlite`. Only its supervisor persists results; public-fetch/classification children receive public JSON, not a database handle or path. The worker owns completion rather than an HTTP request.

The new SQLite tables are `store_index_v2`, `store_verification_v2`, `store_classification_v2`, `jobs_v2`, `provenance_v2`, `batches`, and `events_v2`. [001_initial.sql](../../../index_v2/001_initial.sql) is **SQLite-only** and must never run against Supabase. Initialization is explicit, transactional, schema version 1, and refuses an existing file. Connections enable foreign keys, WAL, FULL durability, and a five-second busy timeout. Seed import is one idempotent transaction.

Render persistent disks support a single running service instance, are unavailable during builds/predeploy, and cannot be shared with another service. This deliberately forgoes horizontal scaling and direct API serving. SQLite's backup API produces portable consistent snapshots; copying an open database file or blindly restoring a disk snapshot is not the recovery procedure. [Render disk documentation](https://render.com/docs/disks).

V2 uses existing Phase 1 catalog/lifecycle/classification functions through injected transport and pure classification adapters. Existing legacy wrappers still enforce their deployment hold and perform their original version-checked writes. The legacy hold stays enabled; V2 has its own separately approved activation (`INDEX_V2_ENABLED=true` **and** exact `INDEX_V2_MANIFEST_SHA256`). Manifests remain `enabled:false`; importing one never starts processing. This is a new isolated execution authorization, not a release of the old pipeline hold.

At startup V2 refuses inherited Supabase, database, Redis, Celery broker, internal API, Anthropic, Stripe, or Resend credentials. Children get a minimal allowlisted environment with the legacy hold true and an import guard refusing service clients, application/API startup, and Celery tasks. No runtime call reads legacy tables or queues. Legacy Web can continue its current behavior without access to this disk or V2 queue. V2 does not remove the unresolved risk from a future migration of the legacy shared tables.

## Identity, seed, ownership, and failure accounting

Canonical identity is lowercase IDNA hostname with only the leading `www.` removed. It is established **before** any queue insertion. Original hostname, source index row identifier, source attribution, and source update timestamp are retained in provenance. Apex and www share one primary-keyed job across manifests. If explicit evidence indicates different storefronts, preparation stops for review rather than silently creating two jobs. Other subdomains are not merged.

The read-only [seed query](seed-query.sql) selected 4,500 canonical identities from the existing `discovered` index backlog with deterministic salted ordering and retrieved all corresponding aliases: **4,518 source hostname rows → 4,500 jobs**. It did not repeat the funnel census. [Source export](seed-source.json) contains public index domain/provenance fields, not customer data. The Python preparation step deterministically orders and bounds these exported identities again; source hash and exact membership travel in each manifest.

| Prepared manifest | Canonical stores | Attempt cap | Wire reservation cap | Canonical-JSON SHA-256 |
|---|---:|---:|---:|---|
| [Pilot](manifest-100.json) | 100 | 300 | 2,400 | `3e72d96bc8d513e43175fe7d8f40c57dbdc6f3bbb7b9ec89230b7b94b9e34a8a` |
| [1k-eligible target](manifest-4500.json) | 4,500 | 6,750 | 54,000 | `845597fdaa91fba020b0c083ceb5614c0df6d0f07c48fc8294c62b937cccadf2` |

Both expire **2026-09-26 23:59:59 UTC**, target 1,000 eligible V2 records, and are disabled. A 100-store pilot can only consume its bounded membership, regardless of that target. These are V2 manifests, not a recreation of the old 12-store canary. Hashes use `index_v2.identity.digest`, not formatted-file bytes. An expired manifest requires another reviewed preparation, never a silent date extension.

Overlapping imports never reset job ownership, attempts, saved results, or original batch membership. If the pilot runs first, those 100 jobs retain the pilot budget and retry schedule when the larger manifest is imported. Its eligible outcomes count toward the global 1,000 target; the other 4,400 jobs belong to the larger batch. Switching the active manifest does not run both simultaneously. Across both manifests the theoretical reserved allowance is 7,050 attempts / 56,400 wire requests, but each job remains capped at three attempts and only one manifest runs at once. Approve their budgets separately; do not describe the two-stage rollout as a shared 6,750 cap.

Lifecycle: pending → claimed → verifying → verified → classifying → eligible/ineligible. Failed verification has a named access state and a future due time. `BEGIN IMMEDIATE` atomically acquires an owner token, records the attempt and reserves its request allowance before dispatch. One active owned job is permitted across the database. A 180-second lease renews every 20 seconds. Completion checks owner, attempt and unexpired lease; stale owners cannot commit. An identical completion is idempotent.

If verification was durably saved before interruption, the next authorized owner resumes classification from that saved observation without a second fetch. An interrupted verification becomes `interrupted_unknown`, keeps its full request reservation, and waits at least an hour. A supervisor failure pauses the batch for review rather than allowing Render restarts to silently resume it. Paused batch recovery requires an explicit operator decision; importing the same manifest never clears its pause. Unknown requests are never counted as zero or refunded.

## Verification and classification bounds

| Guard | Reviewed value |
|---|---|
| Concurrent jobs / child stages | 1 / sequential verify then classify |
| Minimum verification starts | 10 seconds apart |
| Wire requests | At most 8 per verification attempt, including redirects |
| Intra-attempt pacing | At least 1 second between wire starts |
| Internal transport deadline | 75 seconds; DNS included in outer child bound |
| Child wall deadline | 90 seconds per stage; parent terminates then kills after 3 seconds if needed |
| Linux child limits | 320 MiB address space, 60 CPU seconds, 2 MiB output, parent-death SIGKILL, 90-second alarm |
| Whole-service operating ceiling | 400 MiB cgroup usage, checked before jobs and during children |
| Response body / public input-output | 8 MiB per response / 2 MiB |
| Disk stop | Less than 512 MiB free |
| Per-domain verification attempts | 3, also constrained by manifest/global reserved budgets |
| Classification | Free deterministic reviewed classifier and DNA fallback, threshold **55** |

Transport uses the existing curl-cffi/Chrome120 configuration and headers, explicit certificate verification, no environment proxy, no retained cookies, and manual redirects. Resolved IPs must be public and are pinned per request; redirects outside the www/apex identity are rejected. No browser challenge solving, proxy rotation, paid AI, or new evasion behavior is introduced. Challenge/429/password responses stop further access; an optional collections failure does not invalidate an already-readable product catalog. The four catalog endpoints all use the injected bounded transport, covered by a regression test forbidding legacy `_get` and Redis pacing.

Verification requires the reviewed readable product-catalog evidence and confidence ≥60. Retry timing reuses Phase 1: temporary/probable/ambiguous start at one hour; blocked/password/no-catalog/unavailable start at 24 hours; doubling up to seven days plus deterministic 0–600-second jitter. Definitive non-Shopify/dead-domain states wait 30 days, beyond these manifests. A longer Retry-After always wins. No failure is promoted to success. Three-attempt limits do not override cooldowns.

Each successful verification immediately enters free classification. Attempted/saved timestamps, confidence, eligibility, exclusion, and child runtime/memory measurements are persisted separately. Weak classifications are saved ineligible; there is no repeated paid call or forced threshold pass. Changing their evidence/reclassifying later requires a reviewed follow-up, not a fabricated category. Saved observations keep their real timestamps.

Automatic batch pauses include: invalid child output or identity/signature, lease loss, child failure/timeout, interruption, memory ceiling, disk headroom, and access failure rates after at least 20 completed attempts (>30% blocked/password or >25% temporary/unknown). These gates can stop a low-yield batch well before its capacity estimate. Expiry, target attainment and exhausted budgets prevent new claims. Manifest expiry stops dispatch; an already-owned bounded attempt may finish after expiry, still within its reserved allowance.

## Measured local validation

[Local measurement](local-measurement.json) replays **36 already captured successful catalogs** through real supervised classification child processes and the new SQLite persistence path. It makes no merchant requests and does not repeat the prior diagnosis. Catalog observation timestamps were retained. A synthetic queue clock skips the 10-second dispatch interval solely to measure processing overhead.

- 36 verification checkpoints recorded, 36/36 classifications saved, **20/36 eligible (55.6%)**, 16 honestly excluded.
- Initial measured run: **16.8 seconds total**, 2.14 rows/second including SQLite commits; classification child mean 0.455 seconds, max 0.523 seconds. The JSON artifact is authoritative if a final re-run differs.
- Reopening SQLite and importing the same manifest created zero new attempts; backup validation succeeded.
- Backend suite: **427 passing**, three Linux-only tests skipped on Windows, 11 existing deprecation warnings (final console/report supersedes if counts change).
- Regression coverage includes the legacy 100-row www-head failure pattern (100www +100apex →100jobs/100attempts), lease expiry/stale writes, competing owners, restart at classification, exact replay, reserved budgets, Retry-After, protection/redirect stopping, no legacy transport, low-confidence persistence, credential isolation, real child shutdown, withdrawn eligibility exports, and backups.

**No Linux image was built here.** Docker/Podman are unavailable and WSL is not installed. [Validation-only workflow](../../../.github/workflows/index-v2-image.yml) and [script](../../../scripts/validate_index_v2_image.sh) are prepared locally, not published. They require exact approved SHA matching, build the explicit `index-v2` target from the immutable existing base and locked dependencies, compare source/dependency inventory, run full tests without network/production secrets, and exercise Linux resource guards, parent-death behavior, direct invocation, sustained disabled runtime, and TERM/INT. The original Docker default remains the scheduler target. No package/dependency changes were made.

Image ID/digest and Linux memory/transport runtime compatibility therefore remain **unproven release gates**. Windows throughput is not evidence of Render memory headroom or live yield. This report does not authorize deployment or claim production-ready validation has passed.

## First 1,000 eligible stores: capacity and cost

Use the previous measured samples only as sensitivity anchors, not a probability distribution. They had different transport/network conditions and selected populations. No fresh live V2 success rate has been measured.

| Scenario | Verify × classification pass | New eligible / 4,500 distinct domains, first pass | Distinct domains needed for 1,000 V2 eligible |
|---|---:|---:|---:|
| Adverse prior samples | 24/248 ×20/36 =5.38% |242|18,600|
| Planning assumptions |40% ×60% =24%|1,080|4,167|
| Favorable prior samples |36/49 ×20/36 =40.82%|1,837|2,450|

Planning budget 4,167 distinct domains ×1.5 attempts ≈6,251 raw attempts; retry load is included but **no recovery yield is credited**. The 4,500-domain manifest reserves at most 6,750 attempts. At assumed mean complete attempt-slot durations of 12/32/62 seconds, full-budget processing needs **22.5/60/116.25 hours** (300/112.5/58.1 attempts per hour). Ten-second start spacing gives an absolute dispatch ceiling of 360 attempts/hour, not a sustainable guarantee. Retry cooldowns, rate pauses, outages, and expiry add calendar delay; this is not a fixed drain wait or promise of completion. At adverse yield the first batch must stop without reaching 1,000.

Local classification is about half a second including child startup; external verification and access response rates are the unknown bottleneck. V2 adds **zero production Redis/Celery commands and zero Supabase queries/writes**. It uses local SQLite transactions, results and lease renewals. Per-response/body and disk ceilings bound retained volume, but no Render disk/CPU/egress load test has occurred. `python -m index_v2.cli metrics --db /var/data/store-index-v2.sqlite` reports outcome counts, observed vs reserved requests, classification pass/yield and child runtimes/RSS; aggregate Render cgroup memory, CPU, OOM/restart and disk measurements are still required at the pilot. Child RSS is not whole-worker memory.

Recommended **dedicated 512 MiB worker +5 GB disk: $7 +$1.25 = $8.25/month**, excluding applicable workspace, build, transfer and backup costs; paid classification $0. Budget one month for the first checkpoint rather than implying a guaranteed per-store cost. An illustrative 1–5 processing days is $0.28–$1.38 at a simple 30-day prorating assumption, but cooldowns and service retention make $8.25 the useful planning allowance. Check actual billing before purchase. [Official Render pricing](https://render.com/pricing), checked September20 UTC; [disk constraints](https://render.com/docs/disks).

Existing Worker1 could run V2 without any legacy Web cutover **only after** separately approved repurposing: remove all legacy credential/env-group inheritance, add its own disk, use the V2 command and reviewed release, retain single-instance execution and prevent restoration of Celery on that V2 disk/configuration. If it is already a paid $7 worker, incremental disk cost is $1.25/month. That path changes a validated inert service and complicates recovery of the old worker. A dedicated service is the clearer boundary for $7/month additional compute, and leaves Web/Worker1/Beat untouched. Do not increase concurrency to2 or purchase a larger tier without measured need. If 400 MiB is exceeded, pause and diagnose rather than silently upgrading.

## Coverage-only Discovery experiment

`index_v2.cli export --input LEGACY_PUBLIC_SNAPSHOT --output NEW_DIRECTORY` creates legacy/V2/combined eligible inputs under one clock, hashes, and canonical deduplication. V2 eligibility requires both the durable queue flag and the reviewed current catalog/classification gates. Combining chooses the latest eligible observation per canonical identity; stale/ineligible retained payloads cannot re-enter. Original inputs and frozen judgments are not edited.

Run:

```text
node tests/evaluations/index_growth_retrieval.mjs ../storescout-phase1 NEW_DIRECTORY/experiment.json
python -X utf8 tests/evaluations/index_v2_benchmark.py NEW_DIRECTORY
```

The exact existing 25-business queries, PostgreSQL retrieval channels, matching and ranking are reused. Scores include P@5/P@10, reference recall, useful/wrong rates, ≥3 useful top5, and niche breakdowns. Newly placed domains require explicit `new-judgments.json`; unknown placements are not credited, and metrics remain provisional until adjudication. Canonical aliases do not silently inherit a different domain's judgment. Replay variants run in separate processes so frozen no-network guards cannot interfere with later Windows event loops.

Tool wiring was exercised with an empty legacy test input and the **20 eligible captured rows**, not a new production checkpoint: 75 SQL channels and50 case/mode replays per variant, zero endpoint errors, three unadjudicated placements in each nonempty variant correctly flagged. These smoke-test scores are not presented as Discovery improvement. No new 1k/5k/10k supply exists yet. The previous current/frozen benchmark artifacts remain untouched; this task did not repeat that benchmark or modify customer ranking.

## Exact proposed production sequence — not executed

1. Review this local candidate diff and SHA. Separately approve publishing a validation-only branch/workflow. Run the exact-SHA Linux workflow, retain image archive checksum/image ID/source inventory and passing tests. Stop if Linux limits, curl compatibility, signals, identity, dependency inventory or memory checks fail. Review any necessary fix in a new commit.
2. With separate production/purchase approval, create one dedicated background worker, 512MiB, one instance,5GB disk mounted `/var/data`, no env groups/secrets, auto-deploy off. Pin an immutable branch to the validated V2 commit. Use the repository Dockerfile and exact Docker Command `./scripts/store_index_v2.py` with no wrapper. The prepared image workflow builds both the explicit V2 target and ordinary Render-style final target, requires identical filesystem layers/no ENTRYPOINT, and exercises this exact override on the latter. Stop if that gate fails; no Render target-selection feature is assumed.
3. Start **disabled** with `INDEX_V2_ENABLED=false`, legacy `STORE_INDEX_DEPLOYMENT_HOLD=true`, old canary disabled; confirm exact source/image, PID1 Python direct executable, disabled log, zero database creation/network/jobs, and disk mount. Do not change Web, Worker1, Beat, their pins, environment or source.
4. After approved local-to-service file transfer, verify exact manifest digest/source hash; manifests are excluded from the Docker build context and must be transferred explicitly. Initialize only the new disk file: `python -m index_v2.cli init --db /var/data/store-index-v2.sqlite`. Import only the100-domain manifest: `python -m index_v2.cli seed --db /var/data/store-index-v2.sqlite --input /var/data/manifest-100.json`. Re-import to confirm unchanged counts. Record a SQLite backup. No legacy SQL is run.
5. Separately authorize the pilot by setting only V2 enable+manifest digest and restarting/deploying **the new service only**. Record process, cgroup memory, actual wire request count, access states, durable attempts, classification persistence, eligibility, pauses and restart events. No old queue runs. Do not proceed beyond the100-domain manifest because a raw count looks encouraging.
6. Stop/disable V2 after the pilot, wait for its bounded children or account for interrupted attempts, export aggregate metrics and a consistent backup. Approve expansion only if no ownership/identity/isolation failure, no OOM, complete accounting, and access/classification yield supports the next budget. Network/IP behavior is measured here; it cannot be inferred from this Windows replay.
7. If approved, transfer/verify/import the4,500 manifest and activate its digest. Existing pilot identities retain their state/budgets; no duplicated jobs. Stop at1,000 eligible, caps, expiry or any failure gate. Do not compensate for blocking by raising concurrency. Recheck freshness at export; durable eligible flags alone are insufficient.
8. Export V2 and legacy snapshots read-only, run all three frozen benchmark variants and explicitly adjudicate new placements. Keep V2 data out of customer Discovery until a separate integration review/approval. Legacy migration, acquisition and canary remain untouched.

## Stop/recovery

Stop the **new** worker if command/SHA/mount differs, any legacy credential/client/queue is present, unexpected legacy writes are attributable to V2, SQLite integrity fails, owner accounting is ambiguous, requests exceed reservations, DNS/redirect safety fails, memory/OOM/restart occurs, or automatic limits pause the batch. No automatic recovery into Celery or the legacy Web verifier exists.

Recovery preserves isolation: disable `INDEX_V2_ENABLED`, terminate only the V2 worker, retain its disk, database and WAL, record integrity/attempt/owner state, and take a SQLite backup. Normal shutdown terminates its current child, retains an unresolved attempt or resumable verification checkpoint, and pauses for review. After a crash, expired unknown verification retains its reserved budget; classification resumes from its durable checkpoint. Never reset counts or refund unknown requests.

For a paused batch, first inspect events and prove no old V2 supervisor/child remains; take a backup, confirm owners are expired and classify any incomplete attempt. A separately approved V2-only operator transaction may clear `batches.stopped_reason` for the exact digest once the cause is fixed. This is not a production command to run now. Reclaim then enforces normal expiry/quarantine and stale-write checks. Restoring a validated prior **V2** image with compatible schema preserves the current isolated environment; restoring an older database snapshot requires explicit reconciliation to avoid repeating requests. No legacy rollback, credential restoration, production Supabase migration, or customer data write is part of recovery.

**Next gate: approve validation-only publication and pass the exact Linux image workflow.** No production action is required to unblock that gate, and no legacy Web retirement evidence is needed for this isolated design. Real 1k-eligible execution still requires the separate service/pilot/expansion approvals above.
