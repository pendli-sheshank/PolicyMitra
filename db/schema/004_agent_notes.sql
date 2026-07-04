-- Layer 4: Agent-Mode Client Notes (B2B, Module 3). Belongs to the licensed
-- agent's own book of business — scoped per agent login, never shared across
-- agents, never joined into kb (memory.md).

CREATE TABLE IF NOT EXISTS agent_agents (
    agent_id        TEXT PRIMARY KEY,
    display_name    TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00','now'))
);

CREATE TABLE IF NOT EXISTS agent_client_notes (
    note_id             TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' ||
                            substr(hex(randomblob(2)),2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) ||
                            substr(hex(randomblob(2)),2) || '-' || hex(randomblob(6)))),
    agent_id            TEXT NOT NULL REFERENCES agent_agents(agent_id) ON DELETE CASCADE,
    client_ref          TEXT NOT NULL,
    note_content         TEXT NOT NULL,
    related_draft_id    TEXT,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00','now')),
    updated_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00','now'))
);

CREATE INDEX IF NOT EXISTS idx_agent_notes_scope ON agent_client_notes (agent_id);
