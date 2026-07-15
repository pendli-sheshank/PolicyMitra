from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from agents.guardrail_agent import GuardrailAgent
from agents.orchestrator import run_qa
from agents.qa_agent import QAAgent
from agents.retrieval_agent import RetrievalAgent
from agents.router_agent import RouterAgent
from api.deps import (
    get_conn,
    get_guardrail_agent,
    get_qa_agent,
    get_retrieval_agent,
    get_router_agent,
    touch_session,
)
from api.schemas.qa import QARequest, QAResponse

router = APIRouter()


@router.post("/qa", response_model=QAResponse)
def ask_question(
    request: QARequest,
    conn: psycopg.Connection = Depends(get_conn),
    router_agent: RouterAgent = Depends(get_router_agent),
    retrieval_agent: RetrievalAgent = Depends(get_retrieval_agent),
    qa_agent: QAAgent = Depends(get_qa_agent),
    guardrail: GuardrailAgent = Depends(get_guardrail_agent),
) -> QAResponse:
    session_id = touch_session(conn, request.session_id)
    known_slots = {"insurer": request.insurer_filter} if request.insurer_filter else {}

    outcome = run_qa(
        conn,
        router_agent,
        retrieval_agent,
        qa_agent,
        guardrail,
        request.message,
        known_slots,
        session_id,
    )

    return QAResponse(
        response_id=outcome.response_id,
        session_id=session_id,
        answer=outcome.answer,
        not_found=outcome.not_found,
        citations=outcome.citations,
        confidence=outcome.confidence,
        guardrail_verdict=outcome.guardrail_verdict,
        disclaimer=outcome.disclaimer,
    )
