"""Thin wrapper over retrieval/hybrid.py. A retrieval function, not a
generative call, aside from an optional LLM query-rewrite for vague
questions (skipped entirely when no LLM client is configured)."""

from __future__ import annotations

from typing import Any

import psycopg

from agents.base import LLMNotConfiguredError
from ingestion.embedding.base import Embedder
from retrieval.hybrid import hybrid_search
from retrieval.models import RetrievalFilters, RetrievalResult
from retrieval.query_rewrite import rewrite_query
from retrieval.reranker import Reranker

VAGUE_QUERY_MAX_WORDS = 4


class RetrievalAgent:
    def __init__(self, embedder: Embedder, reranker: Reranker | None = None, llm_client: Any | None = None):
        self.embedder = embedder
        self.reranker = reranker
        self.llm_client = llm_client

    def retrieve(
        self,
        conn: psycopg.Connection,
        query: str,
        filters: RetrievalFilters | None = None,
        k: int = 5,
        known_slots: dict | None = None,
    ) -> RetrievalResult:
        effective_query = query
        is_vague = len(query.split()) <= VAGUE_QUERY_MAX_WORDS

        if is_vague and self.llm_client is not None:
            try:
                effective_query = rewrite_query(self.llm_client, query, known_slots or {})
            except LLMNotConfiguredError:
                pass  # no key configured -> search with the original query as-is

        return hybrid_search(conn, effective_query, self.embedder, k=k, filters=filters, reranker=self.reranker)
