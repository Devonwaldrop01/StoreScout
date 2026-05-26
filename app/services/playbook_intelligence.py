"""
Playbook intelligence generators.

Two sources:
  1. snapshot_intelligence(snap, hostname, comp_id)  — derived from current scan state,
     always available after the first scan, no change events required.
  2. change_event_play(change, hostname, comp_id)    — reactive, requires scan-to-scan diff.

Both return a list of PlaybookPlay dicts (or empty list).
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


def _price_gap_play(pricing: dict, hostname: str, comp_id: str) -> Optional[dict]:
    """Find an uncontested price band in their distribution."""
    pb = pricing.get("price_buckets") or {}
    buckets = pb.get("buckets") or {}
    order = pb.get("bucket_order") or []

    if not buckets or not order or len(order) < 3:
        return None

    total = sum(buckets.get(b, 0) for b in order)
    if total < 5:
        return None

    shares = {b: buckets.get(b, 0) / total for b in order}

    for i in range(1, len(order) - 1):
        b = order[i]
        if shares.get(b, 0) < 0.05:
            before_pop = any(shares.get(order[j], 0) > 0.10 for j in range(i))
            after_pop = any(shares.get(order[j], 0) > 0.10 for j in range(i + 1, len(order)))
            if before_pop and after_pop:
                return _play(
                    id=f"snap-pricegap-{comp_id}",
                    section="this_week",
                    priority=62,
                    competitor_id=comp_id,
                    hostname=hostname,
                    headline=f"{hostname} has almost no products priced in the {b} range",
                    action=(
                        f"The {b} price point sits between their two main ranges — uncontested territory. "
                        f"A product here captures shoppers who find them too expensive or too cheap, "
                        f"without going head-to-head on their core SKUs."
                    ),
                    deadline="this week",
                    play_type="pricing",
                    source="snapshot",
                    tab="pricing",
                )
    return None


# ── snapshot intelligence (always available after first scan) ─────────────────

def snapshot_intelligence(snap: dict, hostname: str, comp_id: str) -> list[dict]:
    """
    Generate plays from the current snapshot state — no change events required.
    snap contains both scan_snapshots row columns AND the snapshot_data JSONB.
    """
    plays: list[dict] = []
    sd = snap.get("snapshot_data") or {}

    # Convenience aliases
    pricing     = sd.get("pricing") or {}
    discounts   = sd.get("discounts") or {}
    positioning = sd.get("positioning") or {}
    launch      = sd.get("launch_timeline") or {}
    vendor      = sd.get("vendor_analysis") or {}

    # Prefer column values (already computed); fall back to snapshot_data
    promo_rate  = snap.get("promo_rate") or discounts.get("discounted_pct") or 0
    new_30d     = snap.get("new_30d") or 0
    median      = snap.get("median_price") or pricing.get("median") or 0
    total       = snap.get("product_count") or (sd.get("catalog") or {}).get("total_products") or 0

    # 1 ── Discount dependency ─────────────────────────────────────────────────
    if promo_rate >= 0.40:
        pct = int(promo_rate * 100)
        avg_disc = discounts.get("avg_discount_pct") or 0
        avg_note = f" at an average {avg_disc:.0f}% off" if avg_disc else ""
        plays.append(_play(
            id=f"snap-discount-{comp_id}",
            section="right_now",
            priority=68,
            competitor_id=comp_id,
            hostname=hostname,
            headline=f"{hostname} has {pct}% of their catalog on sale right now{avg_note}",
            action=(
                f"They're conditioning customers to wait for the next deal. "
                f"Send an email this week positioning your products as 'always worth full price' — "
                f"their loyal full-price shoppers are your best acquisition target right now."
            ),
            deadline="this week",
            play_type="positioning",
            source="snapshot",
            tab="discounts",
        ))

    # 2 ── Launch velocity slow → window to own new search ────────────────────
    velocity_label = (positioning.get("launch_velocity") or {}).get("label", "")
    last_30d_rate  = (launch.get("velocity") or {}).get("last_30d") or 0

    if new_30d == 0 or velocity_label == "slow":
        plays.append(_play(
            id=f"snap-nolaunches-{comp_id}",
            section="right_now",
            priority=60,
            competitor_id=comp_id,
            hostname=hostname,
            headline=f"{hostname} hasn't launched a new product in 30+ days",
            action=(
                f"They're in a quiet catalog phase. Launch something in this category now "
                f"and own new-product search results before they push again. "
                f"A basic listing this week beats a polished one next month."
            ),
            deadline="this week",
            play_type="catalog",
            source="snapshot",
            tab="launches",
        ))
    elif new_30d >= 8 or last_30d_rate >= 8:
        plays.append(_play(
            id=f"snap-launches-{comp_id}",
            section="right_now",
            priority=65,
            competitor_id=comp_id,
            hostname=hostname,
            headline=f"{hostname} launched {new_30d or int(last_30d_rate)} products this month — aggressive push",
            action=(
                f"Check their newest listings now. If any show full-price traction after 2 weeks, "
                f"that category has freshly validated demand — research sourcing before "
                f"they build organic momentum and own the search rankings."
            ),
            deadline="right now",
            play_type="catalog",
            source="snapshot",
            tab="launches",
        ))

    # 3 ── Price band gap ──────────────────────────────────────────────────────
    gap_play = _price_gap_play(pricing, hostname, comp_id)
    if gap_play:
        plays.append(gap_play)

    # 4 ── Premium price = accessibility gap ───────────────────────────────────
    if median >= 90 and total >= 10:
        plays.append(_play(
            id=f"snap-premium-{comp_id}",
            section="this_week",
            priority=50,
            competitor_id=comp_id,
            hostname=hostname,
            headline=f"{hostname}'s median price is ${median:.0f} — premium territory with an entry-level gap",
            action=(
                f"An SKU priced $40–$70 below their median captures their consideration set "
                f"without competing on their core range. Even one accessible option funnels "
                f"budget-conscious shoppers into your brand before they're ready to spend more."
            ),
            deadline="this week",
            play_type="pricing",
            source="snapshot",
            tab="pricing",
        ))

    # 5 ── Vendor concentration = supply chain risk for them ───────────────────
    top_vendors = vendor.get("top_vendors") or []
    if top_vendors:
        top = top_vendors[0]
        top_pct = top.get("pct") or 0
        top_name = top.get("vendor") or ""
        if top_pct >= 0.55 and top_name and vendor.get("vendor_count", 99) <= 3:
            plays.append(_play(
                id=f"snap-vendor-{comp_id}",
                section="this_week",
                priority=44,
                competitor_id=comp_id,
                hostname=hostname,
                headline=f"{hostname} sources {int(top_pct * 100)}% of their catalog from one vendor",
                action=(
                    f"Single-source dependency is a supply chain risk — especially near peak season. "
                    f"Emphasize your product or supplier diversity in marketing copy. "
                    f"'We don't put all our eggs in one basket' resonates strongly with buyers "
                    f"who've experienced out-of-stock issues before."
                ),
                deadline="this week",
                play_type="positioning",
                source="snapshot",
                tab="overview",
            ))

    # 6 ── Heavy discounting → full-price positioning opportunity ─────────────
    avg_disc = discounts.get("avg_discount_pct") or 0
    max_disc = discounts.get("max_discount_pct") or 0
    if avg_disc >= 25 and promo_rate < 0.40:  # moderate count, deep discounts
        plays.append(_play(
            id=f"snap-deepdisc-{comp_id}",
            section="this_week",
            priority=48,
            competitor_id=comp_id,
            hostname=hostname,
            headline=f"{hostname} averages {avg_disc:.0f}% off when they discount — deep markdown culture",
            action=(
                f"Deep markdowns signal margin pressure and erode perceived quality. "
                f"Position your brand as 'we price honestly from day one' — add a "
                f"'Why we don't discount' note to your about page and email footer. "
                f"This converts their deal-fatigued customers into your loyal ones."
            ),
            deadline="this week",
            play_type="positioning",
            source="snapshot",
            tab="discounts",
        ))

    return plays


# ── change event plays (reactive, time-sensitive) ─────────────────────────────

def change_event_play(change: dict, hostname: str, comp_id: str) -> Optional[dict]:
    """
    Convert a single change_event row into a time-sensitive playbook play.
    Returns None for info-severity or low-value changes.
    """
    ct    = change.get("change_type", "")
    sev   = change.get("severity", "info")
    delta = change.get("delta_pct") or 0
    title = (change.get("product_title") or "")[:40]
    old_v = change.get("old_value") or {}
    new_v = change.get("new_value") or {}
    count = old_v.get("count") or new_v.get("count") or "several"

    # Skip low-signal events
    if sev == "info" and ct not in ("discount_end", "availability_change"):
        return None

    from datetime import datetime, timezone, timedelta
    detected = change.get("detected_at", "")
    hours_ago = 0
    if detected:
        try:
            dt = datetime.fromisoformat(detected.replace("Z", "+00:00"))
            hours_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        except Exception:
            pass

    # Deadline string
    if hours_ago < 24:
        deadline = "today"
    elif hours_ago < 48:
        deadline = "within 48h"
    else:
        deadline = "this week"

    base = dict(
        competitor_id=comp_id,
        hostname=hostname,
        source="change_event",
        tab="changes",
    )

    # ── Flash sale / big price drop ───────────────────────────────────────────
    if ct == "price_change" and delta <= -15 and sev == "critical":
        return _play(
            id=f"change-flash-{change['id']}",
            section="act_now",
            priority=95,
            headline=f"{hostname} flash sale — {abs(delta):.0f}% off key products",
            action=(
                f"Run a competing offer before their sale ends — flash sales typically last 48–72h. "
                f"Hit your email list now with a bundle or limited offer. "
                f"Once their sale ends, their price-sensitive shoppers flood back to the market."
            ),
            deadline="within 48h",
            play_type="change",
            **base,
            tab="pricing",
        )

    # ── Price increase ────────────────────────────────────────────────────────
    if ct == "price_change" and delta >= 10:
        return _play(
            id=f"change-priceinc-{change['id']}",
            section="act_now",
            priority=85,
            headline=f"{hostname} raised prices {delta:.0f}% on {title or 'key products'}",
            action=(
                f"Their price-sensitive customers are comparison shopping right now. "
                f"Run a targeted campaign this week — even just updating your ad copy "
                f"to reference your price point captures people actively comparing."
            ),
            deadline="today",
            play_type="change",
            **base,
            tab="pricing",
        )

    # ── Moderate price drop ───────────────────────────────────────────────────
    if ct == "price_change" and delta < -5:
        return _play(
            id=f"change-pricedrop-{change['id']}",
            section="act_now",
            priority=80,
            headline=f"{hostname} cut prices {abs(delta):.0f}% on {title or 'products'}",
            action=(
                f"Their price-sensitive shoppers are comparing right now. "
                f"Position your store before the weekend — update your homepage or ads "
                f"to highlight your value relative to their new price point."
            ),
            deadline="today",
            play_type="change",
            **base,
            tab="pricing",
        )

    # ── Bulk price change ─────────────────────────────────────────────────────
    if ct == "bulk_price_change":
        return _play(
            id=f"change-bulkprice-{change['id']}",
            section="act_now",
            priority=72,
            headline=f"{hostname} repriced {count} products",
            action=(
                f"Check if any repriced SKUs overlap with your catalog — "
                f"a quick scan this week keeps you from being quietly undercut. "
                f"If they went up, you may have room to move too."
            ),
            deadline="this week",
            play_type="change",
            **base,
            tab="pricing",
        )

    # ── New product ───────────────────────────────────────────────────────────
    if ct == "new_product":
        return _play(
            id=f"change-newprod-{change['id']}",
            section="act_now",
            priority=68,
            headline=f"{hostname} launched: {title}" if title else f"{hostname} launched a new product",
            action=(
                f"Check if this fills a gap in your catalog — if it overlaps, "
                f"watch their early pricing strategy. If it sticks at full price after 2 weeks, "
                f"the category has freshly validated demand worth sourcing."
            ),
            deadline="this week",
            play_type="change",
            **base,
            tab="launches",
        )

    # ── Bulk new products ─────────────────────────────────────────────────────
    if ct == "bulk_new_products":
        return _play(
            id=f"change-bulklaunch-{change['id']}",
            section="act_now",
            priority=70,
            headline=f"{hostname} added {count} new products — likely ahead of a campaign push",
            action=(
                f"Watch for paid social promotions from them in the next 7 days — "
                f"bulk launches often precede ad campaigns. If you compete in the same category, "
                f"increase your own bids before their campaign drives up CPMs."
            ),
            deadline="this week",
            play_type="change",
            **base,
            tab="launches",
        )

    # ── Product removed ───────────────────────────────────────────────────────
    if ct == "product_removed":
        return _play(
            id=f"change-removed-{change['id']}",
            section="act_now",
            priority=55,
            headline=f"{hostname} pulled '{title or 'a product'}' from their catalog",
            action=(
                f"If you carry something similar, there's now less competition — "
                f"push that SKU in your ads this week while the search demand still exists "
                f"but their listing is gone."
            ),
            deadline="this week",
            play_type="change",
            **base,
            tab="changes",
        )

    # ── Discount started ──────────────────────────────────────────────────────
    if ct == "discount_start":
        pct_disc = new_v.get("discounted_pct") or 0
        if pct_disc >= 30 or sev == "critical":
            return _play(
                id=f"change-discstart-{change['id']}",
                section="act_now",
                priority=82,
                headline=f"{hostname} has {pct_disc:.0f}% of their catalog on sale" if pct_disc else f"{hostname} started a sitewide discount campaign",
                action=(
                    f"Don't race them to the bottom — push a 'full-price quality' message instead. "
                    f"Their discount-fatigued customers are your best acquisition target right now. "
                    f"Send your email list today."
                ),
                deadline="today",
                play_type="change",
                **base,
                tab="discounts",
            )

    # ── Sale ended → post-sale recapture ─────────────────────────────────────
    if ct == "discount_end":
        return _play(
            id=f"change-discend-{change['id']}",
            section="act_now",
            priority=88,
            headline=f"{hostname}'s sale just ended — their customers are back in the market",
            action=(
                f"Price-sensitive shoppers who missed their sale are actively looking for alternatives right now. "
                f"Hit your email list today with an offer — even a small bundle or free shipping "
                f"converts well in the 24h window after a competitor's sale ends."
            ),
            deadline="today",
            play_type="change",
            **base,
            tab="discounts",
        )

    # ── Availability / OOS ────────────────────────────────────────────────────
    if ct == "availability_change":
        return _play(
            id=f"change-oos-{change['id']}",
            section="act_now",
            priority=75,
            headline=f"{hostname} has stock gaps — products going out of stock",
            action=(
                f"Run retargeting targeting their audience with 'In Stock Now' ad copy. "
                f"Their customers are actively looking for an alternative — "
                f"this window closes when they restock, typically within 1–2 weeks."
            ),
            deadline="right now",
            play_type="availability",
            **base,
            tab="overview",
        )

    return None
