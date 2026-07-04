-- Layer 2: Session Memory. Conversation-level, short-lived, auto-expiring.
-- Not persisted to a user profile unless the user explicitly opts into Layer 3.
--
-- Timestamps are UTC ISO-8601 TEXT (single format enforced by
-- db/connection.py utc_now_iso() and the strftime defaults below), so the
-- lazy TTL sweep can compare them lexicographically. The old Postgres
-- mem.expire_sessions() SQL function is now a Python helper in api/deps.py.

CREATE TABLE IF NOT EXISTS mem_sessions (
    session_id      TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' ||
                        substr(hex(randomblob(2)),2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) ||
                        substr(hex(randomblob(2)),2) || '-' || hex(randomblob(6)))),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00','now')),
    expires_at      TEXT NOT NULL,
    last_active_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00','now')),
    mode            TEXT NOT NULL DEFAULT 'consumer' CHECK (mode IN ('consumer', 'agent'))
);

CREATE INDEX IF NOT EXISTS idx_mem_sessions_expires ON mem_sessions (expires_at);

CREATE TABLE IF NOT EXISTS mem_session_turns (
    turn_id         TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' ||
                        substr(hex(randomblob(2)),2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) ||
                        substr(hex(randomblob(2)),2) || '-' || hex(randomblob(6)))),
    session_id      TEXT NOT NULL REFERENCES mem_sessions(session_id) ON DELETE CASCADE,
    turn_index      INTEGER NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,             -- redacted before insert, see api redaction helper
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00','now')),
    UNIQUE (session_id, turn_index)
);

-- Structured slots only (memory.md "What NOT to Persist": prefer has_diabetes:true
-- over the verbatim sentence). ailments_flagged holds structured booleans as a
-- JSON object serialized to TEXT, never prose.
CREATE TABLE IF NOT EXISTS mem_session_slots (
    session_id          TEXT PRIMARY KEY REFERENCES mem_sessions(session_id) ON DELETE CASCADE,
    age                 INTEGER,
    city_tier           TEXT CHECK (city_tier IN ('tier1', 'tier2', 'tier3')),
    dependents          INTEGER,
    ailments_flagged    TEXT NOT NULL DEFAULT '{}',
    insurer_mentioned   TEXT,
    updated_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00','now'))
);
