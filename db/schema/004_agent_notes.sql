-- Layer 4: Agent-Mode Client Notes (B2B, Module 3). Belongs to the licensed
-- agent's own book of business — scoped per agent login, never shared across
-- agents, never joined into kb (memory.md).

CREATE TABLE IF NOT EXISTS agent.agents (
    agent_id        TEXT PRIMARY KEY,
    display_name    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent.client_notes (
    note_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id            TEXT NOT NULL REFERENCES agent.agents(agent_id) ON DELETE CASCADE,
    client_ref          TEXT NOT NULL,
    note_content         TEXT NOT NULL,
    related_draft_id    UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_notes_scope ON agent.client_notes (agent_id);
