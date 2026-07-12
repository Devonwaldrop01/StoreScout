"""Canonical plan-entitlement tests — the single source of truth in
app/services/entitlements.py, and that the four former copies now defer to it.

Covers every plan (free/pro/agency/developer) and every subscription state the
product uses (active, trialing, canceled-active-until-period-end, expired/
inactive, past_due, webhook-delayed, missing row)."""
import pytest

from app.services import entitlements as ent


# ── Tier normalization / fail-closed ───────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("free", "free"), ("pro", "pro"), ("agency", "agency"), ("developer", "developer"),
    ("PRO", "pro"), (" pro ", "pro"),
    (None, "free"), ("", "free"), ("enterprise", "free"), ("garbage", "free"),
])
def test_normalize_tier_fails_closed(raw, expected):
    assert ent.normalize_tier(raw) == expected


def test_resolve_tier_missing_row_is_free():
    assert ent.resolve_tier(None) == "free"
    assert ent.resolve_tier({}) == "free"
    assert ent.resolve_tier({"tier": "pro"}) == "pro"
    assert ent.resolve_tier({"tier": "bogus"}) == "free"


# ── Limits: exact numbers per tier (locks the matrix) ──────────────────────

def test_limits_free():
    l = ent.limits_for("free")
    assert l["max_competitors"] == 1
    assert l["scan_hours"] == 168
    assert l["history_days"] == 0
    assert l["watch_cap"] == 3
    assert l["ai_digest"] is False
    assert l["automatic_scans"] is True   # free is auto-weekly, NOT manual-only


def test_limits_pro():
    l = ent.limits_for("pro")
    assert (l["max_competitors"], l["scan_hours"], l["history_days"], l["watch_cap"]) == (10, 24, 90, 25)
    assert l["ai_digest"] is True


def test_limits_agency():
    l = ent.limits_for("agency")
    assert (l["max_competitors"], l["scan_hours"], l["history_days"], l["watch_cap"]) == (50, 12, 3650, 25)
    assert l["ai_digest"] is True


def test_limits_developer():
    l = ent.limits_for("developer")
    assert (l["max_competitors"], l["scan_hours"]) == (50, 12)
    assert l["history_days"] == 3650


def test_unknown_tier_gets_free_limits():
    assert ent.limits_for("mystery") == ent.limits_for("free")


# ── Feature gates ──────────────────────────────────────────────────────────

def test_free_features_all_locked_except_baseline():
    f = ent.features_for("free")
    for gated in ("ai_summary", "csv_export", "realtime_alerts", "api_access",
                  "team_seats", "price_history_full", "gaps_full", "comparison_full"):
        assert f[gated] is False, gated


@pytest.mark.parametrize("tier", ["pro", "agency", "developer"])
def test_paid_unlocks_core_features(tier):
    f = ent.features_for(tier)
    for feat in ("ai_summary", "csv_export", "realtime_alerts", "api_access",
                 "price_history_full", "gaps_full", "comparison_full", "winning_products_full"):
        assert f[feat] is True, f"{tier}:{feat}"


def test_team_seats_are_agency_only():
    assert ent.features_for("agency")["team_seats"] is True
    assert ent.features_for("pro")["team_seats"] is False
    assert ent.features_for("developer")["team_seats"] is False


def test_is_paid():
    assert ent.is_paid("free") is False
    assert all(ent.is_paid(t) for t in ("pro", "agency", "developer"))


# ── Subscription state resolution (every state the product uses) ───────────

@pytest.mark.parametrize("profile,expected", [
    (None, "none"),                                             # missing row
    ({"tier": "free"}, "none"),                                 # free, no sub
    ({"tier": "pro", "subscription_status": "active"}, "active"),
    ({"tier": "pro", "subscription_status": "trialing"}, "trialing"),
    ({"tier": "pro", "subscription_status": "past_due"}, "past_due"),
    ({"tier": "pro", "subscription_status": "canceled"}, "canceled"),   # active-until-period-end reads as canceled once Stripe flips it
    ({"tier": "free", "subscription_status": "inactive"}, "inactive"),  # after deletion/expiry
    ({"tier": "pro", "subscription_status": None}, "active"),           # webhook delay: paid tier, no status yet → treat active
])
def test_subscription_state(profile, expected):
    assert ent.subscription_state(profile) == expected


def test_past_due_retains_paid_tier_access():
    # Grace: a past_due Pro keeps Pro entitlements (webhook updates status, not tier)
    profile = {"tier": "pro", "subscription_status": "past_due"}
    assert ent.resolve_tier(profile) == "pro"
    assert ent.limits_for(ent.resolve_tier(profile))["max_competitors"] == 10
    assert ent.features_for(ent.resolve_tier(profile))["ai_summary"] is True


def test_webhook_delay_paid_tier_without_status_still_paid():
    # Checkout completed set tier=pro but the subscription.updated webhook hasn't
    # landed yet — the user must not be denied paid features in the gap.
    profile = {"tier": "pro"}
    assert ent.limits_for(ent.resolve_tier(profile))["max_competitors"] == 10


# ── The former duplicate maps now defer to the canonical source ────────────

def test_webhook_limits_match_canonical():
    for tier in ("free", "pro", "agency", "developer"):
        l = ent.limits_for(tier)
        assert ent.webhook_limits(tier) == (l["max_competitors"], l["scan_hours"])


def test_competitors_tier_limits_defers_to_entitlements():
    from app.api.v1.competitors import _tier_limits
    for tier in ("free", "pro", "agency", "developer"):
        assert _tier_limits(tier) == ent.limits_for(tier)


def test_webhook_tier_limits_defers_to_entitlements():
    from app.api.v1.webhooks import _tier_limits as wh_limits
    for tier in ("free", "pro", "agency", "developer"):
        assert wh_limits(tier) == ent.webhook_limits(tier)


def test_watch_cap_helper():
    assert ent.watch_cap_for("free") == 3
    assert ent.watch_cap_for("pro") == 25
    assert ent.watch_cap_for("bogus") == 3
