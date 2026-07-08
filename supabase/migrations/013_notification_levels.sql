-- Three-level notification system:
--   critical_only — instant emails for critical events, nothing else
--   daily         — instant criticals + ONE Daily Intelligence Brief (default)
--   weekly        — weekly digest only
--   quiet         — in-app only, no email
-- digest_hour is the UTC hour the daily brief is assembled for the user.

ALTER TABLE notification_prefs
  ADD COLUMN IF NOT EXISTS notification_level TEXT NOT NULL DEFAULT 'daily'
    CHECK (notification_level IN ('critical_only', 'daily', 'weekly', 'quiet')),
  ADD COLUMN IF NOT EXISTS digest_hour INT NOT NULL DEFAULT 8
    CHECK (digest_hour >= 0 AND digest_hour <= 23);
