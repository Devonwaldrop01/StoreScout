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

_PRIO_NUM = {"high": 90, "medium": 60, "low": 35}
_TF_SECTION = {"today": "act_now", "this week": "right_now", "this month": "this_week"}


def _rec(id, competitor_id, hostname, category, title, what_happened, why_it_matters,
         interpretation, objective, execution_paths, expected_outcome, evidence,
         confidence="verified", priority="medium", effort="1 hour", timeframe="this week") -> dict:
    """Build a strategy-first recommendation in the Playbook-2.0 schema
    (deterministic template fallback — instant, grounded, no channel-first)."""
    return {
        "id": id,
        "section": _TF_SECTION.get(timeframe, "right_now"),
        "priority": _PRIO_NUM.get(priority, 60),
        "competitor_id": competitor_id,
        "hostname": hostname,
        "source": "snapshot",
        # strategy-first
        "category": category,
        "title": title,
        "what_happened": what_happened,
        "why_it_matters": why_it_matters,
        "interpretation": interpretation,
        "objective": objective,
        "execution_paths": execution_paths,
        "expected_outcome": expected_outcome,
        "evidence": evidence,
        "confidence": confidence,
        "priority_label": priority,
        "effort": effort,
        "timeframe": timeframe,
        # legacy-compat
        "headline": title,
        "action": (execution_paths[0]["action"] if execution_paths else objective),
        "deadline": timeframe,
        "type": category.lower(),
        "tab": "overview",
        "detail": {
            "steps": [f"{ep['surface']}: {ep['action']}" for ep in execution_paths],
            "why": why_it_matters,
            "outcome": expected_outcome,
            "competitors": [{"hostname": hostname, "metric": evidence[0] if evidence else ""}],
        },
        "draft_asset": None,
    }


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

    recs: list[dict] = []

    # ── Discount posture — protect margin when the market races to the bottom ──
    if len(heavy_discounters) >= 2:
        names = ", ".join(d["hostname"] for d in heavy_discounters[:3])
        avg_promo = int(sum(d["promo_pct"] for d in heavy_discounters) / len(heavy_discounters))
        recs.append(_rec(
            id="synth-discount-industry",
            competitor_id=heavy_discounters[0]["comp_id"],
            hostname=f"{len(heavy_discounters)} competitors",
            category="Competitive Defense",
            title="Hold the full-price lane while rivals train their customers to wait for discounts",
            what_happened=f"{len(heavy_discounters)} competitors ({names}) are discounting at once — averaging {avg_promo}% of catalog on sale.",
            why_it_matters="When a whole niche discounts at once, shoppers can develop deal fatigue and margins tend to erode across the market. Full price can become a differentiator rather than a disadvantage.",
            interpretation="It looks like a price-led race — the kind that tends to condition customers to wait for markdowns and squeeze margins. That's a lane you may be able to exploit rather than match.",
            objective="Reduce discount dependence and protect margin",
            execution_paths=[
                {"surface": "Homepage", "action": "Lead with quality, guarantee, and craftsmanship messaging that justifies full price instead of matching their sale."},
                {"surface": "Merchandising", "action": "Raise perceived value with a bundle or a bonus at full price rather than cutting the price itself."},
                {"surface": "Email", "action": "Tell your list plainly why you don't chase discounts — consistent pricing signals confidence and quality."},
                {"surface": "Product Pages", "action": "Add trust signals (materials, warranty, reviews) so the price feels earned next to their markdowns."},
            ],
            expected_outcome="You protect margin and premium perception while competitors erode theirs.",
            evidence=[f"{len(heavy_discounters)} competitors ≥45% of catalog on sale", f"avg {avg_promo}% on sale"],
            confidence="verified", priority="high", effort="half day", timeframe="this week",
        ))
    elif len(heavy_discounters) == 1:
        d = heavy_discounters[0]
        recs.append(_rec(
            id=f"snap-discount-{d['comp_id']}",
            competitor_id=d["comp_id"], hostname=d["hostname"],
            category="Pricing",
            title=f"Use {d['hostname'].split('.')[0].title()}'s heavy discounting to look like the confident choice",
            what_happened=f"{d['hostname']} has {d['promo_pct']}% of its catalog on sale (avg {d['avg_disc']:.0f}% off).",
            why_it_matters="A near-permanent sale teaches their buyers to never pay full price — quietly training away their own margin and brand equity.",
            interpretation="This is a demand or inventory problem they're solving with price. Their discount is your opening to own the quality position.",
            objective="Win the full-price lane in your category",
            execution_paths=[
                {"surface": "Product Pages", "action": "On products you both carry, hold price and strengthen the value story instead of matching."},
                {"surface": "Homepage", "action": "Make 'always fair pricing, never a fake sale' a visible promise."},
                {"surface": "Email", "action": "Contrast your steady pricing with the discount treadmill — without naming them."},
            ],
            expected_outcome="You capture price-shoppers who've stopped trusting their 'sales' while keeping margin intact.",
            evidence=[f"{d['promo_pct']}% on sale", f"avg {d['avg_disc']:.0f}% off"],
            confidence="verified", priority="medium", effort="1 hour", timeframe="this week",
        ))

    # ── Launch cadence — freshness as a retention lever ──
    if fast_launchers:
        f = max(fast_launchers, key=lambda x: x.get("launch_count", 0))
        recs.append(_rec(
            id=f"snap-launch-{f['comp_id']}",
            competitor_id=f["comp_id"], hostname=f["hostname"],
            category="Product Strategy",
            title="Match their launch momentum with a cadence you can actually sustain",
            what_happened=f"{f['hostname']} shipped {f.get('launch_count', 0)} new products in the last 30 days.",
            why_it_matters="Constant freshness keeps a brand top-of-mind with repeat visitors and gives email/social a reason to fire — it compounds into retention.",
            interpretation="They're using velocity to stay relevant. You don't need to out-launch them; you need a rhythm your audience can rely on.",
            objective="Stay fresh and top-of-mind without over-extending",
            execution_paths=[
                {"surface": "Collections", "action": "Stand up a 'Just In' collection and rotate it on a fixed schedule (e.g. every 2 weeks)."},
                {"surface": "Email", "action": "Announce each drop to your list — a predictable cadence beats sporadic volume."},
                {"surface": "Merchandising", "action": "Rotate your homepage hero with each launch so returning visitors always see something new."},
                {"surface": "Content", "action": "Post the story behind each launch — freshness plus narrative outperforms freshness alone."},
            ],
            expected_outcome="Repeat visitors see a living store and a reason to come back, without you burning out on production.",
            evidence=[f"{f.get('launch_count', 0)} launches in 30d"],
            confidence="verified", priority="medium", effort="half day", timeframe="this month",
        ))
    elif slow_launchers and len(slow_launchers) >= 2:
        s = slow_launchers[0]
        recs.append(_rec(
            id="snap-launch-quiet",
            competitor_id=s["comp_id"], hostname=f"{len(slow_launchers)} competitors",
            category="Market Expansion",
            title="Competitors have gone quiet on launches — an opening to own attention in the niche",
            what_happened=f"{len(slow_launchers)} tracked competitors have launched little or nothing new in 30 days.",
            why_it_matters="When rivals stall, the customers browsing the category still want newness. Whoever shows up with fresh product captures that attention.",
            interpretation="A lull in the market is a demand vacuum. Momentum right now costs less to win than it will once they wake up.",
            objective="Capture demand while attention is uncontested",
            execution_paths=[
                {"surface": "Product Launches", "action": "Push your next launch forward and market it hard while the category is quiet."},
                {"surface": "SEO", "action": "Publish category/'new for [season]' content — you'll rank while competitors aren't producing."},
                {"surface": "Collections", "action": "Feature a prominent 'New Arrivals' set to signal you're the active brand."},
            ],
            expected_outcome="You become the brand that's clearly moving while others coast — winning share of attention cheaply.",
            evidence=[f"{len(slow_launchers)} competitors stalled on launches"],
            confidence="estimated", priority="medium", effort="half day", timeframe="this month",
        ))

    # ── Price-band white space ──
    if price_gap_comps:
        g = price_gap_comps[0]
        recs.append(_rec(
            id=f"snap-gap-{g['comp_id']}",
            competitor_id=g["comp_id"], hostname=g["hostname"],
            category="Catalog",
            title=f"Move into the {g['band']} price band they've left thin",
            what_happened=f"{g['hostname']} concentrates its catalog away from the {g['band']} band, leaving it underserved.",
            why_it_matters="A price band a competitor ignores is demand with no strong answer — the cheapest place to win a sale is where no one is really competing.",
            interpretation="Their pricing is clustered elsewhere by choice or constraint. That gap is assortment white space you can own.",
            objective="Expand assortment into an uncontested price band",
            execution_paths=[
                {"surface": "Catalog", "action": f"Introduce or reposition 2-3 products squarely in the {g['band']} band."},
                {"surface": "Collections", "action": f"Create a curated collection anchored on the {g['band']} price point."},
                {"surface": "Merchandising", "action": "Feature these on category pages so shoppers filtering by price find you first."},
            ],
            expected_outcome=f"You capture buyers shopping the {g['band']} range who currently have no strong option.",
            evidence=[f"white space in {g['band']} band"],
            confidence="estimated", priority="medium", effort="several days", timeframe="this month",
        ))

    # ── Premium rival → accessible entry point ──
    if premium_comps and not price_gap_comps:
        p = premium_comps[0]
        entry_low, entry_high = int(p["median"] * 0.35), int(p["median"] * 0.55)
        recs.append(_rec(
            id=f"snap-premium-{p['comp_id']}",
            competitor_id=p["comp_id"], hostname=p["hostname"],
            category="Market Expansion",
            title=f"Capture {p['hostname'].split('.')[0].title()}'s aspirational audience with an accessible entry product",
            what_happened=f"{p['hostname']} sits at a ${p['median']:.0f} median — premium positioning.",
            why_it_matters="Premium brands have a large audience of shoppers who admire them but can't buy yet. Those people are actively seeking accessible alternatives in the same category.",
            interpretation="Their price is a moat that also locks out their own aspirational demand. An entry product at a fraction of their price scoops up that consideration set.",
            objective="Capture demand priced out of a premium rival",
            execution_paths=[
                {"surface": "Catalog", "action": f"Offer an entry product at ${entry_low}-${entry_high} that echoes the premium look at an accessible price."},
                {"surface": "Product Pages", "action": "Position it as 'the accessible way in' — same category, honest price."},
                {"surface": "SEO", "action": f"Target '{p['hostname'].split('.')[0]} alternative' and 'affordable [category]' queries."},
            ],
            expected_outcome="You bring their aspirational shoppers into YOUR funnel before they graduate to higher price points.",
            evidence=[f"premium rival at ${p['median']:.0f} median"],
            confidence="estimated", priority="low", effort="several days", timeframe="this month",
        ))

    return recs



# ── change event plays ────────────────────────────────────────────────────────

def change_event_play(change: dict, hostname: str, comp_id: str) -> Optional[dict]:
    """Reactive strategy-first recommendation from a single competitor change
    event. Strategy is the recommendation; execution paths are tool-agnostic
    options — never 'run a Meta ad'."""
    ct    = change.get("change_type", "")
    sev   = change.get("severity", "info")
    delta = float(change.get("delta_pct") or 0)
    prod  = (change.get("product_title") or "").strip()[:60]
    old_v = change.get("old_value") or {}
    new_v = change.get("new_value") or {}
    count = old_v.get("count") or new_v.get("count") or "several"
    brand = hostname.split(".")[0].title()

    if sev == "info" and ct not in ("discount_end", "availability_change"):
        return None

    from datetime import datetime, timezone
    detected = change.get("detected_at", "")
    hours_ago = 999.0
    if detected:
        try:
            dt = datetime.fromisoformat(detected.replace("Z", "+00:00"))
            hours_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        except Exception:
            pass
    timeframe = "today" if hours_ago < 48 else "this week"

    def mk(cid_suffix, category, title, what, why, interp, objective, paths, outcome,
           priority="medium", effort="1 hour", confidence="verified"):
        return _rec(
            id=f"change-{cid_suffix}-{change.get('id', '')}",
            competitor_id=comp_id, hostname=hostname, category=category, title=title,
            what_happened=what, why_it_matters=why, interpretation=interp, objective=objective,
            execution_paths=paths, expected_outcome=outcome,
            evidence=[f"{ct.replace('_',' ')}" + (f" · {prod}" if prod else "") + (f" · {delta:+.0f}%" if delta else "")],
            confidence=confidence, priority=priority, effort=effort, timeframe=timeframe,
        )

    # ── Competitor flash sale / deep price drop ──
    if ct == "price_change" and delta <= -15 and sev == "critical":
        return mk("flash", "Competitive Defense",
            f"{brand} just cut prices {abs(delta):.0f}% — meet the moment without joining the race",
            f"{hostname} dropped price {abs(delta):.0f}%" + (f" on {prod}" if prod else "") + " — likely a short flash window.",
            "A cut this deep often puts shoppers in a comparing mindset — a moment to be visible with a confident answer, not to panic-discount.",
            "A short, deep cut can point to inventory pressure or a limited-time promo — either way, a reason to hold your position rather than mirror it.",
            "Capture their comparison shoppers while protecting your margin",
            [
                {"surface": "Email", "action": "Send a timely note to your list — steady pricing, in stock, no games. You don't need a sale to win the comparison."},
                {"surface": "Homepage", "action": "Surface your best sellers and guarantees so comparers landing on you see value immediately."},
                {"surface": "Pricing", "action": "If you must respond, use a time-boxed bundle rather than an across-the-board cut."},
            ],
            "You convert their in-market shoppers without training your own customers to wait for discounts.",
            priority="high", effort="1 hour")

    # ── Competitor raised prices ──
    if ct == "price_change" and delta >= 10:
        return mk("priceinc", "Pricing",
            f"{brand} raised prices {delta:.0f}% — become the better-value choice in the comparison",
            f"{hostname} increased price {delta:.0f}%" + (f" on {prod}" if prod else "") + ".",
            "A price increase sends their price-sensitive customers shopping — and you're the alternative they'll find.",
            "They're prioritizing margin over volume. That trade-off opens a value gap you can occupy.",
            "Win their price-sensitive shoppers",
            [
                {"surface": "Product Pages", "action": "On the equivalent products, make your (now-relatively-lower) price and value explicit."},
                {"surface": "SEO", "action": f"Publish a '{brand} alternative' / comparison page targeting shoppers reacting to the increase."},
                {"surface": "Email", "action": "Remind your list of your steady, fair pricing — quietly contrasting the market."},
            ],
            "You capture the demand their increase pushed out the door.",
            priority="high")

    # ── Competitor cut price modestly ──
    if ct == "price_change" and delta < -5:
        return mk("pricecut", "Pricing",
            f"{brand} trimmed prices {abs(delta):.0f}% — decide deliberately whether to hold or differentiate",
            f"{hostname} lowered price {abs(delta):.0f}%" + (f" on {prod}" if prod else "") + ".",
            "Small cuts test elasticity. Reflexively matching erodes your margin for no strategic gain.",
            "They may be probing price sensitivity. Your best answer is usually value, not a matching cut.",
            "Protect margin while staying competitive",
            [
                {"surface": "Product Pages", "action": "Reinforce why your equivalent product is worth its price — reviews, materials, service."},
                {"surface": "Merchandising", "action": "Add value with a bundle instead of dropping price."},
            ],
            "You stay competitive on perceived value without giving up margin.",
            priority="medium")

    if ct == "bulk_price_change":
        return mk("bulkprice", "Competitive Defense",
            f"{brand} repriced across its catalog — re-check where you now stand",
            f"{hostname} changed prices on {count} products at once.",
            "A catalog-wide reprice resets the competitive map — your relative position just moved, for better or worse.",
            "Broad repricing is a strategy shift, not a one-off. It's worth a deliberate response.",
            "Re-establish your price positioning",
            [
                {"surface": "Pricing", "action": "Audit your prices against theirs on your top overlapping products and decide where to hold vs adjust."},
                {"surface": "Collections", "action": "Re-merchandise so your strongest value propositions lead."},
            ],
            "Your pricing stays intentional relative to a competitor that just shifted the board.",
            priority="medium", effort="half day")

    if ct in ("new_product", "bulk_new_products"):
        many = ct == "bulk_new_products"
        return mk("launch", "Product Strategy",
            f"{brand} launched " + (f"{count} new products" if many else (prod or "a new product")) + " — read the signal before you react",
            f"{hostname} added " + (f"{count} products" if many else (f'"{prod}"' if prod else "a product")) + " to its catalog.",
            "New launches reveal where a competitor sees demand — a free read on the category's direction.",
            "They're betting on this direction. You can fast-follow, counter-position, or deliberately skip it.",
            "Turn their launch into your assortment decision",
            [
                {"surface": "Catalog", "action": "Decide: do you have (or can you quickly add) an answer in this space, or is it a lane to concede?"},
                {"surface": "Product Pages", "action": "If you already compete here, sharpen your equivalent's positioning to intercept the interest they're generating."},
                {"surface": "Content", "action": "Publish comparison/education content for the category they just validated."},
            ],
            "You respond to their bet with a decision, not a reflex — expanding where it's smart, skipping where it isn't.",
            priority="medium", effort="1 hour", confidence="verified")

    if ct == "product_removed":
        return mk("removed", "Market Expansion",
            f"{brand} pulled " + (prod or "a product") + " — a gap may have just opened",
            f"{hostname} removed " + (f'"{prod}"' if prod else "a product") + " from its catalog.",
            "A discontinued product leaves its buyers looking for a replacement — demand with a suddenly-weaker answer.",
            "They exited this for a reason (margin, inventory, focus). Their exit is your entry if the demand remains.",
            "Capture orphaned demand from a discontinued product",
            [
                {"surface": "SEO", "action": f"Target searches for the discontinued item and '{brand} alternative' to catch its former buyers."},
                {"surface": "Catalog", "action": "Make sure you carry (or add) a strong equivalent, and feature it."},
            ],
            "You absorb the demand their exit left behind.",
            priority="low", confidence="estimated")

    if ct == "discount_start":
        return mk("promostart", "Competitive Defense",
            f"{brand} started a promotion — hold your position with intent",
            f"{hostname} launched a discount/campaign" + (f" on {prod}" if prod else "") + ".",
            "A competitor's sale pulls attention and comparison traffic into the category — including toward you.",
            "This is likely a planned campaign, not desperation. Reacting emotionally with your own sale is the trap.",
            "Benefit from the attention without discounting reflexively",
            [
                {"surface": "Homepage", "action": "Make your value and guarantees prominent for the comparison traffic their sale stirs up."},
                {"surface": "Email", "action": "Time a value-led (not discount-led) message to your list while the category is hot."},
            ],
            "You capture spillover attention while keeping your pricing discipline.",
            priority="medium")

    if ct == "discount_end":
        return mk("promoend", "Pricing",
            f"{brand}'s promotion ended — a brief window where your price looks strong",
            f"{hostname} ended a discount/campaign" + (f" on {prod}" if prod else "") + ", returning to full price.",
            "When their sale ends, your steady price is momentarily the better deal in the category.",
            "Post-sale, their prices snap back up. For a short window you're the value option by default.",
            "Capitalize on the post-promo price gap",
            [
                {"surface": "Product Pages", "action": "On overlapping products, make your comparatively-lower price obvious now."},
                {"surface": "Email", "action": "Send a well-timed nudge while your price advantage is real."},
            ],
            "You convert shoppers during the brief window your pricing looks best.",
            priority="low", confidence="estimated")

    if ct == "availability_change":
        return mk("stock", "Market Expansion",
            f"{brand} has stock gaps — be the in-stock answer",
            f"{hostname} shows out-of-stock/availability changes" + (f" on {prod}" if prod else "") + ".",
            "Out-of-stock is unmet demand in real time — those shoppers need an alternative right now.",
            "Stock gaps are the most perishable opportunity in ecommerce; the demand doesn't wait.",
            "Capture demand they can't currently fulfill",
            [
                {"surface": "Merchandising", "action": "Make sure your equivalent in-stock product is easy to find and prominently featured."},
                {"surface": "SEO", "action": f"Ensure you rank for the category / '{brand} alternative' so their stranded shoppers find you."},
            ],
            "You convert shoppers their stockout sent looking.",
            priority="medium", confidence="estimated")

    return None

