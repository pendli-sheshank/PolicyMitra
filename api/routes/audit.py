"""Internal debug/compliance endpoint: returns the full audit trail for a
response, including exact chunk_ids_used (PRD F11 auditability)."""

from __future__ import annotations

import json
import sqlite3
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_conn

router = APIRouter()

_SELECT_COLUMNS = (
    "response_id, session_id, agent_id, module, query_text, response_text, "
    "chunk_ids_used, guardrail_verdict, guardrail_detail, confidence_score, created_at"
)


@router.get("/audit/{response_id}")
def get_audit_entry(response_id: UUID, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    with conn.cursor() as cur:
        cur.execute(f"SELECT {_SELECT_COLUMNS} FROM audit_responses WHERE response_id = ?", (response_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Audit entry not found.")
    return {
        "response_id": row[0],
        "session_id": row[1],
        "agent_id": row[2],
        "module": row[3],
        "query_text": row[4],
        "response_text": row[5],
        "chunk_ids_used": json.loads(row[6]),
        "guardrail_verdict": row[7],
        "guardrail_detail": json.loads(row[8]) if row[8] is not None else None,
        "confidence_score": row[9],
        "created_at": row[10],
    }
