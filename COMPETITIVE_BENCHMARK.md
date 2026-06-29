# StoreScout — Competitive Benchmark & What's Next

**For:** Devon + Jaiden, pre-outreach. Companion to `MARKETING_HANDOFF.md`, `OUTREACH_PROSPECTS.md`, `LAUNCH_READINESS.md`.
**Last updated:** 2026-06-29
**Method:** three research passes — current StoreScout surfaces (from the codebase), direct-competitor pricing/features (15+ tools, 2025–26), and 2026 freemium UX/onboarding/landing benchmarks. Sources at the bottom.

> ⚠️ **Note on stale web data:** public sources still describe StoreScout as the old "$9 one-time PDF report." That product is gone. This doc reflects the **current** product: a continuous-monitoring SaaS — **Free / $29 Pro / $79 Agency** — with change alerts + AI "Your Move" plays.

---

## 1. TL;DR verdict

**Are the plans good enough to sell? Yes on paid; the free plan has one fixable gap.**

- **Paid is competitive and well-priced.** $29 Pro gives continuous alerts + AI action plays + 10 competitors + 90-day history. The only comparable *continuous-monitoring* tools cost more and do less: Prisync ($99, price-only), Price2Spy ($40, price-only), Similarweb ($125, traffic-only). Agency ($79 / 50 competitors + shareable reports) is strong for the agency segment.
- **The moat is the AI action layer.** Almost every competitor stops at "here's what changed." StoreScout says **"here's exactly what to do about it."** Lead with this everywhere.
- **The one gap:** free rivals **Snoopie** and **Lurk** give *real-time per-change alerts for free*; StoreScout gates real-time alerts to Pro (free gets a once-weekly summary). Since "alerts within 15 min" is the headline promise, a free user never feels the core hook.

**Highest-leverage next move:** a **14-day reverse trial** (give new users Pro, then auto-downgrade to free). It closes the free-alert gap, lets every signup feel the aha, and — per 2026 benchmarks — converts **2–3× better than free-forever**.

---

## 2. Competitor landscape (corrected)

| Tool | Entry price | Free plan? | Continuous alerts? | AI insights? | Focus |
|---|---|---|---|---|---|
| **StoreScout** | **$29/mo** | **Yes** | **Yes (Pro+)** | **Yes — action plays** | **Shopify price + launch + discount + stock monitoring with AI "what to do"** |
| *Snapshot / research tools* | | | | | |
| Koala Inspector | $22/mo | Yes (15 tokens) | No | No | Shopify spy (point-in-time) |
| Commerce Inspector / Shine | ~$49/mo | Yes (limited) | No | Limited | Store + sales-estimate research |
| Ecomhunt | $29/mo | Yes | Limited | Yes (trend scoring) | Curated product research |
| SellerCenter | Free | Yes | No | No | Store database (2.3M) |
| UniSpy / Niche Scraper | $40–50/mo | Yes (limited) | Limited | Limited–Yes | Sales tracking / product research |
| *Continuous-alert tools* | | | | | |
| **Snoopie** | Free+ | Yes | **Yes (free)** | No | Store-change email alerts |
| **Lurk** | Free+ | Yes | **Yes (free)** | Yes | AI price crawl + repricing |
| PPSPY | $39/mo | Yes | Yes (major actions) | Moderate | Dropshipper sales tracking |
| Prisync | $99/mo | 14-day trial | Yes | Moderate | Price monitoring + dynamic repricing |
| Price2Spy | $40/mo | Limited | Yes | Limited | Budget price monitoring |
| *Enterprise* | | | | | |
| Similarweb | $125/mo | Yes (basic) | No | Limited | Traffic intelligence (not ecommerce-specific) |
| Competera / Intelligence Node | ~$50k/yr | No | Yes | Yes | Enterprise price optimization |

---

## 3. Where StoreScout wins / is exposed

**Wins:**
- **AI action layer** — "Your Move" plays with platform + budget + copy. Near-unique; the rest give data.
- **Multi-signal** — price *and* launches *and* discounts *and* stock, not price-only (Prisync/Price2Spy).
- **Continuous monitoring at $29** — below every comparable continuous tool except free ones that lack AI.
- **Agency fit** — 50 competitors + shareable report URLs at $79; no clean equivalent.
- **Trust angle** — public Shopify data, "no ToS issues," no API keys.

**Exposed:**
- **Free real-time alerts** — Snoopie/Lurk give them free; StoreScout gives free users only a weekly summary. (Top fix.)
- **No dynamic repricing** — Prisync/Lurk auto-reprice; StoreScout recommends, doesn't act. (Fine — different lane; don't chase it.)
- **Brand-new, no reviews yet** — competitors have G2/review history. The feedback→testimonial loop is built; needs first real reviews.

---

## 4. Plan adequacy

| | Free | Pro $29 ($23 annual) | Agency $79 ($63 annual) |
|---|---|---|---|
| Competitors | 1 | 10 | 50 |
| Scan cadence | weekly (manual) | daily | every 12h |
| Price history | current only | 90 days | unlimited |
| Real-time alerts (email/Slack) | ❌ (weekly summary only) | ✅ | ✅ |
| AI weekly digest | ❌ | ✅ | ✅ |
| AI playbook / Scout Brief | brief on Overview ✅; full playbook teaser | ✅ full | ✅ full |
| Team seats / shareable reports | ❌ | reports ✅ | team ✅ + reports ✅ |

**Read:** pricing is competitive — $29 entry sits below the continuous-monitoring pack ($39–$99) while adding AI nobody else has. The free tier is *insight-rich* (real AI brief, positioning scores, watchlist, checklist) but *alert-poor* vs free rivals. Two ways to close it: **(a) reverse trial** (preferred — see §6), or **(b) a single free real-time alert taste**.

---

## 5. Page-by-page scorecard (vs 2026 benchmarks)

**Landing — Strong, 3 gaps.** Has: outcome-led headline, inline product mockups (≈ interactive), comparison table, risk reversal ("no credit card"), transparent pricing. Gaps:
- **Social proof above the fold** (benchmark: +63% CVR when near the hero/CTA). Currently mid-page and empty until reviews land.
- **Clickable/interactive demo** (benchmark: 2× engagement; 88% want to see the product before booking). The inline mockups are static.
- **Named-competitor comparison** — the table compares "Chrome extensions / one-time reports," not Koala/Prisync/Snoopie. Buyers compare named tools.
- Could **lead harder on the AI differentiator** ("we tell you what to do").

**Onboarding — Strong.** 4 steps (URL + real-time validation → about-you + category suggestions → plan → ~60s first scan), now with the Getting Started checklist. Near best-practice (aha < 2 min). Keep as-is; just confirm the first scan reliably lands < 2 min on production.

**Dashboard — Rich, watch density.** ScoutBrief, StatsBar, checklist, "Your Move," signal feed, watchlist, playbook widget, integration nudge. For a **1-competitor free user** much of this is empty/zero — benchmark warns against overwhelming early. Consider progressive disclosure (the checklist already helps).

**Free plan — Strong on insight, gap on alerts.** See §4 / §1.

---

## 6. What to do next (prioritized)

**P0 — Reverse trial (highest leverage; strategic — needs Devon's sign-off).**
14 days of Pro on signup (no card) → auto-downgrade to free. Every new user feels real-time alerts + AI digest + full playbook, then converts on loss aversion. Benchmark: reverse trials convert **2–3× vs free-forever**; **60% of conversions happen in the first 14 days**. Implementation touches tier logic in `app/core/config.py` / `app/api/v1/user.py` + a `trial_ends_at` on the profile + a downgrade job + an in-app trial banner.

**P0 — Sharpen landing differentiation (quick, no monetization risk).**
In `frontend/app/page.tsx`: add a "StoreScout vs Koala / Prisync / Snoopie" comparison, and tighten the hero/positioning around **"know what to *do*, not just what changed."**

**P1 — Social proof above the fold.** The feedback→`/feedback/public` loop is built; once 2–3 real ★≥4 reviews exist, surface one + Shopify-store logos near the hero (not just the mid-page section).

**P1 — Interactive/clickable demo.** Animate the existing inline mockups, or add a short guided demo near the hero.

**P1 — Free-plan alert taste (only if NOT doing the reverse trial).** Let free users feel one real alert — e.g., email their *first* detected change once, or speed up the weekly free summary — to counter Snoopie/Lurk free alerts.

**P1 — Behavioral upgrade triggers.** Fire contextual upgrade prompts exactly when a free user hits "90-day history," a locked play, or the discovery limit. Benchmark: behavioral triggers convert **3.4× vs time-based**. (The competitor-limit modal already does this — extend the pattern.)

**P2 — Pricing-page polish** (mobile table, explicit free-vs-paid rows) and **dashboard density tuning** for 1-competitor free users.

**Recommended sequence:** landing differentiation first (cheap, safe, helps Jaiden's outreach immediately) → scope the reverse trial with Devon (biggest lever) → social proof as reviews arrive → behavioral triggers.

---

## 7. Sources

**Competitors:** Koala Inspector pricing (koala-apps.io); Commerce Inspector 2026 (news.astools.app); PPSPY (ppspy.com); Ecomhunt (ecomhunt.com/pricing); Similarweb / ecommerce alternative (brandsearch.co); Prisync (capterra.com/p/153451); Price2Spy (capterra.com/p/154047); Snoopie & Lurk (Shopify App Store); SellerCenter (sellercenter.io); best Shopify spy tools 2026 (pagefly.io).
**Freemium / onboarding / landing (2026):** ChartMogul SaaS conversion report; First Page Sage freemium conversion 2026; Userpilot freemium guide; Flowjam & Candu onboarding 2025–26; DigitalApplied time-to-value 2026; SaaSHero/LaunchWall social-proof guides; SuccessKnocks B2B pricing-page 2026; Semrush pricing 2026 (backlinko, ampifire).

*If reality and this doc disagree, the product wins — update the doc. Competitor pricing changes often; re-verify before quoting specific numbers in outreach.*
