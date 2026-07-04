"""Orchestrates parse -> chunk -> embed -> upsert for one insurer directory.

Idempotent per doc_version: re-running against the same insurer/product/
version wipes and re-inserts that document's chunks (the FTS5 sync triggers
keep the full-text index consistent through the delete+reinsert), and marks
any older version of the same insurer/product as no longer current
(kb_documents.is_current) so answers stay traceable to a specific document
version (memory.md Layer 1).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from db.connection import get_connection, pack_vector, utc_now_iso
from ingestion.chunking.clause_chunker import chunk_prose
from ingestion.chunking.models import Chunk, DocumentMeta
from ingestion.chunking.table_chunker import chunk_table
from ingestion.embedding.base import Embedder
from ingestion.parsers.markdown_parser import MarkdownParser


def load_meta(insurer_dir: Path) -> DocumentMeta:
    data = yaml.safe_load((insurer_dir / "meta.yaml").read_text(encoding="utf-8"))
    return DocumentMeta(**data)


def build_chunks(insurer_dir: Path) -> list[Chunk]:
    meta = load_meta(insurer_dir)
    doc_path = insurer_dir / "policy_wording.md"
    raw_doc = MarkdownParser().parse(doc_path, meta)

    chunks: list[Chunk] = []
    for block in raw_doc.blocks:
        if block.block_type == "table":
            chunks.extend(chunk_table(block, meta))
        elif block.block_type == "prose":
            chunks.extend(chunk_prose(block, meta))
    return chunks


def run_ingestion(insurer_dir: Path, embedder: Embedder) -> int:
    meta = load_meta(insurer_dir)
    doc_path = insurer_dir / "policy_wording.md"
    chunks = build_chunks(insurer_dir)

    with get_connection() as conn, conn.cursor() as cur:
        # One explicit transaction per document: connections are otherwise in
        # autocommit mode, and per-statement fsync would make ingest crawl.
        cur.execute("BEGIN")
        try:
            cur.execute(
                """
                UPDATE kb_documents SET is_current = 0
                WHERE insurer = ? AND product_name = ? AND doc_version != ?
                """,
                (meta.insurer, meta.product_name, meta.doc_version),
            )
            cur.execute(
                """
                INSERT INTO kb_documents (insurer, product_name, doc_version, effective_date, source_path)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (insurer, product_name, doc_version)
                DO UPDATE SET source_path = excluded.source_path, ingested_at = ?, is_current = 1
                RETURNING doc_id
                """,
                (meta.insurer, meta.product_name, meta.doc_version, meta.effective_date, str(doc_path), utc_now_iso()),
            )
            doc_id = cur.fetchone()[0]

            cur.execute("DELETE FROM kb_chunks WHERE doc_id = ?", (doc_id,))

            texts = [c.text_content for c in chunks]
            vectors = embedder.embed(texts) if texts else []

            for chunk, vector in zip(chunks, vectors, strict=True):
                cur.execute(
                    """
                    INSERT INTO kb_chunks
                        (doc_id, clause_id, chunk_type, section_title, page_number,
                         text_content, table_context, token_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    RETURNING chunk_id
                    """,
                    (
                        doc_id,
                        chunk.metadata.clause_id,
                        chunk.metadata.chunk_type,
                        chunk.metadata.section_title,
                        chunk.metadata.page_number,
                        chunk.text_content,
                        chunk.table_context,
                        chunk.token_count,
                    ),
                )
                chunk_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO kb_embeddings (chunk_id, embedding, embedder_name) VALUES (?, ?, ?)",
                    (chunk_id, pack_vector(vector), embedder.name),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return len(chunks)
