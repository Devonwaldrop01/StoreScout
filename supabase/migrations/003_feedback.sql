-- Feedback / testimonials table
CREATE TABLE IF NOT EXISTS feedback (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID REFERENCES user_profiles(id) ON DELETE SET NULL,
  rating          SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  message         TEXT NOT NULL,
  allow_testimonial BOOLEAN NOT NULL DEFAULT false,
  -- anonymized display name (set by trigger or app)
  initials        TEXT,
  page            TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_testimonial ON feedback(allow_testimonial, rating) WHERE allow_testimonial = true;

-- RLS: users can insert their own; public can read approved testimonials
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can submit feedback"
  ON feedback FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Approved testimonials are public"
  ON feedback FOR SELECT
  TO anon, authenticated
  USING (allow_testimonial = true AND rating >= 4);
