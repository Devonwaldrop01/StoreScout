# StoreScout — Bug Tracker

Living document. Add new bugs as found; update Status when fixed.

---

## How to file a bug

```
### BUG-NNN — Title
- **Severity**: Critical / High / Medium / Low
- **Route/Page**: e.g. POST /api/v1/competitors, /dashboard/[id]
- **Steps to reproduce**:
- **Expected**:
- **Actual**:
- **Root cause**:
- **Status**: Open / Fixed (commit abc1234)
```

---

## Open bugs

### BUG-001 — Competitor limit check is non-atomic
- **Severity**: Critical
- **Route/Page**: `POST /api/v1/competitors`
- **Steps to reproduce**: Open two browser tabs simultaneously and add a competitor from each. Submit both within ~100ms.
- **Expected**: Second add returns 402 (limit reached).
- **Actual**: Both succeed — user ends up with 2 competitors on the free tier.
- **Root cause**: `SELECT count → INSERT` is not wrapped in a transaction. TOCTOU race window between lines 80–95 of `app/api/v1/competitors.py`.
- **Status**: Fixed (62a1861 — unique constraint + violation catch)

---

### BUG-002 — Large stores exceed Celery 120s timeout
- **Severity**: Critical
- **Route/Page**: Celery task `scan_competitor`
- **Steps to reproduce**: Add fashionnova.com (10k+ products). Wait for scan to start.
- **Expected**: Scan completes with up to 2,500 products (MAX_PAGES cap); partial flag noted.
- **Actual**: Celery `time_limit=120s` hit before fetch finishes (10 pages × 25s timeout = 250s). Worker crashes; scan stuck in "scanning" until `recover_stuck_scans` fires 10 min later.
- **Root cause**: `app/tasks/scan.py` task decorator uses `time_limit=120`. `app/services/fetch.py` has no elapsed-time guard in the page loop.
- **Status**: Fixed (see Pattern B commit)

---

### BUG-003 — Non-Shopify URL accepted at add time
- **Severity**: High
- **Route/Page**: `POST /api/v1/competitors`, onboarding step 1
- **Steps to reproduce**: Add `amazon.com` or `google.com` as a competitor.
- **Expected**: Immediate validation error — "this doesn't appear to be a Shopify store."
- **Actual**: Competitor row is created, initial scan is triggered, scan fails with `not_shopify` error. User has to wait ~60s to learn the URL was invalid.
- **Root cause**: `add_competitor()` does not call `check_store()`. Shopify validation only happens inside the Celery scan task.
- **Status**: Fixed (see Pattern A commit)

---

### BUG-004 — Manual rescan endpoint has no rate limit
- **Severity**: High
- **Route/Page**: `POST /api/v1/competitors/{id}/rescan`
- **Steps to reproduce**: Script 20 POST requests to the rescan endpoint in < 1s.
- **Expected**: First enqueues; subsequent requests return 429 for 60s.
- **Actual**: All 20 enqueue to the priority Celery queue, flooding it.
- **Root cause**: `competitors.py` only checks `scan_status == "scanning"` — no cooldown between rescans.
- **Status**: Fixed (see Pattern C commit)

---

### BUG-005 / BUG-012 — Rescan button not disabled during API call
- **Severity**: High
- **Route/Page**: `/dashboard/[id]` — rescan button
- **Steps to reproduce**: Click rescan button rapidly 5 times.
- **Expected**: Button disables immediately on first click; re-enables after response.
- **Actual**: Button has a 3-second timer animation but no `disabled` prop — every click fires an API request.
- **Root cause**: `disabled` prop missing from rescan button in `frontend/app/(app)/dashboard/[id]/page.tsx`.
- **Status**: Fixed (see Pattern C commit)

---

### BUG-006 — Bulk product change creates N individual change_events
- **Severity**: Medium
- **Route/Page**: `app/tasks/detect_changes.py`, alerts feed
- **Steps to reproduce**: Scan a store before and after a bulk removal/price change of 50+ products.
- **Expected**: One aggregated change_event like "50 products removed" with a sample list.
- **Actual**: 50 individual `product_removed` change_events created; alert email sends top 10 with no summary; change feed shows 50 rows.
- **Root cause**: `detect_changes.py` creates one row per changed product with no aggregation threshold.
- **Status**: Fixed (see Pattern D commit)

---

### BUG-007 — `enqueue_due_scans` scheduler has no lock
- **Severity**: Medium
- **Route/Page**: `app/tasks/scheduler.py` — `enqueue_due_scans`
- **Steps to reproduce**: Run two Celery Beat processes simultaneously (e.g., deploy with 2 scheduler instances).
- **Expected**: Each competitor scan enqueued exactly once per cycle.
- **Actual**: Both processes query `next_scan_at <= now()` simultaneously and enqueue the same competitors twice.
- **Root cause**: No Redis lock around the enqueue loop in `scheduler.py`.
- **Status**: Fixed — Redis `SET NX ex=300` lock acquired at task start; second process skips cycle if lock held.

---

### BUG-008 — `user_profiles` insert failure silently swallowed in `add_competitor`
- **Severity**: Medium
- **Route/Page**: `POST /api/v1/competitors`
- **Steps to reproduce**: Cause a DB error during user auto-provision (e.g., RLS policy mismatch).
- **Expected**: Error logged; tier re-fetched so paid users are not silently demoted to free.
- **Actual**: `except: pass` swallows the error; tier falls back to "free" regardless of actual paid status.
- **Root cause**: Overly broad exception suppression with no re-fetch after failure.
- **Status**: Fixed — `except Exception as provision_exc` logs the error + unconditional re-fetch after provision attempt picks up real tier.

---

### BUG-009 — No React Error Boundary
- **Severity**: Medium
- **Route/Page**: All app pages
- **Steps to reproduce**: Introduce a null-dereference in any component (e.g., `data.products.map(...)` when `data` is null).
- **Expected**: Error is caught; user sees a friendly "Something went wrong" screen with a retry option.
- **Actual**: Entire page goes white/blank with no feedback.
- **Root cause**: No `<ErrorBoundary>` component wrapping the app or individual route segments.
- **Status**: Fixed (e40b00f — `frontend/components/ErrorBoundary.tsx` wraps children in `app/(app)/layout.tsx`)

---

### BUG-010 — Duplicate change_events if detect_changes runs twice on same snapshot
- **Severity**: Low
- **Route/Page**: `app/tasks/detect_changes.py`
- **Steps to reproduce**: Manually enqueue `detect_changes(competitor_id, snapshot_id)` twice (or simulate a Celery retry on a successful task).
- **Expected**: Idempotent — second run produces no new rows.
- **Actual**: Second run diffs the same two snapshots and inserts duplicate change_events.
- **Root cause**: No deduplication guard on the task.
- **Status**: Fixed — Redis `SET NX ex=7200` on `detect_changes:done:{snapshot_id}` at task start; second invocation returns `already_processed` immediately.

---

### BUG-011 — `http://` URLs not normalized to `https://` in frontend
- **Severity**: Low
- **Route/Page**: `/onboarding` step 1, Add Competitor modal
- **Steps to reproduce**: Paste `http://gymshark.com` into the competitor URL field.
- **Expected**: Normalized to `https://gymshark.com` before submission.
- **Actual**: `http://gymshark.com` sent to API as-is; backend normalizes the stored URL to `https://` but the `check_store` pre-flight call may receive the http variant.
- **Root cause**: Frontend only prepends `https://` if there's no protocol — doesn't replace `http://`.
- **Status**: Fixed (see BUG-011 commit)

---

## Fixed bugs (archive)

| ID | Title | Fixed in |
|----|-------|----------|
| BUG-007 | `enqueue_due_scans` double-enqueues with two Beat processes | this commit |
| BUG-008 | `user_profiles` provision failure silently gave paid user free tier | this commit |
| BUG-010 | `detect_changes` not idempotent — retries created duplicate events | this commit |
| BUG-013 | `/competitors/discover` → 500 (route order) | 62a1861 |
| BUG-014 | `/competitors/{id}/price-history` → 500 (`asc=True`) | 62a1861 |
| BUG-015 | `/user/notification-prefs` → 500 (missing table columns) | 62a1861 |
| BUG-016 | `/user/provision` → 500 (notification_prefs insert) | 62a1861 |
| BUG-017 | `/team/members` → 403 for Pro users on settings load | 62a1861 |
| BUG-018 | AI summary infinite loop on Intelligence tab | d870549 |
| BUG-019 | Price history paywall shown to paid users | d870549 |
| BUG-020 | Scan stuck in "scanning" forever | d870549 |
| BUG-021 | Hostname shows UUID before first scan | d870549 |
| BUG-022 | Stripe webhook 500s → retry storms | 90f9882 |
