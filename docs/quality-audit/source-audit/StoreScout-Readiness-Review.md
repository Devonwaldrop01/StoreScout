> Historical initial review of e66e3f0. Subsequent local repairs at 70af98e/ff555bb supersede completed findings. Retained as evidence; do not repeat completed work or treat every original finding as still open.

# StoreScout customer-readiness review

Prepared for Devon • 5 September 2026

**Verdict: there is a plausible paid use case, but StoreScout is not ready for unattended, self-service sales today.** The public site is suspended, and isolated reproductions found failures in the billing acknowledgement and the data customers would rely on. Restore availability, close the trust and access-control gaps, and validate the complete purchase-to-result journey before directing buyers to checkout.

This review covers [Devonwaldrop01/StoreScout](https://github.com/Devonwaldrop01/StoreScout), `main` at commit `e66e3f05417cea5d57f27800c755c2353ca2b791` (12 July 2026). It combines source inspection, local checks, isolated defect reproductions, public availability checks, and current market research. It is a review, not a claim that fixes have been deployed. The repository was not modified, and no prospects were contacted.

## What is already working in the engineering foundation

The project has a substantial SaaS implementation: a Next.js frontend, FastAPI API, background scans, Supabase accounts and data, Stripe billing, reports, and AI-assisted summaries. Backend dependencies are pinned, CI runs on main and PRs, several API routes enforce ownership, and the code includes AI fallback and scan lifecycle handling.

| Verification | Result | What this establishes |
| --- | --- | --- |
| Existing backend tests, local Python 3.12 environment | **137 passed** | Existing test expectations hold; dependencies were available for the final run. |
| Existing frontend tests | **36 passed**, four files | Covered auth routing, playbook steps, market helpers, and scan lifecycle behavior. |
| Frontend TypeScript check | Passed | No reported type errors. |
| Next.js production build | Passed | Frontend compiles and builds successfully. |
| GitHub CI at the reviewed commit | Passed | Historical CI agrees with the local baseline. [CI run](https://github.com/Devonwaldrop01/StoreScout/actions/runs/29214176367). |
| Six isolated audit probes | Six problematic outcomes reproduced | Specific business-critical cases are missing from the existing test coverage. |
| Public homepage, signup, privacy | **HTTP 503; “Service Suspended”** | Customers cannot currently enter the normal journey. |
| Production signup, payment, scheduled scan, email delivery, cancellation | **Not verified** | These require a functioning deployment and real environment configuration. |

A green build is useful evidence. It does not establish that a payment activates access, a competitor change is detected, or a report is accurate.

## Blockers and concrete fixes

### 1. The public service is suspended — stop paid traffic

Read-only requests to [the homepage](https://getstorescout.com/), [signup](https://getstorescout.com/auth/signup), and [privacy page](https://getstorescout.com/privacy) returned HTTP 503 with a suspension page on 5 September. This is more specific than a slow cold start. The reason for the suspension was not established.

Render was successfully connected during this review, but its service-control tools did not load into this session. Consequently, the Render account's suspension reason, service settings, logs, and deployed commit could not be inspected. No hosting changes were made.

**Next action:** inspect the suspension notice on the StoreScout service in Render. Resolve the stated cause, then verify the frontend domain and API, worker, scheduler, Redis, and database together. The runbook describes a Vercel frontend with Render backend services; the repository also retains an older FastAPI PDF interface. Confirm that the custom domain serves the intended Next.js SaaS frontend. Do not infer the deployed architecture from old documentation alone.

**Acceptance:** the public homepage, signup and policy pages load; a new user can reach a completed first scan; worker and scheduler health are verified from an actual scan rather than just an HTTP health endpoint.

### 2. A failed payment handler is acknowledged as successful — fix before charging

In [webhooks.py, line 73](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/app/api/v1/webhooks.py#L73), exceptions from event handling are caught, logged, and followed by a successful acknowledgement. An isolated probe made the handler throw a database error; the route still returned `{"received": true}`. A customer can pay while their entitlement update is lost.

**Fix:** validate the signature and durably record or enqueue the event before acknowledging success. Otherwise return a retryable failure when persistence fails. Deduplicate by event ID, and reconcile against current subscription state when events arrive out of order. Stripe documents retries, duplicate deliveries, unordered events, and asynchronous processing. [Stripe webhook guidance](https://docs.stripe.com/webhooks).

Two related source findings need verification:

- The [Next.js API proxy](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/frontend/app/api/v1/%5B...path%5D/route.ts) forwards selected headers but omits `stripe-signature`. This breaks signature verification **if** Stripe is configured to use the proxied frontend URL. A direct API webhook URL avoids this particular problem; the production URL is unknown.
- [Checkout creation](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/app/api/v1/billing.py#L75) creates a new subscription session without an evident active-subscription guard. Repeated checkout completion may create multiple subscriptions. Route existing subscribers into plan management and make customer/session creation safe to retry.

**Acceptance:** a test payment grants the right tier; an injected database failure recovers after redelivery; duplicate events do not duplicate work; cancellation and payment failure produce the intended access state; repeated checkout cannot silently bill twice. Verify the exact endpoint configured in Stripe.

### 3. Database policies may allow customers to edit their own plan — close the entitlement boundary

The initial migration permits a user to update their own entire `user_profiles` row, which contains the tier, subscription status, competitor limit, scan interval, and Stripe identifiers. It also grants owner-level `FOR ALL` access to competitors. [Profile policy, line 23](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/supabase/migrations/001_initial_schema.sql#L23); [competitor policy, line 49](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/supabase/migrations/001_initial_schema.sql#L49).

**Evidence level:** the broad policies are present in source. Exploitability in production depends on the actual database grants and later/manual changes, which were not inspected. With normal table update privileges, row ownership does not protect sensitive columns. Supabase explicitly distinguishes row-level access from column privileges. [Supabase guidance](https://supabase.com/docs/guides/database/postgres/column-level-security).

**Fix:** keep billing and entitlement fields under trusted server control, preferably in a separate protected table or through carefully restricted column grants. Enforce quotas at the database/trusted-write boundary as well as in API code. Review all exposed tables, including `alert_email_log`, for appropriate access controls.

**Acceptance:** using an ordinary authenticated staging account and the public Supabase API, attempts to change tier/limits/Stripe IDs or bypass competitor quotas fail. A second user cannot read or modify the first user's private records. Legitimate account settings still work.

### 4. User-supplied URLs and internal authentication need hardening

The URL handling accepts arbitrary hosts without an evident centralized exclusion of private, loopback, or link-local destinations. Fetchers follow redirects. This can let a caller make the server request internal resources. Relevant paths include [competitor creation](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/app/api/v1/competitors.py#L33), the older public preview/check routes in [app/main.py](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/app/main.py), and [fetch.py](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/app/services/fetch.py). Production exploitation was not attempted.

The internal secret also has a predictable development fallback in [config.py, line 54](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/app/core/config.py#L54). The Blueprint declares it for the worker but not the API; dashboard overrides may exist. [render.yaml](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/render.yaml).

**Fix:** use one URL-validation and outbound-request policy across scans, previews, and outgoing integrations. Validate resolved destinations and every redirect; reject private destinations, credentials in URLs, and unsupported schemes/ports; add network-level restrictions where possible. Fail closed if an internal secret is absent or still the development default, and configure the same random secret on the required services. [OWASP SSRF prevention guidance](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).

**Acceptance:** staging rejects private-address and redirect-to-private probes without making those requests; public supported Shopify stores still work; internal routes reject missing or incorrect credentials.

### 5. A single unchanged product can suppress a real scan — core value failure

The [skip-if-unchanged logic](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/app/api/v1/internal.py#L57) fetches one product and compares its timestamp with the previous snapshot's newest entry. That is not a catalog-wide change signal.

**Reproduction:** product A's timestamp stayed the same while product B changed. The function fetched only one product, returned `status: unchanged`, and skipped the full scan. This can make the dashboard look recently checked while missing the change the customer paid to catch.

**Fix:** remove the shortcut until there is a reliable catalog-wide change token. Preserve “last attempted,” “last successfully checked,” and “last complete snapshot” as distinct concepts.

**Acceptance:** changing any supported product, including one outside the first fetched result, is detected on the next successful scan.

### 6. Partial catalogs can produce false removal alerts — core value failure

[fetch.py](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/app/services/fetch.py) returns accumulated products after some later-page errors or time limits. [Change detection](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/app/tasks/detect_changes.py#L43) interprets absent handles as removed without requiring exhaustive snapshots. The default 1,500-product cap creates another non-exhaustive case.

**Reproductions:** a page-two HTTP 503 returned a normal-looking one-product list; comparing two explicitly truncated snapshots emitted a `product_removed` event for an absent item.

**Fix:** return structured fetch results with completeness, reason, and coverage. Keep the last trustworthy baseline. Label partial analysis and suppress removal/campaign-shift conclusions unless coverage supports them. Use stable product identity where possible.

**Acceptance:** failures, timeouts, caps, and pagination reordering cannot generate confirmed removals; customers see an accurate coverage warning; a genuine removal is still detected after a complete comparison.

### 7. Discount calculations combine different variants — incorrect customer evidence

[normalize.py](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/app/services/normalize.py#L37) computes minimum price and minimum compare-at price separately, then treats them as a pair.

**Reproduction:** variant A costs 10 and has no compare-at price; variant B costs 100 with a compare-at price of 100. Neither is discounted. StoreScout returned a 90% discount and a 100% discounted-product share. A second probe with one malformed numeric price raised a `TypeError`.

**Fix:** calculate markdowns within the same variant, then aggregate with an explicit definition. Ignore invalid/nonfinite prices while disclosing reduced coverage. Treat zero prices deliberately. Retain currency and market context rather than silently labeling every amount as dollars.

**Acceptance:** mixed-price variants, missing compare-at values, zero prices, malformed values, and nondiscounted variants have correct results. The customer can tell whether a percentage refers to products or variants. Cross-market comparisons are unavailable or explicitly qualified until currencies and regional prices are supported.

### 8. Source-controlled migrations do not cover every advertised feature

API code references `team_members`, `api_keys`, and `action_items`, but their table-creation migrations were not found in the tracked migration directories. There are also two `003` migrations and a separate top-level migration directory. The current schema-health check does not cover the whole account/billing/team surface. [Migrations](https://github.com/Devonwaldrop01/StoreScout/tree/e66e3f05417cea5d57f27800c755c2353ca2b791/supabase/migrations); [schema health](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/app/services/schema_health.py).

**Evidence level:** reproducibility gap in source; the production database may contain manually created objects. This is not proof that those production tables are absent.

**Fix:** compare the actual schema with a versioned migration manifest, reconcile missing objects, and verify a clean staging database. Do not blindly rerun every migration against production. Hide optional features that cannot pass their acceptance checks. Teams, developer APIs, and new integrations are not required to win the first Pro customer.

### 9. Public reports can mix dates

[reports.py](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/app/api/v1/reports.py) loads pricing by snapshot ID but attaches the latest AI brief for that competitor. A historical snapshot can therefore display newer commentary. A snapshot-specific URL is also not inherently an always-current report.

**Fix:** bind the brief to the snapshot, or make the entire report explicitly current. Display observation date, currency, coverage, and source links. Define which information is intentionally public, and provide share controls appropriate to that scope before adding private client or integration data.

## Does the product story make sense?

The useful core is straightforward: **help a Shopify operator or consultant review public competitor catalog and pricing evidence before a promotion or client meeting.** The current presentation mixes that job with real-time warnings, buyer-intent claims, broad AI recommendations, lead discovery, and an older one-off PDF product. That makes the promise harder to understand and harder to trust.

| Current inconsistency | Why it matters | Recommended wording or behavior |
| --- | --- | --- |
| FAQ says a 9am price cut is known by 9:15 | Pro is configured for 24-hour scans; Agency for 12 hours. A short promotion may be missed entirely. | “Pro checks supported stores daily. Alerts follow a successful scan. Changes between scans may be missed.” |
| FAQ describes users matching flash sales | This review found no evidence supporting that specific customer story. | Remove unless backed by a real, permissioned example. |
| Static landing-page examples display “LIVE” | A visitor may mistake illustrative figures for current observations. | Label every mockup “Illustrative example.” Use dated real output for demonstrations. |
| Copy infers shoppers are actively comparing or returning to market | Public catalog changes do not reveal individual shopper behavior. | Describe the observed change; label any recommended response as a hypothesis. |
| README says “No accounts. No dashboards.” | It describes the older PDF product, not the current SaaS. | Make the current architecture, plans, deployment, and first customer journey the canonical README. |
| Marketing handoff calls integrations live; launch checklist still requires verification | Implemented code is not evidence of a working production integration. | Use verified / implemented but unverified / planned statuses. |
| Default price bands and dollar labels imply universal comparability | A premium threshold differs by category, currency, and market. | Restrict early examples to comparable products in a confirmed currency; explain the metric. |

The FAQ and mockup findings are grounded in [FaqAccordion.tsx](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/frontend/components/landing/FaqAccordion.tsx), [the landing page](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/frontend/app/page.tsx), and [frontend copy helpers](https://github.com/Devonwaldrop01/StoreScout/blob/e66e3f05417cea5d57f27800c755c2353ca2b791/frontend/lib/utils.ts).

Do not equate public product creation dates with confirmed launches, availability flags with units in stock, or compare-at markdowns with every promotion available at checkout. Sales, revenue, traffic, profit, and customer intent are outside what this public-catalog evidence establishes.

## Minimum customer journey to release

1. A visitor understands the buyer, decision, supported stores, scan cadence, monthly price, and an honest sample within one screen.
2. Signup, verification, password recovery, login, and logout work through the actual production domain.
3. A supported competitor URL passes preflight; unsupported stores receive a useful message before payment.
4. The first scan reaches a clear success, partial, or failure state. A failed scan offers recovery rather than an endless spinner.
5. The result displays source, timestamp, currency, and coverage. A human can verify representative prices and every headline claim.
6. Checkout activates the correct plan; the customer can manage and cancel it. The configured payment events survive retries.
7. A controlled change is detected by the scheduled worker and its email arrives at a real test inbox.
8. Account ownership, quotas, private data, and internal routes pass the staging checks above.
9. A customer can find a working support contact and accurate policies; logs and a rollback path are available to the operator.

**Launch decision:** enable paid self-service only after these gates pass. An explicitly manual research service can be sold separately while the software is repaired, provided the research and payment route can actually be delivered safely and accurately. Do not describe that service as automated SaaS access.

## Suggested repair sequence

| Order | Work package | Evidence to collect |
| --- | --- | --- |
| 1 | Restore the correct deployment; protect internal routes and database entitlements | Working URLs, service status, authenticated permission checks |
| 2 | Repair billing delivery and repeated checkout behavior | Test payment, retry, duplicate, failure and cancellation results |
| 3 | Repair scan completeness, skip logic, variant discounts, and date/currency labels | Focused regression tests based on the six reproduced cases |
| 4 | Reconcile required schema and hide unverified optional features | Clean staging setup plus first-user smoke test |
| 5 | Correct claims and run the complete customer journey | A dated, source-backed demo and one observed end-to-end test |

This is a priority order, not a promise that all repairs fit into one evening. Avoid adding new features, paid ads, or a large launch while the core journey remains uncertain.

## Reproduction evidence and limits

The accompanying `StoreScout-Audit-Reproductions.py` reads the reviewed source and runs six offline probes. API, database, payment verification, and HTTP boundaries are faked; some functions are extracted through Python's AST with decorators removed. It does not contact production, and it is not an integration or penetration test. Its JSON output demonstrates the specific source-level outcomes described above. It should be converted into focused regression tests as the defects are fixed.

Run it against a local checkout of the reviewed commit:

```bash
python StoreScout-Audit-Reproductions.py /absolute/path/to/StoreScout
```

The six observations are: false 90% markdown; malformed-price crash; false removal from truncated snapshots; partial fetch returned as an ordinary list; a real change missed by a one-product probe; payment-handler failure acknowledged as received. The existing 173 tests passing does not contradict these additional cases.

The market evidence, first offer, eight prospect hypotheses, outreach drafts, complete marketing posts, and dated two-week plan are in `StoreScout-First-Sales-Kit.md`.
