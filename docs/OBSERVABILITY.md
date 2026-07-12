# Observability (production)

## What exists today

**Structured error reporting — `app/core/obs.py:report_error`.** Every
high-risk failure path funnels through it, emitting one greppable log line with:

- `operation` (route/task/feature, e.g. `ai.ask_storescout`, `task.scan_competitor`)
- `exc_class` (exception type)
- `error` (concise, **redacted** message)
- `user_id` (when safely available)
- `entity` (competitor / store / domain id)
- `degraded` (did we fall back?)
- `ref` (short correlation id, also returned to the client on 5xx so a user
  report maps to a log line)
- any extra key=value context (model, failure code, retries…)

**Redaction.** Messages are scrubbed for credential-shaped substrings
(`sk-…`, `sk_live_…`, `Bearer …`, JWTs, `token/secret/password/authorization=…`)
and hard-truncated (300 chars) *before* logging or forwarding — so API keys,
auth headers, integration credentials, full prompts, and complete scraped
storefront bodies never reach the logs. (Prompts/bodies are never passed in;
only concise messages are.)

**De-duplication.** Identical `(operation, exc_class, message)` errors within a
60s window log once at full level and then at debug — a broken dependency can't
flood the logs.

**Wired paths:** provisioning (`user.provision.*`), the shared Anthropic layer
(`ai.<feature>`), `safe_read` (degrading GETs), `guarded_required` (required
dossier routes → clean 503 + ref), scans (`task.scan_competitor`), and the
schema-health / scheduler fallbacks.

**Admin error summary — `GET /admin/error-summary`** (admin-token gated) and the
panel on the admin Store Index page: recent failures grouped by
`operation × exception` with a count, last-seen, latest `ref`, and a redacted
sample. **In-process only** (a `deque`, no new dependency): it reflects the API
process it runs in and is cleared on restart. Worker/scheduler failures appear
in that process's own logs (and, for scans, in the competitor row's
`error_message`), not in this API-process summary.

**Where to look in production:** Render → the relevant service → Logs. Filter by
`operation=` or `ref=`. The `ref` shown to a user (or in a 503 body) is the join
key.

## What is NOT enabled

**Sentry is not active.** `report_error` is Sentry-*ready*: if `SENTRY_DSN` is
set in the environment AND the `sentry_sdk` package is installed, errors are also
forwarded (with the same tags/extras). Neither is configured, so no external
capture happens today. Do not represent Sentry as live.

## To add external monitoring later (Sentry example)

1. `pip install sentry-sdk` — add `sentry-sdk==<pinned>` to `requirements.txt`
   (follow `docs/DEPENDENCIES.md`).
2. Initialize once at startup (e.g. top of `app/main.py` and the Celery worker
   bootstrap):
   ```python
   import os, sentry_sdk
   if os.environ.get("SENTRY_DSN"):
       sentry_sdk.init(dsn=os.environ["SENTRY_DSN"], traces_sample_rate=0.0,
                       send_default_pii=False)
   ```
3. Set `SENTRY_DSN` on each Render service (api, worker, scheduler).
4. `report_error` will forward automatically — no call-site changes. Cross-process
   aggregation and history then come from Sentry rather than the in-process
   summary. Keep `send_default_pii=False`; our messages are already redacted.
