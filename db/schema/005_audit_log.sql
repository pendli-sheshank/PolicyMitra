-- Audit log: separate from Session/Profile memory. Internal compliance/debug
-- trail, own longer retention policy, must survive deletion of the
-- session/profile it originated from (breach-reportability under DPDP Act
-- must not depend on a user's deletion request having not yet happened).
-- Deliberately not FK'd to mem.sessions / mem.user_profiles.

CREATE TABLE IF NOT EXISTS audit.responses (
    response_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID,
    agent_id            TEXT,
    module              TEXT NOT NULL CHECK (module IN ('qa', 'recommendation', 'comparison', 'drafting')),
    query_text          TEXT NOT NULL,
    response_text       TEXT NOT NULL,
    chunk_ids_used       UUID[] NOT NULL DEFAULT '{}',
    guardrail_verdict   TEXT NOT NULL CHECK (guardrail_verdict IN ('pass', 'repaired', 'blocked')),
    guardrail_detail    JSONB,
    confidence_score    NUMERIC(4, 3),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_created ON audit.responses (created_at);
CREATE INDEX IF NOT EXISTS idx_audit_module ON audit.responses (module);
