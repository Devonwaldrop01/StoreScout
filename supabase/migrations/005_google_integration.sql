ALTER TABLE user_integrations ADD COLUMN IF NOT EXISTS google_access_token  TEXT;
ALTER TABLE user_integrations ADD COLUMN IF NOT EXISTS google_refresh_token TEXT;
ALTER TABLE user_integrations ADD COLUMN IF NOT EXISTS google_token_expiry  TIMESTAMPTZ;
ALTER TABLE user_integrations ADD COLUMN IF NOT EXISTS google_ga4_property_id TEXT;
ALTER TABLE user_integrations ADD COLUMN IF NOT EXISTS google_gsc_site_url   TEXT;
