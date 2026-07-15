"""FastAPI dependencies: DB connections, agent instances, and the request-time
identity dependency for Module 3's agent-scoped Layer-4 endpoints."""

from __future__ import annotations

import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import psycopg
from fastapi import Header, HTTPException

from agents.comparison_agent import ComparisonAgent
from agents.drafting_agent import DraftingAgent
from agents.guardrail_agent import GuardrailAgent
from agents.llm_client import get_llm_client
from agents.qa_agent import QAAgent
from agents.recommendation_agent import RecommendationAgent
from agents.retrieval_agent import RetrievalAgent
from agents.router_agent import RouterAgent
from db.connection import get_connection
from ingestion.embedding import get_default_embedder
from retrieval.reranker import LexicalOverlapReranker

_embedder = get_default_embedder()  # OpenAI when OPENAI_API_KEY is set, else offline local
_reranker = LexicalOverlapReranker()
_llm_client = get_llm_client()  # computed once at startup, reflects env at boot


def get_conn() -> Generator[psycopg.Connection, None, None]:
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


def expire_sessions(conn: psycopg.Connection) -> None:
    """Lazy TTL sweep, run on every session touch (docs/architecture.md #8 —
    no pg_cron dependency assumed)."""
    conn.execute("SELECT mem.expire_sessions()")


def touch_session(conn: psycopg.Connection, session_id: UUID | None, mode: str = "consumer") -> UUID:
    """Lazily expires stale sessions on every touch, then validates or
    creates a session."""
    with conn.cursor() as cur:
        expire_sessions(conn)

        if session_id is not None:
            cur.execute("SELECT session_id FROM mem.sessions WHERE session_id = %s", (session_id,))
            if cur.fetchone() is not None:
                cur.execute(
                    "UPDATE mem.sessions SET last_active_at = now() WHERE session_id = %s",
                    (session_id,),
                )
                return session_id

        ttl_hours = int(os.environ.get("SESSION_TTL_HOURS", "24"))
        expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)
        cur.execute(
            "INSERT INTO mem.sessions (expires_at, mode) VALUES (%s, %s) RETURNING session_id",
            (expires_at, mode),
        )
        return cur.fetchone()[0]
