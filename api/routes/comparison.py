from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from agents.comparison_agent import ComparisonAgent
from agents.orchestrator import run_comparison
from agents.retrieval_agent import RetrievalAgent
from api.deps import get_comparison_agent, get_conn, get_retrieval_agent, touch_session
from api.schemas.comparison import CompareRequest, CompareResponse

router = APIRouter()


@router.post("/compare", response_model=CompareResponse)
def compare(
    request: CompareRequest,
    conn: psycopg.Connection = Depends(get_conn),
    retrieval_agent: RetrievalAgent = Depends(get_retrieval_agent),
    comparison_agent: ComparisonAgent = Depends(get_comparison_agent),
) -> CompareResponse:
    session_id = touch_session(conn, request.session_id)

    outcome = run_comparison(conn, retrieval_agent, comparison_agent, request.plans, session_id)

    return CompareResponse(
        response_id=outcome.response_id,
        session_id=session_id,
        table=outcome.table,
        disclaimer=outcome.disclaimer,
    )
