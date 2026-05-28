-- Shopify OAuth connections (both App Store installs and Connect flows)
CREATE TABLE IF NOT EXISTS shopify_connections (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shop            TEXT NOT NULL UNIQUE,
  user_id         UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
  access_token    TEXT NOT NULL,
  scope           TEXT,
  shop_name       TEXT,
  merchant_email  TEXT,
  connection_type TEXT DEFAULT 'connect',  -- 'install' | 'connect'
  uninstalled_at  TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_shopify_connections_user ON shopify_connections(user_id);

ALTER TABLE competitors ADD COLUMN IF NOT EXISTS shopify_shop TEXT;

ALTER TABLE shopify_connections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON shopify_connections USING (false);
