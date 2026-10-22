PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS forms (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, introduction TEXT NOT NULL,
 service TEXT NOT NULL, questions TEXT NOT NULL, auto_publish INTEGER NOT NULL DEFAULT 0,
 created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS invitations (
 id TEXT PRIMARY KEY, form_id TEXT NOT NULL REFERENCES forms(id),
 email TEXT NOT NULL, client_name TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
 expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL,
 mail_status TEXT NOT NULL DEFAULT 'pending', revoked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS responses (
 id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL UNIQUE REFERENCES invitations(id),
 name TEXT NOT NULL, company TEXT NOT NULL, role TEXT NOT NULL,
 quote TEXT NOT NULL, answers TEXT NOT NULL, consent INTEGER NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('private','pending','published','hidden')),
 created_at INTEGER NOT NULL, published_at INTEGER
);
CREATE TABLE IF NOT EXISTS login_attempts (created_at INTEGER NOT NULL);
