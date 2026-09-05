from __future__ import annotations
import logging
from typing import Literal

import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.core.config import get_settings
from app.core.database import get_supabase

router = APIRouter(prefix="/billing", tags=["billing"])
logger = logging.getLogger(__name__)


class CheckoutRequest(BaseModel):
    plan: Literal["pro", "agency", "developer"]
    billing: Literal["monthly", "annual"] = "monthly"


def _price_id_for_plan(plan: str, billing: str, settings) -> str:
    annual = billing == "annual"
    if plan == "pro":
        return settings.stripe_pro_annual_price_id if annual else settings.stripe_pro_price_id
    if plan == "agency":
        return settings.stripe_agency_annual_price_id if annual else settings.stripe_agency_price_id
    if plan == "developer":
        return settings.stripe_developer_annual_price_id if annual else settings.stripe_developer_price_id
    raise HTTPException(400, "Invalid plan")


def _get_or_create_stripe_customer(db, user_id: str, email: str, settings) -> str:
    """Return the Stripe customer_id, creating one if needed."""
    user = db.table("user_profiles").select("stripe_customer_id, email").eq("id", user_id).maybe_single().execute()
    existing_cid = (user.data or {}).get("stripe_customer_id") or ""
    if existing_cid:
        return existing_cid

    stripe.api_key = settings.stripe_secret_key
    customer = stripe.Customer.create(
        email=email,
        metadata={"supabase_user_id": user_id},
        idempotency_key=f"storescout-customer-{user_id}",
    )
    db.table("user_profiles").update({"stripe_customer_id": customer["id"]}).eq("id", user_id).execute()
    return customer["id"]


def _get_user_email(db, user_id: str) -> str:
    user = db.table("user_profiles").select("email").eq("id", user_id).maybe_single().execute()
    email = ((user.data or {}).get("email") or "").strip()
    if not email:
        try:
            auth_user = db.auth.admin.get_user_by_id(user_id)
            email = (auth_user.user.email or "").strip() if auth_user.user else ""
        except Exception:
            pass
    return email


@router.post("/checkout")
def create_checkout(body: CheckoutRequest, user_id: str = Depends(get_current_user_id)):
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key

    price_id = _price_id_for_plan(body.plan, body.billing, settings)
    if not price_id:
        raise HTTPException(400, f"No Stripe price configured for {body.plan}/{body.billing}")

    db = get_supabase()
    email = _get_user_email(db, user_id)
    customer_id = _get_or_create_stripe_customer(db, user_id, email, settings)

    # Existing subscribers manage their subscription in the portal. Consult
    # Stripe as well as local state so delayed webhooks cannot invite rebilling.
    try:
        subscriptions = stripe.Subscription.list(customer=customer_id, status="all", limit=100)
        if subscriptions.get("has_more") or any(
            sub.get("status") not in {"canceled", "incomplete_expired"}
            for sub in subscriptions.get("data", [])
        ):
            raise HTTPException(409, "A subscription already exists. Use Manage billing in Settings.")
    except stripe.StripeError as exc:
        raise HTTPException(503, "Could not verify your billing account. Please try again.") from exc

    frontend_base = settings.public_base_url
    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{frontend_base}/settings?upgraded=1",
            cancel_url=f"{frontend_base}/settings?upgraded=0",
            metadata={"supabase_user_id": user_id, "plan": body.plan},
            subscription_data={"metadata": {"supabase_user_id": user_id}},
            allow_promotion_codes=True,
        )
    except stripe.StripeError as exc:
        logger.error("Stripe checkout creation failed for user %s: %s", user_id, exc)
        raise HTTPException(502, f"Stripe error: {exc.user_message or str(exc)}")

    return {"url": session.url}


@router.post("/portal")
def create_portal(user_id: str = Depends(get_current_user_id)):
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key

    db = get_supabase()
    user = db.table("user_profiles").select("stripe_customer_id").eq("id", user_id).maybe_single().execute()
    customer_id = ((user.data or {}).get("stripe_customer_id") or "").strip()
    if not customer_id:
        raise HTTPException(400, "No billing account found. Please subscribe first.")

    frontend_base = settings.public_base_url
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{frontend_base}/settings",
        )
    except stripe.StripeError as exc:
        logger.error("Stripe portal creation failed for user %s: %s", user_id, exc)
        raise HTTPException(502, f"Stripe error: {exc.user_message or str(exc)}")

    return {"url": session.url}
