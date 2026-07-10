-- Richer Business Profile — the onboarding answers that power direct-competitor
-- matching and personalization. Adds the brand descriptors + free-text notes
-- (and ensures `sells`, the specific "what do you sell" description, exists).
ALTER TABLE business_profiles
  ADD COLUMN IF NOT EXISTS sells        TEXT,
  ADD COLUMN IF NOT EXISTS brand_traits JSONB,   -- ["Premium","Sustainable",...]
  ADD COLUMN IF NOT EXISTS notes        TEXT;
