-- Sample of product titles captured at verification, used by the knowledge
-- stage as a strong (merchant-declared) classification signal. Separate from
-- 015 so it applies cleanly whether or not 015 has already been run.
ALTER TABLE shopify_store_index
  ADD COLUMN IF NOT EXISTS product_titles JSONB;
