from __future__ import annotations
from typing import Optional


def action_for_change(change: dict, hostname: str) -> str:
    ct = change.get("change_type", "")
    delta = change.get("delta_pct") or 0
    title = (change.get("product_title") or "")[:40]
    old_v = change.get("old_value") or {}
    new_v = change.get("new_value") or {}
    count = old_v.get("count") or new_v.get("count") or "several"

    if ct == "price_change" and delta <= -15 and change.get("severity") == "critical":
        return (
            f"Flash sale — run a competing offer before {hostname}'s sale ends "
            f"(flash sales typically last 48–72h)."
        )
    elif ct == "price_change" and delta < -5:
        abs_delta = abs(delta)
        return (
            f"{hostname} cut prices {abs_delta:.0f}%. Their price-sensitive shoppers "
            f"are comparing right now — position your store before the weekend."
        )
    elif ct == "price_change" and delta > 15:
        return (
            f"{hostname} raised prices {delta:.0f}% on {title or 'key products'}. "
            f"Their value customers are now comparison shopping — this week is your window."
        )
    elif ct == "price_change" and delta > 0:
        return (
            f"{hostname} nudged prices up {delta:.0f}%. Watch whether it holds — "
            f"if it does, you have room to adjust your own pricing upward."
        )
    elif ct == "bulk_price_change":
        return (
            f"{hostname} repriced {count} products. Check if any of your pricing "
            f"overlaps — a quick scan this week keeps you from being undercut."
        )
    elif ct == "new_product":
        return (
            f"{hostname} just launched '{title}'. Check if this fills a gap in your "
            f"catalog — if it overlaps, watch their early pricing strategy."
        )
    elif ct == "bulk_new_products":
        return (
            f"{hostname} added {count} products — likely ahead of a campaign push. "
            f"Watch for paid social promotions in the next 7 days."
        )
    elif ct == "product_removed":
        return (
            f"{hostname} pulled '{title or 'a product'}'. If you carry something similar, "
            f"there's now less competition — push that SKU in your ads this week."
        )
    elif ct == "bulk_removal":
        return (
            f"{hostname} removed {count} products. Watch what replaces them — "
            f"it signals where they're repositioning."
        )
    elif ct == "discount_start":
        pct = new_v.get("discounted_pct", 0) or 0
        if pct >= 30:
            return (
                f"{hostname} has {pct:.0f}% of their catalog on sale. Don't race them — "
                f"push a 'full-price quality' message to your email list instead."
            )
        return (
            f"{hostname} started discounting. If it spreads site-wide in the next "
            f"48h, prepare a counter-offer — otherwise hold and monitor."
        )
    elif ct == "discount_end":
        return (
            f"{hostname}'s sale just ended. Their price-sensitive customers "
            f"are back in the market — reach your email list today."
        )
    elif ct == "availability_change":
        return (
            f"{hostname} has stock gaps. Being reliably in-stock is a positioning "
            f"advantage right now — push that message in your ads."
        )
    return f"Review recent changes at {hostname} to see if a response makes sense."


def action_for_gap(gap: dict, hostname: str) -> str:
    gap_type = gap.get("type", "")
    if gap_type == "price_band":
        return (
            f"{hostname} doesn't cover this price point — "
            f"you could enter without competing head-on."
        )
    elif gap_type == "availability":
        return (
            f"{hostname} has stock issues — position your in-stock "
            f"inventory as the reliable alternative."
        )
    elif gap_type == "category":
        return (
            f"{hostname} is thin in this category — expansion here "
            f"captures demand they're not serving."
        )
    elif gap_type == "discount":
        return (
            f"{hostname} leans heavily on discounts — full-price positioning "
            f"and quality messaging differentiates you."
        )
    elif gap_type == "launch_momentum":
        return (
            f"{hostname}'s launch pace is slowing — this is your window "
            f"to dominate new product search."
        )
    return f"Gap identified in {hostname}'s catalog — see the Gaps tab for the full opportunity."
