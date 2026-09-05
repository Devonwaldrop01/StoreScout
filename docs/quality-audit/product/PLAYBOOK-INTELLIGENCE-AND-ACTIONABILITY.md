# Playbook intelligence and actionability

> Extracted from the saved state report (source SHA256 `a6f1af42bfdde428d6e0bd3b1d10e7b6685ed316ccff904e48ba9e5336201bcc`), not a new audit. Original application checkpoint ff555bb. Current discovery measurements supersede historical access blockers.

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
