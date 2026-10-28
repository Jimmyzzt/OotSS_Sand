-- Expand only the map constraint. Preserve every report, identifier and index.
CREATE TABLE feedback_intro (
  id TEXT PRIMARY KEY,
  request_key TEXT NOT NULL UNIQUE,
  payload_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  type TEXT NOT NULL CHECK(type IN ('mismatch','duplicate','missing','other')),
  map_id TEXT NOT NULL CHECK(map_id IN ('overworld','sky','underworld','intro')),
  level_id TEXT,
  description TEXT NOT NULL,
  evidence_url TEXT NOT NULL DEFAULT '',
  context_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','confirmed','fixed','duplicate','invalid')),
  admin_note TEXT NOT NULL DEFAULT '',
  updated_by TEXT NOT NULL DEFAULT ''
);
INSERT INTO feedback_intro SELECT * FROM feedback;
DROP TABLE feedback;
ALTER TABLE feedback_intro RENAME TO feedback;
CREATE INDEX feedback_status_created ON feedback(status,created_at DESC,id DESC);
CREATE INDEX feedback_created ON feedback(created_at DESC,id DESC);
CREATE INDEX feedback_level ON feedback(level_id,created_at DESC);
