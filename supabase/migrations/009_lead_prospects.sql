-- Internal Lead Discovery Engine (NOT customer-facing).
--
-- A prospect is a verified Shopify store from shopify_store_index that the
-- qualification model believes would genuinely benefit from StoreScout.
-- This table behaves like a lightweight CRM: each row carries its scores
-- (with every reason stored), the research findings, a grounded outreach
-- angle + draft email, and its pipeline stage.

CREATE TABLE IF NOT EXISTS lead_prospects (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain                TEXT UNIQUE NOT NULL,      -- references shopify_store_index.domain
  brand_name            TEXT,
  category              TEXT,
  subcategory           TEXT,
  country               TEXT,
  business_stage        TEXT,
  pricing_tier          TEXT,
  lead_score            INTEGER,                   -- likelihood of becoming a successful customer
  qualification_score   INTEGER,                   -- would StoreScout genuinely help this business?
  score_reasons         JSONB,                     -- [str] every positive signal
  disqualifiers         JSONB,                     -- [str] every negative signal
  outreach_status       TEXT NOT NULL DEFAULT 'discovered'
                          CHECK (outreach_status IN (
                            'discovered', 'qualified', 'research_complete',
                            'ready', 'contacted', 'replied', 'demo_scheduled',
                            'trial_started', 'customer', 'lost', 'never_contact')),
  research_status       TEXT DEFAULT 'pending'
                          CHECK (research_status IN ('pending', 'complete', 'failed')),
  competitors_found     INTEGER,
  tracked_in_index      BOOLEAN DEFAULT true,
  generated_insights    JSONB,                     -- {competitors: [...], findings: [str], market: {...}}
  recommended_angle     TEXT,                      -- the one genuinely interesting conversation starter
  suggested_subject     TEXT,
  suggested_email       TEXT,
  notes                 TEXT,
  assigned_to           TEXT,
  created_at            TIMESTAMPTZ DEFAULT now(),
  updated_at            TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lead_prospects_domain     ON lead_prospects(domain);
CREATE INDEX IF NOT EXISTS idx_lead_prospects_score      ON lead_prospects(lead_score);
CREATE INDEX IF NOT EXISTS idx_lead_prospects_status     ON lead_prospects(outreach_status);
CREATE INDEX IF NOT EXISTS idx_lead_prospects_category   ON lead_prospects(category);
CREATE INDEX IF NOT EXISTS idx_lead_prospects_created_at ON lead_prospects(created_at);

ALTER TABLE lead_prospects ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role only" ON lead_prospects USING (false);
