-- Lead-quality intelligence. The strongest predictor of whether a Shopify
-- brand will BUY StoreScout isn't catalog size — it's whether they already
-- spend on marketing/SaaS and can be reached. Capture those footprints during
-- indexing (from the homepage we already fetch) and give leads a real fit tier.

-- Commercial signals on every verified store (collected at verification).
ALTER TABLE shopify_store_index
  ADD COLUMN IF NOT EXISTS tech_signals    JSONB,     -- [klaviyo, meta_pixel, judgeme, recharge, ...]
  ADD COLUMN IF NOT EXISTS contact_email   TEXT,
  ADD COLUMN IF NOT EXISTS contact_source  TEXT,      -- mailto | page
  ADD COLUMN IF NOT EXISTS sells_wholesale BOOLEAN,
  ADD COLUMN IF NOT EXISTS multi_market    BOOLEAN;

-- Fit verdict + contact on each prospect.
ALTER TABLE lead_prospects
  ADD COLUMN IF NOT EXISTS fit_tier       TEXT,   -- hot | warm | cold | not_a_fit
  ADD COLUMN IF NOT EXISTS fit_reasoning  TEXT,   -- one-paragraph AI verdict: would THIS store buy?
  ADD COLUMN IF NOT EXISTS contact_email  TEXT,
  ADD COLUMN IF NOT EXISTS contact_source TEXT,
  ADD COLUMN IF NOT EXISTS tech_signals   JSONB,
  ADD COLUMN IF NOT EXISTS score_breakdown JSONB;  -- [{factor, points, note}]

CREATE INDEX IF NOT EXISTS idx_lead_prospects_fit_tier ON lead_prospects(fit_tier);
