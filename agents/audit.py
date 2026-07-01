"""Writes every response to audit.responses — separate from Session/Profile
memory (memory.md §7), and never skipped regardless of the Guardrail
verdict (agents.md: "always log it")."""

from __future__ import annotations

import json
from uuid import UUID

import psycopg


def write_audit_entry(
    conn: psycopg.Connection,
    module: str,
    query_text: str,
    response_text: str,
    chunk_ids_used: list[UUID],
    guardrail_verdict: str,
    guardrail_detail: list[dict],
    confidence_score: float | None,
    session_id: UUID | None = None,
    agent_id: str | None = None,
) -> UUID:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO audit.responses
                (session_id, agent_id, module, query_text, response_text, chunk_ids_used,
                 guardrail_verdict, guardrail_detail, confidence_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING response_id
            """,
            (
                session_id,
                agent_id,
                module,
                query_text,
                response_text,
                chunk_ids_used,
                guardrail_verdict,
                json.dumps(guardrail_detail),
                confidence_score,
            ),
        )
        return cur.fetchone()[0]
