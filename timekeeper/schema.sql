PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS clients (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, contact TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '',
 phone TEXT NOT NULL DEFAULT '', rate_cents INTEGER NOT NULL CHECK(rate_cents>=0), color TEXT NOT NULL DEFAULT 'green',
 notes TEXT NOT NULL DEFAULT '', archived INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS entries (
 id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES clients(id), rate_cents INTEGER NOT NULL CHECK(rate_cents>=0),
 started_at INTEGER NOT NULL, ended_at INTEGER, status TEXT NOT NULL CHECK(status IN ('running','draft','complete')),
 summary TEXT NOT NULL DEFAULT '', deliverables TEXT NOT NULL DEFAULT '', next_steps TEXT NOT NULL DEFAULT '',
 private_notes TEXT NOT NULL DEFAULT '', revision INTEGER NOT NULL DEFAULT 0,
 CHECK(ended_at IS NULL OR ended_at>=started_at),
 CHECK((status='running' AND ended_at IS NULL) OR (status IN ('draft','complete') AND ended_at IS NOT NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_entry ON entries((1)) WHERE status IN ('running','draft');
CREATE INDEX IF NOT EXISTS entries_client_date ON entries(client_id,started_at);
CREATE TABLE IF NOT EXISTS documents (
 id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES clients(id), name TEXT NOT NULL, size INTEGER NOT NULL,
 content BLOB NOT NULL, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY, client_id TEXT REFERENCES clients(id), title TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('call','focus','off','deadline')),
 starts_at INTEGER NOT NULL, ends_at INTEGER NOT NULL CHECK(ends_at>starts_at),
 notes TEXT NOT NULL DEFAULT '', revision INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS events_start ON events(starts_at);
CREATE TABLE IF NOT EXISTS login_attempts (created_at INTEGER NOT NULL);
