# StoreScout — Edge Case QA Checklist

Run through this checklist before every significant release. Check off items as you verify them. Re-open (uncheck) if a regression is found.

Use `seed_test_data.py` to set up the required user states quickly.

---

## Shopify URL Inputs

- [ ] **Non-Shopify URL** (`amazon.com`) — immediate 422 "not a Shopify store", no competitor row created
- [ ] **URL with path** (`gymshark.com/collections/sale`) — stripped to root domain, scan succeeds
- [ ] **`http://` URL** (`http://gymshark.com`) — normalized to `https://` before submission
- [ ] **Bare domain without protocol** (`gymshark.com`) — works, `https://` prepended
- [ ] **Random text** (`asdf`, `!!!`) — validation error shown, submit disabled
- [ ] **Empty string** — submit button disabled
- [ ] **Very long string (>500 chars)** — no crash, handled gracefully
- [ ] **IP address** (`192.168.1.1`) — rejected or fails scan gracefully
- [ ] **URL with port** (`example.com:8080`) — handled without crash

---

## Store Edge Cases

- [ ] **0-product store** — scan completes, dashboard shows "0 products", no crash
- [ ] **Store returns 403 (bot blocked)** — scan_status=error, "blocked by store" message shown
- [ ] **Store returns 429 (rate limited)** — scan marks error, retry scheduled, no crash
- [ ] **Very large store (fashionnova.com, ~10k products)** — scan completes within timeout, partial results with truncated flag if capped
- [ ] **Store goes offline mid-scan** — fetch timeout handled, scan_status=error
- [ ] **Store with duplicate product handles in catalog** — normalize handles this, no crash
- [ ] **Store with no images on products** — image fields null, no crash in ProductImage component
- [ ] **Store with extreme prices** (`$0.00`, `$99,999.99`) — no display or formatting crash
- [ ] **Store with non-ASCII characters in product titles** — renders correctly
- [ ] **Store with < 2 scans** — price history shows "builds over time", not a 500 or empty chart

---

## Competitor CRUD

- [ ] **Add 2nd competitor as free user** — 402 returned, upgrade modal fires, no competitor row created
- [ ] **Add same competitor twice** — 409 Conflict, "already tracking" message shown
- [ ] **Add competitor with concurrent requests (race condition)** — only 1 row created, 2nd returns 409
- [ ] **Delete competitor** — removed from dashboard; associated scan_snapshots and change_events cleaned up
- [ ] **Delete competitor mid-scan** — Celery task completes or fails cleanly; no orphaned rows
- [ ] **Deactivate competitor** — not scanned on next scheduler cycle
- [ ] **Re-add previously deleted competitor** — works (new row, fresh scan)

---

## Scan States

- [ ] **First scan completes** — dashboard populates without manual page refresh (Supabase Realtime)
- [ ] **Scan stuck >5 min** — `recover_stuck_scans` resets to "pending" within 10 min
- [ ] **Manual rescan — single click** — scan enqueues, button shows spinner and disables
- [ ] **Manual rescan — rapid clicks (spam)** — only 1 scan enqueued; 2nd–Nth return 429
- [ ] **Celery worker offline** — scan_status stays "pending"; shown to user with message
- [ ] **Scan error state** — error message shown on competitor card; retry option available
- [ ] **Scan on very large store** — completes in <300s; partial flag shown if truncated

---

## Tier Gating

- [ ] **Free: add 2nd competitor** → 402 + upgrade modal
- [ ] **Free: view price history** → locked overlay shown, not a 500 or blank
- [ ] **Free: click AI Insights tab** → upgrade prompt, not a 500
- [ ] **Free: CSV export** → upgrade modal, not a 500
- [ ] **Free: change history** → only last 3 changes shown, rest locked
- [ ] **Free: winning products** → top 1 shown, rest locked
- [ ] **Pro: all Pro features accessible** (price history, AI, CSV, full changes)
- [ ] **Agency: team invite** → invite email sent, member can accept
- [ ] **Tier upgrade via Stripe** → tier updates in `user_profiles` within 30s of payment
- [ ] **Subscription cancelled** → downgraded to free on next page load (subscription webhook)
- [ ] **Upgrade modal opened** → correct plan + price shown; checkout redirects to Stripe

---

## Auth & Session

- [ ] **JWT expires mid-session** → 401 returned from API, user redirected to `/auth/login`
- [ ] **`user_profiles` row missing** → auto-provisioned on next competitor add, no crash
- [ ] **Google OAuth signup** → onboarding flow with `?plan=` param preserved
- [ ] **Email confirm link** → clicking on mobile redirects to app correctly
- [ ] **Sign out** → session cleared, redirect to marketing page
- [ ] **Sign in with wrong password** → clear error message (not a 500)
- [ ] **Two tabs open** → signing out in one tab reflects in the other on next API call

---

## Alerts

- [ ] **1 price change detected** → alert email received within 15 min
- [ ] **50 price changes (bulk promo)** → 1 aggregated email, not 50 separate emails
- [ ] **Alert cooldown** → 2nd alert for same competitor within 4h is suppressed
- [ ] **Mark all read** → unread badge count goes to 0
- [ ] **Mark individual alert read** → badge decrements correctly
- [ ] **Filter alerts by type** → correct subset shown, no crash on empty filter
- [ ] **Alerts page with 0 alerts** → "All clear" empty state shown
- [ ] **Alert email link** → clicking "View dashboard" opens correct competitor detail

---

## Empty States

- [ ] **Dashboard — 0 competitors** → "Track your first competitor" CTA shown
- [ ] **Alerts — 0 alerts** → "All clear" message shown
- [ ] **Changes tab — no changes** → "No changes detected yet" message
- [ ] **Winning Products — no data** → "No products to score yet" message
- [ ] **Price History — < 2 scans** → "builds over time" message (not blank chart or 500)
- [ ] **Gaps tab — no gaps found** → "No major gaps detected" message
- [ ] **Intelligence Stream — no signals** → "All quiet" message
- [ ] **AI Insights — not yet generated** → "Check back after next scan" message
- [ ] **Settings — no API keys** → empty state, "Create API key" shown

---

## Loading States

- [ ] **Dashboard initial load** → skeleton shown while competitors fetch
- [ ] **Competitor detail load** → KPI card skeletons shown
- [ ] **Add Competitor modal submit** → button shows spinner, is disabled during API call
- [ ] **Rescan button** → spinner shown, button disabled until response received
- [ ] **Onboarding scan in progress** → progress indicator shown, not a blank screen
- [ ] **AI summary generating** → spinner shown, not blank

---

## Mobile (< 640px)

- [ ] **Dashboard competitor list** → readable, cards stack correctly
- [ ] **Competitor detail tabs** → horizontally scrollable, no overflow clipping
- [ ] **Add competitor modal** → fits screen, input accessible, keyboard doesn't push layout
- [ ] **Bottom nav** → correct active state per page
- [ ] **Onboarding wizard** → all 4 steps usable, form fields accessible
- [ ] **Alerts feed** → rows readable, timestamps visible
- [ ] **Settings page** → sections stack, no horizontal overflow

---

## Settings

- [ ] **Notification prefs load** → correct values shown (or defaults if table missing columns)
- [ ] **Save notification prefs** → success feedback shown, changes persist on refresh
- [ ] **Agency: team invite** → invite email sent; invited user sees acceptance screen at `/invite/{token}`
- [ ] **Pro: team members section** → not shown (no 403 in network console)
- [ ] **Manage billing** → Stripe Customer Portal opens
- [ ] **API keys (Pro+)** → create, copy, revoke all work
- [ ] **Password reset** → email sent, link works

---

## Stripe / Payments

- [ ] **Webhook signing secret** → `STRIPE_WEBHOOK_SECRET` on Render matches Stripe dashboard; no 400 errors in Stripe event log
- [ ] **`checkout.session.completed`** → `user_profiles.tier` updated within 30s
- [ ] **`customer.subscription.deleted`** → user downgraded to free
- [ ] **`customer.created`** → no 500 in Stripe logs (event handled or swallowed cleanly)
- [ ] **Upgrade from free → Pro** → competitor limit increases to 10, price history unlocked
- [ ] **Test mode payment** → use Stripe test card `4242 4242 4242 4242`, verify end-to-end

---

## Performance

- [ ] **Dashboard with 10 competitors (Pro)** → loads in < 2s on a standard connection
- [ ] **Competitor detail with 2,500 products** → overview tab loads without timeout
- [ ] **Alerts with 200 items** → feed scrolls smoothly, no layout jank
- [ ] **Price history chart with 90 data points** → chart renders without freeze
