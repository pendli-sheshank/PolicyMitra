"""Hybrid retrieval: BM25 + dense candidates merged via Reciprocal Rank
Fusion (rank-based, avoids normalizing two incomparable score scales — see
docs/architecture.md #4), then optionally reranked."""

from __future__ import annotations

import sqlite3
from uuid import UUID

from ingestion.embedding.base import Embedder
from retrieval.bm25_index import bm25_search
from retrieval.dense_index import dense_search
from retrieval.models import RetrievalFilters, RetrievalResult
from retrieval.reranker import Reranker
from retrieval.store import fetch_chunks

RRF_K = 60


def reciprocal_rank_fusion(ranked_lists: list[list[tuple[UUID, float]]], k: int = RRF_K) -> dict[UUID, float]:
    scores: dict[UUID, float] = {}
    for ranked in ranked_lists:
        for rank, (chunk_id, _raw_score) in enumerate(ranked, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return scores


def hybrid_search(
    conn: sqlite3.Connection,
    query: str,
    embedder: Embedder,
    k: int = 5,
    candidate_k: int = 20,
    filters: RetrievalFilters | None = None,
    reranker: Reranker | None = None,
) -> RetrievalResult:
    bm25_hits = bm25_search(conn, query, candidate_k, filters)
    query_vector = embedder.embed([query])[0]
    dense_hits = dense_search(conn, query_vector, candidate_k, filters)

    fused = reciprocal_rank_fusion([bm25_hits, dense_hits])
    if not fused:
        return RetrievalResult(query=query, chunks=[])

    ranked_ids = sorted(fused, key=lambda cid: fused[cid], reverse=True)[:candidate_k]
    hydrated = fetch_chunks(conn, ranked_ids)

    candidates = []
    for chunk_id in ranked_ids:
        chunk = hydrated.get(chunk_id)
        if chunk is None:
            continue
        chunk.score = fused[chunk_id]
        candidates.append(chunk)

    if reranker is not None:
        candidates = reranker.rerank(query, candidates)
    else:
        candidates.sort(key=lambda c: c.score, reverse=True)

    return RetrievalResult(query=query, chunks=candidates[:k])
