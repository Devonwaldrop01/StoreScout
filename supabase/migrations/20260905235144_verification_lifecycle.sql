-- Local Phase 1 schema. Applying this migration to production is NOT authorized.
-- No backfill: historical flags cannot manufacture successful catalog evidence.
ALTER TABLE public.shopify_store_index
  ADD COLUMN verification_state text CHECK (verification_state IN (
    'verified_shopify', 'probable_shopify', 'temporarily_unreachable', 'dead_domain',
    'blocked', 'password_protected', 'no_readable_catalog', 'non_shopify',
    'ambiguous', 'storefront_unavailable')),
  ADD COLUMN catalog_observation jsonb,
  ADD COLUMN last_attempted_at timestamptz,
  ADD COLUMN next_verification_at timestamptz,
  ADD COLUMN verification_attempts integer NOT NULL DEFAULT 0 CHECK (verification_attempts >= 0),
  ADD COLUMN verification_token uuid;

CREATE INDEX idx_store_verification_due
  ON public.shopify_store_index (status, next_verification_at, created_at, domain);
-- Existing verified rows need renewal based on their historical success date.
CREATE INDEX idx_store_verification_legacy_renewal
  ON public.shopify_store_index (last_verified_at, domain)
  WHERE status = 'verified' AND next_verification_at IS NULL;

-- Existing RLS/service-role access is unchanged. No new public RPCs or grants.
