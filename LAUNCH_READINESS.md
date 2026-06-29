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
- [ ] 🚫 **Fill in `[GOVERNING STATE]`** in `frontend/app/terms/page.tsx` §14 (governing law + venue). Reply to Devon's chat with the US state and it gets dropped in.
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
- [ ] 🚫 Confirm the 3 landing-page testimonials (Sarah M., Marcus R., Jake L.) are **real**, or replace/remove them. Fake testimonials are an FTC + trust risk — higher exposure now that we're doing outreach.

---

## 🟡 Important — sell, but fix fast / don't oversell

### 5. Analytics & conversion tracking
- [x] ✅ GA4 + Meta Pixel wired (env-gated, ships inert until keys set). `frontend/components/Analytics.tsx`, `frontend/lib/analytics.ts`, mounted in `app/layout.tsx`.
- [x] ✅ Provider-agnostic `track()` helper + initial events: `upgrade_clicked`, `competitor_added`.
- [ ] ⬜ Set env vars in prod: `NEXT_PUBLIC_GA_ID` (GA4 measurement ID) and `NEXT_PUBLIC_FB_PIXEL_ID` (Meta Pixel ID). Until set, no tracking fires.
- [ ] ⬜ Add remaining funnel events from the blueprint: `signup_completed`, `first_scan_completed`, `subscription_started` (server-side from the Stripe webhook is most reliable for the last one). The helper + Meta standard-event mapping are already in place.
- [ ] ⬜ Create the GA4 property + Meta Pixel; define the activation funnel (signup → competitor_added → first_scan → upgrade).

### 6. Google GA4/GSC integration (partial)
- [ ] ⬜ Either finish data sync, or **hide the Google integration** from Settings/marketing so we don't promise what isn't live. (Klaviyo, Slack, Shopify-connect are fully shipped — those are fine to feature.)

### 7. Demo account
- [ ] ⬜ Stand up a presentable demo account with good-looking real data (for screenshots + sales calls). Confirm which `scripts/seed_test_data.py` user is safe to use.

### 8. Fresh-signup QA pass
- [ ] ⬜ Walk the full new-free-user path once on production after recent changes (tier-aware upgrade modal, discovery limit = 1, free weekly alert, integration nudges): signup → onboarding → first scan populates → upgrade prompts fire correctly → free limits enforced.

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

---

*When every 🚫 is ✅, we can start selling. The 🟡 items should follow within the first week or two of live sales.*
