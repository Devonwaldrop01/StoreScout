-- SQLite only. NEVER run this against the legacy Supabase database.
BEGIN IMMEDIATE;
CREATE TABLE batches (
 digest TEXT PRIMARY KEY, manifest TEXT NOT NULL, stopped_reason TEXT,
 created_at REAL NOT NULL
);
CREATE TABLE store_index_v2 (
 canonical TEXT PRIMARY KEY, fetch_host TEXT NOT NULL, row_json TEXT,
 eligible INTEGER NOT NULL DEFAULT 0 CHECK(eligible IN (0,1)),
 exclusion TEXT, updated_at REAL NOT NULL
);
CREATE TABLE provenance_v2 (
 batch TEXT NOT NULL REFERENCES batches(digest), canonical TEXT NOT NULL REFERENCES store_index_v2(canonical),
 hostname TEXT NOT NULL, evidence TEXT NOT NULL,
 PRIMARY KEY(batch,canonical,hostname,evidence)
);
CREATE TABLE jobs_v2 (
 canonical TEXT PRIMARY KEY REFERENCES store_index_v2(canonical), batch TEXT NOT NULL REFERENCES batches(digest),
 state TEXT NOT NULL CHECK(state IN ('pending','claimed','verifying','verified','failed','classifying','eligible','ineligible')),
 attempts INTEGER NOT NULL DEFAULT 0, next_due REAL NOT NULL DEFAULT 0,
 owner TEXT, lease_until REAL, attempt_id TEXT, last_result TEXT
);
CREATE TABLE store_verification_v2 (
 attempt_id TEXT PRIMARY KEY, canonical TEXT NOT NULL REFERENCES jobs_v2(canonical),
 batch TEXT NOT NULL REFERENCES batches(digest), owner TEXT NOT NULL,
 started_at REAL NOT NULL, finished_at REAL, outcome TEXT,
 reserved_requests INTEGER NOT NULL, result_json TEXT, result_hash TEXT
);
CREATE TABLE store_classification_v2 (
 attempt_id TEXT PRIMARY KEY REFERENCES store_verification_v2(attempt_id),
 attempted_at REAL NOT NULL, saved_at REAL, confidence REAL,
 eligible INTEGER, exclusion TEXT, result_json TEXT, metrics_json TEXT
);
CREATE TABLE events_v2 (
 id INTEGER PRIMARY KEY, attempt_id TEXT NOT NULL, state TEXT NOT NULL, at REAL NOT NULL
);
CREATE INDEX jobs_v2_due ON jobs_v2(batch,state,next_due);
CREATE INDEX attempts_v2_batch ON store_verification_v2(batch,finished_at);
PRAGMA user_version=1;
COMMIT;
