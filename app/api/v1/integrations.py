from __future__ import annotations
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode, quote

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.core.database import get_supabase

router = APIRouter(prefix="/integrations", tags=["integrations"])
logger = logging.getLogger(__name__)

_KLAVIYO_BASE = "https://a.klaviyo.com/api"
_KLAVIYO_REVISION = "2024-02-15"


def _klaviyo_headers(api_key: str) -> dict:
    return {"Authorization": f"Klaviyo-API-Key {api_key}", "revision": _KLAVIYO_REVISION}


def _mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return "****"
    return key[:6] + "****" + key[-4:]


def _get_integration_row(user_id: str) -> dict:
    db = get_supabase()
    result = db.table("user_integrations").select("*").eq("user_id", user_id).maybe_single().execute()
    return result.data or {}


# ── GET /integrations ──────────────────────────────────────────────────────────

@router.get("")
def get_integrations(user_id: str = Depends(get_current_user_id)):
    """Return integration status for the current user (keys masked)."""
    row = _get_integration_row(user_id)
    klaviyo_key = row.get("klaviyo_api_key") or ""
    return {
        "data": {
            "klaviyo": {
                "connected": bool(klaviyo_key),
                "key_preview": _mask_key(klaviyo_key) if klaviyo_key else None,
            }
        }
    }


# ── Klaviyo ────────────────────────────────────────────────────────────────────

class KlaviyoKeyRequest(BaseModel):
    api_key: str


@router.put("/klaviyo")
def save_klaviyo_key(body: KlaviyoKeyRequest, user_id: str = Depends(get_current_user_id)):
    """Store a Klaviyo private API key for this user."""
    key = body.api_key.strip()
    if not key:
        raise HTTPException(400, "api_key is required")

    db = get_supabase()
    db.table("user_integrations").upsert({
        "user_id": user_id,
        "klaviyo_api_key": key,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id").execute()

    return {"data": {"connected": True, "key_preview": _mask_key(key)}}


@router.delete("/klaviyo", status_code=204)
def remove_klaviyo_key(user_id: str = Depends(get_current_user_id)):
    """Remove Klaviyo key for this user."""
    db = get_supabase()
    db.table("user_integrations").update({
        "klaviyo_api_key": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("user_id", user_id).execute()


@router.post("/klaviyo/test")
def test_klaviyo(user_id: str = Depends(get_current_user_id)):
    """Test the stored Klaviyo key — returns list count and total profiles."""
    row = _get_integration_row(user_id)
    api_key = row.get("klaviyo_api_key") or ""
    if not api_key:
        raise HTTPException(400, "No Klaviyo key saved")

    try:
        resp = httpx.get(
            f"{_KLAVIYO_BASE}/lists/",
            headers=_klaviyo_headers(api_key),
            # profile_count is a relationship field Klaviyo omits unless explicitly requested
            params={"page[size]": 100, "additional-fields[list]": "profile_count"},
            timeout=10.0,
        )
        resp.raise_for_status()
        lists_data = resp.json().get("data", [])
        list_count = len(lists_data)
        total_profiles = sum(
            (item.get("attributes", {}).get("profile_count") or 0)
            for item in lists_data
        )
        return {
            "status": "ok",
            "list_count": list_count,
            "total_profiles": total_profiles,
            "lists": [
                {
                    "name": item.get("attributes", {}).get("name", ""),
                    "profile_count": item.get("attributes", {}).get("profile_count") or 0,
                }
                for item in lists_data[:5]
            ],
        }
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            raise HTTPException(401, "Invalid Klaviyo API key")
        raise HTTPException(502, f"Klaviyo API error: {exc.response.status_code}")
    except Exception as exc:
        logger.error("Klaviyo test failed for user %s: %s", user_id, exc)
        raise HTTPException(502, "Could not reach Klaviyo API")


# ── Helper used by playbook_ai.py ─────────────────────────────────────────────

def get_klaviyo_context(user_id: str) -> Optional[str]:
    """Fetch Klaviyo list data and return a one-line context string for the AI prompt.
    Returns None if no key or API call fails."""
    row = _get_integration_row(user_id)
    api_key = row.get("klaviyo_api_key") or ""
    if not api_key:
        return None

    try:
        resp = httpx.get(
            f"{_KLAVIYO_BASE}/lists/",
            headers=_klaviyo_headers(api_key),
            # profile_count is a relationship field Klaviyo omits unless explicitly requested
            params={"page[size]": 100, "additional-fields[list]": "profile_count"},
            timeout=8.0,
        )
        resp.raise_for_status()
        lists_data = resp.json().get("data", [])
        if not lists_data:
            return None

        total_profiles = sum(
            (item.get("attributes", {}).get("profile_count") or 0)
            for item in lists_data
        )
        list_count = len(lists_data)
        largest = max(lists_data, key=lambda x: x.get("attributes", {}).get("profile_count") or 0)
        largest_name = largest.get("attributes", {}).get("name", "")
        largest_count = largest.get("attributes", {}).get("profile_count") or 0

        parts = [f"Email list: {total_profiles:,} subscribers across {list_count} list{'s' if list_count != 1 else ''}"]
        if largest_name and list_count > 1:
            parts.append(f"largest list: \"{largest_name}\" ({largest_count:,} subscribers)")

        # Recent email campaign cadence — tells the AI how active their email program is
        # and when they last sent, so it can recommend timing realistically.
        try:
            camp_resp = httpx.get(
                f"{_KLAVIYO_BASE}/campaigns/",
                headers=_klaviyo_headers(api_key),
                # channel filter is required by the campaigns endpoint
                params={"filter": "equals(messages.channel,'email')", "sort": "-created_at", "page[size]": 20},
                timeout=8.0,
            )
            if camp_resp.status_code == 200:
                camps = camp_resp.json().get("data", [])
                cutoff = datetime.now(timezone.utc) - timedelta(days=30)
                recent = 0
                last_send: Optional[datetime] = None
                for c in camps:
                    attrs = c.get("attributes", {})
                    raw = attrs.get("send_time") or attrs.get("scheduled_at") or attrs.get("created_at")
                    if not raw:
                        continue
                    try:
                        sent = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                    except Exception:
                        continue
                    if sent >= cutoff:
                        recent += 1
                    if last_send is None or sent > last_send:
                        last_send = sent
                if last_send:
                    days_ago = max(0, (datetime.now(timezone.utc) - last_send).days)
                    parts.append(f"email cadence: {recent} campaign{'s' if recent != 1 else ''} in last 30d, last sent {days_ago}d ago")
        except Exception as _ce:
            logger.debug("Klaviyo campaign cadence fetch failed for user %s: %s", user_id, _ce)

        return " · ".join(parts)
    except Exception as exc:
        logger.debug("Klaviyo context fetch failed for user %s: %s", user_id, exc)
        return None


# ── Google OAuth (GA4 + Search Console) ───────────────────────────────────────

_GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_SCOPES = " ".join([
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
    "openid email",
])


def _get_google_settings():
    from app.core.config import get_settings
    return get_settings()


def _redis():
    import redis as _r
    return _r.from_url(_get_google_settings().redis_url, socket_connect_timeout=2)


def _google_access_token(row: dict) -> Optional[str]:
    """Return a valid access token, refreshing if needed. Updates DB row in-place."""
    access_token = row.get("google_access_token") or ""
    refresh_token = row.get("google_refresh_token") or ""
    expiry_raw = row.get("google_token_expiry")

    if not access_token and not refresh_token:
        return None

    # Refresh if expired or within 5 minutes of expiry
    needs_refresh = True
    if expiry_raw:
        try:
            expiry = datetime.fromisoformat(expiry_raw.replace("Z", "+00:00"))
            needs_refresh = expiry < datetime.now(timezone.utc) + timedelta(minutes=5)
        except Exception:
            pass

    if needs_refresh and refresh_token:
        settings = _get_google_settings()
        try:
            resp = httpx.post(_GOOGLE_TOKEN_URL, data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            access_token = data["access_token"]
            expiry = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
            # Update DB
            user_id = row.get("user_id")
            if user_id:
                get_supabase().table("user_integrations").update({
                    "google_access_token": access_token,
                    "google_token_expiry": expiry.isoformat(),
                }).eq("user_id", user_id).execute()
            row["google_access_token"] = access_token
        except Exception as exc:
            logger.warning("Google token refresh failed: %s", exc)
            return None

    return access_token or None


@router.get("/google/connect-url")
def google_connect_url(user_id: str = Depends(get_current_user_id)):
    """Return a Google OAuth URL. Stores user_id in Redis keyed by state (10-min TTL)."""
    settings = _get_google_settings()
    if not settings.google_client_id:
        raise HTTPException(503, "Google integration not configured")

    state = secrets.token_hex(16)
    try:
        r = _redis()
        r.setex(f"google_oauth_state:{state}", 600, user_id)
    except Exception as exc:
        logger.warning("Redis unavailable for Google state: %s", exc)
        raise HTTPException(503, "OAuth state storage unavailable")

    params = urlencode({
        "client_id": settings.google_client_id,
        "redirect_uri": f"{settings.public_base_url}/api/v1/integrations/google/callback",
        "response_type": "code",
        "scope": _GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })
    return {"url": f"{_GOOGLE_AUTH_URL}?{params}"}


@router.get("/google/callback")
def google_callback(code: str = "", state: str = "", error: str = ""):
    """Google redirects here after user approves OAuth."""
    settings = _get_google_settings()

    if error or not code:
        return RedirectResponse(
            f"{settings.public_base_url}/settings?google_error={error or 'cancelled'}",
            status_code=302,
        )

    # Recover user_id from Redis
    user_id = None
    try:
        r = _redis()
        raw = r.get(f"google_oauth_state:{state}")
        user_id = raw.decode() if raw else None
        r.delete(f"google_oauth_state:{state}")
    except Exception as exc:
        logger.warning("Redis unavailable reading Google state: %s", exc)

    if not user_id:
        return RedirectResponse(
            f"{settings.public_base_url}/settings?google_error=session_expired",
            status_code=302,
        )

    # Exchange code for tokens
    try:
        resp = httpx.post(_GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": f"{settings.public_base_url}/api/v1/integrations/google/callback",
            "grant_type": "authorization_code",
        }, timeout=15.0)
        resp.raise_for_status()
        token_data = resp.json()
    except Exception as exc:
        logger.error("Google token exchange failed: %s", exc)
        return RedirectResponse(
            f"{settings.public_base_url}/settings?google_error=token_exchange_failed",
            status_code=302,
        )

    access_token  = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in    = token_data.get("expires_in", 3600)
    expiry        = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    db = get_supabase()
    db.table("user_integrations").upsert({
        "user_id": user_id,
        "google_access_token": access_token,
        "google_refresh_token": refresh_token or None,
        "google_token_expiry": expiry.isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id").execute()

    return RedirectResponse(
        f"{settings.public_base_url}/settings?google_connected=true",
        status_code=302,
    )


@router.get("/google/properties")
def google_properties(user_id: str = Depends(get_current_user_id)):
    """List available GA4 properties and GSC sites for the connected Google account."""
    db = get_supabase()
    row_res = db.table("user_integrations").select("*").eq("user_id", user_id).maybe_single().execute()
    row = (row_res.data or {}) if row_res else {}
    row["user_id"] = user_id

    access_token = _google_access_token(row)
    if not access_token:
        raise HTTPException(400, "Google account not connected")

    headers = {"Authorization": f"Bearer {access_token}"}
    ga4_properties = []
    gsc_sites = []

    # GA4 properties — accountSummaries returns every property the user can access
    # across all their accounts in one call (the properties.list endpoint requires a
    # specific account filter and has no wildcard).
    try:
        resp = httpx.get(
            "https://analyticsadmin.googleapis.com/v1beta/accountSummaries",
            headers=headers,
            params={"pageSize": 200},
            timeout=10.0,
        )
        if resp.status_code == 200:
            for acct in resp.json().get("accountSummaries", []):
                for prop in acct.get("propertySummaries", []):
                    ga4_properties.append({
                        "id": prop.get("property", "").replace("properties/", ""),
                        "display_name": prop.get("displayName", ""),
                        "website_url": "",
                    })
        else:
            logger.warning("GA4 accountSummaries returned %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning("GA4 property list failed: %s", exc)

    # GSC sites
    try:
        resp = httpx.get(
            "https://www.googleapis.com/webmasters/v3/sites",
            headers=headers,
            timeout=10.0,
        )
        if resp.status_code == 200:
            for site in resp.json().get("siteEntry", []):
                if site.get("permissionLevel") in ("siteOwner", "siteFullUser", "siteRestrictedUser"):
                    gsc_sites.append({
                        "url": site.get("siteUrl", ""),
                        "permission": site.get("permissionLevel", ""),
                    })
    except Exception as exc:
        logger.warning("GSC site list failed: %s", exc)

    return {"ga4_properties": ga4_properties, "gsc_sites": gsc_sites}


class GooglePropertyRequest(BaseModel):
    ga4_property_id: Optional[str] = None
    gsc_site_url: Optional[str] = None


@router.put("/google/property")
def save_google_property(body: GooglePropertyRequest, user_id: str = Depends(get_current_user_id)):
    """Save the user's selected GA4 property and/or GSC site."""
    db = get_supabase()
    update: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if body.ga4_property_id is not None:
        update["google_ga4_property_id"] = body.ga4_property_id or None
    if body.gsc_site_url is not None:
        update["google_gsc_site_url"] = body.gsc_site_url or None
    db.table("user_integrations").upsert(
        {"user_id": user_id, **update}, on_conflict="user_id"
    ).execute()
    return {"status": "ok"}


@router.delete("/google", status_code=204)
def disconnect_google(user_id: str = Depends(get_current_user_id)):
    """Disconnect Google — clear tokens and property selections."""
    db = get_supabase()
    db.table("user_integrations").update({
        "google_access_token": None, "google_refresh_token": None,
        "google_token_expiry": None, "google_ga4_property_id": None,
        "google_gsc_site_url": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("user_id", user_id).execute()


# ── Google context for playbook AI ────────────────────────────────────────────

def get_google_context(user_id: str) -> Optional[str]:
    """Fetch GA4 + GSC data and return a context string for the AI prompt."""
    db = get_supabase()
    row_res = db.table("user_integrations").select("*").eq("user_id", user_id).maybe_single().execute()
    row = (row_res.data or {}) if row_res else {}
    if not row:
        return None
    row["user_id"] = user_id

    access_token     = _google_access_token(row)
    ga4_property_id  = row.get("google_ga4_property_id") or ""
    gsc_site_url     = row.get("google_gsc_site_url") or ""

    if not access_token or (not ga4_property_id and not gsc_site_url):
        return None

    headers = {"Authorization": f"Bearer {access_token}"}
    parts: list[str] = []

    # GA4: sessions + top pages
    if ga4_property_id:
        try:
            today = datetime.now(timezone.utc).date().isoformat()
            thirty_ago = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
            resp = httpx.post(
                f"https://analyticsdata.googleapis.com/v1beta/properties/{ga4_property_id}:runReport",
                headers=headers,
                json={
                    "dateRanges": [{"startDate": thirty_ago, "endDate": today}],
                    "dimensions": [{"name": "pagePath"}],
                    # Only request sessions — adding `conversions` 400s the whole report
                    # on properties without a conversion configured, and we don't use it.
                    "metrics": [{"name": "sessions"}],
                    "limit": 5,
                    "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                rows = data.get("rows", [])
                totals = data.get("totals", [{}])[0].get("metricValues", [])
                total_sessions = int((totals[0].get("value") or "0") if totals else 0)
                if total_sessions:
                    parts.append(f"GA4 (last 30d): {total_sessions:,} sessions")
                top_pages = []
                for r in rows[:3]:
                    path   = r["dimensionValues"][0]["value"]
                    sess   = int(r["metricValues"][0]["value"] or 0)
                    top_pages.append(f"{path} ({sess:,} sessions)")
                if top_pages:
                    parts.append(f"top pages: {', '.join(top_pages)}")
        except Exception as exc:
            logger.debug("GA4 context failed for user %s: %s", user_id, exc)

    # GSC: top queries
    if gsc_site_url:
        try:
            today = datetime.now(timezone.utc).date().isoformat()
            thirty_ago = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
            # The siteUrl is a path segment and MUST be percent-encoded — for a
            # URL-prefix property it contains "https://" and slashes.
            site_enc = quote(gsc_site_url, safe="")
            resp = httpx.post(
                f"https://www.googleapis.com/webmasters/v3/sites/{site_enc}/searchAnalytics/query",
                headers=headers,
                json={
                    "startDate": thirty_ago, "endDate": today,
                    "dimensions": ["query"], "rowLimit": 8,
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                rows = resp.json().get("rows", [])
                queries = []
                for r in rows[:5]:
                    query   = r.get("keys", [""])[0]
                    impr    = int(r.get("impressions", 0))
                    pos     = round(r.get("position", 0), 1)
                    queries.append(f'"{query}" ({impr:,} impr, pos {pos})')
                if queries:
                    parts.append(f"top search queries: {'; '.join(queries)}")
        except Exception as exc:
            logger.debug("GSC context failed for user %s: %s", user_id, exc)

    return "\n  ".join(parts) if parts else None


# ── Shopify Admin context for playbook AI ─────────────────────────────────────

def get_shopify_context(user_id: str) -> Optional[str]:
    """Fetch private Shopify Admin data (real inventory + active discounts) for the
    user's connected store and return a context string for the AI prompt.

    Justifies the read_inventory / read_price_rules / read_discounts scopes the
    Connect flow requests. Returns None if no store is connected or calls fail.
    Public scan data already covers prices/catalog — this adds what's only visible
    to the merchant: true stock levels and active discount rules.
    """
    db = get_supabase()
    res = (
        db.table("shopify_connections")
        .select("shop, access_token")
        .eq("user_id", user_id)
        .is_("uninstalled_at", "null")
        .maybe_single()
        .execute()
    )
    row = (res.data or {}) if res else {}
    shop = row.get("shop") or ""
    token = row.get("access_token") or ""
    if not shop or not token:
        return None

    headers = {"X-Shopify-Access-Token": token}
    parts: list[str] = []

    # Real inventory — public scans only see a boolean "available"; the Admin API
    # exposes actual stock. Count out-of-stock variants among the first 250 products.
    try:
        resp = httpx.get(
            f"https://{shop}/admin/api/2024-01/products.json",
            headers=headers,
            params={"limit": 250, "fields": "variants"},
            timeout=8.0,
        )
        if resp.status_code == 200:
            variants = [v for p in resp.json().get("products", []) for v in (p.get("variants") or [])]
            tracked = [v for v in variants if v.get("inventory_management")]
            oos = sum(1 for v in tracked if (v.get("inventory_quantity") or 0) <= 0)
            if tracked:
                parts.append(
                    f"Your store inventory (Shopify Admin): {oos} of {len(tracked)} tracked variants out of stock"
                )
    except Exception as exc:
        logger.debug("Shopify inventory context failed for user %s: %s", user_id, exc)

    # Active discount rules — only the merchant can see these.
    try:
        resp = httpx.get(
            f"https://{shop}/admin/api/2024-01/price_rules.json",
            headers=headers,
            params={"limit": 250},
            timeout=8.0,
        )
        if resp.status_code == 200:
            now = datetime.now(timezone.utc)
            active = []
            for rule in resp.json().get("price_rules", []):
                ends_raw = rule.get("ends_at")
                starts_raw = rule.get("starts_at")
                try:
                    started = (not starts_raw) or datetime.fromisoformat(starts_raw.replace("Z", "+00:00")) <= now
                    not_ended = (not ends_raw) or datetime.fromisoformat(ends_raw.replace("Z", "+00:00")) >= now
                except Exception:
                    started, not_ended = True, True
                if started and not_ended:
                    active.append(rule)
            if active:
                example = (active[0].get("title") or "").strip()
                example_str = f' (e.g. "{example}")' if example else ""
                parts.append(f"Your active discount rules: {len(active)}{example_str}")
    except Exception as exc:
        logger.debug("Shopify price-rule context failed for user %s: %s", user_id, exc)

    return "\n  ".join(parts) if parts else None


# ── Meta Ad Library (public competitor ad intelligence) ───────────────────────
#
# Uses Meta's OFFICIAL Ad Library Graph API (graph.facebook.com/.../ads_archive).
# This does NOT use the user's own ad account and is independent of the user's
# Meta Ads integration — it reads the public ad archive.
#
# COVERAGE CAVEAT (be honest in marketing): the official API returns ALL ads for
# campaigns served in the EU (DSA) and political/issue ads everywhere, but US
# *commercial* ads are only partially available. Broader access aligns with the
# verified-business step (the same Meta business registration on the roadmap).
# Gated on a configured token — returns None (inert) until META_AD_LIBRARY_TOKEN
# is set, so it never breaks the playbook.

def get_competitor_ads_context(hostname: str) -> Optional[str]:
    """Best-effort: how many active ads a competitor is running, via the public
    Meta Ad Library API. Returns a one-line context string or None."""
    settings = _get_google_settings()
    token = getattr(settings, "meta_ad_library_token", "") or ""
    if not token or not hostname:
        return None

    # Brand name guess from hostname (e.g. "gymshark.com" -> "gymshark")
    brand = hostname.split(".")[0].replace("-", " ").strip()
    if not brand:
        return None

    try:
        resp = httpx.get(
            "https://graph.facebook.com/v19.0/ads_archive",
            params={
                "access_token": token,
                "search_terms": brand,
                "ad_type": "ALL",
                "ad_active_status": "ACTIVE",
                "ad_reached_countries": "['US']",
                "fields": "id,ad_delivery_start_time,publisher_platforms",
                "limit": 50,
            },
            timeout=10.0,
        )
        if resp.status_code != 200:
            logger.debug("Meta Ad Library returned %s for %s: %s", resp.status_code, brand, resp.text[:200])
            return None
        ads = resp.json().get("data", [])
        if not ads:
            return None
        # Longest-running active ad = their proven creative
        starts = []
        for a in ads:
            raw = a.get("ad_delivery_start_time")
            if raw:
                try:
                    starts.append(datetime.fromisoformat(str(raw).replace("Z", "+00:00")))
                except Exception:
                    pass
        oldest_days = ""
        if starts:
            d = max(0, (datetime.now(timezone.utc) - min(starts)).days)
            oldest_days = f", longest-running active {d}d"
        return f"Meta Ads: {len(ads)} active ad{'s' if len(ads) != 1 else ''} in the Ad Library{oldest_days}"
    except Exception as exc:
        logger.debug("Meta Ad Library fetch failed for %s: %s", brand, exc)
        return None
