-- Layer 1: Knowledge Base. Non-personal, insurer-published documents.
-- Kept in its own schema so a deletion request against mem/agent can never
-- accidentally touch it, and can never accidentally miss it either (memory.md).

CREATE TABLE IF NOT EXISTS kb.documents (
    doc_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insurer         TEXT NOT NULL,
    product_name    TEXT NOT NULL,
    doc_version     TEXT NOT NULL,
    effective_date  DATE NOT NULL,
    source_path     TEXT NOT NULL,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_current      BOOLEAN NOT NULL DEFAULT true,
    UNIQUE (insurer, product_name, doc_version)
);

CREATE TABLE IF NOT EXISTS kb.chunks (
    chunk_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id          UUID NOT NULL REFERENCES kb.documents(doc_id) ON DELETE CASCADE,
    clause_id       TEXT NOT NULL,
    chunk_type      TEXT NOT NULL CHECK (chunk_type IN ('prose', 'table_row', 'table_block', 'heading')),
    section_title   TEXT,
    page_number     INTEGER,
    text_content    TEXT NOT NULL,
    table_context   TEXT,
    token_count     INTEGER NOT NULL,
    fts             TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', text_content)) STORED,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_kb_chunks_fts ON kb.chunks USING GIN (fts);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_doc ON kb.chunks (doc_id);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_clause ON kb.chunks (clause_id);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_insurer_trgm ON kb.chunks USING GIN (clause_id gin_trgm_ops);

-- Embedding dimension fixed at 1536 to match OpenAI text-embedding-3-small
-- (the production embedder); the no-key local fallback embedder produces the
-- same dimension so both share this column. Swapping to a provider with a
-- different dimension requires ALTER COLUMN + re-embed.
CREATE TABLE IF NOT EXISTS kb.embeddings (
    chunk_id        UUID PRIMARY KEY REFERENCES kb.chunks(chunk_id) ON DELETE CASCADE,
    embedding       VECTOR(1536) NOT NULL,
    embedder_name   TEXT NOT NULL,
    embedded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- HNSW over ivfflat: no training-sample requirement, which matters on a
-- corpus this small (ivfflat lists would be near-empty and recall unstable).
CREATE INDEX IF NOT EXISTS idx_kb_embeddings_hnsw ON kb.embeddings
    USING hnsw (embedding vector_cosine_ops);
