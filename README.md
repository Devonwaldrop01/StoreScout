# StoreScout

StoreScout is an existing Shopify competitor-monitoring SaaS. Users sign in,
add a public Shopify storefront, review a catalog snapshot, and return for
scheduled price, availability, and catalog-change observations.

The repository also contains an older one-time PDF-report flow. It has not
been removed because its production use has not yet been established.

## System

| Component | Implementation |
| --- | --- |
| Frontend | Next.js App Router, React, Tailwind, Supabase SSR authentication |
| API | FastAPI under `app/`, including versioned SaaS routes and legacy routes |
| Data/auth | Supabase Postgres and Auth; trusted server uses service-role credentials |
| Background work | Celery worker, Celery Beat scheduler, Redis broker/cache |
| Catalog collection | Public Shopify JSON endpoints; `curl_cffi` with HTTP fallback |
| Reports | Python normalization/analysis; Playwright/Chromium for PDF rendering |
| Billing | Stripe Checkout, subscription webhooks, billing portal; legacy one-time flow |
| Optional services | Anthropic summaries, Resend email, configured GA4/Meta analytics |

Scheduled scan tasks call the API's protected internal scan endpoint. The API
performs the expensive catalog fetch and analysis. Worker memory recycling
therefore does not by itself bound API memory usage.

## Local development

Use `.env.example` as a list of backend configuration names. Supply your own
development values locally; never commit credentials. Frontend configuration
includes `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and
server-side `API_URL`, which points the Next.js API proxy at the backend.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt pytest
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 10000
```

In `frontend/`:

```sh
npm ci
npm run dev
```

Full authenticated jobs additionally require a development Supabase project,
Redis, and a Celery worker. Run only one Beat scheduler for a given queue.
`API_INTERNAL_URL` must reach the API from the worker. Set the same strong
`INTERNAL_SECRET` on both API and worker; empty and former default values are
rejected. Do not substitute production credentials into test environments.

## Verification

From the repository root:

```sh
.venv/bin/python -m pytest -q
```

From `frontend/`:

```sh
npm test
npx tsc --noEmit
npm run build
```

These checks do not certify deployed authentication, payments, email delivery,
queue scheduling, mobile layouts, or memory behavior under concurrent load.

## Deployment and launch status

`render.yaml` declares an API, a worker, and a scheduler. It references Redis
and Supabase but does not provision them, and it does not declare the Next.js
frontend. Inspect the actual hosting account before restoring or creating any
service. A blueprint is not a record of what is currently deployed.

As checked September 5, 2026, `https://getstorescout.com/` returns HTTP 503 with
`Service Suspended`. The account-level reason and affected service are not yet
confirmed. No restoration or paid infrastructure change has been performed.

The launch-readiness branch includes conservative catalog coverage handling,
paired-variant discounts, safer payment retries, proxy corrections, internal
endpoint protection, and corrections to misleading UI claims. It is not a
production sign-off. Remaining gates include:

- Confirm actual services, suspension reason, environment wiring and schema.
- Apply reviewed entitlement/RLS restrictions in staging before production.
- Close outbound-request SSRF exposure, including redirects and DNS changes.
- Reconcile Stripe events safely and test payment/cancellation lifecycles.
- Enforce quotas atomically; settle manual-rescan versus advertised cadence.
- Verify snapshot-specific diff execution, retries and concurrent scan budgets.
- Exercise signup, confirmation, reset, logout, reports and billing end to end.
- Verify support/deletion fulfillment and privacy/marketing settings.

`supabase/migrations/023_protect_entitlements.sql` is prepared for review only.
Inspect the deployed schema, existing grants and migration history before
applying it. Multiple migration directories and missing table definitions in
source mean migrations must not be applied blindly.

## Data boundaries

Public catalog data does not establish revenue, units sold, exact inventory,
actual customer demand, or cart-level promotions. Catalog caps and failed pages
must remain visible; partial observations cannot establish whole-catalog
additions/removals. Historical observations start when monitoring begins.
