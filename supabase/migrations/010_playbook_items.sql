-- Playbook items — the persisted half of the action loop.
--
-- Until now the Playbook only held AI-generated plays with completion state
-- in localStorage. This table makes recommendations from ANYWHERE in the app
-- (signal rows, gap cards, winning products, briefs, Pro analysis) savable as
-- durable tasks with evidence, a source link, server-side status, and an
-- outcome — closing the loop: detect → explain → recommend → act → track.

CREATE TABLE IF NOT EXISTS playbook_items (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
  source_type    TEXT NOT NULL CHECK (source_type IN
                   ('signal', 'gap', 'winning_product', 'pricing', 'brief', 'pro_analysis', 'manual')),
  source_ref     TEXT,                    -- id/handle of the thing that spawned this
  competitor_id  UUID REFERENCES competitors(id) ON DELETE SET NULL,
  hostname       TEXT,                    -- kept even if the competitor is removed
  title          TEXT NOT NULL,
  reason         TEXT,                    -- why StoreScout recommended it
  evidence       TEXT,                    -- the observed data it rests on
  priority       TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),
  due_at         TIMESTAMPTZ,
  status         TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done', 'dismissed')),
  outcome        TEXT CHECK (outcome IN ('worked', 'too_early', 'not_relevant')),
  notes          TEXT,
  dedupe_key     TEXT NOT NULL,           -- source_type:source_ref:title hash — saves are idempotent
  created_at     TIMESTAMPTZ DEFAULT now(),
  updated_at     TIMESTAMPTZ DEFAULT now(),
  completed_at   TIMESTAMPTZ,
  UNIQUE(user_id, dedupe_key)
);

CREATE INDEX IF NOT EXISTS idx_playbook_items_user    ON playbook_items(user_id);
CREATE INDEX IF NOT EXISTS idx_playbook_items_status  ON playbook_items(user_id, status);
CREATE INDEX IF NOT EXISTS idx_playbook_items_created ON playbook_items(created_at);

ALTER TABLE playbook_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON playbook_items USING (false);
