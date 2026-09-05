# StoreScout restoration status — sanitized

## 3. Infrastructure restoration — sanitized operational record

Observation date: 5 September 2026; not a new live check. Private billing amounts/history, invoice/workspace identifiers and support-message text are intentionally excluded from the repository copy. The full private source remains with the owner.

The API, Celery worker and Beat scheduler were billing-suspended. Settling an account balance may resume background work; it does not establish application readiness. An information-only support inquiry was authorized earlier; the automatic-resumption behavior remained unresolved at that checkpoint. Do not pay, retry charges, resume/restart, deploy, or change configuration without the owner's explicit approval.

| Component | Recorded non-sensitive operational evidence | Remaining gate |
|---|---|---|
| API | Starter compute, roughly 512 MiB, configured one instance but stopped; `uvicorn app.main:app --host 0.0.0.0 --port $PORT`; port 10000; HTTP health-check path blank | Correct frontend/API routing, dependency health and safe startup |
| Task worker | Consumes `default,priority`; actual concurrency 2, while blueprint specifies 1 and recycling limits absent from the live command | Review drift before any approved change |
| Beat | Separate scheduler, not a second task consumer | Verify one active scheduler and controlled queue processing after approved restoration |
| Deployment | All three tracked GitHub main with automatic deploy enabled; last recorded deployed revision `e66e3f05417cea5d57f27800c755c2353ca2b791` | Local repairs and discovery baseline have not been deployed |
| Public routing | Apex/www and Render origin returned suspension responses; API subdomain had no DNS record; Docker serves an older root HTML page, not the Next.js build | Verify intended frontend deployment/domain layout before launch |
| Frontend | Earlier GitHub metadata identified separate Vercel deployments; current production target/aliases remained unverified | Direct authorized frontend check; failed local access does not prove Vercel outage |
| Supabase | Historical traffic showed successful database operations; subsequent real-index read-only census is now completed in the measured results | Auth/RLS, migrations, redirects, backups and customer-path behavior remain separate gates |
| Redis | Environment variable names and earlier queue activity existed; provider/current persistence/backlog unverified | Read-only dependency and backlog inspection before activation |
| Other providers | Anthropic requests previously failed for insufficient credit; Stripe/Resend variable names existed, values were not inspected | Explicit approval for funding/configuration; test billing and sender behavior separately |

Hourly historical samples reached roughly 504 MiB for API memory, 422 MiB for worker and 88 MiB for Beat. These were sampled peaks, not confirmed OOM kills. HTTP aggregates included 264 status-500 and 31 status-502 responses; they include internal/bot traffic and are not customer counts. Duplicate-domain inserts produced PostgreSQL 23505 errors; source read-then-insert is a plausible race mechanism, not proof of every failure. Task-framework success did not always mean successful catalog retrieval.

Preserve queued work and databases. Obtain the owner’s restoration decision through their private account record; then, only within approved scope, verify service state, application-level successful scans, queue consumption and resource headroom. Paying for hosting does not certify tenant isolation, billing correctness, discovery relevance, or the intended signup/dashboard route. No restoration action was performed for this handoff.
