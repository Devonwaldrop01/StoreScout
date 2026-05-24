-- Separate "email sent" (alert_sent) from "user read in app" (read_at).
-- alert_sent: used only by the Celery cooldown check — do not touch.
-- read_at:    set when the user views the alerts page or clicks mark-read.
--             NULL = unread in-app. Used by unread_count and mark-read endpoints.

ALTER TABLE change_events
  ADD COLUMN IF NOT EXISTS read_at TIMESTAMPTZ;

-- Index so the unread-count query is fast
CREATE INDEX IF NOT EXISTS idx_change_events_read_at
  ON change_events (competitor_id, read_at)
  WHERE read_at IS NULL;
