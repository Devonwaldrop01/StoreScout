# Isolated release candidate validation

Authorized scope: local unconditional index hold plus a dedicated GitHub Actions
Linux image build. No Render change, migration, production write, or canary run.

## Deployment interlock

`STORE_INDEX_DEPLOYMENT_HOLD` is independent of the database enable override.
Only the exact value `false` permits index work. Missing, empty, invalid or
unreadable state holds writers. No new production environment value is required
to start the release held. Canary activation remains separately disabled; even
an enabled canary cannot bypass the hold.

The guard covers all index Celery tasks (including legacy/manual/force paths),
Beat publication, retries, delegated requests, verification/renewal, knowledge,
candidate generation, tracked-scan index enrichment, inspector/seed/reclassify
routes and index-related bookkeeping. Database mutations are checked again at
execution, including prepared requests. Read-only discovery and unrelated
customer tables retain their existing behavior. Held web writers return 503;
held worker deliveries finish with a deployment_hold result rather than creating
a retry backlog. Subsequent normal schedules resume when explicitly released.

Lease release always remains available. An interrupted stage releases its owned
Redis lease in finally; dead processes retain only bounded TTLs. Interrupted
row claims remain protected until their existing five-minute deadline and then
become retryable. Do not delete another process's lease or bulk-clear row tokens.

This is a process-local interlock, not a retroactive distributed transaction
barrier. It cannot stop the currently deployed old code or retract a database
request already sent. A future approved migration still requires draining old
web/worker writers and confirming zero in-flight writes. Environment changes
must reach every intended process before relying on them. Reverting to the old
image removes this interlock: keep old writers stopped during rollback.

## Checks before publication

- 378 hermetic Python tests pass, including 53 hold cases.
- Frozen and controlled benchmark replays preserve all 100 ranked lists, with
  earlier outputs unchanged. Replay artifacts: outputs/release-validation.
- Offline PGlite checks pass on the 38,221-row baseline and reconstructed
  54-column production schema, preserving row counts, domain uniqueness and RLS.
- Compile checks, pip check, shell syntax, workflow permissions and diff checks pass.
- Main remains 288223a2acb62bd6893e3370268f854bb2e16b12.
- The original 12-domain manifest is unchanged. It expires September 8 at 21:13
  UTC; expiration cannot be silently extended. Canary preflight must be refreshed
  under separate approval before execution.

## Image validation contract

Only pushes to codex/release-validation-2026-09-08 trigger the new workflow.
Checkout uses the triggering SHA, with persisted credentials disabled. The
workflow has contents:read only; it references no repository secrets, production
environments, deploy hooks or registries requiring production credentials.

Docker builds the existing final scheduler target for linux/amd64, with explicit
web/Worker 1/Beat command overrides matching the captured architecture. The
Playwright base is pinned by digest. Application dependencies are constrained to
the tested versions, with the Linux-only uvloop dependency explicitly pinned.
The build checks all installed application packages against these constraints
and compares every /app file to a Git-derived inventory.

Tests run against this image with test packages mounted separately and outbound
network disabled. Schema tests use PGlite and recorded metadata only. Startup
tests use a disposable Redis TLS server on an internal Docker network, with a
test certificate and offline Supabase URL. Real worker startup, web maintenance
response, Beat startup, TLS certificate/hostname verification, two-process lease
exclusion and renewal/release recovery are checked. No catalog jobs are sent.
The final immutable image tar, its checksum, source SHA and logs are retained
as an Actions artifact for 14 days. No image is deployed by this workflow.

The image gate remains pending until the exact published SHA finishes all these
checks. A successful local suite alone does not authorize rollout.

The first isolated run exposed an inherited orphan Git submodule entry at
`.claude/worktrees/laughing-dewdney-a9b2f0`, without any .gitmodules mapping.
It prevented Actions checkout cleanup. The release removes only this stale Git
index entry, preserving the local directory, and ignores local Claude worktrees
in Git and Docker packaging. No application source was removed.

The inventory gate also identified previously committed generated PDFs under
app/outputs. Docker now excludes generated output directories at every depth.
The approved manifest uses CRLF bytes: a file-specific Git attribute disables
line-ending normalization so Linux receives its original SHA-256 exactly.
Both manifest and migration byte digests are enforced before and inside builds.
Pygments, a transitive runtime dependency of rich, is constrained to the already
tested 2.21.0 version as well.

## Remaining production gates

After image success, recheck deployed source/configuration, migration checksum,
rollback artifact retention and hold/drain mechanics read-only. Saved Redis URL
corrections were previously verified on all three services; they are not proof
that old processes have adopted those values. Revalidate during an approved
deployment. Preserve all existing batch/concurrency limits.

The next production step requires fresh approval: disable automatic deployment,
hold/drain old writers, reconfirm rollback points, apply only the reviewed
additive lifecycle migration transaction, then deploy the exact reviewed release
web → Worker 1 → Beat. Keep the new interlock enabled and canary disabled.
Stop on drift, in-flight writers, TLS/lease errors, schema incompatibility,
unexpected writes, health errors or unavailable rollback artifacts. Rollback
keeps the additive schema; old images must remain externally held because they
do not implement the new guard. No schema downgrade or queue/lease purge.
