-- Three-stage Competitive Intelligence Index: DISCOVERY → VERIFICATION →
-- KNOWLEDGE. Discovery only collects candidate domains; verification turns
-- them into confirmed Shopify stores (with a reason on rejection); knowledge
-- runs only on verified stores and builds a multi-signal, confidence-scored
-- profile. Every stage records its own timestamp.

ALTER TABLE shopify_store_index
  -- Pipeline provenance + timing
  ADD COLUMN IF NOT EXISTS discovery_source   TEXT,          -- shop_app | discovery | tracked | seed | ...
  ADD COLUMN IF NOT EXISTS discovered_at      TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS verified_at        TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS knowledge_at       TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS rejection_reason   TEXT,          -- not_shopify | no_products | dead_domain | duplicate | password_protected | invalid_storefront | low_confidence
  -- Multi-signal category knowledge
  ADD COLUMN IF NOT EXISTS category_confidence INTEGER,      -- 0-100
  ADD COLUMN IF NOT EXISTS category_evidence   JSONB,        -- [{signal, detail, weight}]
  ADD COLUMN IF NOT EXISTS price_bands         JSONB,        -- {p25, p50, p75}
  ADD COLUMN IF NOT EXISTS target_customer     TEXT,
  ADD COLUMN IF NOT EXISTS brand_keywords      JSONB,        -- [str]
  ADD COLUMN IF NOT EXISTS homepage_message    TEXT,
  ADD COLUMN IF NOT EXISTS collection_count    INTEGER,
  -- Relationship-graph foundation (structure only; not populated yet)
  ADD COLUMN IF NOT EXISTS related_ready       BOOLEAN DEFAULT false;

-- 'discovered' is the new pre-verification state. Widen the CHECK.
ALTER TABLE shopify_store_index DROP CONSTRAINT IF EXISTS shopify_store_index_status_check;
ALTER TABLE shopify_store_index
  ADD CONSTRAINT shopify_store_index_status_check
  CHECK (status IN ('discovered', 'candidate', 'verified', 'rejected', 'failed'));

CREATE INDEX IF NOT EXISTS idx_store_index_cat_conf  ON shopify_store_index(category, category_confidence);
CREATE INDEX IF NOT EXISTS idx_store_index_knowledge ON shopify_store_index(knowledge_at);
CREATE INDEX IF NOT EXISTS idx_store_index_disc_src  ON shopify_store_index(discovery_source);

-- Resumable discovery cursors — each source remembers where it left off so
-- the crawler continues over time and never rediscovers the same store.
CREATE TABLE IF NOT EXISTS discovery_cursors (
  source      TEXT PRIMARY KEY,
  cursor      JSONB,                 -- source-specific position (page, token, offset…)
  enabled     BOOLEAN DEFAULT true,
  last_run_at TIMESTAMPTZ,
  discovered  INTEGER DEFAULT 0,     -- lifetime domains this source has surfaced
  updated_at  TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE discovery_cursors ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON discovery_cursors USING (false);
