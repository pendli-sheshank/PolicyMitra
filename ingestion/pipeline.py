"""Orchestrates parse -> chunk -> embed -> upsert for one insurer directory.

Idempotent per doc_version: re-running against the same insurer/product/
version wipes and re-inserts that document's chunks, and marks any older
version of the same insurer/product as no longer current (kb.documents.
is_current) so answers stay traceable to a specific document version
(memory.md Layer 1).
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pgvector.psycopg import Vector

from db.connection import get_connection
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
        cur.execute(
            """
            UPDATE kb.documents SET is_current = false
            WHERE insurer = %s AND product_name = %s AND doc_version != %s
            """,
            (meta.insurer, meta.product_name, meta.doc_version),
        )
        cur.execute(
            """
            INSERT INTO kb.documents (insurer, product_name, doc_version, effective_date, source_path)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (insurer, product_name, doc_version)
            DO UPDATE SET source_path = EXCLUDED.source_path, ingested_at = now(), is_current = true
            RETURNING doc_id
            """,
            (meta.insurer, meta.product_name, meta.doc_version, meta.effective_date, str(doc_path)),
        )
        doc_id = cur.fetchone()[0]

        cur.execute("DELETE FROM kb.chunks WHERE doc_id = %s", (doc_id,))

        texts = [c.text_content for c in chunks]
        vectors = embedder.embed(texts) if texts else []

        for chunk, vector in zip(chunks, vectors, strict=True):
            cur.execute(
                """
                INSERT INTO kb.chunks
                    (doc_id, clause_id, chunk_type, section_title, page_number,
                     text_content, table_context, token_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
                "INSERT INTO kb.embeddings (chunk_id, embedding, embedder_name) VALUES (%s, %s, %s)",
                (chunk_id, Vector(vector), embedder.name),
            )

    return len(chunks)
