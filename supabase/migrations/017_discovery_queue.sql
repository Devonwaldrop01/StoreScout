-- Staging queue for the "discovered universe" — the largest, cheapest stage of
-- the pipeline. Sources bulk-harvest raw refs here (e.g. shop.app/m/{handle})
-- WITHOUT the expensive per-store resolution. A background resolution stage
-- then turns each ref into a real merchant domain and promotes it into
-- shopify_store_index as 'discovered', where verification + knowledge take over.
--
-- This keeps shopify_store_index clean (real domains only, user-facing quality)
-- while letting discovery scale to 100k+ without rate-limited fetches, exactly
-- per the Discovered → Resolved → Verified → Classified design.

CREATE TABLE IF NOT EXISTS discovery_queue (
  id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source         TEXT NOT NULL,                 -- shop_app | ...
  ref            TEXT NOT NULL,                 -- shop.app/m/{handle}  OR  a bare domain
  status         TEXT NOT NULL DEFAULT 'pending', -- pending | resolved | failed
  resolved_domain TEXT,
  attempts       INTEGER DEFAULT 0,
  discovered_at  TIMESTAMPTZ DEFAULT now(),
  resolved_at    TIMESTAMPTZ,
  updated_at     TIMESTAMPTZ DEFAULT now(),
  UNIQUE (source, ref)
);

CREATE INDEX IF NOT EXISTS idx_discovery_queue_status ON discovery_queue(status, source);
CREATE INDEX IF NOT EXISTS idx_discovery_queue_disc   ON discovery_queue(discovered_at);

ALTER TABLE discovery_queue ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON discovery_queue USING (false);
