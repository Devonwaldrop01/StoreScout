-- Business profile — the onboarding answers, persisted and reused.
-- Until now category/goal were collected in onboarding then thrown away, so
-- nothing downstream could personalize. This is the durable record that
-- feeds the dashboard, Playbook, vs-You, and every AI recommendation.

CREATE TABLE IF NOT EXISTS business_profiles (
  user_id         UUID PRIMARY KEY REFERENCES user_profiles(id) ON DELETE CASCADE,
  category        TEXT,           -- what they sell (taxonomy label)
  price_range     TEXT,           -- budget | mid | premium | luxury
  target_customer TEXT,           -- free-text "who buys from you"
  primary_goal    TEXT,           -- pricing | gaps | launches | plays | monitoring
  sells           TEXT,           -- optional richer description
  own_store_url   TEXT,           -- optional, recommended — powers vs-You
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE business_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON business_profiles USING (false);
