-- Layer 1: Knowledge Base. Non-personal, insurer-published documents.
-- Postgres-era schemas (kb/mem/agent/audit) are collapsed into table-name
-- prefixes; the kb_ prefix keeps the same deletion-safety property: a deletion
-- request against mem_/agent_ tables can never touch kb_ tables (memory.md).

CREATE TABLE IF NOT EXISTS kb_documents (
    doc_id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' ||
                        substr(hex(randomblob(2)),2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) ||
                        substr(hex(randomblob(2)),2) || '-' || hex(randomblob(6)))),
    insurer         TEXT NOT NULL,
    product_name    TEXT NOT NULL,
    doc_version     TEXT NOT NULL,
    effective_date  TEXT NOT NULL,
    source_path     TEXT NOT NULL,
    ingested_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00','now')),
    is_current      INTEGER NOT NULL DEFAULT 1,
    UNIQUE (insurer, product_name, doc_version)
);

CREATE TABLE IF NOT EXISTS kb_chunks (
    chunk_id        TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' ||
                        substr(hex(randomblob(2)),2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) ||
                        substr(hex(randomblob(2)),2) || '-' || hex(randomblob(6)))),
    doc_id          TEXT NOT NULL REFERENCES kb_documents(doc_id) ON DELETE CASCADE,
    clause_id       TEXT NOT NULL,
    chunk_type      TEXT NOT NULL CHECK (chunk_type IN ('prose', 'table_row', 'table_block', 'heading')),
    section_title   TEXT,
    page_number     INTEGER,
    text_content    TEXT NOT NULL,
    table_context   TEXT,
    token_count     INTEGER NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00','now'))
);

CREATE INDEX IF NOT EXISTS idx_kb_chunks_doc ON kb_chunks (doc_id);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_clause ON kb_chunks (clause_id);

-- Full-text index. External-content FTS5 against kb_chunks, kept in sync by
-- the triggers below (so the pipeline's DELETE + re-INSERT during re-ingest
-- maintains the index with no explicit sync code). Porter stemming mirrors
-- the stemming behaviour of the previous Postgres 'english' text-search
-- config — the main defence against retrieval-recall regression.
CREATE VIRTUAL TABLE IF NOT EXISTS kb_chunks_fts USING fts5(
    text_content,
    content='kb_chunks',
    content_rowid='rowid',
    tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS trg_kb_chunks_ai AFTER INSERT ON kb_chunks BEGIN
    INSERT INTO kb_chunks_fts(rowid, text_content) VALUES (new.rowid, new.text_content);
END;

CREATE TRIGGER IF NOT EXISTS trg_kb_chunks_ad AFTER DELETE ON kb_chunks BEGIN
    INSERT INTO kb_chunks_fts(kb_chunks_fts, rowid, text_content) VALUES ('delete', old.rowid, old.text_content);
END;

CREATE TRIGGER IF NOT EXISTS trg_kb_chunks_au AFTER UPDATE OF text_content ON kb_chunks BEGIN
    INSERT INTO kb_chunks_fts(kb_chunks_fts, rowid, text_content) VALUES ('delete', old.rowid, old.text_content);
    INSERT INTO kb_chunks_fts(rowid, text_content) VALUES (new.rowid, new.text_content);
END;

-- Embedding dimension fixed at 384 to match the no-API-key local fallback
-- embedder (see docs/architecture.md #2): 384 packed little-endian float32
-- values = 1536 bytes per BLOB. Swapping providers with a different dimension
-- just requires a re-embed (the BLOB carries no declared dimension).
CREATE TABLE IF NOT EXISTS kb_embeddings (
    chunk_id        TEXT PRIMARY KEY REFERENCES kb_chunks(chunk_id) ON DELETE CASCADE,
    embedding       BLOB NOT NULL,
    embedder_name   TEXT NOT NULL,
    embedded_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00','now'))
);
