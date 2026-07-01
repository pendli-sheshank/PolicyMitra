"""Dense semantic search via pgvector cosine similarity."""

from __future__ import annotations

from uuid import UUID

import psycopg
from pgvector.psycopg import Vector

from retrieval.models import RetrievalFilters


def dense_search(
    conn: psycopg.Connection,
    query_embedding: list[float],
    k: int,
    filters: RetrievalFilters | None = None,
) -> list[tuple[UUID, float]]:
    filters = filters or RetrievalFilters()
    conditions = ["d.is_current = true"]
    params: dict = {"qvec": Vector(query_embedding), "k": k}

    if filters.insurer:
        conditions.append("d.insurer = %(insurer)s")
        params["insurer"] = filters.insurer
    if filters.product_name:
        conditions.append("d.product_name = %(product_name)s")
        params["product_name"] = filters.product_name

    sql = f"""
        SELECT e.chunk_id, 1 - (e.embedding <=> %(qvec)s) AS score
        FROM kb.embeddings e
        JOIN kb.chunks c ON c.chunk_id = e.chunk_id
        JOIN kb.documents d ON c.doc_id = d.doc_id
        WHERE {" AND ".join(conditions)}
        ORDER BY e.embedding <=> %(qvec)s
        LIMIT %(k)s
    """
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [(row[0], float(row[1])) for row in cur.fetchall()]
