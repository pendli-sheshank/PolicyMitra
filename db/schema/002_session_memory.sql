-- Layer 2: Session Memory. Conversation-level, short-lived, auto-expiring.
-- Not persisted to a user profile unless the user explicitly opts into Layer 3.

CREATE TABLE IF NOT EXISTS mem.sessions (
    session_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,
    last_active_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    mode            TEXT NOT NULL DEFAULT 'consumer' CHECK (mode IN ('consumer', 'agent'))
);

CREATE INDEX IF NOT EXISTS idx_mem_sessions_expires ON mem.sessions (expires_at);

CREATE TABLE IF NOT EXISTS mem.session_turns (
    turn_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES mem.sessions(session_id) ON DELETE CASCADE,
    turn_index      INTEGER NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,             -- redacted before insert, see ingestion/../api redaction helper
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (session_id, turn_index)
);

-- Structured slots only (memory.md "What NOT to Persist": prefer has_diabetes:true
-- over the verbatim sentence). ailments_flagged holds structured booleans, never prose.
CREATE TABLE IF NOT EXISTS mem.session_slots (
    session_id          UUID PRIMARY KEY REFERENCES mem.sessions(session_id) ON DELETE CASCADE,
    age                 INTEGER,
    city_tier           TEXT CHECK (city_tier IN ('tier1', 'tier2', 'tier3')),
    dependents          INTEGER,
    ailments_flagged    JSONB NOT NULL DEFAULT '{}'::jsonb,
    insurer_mentioned   TEXT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Lazy TTL sweep: called on every session read (api/deps.py). Also runnable
-- standalone via api/jobs/expire_sessions.py for a real cron deployment.
-- No pg_cron dependency assumed (see docs/architecture.md #8).
CREATE OR REPLACE FUNCTION mem.expire_sessions() RETURNS void AS $$
    DELETE FROM mem.sessions WHERE expires_at < now();
$$ LANGUAGE sql;
