from __future__ import annotations
import logging
import stripe
from fastapi import APIRouter, HTTPException, Request
from app.core.config import get_settings
from app.core.database import get_supabase

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


TIER_MAP = {
    # stripe_price_id -> tier name — populated from env at runtime
}

def _get_tier_for_price(price_id: str) -> str:
    settings = get_settings()
    if price_id == settings.stripe_pro_price_id:
        return "pro"
    if price_id == settings.stripe_agency_price_id:
        return "agency"
    return "free"


def _tier_limits(tier: str):
    settings = get_settings()
    return {
        "pro": (settings.pro_max_competitors, settings.pro_scan_interval_hours),
        "agency": (settings.agency_max_competitors, settings.agency_scan_interval_hours),
    }.get(tier, (settings.free_max_competitors, settings.free_scan_interval_hours))


@router.post("/stripe-subscriptions")
async def stripe_subscription_webhook(request: Request):
    settings = get_settings()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except Exception as exc:
        logger.warning(f"Stripe webhook validation failed: {exc}")
        raise HTTPException(400, "Invalid signature")

    db = get_supabase()
    etype = event["type"]
    data = event["data"]["object"]

    if etype in ("customer.subscription.created", "customer.subscription.updated"):
        customer_id = data["customer"]
        status = data["status"]
        sub_id = data["id"]
        price_id = data["items"]["data"][0]["price"]["id"] if data.get("items") else ""
        tier = _get_tier_for_price(price_id)
        max_comp, scan_h = _tier_limits(tier)

        db.table("user_profiles").update({
            "tier": tier,
            "stripe_subscription_id": sub_id,
            "subscription_status": status,
            "max_competitors": max_comp,
            "scan_interval_hours": scan_h,
        }).eq("stripe_customer_id", customer_id).execute()

    elif etype == "customer.subscription.deleted":
        customer_id = data["customer"]
        db.table("user_profiles").update({
            "tier": "free",
            "subscription_status": "inactive",
            "max_competitors": 1,
            "scan_interval_hours": 168,
        }).eq("stripe_customer_id", customer_id).execute()

    elif etype == "customer.created":
        # Link Stripe customer ID to user profile via metadata
        customer_id = data["id"]
        metadata = data.get("metadata") or {}
        user_id = metadata.get("supabase_user_id")
        if user_id:
            db.table("user_profiles").update({"stripe_customer_id": customer_id}).eq("id", user_id).execute()

    return {"received": True}
