-- Brand Intel v2: a decoded, readable strategy brief instead of raw signal
-- flags. Cached on the competitor row (keyed by a signature of the inputs) so
-- it's generated once per meaningful change, not on every page load.
ALTER TABLE competitors
  ADD COLUMN IF NOT EXISTS brand_decode      JSONB,
  ADD COLUMN IF NOT EXISTS brand_decode_sig  TEXT,
  ADD COLUMN IF NOT EXISTS brand_decode_at   TIMESTAMPTZ;
