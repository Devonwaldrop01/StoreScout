-- Runtime configuration — a tiny key/value store for operational knobs that
-- admins flip from /admin without a redeploy or restart.
--
-- The env vars (SHOPIFY_INDEX_ENABLED, LEAD_ENGINE_DAILY_TARGET, …) remain
-- the DEFAULTS for a fresh deploy. A row here OVERRIDES its env var; the
-- workers read this table (with a short cache) at the start of each run, so
-- toggling a value takes effect within seconds. Only a fixed allowlist of
-- keys is honored (see app/services/runtime_config.py).

CREATE TABLE IF NOT EXISTS app_config (
  key         TEXT PRIMARY KEY,
  value       JSONB NOT NULL,          -- bool or int, JSON-typed
  updated_at  TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE app_config ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON app_config USING (false);
