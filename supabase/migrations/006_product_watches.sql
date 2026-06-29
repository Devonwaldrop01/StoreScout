-- Product watchlist — lets users pin specific competitor products and track
-- price/stock changes on them over time. Gives free users (1 competitor) a
-- personal engagement loop.

CREATE TABLE IF NOT EXISTS product_watches (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
  competitor_id  UUID REFERENCES competitors(id) ON DELETE CASCADE,
  product_handle TEXT NOT NULL,
  product_title  TEXT,
  product_url    TEXT,
  pinned_price   NUMERIC,            -- price at pin time, for the "since you pinned" delta
  created_at     TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, competitor_id, product_handle)
);

CREATE INDEX IF NOT EXISTS idx_product_watches_user ON product_watches(user_id);

ALTER TABLE product_watches ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON product_watches USING (false);
