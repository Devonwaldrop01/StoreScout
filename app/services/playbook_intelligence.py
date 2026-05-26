"""
Playbook intelligence — v2.

Architecture: both functions take ALL competitors at once for cross-competitor synthesis.

Rules:
- Max ~8 total plays returned
- One play per signal type (synthesised across competitors, not one per competitor)
- Actions are 30-minute executable tasks with specific platforms, budgets, and success criteria
- Each play includes a `detail` dict: numbered steps, competitor breakdown, why, outcome
"""
from __future__ import annotations

from typing import Optional


# ── helpers ───────────────────────────────────────────────────────────────────

def _play(
    id: str,
    section: str,
    priority: int,
    competitor_id: str,
    hostname: str,
    headline: str,
    action: str,
    deadline: str,
    play_type: str,
    source: str,
    tab: str = "overview",
    detail: Optional[dict] = None,
) -> dict:
    p = {
        "id": id,
        "section": section,
        "priority": priority,
        "competitor_id": competitor_id,
        "hostname": hostname,
        "headline": headline,
        "action": action,
        "deadline": deadline,
        "type": play_type,
        "source": source,
        "tab": tab,
    }
    if detail:
        p["detail"] = detail
    return p


def _normalize_pct(value) -> float:
    """Normalise a percentage value to 0–1 fraction, handling both scales."""
    if value is None:
        return 0.0
    v = float(value)
    return v / 100.0 if v > 1.0 else v


def _find_price_gap(pricing: dict) -> Optional[dict]:
    """Find an uncontested price band. Returns {band} or None."""
    pb     = pricing.get("price_buckets") or {}
    buckets = pb.get("buckets") or {}
    order  = pb.get("bucket_order") or []

    if not buckets or not order or len(order) < 3:
        return None

    total = sum(buckets.get(b, 0) for b in order)
    if total < 8:
        return None

    shares = {b: buckets.get(b, 0) / total for b in order}

    for i in range(1, len(order) - 1):
        b = order[i]
        if shares.get(b, 0) < 0.04:
            before_pop = any(shares.get(order[j], 0) > 0.12 for j in range(i))
            after_pop  = any(shares.get(order[j], 0) > 0.12 for j in range(i + 1, len(order)))
            if before_pop and after_pop:
                return {"band": b}
    return None


# ── snapshot intelligence — takes ALL competitors at once ────────────────────

def snapshot_intelligence(competitors_data: list[dict]) -> list[dict]:
    """
    Analyse all competitors' snapshots together and return synthesised plays.
    competitors_data: list of {competitor_id, hostname, snap}
    """
    plays: list[dict] = []

    heavy_discounters: list[dict] = []
    slow_launchers:    list[dict] = []
    fast_launchers:    list[dict] = []
    price_gap_comps:   list[dict] = []
    premium_comps:     list[dict] = []

    for item in competitors_data:
        comp_id  = item["competitor_id"]
        hostname = item["hostname"]
        snap     = item["snap"]
        sd       = snap.get("snapshot_data") or {}

        discounts   = sd.get("discounts")    or {}
        pricing_d   = sd.get("pricing")      or {}
        positioning = sd.get("positioning")  or {}
        launch_d    = sd.get("launch_timeline") or {}

        raw_col = snap.get("promo_rate")
        promo_rate = float(raw_col) if raw_col is not None else _normalize_pct(discounts.get("discounted_pct"))

        new_30d    = int(snap.get("new_30d") or 0)
        median     = float(snap.get("median_price") or pricing_d.get("median") or 0)
        avg_disc   = _normalize_pct(discounts.get("avg_discount_pct")) * 100
        velocity_label = (positioning.get("launch_velocity") or {}).get("label", "")
        last_30d_rate  = float((launch_d.get("velocity") or {}).get("last_30d") or 0)

        entry = {
            "comp_id": comp_id,
            "hostname": hostname,
            "promo_pct": int(promo_rate * 100),
            "avg_disc": round(avg_disc, 1),
            "new_30d": new_30d,
            "median": median,
            "velocity_label": velocity_label,
        }

        if promo_rate >= 0.45:
            heavy_discounters.append(entry)

        effective_30d = new_30d or int(last_30d_rate)
        if effective_30d == 0 or velocity_label == "slow":
            slow_launchers.append(entry)
        elif effective_30d >= 8:
            entry["launch_count"] = effective_30d
            fast_launchers.append(entry)

        gap = _find_price_gap(pricing_d)
        if gap:
            price_gap_comps.append({**entry, "band": gap["band"]})

        if median >= 90:
            premium_comps.append(entry)

    # ── 1. Discount synthesis ─────────────────────────────────────────────────
    if len(heavy_discounters) >= 2:
        avg_promo = int(sum(d["promo_pct"] for d in heavy_discounters) / len(heavy_discounters))
        names_2   = [d["hostname"] for d in heavy_discounters[:2]]
        rest_n    = len(heavy_discounters) - 2
        names_str = f"{names_2[0]}, {names_2[1]}, and {rest_n} others" if rest_n > 0 else " and ".join(names_2)

        comp_rows = [
            {"hostname": d["hostname"],
             "metric": f"{d['promo_pct']}% on sale · avg {d['avg_disc']:.0f}% off"}
            for d in heavy_discounters
        ]
        brand_list = ", ".join(d["hostname"].split(".")[0].title() for d in heavy_discounters[:3])

        plays.append(_play(
            id="synth-discount-industry",
            section="right_now",
            priority=72,
            competitor_id=heavy_discounters[0]["comp_id"],
            hostname=f"{len(heavy_discounters)} competitors",
            headline=f"{len(heavy_discounters)} of your competitors are discounting right now — averaging {avg_promo}% of catalog on sale",
            action=(
                f"{names_str} are all running sales simultaneously. "
                f"When the whole market discounts, full-price is the differentiator. "
                f"Open Meta Ads Manager, duplicate your best ad set, narrow the audience to followers "
                f"of any of these brands, and change the headline to '[Their brand] is on sale. We never are.' "
                f"Run $10/day for 5 days and compare CTR to your control."
            ),
            deadline="this week",
            play_type="positioning",
            source="snapshot",
            tab="discounts",
            detail={
                "competitors": comp_rows,
                "steps": [
                    "Open Meta Ads Manager → go to Ad Sets",
                    f"Find your best-performing ad set (highest CTR or lowest CPA in the last 30 days)",
                    "Click Duplicate on that ad set",
                    f"In the new ad set, open Audience → add Interests or Pages for: {brand_list}",
                    "Go to the Ad level → edit the headline",
                    "Try: '[Brand] is on sale. We never are.' or 'Still full price. Still worth it.'",
                    "Set daily budget: $10/day",
                    "Run for 5 days, then compare CTR to your original ad set",
                    "If CTR is >15% higher — you have a repeatable campaign to run every time they discount",
                ],
                "why": (
                    f"When {len(heavy_discounters)} competitors discount simultaneously, their shared audience "
                    f"experiences deal fatigue. Full-price positioning stands out more in this environment, not less. "
                    f"The contrast is doing the work for you."
                ),
                "outcome": (
                    "A CTR lift of >15% confirms the full-price angle resonates with their audience. "
                    "If it works, save this ad set and reactivate it every time these brands run a sale."
                ),
            },
        ))
    elif len(heavy_discounters) == 1:
        d = heavy_discounters[0]
        plays.append(_play(
            id=f"snap-discount-{d['comp_id']}",
            section="right_now",
            priority=65,
            competitor_id=d["comp_id"],
            hostname=d["hostname"],
            headline=f"{d['hostname']} has {d['promo_pct']}% of their catalog on sale right now",
            action=(
                f"Open {d['hostname']}'s site and find their top 3 discounted products. "
                f"Check if you carry anything similar. If yes — hold your price and update your listing "
                f"to lead with a value angle that isn't price. If no — their shoppers are comparison searching. "
                f"Run a $10 Google Shopping campaign on their exact product names this week."
            ),
            deadline="this week",
            play_type="positioning",
            source="snapshot",
            tab="discounts",
            detail={
                "competitors": [{"hostname": d["hostname"], "metric": f"{d['promo_pct']}% on sale · avg {d['avg_disc']:.0f}% off"}],
                "steps": [
                    f"Go to {d['hostname']} and sort by 'On Sale' or 'Discount'",
                    "Find the top 3 discounted products by traffic or positioning (usually homepage or nav featured)",
                    "Check: do you carry anything similar in your catalog?",
                    "If YES: go to that product page in your store → add social proof (reviews, images, guarantee) to justify full price",
                    "If NO: open Google Ads → Shopping campaigns → add those exact product names as search terms",
                    "Budget: $10/day, 5-day test. Measure clicks and cost per click vs your other Shopping campaigns",
                ],
                "why": f"{d['hostname']} training their customers to wait for discounts creates a comparison-shopping window. Shoppers who search their product names are still deciding.",
                "outcome": "Even a small Google Shopping test captures in-market shoppers who searched their product and are now comparing alternatives.",
            },
        ))

    # ── 2. Slow launch → own new search ──────────────────────────────────────
    if slow_launchers:
        s = slow_launchers[0]
        others = len(slow_launchers) - 1
        others_note = f" ({others} other competitor{'s' if others > 1 else ''} also in a quiet phase)" if others else ""
        all_slow = [{"hostname": sl["hostname"], "metric": "0 products launched in 30 days"} for sl in slow_launchers]
        plays.append(_play(
            id=f"snap-slowlaunch-{s['comp_id']}",
            section="right_now",
            priority=60,
            competitor_id=s["comp_id"],
            hostname=s["hostname"],
            headline=f"{s['hostname']} hasn't launched a new product in 30+ days{others_note}",
            action=(
                f"Open Google and search their main product category — check the Shopping tab "
                f"and filter to 'Past 90 days'. If their new listings are absent, "
                f"there's organic search demand with no fresh competition. "
                f"A new listing with original photos and a solid title can rank in 2–4 weeks."
            ),
            deadline="this week",
            play_type="catalog",
            source="snapshot",
            tab="launches",
            detail={
                "competitors": all_slow,
                "steps": [
                    "Go to google.com → Shopping tab (or google.com/shopping)",
                    f"Search {s['hostname']}'s core product type — use a category term, not their brand name (e.g. 'resistance bands' not 'brand X bands')",
                    "Click Tools → Any time → Past 90 days",
                    f"Count how many Shopping results are from {s['hostname']} vs other brands",
                    "If their listings are thin, dated, or absent: you have a recency opening",
                    "Open your Shopify admin → Products → pick your most relevant product for this category",
                    "Rewrite the SEO title to lead with the category term you searched (Shopify admin → Edit website SEO)",
                    "Submit your updated product feed to Google Merchant Center — new listings with original content typically appear in Shopping results in 2–4 weeks",
                ],
                "why": (
                    f"New product launches from competitors create Google Shopping ranking pressure. "
                    f"When they stop launching, that pressure lifts. A fresh listing from you has "
                    f"less recency competition and can move up faster."
                ),
                "outcome": "A well-titled listing with original images can rank in Shopping results within 2–4 weeks with no ad spend needed.",
            },
        ))

    # ── 3. Fast launch → research their bets ─────────────────────────────────
    if fast_launchers:
        f = fast_launchers[0]
        others = len(fast_launchers) - 1
        others_note = f" (and {others} other{'s' if others > 1 else ''} pushing hard)" if others else ""
        all_fast = [{"hostname": fl["hostname"], "metric": f"{fl.get('launch_count', '?')} products launched this month"} for fl in fast_launchers]
        plays.append(_play(
            id=f"snap-fastlaunch-{f['comp_id']}",
            section="right_now",
            priority=65,
            competitor_id=f["comp_id"],
            hostname=f["hostname"],
            headline=f"{f['hostname']} launched {f.get('launch_count', 'many')} products this month{others_note}",
            action=(
                f"Go to {f['hostname']}/collections/new right now. "
                f"Find any products that are: full price, have 8+ variants, and are outside their usual range. "
                f"Those are their conviction bets. Research those categories for sourcing "
                f"before they build organic momentum over the next 4–6 weeks."
            ),
            deadline="right now",
            play_type="catalog",
            source="snapshot",
            tab="launches",
            detail={
                "competitors": all_fast,
                "steps": [
                    f"Go to {f['hostname']}/collections/new (if that 404s, try /collections/all?sort_by=created-descending)",
                    "Look at the last 10 products added",
                    "For each product, check: (1) Is it full price, not discounted? (2) How many variants? (3) Is it in their usual category or something new?",
                    "Make a note of any that are: full price + 8+ variants + different from their usual range",
                    "Those are their conviction bets — they invested in depth because they believe in them",
                    "Search that product category on Alibaba or your sourcing platform with the price band in mind",
                    "Set a reminder for 14 days: go back and check if those products are still at full price",
                    "Still full price in 14 days = validated demand. That's your sourcing window.",
                ],
                "why": (
                    "Established brands test products before investing in variants and photography. "
                    "When they launch with deep variants and full price, they have internal data that the product works. "
                    "Getting into that category early compounds over the next 4–6 weeks as their product gains reviews."
                ),
                "outcome": "If their product is still at full price in 2 weeks, you have category validation that no market research tool can give you — real sales data from a real competitor.",
            },
        ))

    # ── 4. Price band gap ─────────────────────────────────────────────────────
    for comp in price_gap_comps[:2]:
        plays.append(_play(
            id=f"snap-pricegap-{comp['comp_id']}",
            section="this_week",
            priority=62,
            competitor_id=comp["comp_id"],
            hostname=comp["hostname"],
            headline=f"{comp['hostname']} has almost nothing priced in the {comp['band']} range",
            action=(
                f"If you have a product that could sit in the {comp['band']} range, "
                f"move its price there and push it in your ads this week — you're in uncontested territory. "
                f"No product? Search Alibaba with {comp['band']} as your cost ceiling and add it to your sourcing list."
            ),
            deadline="this week",
            play_type="pricing",
            source="snapshot",
            tab="pricing",
            detail={
                "competitors": [{"hostname": comp["hostname"], "metric": f"near-zero products in {comp['band']} range"}],
                "steps": [
                    f"Check your current catalog: do you have any product priced in the {comp['band']} range?",
                    "If YES: push that product to the top of your store homepage and ads this week — you own that price point",
                    f"If NO: open Alibaba.com and search '[their product category]'",
                    f"Filter by the cost range that would allow you to retail in the {comp['band']} band (usually 3–5x cost)",
                    "Look for verified suppliers with MOQ you can handle (start with 50–100 units to test)",
                    "Order samples if unit cost fits your margin target",
                    "Add this as a sourcing priority — price band gaps close when competitors eventually fill them",
                ],
                "why": (
                    f"Their customers are already spending in the {comp['band']} range — just not with them. "
                    f"This is captured demand, not created demand. You're not convincing anyone to spend money; "
                    f"you're just showing up where they're already looking."
                ),
                "outcome": f"A product in the {comp['band']} range competes with zero resistance from {comp['hostname']} specifically. You're not fighting for their customers — they're looking for alternatives.",
            },
        ))

    # ── 5. Premium price → entry point ───────────────────────────────────────
    if premium_comps:
        p = premium_comps[0]
        entry_low  = max(29, int(p["median"] * 0.35))
        entry_high = int(p["median"] * 0.55)
        plays.append(_play(
            id=f"snap-premium-{p['comp_id']}",
            section="this_week",
            priority=50,
            competitor_id=p["comp_id"],
            hostname=p["hostname"],
            headline=f"{p['hostname']}'s median price is ${p['median']:.0f} — their entry-level is a gap you can own",
            action=(
                f"Go to {p['hostname']}'s site and look at their cheapest in-stock products. "
                f"A ${entry_low}–${entry_high} product from you in the same category "
                f"gets discovered by their audience before they're ready to spend ${p['median']:.0f}."
            ),
            deadline="this week",
            play_type="pricing",
            source="snapshot",
            tab="pricing",
            detail={
                "competitors": [{"hostname": p["hostname"], "metric": f"${p['median']:.0f} median price"}],
                "steps": [
                    f"Go to {p['hostname']}'s site and sort by 'Price: low to high'",
                    "Look at their cheapest in-stock, non-clearance products — that's their entry point",
                    f"Identify what category those entry-level products are in",
                    f"Check your catalog: do you have anything priced ${entry_low}–${entry_high} in that category?",
                    "If YES: push that product in your Google Shopping and Meta ads targeting their audience",
                    "If NO: add a ${entry_low}–${entry_high} product in that category to your sourcing pipeline",
                    "The goal is to be the first brand their audience discovers before they're ready to spend ${:.0f}".format(p["median"]),
                ],
                "why": (
                    f"Premium brands like {p['hostname']} (${p['median']:.0f} median) have an audience of people "
                    f"who can't afford them yet. Those shoppers are actively looking for accessible alternatives "
                    f"in the same category. A ${entry_low}–${entry_high} product from you captures that "
                    f"consideration set and builds brand familiarity before they graduate to higher price points."
                ),
                "outcome": f"An entry-level product at ${entry_low}–${entry_high} attracts {p['hostname']}'s aspirational audience. Once they buy from you, they're in your funnel — not theirs.",
            },
        ))

    return plays


# ── change event plays ────────────────────────────────────────────────────────

def change_event_play(change: dict, hostname: str, comp_id: str) -> Optional[dict]:
    ct    = change.get("change_type", "")
    sev   = change.get("severity", "info")
    delta = float(change.get("delta_pct") or 0)
    title = (change.get("product_title") or "")[:40]
    old_v = change.get("old_value") or {}
    new_v = change.get("new_value") or {}
    count = old_v.get("count") or new_v.get("count") or "several"

    if sev == "info" and ct not in ("discount_end", "availability_change"):
        return None

    from datetime import datetime, timezone, timedelta
    detected  = change.get("detected_at", "")
    hours_ago = 0.0
    if detected:
        try:
            dt = datetime.fromisoformat(detected.replace("Z", "+00:00"))
            hours_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        except Exception:
            pass

    deadline = "today" if hours_ago < 24 else ("within 48h" if hours_ago < 48 else "this week")
    base = dict(competitor_id=comp_id, hostname=hostname, source="change_event", tab="changes")

    if ct == "price_change" and delta <= -15 and sev == "critical":
        return _play(
            id=f"change-flash-{change['id']}", section="act_now", priority=95,
            headline=f"{hostname} flash sale — {abs(delta):.0f}% off",
            action=(
                f"Flash sales typically run 48–72h. Queue an email to your list in the next 6 hours. "
                f"Even 'our prices didn't change' captures their shoppers who are actively comparing. "
                f"If running a counter-offer, keep it time-limited to match their urgency."
            ),
            deadline="within 48h", play_type="change", **base, tab="pricing",
            detail={
                "steps": [
                    f"Go to {hostname} right now and confirm the sale is live",
                    "Note which categories and price points are discounted",
                    "Open your email tool and create a new campaign — target your full list",
                    "Subject line options: 'Still full price.' / 'No flash needed.' / 'Our prices haven't changed'",
                    "Body: 1-2 sentences, your product, in-stock, no games. CTA to your site.",
                    "Send within the next 6 hours — flash sale windows move fast",
                    "Optional: run a $15/day Meta ad to their audience with the same 'no flash needed' angle",
                ],
                "why": f"Their shoppers are in a buying mindset right now and actively comparing. The 48–72h flash sale window is the highest-intent moment for competitor audiences.",
                "outcome": "Email opens during competitor sale windows are typically 20–30% higher than normal. Even a 2% conversion on your list is meaningful.",
            },
        )

    if ct == "price_change" and delta >= 10:
        return _play(
            id=f"change-priceinc-{change['id']}", section="act_now", priority=85,
            headline=f"{hostname} raised prices {delta:.0f}% on {title or 'key products'}",
            action=(
                f"Their price-sensitive customers are comparison shopping right now. "
                f"Pull up Google Ads or Meta — search their brand and see if they're running ads. "
                f"'[Their product] just got more expensive. Ours didn't.' Even $20 this week captures active comparers."
            ),
            deadline="today", play_type="change", **base, tab="pricing",
            detail={
                "steps": [
                    f"Go to {hostname} and verify the price increase on {title or 'their products'}",
                    "Note the old vs new price — that delta is your headline",
                    "Open Google Ads → find or create a Search campaign",
                    f"Add keyword: '{hostname.split('.')[0]} {title or 'product'}' (exact match)",
                    "Ad headline: '[Their product] just went up. Ours is still $[your price].'",
                    "Budget: $15–20/day for 7 days",
                    "Also try Meta: duplicate your best ad set → narrow audience to their brand followers",
                    "Measure clicks and conversions for 7 days before deciding to scale",
                ],
                "why": f"Price increases create a 1–2 week window where their loyal customers reconsider. People who were loyal because of value are suddenly in the market.",
                "outcome": "Price comparison searches spike for 1–2 weeks after a competitor increase. A targeted campaign in this window captures high-intent shoppers at peak decision time.",
            },
        )

    if ct == "price_change" and delta < -5:
        return _play(
            id=f"change-pricedrop-{change['id']}", section="act_now", priority=78,
            headline=f"{hostname} dropped prices {abs(delta):.0f}% on {title or 'products'}",
            action=(
                f"Check if their discounted products overlap with yours. Go to their site and find the exact SKUs. "
                f"If you have similar products — don't match the price. Lead with value that isn't price: "
                f"better materials, warranty, reviews. Price wars on Shopify rarely win."
            ),
            deadline="today", play_type="change", **base, tab="pricing",
            detail={
                "steps": [
                    f"Go to {hostname} and find the exact products that dropped",
                    "Search those product names or categories in your own catalog",
                    "If you have similar products: do NOT lower your price to match",
                    "Instead: update your product page to lead with differentiation — materials, warranty, reviews, photos",
                    "Add a comparison table if you have one ('Us vs them')",
                    "If you don't have similar products: monitor for 2 weeks to see if the drop is permanent or a test",
                ],
                "why": "Matching a competitor's price cut signals to customers that yours was overpriced. Reinforcing your value proposition converts better than racing to the bottom.",
                "outcome": "Customers who choose you at full price after comparing are more loyal and have higher LTV than discount buyers.",
            },
        )

    if ct == "bulk_price_change":
        return _play(
            id=f"change-bulkprice-{change['id']}", section="act_now", priority=70,
            headline=f"{hostname} repriced {count} products",
            action=(
                f"Open their site and sort by Price: low to high. Scan the first two pages — what changed? "
                f"If they went up, you have room to move yours. If they went down across the board, they may be clearing a category."
            ),
            deadline="this week", play_type="change", **base, tab="pricing",
            detail={
                "steps": [
                    f"Go to {hostname} → sort by Price: low to high",
                    "Scan the first 2 pages — look for products that now sit at odd price points (signs of adjustment)",
                    "Did prices go up or down overall?",
                    "If UP: check if any overlap your catalog — you now have room to raise too without looking expensive",
                    "If DOWN across the board: they may be clearing out a category. Watch for what replaces it in 2–3 weeks",
                    "Take a screenshot for your records so you can compare at next scan",
                ],
                "why": "Bulk repricing is a strategic signal — it means they reviewed their entire pricing model, not just one product. Understanding the direction tells you where they're going.",
                "outcome": "Knowing their new pricing structure lets you position yours intentionally, not reactively.",
            },
        )

    if ct == "new_product":
        return _play(
            id=f"change-newprod-{change['id']}", section="act_now", priority=65,
            headline=f"{hostname} launched: {title}" if title else f"{hostname} launched a new product",
            action=(
                f"Go look at the listing now. Is it full price or discounted? How many variants? "
                f"If it overlaps your catalog — watch if it's still at full price in 2 weeks. "
                f"If yes, that's validated demand. If it goes on sale fast, they misjudged."
            ),
            deadline="this week", play_type="change", **base, tab="launches",
            detail={
                "steps": [
                    f"Go to {hostname} and find the new listing: {title or 'check their new arrivals'}",
                    "Note: current price, number of variants, product category",
                    "Is it in their usual product range or something new?",
                    "Does it overlap with anything in your catalog?",
                    "Set a 14-day reminder to check back on this product",
                    "At 14 days: still full price + still listed = real demand. Discounted or removed = misjudged.",
                    "If still full price at 14 days: research sourcing in that category",
                ],
                "why": "New product launches are experiments. You can't know if they worked from the launch alone — but 14 days of full-price listing is a reliable validation signal.",
                "outcome": "A 14-day full-price hold means their internal data supports the product. That's better market research than any survey.",
            },
        )

    if ct == "bulk_new_products":
        return _play(
            id=f"change-bulklaunch-{change['id']}", section="act_now", priority=68,
            headline=f"{hostname} added {count} new products",
            action=(
                f"Filter their site to newest. Pick the 3 that look most different from their usual range — those are their category bets. "
                f"Full price with deep variants = conviction. Set a 14-day reminder to check if they're still there."
            ),
            deadline="this week", play_type="change", **base, tab="launches",
            detail={
                "steps": [
                    f"Go to {hostname} → filter or sort by newest products",
                    "Look at the first 10 new additions",
                    "Flag any that are: (a) full price (b) 8+ variants (c) outside their usual category",
                    "Those are the ones they believe in — the others are tests",
                    "Research the category of your flagged products on Google Trends and Alibaba",
                    "Set a 14-day reminder: check which of these are still live and still full price",
                    "Still live + full price at 14 days = demand validated. That's your sourcing signal.",
                ],
                "why": f"When brands launch in bulk, most products are experiments. The ones with deep variants and full price are the bets. Identifying those early gives you a sourcing lead time advantage.",
                "outcome": "If you source into their validated category while they're still building reviews and organic rank, you enter with lower CPA than if you wait.",
            },
        )

    if ct == "product_removed":
        return _play(
            id=f"change-removed-{change['id']}", section="act_now", priority=55,
            headline=f"{hostname} pulled '{title or 'a product'}' from their catalog",
            action=(
                f"Search the product name on Google Shopping. If there's search demand (autocomplete, related searches), "
                f"that demand doesn't disappear when they delist — it redirects. If you carry something similar, push it now."
            ),
            deadline="this week", play_type="change", **base,
            detail={
                "steps": [
                    f"Search '{title or 'their product name'}' on Google Shopping",
                    "Check if autocomplete shows related searches — that's evidence of active demand",
                    "Check if other brands are appearing in results for that term",
                    "If you carry something similar: add it to your Google Shopping feed and update the title to include that search term",
                    "If you don't carry it: check if demand is high enough to source (search volume on Google Keyword Planner)",
                ],
                "why": "When a product is delisted, its search demand doesn't disappear immediately. Shoppers still search for it and get redirected to alternatives. Being that alternative is a traffic opportunity.",
                "outcome": "A product that matches a delisted competitor SKU can see organic Shopping traffic within 2–3 weeks of being listed.",
            },
        )

    if ct == "discount_start":
        pct_disc = _normalize_pct(new_v.get("discounted_pct")) * 100
        if pct_disc >= 25 or sev == "critical":
            return _play(
                id=f"change-discstart-{change['id']}", section="act_now", priority=80,
                headline=f"{hostname} started discounting — {pct_disc:.0f}% of catalog on sale" if pct_disc else f"{hostname} started a discount campaign",
                action=(
                    f"Identify which category is most discounted on their site — that's the inventory they're clearing. "
                    f"If you don't carry it, no action needed. If you do — hold your price and add social proof to justify it."
                ),
                deadline="today", play_type="change", **base, tab="discounts",
                detail={
                    "steps": [
                        f"Go to {hostname} → filter by 'On Sale' or 'Discounted'",
                        "Which category has the most discounts? (clothing, footwear, accessories, etc.)",
                        "Do you carry anything in that category?",
                        "If NO: no urgent action — monitor for 1 week",
                        "If YES: go to your product page for those items",
                        "Add: customer reviews, better photos, a short 'why we're worth full price' section",
                        "Run a small retargeting ad ($10/day) to people who visited your site but didn't convert — 'still full price, still in stock'",
                    ],
                    "why": "Discount campaigns drive comparison shopping. Shoppers who see a competitor's sale often open multiple tabs. Being positioned with strong social proof converts better than matching the price.",
                    "outcome": "Retargeting your own site visitors during a competitor's sale period typically shows 2–3x higher conversion rates than cold traffic.",
                },
            )

    if ct == "discount_end":
        return _play(
            id=f"change-discend-{change['id']}", section="act_now", priority=88,
            headline=f"{hostname}'s sale just ended — post-sale window is open",
            action=(
                f"Shoppers who missed their sale are still in a buying mindset. "
                f"Send an email to your list in the next 4 hours. "
                f"'This week only: [your offer]' converts well in this exact window."
            ),
            deadline="today", play_type="change", **base, tab="discounts",
            detail={
                "steps": [
                    f"Confirm {hostname}'s sale has ended (check their site)",
                    "Open your email tool — create a new broadcast to your full list",
                    "Subject line: time-sensitive but doesn't need to mention the competitor",
                    "Try: 'Still looking for [product]? We have it.' or '[Product] — this week only: [your offer]'",
                    "Body: keep it to 3 sentences max. Your product, your CTA, your price.",
                    "Send within 4 hours of confirming their sale ended",
                    "Optional: run $15/day Meta retargeting to your site visitors for the next 48 hours",
                ],
                "why": "The 4–24h window after a competitor's sale ends is one of the highest-intent moments in competitive e-commerce. Shoppers who missed the deal are still in the market and actively reconsidering.",
                "outcome": "Post-sale email windows typically see 25–40% higher open rates if sent within 4 hours. The urgency is real — it drops off sharply after 24h.",
            },
        )

    if ct == "availability_change":
        return _play(
            id=f"change-oos-{change['id']}", section="act_now", priority=75,
            headline=f"{hostname} has products going out of stock",
            action=(
                f"Open Meta Ads Manager and create an audience of {hostname} followers. "
                f"Run 'Ready to ship' copy with your product, fully in stock. "
                f"$15/day until they restock — usually 1–2 weeks. OOS windows are the fastest-converting moments."
            ),
            deadline="right now", play_type="availability", **base,
            detail={
                "steps": [
                    "Open Meta Ads Manager → Audiences",
                    f"Create a new Saved Audience: Interests → search '{hostname.split('.')[0]}' and select their brand page",
                    "Create a new campaign with this audience",
                    "Creative: your product photo, in stock, with copy 'Ready to ship — no waitlist'",
                    "Headline: 'In stock now' or 'Ships today' (contrast with their OOS state)",
                    "Budget: $15/day",
                    "Run until you see their products restock (check their site every few days)",
                    "OOS windows typically last 1–3 weeks for established brands",
                ],
                "why": f"{hostname} shoppers who hit an out-of-stock page are immediately in the market for alternatives. They've already decided to buy — they just need a place to buy from.",
                "outcome": "OOS retargeting campaigns typically see 2–4x higher CTR than standard prospecting because the audience is already purchase-ready.",
            },
        )

    return None
