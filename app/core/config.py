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
    # Hide the Google (GA4/Search Console) integration until the production
    # OAuth redirect URI is registered in Google Cloud Console. Ship OFF for
    # launch; flip on once the Console + prod domain are verified.
    google_integration_enabled: bool = False

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
    # Shared AI-call layer (app/services/ai.py): explicit timeout, bounded
    # transient retries, and a per-feature circuit breaker so a failing
    # Anthropic never hangs requests or hammers the API. All safe defaults.
    anthropic_timeout_s: float = 30.0
    anthropic_max_retries: int = 2            # transient failures only (429/5xx/timeouts)
    ai_circuit_threshold: int = 5             # consecutive failures before the breaker opens
    ai_circuit_cooldown_s: int = 60           # how long the breaker stays open

    # Server-side AI abuse controls (app/core/ratelimit.py) for interactive
    # endpoints. Per-user hourly caps + input bounds; Redis-backed, fail-open.
    ai_ratelimit_ask_per_hour: int = 30
    ai_ratelimit_interpret_per_hour: int = 60
    ai_max_question_len: int = 500            # Ask StoreScout question hard cap
    ai_max_signals: int = 8                   # market-signal interpretation list cap

    # A scan stuck in 'scanning' longer than this is treated as timed_out by the
    # scan-status lifecycle endpoint (the worker recycles well under this).
    scan_timeout_minutes: int = 15

    # Launch-time memory guard: hard cap on products a single scan processes.
    # Bounds peak memory of fetch → normalize → analyze → detect for huge
    # catalogs so the 512MB worker/web dynos don't OOM. Raise once on bigger
    # plans. 0 = uncapped.
    scan_max_products: int = 1500

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
    # The worker optimizes for NEW VERIFIED stores per day, not candidates
    # processed. candidate_limit stays as the hard request budget.
    # Dev 25–50 / early prod 50–100 / scaled 100–250.
    shopify_index_daily_verified_target: int = 25
    shopify_index_daily_candidate_limit: int = 150
    shopify_index_min_confidence: int = 60
    shopify_index_concurrency: int = 2
    # Three-stage pipeline knobs (discovery → verification → knowledge). Each
    # stage is chunked so it fits the shared worker's memory and can resume.
    shopify_index_discovery_batch: int = 60   # candidate domains surfaced per discovery run
    shopify_index_harvest_batch: int = 1000   # raw refs bulk-harvested into the queue per run
    shopify_index_resolve_batch: int = 40     # queued refs resolved → real domains per run
    shopify_index_verify_batch: int = 40      # discovered → verified/rejected per verify run
    shopify_index_knowledge_batch: int = 60   # verified → classified per knowledge run
    # Only recommend a store when its category is at least this confident —
    # this is the guard against "Everlane for pet accessories" weak guesses.
    shopify_index_category_min_confidence: int = 55

    # Admin endpoints (/api/v1/admin/*) — disabled while this is empty
    admin_token: str = ""

    # Internal lead discovery engine — growth tooling, never customer-facing
    lead_engine_enabled: bool = False
    lead_engine_daily_target: int = 20        # HIGH-QUALITY prospects/day, not volume
    lead_engine_min_qualification: int = 55   # below this a store never becomes a prospect
    lead_outreach_sender_name: str = "Devon"

    # Intent-signal engine (Phase 2) — inbound buying-intent from public
    # discussions. Off by default; the live fetch runs on the web process.
    intent_engine_enabled: bool = False
    intent_min_score: int = 60        # below this an intent post is ignored


@lru_cache
def get_settings() -> Settings:
    return Settings()
