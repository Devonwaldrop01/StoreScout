-- Store DNA — a semantic business profile for every VERIFIED indexed store,
-- generated during the knowledge stage from the signals StoreScout already
-- collected (product titles/types, collections, pricing, homepage message).
--
-- Tracked competitors get a full Brand Decode; indexed stores only had
-- category/subcategory/target_customer/brand_keywords. Store DNA closes that
-- gap so the index can rank TRUE direct competitors — not just same-category
-- stores — during onboarding and discovery.
--
-- store_dna holds the human-readable profile; dna_keywords is the flat,
-- normalized tag set used for fast overlap matching; dna_signature caches the
-- inputs so the (Haiku) generation only re-runs when the picture changes.

ALTER TABLE shopify_store_index
  ADD COLUMN IF NOT EXISTS store_dna      JSONB,   -- {summary, sells, audience, price_positioning, personality[], differentiators[], keywords[]}
  ADD COLUMN IF NOT EXISTS dna_keywords   JSONB,   -- [str] flat semantic tags for matching
  ADD COLUMN IF NOT EXISTS dna_signature  TEXT,    -- hash of the inputs; skip regen when unchanged
  ADD COLUMN IF NOT EXISTS dna_at         TIMESTAMPTZ;

-- GIN index over the flat keyword array so direct-competitor overlap lookups
-- (dna_keywords ?| array[...]) stay fast as the index scales past 100k rows.
CREATE INDEX IF NOT EXISTS idx_store_index_dna_keywords
  ON shopify_store_index USING GIN (dna_keywords);
CREATE INDEX IF NOT EXISTS idx_store_index_dna_at
  ON shopify_store_index(dna_at);
