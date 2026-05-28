CREATE TABLE IF NOT EXISTS user_integrations (
  user_id         UUID PRIMARY KEY REFERENCES user_profiles(id) ON DELETE CASCADE,
  klaviyo_api_key TEXT,
  updated_at      TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE user_integrations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON user_integrations USING (false);
