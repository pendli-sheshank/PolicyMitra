"""FastAPI dependencies: DB connections, agent instances, and the request-time
identity dependency for Module 3's agent-scoped Layer-4 endpoints."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Header, HTTPException

from agents.comparison_agent import ComparisonAgent
from agents.drafting_agent import DraftingAgent
from agents.guardrail_agent import GuardrailAgent
from agents.llm_client import get_llm_client
from agents.qa_agent import QAAgent
from agents.recommendation_agent import RecommendationAgent
from agents.retrieval_agent import RetrievalAgent
from agents.router_agent import RouterAgent
from db.connection import get_connection, utc_now_iso
from ingestion.embedding.local_hash_embedder import LocalHashEmbedder
from retrieval.reranker import LexicalOverlapReranker

_embedder = LocalHashEmbedder()
_reranker = LexicalOverlapReranker()
_llm_client = get_llm_client()  # computed once at startup, reflects env at boot


def get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def get_router_agent() -> RouterAgent:
    return RouterAgent(_llm_client)


def get_retrieval_agent() -> RetrievalAgent:
    return RetrievalAgent(_embedder, reranker=_reranker, llm_client=_llm_client)


def get_qa_agent() -> QAAgent:
    threshold = float(os.environ.get("RETRIEVAL_CONF_THRESHOLD", "0.35"))
    return QAAgent(_llm_client, confidence_threshold=threshold)


def get_guardrail_agent() -> GuardrailAgent:
    return GuardrailAgent(_llm_client)


def get_recommendation_agent() -> RecommendationAgent:
    return RecommendationAgent(_llm_client)


def get_comparison_agent() -> ComparisonAgent:
    return ComparisonAgent()


def get_drafting_agent() -> DraftingAgent:
    return DraftingAgent(_llm_client)


def get_current_agent_id(x_agent_id: str | None = Header(default=None)) -> str:
    if not x_agent_id:
        raise HTTPException(status_code=401, detail="X-Agent-Id header is required for agent-copilot endpoints.")
    return x_agent_id


def expire_sessions(conn: sqlite3.Connection) -> None:
    """Lazy TTL sweep, run on every session touch (docs/architecture.md #8 —
    no scheduler dependency assumed). Timestamps are ISO-8601 UTC TEXT, so a
    lexicographic comparison is a chronological one."""
    conn.execute("DELETE FROM mem_sessions WHERE expires_at < ?", (utc_now_iso(),))


def touch_session(conn: sqlite3.Connection, session_id: UUID | None, mode: str = "consumer") -> UUID:
    """Lazily expires stale sessions on every touch, then validates or
    creates a session."""
    with conn.cursor() as cur:
        expire_sessions(conn)

        if session_id is not None:
            cur.execute("SELECT session_id FROM mem_sessions WHERE session_id = ?", (session_id,))
            if cur.fetchone() is not None:
                cur.execute(
                    "UPDATE mem_sessions SET last_active_at = ? WHERE session_id = ?",
                    (utc_now_iso(), session_id),
                )
                return session_id

        ttl_hours = int(os.environ.get("SESSION_TTL_HOURS", "24"))
        expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)
        cur.execute(
            "INSERT INTO mem_sessions (expires_at, mode) VALUES (?, ?) RETURNING session_id",
            (expires_at, mode),
        )
        return UUID(cur.fetchone()[0])
