"""Hydrates chunk_ids (as returned by bm25/dense search) into full
RetrievedChunk objects with insurer/doc metadata joined in."""

from __future__ import annotations

from uuid import UUID

import psycopg

from retrieval.models import RetrievedChunk


def fetch_chunks(conn: psycopg.Connection, chunk_ids: list[UUID]) -> dict[UUID, RetrievedChunk]:
    if not chunk_ids:
        return {}
    sql = """
        SELECT c.chunk_id, c.doc_id, c.clause_id, c.chunk_type, c.text_content, c.table_context,
               d.insurer, d.product_name, d.doc_version, d.effective_date, c.section_title
        FROM kb.chunks c
        JOIN kb.documents d ON c.doc_id = d.doc_id
        WHERE c.chunk_id = ANY(%(ids)s)
    """
    with conn.cursor() as cur:
        cur.execute(sql, {"ids": chunk_ids})
        rows = cur.fetchall()

    result: dict[UUID, RetrievedChunk] = {}
    for row in rows:
        result[row[0]] = RetrievedChunk(
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
    return result
