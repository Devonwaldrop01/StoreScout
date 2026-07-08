-- Competitor knowledge graph — StoreScout's accumulated map of who competes
-- with whom. Every discovery search, every tracked competitor, and every
-- piece of user feedback writes an edge; future discoveries query the graph
-- BEFORE asking AI. Over time StoreScout relies less on AI per search and
-- more on its own compounding relationship data.
--
-- source_key is usually a store domain; for users without a connected store
-- it falls back to "user:{id}" so their feedback still improves THEIR results.
-- Negative weight = confirmed not-a-competitor (excluded from suggestions).

CREATE TABLE IF NOT EXISTS competitor_edges (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_key     TEXT NOT NULL,
  target_domain  TEXT NOT NULL,
  weight         INTEGER NOT NULL DEFAULT 1,
  edge_source    TEXT,               -- discovery | tracked | feedback
  created_at     TIMESTAMPTZ DEFAULT now(),
  updated_at     TIMESTAMPTZ DEFAULT now(),
  UNIQUE(source_key, target_domain)
);

CREATE INDEX IF NOT EXISTS idx_competitor_edges_source ON competitor_edges(source_key);
CREATE INDEX IF NOT EXISTS idx_competitor_edges_target ON competitor_edges(target_domain);

ALTER TABLE competitor_edges ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON competitor_edges USING (false);
