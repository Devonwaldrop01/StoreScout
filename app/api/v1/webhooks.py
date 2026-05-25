from __future__ import annotations
import logging
import stripe
from fastapi import APIRouter, HTTPException, Request
from app.core.config import get_settings
from app.core.database import get_supabase

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

# Statuses where a subscription is considered fully active
_ACTIVE_STATUSES = {"active", "trialing"}


def _get_tier_for_price(price_id: str) -> str:
    """Map a Stripe price ID to an internal tier name. Checks both monthly and annual variants."""
    settings = get_settings()
    if price_id and price_id in (settings.stripe_pro_price_id, settings.stripe_pro_annual_price_id):
        return "pro"
    if price_id and price_id in (settings.stripe_agency_price_id, settings.stripe_agency_annual_price_id):
        return "agency"
    if price_id and price_id in (settings.stripe_developer_price_id, settings.stripe_developer_annual_price_id):
        return "developer"
    return "free"


def _tier_limits(tier: str):
    settings = get_settings()
    return {
        "pro": (settings.pro_max_competitors, settings.pro_scan_interval_hours),
        "agency": (settings.agency_max_competitors, settings.agency_scan_interval_hours),
        "developer": (50, 12),
    }.get(tier, (settings.free_max_competitors, settings.free_scan_interval_hours))


def _apply_tier(db, *, user_id: str | None = None, customer_id: str | None = None,
                tier: str, status: str, sub_id: str | None = None):
    """Write tier + limits to user_profiles. Looks up by user_id or stripe customer_id."""
    max_comp, scan_h = _tier_limits(tier)
    update: dict = {
        "tier": tier,
        "subscription_status": status,
        "max_competitors": max_comp,
        "scan_interval_hours": scan_h,
    }
    if sub_id:
        update["stripe_subscription_id"] = sub_id

    if user_id:
        db.table("user_profiles").update(update).eq("id", user_id).execute()
    elif customer_id:
        db.table("user_profiles").update(update).eq("stripe_customer_id", customer_id).execute()


@router.post("/stripe-subscriptions")
async def stripe_subscription_webhook(request: Request):
    settings = get_settings()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except Exception as exc:
        logger.warning("Stripe webhook validation failed: %s", exc)
        raise HTTPException(400, "Invalid signature")

    db = get_supabase()
    etype = event["type"]
    data = event["data"]["object"]

    try:
        _handle_event(db, etype, data)
    except Exception as exc:
        # Log and swallow — always ACK to Stripe so it stops retrying.
        # Individual handler bugs should not cause aggressive retry storms.
        logger.exception("Unhandled error processing Stripe event %s: %s", etype, exc)

    return {"received": True}


def _handle_event(db, etype: str, data: dict):
    # ── Checkout completed: immediate tier update using session metadata ──────
    if etype == "checkout.session.completed":
        if data.get("mode") == "subscription" and data.get("payment_status") == "paid":
            meta = data.get("metadata") or {}
            user_id = meta.get("supabase_user_id")
            plan = meta.get("plan")
            sub_id = data.get("subscription") or ""
            customer_id = data.get("customer") or ""

            if user_id and plan in ("pro", "agency", "developer"):
                logger.info("checkout.session.completed: upgrading user %s to %s", user_id, plan)
                _apply_tier(db, user_id=user_id, tier=plan, status="active", sub_id=sub_id)
                # Also ensure customer_id is linked
                if customer_id:
                    db.table("user_profiles").update(
                        {"stripe_customer_id": customer_id}
                    ).eq("id", user_id).execute()

    # ── Subscription created / updated ────────────────────────────────────────
    elif etype in ("customer.subscription.created", "customer.subscription.updated"):
        customer_id = data["customer"]
        status = data["status"]
        sub_id = data["id"]
        price_id = ""
        items = data.get("items") or {}
        item_list = items.get("data") or []
        if item_list:
            price_id = (item_list[0].get("price") or {}).get("id") or ""

        tier = _get_tier_for_price(price_id)

        if status in _ACTIVE_STATUSES:
            # Active subscription — set tier + limits
            logger.info("subscription %s: setting customer %s to tier=%s status=%s", sub_id, customer_id, tier, status)
            _apply_tier(db, customer_id=customer_id, tier=tier, status=status, sub_id=sub_id)
        else:
            # incomplete / past_due / etc. — update status only; don't change tier
            # (avoid granting or revoking access for transient states)
            logger.info("subscription %s: status=%s (no tier change)", sub_id, status)
            db.table("user_profiles").update({
                "stripe_subscription_id": sub_id,
                "subscription_status": status,
            }).eq("stripe_customer_id", customer_id).execute()

    # ── Subscription deleted / cancelled ─────────────────────────────────────
    elif etype == "customer.subscription.deleted":
        customer_id = data["customer"]
        settings = get_settings()
        logger.info("subscription deleted for customer %s — reverting to free", customer_id)
        _apply_tier(db, customer_id=customer_id, tier="free", status="inactive")

    # ── Customer created: back-fill customer_id if not already linked ─────────
    elif etype == "customer.created":
        customer_id = data["id"]
        meta = data.get("metadata") or {}
        user_id = meta.get("supabase_user_id")
        if user_id:
            db.table("user_profiles").update(
                {"stripe_customer_id": customer_id}
            ).eq("id", user_id).execute()
