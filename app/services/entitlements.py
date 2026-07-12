"""Single source of truth for plan entitlements.

Every tier limit and feature gate resolves through this module so the API, the
workers, the Stripe webhook handler and the frontend all agree on what each
plan can do. Before this, the limits map was copied into four files and drifted.

Authoritative plan state lives on `user_profiles` (`tier` + `subscription_status`);
this module only interprets it. Operator-tunable numbers (competitor caps, scan
intervals) still come from settings so the existing env knobs keep working;
everything else — history retention, watchlist caps, feature booleans — is
defined here.

Subscription-state semantics (kept consistent with the webhook handler):
  · active / trialing         → full paid access
  · past_due                  → paid access retained (grace during Stripe retries;
                                the webhook updates status only, not tier)
  · cancel-at-period-end      → Stripe keeps status 'active' until the period ends,
                                then emits subscription.deleted → tier reverts to free
  · canceled / unpaid / inactive (deleted) → free
  · missing row / webhook delay → treated as free (fail-closed)
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.config import get_settings

VALID_TIERS = ("free", "pro", "agency", "developer")
PAID_TIERS = ("pro", "agency", "developer")

# Statuses under which a *paid* tier still grants access. 'past_due' is included
# as a grace state (matches the webhook, which does not downgrade on past_due).
ACTIVE_PAID_STATUSES = frozenset({"active", "trialing", "past_due"})

# The default (free) fallback used everywhere a tier is unknown/missing.
_DEFAULT_TIER = "free"


def normalize_tier(raw: Optional[str]) -> str:
    """Coerce any stored/absent tier value into a known tier (fail-closed to free)."""
    t = (raw or "").strip().lower()
    return t if t in VALID_TIERS else _DEFAULT_TIER


def resolve_tier(profile: Optional[Dict[str, Any]]) -> str:
    """The effective tier for a `user_profiles` row (or None). Tier is managed by
    the webhook handler (it flips to free on subscription.deleted), so we honor the
    stored value and only fail-closed to free when it is missing/unknown."""
    return normalize_tier((profile or {}).get("tier"))


def subscription_state(profile: Optional[Dict[str, Any]]) -> str:
    """Normalized subscription status for display/tests: one of
    active | trialing | past_due | canceled | inactive | none."""
    if not profile:
        return "none"
    status = (profile.get("subscription_status") or "").strip().lower()
    if status in ("active", "trialing", "past_due", "canceled", "inactive"):
        return status
    # A paid tier with no explicit status is treated as active; free as none.
    if resolve_tier(profile) in PAID_TIERS:
        return "active"
    return "none"


def is_paid(tier: str) -> bool:
    return normalize_tier(tier) in PAID_TIERS


def limits_for(tier: str) -> Dict[str, Any]:
    """Canonical numeric limits for a tier. Competitor caps and scan intervals
    come from settings; retention/caps/flags are defined here. Returns a superset
    (extra keys are additive and safe for existing consumers)."""
    s = get_settings()
    table: Dict[str, Dict[str, Any]] = {
        "free": {
            "max_competitors": s.free_max_competitors, "scan_hours": s.free_scan_interval_hours,
            "history_days": 0, "watch_cap": 3, "ai_digest": False, "automatic_scans": True,
        },
        "pro": {
            "max_competitors": s.pro_max_competitors, "scan_hours": s.pro_scan_interval_hours,
            "history_days": 90, "watch_cap": 25, "ai_digest": True, "automatic_scans": True,
        },
        "agency": {
            "max_competitors": s.agency_max_competitors, "scan_hours": s.agency_scan_interval_hours,
            "history_days": 3650, "watch_cap": 25, "ai_digest": True, "automatic_scans": True,
        },
        "developer": {
            "max_competitors": 50, "scan_hours": 12,
            "history_days": 3650, "watch_cap": 25, "ai_digest": True, "automatic_scans": True,
        },
    }
    return table.get(normalize_tier(tier), table["free"])


def features_for(tier: str) -> Dict[str, bool]:
    """Canonical feature gates for a tier. Paid = pro/agency/developer.
    These mirror the enforcement points in the API and workers."""
    t = normalize_tier(tier)
    paid = t in PAID_TIERS
    return {
        "price_history_full": paid,     # free sees a short teaser window only
        "ai_summary": paid,             # Intelligence Pro (per-competitor AI report)
        "winning_products_full": paid,  # free sees top-3 without the "why"
        "gaps_full": paid,              # free sees top-3 titles without detail
        "comparison_full": paid,        # free sees diagnosis, not prescription
        "quick_wins_full": paid,        # free sees 2
        "playbook_full": paid,          # free sees 4 plays
        "action_items_full": paid,      # free sees 2
        "csv_export": paid,             # free: 403
        "realtime_alerts": paid,        # free: weekly teaser only
        "ai_digest": paid,              # weekly AI digest email
        "api_access": t in PAID_TIERS,  # api keys require a paid tier
        "team_seats": t == "agency",    # team invites are Agency-only
    }


def webhook_limits(tier: str) -> tuple:
    """(max_competitors, scan_interval_hours) written to user_profiles by the
    Stripe webhook handler. Derived from the canonical limits map."""
    lim = limits_for(tier)
    return lim["max_competitors"], lim["scan_hours"]


def watch_cap_for(tier: str) -> int:
    return limits_for(tier)["watch_cap"]
