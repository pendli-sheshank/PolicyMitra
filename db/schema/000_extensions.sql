-- Extensions + schema separation.
-- kb    = Layer 1 Knowledge Base (non-personal, memory.md)
-- mem   = Layers 2-3 Session + User Profile Memory (personal)
-- agent = Layer 4 Agent-Mode Client Notes (B2B, per-agent)
-- audit = Guardrail / response audit trail (own retention policy, outlives mem deletion)

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE SCHEMA IF NOT EXISTS kb;
CREATE SCHEMA IF NOT EXISTS mem;
CREATE SCHEMA IF NOT EXISTS agent;
CREATE SCHEMA IF NOT EXISTS audit;
