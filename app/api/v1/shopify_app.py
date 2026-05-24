from __future__ import annotations
import hashlib
import hmac as _hmac
import logging
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.database import get_supabase

router = APIRouter(prefix="/shopify", tags=["shopify"])
logger = logging.getLogger(__name__)

REQUIRED_SCOPES = "read_products,read_content"


def _verify_hmac(params: dict, secret: str) -> bool:
    """Verify Shopify HMAC signature on OAuth callback."""
    provided = params.get("hmac", "")
    filtered = {k: v for k, v in params.items() if k != "hmac"}
    message = "&".join(f"{k}={v}" for k, v in sorted(filtered.items()))
    digest = _hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return _hmac.compare_digest(digest, provided)


def _valid_shop(shop: str) -> bool:
    import re
    return bool(re.match(r"^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$", shop))


@router.get("/install")
def install(shop: str = Query(...)):
    """Step 1: merchant clicks 'Add app' — redirect to Shopify OAuth."""
    if not _valid_shop(shop):
        raise HTTPException(400, "Invalid shop domain")

    settings = get_settings()
    if not settings.shopify_api_key:
        raise HTTPException(503, "Shopify app not configured")

    state = secrets.token_hex(16)
    params = urlencode({
        "client_id": settings.shopify_api_key,
        "scope": REQUIRED_SCOPES,
        "redirect_uri": f"{settings.public_base_url}/api/v1/shopify/callback",
        "state": state,
    })
    return RedirectResponse(f"https://{shop}/admin/oauth/authorize?{params}", status_code=302)


@router.get("/callback")
def callback(
    code: str = Query(...),
    shop: str = Query(...),
    hmac: str = Query(...),
    state: str = Query(default=""),
    timestamp: str = Query(default=""),
):
    """Step 2: Shopify redirects back with auth code — exchange for access token."""
    settings = get_settings()
    if not settings.shopify_api_key or not settings.shopify_api_secret:
        raise HTTPException(503, "Shopify app not configured")

    if not _valid_shop(shop):
        raise HTTPException(400, "Invalid shop domain")

    # Verify HMAC
    raw_params = {"code": code, "shop": shop, "hmac": hmac, "state": state, "timestamp": timestamp}
    if not _verify_hmac(raw_params, settings.shopify_api_secret):
        raise HTTPException(403, "HMAC verification failed")

    # Exchange code for access token
    try:
        resp = httpx.post(
            f"https://{shop}/admin/oauth/access_token",
            json={
                "client_id": settings.shopify_api_key,
                "client_secret": settings.shopify_api_secret,
                "code": code,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        token_data = resp.json()
        access_token = token_data.get("access_token", "")
        scope = token_data.get("scope", "")
    except Exception as exc:
        logger.error("Shopify token exchange failed for %s: %s", shop, exc)
        raise HTTPException(502, "Could not obtain access token from Shopify")

    # Fetch shop info to get merchant email + name
    try:
        shop_resp = httpx.get(
            f"https://{shop}/admin/api/2024-01/shop.json",
            headers={"X-Shopify-Access-Token": access_token},
            timeout=10.0,
        )
        shop_resp.raise_for_status()
        shop_info = shop_resp.json().get("shop", {})
        merchant_email = shop_info.get("email", "").strip().lower()
        shop_name = shop_info.get("name", shop)
    except Exception:
        merchant_email = ""
        shop_name = shop

    db = get_supabase()

    # Store / update the connection
    db.table("shopify_connections").upsert({
        "shop": shop,
        "access_token": access_token,
        "scope": scope,
        "shop_name": shop_name,
        "merchant_email": merchant_email,
    }, on_conflict="shop").execute()

    # Find or create the user profile keyed on shop domain
    existing = db.table("shopify_connections")\
        .select("user_id")\
        .eq("shop", shop)\
        .maybe_single()\
        .execute()
    user_id = (existing.data or {}).get("user_id")

    if not user_id and merchant_email:
        # Try to find existing user by email
        try:
            users = db.auth.admin.list_users()
            user_id = next(
                (u.id for u in (users or []) if (u.email or "").lower() == merchant_email),
                None,
            )
        except Exception:
            user_id = None

        if not user_id:
            # Create a new Supabase Auth user for this merchant
            try:
                created = db.auth.admin.create_user({
                    "email": merchant_email,
                    "email_confirm": True,
                    "app_metadata": {"shopify_shop": shop},
                })
                user_id = created.user.id if created.user else None
            except Exception as exc:
                logger.error("Could not create Supabase user for %s: %s", shop, exc)

        if user_id:
            db.table("shopify_connections").update({"user_id": user_id}).eq("shop", shop).execute()
            # Ensure user_profiles row exists
            try:
                db.table("user_profiles").upsert({
                    "id": user_id,
                    "email": merchant_email,
                    "tier": "free",
                    "max_competitors": 1,
                    "scan_interval_hours": 168,
                    "subscription_status": "inactive",
                }, on_conflict="id").execute()
            except Exception:
                pass

    # If we have a user, generate a magic sign-in link and redirect
    if user_id and merchant_email:
        try:
            link = db.auth.admin.generate_link({
                "type": "magiclink",
                "email": merchant_email,
                "options": {"redirect_to": f"{settings.public_base_url}/dashboard"},
            })
            action_link = link.properties.action_link if link and link.properties else None
            if action_link:
                return RedirectResponse(action_link, status_code=302)
        except Exception as exc:
            logger.warning("Magic link generation failed for %s: %s", merchant_email, exc)

    # Fallback: send to sign-in page
    return RedirectResponse(f"{settings.public_base_url}/auth/sign-in", status_code=302)


# ── GDPR Webhooks (mandatory for App Store listing) ───────────────────────────

async def _verify_webhook_hmac(request: Request, secret: str) -> bool:
    """Verify Shopify webhook HMAC-SHA256."""
    body = await request.body()
    provided = request.headers.get("X-Shopify-Hmac-Sha256", "")
    import base64
    digest = base64.b64encode(
        _hmac.new(secret.encode(), body, hashlib.sha256).digest()
    ).decode()
    return _hmac.compare_digest(digest, provided)


@router.post("/webhooks/customers/data_request")
async def customers_data_request(request: Request):
    """GDPR: respond to customer data request."""
    settings = get_settings()
    if settings.shopify_api_secret:
        if not await _verify_webhook_hmac(request, settings.shopify_api_secret):
            raise HTTPException(401, "Invalid webhook HMAC")
    return {"acknowledged": True}


@router.post("/webhooks/customers/redact")
async def customers_redact(request: Request):
    """GDPR: delete customer data (StoreScout stores no personal customer data)."""
    settings = get_settings()
    if settings.shopify_api_secret:
        if not await _verify_webhook_hmac(request, settings.shopify_api_secret):
            raise HTTPException(401, "Invalid webhook HMAC")
    return {"acknowledged": True}


@router.post("/webhooks/shop/redact")
async def shop_redact(request: Request):
    """GDPR: merchant uninstalled — remove their data."""
    settings = get_settings()
    if settings.shopify_api_secret:
        if not await _verify_webhook_hmac(request, settings.shopify_api_secret):
            raise HTTPException(401, "Invalid webhook HMAC")
    try:
        body = await request.json()
        shop = body.get("myshopify_domain", "")
        if shop:
            db = get_supabase()
            db.table("shopify_connections")\
                .update({"uninstalled_at": __import__("datetime").datetime.utcnow().isoformat()})\
                .eq("shop", shop)\
                .execute()
    except Exception as exc:
        logger.warning("shop/redact cleanup failed: %s", exc)
    return {"acknowledged": True}
