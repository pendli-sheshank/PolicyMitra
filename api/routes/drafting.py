from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from agents.drafting_agent import DraftingAgent
from agents.guardrail_agent import GuardrailAgent
from agents.orchestrator import run_drafting
from api.deps import (
    get_conn,
    get_current_agent_id,
    get_drafting_agent,
    get_guardrail_agent,
    touch_session,
)
from api.schemas.drafting import DraftRequest, DraftResponse

router = APIRouter()


@router.post("/draft", response_model=DraftResponse)
def draft(
    request: DraftRequest,
    conn: sqlite3.Connection = Depends(get_conn),
    drafting_agent: DraftingAgent = Depends(get_drafting_agent),
    guardrail: GuardrailAgent = Depends(get_guardrail_agent),
    agent_id: str = Depends(get_current_agent_id),
) -> DraftResponse:
    session_id = touch_session(conn, request.session_id, mode="agent")

    outcome = run_drafting(
        conn,
        drafting_agent,
        guardrail,
        request.channel,
        request.source_text,
        request.source_chunk_ids,
        request.chunk_text_lookup,
        agent_id,
        request.agent_notes,
        session_id,
    )

    return DraftResponse(
        response_id=outcome.response_id,
        draft=outcome.draft,
        guardrail_verdict=outcome.guardrail_verdict,
        disclaimer=outcome.disclaimer,
    )
