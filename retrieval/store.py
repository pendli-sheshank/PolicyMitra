"""Hydrates chunk_ids (as returned by bm25/dense search) into full
RetrievedChunk objects with insurer/doc metadata joined in."""

from __future__ import annotations

import sqlite3
from uuid import UUID

from retrieval.models import RetrievedChunk


def fetch_chunks(conn: sqlite3.Connection, chunk_ids: list[UUID]) -> dict[UUID, RetrievedChunk]:
    if not chunk_ids:
        return {}
    placeholders = ", ".join("?" for _ in chunk_ids)
    sql = f"""
        SELECT c.chunk_id, c.doc_id, c.clause_id, c.chunk_type, c.text_content, c.table_context,
               d.insurer, d.product_name, d.doc_version, d.effective_date, c.section_title
        FROM kb_chunks c
        JOIN kb_documents d ON c.doc_id = d.doc_id
        WHERE c.chunk_id IN ({placeholders})
    """
    with conn.cursor() as cur:
        cur.execute(sql, [str(cid) for cid in chunk_ids])
        rows = cur.fetchall()

    result: dict[UUID, RetrievedChunk] = {}
    for row in rows:
        chunk = RetrievedChunk(
            chunk_id=row[0],
            doc_id=row[1],
            clause_id=row[2],
            chunk_type=row[3],
            text_content=row[4],
            table_context=row[5],
            insurer=row[6],
            product_name=row[7],
            doc_version=row[8],
            effective_date=row[9],
            section_title=row[10],
            score=0.0,
        )
        result[chunk.chunk_id] = chunk
    return result
