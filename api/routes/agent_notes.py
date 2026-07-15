"""Layer 4 Agent-Mode Client Notes (B2B, Module 3): scoped per agent login,
never shared across agents, never joined into kb (memory.md). Every query is
filtered by agent_id server-side (from X-Agent-Id, not client-suppliable in
the body) so cross-agent leakage is structurally impossible even if a
note_id is guessed."""

from __future__ import annotations

from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_conn, get_current_agent_id
from api.schemas.agent_notes import ClientNoteCreateRequest, ClientNoteResponse

router = APIRouter()

_SELECT_COLUMNS = "note_id, agent_id, client_ref, note_content, related_draft_id, created_at, updated_at"


def _row_to_response(row) -> ClientNoteResponse:
    return ClientNoteResponse(
        note_id=row[0],
        agent_id=row[1],
        client_ref=row[2],
        note_content=row[3],
        related_draft_id=row[4],
        created_at=row[5],
        updated_at=row[6],
    )


def _require_path_matches_identity(agent_id: str, current_agent_id: str) -> None:
    if agent_id != current_agent_id:
        raise HTTPException(status_code=403, detail="X-Agent-Id does not match the path agent_id.")


@router.post("/agent/{agent_id}/notes", response_model=ClientNoteResponse)
def create_note(
    agent_id: str,
    request: ClientNoteCreateRequest,
    conn: psycopg.Connection = Depends(get_conn),
    current_agent_id: str = Depends(get_current_agent_id),
) -> ClientNoteResponse:
    _require_path_matches_identity(agent_id, current_agent_id)
    with conn.cursor() as cur:
        cur.execute("INSERT INTO agent.agents (agent_id) VALUES (%s) ON CONFLICT DO NOTHING", (agent_id,))
        cur.execute(
            f"""
            INSERT INTO agent.client_notes (agent_id, client_ref, note_content, related_draft_id)
            VALUES (%s, %s, %s, %s)
            RETURNING {_SELECT_COLUMNS}
            """,
            (agent_id, request.client_ref, request.note_content, request.related_draft_id),
        )
        row = cur.fetchone()
    return _row_to_response(row)


@router.get("/agent/{agent_id}/notes", response_model=list[ClientNoteResponse])
def list_notes(
    agent_id: str,
    conn: psycopg.Connection = Depends(get_conn),
    current_agent_id: str = Depends(get_current_agent_id),
) -> list[ClientNoteResponse]:
    _require_path_matches_identity(agent_id, current_agent_id)
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {_SELECT_COLUMNS} FROM agent.client_notes WHERE agent_id = %s ORDER BY created_at DESC",
            (agent_id,),
        )
        rows = cur.fetchall()
    return [_row_to_response(row) for row in rows]


@router.delete("/agent/{agent_id}/notes/{note_id}", status_code=204)
def delete_note(
    agent_id: str,
    note_id: UUID,
    conn: psycopg.Connection = Depends(get_conn),
    current_agent_id: str = Depends(get_current_agent_id),
) -> None:
    _require_path_matches_identity(agent_id, current_agent_id)
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM agent.client_notes WHERE agent_id = %s AND note_id = %s",
            (agent_id, note_id),
        )
