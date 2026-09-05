> Repository copy: private billing/account/support transcript redacted. The full feature audit, product analysis, public prospect research and measured resume are retained. Read the latest measured section and real-world priorities before historical blocked-status passages.

> **Measured resume update — 5 September 2026:** Supabase read/query access now works; the index census and 25-business real-data replay are completed. Earlier blocked-access statements below are historical. Discovery remains **Weak**. Commit `ff555bb` and the original reference panel are preserved. No application or production records/configuration were changed.

# StoreScout: state of the product and first-customer plan

Prepared September 5, 2026. Existing repository: `Devonwaldrop01/StoreScout`; inspected baseline `e66e3f05417cea5d57f27800c755c2353ca2b791`. Changes are local on `codex/launch-readiness-2026-09-05`. No production configuration, database, billing account, or public deployment has been changed. No prospect has been contacted.

## State of the product

**StoreScout is a substantial existing application, but it is not ready to accept paying customers.** Its public site returns HTTP 503 with “Service Suspended.” The prior authenticated inspection identified a billing restriction; private account details are omitted here. All three backend services are billing-suspended. The application also has independent reliability and security blockers, so restoring hosting alone would not make it launch-ready.

The strongest current product is a known-competitor Shopify catalog monitor: enter a storefront, collect public catalog data, inspect pricing/availability and later changes, and receive summaries or alerts. Broader discovery, winning-product, campaign, integration and agency features considerably exceed what has been validated.

What works locally: backend and frontend suites, TypeScript, production compilation, and one real ten-product Shopify fetch through StoreScout's own fetch/normalize/analyze pipeline. What remains unverified: deployed authentication, subscription lifecycle, database grants, queue scheduling, email, authenticated end-to-end flows, mobile/desktop rendered UI, and authenticated dependency health. Historical production resource usage has now been inspected; see section 3.

I repaired several confirmed defects without rebuilding the application. Important remaining risks include server-side requests to unsafe destinations, permissive database access in the tracked schema, billing reconciliation, quota races, diff-job ordering, and unsupported interpretations of public data. Settling the confirmed hosting arrears addresses the billing suspension, but separate routing, application and dependency problems remain.

The market is competitive at low prices. The initial audience to test is **a small Shopify CRO or merchandising consultancy doing recurring competitor reviews for clients**. This is a hypothesis supported by published service offerings, not a verified paying ICP. Generic dropshipping “winning products” positioning is a weaker fit for the data StoreScout can substantiate.

## 1. System inventory

The review covered all 298 tracked-file paths, architecture and function inventories, configuration, migrations, tests, key frontend routes, and the critical authentication/billing/scan/report paths. An earlier readiness review was used as a checklist and checked against current source. This is not a claim that every optional integration was exercised or every source line exhaustively audited.

| Area | Confirmed in source | Practical implication |
| --- | --- | --- |
| Primary workflow | Supabase signup/login → onboarding → add competitor → queued scan → dashboard/reveal → later scans/alerts → Stripe upgrade | First successful evidence review, then repeat use, should drive activation |
| Frontend | Next.js 16.2.6 App Router, React 19.2.4, Tailwind 4, server API proxy | Preserve the existing frontend; improve clarity and broken paths |
| Backend | FastAPI, 22 versioned routers, additional legacy routes | Large existing scope; launch a narrow verified workflow |
| Storage | Supabase Postgres; profiles, competitors, snapshots, changes, summaries, reports and operational tables | Schema and RLS must be reconciled with the actual project |
| Authentication | Supabase SSR/browser sessions, JWT verification in API, hashed API keys, team access helper | Signup UI alone does not prove deployed auth works |
| Payments | Stripe subscriptions, Checkout, portal, subscription webhook; older one-time PDF payment route | Determine whether legacy purchases/customers still exist before removal |
| Collection | Shopify public JSON endpoints, pagination/caps; curl_cffi with HTTP fallback; supplemental collections/pages/blogs | Coverage and failures must remain explicit |
| Browser automation | Playwright/Chromium is present for PDF rendering; the core catalog fetch is HTTP-based | A new paid browser service is not an established requirement |
| Jobs | Celery worker + Beat + Redis; worker calls protected API scan endpoint | API performs the heavy work; worker recycling alone cannot prevent API memory exhaustion |
| Limits | Free 1 competitor/168h, Pro 10/24h, Agency 50/12h; developer mapping existed inconsistently | Manual rescan, quota and entitlement enforcement need reconciliation |
| Public pricing | Pro $29/month, Agency $79/month; annual equivalents displayed at $23/$63 monthly | Actual Stripe price IDs, amounts, modes and annual totals remain unverified |
| Rate protection | Redis limits, domain delays, task retry/circuit patterns and AI call caps | Some Redis paths fail open; count-then-insert quotas are not atomic |
| Optional services | Anthropic, Resend, Shopify/advertising integrations, environment-gated GA4 and Meta | Keep first-customer workflow independent of unnecessary integrations |
| Observability | Structured error helpers, redaction, recent in-process error summaries and scan logs | In-memory error history disappears on restart; production log retention is unknown |
| Tests | Existing backend/frontend regression tests, expanded during this work | Useful local protection, not live integration certification |
| Scope/dead code | Legacy report flow; broad admin/discovery/lead engine; stale README; multiple migration locations | README corrected; do not delete legacy functionality without usage evidence |

### Current verification

| Check | Result |
| --- | --- |
| Baseline backend suite | 137 passed |
| Repaired backend suite | 160 passed on the final backend changes |
| Baseline frontend suite | 36 passed |
| Repaired frontend suite | 46 passed |
| TypeScript + Next.js production build | Passed; all listed routes compiled |
| Diff whitespace validation | Passed |
| Current tracked-file credential-pattern check | No detected matches for selected common live-key/private-key patterns; not a full historical secret audit |
| Public site `/`, `/auth/signup`, `/privacy` | 503, “Service Suspended” |
| Real Shopify sample | StoreScout fetched and analyzed ten Allbirds catalog entries; intentionally capped/partial |
| Rendered browser QA | Blocked: preview browser rejected local URL with `ERR_BLOCKED_BY_CLIENT`; no visual/mobile sign-off |
| Production auth, Stripe, email, DB migrations, queue | No active end-to-end tests executed. Historical logs and masked configuration inventories inspected read-only |

## 2. P0/P1 findings and changes

“Fixed locally” means source changes with local checks, not a deployed fix. P0 blocks customer use/payment. P1 seriously harms reliability, conversion or trust. P2 can wait.

| ID | Severity | Finding | State and next gate |
| --- | --- | --- | --- |
| INF-01 | P0 | API, worker and scheduler suspended for non-payment | Cause confirmed. Private account resolution requires owner approval. Automatic service resumption remains unconfirmed; see section 3 |
| BILL-01 | P0 | Subscription webhook swallowed processing errors and acknowledged failed entitlement writes | Fixed locally: return 503 on processing failure; exact signature/body forwarding repaired. Still verify real webhook destination/secret and end-to-end entitlement |
| DATA-01 | P1 | Independent variant minima could invent a markdown; malformed/nonfinite prices could crash or pollute analysis | Fixed locally: finite nonnegative values, same-variant markdown calculation, zero handling, timezone-safe missing-date sorting |
| DATA-02 | P1 | Failed later catalog pages could become successful partial baselines; a one-product probe could skip unrelated changes | Fixed locally: failed catalog requests fail the scan; removed unsafe probe; explicit coverage state |
| DATA-03 | P1 | Capped/legacy snapshots could produce false additions/removals and promotion-share changes | Fixed locally: whole-catalog changes require two explicit complete indexes; observed common-product changes remain possible |
| REPORT-01 | P1 | Public historical report could attach a newer brief | Fixed locally: new briefs carry snapshot provenance; report chooses only a matching brief. Legacy unbound briefs omitted |
| AUTH-01 | P1 | Internal endpoint had a predictable fallback secret | Fixed locally: empty/former default rejected, constant-time comparison, API blueprint secret entry. Provision matching API/worker secret before deployment |
| AUTH-02 | P1 | Callback `next` could lead outside the application | Fixed locally with local-path validation and regression tests |
| UI-01 | P1 | Frontend proxy omitted PATCH; successful DELETE 204 triggered JSON parse failure | Fixed locally; raw signed bodies preserved and unreachable backend gets a useful 503 |
| BILL-02 | P1 | Repeated upgrade path could create another subscription; invalid plan/billing inputs weakly constrained | Partially fixed: typed inputs, idempotent customer creation, existing Stripe subscriptions direct user to portal. Simultaneous unfinished checkouts remain a race |
| DB-01 | P1 | Tracked owner-update policies allow protected billing/limit fields; competitor writes may bypass API limits; email log lacks RLS | Migration 023 prepared, NOT applied. Inspect actual grants/schema; test with two users and service role in staging |
| SEC-01 | P1 | User-controlled outbound requests lack consistent destination/redirect/DNS protection | Open. Cover catalogs, probes, supplemental requests, favicons and webhook URLs with one reviewed outbound policy; test private/link-local/IPv6/redirect/rebinding cases |
| BILL-03 | P1 | No durable event ordering/reconciliation; zero-row updates can be acknowledged; terminal statuses can leave access | Open. Reconcile against current Stripe subscription state, persist successful event handling atomically, test duplicate/out-of-order/failed-payment/cancel cases |
| LIMIT-01 | P1 | Manual rescan cooldown differs from advertised cadence; concurrent creation/reactivation can bypass quotas | Open. Enforce current intended entitlements atomically; confirm whether manual scans intentionally differ before changing customer behavior |
| JOB-01 | P1 | Diff task marks idempotency before work and selects latest snapshots instead of strictly its supplied snapshot | Open. Bind work to requested snapshot and durable successful completion; verify retry does not lose or duplicate changes |
| OPS-01 | P1 | Heavy work runs in API; no demonstrated global memory/concurrency budget; multiple timeouts can overlap | Open. Profile representative catalogs, cap concurrent scans, verify timeout/retry ownership, test worker/API interruption |
| AUTH-03 | P1 | JWT audience verification disabled; JWKS cached indefinitely | Open. Verify actual Supabase issuer/signing setup; enforce audience/issuer and refresh rotating keys without locking out legitimate users |
| SCHEMA-01 | P1 | Multiple migration trees/duplicate numbering; referenced tables lack tracked creation definitions | Open. Reconcile `team_members`, `api_keys`, `action_items` and existing schema before claiming those features work |
| TRUST-01 | P1 | “Delete account” only signed the user out | UI corrected to an explicit support deletion request; no claim of self-service deletion. Mailbox and actual deletion/billing handling must be verified |
| TRUST-02 | P1 | Mock “live” output, unsupported scale/legal guarantees and instant/guaranteed timing claims | Main landing examples labeled; core claims narrowed. Broader “winning products,” threat and recommended-action interpretation still needs evidence boundaries |
| DATA-04 | P1 | Currency/market and merchandise-vs-service distinctions can make aggregate pricing misleading | Open. Live sample includes a returns-coverage service at $0.80 alongside footwear. Do not interpret that as footwear entry price or compare markets blindly |
| PRIV-01 | P1 | Legal pages exist, but operator identity/support delivery, consent, marketing opt-out and deletion fulfillment are unverified | Confirm operational facts and applicable obligations before launch; do not infer compliance from page presence |
| REPORT-02 | P1 | Reports are accessible by snapshot UUID; explicit sharing/revocation expectations not established | Confirm intended public data scope and user expectation; do not present private/client information in public output |
| UI-02 | P2 | Dense landing sections, varied typographic styles, animated mock output, broad feature navigation | Defer redesign; first finish reliable onboarding/result/error/mobile checks |

No new paid dependency was added. No production data was deleted. The security migration intentionally leaves browser SELECT ownership access while reserving protected writes to the trusted API, but its production safety depends on deployed grants and schema.

### What changed visually

The hero now describes catalog changes and evidence. Examples are explicitly illustrative, and unsupported scale/legal guarantees and several timing promises were removed. Pricing cadence is clearer. Partial-catalog notices appear on the dashboard and public report. FAQ controls gained accessible expanded-state metadata; landing focus styling and muted text contrast were improved. The false deletion action is now an honest request flow. These are source-level improvements; screen rendering, mobile behavior and full keyboard navigation remain unverified.

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

## 4. Initial market evidence: support and disconfirmation

This is an initial research pass, not exhaustive market validation. Sources were accessed September 5, 2026. Community posts establish specific experiences, not market size; vendor pages establish advertised offers, not independently verified performance.

| Evidence | What it supports | What it does not prove |
| --- | --- | --- |
| [Ecommerce discussion: tracking competitor prices](https://www.reddit.com/r/ecommerce/comments/1s8uxca/how_do_you_track_prices_from_competitors/) (March 2026) describes repetitive manual checking | A recognizable time-consuming task | A large market, a budget, or intent to buy StoreScout |
| [Shopify discussion: monitoring competitor promos](https://www.reddit.com/r/shopify/comments/1rfl95c/how_can_i_monitor_competitor_promos/) (February 2026) asks about bundles, BOGO, shipping and cart promotions | Merchants want broader promotional context | Public product JSON covers these needs; it often does not |
| [Shopify community: pricing across regions](https://community.shopify.com/t/how-do-you-research-competitor-pricing-across-different-regions/673744) discusses cross-market research | Market/currency consistency is a real requirement | StoreScout presently makes valid cross-market comparisons |
| [DTC Pages CRO audit](https://www.dtcpages.com/services/cro-audit) includes examining several competitors; [WIRO audits](https://www.wiro.agency/audits) include competitive context | Agencies already package competitor research in commercial client work | They do it weekly, lack adequate tooling, or will pay for this subset |
| [Shop Monitor](https://shop-monitor.com/) offers catalog monitoring with a free tier and low paid prices | Direct competition exists; basic monitoring is commoditized | Its data quality or retention is superior; those were not tested |
| [Store Leads](https://storeleads.app/) sells ecommerce discovery/enrichment at materially higher prices | Agency prospecting has an established paid tool category | StoreScout can replace that database or sell the same job |
| [Shopify's competitive-analysis guide/template](https://www.shopify.com/blog/competitive-analysis) | Manual research has a free, familiar alternative | All users need automation often enough to subscribe |

Excluded from demand validation: tool-builder launch posts, generic vendor assertions, and possible StoreScout-related self-promotion. No customer interview or StoreScout purchase has been observed. No willingness-to-pay claim in this report should be read as proven.

## 5. Competitors and substitutes

Monthly advertised prices unless stated otherwise; taxes, changing offers and exact quotas need checkout verification. Onboarding descriptions below are from public pages, not completed competitor accounts. Strengths and gaps are my assessment of the published scope.

| Product | Buyer/job and advertised functionality | Public price | Onboarding/strength | Gap or implication for StoreScout |
| --- | --- | --- | --- | --- |
| [Shop Monitor](https://shop-monitor.com/) | Small ecommerce teams; Shopify catalog/new product/price changes plus public Instagram | Free 3 stores; $9.90 for 10; $29.90 for 50 | Google sign-in, storefront URL, baseline then history; clear data boundaries | StoreScout cannot credibly win on basic price/store count alone. Agency-ready evidence must prove useful |
| [Beaconmon](https://beaconmon.com/pricing) | Competitor pages/catalog context, digests, own-store uptime/content monitoring | Free 1 competitor monitor; $29 Starter, $79 Growth, $199 Scale | Guided URL setup; bundled monitoring and briefs | Very close narrative competition. Quota units are ambiguous: pricing FAQ says each URL is a competitor monitor. Do not equate counts directly to StoreScout domains |
| [Koala Inspector](https://koala-apps.io/pricing/) | Store/product/theme/app inspection, tracking and broader research | Free 15 tokens/month; $22 Premium/220 tokens | Free inspection lowers friction; broad extension-style research | Tracking costs 15 tokens/shop/month despite an up-to-50-shop limit. StoreScout can test predictable task-focused value, not claim broader intelligence |
| [Prisync](https://prisync.com/) | Retail price/stock monitoring and dynamic pricing across sales channels | Advertises plans starting $99/month | 14-day no-card trial and onboarding assistance; pricing operations depth | StoreScout is not a repricer or cross-channel price-matching replacement |
| [Store Leads](https://storeleads.app/) | Ecommerce lead discovery, filters, enrichment, exports and CRM/API workflows | $75 UI Premium; $250 Pro with exports/API; $450 Elite; $950 Enterprise | Limited preview account; large research database | Strong reason not to pivot immediately into generic lead discovery. StoreScout's potential is analysis of already-known stores |
| [Minea](https://www.minea.com/pricing) | Dropshipping/product/ad/store research | Top pricing section: $49 Starter, $99 Premium, $199 Business; other site sections still show different Business pricing | Broad searchable research workflow | Mature expectation of ads, suppliers and product discovery. StoreScout's public catalog observations do not establish product demand |
| [Manual competitor worksheet](https://www.shopify.com/blog/competitive-analysis) | Merchant/agency manually visits sites and records evidence | Free template plus labor | Flexible, familiar, covers banners/cart context | StoreScout must save a repeatable step without hiding gaps; full manual audit replacement is not credible yet |

**Possible advantage to test:** a concise, dated evidence summary for a small set of known Shopify competitors, showing exactly what was observed and what changed, useful inside an agency's recurring client review. That is a product hypothesis, not a current defensible moat. Reliability and interpretability are required before the hypothesis can be tested fairly.

## 6. Candidate segments and first ICP

The comparison is qualitative judgment informed by the sources above and the actual code. Frequency, budget and retention remain hypotheses until interviews and use establish them.

| Segment | Pain/frequency/urgency hypothesis | Willingness to pay and reach | Competition/current fit | Retention hypothesis and priority |
| --- | --- | --- | --- | --- |
| Small Shopify CRO/merchandising consultancy | Repeated evidence collection across client reviews; urgency near deliverables | Agency owner may control a small tool budget; reachable through public services/directories | Existing paid research work; current catalog subset could save a step | Better if attached to retainers; **first test**, not confirmed winner |
| Operating Shopify brand with known rivals | Pricing/launch checks may recur; urgent during campaigns | Founder reachable but crowded inbox; monitoring budget unproved | Cheap direct alternatives; promo/cart gaps matter | Possible if a recurring decision changes; second test |
| New ecommerce founder | Broad uncertainty, occasional launch research | Easy to find, budget and urgency inconsistent | Free tools/manual work often adequate | One-off use/churn risk; lower priority |
| Dropshipper/product researcher | Frequent search for products likely to sell | Paid tools exist, but social communities are noisy | Minea/Koala offer broader discovery; StoreScout cannot verify winners/revenue | High churn and mismatch risk; deprioritize |
| TikTok Shop seller | Wants platform trends, creators and sales evidence | Tool spending possible; reachable in seller communities | Current Shopify feed is an indirect input, not the core answer | Weak current fit |
| Amazon seller | SKU matching, marketplace price/rank operations | Established tool budgets | StoreScout is not an Amazon monitor/repricer | Weak current fit |
| Ecommerce prospecting freelancer/agency | Recurring lists/enrichment for outreach | Paid alternatives show category monetization | Store Leads database is materially more complete; current index unvalidated | Could retain if lead quality proves out, but would imply a different product focus |
| Enterprise competitive-intelligence user | Regular broad intelligence and reporting | Higher budgets, harder procurement/reach | Coverage, security and collaboration expectations exceed verified product | Too slow for first 1–10 customers |

**Narrow initial ICP hypothesis:** a founder or hands-on CRO lead at a small consultancy serving Shopify DTC clients, personally preparing recurring competitor sections for reviews, tracking approximately 3–10 already-known Shopify storefronts in the same market/currency, and able to purchase a small monthly tool without procurement.

Without StoreScout they visit competitor catalogs, copy prices/availability, capture examples, and turn them into client notes. The proposed desired outcome is “prepare the evidence part of the next competitor review faster, with less manual rechecking.” We must ask about an actual recent task instead of assuming this workflow.

Reasons to pay: the sample fits an upcoming deliverable, the data is trustworthy and correctly scoped, later checks save repeated work, and the existing $29 plan covers their initial workload. Likely objections: free alternatives, another dashboard, inaccurate/outdated data, missing promotions, lack of client-ready output, insufficient recurrence, and wanting evidence on non-Shopify stores. Do not build white-labeling or change pricing until repeated objections make the decision concrete.

This may differ from StoreScout's broad merchant/winning-product framing. Test the narrower audience privately; no audience pivot or new agency promise has been published.

## 7. Twenty evidence-based prospect hypotheses

All are real businesses with public relevant offerings, researched September 5, 2026. These are **prospects to qualify, not confirmed buyers**. “Target role” is who to reach; no named decision-maker identity, company size or current budget is assumed. Public email addresses below were present in Shopify Partner listings. For other entries, use the site's existing contact route after approval; no guessed email addresses. A means stronger explicit workflow overlap; B is a reserve requiring more qualification. A/B are outreach priorities, unrelated to engineering P0/P1.

| Priority | Company / target role | Public contact channel | Observed fit and source | Pain hypothesis / personalization angle |
| --- | --- | --- | --- | --- |
| A1 | [DTC Pages](https://www.dtcpages.com/) / CRO lead | Contact link on company site | [CRO audit](https://www.dtcpages.com/services/cro-audit) explicitly examines several competitors | Ask whether collecting catalog/offer evidence across 3–5 competitors repeats between audits; offer a small evidence table |
| A2 | [Soda Web Media](https://www.sodawebmedia.com/) / strategy or CRO lead | `mihai@sodawebmedia.com` in [Partner profile](https://www.shopify.com/partners/directory/partner/cascadia-consulting) | Evaluation includes competitor analysis and CRO | Reference competitive evaluation; ask whether ongoing client reviews require fresh product/pricing evidence |
| A3 | [Black Comet](https://black-comet.io/) / founder or growth lead | Website contact route | [Service page](https://black-comet.io/) combines Shopify/CRO with competitor analysis | Ask where catalog changes enter its growth reviews; do not promise ad-performance intelligence |
| A4 | [WIRO](https://www.wiro.agency/) / audit or strategy lead | Get Started/contact route on [audits page](https://www.wiro.agency/audits) | Shopify home/lifestyle focus and competitive context in audits | Offer same-category catalog evidence for a home/lifestyle review; confirm that a small tool can enter its process |
| A5 | [CRO Gurus](https://crogurus.com/) / consultant or founder | `samuel@crogurus.com` in [Partner profile](https://www.shopify.com/partners/directory/partner/cro-guru) | Boutique Shopify CRO consultancy/audits | Ask if competitor collection is part of recurring reviews; this specific pain is not stated in profile |
| A6 | [Progryss](https://progryss.com/) / Shopify CRO lead | Website contact route | [Shopify CRO offering](https://progryss.com/services/shopify-cro/) includes competitor research | Ask which public competitor facts its audits repeatedly collect; test whether catalog evidence is one useful input |
| A7 | [TheLiftyfy](https://theliftyfy.com/) / CRO lead | Website contact route | [Shopify CRO page](https://theliftyfy.com/shopify-cro-agency/) includes competitor analysis | Reference the research step, not claimed client outcomes; offer a source-linked sample |
| A8 | [Elevatit](https://www.elevatit.com/) / CRO or strategy lead | Website contact route | [Published work](https://www.elevatit.com/) discusses competitor and CRO analysis | Ask if competitive findings get refreshed after initial work; recurrence determines fit |
| A9 | [Storegrowthx](https://www.storegrowthx.com/) / founder or growth lead | Website contact route | [Service process](https://www.storegrowthx.com/) includes competitor analysis alongside Shopify/CRO | Ask whether research is mostly initial builds or ongoing; only the latter supports retention |
| A10 | [Luscious Leopard](https://www.lusciousleopard.com/) / strategy lead | Website contact route | [Shopify agency offering](https://www.lusciousleopard.com/pages/shopify-agency-usa) includes competitor research in planning | Offer dated product/price evidence for the planning step; qualify ongoing work before pitching monitoring |
| B1 | [UnfoldCRO](https://unfoldcro.com/) / founder or CRO lead | `adarsh@unfoldcro.com` in [Partner profile](https://www.shopify.com/partners/directory/partner/adarsh45) | Shopify CRO/SEO services include competitive analysis | Determine whether analysis is keyword-focused or catalog-focused; do not assume price intelligence need |
| B2 | [Total Commerce](https://totalcommerce.partners/) / Data2Dev or strategy lead | `team@totalcommerce.partners` in [Partner profile](https://www.shopify.com/partners/directory/partner/tvp-nyc) | Site evaluation includes competitor analysis | Ask which evidence is labor-intensive; larger engagements may make a small tool less relevant |
| B3 | [SLFISH](https://www.slfish.marketing/) / growth strategist | Website contact route | [Offering](https://www.slfish.marketing/) connects Shopify CRO, offers and recurring creative/competitor research | Ask whether public catalog evidence informs offers; creative/ad research may be the real need |
| B4 | [SCAEL](https://www.scael.de/) / CRO lead | Website contact route | [Service framework](https://www.scael.de/) includes competitor/data analysis | Test same-market German Shopify workflow; currency and language requirements may disqualify current product |
| B5 | [XgenTech](https://xgentech.net/) / strategy lead | Website contact route | [Shopify/growth services](https://xgentech.net/) include competitor analysis | Ask whether catalog checks repeat within retainers; broader agency process may already have tools |
| B6 | [B2 Agency](https://www.b2agency.com/) / CRO lead | Website contact route | [CRO playbook](https://www.b2agency.com/ae/cro-playbook) includes competitive research | Ask about evidence collection; qualify market/currency and Shopify coverage first |
| B7 | [HavStrategy](https://www.havstrategy.com/) / D2C strategy lead | Website contact route | [Luxury D2C Shopify offering](https://www.havstrategy.com/shopify-agency-for-luxury-brands-d2c-growth-havstrategy/) includes competitor analysis | Offer pricing/catalog observations only; luxury positioning cannot be inferred from aggregate prices alone |
| B8 | [Cosmatify](https://www.cosmatify.com/) / Shopify CRO lead | `sales@cosmatify.com` in [Partner profile](https://www.shopify.com/partners/directory/partner/cosmatify) | Shopify CRO/audits and ongoing management, including apparel/beauty | Ask whether competitor research exists in ongoing delivery; no explicit competitor pain was found |
| B9 | [WebContrive](https://webcontrive.com/) / strategy or SEO lead | `info@webcontrive.com` in [Partner profile](https://www.shopify.com/partners/directory/partner/webcontrive) | Shopify services include keyword/competitor research | Likely SEO-led research and larger scope; qualify before investing in a demo |
| B10 | [ConversionWise](https://conversionwise.com/) / CRO operations lead | Company contact route | [FAQ](https://conversionwise.com/faq) describes ongoing conversion work and its own OptimoAI approach | Explicit incumbent/process objection: ask if a compact source feed fills any gap; do not pitch another generic audit |

Start with five A-priority conversations after approval and basic product safety gates. Do not bulk-send to all twenty. If contact verification shows an address is stale, or a recipient declines, stop and update the list. Re-check the public service page before sending so personalization stays accurate.

## 8. Prepared sales flow — drafts only

The separate **StoreScout-Public-Catalog-Sample.md** contains actual StoreScout output from a ten-product Allbirds fetch. It is a single partial observation, not a client analysis or monitoring history. It uncovered a returns-coverage item that would distort a naive footwear-entry-price claim. Use the sample to demonstrate evidence boundaries, then ask the prospect for a relevant competitor. Do not claim to have already analyzed their client's competitors.

### Initial message: DTC Pages

Subject: Competitor evidence for your CRO audits

Hi DTC Pages team — your CRO audit includes reviewing several competitors. I’m working on StoreScout, which collects public Shopify catalog data and records later changes. I ran a small sample that also caught a useful data-quality trap: a returns-coverage add-on mixed into footwear pricing. Would a short, source-linked example be useful for the research part of an audit?

Devon

### Initial message: Soda Web Media

Subject: A small input for competitor reviews

Hi — I saw that your Shopify evaluation includes competitor analysis. StoreScout collects public Shopify product and price observations, with the date and coverage stated. I’m testing whether this saves any of the manual collection behind client reviews. May I send a small example and ask what would make it useful in your process?

Devon

### Initial message: WIRO

Subject: Evidence for a home and lifestyle review

Hi WIRO team — I saw competitor analysis in your CX audit offering. I’m testing StoreScout as a way to collect the catalog/pricing evidence behind that work. Would it be useful to see a short example before deciding whether a home or lifestyle competitor is worth trying?

Devon

### Follow-up 1 — four business days after an approved initial send

One detail that may help: the example separates what the public feed actually shows from what it cannot tell us, such as cart offers or sales. Is collecting that evidence part of your process, or is another research step the real bottleneck?

### Follow-up 2 — another five business days later, then stop

I’ll leave this here. If collecting Shopify competitor data becomes a chore on a future review, I’d be happy to test one relevant store with you. No need to reply if it is not useful.

No automatic sends or follow-ups have been scheduled. Do not contact community members through scraped private channels. Do not solicit in communities that prohibit it.

### Response handling

| Prospect response | Useful next action |
| --- | --- |
| Interested | Ask for one public competitor URL, target market/currency and the next real deliverable; run and verify it before sharing |
| Already uses a tool | Ask what remains manual; compare the same task. If nothing is missing, accept poor fit |
| “Is the data accurate?” | Show source URLs, observation time, coverage and one manually checked example; explain missing cart/market/sales data |
| Needs revenue, winning products, TikTok or Amazon intelligence | State the current limits; record disqualification rather than promise a feature |
| Too expensive | Ask what task/cost it replaces. Do not invent a discount or change the published plan |
| Only needs a one-off audit | Record weak subscription fit; do not force a recurring pitch. A one-time offer would be a separate decision |
| Wants team/white-label/agency branding | Clarify which deliverable requires it; do not promise the unverified team features |
| Declines/no further contact | Stop; retain only the minimal suppression record needed to respect that request |

### Interested-prospect and demo flow

1. Ask about the last real competitor-research task: what triggered it, which stores, how long collection took, where the findings went, which tools were paid for, and when it happens again.
2. Get one public storefront and the relevant market. Run a safe supported scan; check product links and sampled values manually. Keep failures and partial coverage visible.
3. Show the evidence first in a short screen share or written example. Ask which item, if any, can be used in their deliverable.
4. Once the free-account path is verified, guide them through their own signup and first result. Do not provision accounts or process personal client data without appropriate authorization.
5. Establish a complete baseline and a later comparable check. A quiet interval with no changes is a valid result, not a reason to manufacture an insight.
6. Ask them to repeat the task during their next review. Log use of the result, not praise for the demo.
7. If useful, offer the existing Pro plan after checkout/entitlements/cancellation pass live configuration verification.

### Proposed first-sale offer

“Pro is $29 per month for up to 10 competitors on the existing daily scan schedule. I can help you set up the first research workflow. Would you use it for your next client review at that price?”

This is a proposed conversation using the existing advertised price, not a newly published offer or verified live Stripe amount. No annual commitment, lifetime deal, paid trial, special SLA, guaranteed savings or discount has been created. Checkout should follow only after the actual configured price and cancellation behavior are verified. Payment success is an active verified subscription/entitlement, not a success-page visit.

## 9. Marketing experiments

No ad spend or public post is authorized. Run one small experiment at a time after the launch gates, using real output and openly identifying the builder. Proposed targets are learning thresholds, not forecasts or results.

| Channel | Concrete experiment | What we want to learn | Measurement / decision |
| --- | --- | --- | --- |
| Direct outreach | Five individually approved A-priority messages offering a relevant evidence example | Does the research step recur and warrant a conversation? | Replies with real workflow detail, sample acceptance, repeat use and purchase; zero interest triggers copy/segment review before more sends |
| LinkedIn | A short source-to-output walkthrough using the returns-coverage example and its limitation | Do CRO practitioners value interpretable evidence more than another dashboard? | Qualified conversations and relevant sample requests, not impressions |
| X | A small dated catalog observation thread: raw evidence, a misleading interpretation, corrected interpretation | Which demonstrated research problem attracts actual operators? | Qualified replies and activated accounts with campaign attribution |
| TikTok | 30–45-second recording: a Shopify URL becomes a scoped result; point out one limitation | Can a concrete demonstration attract the right buyer rather than generic dropshipping curiosity? | Relevant requests and successful first results; deprioritize if audience mismatch dominates |
| Reddit | Answer a current relevant question with useful public evidence only where rules allow; disclose affiliation if mentioning StoreScout | Are recurring pain and existing alternatives being described in the user's own words? | Useful discussion/interview invitations allowed by rules; no unsolicited DM campaign. The researched Shopify thread includes rules against solicitation |
| Founder/ecommerce communities | A small documented build/validation lesson tied to the actual sample and request for workflow feedback, only in an appropriate channel | Can peers introduce practitioners with a repeated task? | Qualified introductions and completed research tasks, not supportive comments |

Do not publish competitor logos as endorsements, invent testimonials, reuse vendor claims as facts, or turn a partial single scan into a trend. First content should be a real demonstration, not an abstract list of benefits.

## 10. Minimal measurement

Existing frontend analytics wrap GA4 and Meta with environment gates. Existing calls include `signup_completed`, `competitor_added`, `first_scan_completed`, `first_scan_reveal_completed`, `upgrade_clicked`, and `subscription_started`. Actual provider configuration and receipt of events have not been verified. Signup and subscription frontend events are not sufficient authoritative counts. Existing database timestamps and scan records can provide most early operational counts; avoid adding another analytics platform now.

| Funnel question | Source / minimal event contract | Definition and caveat |
| --- | --- | --- |
| Acquisition source | Approved campaign URL UTM/source plus configured pageview | Count attributable visitors where tracking is enabled appropriately; do not put personal emails/client names in URLs |
| Signup | Auth/profile creation as authoritative count; browser `signup_completed` as diagnostic | Deduplicate by user; distinguish created from confirmed account |
| Activation | First successfully stored scan AND evidence/result viewed | Existing first-scan/reveal events cover onboarding; verify their firing and add general result-view coverage if absent before broad acquisition |
| Successful jobs | Snapshot rows and structured job logs, keyed by competitor/snapshot | Separate complete/partial results; require valid product evidence for first activation |
| Failed jobs | Failed scan state plus structured error category | Track cause, retry and recovery; successful later retry must not erase the historical failure count |
| Repeat use | A second deliberate result review on another day, plus associated account | Scheduled scans alone are not user retention. General result-view/session coverage is a remaining instrumentation task |
| Upgrade attempts | Existing `upgrade_clicked` plus backend checkout creation/error | Separate click, checkout URL creation and purchase |
| Paid | Verified Stripe active subscription plus successfully saved entitlements | Browser `subscription_started` or return URL alone does not establish payment |
| Retention | Cohort repeat review, later renewal and churn | First ten accounts can be reviewed manually; explain denominators and cohort maturity |

Use only stable non-secret IDs internally, event time, source, plan, result coverage and error category. Avoid scraped bodies, tokens, full prospect URLs and emails in third-party analytics. Review analytics/marketing configuration before turning on providers. No new third-party tracking has been enabled.

Initial daily operating ledger: invited prospects, replies, qualified recurring tasks, demonstrations delivered, created/confirmed accounts, first successful results, complete/partial/failed scans, repeat reviews, checkout attempts, paid subscriptions and cancellations. Record actual counts as they happen; all counts are currently unknown, not zero unless observed. Use the source application/database as evidence rather than a fictional dashboard.

## 11. Prioritized execution and release gates

### Next: resolve the remaining restoration decision

Read-only Render inspection is complete to the available access boundary. The previously recorded billing suspension requires the owner’s private account decision. Await the account-specific resumption answer in the existing Render support conversation, then seek approval before settlement or any production action. Finish blocked Vercel and authenticated external-provider checks when access permits. Preserve databases and queued work until understood; see section 3 for the exact sequence.

### Before any paying customer

1. Reconcile deployed schema and protect entitlements; verify two-account data separation and direct API/browser quota bypasses in staging.
2. Close unsafe outbound fetching, then test supported/unsupported/blocked/redirecting stores and partial/malformed catalogs. No anti-bot escalation or additional paid scraping service is assumed.
3. Finish subscription reconciliation and atomic quota enforcement. Exercise test-mode checkout, duplicate delivery, out-of-order events, delayed writes, cancellation, failed payment and portal return.
4. Fix snapshot-bound diff processing and concurrency/retry ownership; observe real API memory and job duration on representative catalogs.
5. Complete signup/confirmation/login/logout/reset and safe redirect checks against the real configured Supabase project or authorized staging equivalent.
6. Verify desktop/mobile/keyboard flows: landing → signup → first result → failure recovery → billing. Replace remaining unsupported result labels rather than decorate them.
7. Verify support, sender, deletion handling and public report expectations. A support link is not proof of a working support operation.
8. Deploy only after explicit approval, then smoke-test health and the protected internal path. Apply the reviewed migration only with a safe migration/rollback procedure and approval for production changes.

### First-customer experiment after technical gates

Start a two-week learning cycle after restoration, not a calendar promise made while the site is suspended. Qualify five A-priority prospects, deliver useful evidence, and ask for existing-price payment after repeat value is observed. Proposed decision gate: at least two prospects describe a recurring task, at least one uses a result in that task, and one accepts paid use. These are test criteria, not expected outcomes. If people only want ad intelligence, cart promotions, or one-off research, do not add features automatically; revisit the ICP with the evidence.

After the first sale: verify the customer can still use the product, review failures and costs, and watch for a second real use and renewal. Only then expand prospecting or consider feature requests.

## Decisions still requiring the owner

- **Support inquiry:** authorized and sent; escalated to Render’s human team. Await an answer without requesting or authorizing production changes.
- **Before restoration:** make the private account restoration decision and explicitly approve any possible automatic service resumption, or decide to defer. Any separate restart/resume, deployment, configuration change or migration still needs approval.
- **Before external action:** approve the concrete recipients/messages or public content. Current drafts are private.
- **Before claims/terms change materially:** confirm the operating entity, support ownership and intended plan/rescan behavior where they affect existing customers.

The work completed here creates a tested repair branch, a candid initial market position, a real limited product sample, a twenty-business research shortlist and a concrete first-sale process. It does not certify StoreScout as launch-ready or establish demand that has not yet been observed.

## Core Product Logic & Discovery Quality

**Additional source and local evaluation audit, September 5, 2026. This extends the completed launch audit; it does not replace it. Production remains untouched and suspended. Competitor discovery quality: WEAK.** The ranking repair improves a deliberately difficult local benchmark, but real index health and real end-to-end recommendation precision remain unverified. StoreScout is not yet ready for an unattended, paid intelligence promise.

### Exact index and discovery architecture

The implementation has four scheduled stages plus alternative candidate sources. Its database is an index of sampled merchant metadata, not a semantic search engine or a continually refreshed copy of every Shopify catalog.

| Stage | Actual behavior and storage | Quality implication |
| --- | --- | --- |
| Candidate supply | `discovery_sources.ShopAppSource` harvests Shop App storefront sitemap references through the API process; persisted cursor resumes collection. `discovery_queue` deduplicates source/reference pairs. The worker delegates resolution because the worker IP has encountered blocking. Only Shop App is registered as a pluggable feed. | Shop App inclusion is useful candidate provenance, not current catalog availability or a relevance label. Rate limits and source structure changes can stop supply. |
| Other supply | Admin seeds, AI niche generation, related-store generation, user discovery probes, and tracked-store scan writeback feed `shopify_store_index`. Rotating niche seeds and demand-triggered seeds supplement Shop App. | AI domains are hypotheses until independently probed. “Suggested/inserted” counters sometimes count attempted rows rather than confirmed new rows. |
| Resolution | `stage_resolution` sends up to 60 queued references to the API with a 180-second timeout; domains become `discovered`; failures accumulate attempts, with four attempts ending in failure. | Existing code can mark a queue reference resolved even when inserting its domain failed. Harvest cursor advancement after failed persistence can also lose work. These remain P1. |
| Verification | `index_store_pass` requests homepage, cart JSON, first 250 products, and collections. Original signals: Shopify CDN +25, theme +25, Shop Pay +15, myshopify reference +15, cart token +20, product JSON +55, generic 403 +35. Scores cap at 100; index acceptance floor defaults to 60. | Multiple correlated fingerprints are not a calibrated probability. Originally empty/malformed product payloads and blocked catalogs could qualify; local fixes require a nonempty product-shaped catalog to assert monitorability, remove the generic-403 confidence boost, and require monitorability for index acceptance. |
| Classification | `run_knowledge` uses AI classification from sampled products/collections/homepage, with weighted rules as fallback; Store DNA is a separate Haiku-generated structured profile with deterministic fallback. Taxonomy is one category/subcategory per domain. | A broad multi-category store is compressed into one label. AI confidence is self-reported; category confidence is not measured against independently labelled merchants. Tags exist but are omitted from the primary AI classification payload. |
| Stored evidence | Domain, brand/homepage text, sampled product count, up to 40 product titles, top product types/tags/vendors, collections, min/median/max/quartile prices, promo rate, timestamps, verification signals, category/evidence/confidence, stage/tier, target customer, `store_dna`, `dna_keywords`, signature and DNA timestamps. | Metadata is sampled. Product count and market stage are not reliable company scale; currency is not carried consistently into price positioning. Catalog titles are stronger matching evidence than a brand slogan. |
| Refresh | Scheduled verification drains `candidate`/`discovered`; knowledge drains verified rows with null `knowledge_at`. The 60-day reverify code lives in the legacy daily task, which is not the scheduled staged pipeline. | Index records can remain verified indefinitely. Local discovery now refuses cached verification older than 60 days, but this is an expiry guard, not a complete refresh policy. A successful local re-verification clears `knowledge_at` so classification can be regenerated. |
| Schedule | Harvest every four hours, resolution every 12 minutes, verification every 15 minutes, knowledge every 20 minutes, rotating candidates every six hours. Stage locks guard overlapping runs. | These are configured schedules, not proof the suspended workers are delivering them. Locks expiring and failure accounting still need real runtime validation. |

Canonicalization originally strips scheme/path and `www`; it does not establish redirect equivalence, normalize every hostname form, or identify the canonical Shopify shop across regional domains. Exact domain uniqueness prevents some duplicates. The old “same brand name on another domain means duplicate” rule could reject unrelated stores or legitimate regional storefronts; it has been removed locally. Canonical deduplication remains an explicit gap, rather than being replaced with another guess.

The original rules classifier adds weights 4 per product-type match, 2 per product-title or collection match, 1 per tag/homepage match. Confidence was `100 × (.45 × winner share + .35 × margin + .20 × min(1, winning weight/12))`. The single word **ceramic** produced **82/100** confidence despite only one homepage signal. Local regression work caps sparse evidence below the default 55 recommendation floor and uses word boundaries instead of arbitrary substring matches. This is a conservative guard, not a calibrated classifier.

Stage is inferred from product-count cutoffs 30/150/800, and price tier from absolute medians 25/75/200. Neither measures business maturity or category-relative positioning. The new discovery scorer no longer boosts inferred company stage; it uses a user's explicitly supplied price-range preference when present. Indexed price tiers remain weak evidence until currency and comparable product mix are understood.

### A discovery request traced through actual logic

Example evaluation input: **“handmade ceramic ashtrays,” adults collecting functional ceramics, budget price range**. The domains in this test are synthetic `.test` records, not real merchants.

1. `POST /api/v1/competitors/discover-ai` reads the user tier and discovery usage. Free allows one monthly search, but the existing read/increment occurs before success and is not atomic. The description is now bounded to 10–2,000 characters. This endpoint still uses the current account rather than the effective team owner, unlike competitor listing.
2. Business understanding originally used own-store index category if confidence ≥50; otherwise it classifies the description, accepting confidence ≥45. It concatenates user words, category, profile and own-store DNA into 24 normalized keywords. A query for a nonexistent `business_profiles.description` column silently discarded manual context. Local code reads actual profile fields and carries the supplied audience and price range. Description words now precede cached own-store DNA.
3. Retrieval originally took up to four positive graph neighbors first, then two queries of **24 rows each**, ordered by platform verification confidence: same category and six description terms matched against category/subcategory/description/brand name. Product titles/types and DNA were not searched. Thus a useful low-platform-score row might never reach ranking. Local retrieval takes bounded pools of 200 per query, adds stored DNA overlap and graph candidates to the pool, and ranks them together. This is still bounded lexical retrieval, not exhaustive matching across thousands of stores.
4. Original score started with verification confidence (0–100), added +60 for category retrieval, up to +20 category confidence, up to +45 DNA match, up to +24 inferred stage similarity, +12 equal inferred price tier; enterprise and category contradictions could be demoted. The DNA subscore used keyword overlap, category/subcategory, a modest tier bonus and optional audience overlap. The route did not supply audience. Equal-category vases could therefore outrank actual ashtray sellers, and graph-prefilled slots bypassed comparative ranking.
5. The local scorer instead computes **65 × query-token coverage + 15 × product-token precision**, with metadata-only matches discounted 20%; same category adds 5, strong cross-category contradictions subtract 15 unless product overlap is very high, audience overlap adds up to 10, and supplied price-tier agreement contributes a small adjustment. Verification is eligibility, not relevance. Output includes matched terms and whether observed product text supported the score. Scores are heuristics, not probabilities.
6. Eligible cached candidates must have verified status, confidence ≥60, an accessible-catalog signal and verification within 60 days; candidates without a product/metadata term match are withheld. Up to eight index matches can now fill the initial list. No invented filler is added to make the list look complete.
7. If configured and needed, AI still proposes additional domains in up to three batches. Fresh cached verification can avoid probes; otherwise the route probes stores and writes results back. Live AI candidates do not yet receive the same deep product matching as indexed rows. The final legacy category-contradiction guard still runs. These two ranking paths are not fully unified: a remaining P1.
8. Original code strengthened graph edges for every displayed result. Local code stops doing that; actual user feedback/tracking remains the relationship signal. Explicit negative edges are fetched separately from the positive limit and override positives. Rejected/blocked probes now say catalog access could not be verified, rather than asserting the domain is not Shopify.
9. A hermetic route test executes a real `discover_ai` call with fake database rows, no Anthropic key, and no write methods. It returns the linen-shirt index candidate with product evidence. The old early missing-key 500 no longer blocks an otherwise useful index result.

No geography, language-market compatibility, shipping-market overlap, sales overlap, calibrated brand positioning, embeddings, learned relevance model, or reliable SKU equivalence is currently part of ranking. Small spelling aliases help common wording, but semantic substitutes can still be missed. Long narrative descriptions dilute product intent, and the 24-token business context truncates information.

### Relevance evaluation and limitations

Baseline was captured before ranking changes at local commit `70af98e`. The evaluation uses eight **synthetic, hand-labelled stress cases**, five candidate stores each, including two intended direct substitutes and three weak/irrelevant choices. Weak choices deliberately have 100 platform confidence; direct substitutes have 70, which is above the real 60 eligibility floor. Prices/audiences are supplied test assumptions. This isolates a real ranking defect; it is not an estimate of live production precision.

| Business/test | Human criterion for a strong competitor | Old top-three labels | Local top-three labels | Remaining false positive in third slot / reason |
| --- | --- | --- | --- | --- |
| Handmade ashtrays | Same functional ceramic product, collectors, similar price position | weak/weak/irrelevant | direct/direct/weak | Same product for luxury hospitality remains adjacent rather than direct |
| Adult running footwear | Running shoes/trainer substitutes for adults at similar prices | no direct substitute | direct/direct/weak | Children's footwear shares nouns; audience mismatch is only partially represented |
| Sensitive dog food | Comparable dog diet product and positioning, not feeding accessories | no direct substitute | direct/direct/weak | Budget-position dog food remains a review candidate |
| Organic infant sleepwear | Infant sleepwear/sleepsuit, matching life stage and price | no direct substitute | direct/direct/weak | Luxury-priced substitute still shares exact product terms |
| Home espresso beans | Coffee beans for home brewers, not equipment/candy or wholesale-only sales | no direct substitute | direct/direct/weak | Wholesale restaurant beans need channel/audience review |
| Eczema skincare | Comparable fragrance-free moisturizer for sensitive skin | no direct substitute | direct/direct/weak | Luxury positioning is not a complete exclusion |
| Ergonomic office chairs | Adult home-office seating, not a broad homewares assortment | no direct substitute | direct/direct/weak | Classroom seating still has lexical overlap |
| Ultralight hiking tents | Backpacking shelter substitutes, not hiking clothing or family car-camping gear | no direct substitute | direct/direct/weak | Different audience/price remains a weak match |

Across these deliberately adversarial pools, old direct precision@3 is **0**, local precision@3 is **2/3**, and both intended direct substitutes move into the top two in all eight cases. Two direct substitutes per pool means 2/3 is the maximum possible precision@3. Do not market this as “67% discovery accuracy.” The third result remains weak in every case; the test exposes that the route still needs explicit direct/related labels or stronger fit confirmation.

Three **held-out wording challenges**, added after implementing the scorer, remain failures: unscented repair balm versus fragrance-free eczema moisturizer; hiking shelter versus ultralight backpacking tent; raw dog treats versus freeze-dried chicken reward bites. In each supplied substitution scenario, a weak candidate sharing the literal query words outranks the intended substitute. This is concrete evidence for the **Weak** rating and against pretending a small synonym map has solved semantic matching.

Additional regression cases cover misleading DNA contradicted by actual product titles, cross-category product overlap, absent metadata, stale/rejected/bot-blocked cached verification, and real route execution without AI. Files: `tests/evaluations/discovery_cases.py`, `discovery_baseline.json`, `discovery_after.json`, `discovery_wording_holdout.json`, and `tests/test_core_quality.py`.

**Real output check already available:** the actual Allbirds ten-entry sample contains a $0.80 returns-coverage service. Treating this as the footwear entry price or using it to infer brand positioning is wrong. This is independent public-data evidence that product-mix filtering matters, not just a synthetic failure. The sample was reused; the completed fetch was not repeated.

### Current index health

| Metric requested | Current evidence | Confidence / missing check |
| --- | --- | --- |
| Number indexed | Unknown | Suspended API; no authorized live database result available |
| Active, valid Shopify-store rate | Unknown | A historical batch accepting 93 of 100 domains is an acceptance rate, not independently checked validity |
| Duplicate rate | Unknown | Exact domain constraint exists; canonical aliases and regional domains not measured |
| Classification coverage | Unknown | Schema supports confidence/evidence; actual coverage counts are unavailable |
| Freshness / unreachable rate | Unknown | No regular refresh in the scheduled staged path; timestamp expiry is now enforced locally on cached discovery candidates |
| Category distribution / niche diversity | Unknown | Taxonomy/seed lists describe intended supply, not observed index distribution |
| Metadata depth | Bounded samples by design | First 250 catalog entries, limited titles/types/tags/collections; broad stores and weak metadata remain difficult |

Prepared **read-only** queries in `docs/quality-audit/index-health-readonly.sql` calculate counts, timestamp coverage, metadata presence, category distribution, likely duplicate candidates and a reproducible category-stratified review sample. They have **not** been run against production. After access is restored, independently inspect at least five stores per populated category, separating “reachable,” “Shopify signals,” “readable nonempty catalog,” and “correct classification.” Report confidence intervals only after a genuine sample exists.

**Root-cause verdict:** confirmed **B (classification), C (retrieval), D (ranking), and E (business understanding)** defects; **A (coverage)** is plausible but not measurable yet. Do not buy traffic or expand the index simply because output is thin. Fix and measure ranking and classification first, then target supply gaps established by labelled misses.

### Other core logic: functioning versus trustworthy

| System | Technically present | Product-quality finding / action |
| --- | --- | --- |
| Manual competitor onboarding | URL normalization, quota, duplicate check, catalog probe, row creation and enqueue | A probe failure is not proof “not Shopify”; exceptions can permit an add. Canonicalization and SSRF protection remain P0/P1. Quota and insert are not atomic. A duplicate-domain constraint does not enforce competitor-count limits. |
| Own business | Manual profile, own storefront, integration records | Own storefront is one competitor row. Changing its URL reuses the ID/history, risking comparisons between two different businesses. One global own-business profile also mixes agency client context. P1 before multi-client use. |
| Catalog ingestion | Curl/httpx public JSON pagination; optional Playwright/extended public page paths; ten-page/180-second cap; explicit coverage flags | Covers up to 2,500 entries, not all catalogs. Existing earlier fixes preserve failed baselines and block absence changes from incomplete scans. Repeated pages, malformed product identities, concurrent catalog movement during pagination and redirects still need detection. |
| Normalization | Product minimum/maximum prices, paired variant markdowns, availability, titles/tags/dates | Same-variant discount arithmetic was already repaired. New fix preserves **unknown** availability instead of turning missing variant flags into false stockouts. New snapshots retain product ID and minimum-price variant IDs. Full variant history is still absent; older snapshots lack those identities. |
| Change detection | ≥3% product-minimum price moves; warning at ≥10% drops; five large drops averaging ≥20% imply flash-sale severity; additions/removals, availability and ≥10 percentage-point catalog promo swings | Two complete snapshots are required for absence and catalog-share changes. Local guards now require shared minimum-price variant identity when either snapshot has the new field, and match known product IDs across handle renames. Older pairs without identity remain uncertain; non-minimum variants are not monitored. Price increases mostly info; no general title/tag/description change detector. Need stable product/variant comparison before claiming precise SKU repricing. |
| Monitoring | Free 168h, Pro 24h, Agency 12h defaults; scheduler queues due scans every 15m; retry count three with exponential delay; stuck scan recovery after five minutes | Schedule is approximate and workers are suspended. New fix makes HTTP-200 JSON `status:error` enter retry handling. Per-competitor scan lease, snapshot order and idempotent event insertion remain unresolved. Async change detection and Playbook dispatch can race. |
| Briefs / summaries | Snapshot brief, weekly summary, Pro strategist analysis, Brand Decode, Ask StoreScout and market interpretation | Prompts include claims discipline in several paths, but lack a universal facts validator. Some direct Anthropic calls bypass shared credit-breaker behavior. First-scan briefs cannot establish changes or threat to an unknown business. Brand Decode also multiplied promo percentage twice; repaired locally. |
| Playbook | Existing AI task, deterministic fallback, saved actions | Successful AI save hit undefined `message.usage` after transport moved to `res`; repaired and tested. New shared grounded candidate pipeline is described below. AI cannot replace observed facts or fabricate actions. |
| Watchlist | Pins handles and compares saved/current minimum prices | Absence from a sampled snapshot was called delisting. Local code now returns `not_observed`, and UI says “not observed”; it does not manufacture a removal. Freshness and variant identity still need improvement. |
| Notifications | Preferences, 30-minute batching, four-hour cooldown, daily/weekly/free summaries, Slack and custom webhook delivery | Batch keys are deleted before confirmed send; failed sends can lose work. Cooldown/dedup is not a transactional outbox. Quiet/daily/weekly paths and opted-in drips need end-to-end checks. Public source text is interpolated into email HTML without consistent escaping. P1 before customer notification promises. |
| Billing / entitlements | Stripe checkout/portal/signed webhook, plan gates and subscription data | Earlier launch fixes remain intact. Advertised and actual limits diverge: Free UI says no alerts/current state while free weekly emails/history exist; Agency UI says unlimited history but query caps at 365 points. Price/history do not prove comparable catalogs. Ordering/idempotency, cancellation, failed renewal, downgrade and actual live Stripe price checks remain launch gates. No prices changed. |

### Changes made and verification in this pass

Local changes concentrate on trust, not new product features: product-evidence ranking and deeper bounded retrieval; correct manual profile loading; index-only discovery without Anthropic; verification freshness/access checks; graph feedback discipline; conservative sparse classification; database-insert race handling that retries only a confirmed duplicate instead of stripping metadata on any error; inaccessible/malformed catalog guards; honest Playbook facts/actions and cache ownership; correct AI usage persistence; percentage units; unknown availability; minimum-price variant identity and product-handle rename guards; scan failure retry; watchlist absence; integration connection/capability accuracy; configured-secret requirement on Shopify privacy webhooks; and the settings password-reset link to the existing route.

The Shopify integration hub had two additional defects: it checked `ga4_property_id`/`gsc_site_url` although stored fields are `google_ga4_property_id`/`google_gsc_site_url`, and it labelled a public own-store URL an authenticated Shopify connection. Both are fixed locally. An empty account no longer gets a “full competitor intelligence” badge. The map is labelled source setup, not a quality score.

Local evaluations and regression tests are hermetic: no real Redis, Anthropic, Shopify account or database calls. Targeted source tests and TypeScript checks are recorded with the final local commit. No repeat full build or live payment test was performed, and no production version contains these changes yet.

### Prioritized remaining work

- **P0:** Hosting/front-end restoration and the previously identified SSRF, database access and billing release gates. Do not accept payments until account isolation and paid entitlements are verified.
- **P1:** Live index health and independent relevance labels; canonical identity; persistent refresh lifecycle; lossless queue promotion; unified AI/index ranking; query intent extraction; precise variant/product identity; stable snapshot/event ordering; dependable notification delivery; client-scoped business context; factual guards for every summary/comparison/benchmark surface. Run a real discovery review across the eight niche families after restoration, with at least 10 candidates per business and independent direct/related/irrelevant judgments.
- **P1:** Require two successful comparable scans before showcasing monitoring. Minimum acceptable discovery gate proposed: at least two independently confirmed direct competitors in the first three results for six of eight niche families, no unrelated category in first three, and explicit “insufficient evidence” for thin niches. This is a proposed internal acceptance criterion, not current performance.
- **P2:** Broader source supply, learned/semantic retrieval, geography and brand positioning, sophisticated action outcome scoring, additional integrations. Only pursue these after measuring whether simpler lexical evidence and targeted curation meet the gate.

## Complete Feature & Actionability Audit

**Inventory basis:** current source routes, frontend pages/components, integrations, jobs and legacy entry points—not README claims. A machine-readable companion, `docs/quality-audit/feature-route-inventory.json`, records **137 route-decorated handlers, 21 frontend pages and 32 decorated job functions** at this checkpoint. Counts include internal/admin/legacy functionality; they are not 137 customer features. The table groups related controls into actual user jobs. All rows were source-inspected; only the explicitly described local regression/evaluation paths were executed. Suspended production and unavailable credentials prevent live certification.

**Rating convention:** “implemented” means the code path exists, not that its remote dependencies or output are proven. “No integration” assumes the user can provide a business description and track a public Shopify competitor. P0/P1/P2 priorities apply to the recommended correction. A decision to merge, hide or deprecate below is a recommendation unless the changes column explicitly says implemented locally.

| Feature / purpose and intended user | Data and technical state | Usefulness, clarity and next action | Without / with integrations | Decision / priority / changes |
| --- | --- | --- | --- | --- |
| Landing, pricing, FAQ and product demonstration; prospective merchant/consultant | Next landing plus independent legacy FastAPI pages. Prior local copy cleanup exists; public deployment is suspended/misrouted. | Strongest ten-second promise: collect dated Shopify competitor catalog evidence. Avoid promising sales winners or automated growth. Show the actual sample and coverage. | No integration needed to understand the output; integrations should be secondary. | **Improve — P0/P1.** Restore the intended frontend; align all entry points and use the real sample. No new redesign in this pass. |
| Signup, login, logout and session recovery; all users | Supabase browser/server clients and protected app layout. Earlier callback/proxy fixes retained. | Basic onboarding prerequisite; not live-verified. Expired sessions need a clear re-login path. | Independent of commerce integrations. | **Improve — P0.** End-to-end account/auth configuration remains a release gate, not repeated here. |
| Forgot/reset password and account settings | Supabase reset/update flow. Settings pointed at nonexistent `/auth/update-password`. | Broken account recovery directly harms trust. | No integration dependency. | **Improve — P1.** Settings link now targets existing `/auth/reset-password`; actual email redirect configuration still needs verification. |
| Onboarding business description, goal, audience, price range and traits | `business_profiles` plus onboarding/reveal pages; source schema has `sells`, `notes`, not `description`. Optional fields and partial migration fallback. | Essential relevance input. Current profile may save only partially; user should see what was retained and confirm category/product focus. | Useful immediately; own catalog can improve it. No need to force Shopify OAuth. | **Improve — P1.** Fixed nonexistent-field reads in discovery and market interpretation. Profile editing/partial-save clarity and field bounds remain. |
| First-scan reveal and getting-started checklist | Competitor scan status, first snapshot, generated brief. | Should teach “sample collected → review comparable products → monitor again.” An AI brief should not block showing raw evidence. | Works without integrations; own-store context improves the comparison. | **Improve — P1.** Finite scan/AI state machinery exists; fully rendered first-success flow needs restoration verification. |
| Add/manage competitor, display name, active tracking and manual rescan | Public URL, duplicate/quota logic, `competitors`, Celery enqueue, status polling. | Clear job and action. Platform errors currently overgeneralize; delivery/monitorability must be distinct from relevance. | Core standalone value. Integrations don't make an unrelated competitor relevant. | **Keep core; Improve — P0/P1.** URL safety, canonicalization, quotas and scan leases remain. |
| Discover Competitors | Indexed metadata/graph, description, optional AI domain proposals, verification. | Useful only if results compete on products/audience. Local ranking improved; weak cases remain. User needs review/add/not-relevant actions and fit evidence. | Works with a manual profile; own catalog can enrich nouns. OAuth not required. | **Improve — P1.** Local scorer, freshness, context, retrieval and feedback fixes; overall **Weak** until live evaluation. |
| Legacy “discover similar” endpoint | Tags/vendors from tracked catalogs and curated fallback stores. | Overlaps primary discovery and can suggest large unrelated brands. Different logic makes results inconsistent. | Standalone but poorly personalized. Integrations do not repair the fallback. | **Merge — P1.** Route through the same measured relevance pipeline after compatibility review; not removed locally. |
| Dashboard portfolio and market pulse | Latest snapshots and competitor status, aggregate counters/trends. | Useful daily orientation; averages/counts need source dates and unknown/partial state. Multiple clients in one portfolio may not share a market. | Standalone; own catalog permits comparisons, not a universal business-health score. | **Improve — P1.** Preserve concise evidence dashboard; avoid implying market completeness. |
| Dashboard Market Signals / signal feed | Client-derived cross-competitor signals, recent events, optional `/market/signals/interpret`. | Helps prioritize review, but “N tracked stores” is not “the market.” Client-supplied signals are not independently re-derived by the server before AI interpretation. | Useful without integrations; manual profile adds context. | **Improve — P1.** Fixed profile field mismatch. Share grounded candidate/fact IDs across surfaces rather than trusting free-text interpretations. |
| Dashboard action items | Separate severity/recency rules and `action_templates`; top five, free top two. | Duplicates Playbook and can offer different advice for the same event. Stock changes and every price rise are not automatically opportunities. | Standalone templates; little actual own-business context. | **Merge — P1.** Reuse Playbook candidate IDs, evidence and risk fields; not yet migrated. |
| Competitor overview KPIs and positioning bars | Sample count, price distribution, promo share, created/updated timestamps; absolute heuristic labels. | Good descriptive facts if dated. “Premium,” “complex,” “threat,” or “slow” are interpretations, not measured strategy. | Public-only; integration does not validate competitor revenue or positioning. | **Improve — P1.** Show sample/currency/source; remove commercial certainty from heuristic labels. |
| Catalog / product search and filters | Normalized sampled catalog and derived lists. Product Intelligence returns a ranked subset, not necessarily every product. | Useful for finding evidence; scope should be visible so “not found” isn't “not sold.” Clear next step is product-page review/pin/export. | Standalone; own catalog enables tentative matches. | **Improve — P1.** Retain source links; expose coverage and distinguish full-catalog browsing from a top-product list. |
| Product Intelligence / “winning products” | 0–100 score: variants 30%, age 25%, no markdown 20%, availability 15%, image count 10%; rank-relative hero/strong/emerging caps. | These are merchandising proxies, not sales, demand, reorder history or proven winners. Current explanations often overread them. | Can identify listings worth inspection without integrations. Own sales would only validate the user's products, not competitors' sales. | **Major redesign of claims — P1.** Retain observed signals; describe “products to review,” not verified winners. No scoring model rewrite made. |
| Market Openings / gaps | Sparse price buckets, unavailable products, promo posture, launch timestamps, tag/collection flags. | Sparse supply is not proven demand. A missing collection in partial scraping is not proof a competitor lacks an offer. | Standalone hypothesis generator; user's product/stock/margin data could filter relevance. | **Merge / Improve — P1.** Feed qualified investigate/watch candidates into Playbook; do not promise validated opportunities. |
| Pricing distribution, quartiles, price buckets | Minimum variant prices across sampled products, no consistent currency contract. | Descriptive within a valid homogeneous sample. Service products, accessories and different currencies can distort comparisons. | Standalone; own catalog requires matching equivalent products before gap claims. | **Improve — P1.** Exclude or label ancillary entries and carry currency/coverage before interpreting positioning. |
| Price history and promotional trend charts | Historical catalog medians/promo rates; free seven points, Pro 90 days, Agency up to 365 query rows. | A changed median may be product-mix change, not repricing. Ascending capped query can omit newest Agency history. | Standalone after repeated scans; integrations don't cure inconsistent samples. | **Improve — P1.** Include coverage/currency and label catalog-level trend; reconcile “unlimited” copy without changing pricing. |
| Launch velocity / newest products / update activity | Created/published/updated dates, grace period, bulk-update heuristic. | Helps inspect additions; store migrations/backfills can look like launches. Publishing date and first observed date have different meanings. | Standalone; own calendar could later contextualize, but is not integrated. | **Improve — P1.** Separate “newly observed” from “created/published”; don't infer launch strategy from one scan. |
| Change feed, alerts list, read/unread controls | `change_events`, severity, read states and prior snapshot comparison. | Valuable when events are correct and deduplicated. No-change, missing-history and failed-scan states must differ. | Core standalone monitoring. Own product mapping prioritizes commercially relevant changes. | **Improve — P1.** Earlier coverage guard preserved; new unknown-availability and retry repairs. Minimum-price variant identity and known product-handle rename guards were added locally; full variant coverage and event idempotency remain. |
| Watchlist / pinned product price | User pins, latest handle lookup, saved minimum price. Free three pins, other plans 25. | Clear focus aid. Stale/missing product is not delisted; minimum-price comparisons are variant-sensitive. | Useful standalone; integration not necessary. | **Improve — P1.** Local `not_observed` state and UI wording replace false delisting. |
| Scout Brief and snapshot report cards | Snapshot facts sent to model after each scan; first-scan and later model choices. | Good quick explanation, but forced “threat/one move” can overstate one observation. Available source links and dates should lead. | Public-only; manual business context should condition “why it matters.” | **Improve — P1.** Reuse fact/action constraints; existing snapshot provenance repair retained. |
| Pro Analysis / strategist summary | Rich public snapshot, optional contextual text, AI-generated recommendations. | Often overlaps Brief and Playbook. Longer prose does not establish better intelligence; unsupported market/intent claims remain possible. | Public facts sufficient for cautious interpretation. Current provider context is aggregate, not product performance. | **Merge — P1.** Brief answers what happened; Playbook answers what to investigate. Preserve distinctive evidence, reduce duplicate strategy panels. |
| Brand Intel / Brand Decode | Collections, public page/technology flags, blog titles/count, stored signature; AI explanation with fallback UI. | Useful merchandising inventory; presence of a rewards/wholesale link is not proof of revenue or channel success. | Standalone. Own similar flags permit an observed comparison, not AOV/LTV conclusions. | **Improve — P1.** Local percentage fix. Prompt/explanations and cache signature coverage still need a claims pass. |
| “vs You” comparison | One own-store snapshot versus competitor aggregates; thresholds score winning/losing/matched. | Useful raw comparison, but higher breadth/launch count and lower promo share do not establish business advantage. Medians don't establish head-to-head pricing. | Requires own public storefront, not OAuth. Private product-level evidence would improve relevance. | **Major redesign of verdicts — P1.** Keep side-by-side observations; remove overall winner/loser verdicts until defensible objectives and equivalent samples exist. |
| Quick Wins / competitor action playbook | Snapshot rules and templates, paid gating of details. | Another advice surface; little own-business evidence, no reliable expected impact. | Standalone but generic; real stock/margin would improve safe selection. | **Merge — P1.** Use the same candidates as central Playbook; remaining local source still has legacy rules. |
| Ask StoreScout and suggested follow-ups | Bounded question/history, competitor snapshot/decode, optional context, rate-limited AI. | Helpful evidence interrogation; free-form answers can exceed known facts. A timeout should state unavailable rather than silently answer nothing. | Works public-only; extra context must be factual and fresh. | **Improve — P1.** Retain narrow question-answering; attach facts/source dates and make unavailable explicit. |
| Category benchmarks and market context | Up to 3,000 same-category index rows; means/percentiles; up to eight peers; count labelled saturation. | Convenience index sample, not a representative market benchmark. Mixed price currencies/categories and stale verification undermine results. | No integration needed; user's private data doesn't make index sample representative. | **Improve / hide conclusions — P1.** Label “indexed peers,” require sample quality and currency, remove saturation/market-average certainty. |
| Product sourcing/wholesale estimates and research links | Frontend product-research heuristics/links layered over public products and indexed context. | Search shortcuts can help, but estimated costs/margins are not supplier quotes or attainable profitability. Weak fit for CRO agency ICP. | Standalone only as explicitly labelled research leads; no supplier/cost integration. | **Remove/deprecate from main journey — P2.** Keep only if research customers demonstrate use; do not treat as verified economics. |
| Central Playbook recommendations | Former unstructured AI prompt plus snapshot templates; now shared structured candidate engine locally. | Must reduce noise and explain evidence, relevance, action, risk, confidence and missing data. Current safe actions emphasize review, not execution claims. | Useful without integrations; fresh own public catalog supplies possible wording matches. Connected private data is not yet safely mapped into this engine. | **Improve — P1.** Implemented grounded candidate generation, conservative priorities, stale-data guard, constrained AI tie-ordering and visible risk/data fields. |
| Save to Playbook, manual tasks, due dates, status, notes and outcomes | `playbook_items`; dedupe key, pending/done/dismissed, worked/too-early/not-relevant. | Useful action loop; saved tasks should retain evidence IDs/date, not just truncated strings. Creation does not independently validate arbitrary competitor association. | Fully useful without integrations. Future data can inform outcomes but “worked” is user feedback, not causal proof. | **Keep / Improve — P1.** Resolve ownership/dedup races and preserve provenance. |
| Local done steps, feedback and execution streak | Browser localStorage for generated cards, plus separate persisted saved-item state. | Device-specific completion can disagree with saved tasks. Stable baseline IDs can remain marked done after evidence changes. Streaks measure activity, not business value. | No integration dependency. | **Merge — P2.** One persisted action/outcome model; remove decorative gamification if unused. |
| Draft email/ad assets embedded in old Playbook cards | Renderer supports `draft_asset`; newer recommendation schema commonly sets it null. No campaign publishing path found here. | Ready-to-send wording needs business facts/claim review. Existing renderer is partly dormant, not an implemented Meta/email campaign integration. | Could draft with manual context, but actual campaign execution remains external. | **Simplify / hide dormant controls — P2.** No new asset generator or integration added. |
| Shareable report page and historical snapshot report | Public UUID snapshot endpoint with selected public data; snapshot-bound brief matching was previously fixed. | Useful consultant evidence handoff. Possession of URL grants access; share/revoke/expiry controls are limited. Report should expose date/coverage and avoid private data. | Public evidence works standalone; never automatically share private provider context. | **Improve — P1.** Explicit sharing expectations and snapshot-only claims remain required. |
| Product CSV export | Owned competitor snapshot/product fields; paid checks and generated CSV. | Useful input to an agency worksheet; must state sample scope and address spreadsheet formula injection from untrusted titles. | Standalone; no private-data promise. | **Keep / Improve — P1.** Verify escaping and coverage in the customer export flow before external use. |
| Legacy HTML/PDF report, preview and one-off purchase | FastAPI templates, `/preview`, `/generate`, `/buy`, `/success`, `/stripe/webhook`, stored files/email path. | Separate business model and entry point from subscriptions; duplicated checkout/report logic increases confusion and attack surface. | Public-store data only. | **Merge / deprecate — P1.** Choose canonical subscription product after review; do not delete paths or alter production routing without approval. |
| Subscription billing, upgrade modal and portal | Stripe checkout/portal, signed webhook, free/pro/agency limits, annual/monthly IDs. | Clear value and cancellation expectations matter. Frontend copy and backend entitlements currently disagree in places. | No commerce integration required to subscribe. | **Improve — P0.** No pricing changes; verify signed events, failure/downgrade ordering and actual provider configuration before sale. |
| Notification preferences and alert delivery | Price/product/promo toggles, daily/weekly/quiet/critical settings, UTC hour, Resend, cooldown/batch logic. | Notification count isn't value. Only meaningful, grounded actions should interrupt; failed delivery should be visible and retried safely. | Core alerts standalone. Integrations could improve priority, but are not required. | **Improve — P1.** Transactional delivery/dedup and preference parity still needed. |
| Slack and custom webhook notifications | Existing webhook URL fields, test-webhook route and notification send paths; catalog paradoxically calls Slack “coming soon.” | Useful agency workflow connector, with SSRF/secret-redaction/delivery validation needed. It is not a general Slack app. | Optional outbound channel; not additional business intelligence. | **Improve — P1.** Reconcile catalog and real webhook feature, protect destinations and verify failure handling. No test message sent. |
| Weekly/daily digests and free weekly teaser | Scheduler, subscription filter, aggregate changes, preferences. | Repetition with immediate alerts can be noisy; no-change versus scan-failure must be explicit. Saved digest_day isn't reflected by fixed Monday batch. | Public-only; integrates with email delivery, not email marketing analytics. | **Improve — P1.** Reconcile cadence/preferences and source constraints. |
| Onboarding/lifecycle drips D0/D1/D3/D7/D14 | Scheduled emails from first scan, sent-record checks and competitor snapshots/changes. | Potentially useful reminders, but can become irrelevant after deletion, success, quiet preference or stale data. | No connected commerce required. | **Simplify — P1.** Audit opt-out and current lifecycle eligibility before enabling for new prospects; no messages sent. |
| Own-store Shopify public tracking | A separate `is_my_store` competitor using the same scan pipeline. | Gives useful public product context without authentication. Public URL is not proof of ownership or an Admin API connection. | Level-1 enrichment; no integration required. | **Keep / Improve — P1.** Connection badge corrected; store identity/history lifecycle remains. |
| Shopify install/connect/disconnect | HMAC OAuth, Redis state, `shopify_connections`; Admin catalog/inventory and price-rule sample. | Partial integration. Requested scopes and reads do not import orders or sales metrics. Fixed API version needs compatibility review. | Optional inventory/discount context; no authenticated Shopify data is required for baseline reviews. | **Improve — P1.** Corrected capability claims and unknown inventory counting. Don't advertise product-sales personalization. |
| Shopify privacy webhooks | Customer request/redact acknowledgement, shop-redact sets uninstall timestamp. | Acknowledgement is not a complete retention/deletion implementation; uninstalled token/data lifecycle needs review. | Relevant only when Shopify app is offered. | **Improve — P0/P1 for app launch.** Missing secret now returns 503 rather than permitting unauthenticated handling; full privacy workflow remains. |
| Klaviyo connect/test/remove | Stored private key, up to 100 lists, list profile counts, up to 20 recent campaign records. | Does not read engagement, flows, revenue, repeat purchases or true customer segments. Summed list counts can double-count people. Draft dates were treated as sends. | Optional aggregate email context, not a prerequisite for Playbook. | **Improve — P1.** Local labels say list memberships; only explicit sent records with nonfuture send dates affect context. Advertised capabilities corrected. |
| Google OAuth, property selection, GA4 | Access/refresh tokens, selected property, top page paths by sessions over 30 days. | Implemented connection; no conversion funnel, bounce analysis, campaign ROAS or competitor-effect model. Token presence ≠ usable fresh data. | Optional page-traffic context. | **Improve — P1.** Hub field mapping and claims fixed; provider validation and structured facts remain. |
| Google Search Console | Selected property, top query sample, impressions and average position over 30 days. | Useful search context; not a complete keyword index or attributed competitor impact. | Optional; no integration needed for catalog evidence. | **Keep / Improve — P1.** Scope/freshness/coverage labels and provider verification. |
| Meta Ads / public competitor ad lookup | Hub Meta entry is coming soon. Separate optional global-token public Ad Library lookup can enrich competitor context. | **No merchant ad-account integration**, own campaigns, spend, performance, audiences or creative conversion data. | Current public-ad lookup, where accessible, is observational only. | **Do not add — P2.** Marketing-performance recommendations require new approved work and suitable permissions. |
| Remaining integration catalog entries | WooCommerce/BigCommerce; other email/ad providers; reviews, SMS, loyalty, support, subscriptions, shipping, finance and productivity entries are mostly coming-soon catalog metadata. | Visual breadth overstates current product depth. No imported metrics merely because an entry exists. | Unavailable; they cannot increase intelligence today. | **Hide/simplify — P2.** Show working sources first; new integrations require evidence and approval. |
| Intelligence Sources / understanding score / integration map | Connection flags and weighted score; history contributes five points, competitor count 20, own store 20, etc. | Measures setup, not business understanding, data validity or prediction accuracy. It can score stale/broken connections. | Manual context has real value despite low connector score. | **Improve — P1/P2.** Hub now says source setup and does not award empty accounts full competitor intelligence. Broader knowledge score still needs replacement with available-fact coverage. |
| Agency team invitation/acceptance/removal | Two additional seats, owner workspace mapping, invitation tokens and email. | Shared owner data exists; separate clients/workspaces and per-client context do not. Mixed effective/current-user routes lead to inconsistent behavior. | Standalone shared competitor data; client integration separation is not implemented. | **Improve — P1.** Limit initial pilot to one client/business context. Do not sell a mature multi-client intelligence platform. |
| API keys and API docs | Up to five hashed keys, one-time display, last-used timestamps, revocation and API-key bearer auth. | Useful for technical customers; permission scope is broad. Existing keys authenticate after downgrade because auth doesn't recheck paid tier. | Optional access method; not commerce data. | **Improve — P1.** Entitlement revalidation, quotas and least-privilege scope need verification. |
| Account deletion/support and legal pages | Manual support request link; privacy/terms pages, no immediate self-service data deletion pipeline. | A clear human support path is acceptable early; do not imply deletion also cancels billing or completes legal/provider obligations. | Independent of integrations; integrations increase data lifecycle obligations. | **Keep manual path / Improve — P1.** Define and test deletion/export/cancellation operating procedure before customers. |
| Feedback widget and opt-in testimonials | Rating/message persistence, explicit testimonial checkbox, public selected feedback endpoint, owner email. | Can capture actual product feedback; must never present sample text as customer endorsement. Public feedback requires moderation/consent clarity. | Standalone. | **Keep / Improve — P2.** Use feedback for fit and relevance labels; do not fabricate validation. |
| Analytics / acquisition and activation measurement | Existing analytics component and app logs; previous report identified funnel instrumentation needs. | Visits and error logs do not show whether a useful competitor result or action was reached. | Standalone telemetry; private integrations shouldn't be necessary for StoreScout's own funnel. | **Improve — P1.** Track source, signup, successful result, relevance accepted/rejected, saved action, repeat review and verified paid entitlement; avoid raw descriptions/private data. No new analytics platform added. |
| Admin store index/inspector/health/config | Admin-token routes, pipeline controls, coverage counts, run history, error summaries and scheduler status. | Useful operations tooling; not customer value or proof index quality. Some “GET” diagnostics invoke internal work rather than purely static reads. | Administrative only. | **Keep / Improve — P1.** Secure exposure; distinguish attempted/accepted/independently valid counts; use prepared read-only health queries. |
| Admin lead engine, outreach drafts and Reddit intent signals | Indexed public store attributes/technology/contact extraction, heuristic and AI fit scoring, AI draft generation, optional public Reddit collection. | Primarily merchant prospecting, not the validated agency shortlist. Source fit score is a hypothesis; AI-written personalization can invent pain. | Internal acquisition support, not a customer feature or outbound approval. | **Keep internal / Improve — P2.** Human qualification and approved drafts only. Do not use the engine to bulk-send. |
| Admin morning brief, telemetry and operational errors | Source/queue/error/worker/lead summaries. | Helps founder operate the service; errors hidden as empty data can still mislead. | Administrative only. | **Keep — P1 operations.** Add product-quality and activation counters, not decorative dashboards. |
| Legacy blog/SEO pages, sitemap/robots, favicon proxy, sample files and script entry points | Separate static templates, historical sample report and one-off scripts (`product_json.py`, CLI-style normalization helpers). | Some are legitimate acquisition/infrastructure utilities; others duplicate current paths or show obsolete product behavior. | Standalone support surfaces. | **Simplify / deprecate dead paths — P2**, with security-sensitive public execution paths P0/P1. No important data deleted. |

### User-state assessment

| User state | Useful now in principle | What must be explicit | Product decision |
| --- | --- | --- | --- |
| New account, no integrations and no competitors | Business brief and guided first competitor selection | No observed market evidence yet; don't display full intelligence or generic urgent advice | Help get one readable, relevant competitor result |
| No integrations, selected competitors | Dated catalog evidence, product review, later trustworthy changes, watchlist and saved review tasks | Their own margins, inventory, sales and audience response are unknown | This is the first-value product; avoid requiring OAuth |
| Own website/public Shopify storefront added | Possible own-product wording matches and public catalog comparison | Not ownership verification; no private inventory or sales | Ask the user to confirm equivalents; preserve separate store identity/history |
| Shopify Admin connected | Sampled inventory and active discount-rule context exists | No order/sales import; missing inventory values are unknown; no per-action product mapping yet | Next contained improvement is a structured product/variant inventory adapter, not an automatic repricer |
| Marketing/email connected | Limited list/campaign-date/page/query context | No Meta performance, conversion funnel, engagement segment or email revenue proof | Do not give spend/segment/ROAS recommendations from nonexistent facts |
| Solo merchant | Known-rival monitoring and a few high-signal review tasks | Avoid making every competitor event urgent | Start with 1–3 confirmed competitors and one repeat decision |
| Consultant | Source-linked evidence table and a manually reviewed client memo | Automated recommendations are hypotheses, not a complete CRO audit | Strongest initial pilot if evidence collection recurs |
| Small agency, multiple clients | Shared data/team seats and exports exist | One global profile/own store cannot represent multiple clients safely; currency/context mixing | One client per pilot; validate need before building client workspaces |

The coherent product journey should be **confirm relevant competitors → collect reliable dated observations → explain changes → decide investigate/watch/action → save a review task and outcome**. Dashboard signals, Quick Wins, Pro Analysis and Playbook should reference the same facts and candidate IDs. Notifications should select from that system, not invent a second interpretation. Integrations add specific available facts; connection count must not stand in for intelligence.

## Playbook Intelligence Architecture

### Before this pass

`generate_ai_playbook` assembled competitor snapshot strings, optional 90-day trend text, recent warning/critical changes, optional own-store aggregates, the knowledge context and public ad context. It asked Sonnet for **3–4 strategic recommendations, different categories and 3–4 execution channels each**. Forced diversity, inferred competitor intent and generic knowledge tiers encouraged plausible but ungrounded advice. No fact IDs or permitted candidate set constrained the output. Unknown competitor hostnames could be mapped to the first real competitor. AI save then referenced an undefined `message.usage`, so the successful model path could fail before persistence.

Fallback `snapshot_intelligence` used fixed thresholds, inferred slow launches from missing values and could turn a stored 50% promo share into 5,000%. It supplied little own-business context. Old cached recommendations could be reattached to another competitor after deletion. Integration presence could make the prompt sound well-informed even when only a key or coarse aggregate was available.

### Local architecture now implemented

`app/services/action_candidates.py` is a small shared module, not a new ML or search platform:

1. **Observed facts:** latest public snapshots, their dates/coverage and observed catalog entries; recent recorded change events; user-supplied business description; fresh own public catalog when available. No provider credentials, speculative margins or invented performance enter this module.
2. **Business context:** explicit `sells`/description and tentative own-product wording overlap. A matching title is labelled a possible match, not product equivalence. If context is absent, say so.
3. **Freshness and relevance filter:** snapshots older than eight days or with unparseable/future dates yield a refresh-evidence task, not current promotion advice. Eight days accommodates the existing weekly free scan interval. Events must be recent and belong to tracked competitors. Unknown percentages are not coerced to zero; values use an explicit 0–100 contract.
4. **Candidate actions:** compare a specific recorded change/product; review comparable offers when observed promo share is high; establish a baseline when there is no meaningful change; refresh stale evidence. Every candidate includes what happened, why it may matter, evidence, action, expected benefit, avoid/tradeoff, confidence and missing data. Absence of integrations still yields a source-based review job.
5. **Priority:** known event magnitude, recency and possible own-product wording matches affect review priority; watch baselines are lower priority. At most two event reviews per competitor and eight total candidates prevent a large event feed becoming a task flood. Cross-competitor behavior, real sales importance and per-product inventory/performance weighting are still proposed, not implemented.
6. **AI boundary:** the model can return existing candidate IDs to order actions of equal grounded priority. It cannot replace facts, create new actions, invent numbers, switch competitor identity or increase confidence. Invalid IDs are ignored; deterministic candidates remain usable. This deliberately trades expressive “strategy” prose for verifiable output. Rich AI explanation can return only after a claims validator and a real quality review exist.
7. **UI and persistence:** new recommendation fields expose Investigate/Watch, risk and missing data. Stored engine version and user identity prevent reuse of older unconstrained cache blobs; deleted competitor references are discarded. Token usage comes from the actual AI result. Data failures return an explicit unavailable message rather than a plausible empty Playbook.

This is a conservative intelligence floor, not the completed deep recommendation product. It does **not** yet infer safe commercial actions from connected Shopify stock or campaign performance. Current AI only assists tie ordering; whether that adds enough value to justify the call should be measured. The older knowledge-context pipeline remains available to other features and requires the same structured-facts treatment.

### Progression with progressively better data

| Level | Available/approved facts | What Playbook can credibly do | What it must not claim | Next work / status |
| --- | --- | --- | --- | --- |
| 1 — Public competitor intelligence | Manual brief, selected rivals, public product/price/availability sample, dated observations/events | Show specific observed change; identify a product to compare; suggest a conditional bundle/shipping review; explain risk; recommend watch/no reaction when evidence is thin | Their intent/sales, the user's margin, confirmed overlap, profitability, a required price cut | **Local grounded candidate engine implemented.** Real user quality evaluation and other-surface consolidation still pending |
| 2 — Business-aware intelligence | Level 1 plus current own catalog and explicitly mapped variants; authenticated inventory where verified; historical own sales only if a supported import exists | Filter to real equivalents; withhold promotions on confirmed low-stock items; prioritize user-designated important products; compare true same-currency variant prices | Existing Shopify integration does not import sales/orders; a missing quantity isn't zero; a broad catalog median isn't a matched price gap | **Partial today.** Public wording matches exist. Structured Shopify product/variant inventory facts and user-confirmed equivalence are the next bounded improvement; no new scopes added |
| 3 — Deep integrated intelligence | Fresh, permissioned marketing/email/commerce facts with time windows, coverage and product mapping | Conditional response informed by own conversion trend, inventory, campaign exposure, consented segments and goals; test before broad changes | No invented ROAS, engagement, segments or causality. Temporal correlation does not prove competitor impact | **Mostly new work.** Meta merchant-account connection, email engagement/segments and sales imports need evidence and approval; not built automatically |

A future fact record should include `source`, `entity/product/variant`, `observed_at`, `window`, `value`, `unit/currency`, `coverage`, and provenance. Distinguish **observation confidence**, **match confidence** and **expected-impact uncertainty**; one “verified” badge is insufficient. Priorities should become **Act now / Investigate / Watch / No action recommended** only when facts justify those states. With current data, urgent commercial execution is rarely justified; investigation is an honest useful action.

For the first customer, measure whether a reviewer can identify the evidence, confirm the affected product, explain the tradeoff and choose a next step in under two minutes. Ask what they would actually use in a client review. Do not reward the engine for generating more cards, more channels or a higher setup score.

## First-customer validation after the quality audit

**Sales gate remains closed for an unattended paid product.** Safe preparation can continue: the existing 20 prospects are re-ranked below using the already-researched public offerings and what the code actually supports. No company is called a confirmed buyer; current budget, team size, recurring pain and contact ownership are unverified. Public service/contact links from section 7 remain the evidence base and should be checked again immediately before an approved send.

The refined hypothesis is **a Shopify CRO or merchandising consultant who repeatedly prepares a competitor evidence section for one client's review, using 3–5 genuinely comparable public Shopify storefronts in the same currency/market**. Start with one client, not an agency-wide rollout. StoreScout's useful contribution is collecting and organizing dated product/price/availability evidence, exposing later reliable changes, and recording what deserves review. It does not replace UX research, analytics diagnosis, A/B testing, creative analysis or checkout research.

Disprove this hypothesis if their competitor work is predominantly screenshots/checkout/ads rather than catalogs; happens only once at project kickoff; depends on non-Shopify or blocked catalogs; requires client workspace separation immediately; or cannot identify a real recurring review where a source table would be used. A completed sample and compliments are not payment evidence.

### Re-ranked existing prospects

| Rank | Prospect / role to qualify | Why this position after inspecting actual capability | Main disqualifier or question |
| --- | --- | --- | --- |
| 1 | DTC Pages / CRO audit lead | Explicit multi-competitor audit step; strongest match for a compact evidence table | Does product/price evidence recur after the audit? |
| 2 | Soda Web Media / strategy/CRO lead | Competitor evaluation alongside CRO; understandable evidence-collection wedge | Is the existing step mostly UX rather than catalog research? |
| 3 | Progryss / Shopify CRO lead | Published competitor-research step maps directly to the proposed input | Would sourced catalog facts enter a real client deliverable? |
| 4 | WIRO / home-lifestyle audit lead | Category focus supports manual comparable-product selection | Mixed homeware categories and price positions; one-client pilot only |
| 5 | Black Comet / growth or founder lead | Competitor analysis and Shopify/CRO workflow | May primarily need acquisition/creative intelligence not available here |
| 6 | TheLiftyfy / CRO lead | Competitor analysis in Shopify CRO offering | Validate recurring collection task and accessible storefronts |
| 7 | Elevatit / CRO strategy lead | Competitive/CRO work creates a plausible review step | Recurrence and product evidence not confirmed |
| 8 | CRO Gurus / consultant lead | Consultancy-style audit workflow may be reachable and specific | Explicit competitor-collection pain has not been established |
| 9 | Storegrowthx / growth lead | Competitor research appears in process | Could be one-time build discovery, with low monitoring retention |
| 10 | Luscious Leopard / strategy lead | Competitor research in planning offers a concrete conversation anchor | Planning may not recur frequently enough to justify subscription |
| 11 | UnfoldCRO / founder/CRO lead | Competitive analysis exists, potentially accessible decision-maker role | SEO/keyword research may dominate |
| 12 | Total Commerce / strategy/Data2Dev lead | Competitive site evaluation fits a small evidence input | Existing larger-agency systems may make integration overhead unattractive |
| 13 | XgenTech / strategy lead | Broad Shopify/growth offering includes research | Needs clear recurring product-level job rather than general growth pitch |
| 14 | SCAEL / CRO lead | Explicit competitive/data framework | Language, geography and currency gaps increase current product risk |
| 15 | B2 Agency / CRO lead | Competitive research in CRO playbook | Market/currency and storefront fit need qualification first |
| 16 | SLFISH / growth strategist | Recurring offer/creative research suggests frequency | Current product cannot provide the creative/ad-performance intelligence likely central to the job |
| 17 | HavStrategy / luxury strategy lead | Competitive luxury D2C work offers a research use | Current price-tier/positioning heuristics particularly risky for luxury |
| 18 | Cosmatify / CRO lead | Shopify audit/management offering | No explicit competitor-collection pain established |
| 19 | ConversionWise / CRO operations | Recurring CRO work exists | Its own OptimoAI/process creates a strong incumbent and generic-audit objection |
| 20 | WebContrive / strategy/SEO lead | Broad Shopify and competitive research relevance | Likely SEO-oriented job; weakest catalog-specific differentiation |

### Top ten personalized opening drafts — not sent

Use the existing verified public site contact route from section 7; named recipients and email ownership must be resolved before sending. These drafts ask permission to discuss a specific job, not to install an integration or start a paid trial. The Allbirds sample is a demonstration of method, not a researched competitor of the agency or its clients.

1. **DTC Pages:** “I noticed your CRO audit includes reviewing several competitors. I’m testing a small way to collect dated Shopify product and price evidence for that step. Do you revisit that evidence after the audit, or is it mainly a one-time exercise? I have a short source-linked sample if useful.”
2. **Soda Web Media:** “Your Shopify evaluation includes competitor analysis. Which part is more repetitive for your team: reviewing the experience, or collecting product and offer facts? StoreScout currently helps with the catalog evidence. Could I show you a one-page sample and ask what would actually fit your review?”
3. **Progryss:** “I saw competitor research in your Shopify CRO process. I’ve put together a dated catalog evidence table that separates observed prices from assumptions about performance. Would that replace any collection step in a client review, or do you usually need different competitor information?”
4. **WIRO:** “Your home/lifestyle focus caught my attention because broad catalog averages can mix very different products. I’m testing a competitor review that makes those limits visible and asks the reviewer to confirm comparable items. Could I show you the format and ask how it would fit one homewares audit?”
5. **Black Comet:** “You combine Shopify CRO with competitor analysis. I’m checking whether dated product/price observations are useful in that work, or whether the real need is creative and acquisition research. StoreScout covers the catalog side today. Would you be open to a quick look at an evidence sample?”
6. **TheLiftyfy:** “Your Shopify CRO page includes competitor analysis. Is collecting the underlying product and price evidence something you repeat between client reviews? I’m testing a small source-linked report for that task and would value a candid ‘useful’ or ‘not the problem’ from someone doing the work.”
7. **Elevatit:** “I saw competitive and CRO analysis in your work. Do those findings get refreshed during ongoing reviews? I’m testing a dated Shopify catalog review with explicit evidence and limits, rather than a generic strategy summary. Could I send the one-page format for a quick reaction?”
8. **CRO Gurus:** “I’m researching how Shopify CRO consultants collect competitor evidence. Is product/pricing research part of your audits, or is your process focused elsewhere? I have a short public-catalog sample, but I’d rather first understand whether it solves a task you actually repeat.”
9. **Storegrowthx:** “Competitor analysis appears in your Shopify process. Is that mainly initial planning, or do you refresh it for ongoing clients? I’m testing a tool that keeps dated product/price evidence for those reviews. Happy to show a short sample if the recurring task exists.”
10. **Luscious Leopard:** “I noticed competitor research in your Shopify planning offering. Which facts do you collect by hand for that step? I’m testing a compact public-catalog evidence report and want to learn whether it would save a useful step—or miss the information your team really needs.”

**Follow-up 1, only after an approved initial send and about four business days:** “One useful limitation from the sample: a returns-coverage service looked like an extremely cheap product in the raw catalog. Separating that from merchandise changed the price read. Is checking that kind of source detail part of your review, or is your bottleneck elsewhere?” Do not imply a relevant prospect-specific discovery.

**Follow-up 2, about five business days later, then stop:** “I’ll leave this here. If competitor catalog research becomes a repeated task, I can show the short evidence format. If it’s mainly a one-off or your process already handles it, no need to reply.”

**Interested response:** ask for one nominated public competitor and one client decision, without requesting private credentials or client sales data. Confirm Shopify/readable catalog and equivalent product context. Prepare a small source-linked table, explicitly label scan scope/date/currency, and review it together. Ask them to identify one row/action they would actually use. Only after restoration and trustworthy repeat scans should they test their own account and repeat the task.

**Objection handling:** if they need ad performance, acknowledge it is not implemented; do not promise Meta integration. If they want CRO lift, explain the product supplies observations, not causal lift estimates. If the research is occasional, test a service-style evidence review before assuming subscription retention. If they already have a process, ask which evidence step remains manual; accept “none” as disconfirmation.

**First-sale offer remains the existing proposed Pro conversation in section 8: $29/month, up to ten competitors, daily configured scans, subject to verified live Stripe and cancellation behavior.** No new discount, paid pilot charge, pricing change or guarantee has been created. The smallest validation win is a named next review, actual use of one evidence table, repeat use, then a completed paid subscription after the safety gates—not ten favorable replies.

### Sample deliverable and next execution gate

`StoreScout-Public-Catalog-Sample.md` now includes a realistic review memo built from the **already-collected actual StoreScout Allbirds output**, plus the exact new grounded Playbook candidate generated from that saved sample. The added human-reviewed footwear subset excludes the returns-coverage service: nine listings, median minimum-variant price $135 USD. This is not a new live scan, full catalog estimate, prospect-specific report or observed price trend.

The report is usable for an information-gathering conversation about research quality. The software is **not yet certified for unsupervised paying customers**. Next consequential gate: restore the correct frontend/backend and obtain authorized live index/dependency access so real relevance, repeat scans, tenant isolation and billing can be verified. Private account settlement details are retained outside Git.

## Final local checkpoint for this audit pass

- **Local commit:** `ff555bb` — `Ground discovery and Playbook in observed product evidence`, on `codex/launch-readiness-2026-09-05`. Not pushed or deployed. Earlier launch repair `70af98e` is preserved.
- **Validation:** 68 focused new/affected backend checks passed; four further cache ownership/deletion/freshness cases passed after the final cache guard. Total **72 targeted checks**, including **34 new core-quality cases**. TypeScript `tsc --noEmit` passed after the frontend edits. Python source parsing and `git diff --check` passed. Installed PostgREST supports the new bounded DNA-overlap query method.
- **Relevance:** eight synthetic before/after stress cases improve from zero to two direct substitutes in the first three results; all three held-out wording cases still fail. Live index relevance, counts and independent valid-store rate are unknown. Overall rating remains **Weak**.
- **Scope:** no completed full audit/build/test suite was repeated. No credentials exposed, new integrations added, pricing changed, production actions performed, or external messages sent in this pass.
- **Next resume point:** inspect the saved report and commit, then resolve authorized restoration/access gates and run the prepared read-only index health review. Do not rerun the completed source inventory, local fixes, synthetic evaluations or targeted tests without a concrete regression reason. Real index sampling and a permitted two-scan customer workflow are the outstanding evidence, not more fixture tuning. Outreach drafts remain unsent.


## Real-world Discovery Quality — continuation after ff555bb

Checkpoint September 5, 2026. **Rating remains Weak; no real-index accuracy claim has been made.** Preserved `ff555bb2842a05f55dcc83403bfef80bc7eb17cf` and application code. No repeat of the completed source audit, local repairs, Playbook work, prospect research or tests.

Prepared an independent public-source reference panel of **25 real businesses across eight niche groups**, with two provisional reference competitors each. Twenty-four core cases plus one separately reported platform-uncertainty control. References precede any StoreScout output; they are analyst judgments, not customer endorsements or complete market ground truth. The companion **StoreScout-Discovery-Real-World-Benchmark.md** contains linked sources, per-business focus/caveats, measurement protocol and the exact resume point. Machine-readable sources/cases, null execution fields and SHA-256 baseline fingerprints are in `docs/quality-audit/real-world/`.

**Genuine blocker updated after connection:** Supabase was successfully connected and installation confirmed during this pass. However, no Supabase SQL/project tools are exposed in this active session after refreshing tool discovery. No production index query could be executed. Total stores, validity, canonical duplicates, classification/freshness distributions and all real discovery metrics therefore remain **unknown**, not zero. A fresh turn is needed to retry access to the connected query tools; do not reconnect or share credentials. No Render secret values were exposed and the production discovery endpoint was not called, because it writes usage/index state and may invoke paid AI or queues.

The new reference research finds useful lifecycle and interpretation controls: Drop's current homepage presents Corsair collaborations; Stewart's relevant pet-product business has a WordPress-based homepage; Quince spans many categories; Gossamer Gear's shelter names do not necessarily contain the product type. These observations are sourced in the companion. They do not describe StoreScout's actual index rows. Platform, catalog access, product relevance and audience/price equivalence must be labelled separately.

The three saved wording failures implicate literal candidate recall and product-head/accessory understanding, not just weights. A balm is not automatically an eczema moisturizer, and freeze-dried chicken is not automatically raw dog treats: prior fixture assumptions also need scrutiny. No new hard-coded aliases were added. Real-world contribution of index coverage versus classification/retrieval/ranking remains unmeasured.

**Implementation specifications prepared:** read-only snapshot/faithful replay; shared product concepts and observed-product retrieval; substitute/accessory ranking; lifecycle/canonical evidence; and the complete interpretation-to-selection experience. Each specifies files, root cause, desired behavior, constraints, regression risks, cases and acceptance criteria. Existing read-only health SQL is retained; an allowlisted paginated export query and schema census are prepared but unexecuted. No production migration or refresh was scheduled.

**Proposed Acceptable gate, not achieved:** padded P@5 ≥0.60; ≥80% of core cases with three useful top-five competitors; wrong-result rate ≤10%; unknown labels ≤5%; no multi-case niche consistently fails (at least two-thirds meet the three-useful gate). Publish P@10, known-reference and eligible-present recall, per-case/niche results and family-held-out comparisons. Index-only results cap at eight, so their P@10 maximum is 0.8. A passing unit test cannot satisfy this gate.

**Feature-audit coverage confirmed:** 58 feature groups contain the requested purpose/implementation/value/actions/integration experiences/flaws/fixes/remaining work/disposition dimensions. All 21 recorded frontend pages map to report groups; the existing inventory retains 137 route-decorated handlers and 32 jobs. This is coverage confirmation, not a repeated source audit or live certification.

**Next:** refresh connected Supabase query access in a fresh turn → schema/census/public-index export → independent stratified store checks → frozen ff555bb replay → blind top-result labels and per-stage misses → measured fix. Keep current source/reference artifacts; do not seed the index with reference competitors before measuring. Paid model runs and production changes require approval. Further outreach remains unsent.

Local documentation checkpoint: `11c1205`, direct child of preserved `ff555bb`. Application source hashes remain unchanged. Artifact integrity checks passed; no application tests were rerun. No push or deployment.


## Real-data measurement completed, 5 September 2026

The index contains 38,221 records: 36,088 discovered, 1,323 candidate, 426 verified, 323 rejected and 61 failed. At the frozen clock, 403 pass the default freshness/catalog gate, or 392 with category confidence ≥55. The 240-domain stratified public sample found readable catalogs for 156/177 discovered stores. A backlog-processing and evidence-lifecycle problem is now demonstrated; unknown/unprocessed is not equivalent to dead.

The untouched local `ff555bb` release candidate was replayed through the original endpoint against real PostgreSQL candidate captures, with production writes and paid calls prohibited. The primary 24-case result excludes the prepared Stewart control: P@5 28.3%, P@10 15.8%, known-reference recall 2/48, useful/returned 38/148 (25.7%), wrong/returned 57/148 (38.5%), unknown 3/148, and three-useful top-five coverage 7/24 (29.2%). Structured notes leave core P@5 and three-useful coverage unchanged. These are source-default local release-candidate measurements, not a live production or AI-assisted benchmark. Relevance is single-analyst, not independently blinded; geographic and price equivalence remain unestablished.

Of 50 original reference relationships including the control, 30 are absent, 16 unverified, two catalog-gated and two returned. Stronger candidates also disappear in retrieval/filtering: HyperX product fields are not searched; the JSONB DNA-overlap query fails; Babysprouts and Terra Moons lose meaningful product evidence. Shared modifiers produce wrong matches. No measured query hits the 200-candidate or first-eight-term cap. Classification and semantic freshness errors are real.

Measured priority order: (1) existing supply verification, renewal and catalog evidence parity; (2) product-based retrieval and substitute/meaning checks; (3) semantic freshness, classification and evidence-based canonical identity; (4) explicit product focus/identity and recoverable sparse-result flows. Numeric weight tuning, larger candidate caps and new explanation UI do not lead this plan.

Complete measurements and all 25 individual case results: `StoreScout-Real-Index-and-Discovery-Results.md`. Codex-ready root causes, components, desired behavior, regression risks, tests, cases and acceptance criteria: `StoreScout-Codex-Discovery-Priorities.md`. Reproducible snapshots, query captures, labels, traces and census data: `StoreScout-Discovery-Evidence.zip`. These measured deliverables supersede earlier null benchmark numbers. The original public catalog sample, prospect work, outreach drafts, source audit and existing tests were not repeated.

The next task is implementation in an isolated local branch, preserving the frozen comparison. No production processing, deployment, paid AI, outreach or configuration changes were authorized. The original panel is now inspected and cannot be described as an untouched blind holdout. Independent adjudication and the existing release gates remain necessary before declaring Acceptable.
