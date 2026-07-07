-- Verified Shopify store index — StoreScout's proprietary, compounding database
-- of lightly-scanned Shopify stores. Populated by the background discovery
-- worker (app/tasks/store_index.py), discovery byproducts, manual seeds, and
-- tracked-store upserts. Powers index-first competitor discovery.
--
-- This is NOT the tracked-competitor pipeline: rows here get a ≤4-request
-- light pass, never full scans, and re-verify on a 60-day cycle.

CREATE TABLE IF NOT EXISTS shopify_store_index (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain                   TEXT UNIQUE NOT NULL,
  brand_name               TEXT,
  homepage_url             TEXT,
  category                 TEXT,
  subcategory              TEXT,
  description              TEXT,
  country                  TEXT,
  language                 TEXT,
  product_count            INTEGER,
  median_price             NUMERIC,
  min_price                NUMERIC,
  max_price                NUMERIC,
  promo_rate               NUMERIC,             -- % of sampled catalog discounted
  collections              JSONB,               -- [{handle, title}] sample
  product_types            JSONB,               -- [str]
  tags                     JSONB,               -- [str]
  vendors                  JSONB,               -- [str]
  verification_confidence  INTEGER,             -- 0-100 multi-signal score
  verification_signals     JSONB,               -- [str] matched signals
  source                   TEXT,                -- seed | ai_niche_query | discovery | tracked | search
  source_query             TEXT,                -- niche query / user description that surfaced it
  status                   TEXT NOT NULL DEFAULT 'candidate'
                             CHECK (status IN ('candidate', 'verified', 'rejected', 'failed')),
  failure_reason           TEXT,
  last_verified_at         TIMESTAMPTZ,
  last_light_scanned_at    TIMESTAMPTZ,
  created_at               TIMESTAMPTZ DEFAULT now(),
  updated_at               TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_store_index_domain          ON shopify_store_index(domain);
CREATE INDEX IF NOT EXISTS idx_store_index_category        ON shopify_store_index(category);
CREATE INDEX IF NOT EXISTS idx_store_index_subcategory     ON shopify_store_index(subcategory);
CREATE INDEX IF NOT EXISTS idx_store_index_confidence      ON shopify_store_index(verification_confidence);
CREATE INDEX IF NOT EXISTS idx_store_index_status          ON shopify_store_index(status);
CREATE INDEX IF NOT EXISTS idx_store_index_last_verified   ON shopify_store_index(last_verified_at);
CREATE INDEX IF NOT EXISTS idx_store_index_last_scanned    ON shopify_store_index(last_light_scanned_at);

ALTER TABLE shopify_store_index ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON shopify_store_index USING (false);
