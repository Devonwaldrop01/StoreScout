from __future__ import annotations
import hashlib
import hmac as _hmac
import logging
import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from app.core.auth import get_current_user_id
from app.core.config import get_settings
from app.core.database import get_supabase

router = APIRouter(prefix="/shopify", tags=["shopify"])
logger = logging.getLogger(__name__)

# Scopes for the App Store install flow (minimal)
_INSTALL_SCOPES = "read_products,read_content"
# Scopes for the Connect flow (richer private data)
_CONNECT_SCOPES = "read_products,read_inventory,read_price_rules,read_discounts"


def _verify_hmac(params: dict, secret: str) -> bool:
    provided = params.get("hmac", "")
    filtered = {k: v for k, v in params.items() if k != "hmac"}
    message = "&".join(f"{k}={v}" for k, v in sorted(filtered.items()))
    digest = _hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return _hmac.compare_digest(digest, provided)


def _valid_shop(shop: str) -> bool:
    import re
    return bool(re.match(r"^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$", shop))


def _redis():
    import redis as _r
    settings = get_settings()
    return _r.from_url(settings.redis_url, socket_connect_timeout=2)


# ── App Store install flow (new user acquisition) ─────────────────────────────

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
        "scope": _INSTALL_SCOPES,
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
    """Step 2: Shopify redirects back — exchange code for access token."""
    settings = get_settings()
    if not settings.shopify_api_key or not settings.shopify_api_secret:
        raise HTTPException(503, "Shopify app not configured")

    if not _valid_shop(shop):
        raise HTTPException(400, "Invalid shop domain")

    raw_params = {"code": code, "shop": shop, "hmac": hmac, "state": state, "timestamp": timestamp}
    if not _verify_hmac(raw_params, settings.shopify_api_secret):
        raise HTTPException(403, "HMAC verification failed")

    try:
        resp = httpx.post(
            f"https://{shop}/admin/oauth/access_token",
            json={"client_id": settings.shopify_api_key, "client_secret": settings.shopify_api_secret, "code": code},
            timeout=15.0,
        )
        resp.raise_for_status()
        token_data = resp.json()
        access_token = token_data.get("access_token", "")
        scope = token_data.get("scope", "")
    except Exception as exc:
        logger.error("Shopify token exchange failed for %s: %s", shop, exc)
        raise HTTPException(502, "Could not obtain access token from Shopify")

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
    db.table("shopify_connections").upsert({
        "shop": shop, "access_token": access_token, "scope": scope,
        "shop_name": shop_name, "merchant_email": merchant_email,
        "connection_type": "install", "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="shop").execute()

    existing = db.table("shopify_connections").select("user_id").eq("shop", shop).maybe_single().execute()
    user_id = (existing.data or {}).get("user_id")

    if not user_id and merchant_email:
        try:
            users = db.auth.admin.list_users()
            user_id = next((u.id for u in (users or []) if (u.email or "").lower() == merchant_email), None)
        except Exception:
            user_id = None

        if not user_id:
            try:
                created = db.auth.admin.create_user({
                    "email": merchant_email, "email_confirm": True,
                    "app_metadata": {"shopify_shop": shop},
                })
                user_id = created.user.id if created.user else None
            except Exception as exc:
                logger.error("Could not create Supabase user for %s: %s", shop, exc)

        if user_id:
            db.table("shopify_connections").update({"user_id": user_id}).eq("shop", shop).execute()
            try:
                db.table("user_profiles").upsert({
                    "id": user_id, "email": merchant_email, "tier": "free",
                    "max_competitors": 1, "scan_interval_hours": 168, "subscription_status": "inactive",
                }, on_conflict="id").execute()
            except Exception:
                pass

    if user_id and merchant_email:
        try:
            link = db.auth.admin.generate_link({
                "type": "magiclink", "email": merchant_email,
                "options": {"redirect_to": f"{settings.public_base_url}/dashboard"},
            })
            action_link = link.properties.action_link if link and link.properties else None
            if action_link:
                return RedirectResponse(action_link, status_code=302)
        except Exception as exc:
            logger.warning("Magic link generation failed for %s: %s", merchant_email, exc)

    return RedirectResponse(f"{settings.public_base_url}/auth/sign-in", status_code=302)


# ── Connect flow (existing StoreScout user links their store) ─────────────────

@router.get("/connect-url")
def connect_url(
    shop: str = Query(...),
    user_id: str = Depends(get_current_user_id),
):
    """Return the Shopify OAuth URL for an existing logged-in user.
    Stores user_id in Redis keyed by state token (10-min TTL).
    Frontend redirects the browser to the returned URL.
    """
    if not _valid_shop(shop):
        raise HTTPException(400, "Invalid shop domain — must be yourstore.myshopify.com")

    settings = get_settings()
    if not settings.shopify_api_key:
        raise HTTPException(503, "Shopify app not configured")

    state = secrets.token_hex(16)
    try:
        r = _redis()
        r.setex(f"shopify_oauth_state:{state}", 600, user_id)
    except Exception as exc:
        logger.warning("Redis unavailable for shopify state storage: %s", exc)
        # Without Redis we can't safely complete the flow
        raise HTTPException(503, "OAuth state storage unavailable — try again shortly")

    params = urlencode({
        "client_id": settings.shopify_api_key,
        "scope": _CONNECT_SCOPES,
        "redirect_uri": f"{settings.public_base_url}/api/v1/shopify/connect-callback",
        "state": state,
    })
    return {"url": f"https://{shop}/admin/oauth/authorize?{params}"}


@router.get("/connect-callback")
def connect_callback(
    code: str = Query(...),
    shop: str = Query(...),
    hmac: str = Query(...),
    state: str = Query(default=""),
    timestamp: str = Query(default=""),
):
    """Shopify redirects here after user approves the connect flow."""
    settings = get_settings()
    if not settings.shopify_api_key or not settings.shopify_api_secret:
        raise HTTPException(503, "Shopify app not configured")

    if not _valid_shop(shop):
        raise HTTPException(400, "Invalid shop domain")

    raw_params = {"code": code, "shop": shop, "hmac": hmac, "state": state, "timestamp": timestamp}
    if not _verify_hmac(raw_params, settings.shopify_api_secret):
        raise HTTPException(403, "HMAC verification failed")

    # Exchange code for access token
    try:
        resp = httpx.post(
            f"https://{shop}/admin/oauth/access_token",
            json={"client_id": settings.shopify_api_key, "client_secret": settings.shopify_api_secret, "code": code},
            timeout=15.0,
        )
        resp.raise_for_status()
        token_data = resp.json()
        access_token = token_data.get("access_token", "")
        scope = token_data.get("scope", "")
    except Exception as exc:
        logger.error("Shopify connect token exchange failed for %s: %s", shop, exc)
        return RedirectResponse(f"{settings.public_base_url}/settings?error=token_exchange_failed", status_code=302)

    # Fetch shop info
    shop_name = shop
    try:
        shop_resp = httpx.get(
            f"https://{shop}/admin/api/2024-01/shop.json",
            headers={"X-Shopify-Access-Token": access_token},
            timeout=10.0,
        )
        if shop_resp.status_code == 200:
            shop_info = shop_resp.json().get("shop", {})
            shop_name = shop_info.get("name", shop)
    except Exception:
        pass

    # Recover user_id from Redis state
    user_id = None
    try:
        r = _redis()
        raw = r.get(f"shopify_oauth_state:{state}")
        user_id = raw.decode() if raw else None
        r.delete(f"shopify_oauth_state:{state}")
    except Exception as exc:
        logger.warning("Redis unavailable reading shopify state: %s", exc)

    if not user_id:
        logger.error("connect-callback: no user_id found for state %s (shop %s)", state, shop)
        return RedirectResponse(f"{settings.public_base_url}/settings?error=session_expired", status_code=302)

    db = get_supabase()

    # Store / update connection
    db.table("shopify_connections").upsert({
        "shop": shop, "user_id": user_id, "access_token": access_token,
        "scope": scope, "shop_name": shop_name, "connection_type": "connect",
        "uninstalled_at": None, "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="shop").execute()

    # Create / update is_my_store competitor row
    store_url = f"https://{shop}"
    existing = (
        db.table("competitors").select("id")
        .eq("user_id", user_id).eq("is_my_store", True)
        .maybe_single().execute()
    )
    if existing and existing.data:
        store_id = existing.data["id"]
        db.table("competitors").update({
            "store_url": store_url, "hostname": shop,
            "display_name": shop_name, "shopify_shop": shop,
            "scan_status": "pending", "error_message": None,
        }).eq("id", store_id).execute()
    else:
        row = db.table("competitors").insert({
            "user_id": user_id, "store_url": store_url, "hostname": shop,
            "display_name": shop_name, "is_my_store": True,
            "shopify_shop": shop, "scan_status": "pending",
        }).execute()
        store_id = row.data[0]["id"]

    try:
        from app.tasks.scan import scan_competitor
        scan_competitor.apply_async(args=[store_id], queue="priority")
    except Exception as exc:
        logger.warning("Could not enqueue scan for shopify-connected store %s: %s", store_id, exc)

    return RedirectResponse(f"{settings.public_base_url}/settings?connected=true", status_code=302)


@router.get("/connection")
def get_connection(user_id: str = Depends(get_current_user_id)):
    """Return the user's connected Shopify store (if any)."""
    db = get_supabase()
    result = (
        db.table("shopify_connections")
        .select("shop, shop_name, scope, created_at")
        .eq("user_id", user_id)
        .is_("uninstalled_at", "null")
        .maybe_single()
        .execute()
    )
    return {"data": result.data if result else None}


@router.delete("/connection", status_code=204)
def delete_connection(user_id: str = Depends(get_current_user_id)):
    """Disconnect the user's Shopify store."""
    db = get_supabase()
    # Mark as uninstalled rather than deleting (preserves audit trail)
    db.table("shopify_connections").update({
        "uninstalled_at": datetime.now(timezone.utc).isoformat(),
    }).eq("user_id", user_id).execute()
    # Also remove the is_my_store competitor row
    db.table("competitors").delete().eq("user_id", user_id).eq("is_my_store", True).execute()


# ── GDPR Webhooks (mandatory for App Store listing) ───────────────────────────

async def _verify_webhook_hmac(request: Request, secret: str) -> bool:
    body = await request.body()
    provided = request.headers.get("X-Shopify-Hmac-Sha256", "")
    import base64
    digest = base64.b64encode(
        _hmac.new(secret.encode(), body, hashlib.sha256).digest()
    ).decode()
    return _hmac.compare_digest(digest, provided)


@router.post("/webhooks/customers/data_request")
async def customers_data_request(request: Request):
    settings = get_settings()
    if settings.shopify_api_secret:
        if not await _verify_webhook_hmac(request, settings.shopify_api_secret):
            raise HTTPException(401, "Invalid webhook HMAC")
    return {"acknowledged": True}


@router.post("/webhooks/customers/redact")
async def customers_redact(request: Request):
    settings = get_settings()
    if settings.shopify_api_secret:
        if not await _verify_webhook_hmac(request, settings.shopify_api_secret):
            raise HTTPException(401, "Invalid webhook HMAC")
    return {"acknowledged": True}


@router.post("/webhooks/shop/redact")
async def shop_redact(request: Request):
    settings = get_settings()
    if settings.shopify_api_secret:
        if not await _verify_webhook_hmac(request, settings.shopify_api_secret):
            raise HTTPException(401, "Invalid webhook HMAC")
    try:
        body = await request.json()
        shop = body.get("myshopify_domain", "")
        if shop:
            db = get_supabase()
            db.table("shopify_connections").update({
                "uninstalled_at": datetime.now(timezone.utc).isoformat(),
            }).eq("shop", shop).execute()
    except Exception as exc:
        logger.warning("shop/redact cleanup failed: %s", exc)
    return {"acknowledged": True}
