-- Store index evolution: from "list of verified stores" to a compounding
-- knowledge graph of the Shopify ecosystem.
--
--  · Market context columns — business stage + pricing tier estimates so
--    discovery can match users with stores they actually compete against
--    (a startup fitness brand should see growing fitness brands, not Nike).
--  · expanded_at — graph expansion bookkeeping: each verified store is used
--    once as a seed for discovering related brands.
--  · store_index_runs — daily worker history for the admin quality dashboard.

ALTER TABLE shopify_store_index
  ADD COLUMN IF NOT EXISTS business_stage TEXT
    CHECK (business_stage IN ('startup', 'growing', 'established', 'enterprise')),
  ADD COLUMN IF NOT EXISTS pricing_tier TEXT
    CHECK (pricing_tier IN ('budget', 'mid-market', 'premium', 'luxury')),
  ADD COLUMN IF NOT EXISTS expanded_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_store_index_stage    ON shopify_store_index(business_stage);
CREATE INDEX IF NOT EXISTS idx_store_index_tier     ON shopify_store_index(pricing_tier);
CREATE INDEX IF NOT EXISTS idx_store_index_expanded ON shopify_store_index(expanded_at);

CREATE TABLE IF NOT EXISTS store_index_runs (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ran_at         TIMESTAMPTZ DEFAULT now(),
  trigger        TEXT,                -- cron | manual
  processed      INTEGER DEFAULT 0,
  verified       INTEGER DEFAULT 0,
  rejected       INTEGER DEFAULT 0,
  failed         INTEGER DEFAULT 0,
  duplicates     INTEGER DEFAULT 0,
  reverified     INTEGER DEFAULT 0,
  source_counts  JSONB,               -- {"seed": 3, "ai_niche_query": 12, ...}
  notes          TEXT
);

CREATE INDEX IF NOT EXISTS idx_store_index_runs_ran_at ON store_index_runs(ran_at);

ALTER TABLE store_index_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON store_index_runs USING (false);
