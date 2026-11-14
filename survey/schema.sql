PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS surveys (
 id TEXT PRIMARY KEY, token TEXT NOT NULL UNIQUE, title TEXT NOT NULL, description TEXT NOT NULL,
 thank_you TEXT NOT NULL, questions TEXT NOT NULL DEFAULT '[]', state TEXT NOT NULL DEFAULT 'draft' CHECK(state IN ('draft','open','closed')),
 revision INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, published_at INTEGER
);
CREATE TABLE IF NOT EXISTS photos (id TEXT PRIMARY KEY, survey_id TEXT NOT NULL REFERENCES surveys(id), content BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS responses (
 id TEXT PRIMARY KEY, survey_id TEXT NOT NULL REFERENCES surveys(id), nonce TEXT NOT NULL UNIQUE,
 answers TEXT NOT NULL, created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS responses_survey ON responses(survey_id,created_at);
CREATE TABLE IF NOT EXISTS attempts (bucket TEXT NOT NULL, created_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS attempts_time ON attempts(created_at);
