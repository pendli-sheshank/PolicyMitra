-- Audit log: separate from Session/Profile memory. Internal compliance/debug
-- trail, own longer retention policy, must survive deletion of the
-- session/profile it originated from (breach-reportability under DPDP Act
-- must not depend on a user's deletion request having not yet happened).
-- Deliberately not FK'd to mem_sessions / mem_user_profiles.
--
-- chunk_ids_used is a JSON array of chunk-id strings serialized to TEXT
-- (was UUID[] in Postgres); guardrail_detail is a JSON object as TEXT.

CREATE TABLE IF NOT EXISTS audit_responses (
    response_id         TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' ||
                            substr(hex(randomblob(2)),2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) ||
                            substr(hex(randomblob(2)),2) || '-' || hex(randomblob(6)))),
    session_id          TEXT,
    agent_id            TEXT,
    module              TEXT NOT NULL CHECK (module IN ('qa', 'recommendation', 'comparison', 'drafting')),
    query_text          TEXT NOT NULL,
    response_text       TEXT NOT NULL,
    chunk_ids_used       TEXT NOT NULL DEFAULT '[]',
    guardrail_verdict   TEXT NOT NULL CHECK (guardrail_verdict IN ('pass', 'repaired', 'blocked')),
    guardrail_detail    TEXT,
    confidence_score    REAL,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00','now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_responses (created_at);
CREATE INDEX IF NOT EXISTS idx_audit_module ON audit_responses (module);
