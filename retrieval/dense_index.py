"""Dense semantic search: brute-force cosine similarity over float32 BLOB
embeddings, computed in Python. At this corpus size (a few hundred chunks x
384 dims) a full scan is sub-10ms — an ANN index or numpy would be pure
overhead (see docs/architecture.md #2)."""

from __future__ import annotations

import heapq
import math
import sqlite3
from uuid import UUID

from db.connection import unpack_vector
from retrieval.models import RetrievalFilters


def dense_search(
    conn: sqlite3.Connection,
    query_embedding: list[float],
    k: int,
    filters: RetrievalFilters | None = None,
) -> list[tuple[UUID, float]]:
    filters = filters or RetrievalFilters()
    conditions = ["d.is_current = 1"]
    params: dict = {}

    if filters.insurer:
        conditions.append("d.insurer = :insurer")
        params["insurer"] = filters.insurer
    if filters.product_name:
        conditions.append("d.product_name = :product_name")
        params["product_name"] = filters.product_name

    sql = f"""
        SELECT e.chunk_id, e.embedding
        FROM kb_embeddings e
        JOIN kb_chunks c ON c.chunk_id = e.chunk_id
        JOIN kb_documents d ON c.doc_id = d.doc_id
        WHERE {" AND ".join(conditions)}
    """

    q_norm = math.sqrt(sum(x * x for x in query_embedding))
    if q_norm == 0.0:
        return []

    scored: list[tuple[float, UUID]] = []
    with conn.cursor() as cur:
        cur.execute(sql, params)
        for chunk_id, blob in cur.fetchall():
            vec = unpack_vector(blob)
            dot = 0.0
            norm_sq = 0.0
            for qx, vx in zip(query_embedding, vec, strict=True):
                dot += qx * vx
                norm_sq += vx * vx
            if norm_sq == 0.0:
                continue
            # Full cosine, not just dot product: local hash embeddings are
            # pre-normalized but external providers' may not be.
            score = dot / (q_norm * math.sqrt(norm_sq))
            scored.append((score, UUID(chunk_id)))

    top = heapq.nlargest(k, scored)
    return [(chunk_id, score) for score, chunk_id in top]
