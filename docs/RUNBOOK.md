# Operations runbook — admin access & the index pipeline

Production infra: **Vercel** (frontend) · **Render** (`storescout-api`, `storescout-worker`,
`storescout-scheduler`) · Redis · Supabase · Stripe · Anthropic.

---

## 1. Admin token (`ADMIN_TOKEN`)

### How the authenticated admin UI reaches the admin endpoints (code path)
1. The operator opens an admin page and **types the token into the gate**; it is
   stored in the browser's `localStorage` under `ss_admin_token`
   (`frontend/app/admin/*` — `TOKEN_KEY`). It is **never** read from an env var
   in the browser.
2. Admin requests send it as the **`X-Admin-Token` request header**
   (`adminFetch` in each admin page/component).
3. The request hits the Next.js **server-side** proxy route
   `frontend/app/api/v1/[...path]/route.ts`, which forwards headers to
   `${API_URL}/api/v1/...` on Render. `API_URL` is a **server-only** var (not
   `NEXT_PUBLIC_*`), so neither the token nor the backend URL is exposed to the
   client bundle.
4. The Render **API** validates it in `_require_admin`:
   `if not settings.admin_token or token != settings.admin_token: 403`.

### Security conclusion
- **No privileged admin token ships to the browser or a `NEXT_PUBLIC_*` var.**
  Repo-wide search confirms there is no `NEXT_PUBLIC` admin/token variable; the
  token is operator-supplied at runtime and kept in `localStorage`.
- An empty `ADMIN_TOKEN` on the backend means `_require_admin` **rejects
  everything (403)** — fail-closed, never open.

### Which Render service needs it
- **`storescout-api` only** — it serves `/api/v1/admin/*`. The worker and
  scheduler don't serve HTTP and don't need it.

### Owner verification step (no claim about the current production value)
`render.yaml` does not declare `ADMIN_TOKEN`, but Render dashboard secrets are
**not** in the repo, so its production presence can't be determined from code.
Verify directly:
1. Render dashboard → **storescout-api** → Environment → confirm `ADMIN_TOKEN`
   exists and is a strong random value (not blank).
2. Functional check: open an admin page, enter that token. If endpoints return
   **403**, the env var is unset or mismatched. If panels load, it is set
   correctly.

---

## 2. The staged index pipeline (`SHOPIFY_INDEX_ENABLED`) — **stays disabled**

Default is `False` (`app/core/config.py`), and it is **not** enabled here.

### Every reader of the flag (resolved as `get_config("shopify_index_enabled", settings.…)`, i.e. app_config DB value first, else the env/default)
| Reader | Runs on | Effect of the flag |
|---|---|---|
| `stage_discovery` / `stage_resolution` / `stage_verification` / `stage_knowledge` guards (`app/tasks/store_index.py`) | **worker** (task execution) | gates whether the staged task does real work |
| legacy `discover_shopify_stores_daily` guard (`store_index.py`) | worker | same |
| `scheduler_status` / `index-ops` display (`app/services/scheduler_status.py`, `app/api/v1/store_index.py`) | **API** | read-only display of the enabled flag |

### Which Render services actually require it to run the pipeline
- **`storescout-worker` — required.** The staged tasks *execute* on the worker,
  so the flag must be truthy there for real work to happen.
- **`storescout-scheduler` (Beat) — not required.** Beat *dispatches* the tasks
  on cron regardless of the flag; the tasks themselves no-op unless the worker
  sees it enabled. (It doesn't hurt to set it, but it isn't what gates work.)
- **`storescout-api` — not required for the pipeline.** It only reads the flag
  to *display* status. Setting it there just makes the admin panels show
  "enabled" — it does not execute anything.
- There is **one** worker service (`storescout-worker`, `--concurrency=1`) plus
  the Beat service (`storescout-scheduler`). If Render shows "two workers," the
  second is the scheduler (Render type `worker` running `celery … beat`).

### Queue routing / which worker consumes each staged task
- `task_routes`: `app.tasks.alerts.* → priority`, `scan.manual_rescan → priority`,
  and the catch-all **`app.tasks.* → default`**. All four staged tasks route to
  **`default`**.
- The worker command consumes **`-Q default,priority`**, so the single
  `storescout-worker` consumes all four staged tasks. Beat consumes nothing (it
  only dispatches).

### Safe post-deployment enablement + rollback

**Preferred — runtime toggle (no redeploy, instant rollback):**
1. Ensure `ADMIN_TOKEN` is set (section 1).
2. Admin → engine controls → set `shopify_index_enabled = true`. This writes the
   `app_config` DB row, which the worker reads via `get_config`, so it takes
   effect on the next scheduled dispatch — no restart.
3. Verify: Admin Store Index → **Scheduler** panel shows recent dispatch + new
   `store_index_runs` rows appearing; the funnel counts start moving.
4. **Rollback:** set `shopify_index_enabled = false` in engine controls. The next
   dispatch no-ops immediately; no redeploy.

**Alternative — env var (requires redeploy):**
1. Render → **storescout-worker** → Environment → add `SHOPIFY_INDEX_ENABLED=true`
   → deploy. (Optionally the same on scheduler/api for consistent display.)
2. Verify as above.
3. **Rollback:** remove the var (or set `false`) → redeploy. Prefer the runtime
   toggle for fast rollback.

**Before enabling**, confirm the worker has memory headroom (it's
`--concurrency=1 --max-memory-per-child`), and start with the small default
batch sizes; watch the Scheduler panel's last-failed-run.
