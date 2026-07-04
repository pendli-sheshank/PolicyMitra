"""Writes every response to audit_responses — separate from Session/Profile
memory (memory.md §7), and never skipped regardless of the Guardrail
verdict (agents.md: "always log it")."""

from __future__ import annotations

import json
import sqlite3
from uuid import UUID


def write_audit_entry(
    conn: sqlite3.Connection,
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
            INSERT INTO audit_responses
                (session_id, agent_id, module, query_text, response_text, chunk_ids_used,
                 guardrail_verdict, guardrail_detail, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING response_id
            """,
            (
                session_id,
                agent_id,
                module,
                query_text,
                response_text,
                json.dumps([str(cid) for cid in chunk_ids_used]),
                guardrail_verdict,
                json.dumps(guardrail_detail),
                confidence_score,
            ),
        )
        return UUID(cur.fetchone()[0])
