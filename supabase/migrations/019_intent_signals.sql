-- Phase 2 of the Lead Engine: inbound INTENT signals. Instead of scoring the
-- whole Shopify universe outbound, this captures people publicly describing
-- StoreScout-shaped pain ("how do I track competitor prices?") from public
-- discussions. High intent, but usually anonymous — so a signal becomes a real
-- lead only when a store domain is extractable and passes the ICP model.

CREATE TABLE IF NOT EXISTS intent_signals (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source         TEXT NOT NULL,               -- reddit | ...
  external_id    TEXT NOT NULL,               -- source-native id (dedupe key)
  title          TEXT,
  quote          TEXT,                         -- the exact intent-bearing text
  author         TEXT,
  url            TEXT,
  channel        TEXT,                         -- subreddit / forum
  intent_score   INTEGER,                      -- 0-100 AI relevance to StoreScout
  intent_reason  TEXT,                         -- why it's relevant
  matched_domain TEXT,                         -- store domain if we could extract one
  contact_email  TEXT,
  status         TEXT NOT NULL DEFAULT 'new'
                   CHECK (status IN ('new','reviewed','promoted','engaged','dismissed')),
  promoted_lead_id UUID,                       -- lead_prospects.id when promoted
  created_at     TIMESTAMPTZ DEFAULT now(),
  posted_at      TIMESTAMPTZ,
  updated_at     TIMESTAMPTZ DEFAULT now(),
  UNIQUE (source, external_id)
);

CREATE INDEX IF NOT EXISTS idx_intent_signals_status ON intent_signals(status);
CREATE INDEX IF NOT EXISTS idx_intent_signals_score  ON intent_signals(intent_score);
CREATE INDEX IF NOT EXISTS idx_intent_signals_posted ON intent_signals(posted_at);

ALTER TABLE intent_signals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON intent_signals USING (false);
