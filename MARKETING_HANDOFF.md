# StoreScout — Internal Marketing Handoff

**Audience:** Jaiden (Marketing, organic content, outreach, social, lead gen, customer conversations)
**Owner of this doc:** Devon (Product, backend, frontend, infra, AI, integrations, paid ads)
**Company:** Anonymous Mentality LLC
**Last updated:** 2026-06-29

> **Purpose:** Make you fully self-sufficient representing StoreScout — accurately. Every claim in here is sourced from the actual shipped product, so you can say it in public without us getting caught overpromising. When in doubt, this document beats memory.

---

## 0. How to use this doc

Read sections 1–6 first — that's everything you need to talk about StoreScout confidently. Sections 7–11 are operational (assets, Q&A bank, outreach motions, logging templates, our weekly feedback ritual).

**Status legend** — every feature is tagged:

| Tag | Meaning |
|---|---|
| ✅ **Live** | Shipped, working in production. Sell it. |
| ⚠️ **Partial** | Half-built. Don't lead with it; don't promise it. |
| 🗺️ **Roadmap** | Planned, not built. Only mention as "coming," never as "we have." |
| 🚫 **Never claim** | We do NOT do this and likely never will. Saying it gets us in trouble. |

**The golden rule of accuracy:** StoreScout reads **public Shopify catalog data**. That's the whole foundation. It is *not* a traffic tool, *not* a revenue estimator, *not* an ad spy tool. When a prospect pushes toward those, redirect to what we actually do (see §2 "What NOT to call it" and §6 objection handling).

---

## 1. Executive Summary

### What StoreScout is
StoreScout is a **live competitor-intelligence platform for Shopify stores**. It monitors any Shopify store around the clock and tells the user — by email, Slack, or in-app — when a competitor changes prices, launches products, starts a discount, or runs a flash sale. Then its AI turns each change into a specific, executable move the operator can run that day.

It works off the **public `/products.json` data that every Shopify store exposes** — no API keys, no logins, no scraping of private pages. If a store runs on Shopify, we can usually track it.

### Who it's for
- **DTC Shopify brand operators** ($500K–$10M revenue, 1–5 person teams) who make pricing and product decisions weekly and can't afford a $800/mo enterprise tool.
- **Shopify agencies** running competitive analysis across multiple clients, who want shareable, always-current reports instead of stale PDF decks.

### The problem it solves
Operators find out what competitors did **days late** — usually after a customer, a Reddit thread, or a Slack message tips them off, by which point the flash sale is over and the margin is already gone. Manually checking competitor sites is tedious, easy to forget, and impossible to scale past one or two stores. StoreScout makes that awareness **continuous and automatic**, and — critically — tells you what to *do* about each change, not just that it happened.

### Elevator pitch
> "StoreScout watches your Shopify competitors 24/7 and emails you the moment they change prices, launch a product, or run a sale — then tells you exactly how to respond. It's like having an analyst who never sleeps, for $29 a month instead of $800."

---

## 2. Product Positioning

### How to describe it
- **Plain:** "Competitor monitoring and alerts for Shopify brands."
- **Sharper:** "Live competitor intelligence for Shopify — know what your competitors do the day they do it, and what to do about it."
- **Strategic narrative (see also §5):** "Semrush for Shopify stores" — a continuous intelligence layer that compounds as it accumulates competitor history over time.

### What category it belongs in
**Competitive / market intelligence for ecommerce**, specifically the Shopify ecosystem. We sit between cheap one-off "spy" Chrome extensions and expensive enterprise market-intelligence suites — continuous monitoring + AI action plays at an operator-friendly price.

### The unique value proposition
**Continuous change detection + AI that tells you what to do, under $100/month.** Other tools give you a point-in-time snapshot or raw data and leave you to figure it out. StoreScout watches over time, flags only what matters, explains why it matters, and hands you a concrete move.

### What NOT to call it (this matters — accuracy guardrails)
- 🚫 **Not an "ad spy tool."** We do not track anyone's ads, ad spend, or creatives.
- 🚫 **Not a "revenue/sales estimator."** We cannot and do not estimate competitor revenue, sales volume, or order counts. Public catalog data does not contain it.
- 🚫 **Not a "traffic/analytics tool."** No visitor counts, no conversion rates, no Similarweb-style traffic.
- 🚫 **Not a "scraper" in the sketchy sense.** Frame it as "reads public product data Shopify already publishes." Never "scrapes private data."
- ⚠️ **Not "real-time" in the literal sense.** Say **"continuous monitoring with alerts within 15 minutes of detection."** Scans run on a schedule (daily on Pro); we alert within ~15 minutes of *detecting* a change at the next scan — usually same-day. (More on this nuance in §6 objection handling.)

---

## 3. Ideal Customer Profile (ICP)

### Primary customers
**DTC Shopify brand operators / founders / ecommerce managers.**
- Company size: solo to ~15 people; roughly $500K–$10M annual revenue.
- They run paid social, set promotions, and make pricing/launch calls weekly.
- Pain: reacting late to competitor promos, guessing on pricing, no time for manual research.
- Why they buy: defend margin, time promos, spot product gaps — without hiring an analyst.

### Secondary customers
**Shopify agencies & freelance ecommerce strategists.**
- Run competitive audits for multiple clients.
- Pain: competitive research is manual, and PDF reports are stale the moment they're sent.
- Why they buy: **shareable, always-current report URLs** (replace PDFs), track up to 50 stores across clients, look more sophisticated to clients. Agency tier is built for this.

### Customers to avoid (poor fit — don't waste outreach on them)
- **Non-Shopify stores** (WooCommerce, BigCommerce, Magento, custom). We only do Shopify today. 🗺️ Others are roadmap.
- **Pre-revenue / hobby stores** with no competitors they actively track and no budget.
- **Enterprises** that need traffic, revenue, or ad-spend intelligence — that's not our data. They'll churn disappointed.
- **Brands whose competitors all block `/products.json`** (rare, but headless/heavily-protected stores can't be read).

### Typical company sizes
1–15 employees. Decision-maker is usually the founder, head of ecommerce, or agency lead — a single person who can swipe a card. No procurement, no committee. This is why $29 is the sweet spot.

### Typical pain points (use these verbatim in copy)
- "I found out my competitor ran a 40%-off sale *after* the weekend."
- "I'm checking 3 competitor sites by hand every Monday and still missing stuff."
- "I have the data but no idea what to actually do with it."
- "Enterprise tools cost more than my ad budget."

---

## 4. Complete Feature Breakdown

> For each: **what it does · why users care · the outcome · common objections · outreach talking points.** Status tag on each.

### 4.1 Competitor tracking & scanning ✅ Live
- **What:** Add any Shopify store by URL; we scan its public catalog (up to 2,500 products) and track product count, median price, promo rate, and full catalog detail. Free scans weekly; Pro daily; Agency every 12h.
- **Why users care:** One place to watch every competitor that matters, updated automatically.
- **Outcome:** They stop manually checking sites and never lose track of a competitor again.
- **Objections:** *"Can't I just check myself?"* → You can, for one store, once. You won't do it for 5 stores every day forever — and you'll still miss the overnight changes. *"Is this legal?"* → Yes; it's public data Shopify publishes (see §6).
- **Talking points:** "Track up to 10 (Pro) or 50 (Agency) competitors on autopilot."

### 4.2 Change detection ✅ Live
- **What:** Compares each scan to the last and flags: new products, removed products, price changes (>3% to cut noise; ≥10% drop = warning), flash sales (5+ products dropping ≥20% = critical), stock-ins/outs, and discount-campaign starts/ends. Bulk changes (>10 of one type) collapse into a single clean summary.
- **Why users care:** Signal, not noise. They see the moves that matter, not every trivial cent.
- **Outcome:** They catch a flash sale or a price drop the day it happens.
- **Objections:** *"Will I get spammed?"* → No — there's a 4-hour cooldown per change type and bulk-aggregation, specifically so you don't get flooded.
- **Talking points:** "We separate a real flash sale from a one-product price tweak automatically."

### 4.3 Real-time alerts (email + Slack + webhook) ✅ Live · Pro/Agency only
- **What:** When a meaningful change is detected, we email it within ~15 minutes — with a severity badge, a 1–2 sentence AI read of what it means, the list of changed products, and a recommended response. Also pushes to Slack or any webhook (Zapier, etc.).
- **Why users care:** Speed. They can match or counter a promo the same day.
- **Outcome:** "Matched their Black Friday offer the same day" (real testimonial theme).
- **Objections:** *"How fast, really?"* → Within ~15 min of **detection**. Pro scans daily, so practically same-day. Be precise here (see §6).
- **Talking points:** "If a competitor drops prices, you'll know before your customers do."

### 4.4 AI Playbook — "Your Move" ✅ Live · Pro/Agency only
- **What:** Claude (Sonnet 4.6) reads all your competitor data + recent changes and generates **3 executable plays**, each in a 3-step format: (1) exact platform + menu path, (2) exact content/copy to use, (3) budget + when to scale. Sorted into "Act Now / Right Now / This Week." Names real platforms (Meta Ads Manager, Google Shopping, Klaviyo, Shopify Admin, TikTok Ads).
- **Why users care:** This is the differentiator. Everyone else gives data; we give *the move*.
- **Outcome:** A non-analyst operator knows precisely what to do this week and how much to spend.
- **Objections:** *"Is it generic AI fluff?"* → No — it cites the specific data point behind each play and names exact products/prices/platforms.
- **Talking points:** "It doesn't just say 'they're on sale' — it says 'duplicate your best Meta ad set, target their followers, run $15/day, scale to $50 once CTR beats 1.8%.'"

### 4.5 Intelligence Brief (Scout Brief) ✅ Live · Pro/Agency (free sees a teaser)
- **What:** After each scan, a 4-card AI brief: **Signal** (most notable thing), **Opportunity** (clearest opening), **Watch** (trend to monitor), **Action** (the one thing to do this week). First scan uses Sonnet 4.6; rescans use Haiku 4.5.
- **Why users care:** 20-second strategic read on each competitor.
- **Outcome:** Instant "so what" without digging through charts.
- **Talking points:** "Your AI strategist already read the data before you logged in."

### 4.6 Weekly AI Digest ✅ Live · Pro/Agency only
- **What:** Every Monday, a 4–6 sentence Claude-written strategic summary per competitor: the biggest pattern, what it signals, one action to consider.
- **Why users care:** A standing Monday-morning briefing with zero effort.
- **Outcome:** They start the week knowing where to focus.
- **Talking points:** "A competitive brief in your inbox every Monday, written to be read in 20 seconds."

### 4.7 Quick Wins, Gaps, Winning Products, Store Profile, Comparison ✅ Live · Pro/Agency
- **Quick Wins:** dismissable opportunity cards per competitor.
- **Gaps:** catalog gap analysis — price bands, availability, category, discount, launch-momentum openings.
- **Winning Products:** flags competitor products worth testing vs. watch vs. skip, with reasoning (momentum, markdown depth, scarcity).
- **Store Profile / Comparison:** positioning scores (market position, promo intensity, launch velocity, catalog complexity) and a **you-vs-them** comparison once the user adds their own store.
- **Why users care:** Turns raw catalog data into "where can I win?"
- **Talking points:** "See exactly where a competitor is thin — and where you can move in."

### 4.8 AI Competitor Discovery ✅ Live
- **What:** Describe your store and the AI suggests real Shopify competitors to track. Free users get **1 discovery search/month**; Pro/Agency unlimited.
- **Why users care:** They may not even know who to watch.
- **Talking points:** "Not sure who your real competitors are? We'll find them."

### 4.9 Shareable Reports ✅ Live · Pro/Agency
- **What:** Public, no-login report URL per competitor snapshot — pricing distribution, discount metrics, launch velocity, AI brief. Safe to share (aggregate data only, no private product dumps).
- **Why users care (esp. agencies):** Replaces stale PDF deliverables with a live link clients actually open and bookmark.
- **Talking points:** "Send clients a link, not a PDF. They'll bookmark it and ask for more stores."

### 4.10 Team seats ✅ Live · Agency only
- **What:** 2 invite-based seats on Agency. **Talking point:** "Bring your strategist or your client onto the account."

### 4.11 Integrations
- **Shopify OAuth (connect your own store)** ✅ Live — verifies your store and personalizes playbook context.
- **Klaviyo** ✅ Live — paste API key; we pull list/segment context into the playbook so email plays are personalized.
- **Slack / generic webhooks** ✅ Live — route alerts anywhere.
- **Google GA4 / Search Console** ✅ Live — connect via OAuth, pick a property/site, and the playbook pulls in sessions, top pages, and top search queries to personalize recommendations. (Verify live with a real connected account before leaning on it in a demo.)
- **API access** ✅ Live · Pro+ — up to 5 keys for developers.

### 4.12 Onboarding & lifecycle emails ✅ Live
- **What:** 4-step onboarding (category → goal → suggested stores → first scan), then a drip sequence (D0 first-scan results, D1, D3, D7, D14) that educates free users and nudges upgrades.
- **Talking point:** "You'll see real competitor data within ~60 seconds of signing up — free, no card."

### Roadmap (🗺️ — say "coming," never "have")
- **Meta Ads integration** — pulling the user's ad-account performance and/or competitor ad intelligence into the playbook. **Deferred until the business is registered** (the Meta Business API requires a registered/verified business). Note: the playbook can still *recommend* Meta ad moves today; this is about *connecting* Meta as a data source. (A public **Meta Ad Library** competitor-ad feed does NOT need the business registered and could land sooner — see below.)
- WooCommerce / BigCommerce support.
- Deeper benchmarking of your store vs. tracked competitors.
- Competitor ad-activity feed via the public Meta Ad Library (independent of the user's own Meta account).

---

## 5. Competitive Landscape

> The honest #1 competitor is **"a spreadsheet + checking sites manually."** Most prospects aren't switching from a tool — they're switching from a chore. Lead with "stop checking by hand."

### Koala Inspector (Chrome extension)
- **Strengths:** Popular, free/cheap, instant per-store inspection (themes, apps, products).
- **Weaknesses:** Point-in-time only — no continuous monitoring, no alerts, no history, no AI action plays. You have to remember to open it on each store.
- **How we differ:** We watch continuously and *alert you*; we don't wait for you to go look. And we tell you what to do.

### Commerce Inspector / Commerce intelligence tools
- **Strengths:** Product/best-seller discovery, some trend data.
- **Weaknesses:** Research-oriented, not a continuous change-alert system; pricier; not focused on "what do I do today."
- **How we differ:** Continuous change detection + AI playbook at operator pricing.

### EcomSpy / PPSPY / dropshipping "spy" tools
- **Strengths:** Cheap, product-hunting features, sometimes sales *estimates*.
- **Weaknesses:** Built for dropshippers hunting winning products; their "sales estimates" are guesses; not built for an established brand defending margin. Noisy.
- **How we differ:** We serve real brands/agencies, we don't fabricate revenue numbers, and we focus on monitoring + action, not product-hunting. (Use our honesty as a selling point: "We won't show you made-up revenue figures.")

### Similarweb / enterprise market intelligence
- **Strengths:** Traffic, audience, broad web data; brand authority.
- **Weaknesses:** $$$ (often $800+/mo), overkill for a single Shopify brand, not Shopify-catalog-specific.
- **How we differ:** Purpose-built for Shopify catalog/pricing intelligence at 1/20th the price. Different data (we don't do traffic — be clear), different buyer.

### Why we win for our ICP (the data-moat / strategic story)
StoreScout accumulates **time-series catalog history** for every tracked store. Anyone can copy a scraper in a week; they can't copy a year of price-and-launch history across thousands of stores. The longer we run, the more valuable and harder to replicate we become. That's the "Semrush for Shopify" thesis — and it's the reason to plant the flag now.

---

## 6. Messaging Guide

### One-sentence pitch
> "StoreScout monitors your Shopify competitors 24/7 and tells you the moment they change prices, launch, or run a sale — plus exactly how to respond."

### Elevator pitch (≈3 sentences)
> "Shopify brands lose margin because they find out about competitor sales and price drops days too late. StoreScout watches any Shopify store around the clock and alerts you within minutes of a change — then its AI hands you a specific move to make that day. It starts free and is $29/month for the full thing, versus $800 for enterprise tools."

### 30-second explanation
> "If you run a Shopify store, you have competitors you should be watching — but checking their sites by hand is a pain and you still miss the overnight changes. StoreScout does it for you automatically. Add your competitors, and we scan their public catalog every day. The second they drop prices, launch a product, or kick off a flash sale, you get an email or Slack ping within about 15 minutes — with the exact products that changed and an AI-written play for how to respond. Operators use it to match promos same-day and protect margin. Free to start, $29/month for daily scans, alerts, and the AI playbook."

### 2-minute explanation
> "StoreScout is competitor intelligence built specifically for Shopify brands. Here's the problem: every Shopify store publishes its full product catalog at a public endpoint. That data — every price, every product, every discount — is sitting right there, but nobody has time to track it across multiple competitors by hand, every day. So operators react late. They find out a competitor ran 40% off *after* the weekend's already gone.
>
> StoreScout fixes that. You add the competitors you care about — and if you're not sure who they are, our AI suggests them. We scan their public catalogs automatically: daily on the paid plan. Every scan, we diff it against the last one and detect what actually changed — price moves, new launches, products pulled, stock-outs, and full-blown flash sales. We filter the noise so you only hear about what matters.
>
> When something does matter, you get an alert within about 15 minutes of us detecting it — email, Slack, or webhook — with a severity flag, the exact products involved, and a one-line read of what it signals. Then the AI Playbook goes further: it generates three concrete moves, each with the exact platform, the exact copy, and the budget to spend. Not 'they're on sale' — actually 'duplicate your best Meta ad set, target their audience, run $15 a day, scale once your click-through beats 1.8%.'
>
> It's free to start with one competitor, $29/month for ten competitors with daily scans, alerts, history, and the AI features, and $79/month for agencies tracking up to fifty stores with shareable client reports. It's all built on public data — no logins, no API keys, completely above board."

### Social media hooks (organic content)
1. "Your Shopify competitor just dropped prices 30%. You'll find out… Tuesday. 😬"
2. "I checked 5 competitor sites by hand every Monday for a year. Here's what I should've done instead. 🧵"
3. "Every Shopify store leaks its entire pricing strategy publicly. Here's where. 👇"
4. "Stop finding out about competitor sales from Reddit."
5. "We built an AI that watches your competitors and tells you what to do. Here's a real play it generated:"
6. "Flash sales last 48 hours. Most brands react in 72. That gap is your margin."
7. "The cheapest competitive-intelligence tool I've found costs $800/mo. So we built a $29 one."
8. "What 2,500 product prices can tell you about a competitor's strategy (a breakdown)."
9. "'Just check their site' doesn't scale past one competitor. Here's the math."
10. "Agencies: stop sending clients PDFs that are stale before they open them."

### Cold-outreach hooks (DM / email openers)
1. "Noticed [brand] competes with [competitor] — did you catch their price drop last week?"
2. "Quick one: how are you currently tracking what [competitor] is doing on pricing?"
3. "Built a tool that would've flagged [competitor]'s flash sale 15 min after it started — worth a look?"
4. "You're clearly watching the [category] space closely — want it on autopilot?"
5. "Saw you run promos often — do you know when your competitors do, before they're over?"
6. (Agency) "Do your competitive audits go stale the day after you send them? There's a fix."

### Value propositions (bank — mix and match by persona)
- **Speed:** "Know the day they move, not the week after."
- **Action:** "We don't just show you data — we give you the move."
- **Price:** "$29/month vs. $800 enterprise tools."
- **Effort:** "Set it once. Stop checking sites by hand."
- **Trust:** "Built on public data — no logins, no gray areas."
- **Agency:** "Shareable live reports your clients actually open."

### Objection handling
| Objection | Response |
|---|---|
| **"Is this legal / ToS-safe?"** | "Yes. We only read the public product data Shopify stores already publish at `/products.json` — same data anyone can see in a browser. No private pages, no checkout, no admin, no logins. Using public competitor pricing is standard practice." |
| **"How fast are alerts, really?"** | Be precise: "Within about 15 minutes of us **detecting** a change. Paid plans scan daily, so in practice it's same-day. We're not claiming to read their mind the instant they click save — we're claiming you'll know the same day, automatically, instead of days later by accident." |
| **"Can't I just check myself?"** | "For one store, once — sure. But you won't do it for five stores every single day forever, and you'll still miss the overnight stuff. We make it automatic and add the 'what to do' on top." |
| **"Does it tell me their revenue/traffic?"** | "No — and we won't pretend to. Tools that 'estimate revenue' are guessing. We work off real, public catalog data: pricing, products, launches, discounts, stock. That's what you can actually act on." |
| **"Is the AI just generic fluff?"** | "It cites the specific data point behind every recommendation and names exact platforms, products, and budgets. I can show you a real play it generated." |
| **"My competitors aren't on Shopify."** | "Then we're not your tool yet — we're Shopify-only today (WooCommerce/BigCommerce are on the roadmap). I'd rather tell you that than sell you something that won't work." |
| **"Why pay when there's a free plan?"** | "Free tracks one competitor and scans weekly with no alerts — great for trying it. The value is in daily scans, real-time alerts, and the AI playbook, which is the $29 plan." |
| **"What if a competitor blocks you?"** | "Most Shopify stores expose this data by default and we handle the protected ones well. A small number of heavily-locked/headless stores can't be read — we'll tell you up front if one can't." |

---

## 7. Marketing Assets Checklist

> Split into **Have now** vs. **Need from Devon / to create.** Confirm access to each before launch.

### ✅ Have now (in the product/codebase)
- **Live landing page** — `getstorescout.com` (hero, pricing, features, testimonials, FAQ).
- **FAQ content** — in the product (`FaqAccordion.tsx`); reuse verbatim for sales replies.
- **Brand basics** — name **StoreScout**; domain **getstorescout.com**; from-email **hello@getstorescout.com**; logo mark = Zap icon; palette: blue `#3b82f6` (primary), emerald `#22c55e` (success), light-blue `#60a5fa` (links), near-black `#060d18` (bg).
- **Pricing** — Free $0 / Pro $29 ($23 annual) / Agency $79 ($63 annual); 20% annual discount.
- **Sample emails** — onboarding drip (D0/D1/D3/D7/D14), change alerts, weekly digest (all real, in product).
- **Testimonials** — 3 on the landing page (Sarah M. footwear, Marcus R. agency, Jake L. fashion). *Confirm with Devon whether these are real customers or illustrative before quoting in outreach.*
- **Demo / seed accounts** — seed users exist (`scripts/seed_test_data.py`, e.g. `seed-pro@storescout.test`, `seed-agency@…`). ⚠️ **Confirm with Devon which are usable for live demos** before showing anyone.

### ⬜ Need from Devon / to create
- **Screenshots** (clean, real-data): dashboard, competitor detail (Overview + Intelligence), an alert email, the AI Playbook, a shareable report. *(Devon to provide a demo account with good-looking data.)*
- **Demo video** (60–90s walkthrough: add competitor → scan → alert → playbook).
- **Brand kit file** (logo SVG/PNG variants, color swatches, font) — currently lives only in code.
- **Pricing one-pager** (PDF/image for DMs and decks).
- **Analytics access:** GA + Meta Pixel on the marketing site (confirm Devon adds you).
- **Social accounts:** confirm which exist / who owns handles (X, LinkedIn, IG, TikTok); get logins.
- **Meta Business / Ads access:** Devon owns paid ads — confirm read access for organic coordination.
- **Email/domain sending:** Resend powers product email; confirm what (if anything) you can send marketing email from, and from which address.
- **A "real customer" testimonial pipeline** — see §10/§11; start collecting from day one.

---

## 8. The 50 Most Likely Prospect Questions (with answers)

> All answers are accuracy-checked. Where a question pushes toward something we don't do, the answer redirects honestly.

**Data & legality**
1. *Is it legal to track a competitor's store?* — Yes. We read only public product data Shopify publishes; no private/admin/checkout access.
2. *Are you scraping their site?* — We read the public `/products.json` catalog Shopify exposes — the same data visible in a browser. No private pages.
3. *Will my competitor know I'm tracking them?* — No. There's no notification to them; we read public data like any visitor.
4. *Where does the data come from?* — Each Shopify store's public catalog endpoint: prices, products, variants, discounts, stock, tags, vendors.
5. *Can you track non-Shopify stores?* — Not today; Shopify only. WooCommerce/BigCommerce are on the roadmap.
6. *What if a store blocks you?* — Most don't. A few heavily-protected/headless stores can't be read; we'll tell you if one can't.
7. *How many products can you analyze per store?* — Up to ~2,500.
8. *Is the data accurate?* — It's the store's own published catalog data, so it's as accurate as what they publish; we note confidence where dates/discount fields are missing.

**What it does / coverage**
9. *What changes do you detect?* — Price changes, new products, removed products, discount campaigns, stock-ins/outs, and flash sales.
10. *Do you tell me their revenue?* — No. We don't estimate revenue or sales — that's not in public data, and we won't fake it.
11. *Do you show their traffic?* — No, we're not a traffic tool. We focus on catalog, pricing, launches, and discounts.
12. *Do you track their ads?* — No, we're not an ad-spy tool.
13. *Do you track their apps/theme?* — No; we focus on catalog/pricing intelligence.
14. *Can I see price history?* — Yes on paid plans: 90 days (Pro), unlimited (Agency). Free is current snapshot only.
15. *Do you track discounts/sales specifically?* — Yes, including flash-sale detection (5+ products dropping ≥20%).
16. *Can I compare a competitor to my own store?* — Yes — connect your store and use the Comparison view.
17. *Do you find competitors for me?* — Yes, AI discovery suggests real Shopify competitors (1/month free, unlimited on paid).

**Alerts & speed**
18. *How fast are alerts?* — Within ~15 min of detection; paid plans scan daily, so typically same-day.
19. *Is it truly real-time?* — Continuous monitoring with near-immediate alerts on detection; scans are scheduled (daily on Pro), not instantaneous to their click.
20. *How do I get alerts?* — Email, Slack, or webhook (e.g., Zapier).
21. *Will I get spammed with alerts?* — No; 4-hour cooldown per change type and bulk changes are summarized.
22. *Can I choose which alert types I get?* — Yes, per-type toggles in notification settings.
23. *Do free users get alerts?* — No — alerts are Pro/Agency. Free is in-app/weekly.

**AI features**
24. *What does the AI actually do?* — Generates a strategic brief and 3 executable "plays" per analysis, plus a weekly digest and per-alert interpretation.
25. *Is it just ChatGPT fluff?* — No; it cites the specific data point and names exact platforms, products, and budgets.
26. *Which AI do you use?* — Anthropic's Claude (Sonnet for playbooks/first brief, Haiku for digests/alerts).
27. *How often does the playbook update?* — Refreshes after scans (cached ~23h to stay efficient).
28. *Can the AI write my ad copy?* — It drafts headline/copy ideas and email angles as part of plays.
29. *Does the weekly digest cost extra?* — No, included on Pro/Agency.

**Pricing & plans**
30. *How much is it?* — Free $0; Pro $29/mo; Agency $79/mo. 20% off annual.
31. *Is there really a free plan?* — Yes, free forever: 1 competitor, weekly scan, in-app only.
32. *What's the difference between Free and Pro?* — Pro adds daily scans, real-time alerts, 90-day history, AI digest + playbook, and 10 competitors.
33. *What's in Agency vs. Pro?* — 50 competitors, unlimited history, 12h scans, 2 team seats, shareable client reports.
34. *Do I need a credit card to start?* — No.
35. *Can I cancel anytime?* — Yes, one click; you keep access until period end, data preserved.
36. *Do you offer annual billing?* — Yes, 20% off.
37. *Is there a free trial of Pro?* — The free plan is the trial; upgrade when you need alerts/daily scans. (Confirm with Devon if a Pro trial is ever offered.)
38. *What happens if I hit my competitor limit?* — You see an upgrade prompt; existing competitors keep scanning — nothing is paused or deleted.
39. *Do you have a refund policy?* — *Confirm exact policy with Devon.* Default: cancel anytime, no lock-in.

**Onboarding & use**
40. *How long to set up?* — About 60 seconds; first scan completes quickly and you see real data.
41. *How many competitors should I track?* — Most operators track 3–5; the ones you actually compete with.
42. *Do I have to connect my store?* — No, optional; connecting it unlocks the you-vs-them comparison and personalizes the AI.
43. *Is there a mobile app?* — It's a responsive web app; alerts come by email/Slack so you're covered on mobile.
44. *Can my team use it?* — Yes on Agency (2 seats).

**Integrations & security**
45. *Do you integrate with Slack?* — Yes, plus generic webhooks (Zapier, etc.).
46. *Do you integrate with Klaviyo?* — Yes; it personalizes email-related plays.
47. *Do you integrate with Google Analytics?* — Yes — connect GA4 + Search Console and the playbook factors in your sessions, top pages, and search queries. (Meta Ads as a connected data source is coming later.)
48. *Is there an API?* — Yes, on paid plans (up to 5 keys).
49. *How is my data / payment handled?* — Payments via Stripe; we don't store card data. Your account data is private to you (and your team on Agency).
50. *Who's behind StoreScout?* — A small, focused team (Anonymous Mentality) building the competitive-intelligence layer for Shopify. *(Keep founder framing consistent with how Devon wants to present the company.)*

---

## 9. Outreach Playbook

> **Principle:** lead with the prospect's pain and a specific observation about *their* niche, not a feature dump. Personalize the first line; keep it short; one ask.

### Cold email
**Structure:** (1) specific observation about their store/niche → (2) the pain → (3) one-line what we do → (4) soft ask.
**Template:**
> Subject: [competitor] dropped prices last week — did you catch it?
>
> Hey [name], I follow the [category] space and noticed [brand] goes head-to-head with [competitor]. They [recent move, if known]. Most operators find out about that kind of thing days late.
>
> I run StoreScout — it watches your Shopify competitors' catalogs daily and emails you within minutes when they change prices, launch, or run a sale, plus an AI play for how to respond. Built entirely on public data.
>
> Want me to set up [competitor] for you free so you can see it live? Takes a minute.

**Rules:** ≤120 words. One link max. Always offer a free, zero-friction look. Follow up max 2–3x.

### Cold DMs (X / LinkedIn / IG)
- Even shorter than email. Lead with a genuine observation or compliment about their store.
- Don't pitch in line 1. Ask a question: "How are you keeping tabs on [competitor] right now?"
- Move to value fast: offer to track one competitor for them free.
- Never paste a wall of features into a DM.

### Organic content (the long game)
- **Teardowns:** "What [well-known Shopify brand]'s catalog tells us about their pricing strategy." Use real StoreScout output (screenshots).
- **Education:** how public Shopify data works; how to time promos; how to spot a competitor's flash sale.
- **Build-in-public:** share real plays the AI generated, anonymized.
- **Cadence:** consistency > volume. 3–5 posts/week, one format you can sustain.

### Founder-led content
- Devon/you posting as real people > a faceless brand account. Show the product, show the thinking, show wins.
- Document the journey (building a Shopify intelligence tool) — this builds the "Semrush for Shopify" narrative and trust.

### Shopify communities (high-intent, easily-burned)
- **Where:** r/shopify, r/ecommerce, r/dropshipping (lower fit), Shopify Community forums, ecommerce Discords/Slacks, DTC/operator Facebook groups, indie-hacker spaces.
- **Etiquette (critical):** be a member first. Answer questions, add value, *then* mention the tool only when directly relevant. Most communities ban overt self-promo — read the rules, don't spam. One helpful comment that mentions us beats ten link drops that get you banned.

### Agency outreach (high LTV)
- Pitch the **shareable report** angle hard: "Replace stale PDF audits with live links clients bookmark."
- Lead with the 50-competitor / multi-client economics and white-label-ready reports.
- Offer to run a competitive report on one of their clients' competitors free as a sample.

### Follow-up sequences
- **Cold email:** Day 0 (initial) → Day 3 (bump: "did this reach you?") → Day 7 (new angle/value, e.g. a free teardown) → stop.
- **After a free setup:** follow up once their first real alert/insight lands — that's the "aha." "See that price drop we caught? Here's the play for it."
- **Always** end sequences gracefully; no guilt-trips. Track everything in §10.

---

## 10. Customer Intelligence Log (fill-in template)

> Log every meaningful customer/prospect signal here. This is the raw material for §11's weekly roadmap loop. Copy this block into a shared sheet/Notion; one row per item.

### Objections heard
| Date | Who / segment | Objection (verbatim) | How I responded | Did it work? |
|---|---|---|---|---|
| 2026-06-29 | DTC apparel | "I can just check their site myself" | Showed the 5-stores-daily math + overnight gap | Booked demo |

### Feature requests
| Date | Who / segment | Request | Why they want it | Urgency (deal-blocker?) |
|---|---|---|---|---|
| | | | | |

### Confusing areas (product or messaging)
| Date | Where they got confused | What they expected vs. saw | My read on the fix |
|---|---|---|---|
| | | | |

### Pricing concerns
| Date | Who / segment | Concern | Plan they were eyeing | Outcome |
|---|---|---|---|---|
| | | | | |

### Messaging that worked (winners to reuse)
| Date | Channel | Exact hook/line | Result (reply/booked/closed) |
|---|---|---|---|
| | | | |

### Raw customer feedback / quotes
| Date | Who (and OK to quote? Y/N) | Quote | Theme |
|---|---|---|---|
| | | | |

---

## 11. Development Feedback Loop (weekly ritual)

> Goal: stop building on assumptions. Marketing insight from real conversations should directly shape the roadmap. This is the mechanism.

### The weekly cadence
1. **Throughout the week:** Jaiden logs everything in §10 as it happens (don't trust memory).
2. **Friday, 30 minutes (Jaiden → Devon):** Jaiden submits the **Weekly Insight Digest** (template below) — not raw notes, but the *patterns*.
3. **Devon triages** each item into one of four buckets and assigns a disposition: **Now / Next / Later / Won't-do (with reason).**
4. **Loop closes:** Devon reports back what shipped or changed as a result, so Jaiden can tell customers "you asked, we built it" — a powerful outreach/retention move.

### Tagging scheme (every logged item gets one)
- 🐞 **Bug / broken** — something doesn't work. (Fast lane.)
- 🧱 **Friction** — confusing UX or messaging causing drop-off.
- ✨ **Feature ask** — net-new capability requested.
- 🏆 **Messaging win** — a hook/line/angle that converted (feed into copy + ads).

### Weekly Insight Digest (copy-paste template)
```
STORESCOUT — WEEKLY INSIGHT DIGEST
Week of: ____________   From: Jaiden

1. TOP 3 PATTERNS THIS WEEK
   - Pattern: ______ | Tag: 🐞/🧱/✨/🏆 | Evidence (how many heard it): __
   - Pattern: ______ | Tag: __ | Evidence: __
   - Pattern: ______ | Tag: __ | Evidence: __

2. DEAL-BLOCKERS (anything that lost or stalled a sale)
   - ______

3. TOP FEATURE ASK (the one most likely to unlock deals)
   - Request: ______ | Asked by: __ segment(s) | Why: ______

4. MESSAGING WINS (reuse these)
   - Hook: "______" | Channel: __ | Result: __

5. CONFUSION / FRICTION
   - ______

6. NUMBERS
   - Conversations: __ | Free signups influenced: __ | Demos: __ | Closed: __
```

### Devon's triage response (closes the loop)
```
TRIAGE — Week of ____________
- [item] → Now / Next / Later / Won't-do (reason)
- Shipping this week as a result: ______
- Tell customers: "______"
```

### Why this matters
Most early SaaS dies building features nobody asked for. This loop guarantees the roadmap is pulled by real demand from real conversations — and gives Jaiden a steady stream of "we just shipped the thing you asked for" moments to re-engage prospects and customers.

---

*This document is the single source of truth for representing StoreScout. If reality and this doc disagree, flag it to Devon and we'll fix the doc — never ship a claim the product can't back up.*
