-- StoreScout SaaS: Initial Schema
-- Run in Supabase SQL editor or via `supabase db push`

-- ─────────────────────────────────────────
-- USER PROFILES (extends Supabase Auth)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  full_name TEXT,
  tier TEXT NOT NULL DEFAULT 'free',
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  subscription_status TEXT NOT NULL DEFAULT 'inactive',
  max_competitors INT NOT NULL DEFAULT 1,
  scan_interval_hours INT NOT NULL DEFAULT 168,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own profile" ON user_profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON user_profiles FOR UPDATE USING (auth.uid() = id);

-- ─────────────────────────────────────────
-- COMPETITORS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS competitors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  store_url TEXT NOT NULL,
  hostname TEXT NOT NULL,
  display_name TEXT,
  is_active BOOLEAN NOT NULL DEFAULT true,
  last_scanned_at TIMESTAMPTZ,
  next_scan_at TIMESTAMPTZ,
  scan_status TEXT NOT NULL DEFAULT 'pending',
  error_message TEXT,
  product_count INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, store_url)
);

CREATE INDEX idx_competitors_user ON competitors(user_id);
CREATE INDEX idx_competitors_next_scan ON competitors(next_scan_at) WHERE is_active = true;

ALTER TABLE competitors ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own competitors" ON competitors FOR ALL USING (auth.uid() = user_id);

-- ─────────────────────────────────────────
-- SCAN SNAPSHOTS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scan_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  competitor_id UUID NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
  scanned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  product_count INT,
  median_price NUMERIC(10,2),
  promo_rate NUMERIC(5,2),
  new_30d INT,
  snapshot_data JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_snapshots_competitor_scanned ON scan_snapshots(competitor_id, scanned_at DESC);

ALTER TABLE scan_snapshots ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own snapshots" ON scan_snapshots FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM competitors c WHERE c.id = competitor_id AND c.user_id = auth.uid()
  ));

-- ─────────────────────────────────────────
-- CHANGE EVENTS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS change_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  competitor_id UUID NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
  detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  change_type TEXT NOT NULL,
  product_handle TEXT,
  product_title TEXT,
  product_url TEXT,
  old_value JSONB,
  new_value JSONB,
  delta_pct NUMERIC(8,2),
  severity TEXT NOT NULL DEFAULT 'info',
  alert_sent BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_changes_competitor_detected ON change_events(competitor_id, detected_at DESC);
CREATE INDEX idx_changes_unread ON change_events(competitor_id, alert_sent) WHERE alert_sent = false;

ALTER TABLE change_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own change events" ON change_events FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM competitors c WHERE c.id = competitor_id AND c.user_id = auth.uid()
  ));
CREATE POLICY "Users update own change events" ON change_events FOR UPDATE
  USING (EXISTS (
    SELECT 1 FROM competitors c WHERE c.id = competitor_id AND c.user_id = auth.uid()
  ));

-- ─────────────────────────────────────────
-- AI SUMMARIES
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_summaries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  competitor_id UUID NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  model TEXT NOT NULL,
  summary_text TEXT NOT NULL,
  summary_type TEXT NOT NULL DEFAULT 'weekly',
  input_tokens INT,
  output_tokens INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ai_summaries_competitor ON ai_summaries(competitor_id, generated_at DESC);

ALTER TABLE ai_summaries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own AI summaries" ON ai_summaries FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM competitors c WHERE c.id = competitor_id AND c.user_id = auth.uid()
  ));

-- ─────────────────────────────────────────
-- NOTIFICATION PREFERENCES
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notification_prefs (
  user_id UUID PRIMARY KEY REFERENCES user_profiles(id) ON DELETE CASCADE,
  email_price_changes BOOLEAN NOT NULL DEFAULT true,
  email_new_products BOOLEAN NOT NULL DEFAULT true,
  email_discount_changes BOOLEAN NOT NULL DEFAULT false,
  email_weekly_digest BOOLEAN NOT NULL DEFAULT true,
  digest_day TEXT NOT NULL DEFAULT 'monday',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE notification_prefs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own prefs" ON notification_prefs FOR ALL USING (auth.uid() = user_id);

-- ─────────────────────────────────────────
-- ALERT EMAIL LOG (for cooldown enforcement)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alert_email_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  competitor_id UUID NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
  sent_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_alert_log_cooldown ON alert_email_log(user_id, competitor_id, sent_at DESC);

-- ─────────────────────────────────────────
-- HELPER FUNCTION: competitors needing AI summary
-- ─────────────────────────────────────────
CREATE OR REPLACE FUNCTION competitors_needing_ai_summary(cutoff TIMESTAMPTZ)
RETURNS TABLE(competitor_id UUID) AS $$
  SELECT c.id
  FROM competitors c
  JOIN user_profiles u ON u.id = c.user_id
  WHERE c.is_active = true
    AND u.tier IN ('pro', 'agency')
    AND u.subscription_status = 'active'
    AND NOT EXISTS (
      SELECT 1 FROM ai_summaries s
      WHERE s.competitor_id = c.id
        AND s.generated_at > cutoff
    )
$$ LANGUAGE SQL STABLE;

-- ─────────────────────────────────────────
-- UPDATED_AT trigger
-- ─────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER competitors_updated_at BEFORE UPDATE ON competitors
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER user_profiles_updated_at BEFORE UPDATE ON user_profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
