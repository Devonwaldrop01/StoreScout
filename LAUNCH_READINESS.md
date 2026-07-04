# StoreScout — Launch Readiness Checklist

**Purpose:** Track what's left before we can really start selling. Owner: Devon (product/infra). Companion to `MARKETING_HANDOFF.md` and `OUTREACH_PROSPECTS.md`.
**Last updated:** 2026-06-29

Status: ✅ done · 🟡 in progress · ⬜ not started · 🚫 blocker (can't sell until done)

---

## 🚫 Hard blockers — cannot really sell until these are all ✅

### 1. Legal pages
- [x] ✅ Privacy Policy page (`/privacy`) — product-accurate (Supabase, Stripe, Resend, Anthropic, GA4/Meta Pixel, integrations). `frontend/app/privacy/page.tsx`
- [x] ✅ Terms of Service page (`/terms`). `frontend/app/terms/page.tsx`
- [x] ✅ Footer links to Privacy + Terms on landing page.
- [x] ✅ Governing law set to **New York** in Terms §14 (Devon = primary operator, Bronx NY). ⚠️ Confirm this matches the LLC's actual state of formation — change to VA/DE if Anonymous Mentality LLC is registered elsewhere.
- [ ] ⬜ Have counsel skim both pages before relying on them (templates are solid but not legal advice). Both files carry a header comment to this effect.
- [ ] ⬜ (Recommended) Link Privacy + Terms from the signup page and the Stripe checkout (Stripe lets you add policy URLs in the dashboard).

### 2. Stripe production config
- [x] ✅ Billing code wired — checkout, customer portal, webhooks (BUG-022 fixed).
- [ ] 🚫 Set real Stripe **price IDs** in production env (currently empty defaults in `app/core/config.py`): `stripe_pro_price_id`, `stripe_pro_annual_price_id`, `stripe_agency_price_id`, `stripe_agency_annual_price_id` (developer ids optional/internal).
- [ ] 🚫 Set `stripe` secret key + webhook signing secret in prod; point a live Stripe webhook at the subscriptions endpoint.
- [ ] 🚫 **Run one real end-to-end purchase per plan** (test mode → then a live $-charge sanity check): checkout → tier upgrades → portal cancel → downgrades.
- [ ] ⬜ Decide what to do with the legacy one-time `STRIPE_PRICE_ID` checkout path in `app/main.py:422` (old $9 PDF flow) — confirm it doesn't collide with subscriptions; remove if dead.

### 3. Email deliverability
- [ ] 🚫 Verify SPF, DKIM, and DMARC are configured for the sending domain in Resend (alerts/digests/drip are the core promise — they can't land in spam).
- [ ] ⬜ Send test alert + digest + onboarding emails to Gmail and Outlook; confirm inbox placement (not spam/promotions).
- [ ] ⬜ Confirm `hello@getstorescout.com` is a monitored inbox (replies will come back to it).

### 4. Testimonials / trust
- [x] ✅ Removed the 3 illustrative/hardcoded testimonials. Landing now shows ONLY real opt-in reviews via `GET /feedback/public` (`components/landing/Testimonials.tsx`); the section is hidden until real reviews exist — no fake social proof.
- [ ] ⬜ Collect first real reviews: the in-app feedback loop now prompts users (checklist step + one-time auto-prompt) — get a few ★≥4 opt-in reviews so the landing testimonials section populates before/early in outreach.

### 4b. Database migrations applied in prod
- [ ] 🚫 Apply all `supabase/migrations/*.sql` in the production Supabase project — most recent: `006_product_watches.sql` (product watchlist). Until applied, the `/watchlist` endpoints error and the watchlist panel shows only its empty state.

---

## 🟡 Important — sell, but fix fast / don't oversell

### 5. Analytics & conversion tracking
- [x] ✅ GA4 + Meta Pixel wired (env-gated, ships inert until keys set). `frontend/components/Analytics.tsx`, `frontend/lib/analytics.ts`, mounted in `app/layout.tsx`.
- [x] ✅ Provider-agnostic `track()` helper + events: `upgrade_clicked`, `competitor_added`.
- [x] ✅ Full funnel events wired: `signup_completed` (onboarding mount, once per browser), `first_scan_completed` (onboarding scan-poll success), `subscription_started` (settings post-checkout `?upgraded=1`, once per checkout). Meta standard-event mapping in place (`CompleteRegistration`, `Subscribe`, `InitiateCheckout`).
- [ ] ⬜ Set env vars in prod: `NEXT_PUBLIC_GA_ID` (GA4 measurement ID) and `NEXT_PUBLIC_FB_PIXEL_ID` (Meta Pixel ID). Until set, no tracking fires.
- [ ] ⬜ Create the GA4 property + Meta Pixel; define the activation funnel (signup_completed → competitor_added → first_scan_completed → upgrade_clicked → subscription_started).
- [ ] ⬜ (Optional, higher accuracy) Also fire `subscription_started` server-side from the Stripe webhook via GA4 Measurement Protocol / Meta Conversions API — the client-side version misses users who close the tab before the redirect.

### 6. Integrations — all built; correctness fixes applied
All integrations are wired end-to-end (backend + Settings UI + DB schema + the AI playbook consumes the data). Fixed several correctness bugs that made them return wrong/empty data:
- [x] ✅ Klaviyo subscriber counts (was always 0 — Lists API needs `additional-fields[list]=profile_count`).
- [x] ✅ GA4 property dropdown (was empty — switched to `accountSummaries`).
- [x] ✅ GA4 report no longer 400s on properties without conversions (dropped unused metric).
- [x] ✅ GSC search-query data (was broken — siteUrl now percent-encoded).
- [x] ✅ Shopify Admin data now actually used — new `get_shopify_context()` feeds real inventory + active discount rules into the playbook, justifying the `read_inventory`/`read_price_rules`/`read_discounts` scopes the Connect flow requests.
- [x] ✅ Deeper Klaviyo — context now includes email-campaign cadence (sends in last 30d + days since last send), not just list size.
- [x] ✅ Playbook quality upgrades — ready-to-paste draft assets (email/ad copy) on act_now/right_now plays; small-account logic (1-competitor users get varied angles instead of impossible "different competitor per play"); channel variety (not every play is paid ads); 90-day trend intelligence (price/promo trajectory + discount-campaign cadence) fed into the prompt.
- [x] ✅ Meta Ad Library competitor feed — `get_competitor_ads_context()` reads the PUBLIC Ad Library (not the user's ad account), token-gated and inert until `META_AD_LIBRARY_TOKEN` is set. ⚠️ Coverage caveat: official API fully covers EU-served ads; broader US commercial coverage aligns with the verified-business step (Meta Ads roadmap item).
- [ ] 🚫 **Live verification required (Devon).** These call external APIs (Klaviyo, GA4, GSC, Shopify Admin, Meta Ad Library) that can't be exercised from the dev environment without real connected accounts. Connect one real account per integration and confirm: Klaviyo shows real subscriber counts + cadence; GA4 dropdown lists properties; a generated playbook references your GA4/GSC/Shopify data and includes draft email/ad copy. Set `google_client_id/secret`, `shopify_api_key/secret` (and optionally `meta_ad_library_token`) in prod env.

### 7. Demo account
- [ ] ⬜ Stand up a presentable demo account with good-looking real data (for screenshots + sales calls). Confirm which `scripts/seed_test_data.py` user is safe to use.

### 8. Fresh-signup QA pass
- [ ] ⬜ Walk the full new-free-user path once on production after recent changes (tier-aware upgrade modal, discovery limit = 1, free weekly alert, integration nudges): signup → onboarding → first scan populates → upgrade prompts fire correctly → free limits enforced.

### 9. Activation & free-tier experience — built
- [x] ✅ Getting Started checklist for free users (orientation so they're not stuck after the first scan).
- [x] ✅ Product watchlist (pin competitor products, "since you pinned" deltas) — engagement loop. *(Needs migration 4b applied.)*
- [x] ✅ Generosity bump (more quick wins / gaps / winning products / price points / changes visible to free).
- [x] ✅ Dashboard "Your Move" widget shows free users 1–2 real plays (+ "more with Pro" footer).
- [x] ✅ Feedback loop: checklist feedback step + one-time auto-prompt after engagement (`lib/feedbackPrompt.ts`, `FeedbackWidget` opens via `ss:open-feedback`).

### 10. Landing page is current (no PDF-era artifacts)
- [x] ✅ Replaced the 5 PDF-era screenshots with on-brand **inline mockups** (price distribution, positioning scores, launch-velocity chart, winning products, discount analysis) that match the current SaaS UI and never go stale. Deleted the unused `/public/screenshots/*.png` files.
- [x] ✅ Copy sweep: the only "report/PDF/one-time" mentions left are **intentional competitor-contrast** (e.g. the comparison table's "One-time reports" column, "shareable report URLs replace PDF attachments") — not stale self-description.
- [ ] ⬜ (Optional, later) Swap the inline mockups for real screenshots of the live app once the demo account (item 7) is polished, if you prefer literal screenshots.

### 11. "Ops Room" full UI redesign — shipped
- [x] ✅ Complete visual identity replacement across every surface (landing, auth, onboarding, app, public reports, legal, emails): warm-charcoal + signal-amber system, Space Grotesk + mono-first instrumentation, panel/hairline shape language, chart palette validated for accessibility, dual-axis chart eliminated.
- [ ] ⬜ **Recapture all marketing assets** — any screenshots/videos Jaiden has (or captures for outreach) must use the new Ops Room look; anything showing the old blue UI is now off-brand.
- [ ] ⬜ Visual QA pass in a real browser across app pages (logged-in surfaces couldn't be smoke-tested in dev container; public routes verified 200 + tsc clean).

---

## 🟢 Polish — before scaling, not before first sales

- [ ] ⬜ Pre-existing lint errors in `UpgradeModal.tsx` (`window.location.href`) and `AddCompetitorModal.tsx` (`checkStore` hoisting) — not introduced by recent work; clean up when convenient.
- [ ] ⬜ Mobile onboarding + error-state QA.
- [ ] ⬜ Hide internal "Developer" tier from public pricing; verify annual toggle math.
- [ ] ⬜ Run the full `EDGE_CASES.md` checklist against production.
- [ ] ⬜ Basic support/help path (even a simple FAQ link or contact form beyond the email).

---

## Quick reference — env vars to set for launch
| Var | Where | Purpose |
|---|---|---|
| `stripe_pro_price_id` / `_annual` | backend (Render) | Pro plan checkout |
| `stripe_agency_price_id` / `_annual` | backend | Agency plan checkout |
| Stripe secret key + webhook secret | backend | billing + webhook verification |
| `NEXT_PUBLIC_GA_ID` | frontend (Vercel) | Google Analytics 4 |
| `NEXT_PUBLIC_FB_PIXEL_ID` | frontend | Meta Pixel |
| Resend domain auth (SPF/DKIM/DMARC) | DNS | email deliverability |
| `META_AD_LIBRARY_TOKEN` (optional) | backend | public competitor ad feed in the playbook |

---

*When every 🚫 is ✅, we can start selling. The 🟡 items should follow within the first week or two of live sales.*
