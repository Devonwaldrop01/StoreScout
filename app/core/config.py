from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Server
    port: int = 10000
    public_base_url: str = "https://getstorescout.com"
    dev_skip_payment: bool = False

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""
    stripe_pro_price_id: str = ""
    stripe_agency_price_id: str = ""
    stripe_pro_annual_price_id: str = ""
    stripe_agency_annual_price_id: str = ""
    stripe_developer_price_id: str = ""
    stripe_developer_annual_price_id: str = ""
    shopify_api_key: str = ""
    shopify_api_secret: str = ""

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Meta Ad Library (public competitor ad intelligence — not the user's ad account)
    meta_ad_library_token: str = ""

    # Email
    resend_api_key: str = ""
    resend_from: str = "StoreScout <hello@getstorescout.com>"
    owner_email: str = "devonwaldrop0131@gmail.com"

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""
    supabase_jwt_secret: str = ""

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # Internal service communication (worker → web service for outbound fetches)
    api_internal_url: str = "http://localhost:10000"
    internal_secret: str = "dev-internal-secret"

    # Anthropic
    anthropic_api_key: str = ""

    # Tier scan intervals (hours)
    free_scan_interval_hours: int = 168
    pro_scan_interval_hours: int = 24
    agency_scan_interval_hours: int = 12

    # Tier competitor limits
    free_max_competitors: int = 1
    pro_max_competitors: int = 10
    agency_max_competitors: int = 50

    # Shopify store index (background discovery worker) — off unless explicitly enabled
    shopify_index_enabled: bool = False
    shopify_index_daily_candidate_limit: int = 75
    shopify_index_min_confidence: int = 60
    shopify_index_concurrency: int = 2

    # Admin endpoints (/api/v1/admin/*) — disabled while this is empty
    admin_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
