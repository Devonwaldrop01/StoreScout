-- ────────────────────────────────────────────────────────────────────────────
-- My Store: the user's own store, tracked as a flagged competitor row so it
-- reuses the entire scan pipeline (scan, snapshot, insights, brand profile).
-- It does NOT count against the competitor tracking limit and is hidden from
-- the competitor grid. The comparison engine reads its latest snapshot.
-- ────────────────────────────────────────────────────────────────────────────

ALTER TABLE competitors
  ADD COLUMN IF NOT EXISTS is_my_store BOOLEAN NOT NULL DEFAULT false;

-- One "my store" per user.
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_my_store_per_user
  ON competitors(user_id)
  WHERE is_my_store = true;
