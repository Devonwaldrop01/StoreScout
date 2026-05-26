"""
Playbook intelligence — v2.

Architecture change from v1: both functions now take ALL competitors at once
so they can synthesize across them instead of generating one card per competitor.

Rules:
- Max ~8 total plays returned
- One play per signal type (synthesized across competitors, not one per competitor)
- Actions are 30-minute executable tasks with specific platforms, budgets, and
  success criteria — not high-level marketing strategy
- Vendor concentration removed (meaningless for branded DTC stores)
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
) -> dict:
    return {
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


def _normalize_pct(value: float | int | None) -> float:
    """Normalize a percentage value to 0–1 fraction, handling both scales."""
    if value is None:
        return 0.0
    v = float(value)
    # If > 1 it's already a percentage (e.g. 48.07), convert to fraction
    return v / 100.0 if v > 1.0 else v


def _find_price_gap(pricing: dict) -> Optional[dict]:
    """Find an uncontested price band. Returns {band, low, high} or None."""
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
    Analyse all competitors' latest snapshots together and return synthesized plays.
    competitors_data: list of {competitor_id, hostname, snap}
    where snap is a scan_snapshots row including snapshot_data JSONB.
    """
    plays: list[dict] = []

    # ── Categorise each competitor ────────────────────────────────────────────
    heavy_discounters: list[dict] = []   # promo_rate >= 0.45
    slow_launchers:    list[dict] = []   # new_30d == 0
    fast_launchers:    list[dict] = []   # new_30d >= 8
    price_gap_comps:   list[dict] = []   # have a clear price band gap
    premium_comps:     list[dict] = []   # median >= $90

    for item in competitors_data:
        comp_id  = item["competitor_id"]
        hostname = item["hostname"]
        snap     = item["snap"]
        sd       = snap.get("snapshot_data") or {}

        discounts   = sd.get("discounts") or {}
        pricing_d   = sd.get("pricing")   or {}
        positioning = sd.get("positioning") or {}
        launch_d    = sd.get("launch_timeline") or {}

        # Normalise promo_rate: DB column is 0–1 fraction; JSON discounted_pct is 0–100
        raw_col = snap.get("promo_rate")
        if raw_col is not None:
            promo_rate = float(raw_col)          # already 0–1
        else:
            promo_rate = _normalize_pct(discounts.get("discounted_pct"))

        new_30d = int(snap.get("new_30d") or 0)
        median  = float(snap.get("median_price") or pricing_d.get("median") or 0)

        velocity_label = (positioning.get("launch_velocity") or {}).get("label", "")
        last_30d_rate  = float((launch_d.get("velocity") or {}).get("last_30d") or 0)

        avg_disc = _normalize_pct(discounts.get("avg_discount_pct")) * 100  # back to pct for display

        entry = {
            "comp_id": comp_id,
            "hostname": hostname,
            "promo_pct": int(promo_rate * 100),
            "avg_disc": avg_disc,
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

    # ── Generate synthesised plays ────────────────────────────────────────────

    # 1. Discount play — one card for all discounters ─────────────────────────
    if len(heavy_discounters) >= 3:
        names    = [d["hostname"] for d in heavy_discounters[:3]]
        rest     = len(heavy_discounters) - 2
        avg_promo = int(sum(d["promo_pct"] for d in heavy_discounters) / len(heavy_discounters))
        names_str = f"{names[0]}, {names[1]}, and {rest} others" if rest > 0 else " and ".join(names)
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
                f"Open Meta Ads Manager, duplicate your best ad set, and narrow the audience to followers of any of these brands. "
                f"Change the headline to something like '[Their brand] is on sale. We never are.' "
                f"Run $10/day for 5 days and compare CTR to your control — if it wins, you have a campaign."
            ),
            deadline="this week",
            play_type="positioning",
            source="snapshot",
            tab="discounts",
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
                f"Check if you carry anything similar. If yes — keep your price and add a comparison note "
                f"to your product page copy ('Compare: we don't discount this'). "
                f"If no — their discount shoppers are comparison searching right now. "
                f"Run a $10 Google Shopping campaign on their exact product names this week."
            ),
            deadline="this week",
            play_type="positioning",
            source="snapshot",
            tab="discounts",
        ))
    elif len(heavy_discounters) == 2:
        d1, d2 = heavy_discounters[0], heavy_discounters[1]
        plays.append(_play(
            id=f"snap-discount-{d1['comp_id']}",
            section="right_now",
            priority=65,
            competitor_id=d1["comp_id"],
            hostname=f"{d1['hostname']} & {d2['hostname']}",
            headline=f"{d1['hostname']} and {d2['hostname']} both have 40%+ of their catalog on sale",
            action=(
                f"Go to each site and find their #1 discounted product. Check if you carry anything similar. "
                f"If yes — hold your price and update that product page to emphasise value. "
                f"If no — open Meta Ads, create an audience of followers of both brands, "
                f"and run a 'never on sale' creative for $10/day this week. Their shoppers are comparing right now."
            ),
            deadline="this week",
            play_type="positioning",
            source="snapshot",
            tab="discounts",
        ))

    # 2. Slow launch → own new search ─────────────────────────────────────────
    if slow_launchers:
        # Show top 1 (most significant single competitor)
        s = slow_launchers[0]
        others = len(slow_launchers) - 1
        others_note = f" ({others} other competitor{'s' if others > 1 else ''} also in a quiet phase)" if others else ""
        plays.append(_play(
            id=f"snap-slowlaunch-{s['comp_id']}",
            section="right_now",
            priority=60,
            competitor_id=s["comp_id"],
            hostname=s["hostname"],
            headline=f"{s['hostname']} hasn't launched a new product in 30+ days{others_note}",
            action=(
                f"Open Google and search their main product category — check the Shopping tab "
                f"and filter to 'Past 90 days'. If their new listings are thin or absent, "
                f"there's organic search demand with no fresh competition from them. "
                f"A new listing with original photos and a solid title can rank in 2–4 weeks."
            ),
            deadline="this week",
            play_type="catalog",
            source="snapshot",
            tab="launches",
        ))

    # 3. Fast launch → research their bets ────────────────────────────────────
    if fast_launchers:
        f = fast_launchers[0]
        others = len(fast_launchers) - 1
        others_note = f" (and {others} other{'s' if others > 1 else ''} pushing hard)" if others else ""
        plays.append(_play(
            id=f"snap-fastlaunch-{f['comp_id']}",
            section="right_now",
            priority=65,
            competitor_id=f["comp_id"],
            hostname=f["hostname"],
            headline=f"{f['hostname']} launched {f.get('launch_count', 'many')} products this month{others_note}",
            action=(
                f"Go to {f['hostname']}/collections/new (or sort by newest) right now. "
                f"Look at their last 5–10 launches. Find any that are: (1) full price, not discounted, "
                f"(2) have 8+ variants, (3) outside their usual product range. "
                f"Those are the bets they have conviction in. Research those categories for sourcing "
                f"before they build organic search momentum over the next 4–6 weeks."
            ),
            deadline="right now",
            play_type="catalog",
            source="snapshot",
            tab="launches",
        ))

    # 4. Price band gap — top 2 competitors ───────────────────────────────────
    for comp in price_gap_comps[:2]:
        plays.append(_play(
            id=f"snap-pricegap-{comp['comp_id']}",
            section="this_week",
            priority=62,
            competitor_id=comp["comp_id"],
            hostname=comp["hostname"],
            headline=f"{comp['hostname']} has almost nothing priced in the {comp['band']} range",
            action=(
                f"That price band is uncontested in their catalog. "
                f"If you have a product that could sit in the {comp['band']} range, "
                f"move its price there and push it to the top of your store and ads this week — "
                f"you're not competing head-on. No product? Add '{comp['band']} {comp['hostname'].split('.')[0]} alternative' "
                f"to your sourcing list and search Alibaba with that price band as your cost ceiling."
            ),
            deadline="this week",
            play_type="pricing",
            source="snapshot",
            tab="pricing",
        ))

    # 5. Premium pricing → entry point opportunity ────────────────────────────
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
            headline=f"{p['hostname']}'s median price is ${p['median']:.0f} — their entry level is a gap you can own",
            action=(
                f"Go to {p['hostname']}'s site and look at their cheapest in-stock products "
                f"(usually accessories or entry-level SKUs). That's what they use to onboard budget shoppers. "
                f"A ${entry_low}–${entry_high} product from you in the same category "
                f"gets discovered by their audience before they're ready to spend ${p['median']:.0f}. "
                f"Check if you have anything in that range that's underselling, or add it to your sourcing pipeline."
            ),
            deadline="this week",
            play_type="pricing",
            source="snapshot",
            tab="pricing",
        ))

    return plays


# ── change event plays (reactive, per event) ──────────────────────────────────

def change_event_play(change: dict, hostname: str, comp_id: str) -> Optional[dict]:
    """
    Convert a single change_event into a time-sensitive playbook play.
    Returns None for low-signal events.
    """
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

    # Flash sale / critical price drop
    if ct == "price_change" and delta <= -15 and sev == "critical":
        return _play(
            id=f"change-flash-{change['id']}",
            section="act_now", priority=95,
            headline=f"{hostname} flash sale — {abs(delta):.0f}% off",
            action=(
                f"Flash sales on Shopify stores typically run 48–72h. "
                f"Open your email tool right now and queue a send to your list "
                f"in the next 6 hours — even a 'our prices didn't change' email captures "
                f"their shoppers who are actively comparing. "
                f"If you want to run a counter-offer, keep it time-limited to match their urgency."
            ),
            deadline="within 48h", play_type="change", **base, tab="pricing",
        )

    # Price increase — their customers are now comparison shopping
    if ct == "price_change" and delta >= 10:
        return _play(
            id=f"change-priceinc-{change['id']}",
            section="act_now", priority=85,
            headline=f"{hostname} raised prices {delta:.0f}% on {title or 'key products'}",
            action=(
                f"Pull up Google Ads or Meta Ads right now. "
                f"Search their brand name — are they running ads? If yes, you can target the same keywords "
                f"with your current price in the headline. "
                f"'[Their product] just went up. Ours didn't.' "
                f"Even a $20 spend this week captures people actively comparing prices."
            ),
            deadline="today", play_type="change", **base, tab="pricing",
        )

    # Moderate price drop
    if ct == "price_change" and delta < -5:
        return _play(
            id=f"change-pricedrop-{change['id']}",
            section="act_now", priority=78,
            headline=f"{hostname} dropped prices {abs(delta):.0f}% on {title or 'products'}",
            action=(
                f"Check if the products they dropped overlap with yours. "
                f"Go to their site and find the exact SKUs. "
                f"If you have similar products, don't match their price — instead update your listing "
                f"to lead with a value angle that isn't price (better materials, warranty, reviews). "
                f"Price wars on Shopify rarely win."
            ),
            deadline="today", play_type="change", **base, tab="pricing",
        )

    # Bulk reprice
    if ct == "bulk_price_change":
        return _play(
            id=f"change-bulkprice-{change['id']}",
            section="act_now", priority=70,
            headline=f"{hostname} repriced {count} products",
            action=(
                f"Open their site and sort by 'Price: low to high'. "
                f"Scan the first two pages — what changed? "
                f"If they went up, you now have room to raise yours without looking expensive. "
                f"If they went down across the board, they may be clearing out a category — "
                f"watch for what they replace it with over the next 2 weeks."
            ),
            deadline="this week", play_type="change", **base, tab="pricing",
        )

    # New product launch
    if ct == "new_product":
        return _play(
            id=f"change-newprod-{change['id']}",
            section="act_now", priority=65,
            headline=f"{hostname} launched: {title}" if title else f"{hostname} launched a new product",
            action=(
                f"Go look at the listing now. Check: is it full price or discounted? "
                f"How many variants? Does it overlap with your catalog? "
                f"If it overlaps — watch if it's still listed at full price in 2 weeks. "
                f"If it is, that's a validated demand signal worth sourcing. "
                f"If it goes on sale fast, they misjudged the market."
            ),
            deadline="this week", play_type="change", **base, tab="launches",
        )

    # Bulk launches
    if ct == "bulk_new_products":
        return _play(
            id=f"change-bulklaunch-{change['id']}",
            section="act_now", priority=68,
            headline=f"{hostname} added {count} new products",
            action=(
                f"Go to their site and filter by newest. Pick the 3 that look most different "
                f"from their usual range — those are their category bets. "
                f"Check if any are full-price with deep variant options. "
                f"Set a reminder to check back in 14 days: still listed at full price = real demand."
            ),
            deadline="this week", play_type="change", **base, tab="launches",
        )

    # Product removed
    if ct == "product_removed":
        return _play(
            id=f"change-removed-{change['id']}",
            section="act_now", priority=55,
            headline=f"{hostname} pulled '{title or 'a product'}' from their catalog",
            action=(
                f"Search the product name on Google Shopping. "
                f"If it's showing organic demand (autocomplete suggestions, related searches), "
                f"that demand doesn't disappear when they delist — it redirects. "
                f"If you carry something similar, push it in your Google Shopping feed this week."
            ),
            deadline="this week", play_type="change", **base, tab="changes",
        )

    # Discount started (significant)
    if ct == "discount_start":
        pct_disc = _normalize_pct(new_v.get("discounted_pct")) * 100
        if pct_disc >= 25 or sev == "critical":
            return _play(
                id=f"change-discstart-{change['id']}",
                section="act_now", priority=80,
                headline=f"{hostname} started a discount campaign — {pct_disc:.0f}% of catalog on sale" if pct_disc else f"{hostname} started discounting",
                action=(
                    f"Open their site and identify which category is most discounted. "
                    f"That's the inventory they're trying to move. "
                    f"If you don't carry it — there's less reason to react. "
                    f"If you do — hold your price and add social proof (reviews, photos) to your listing "
                    f"to justify why yours is worth paying full price."
                ),
                deadline="today", play_type="change", **base, tab="discounts",
            )

    # Sale ended → post-sale capture window
    if ct == "discount_end":
        return _play(
            id=f"change-discend-{change['id']}",
            section="act_now", priority=88,
            headline=f"{hostname}'s sale just ended — post-sale window is open",
            action=(
                f"Shoppers who missed their sale are in the market right now — "
                f"they missed the deal and are still thinking about buying. "
                f"Send an email to your list in the next 4 hours. "
                f"Subject line: something that acknowledges value without mentioning the competitor. "
                f"'This week only: [your offer]' converts well in this exact window."
            ),
            deadline="today", play_type="change", **base, tab="discounts",
        )

    # OOS / availability
    if ct == "availability_change":
        return _play(
            id=f"change-oos-{change['id']}",
            section="act_now", priority=75,
            headline=f"{hostname} has products going out of stock",
            action=(
                f"Open Meta Ads Manager and create an audience of people who follow {hostname} "
                f"or engage with their content. Run a simple creative: "
                f"your product, fully in stock, with 'Ready to ship' copy. "
                f"Budget: $15/day. Run it until they restock — usually 1–2 weeks. "
                f"OOS windows are the fastest-converting moments for competitors."
            ),
            deadline="right now", play_type="availability", **base, tab="overview",
        )

    return None
