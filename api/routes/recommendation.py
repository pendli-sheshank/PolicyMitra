from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from agents.guardrail_agent import GuardrailAgent
from agents.orchestrator import run_recommendation
from agents.recommendation_agent import RecommendationAgent
from agents.retrieval_agent import RetrievalAgent
from api.deps import (
    get_conn,
    get_guardrail_agent,
    get_recommendation_agent,
    get_retrieval_agent,
    touch_session,
)
from api.schemas.recommendation import (
    PortabilityRequest,
    PortabilityResponse,
    RecommendRequest,
    RecommendResponse,
)

router = APIRouter()


@router.post("/recommend", response_model=RecommendResponse)
def recommend(
    request: RecommendRequest,
    conn: psycopg.Connection = Depends(get_conn),
    retrieval_agent: RetrievalAgent = Depends(get_retrieval_agent),
    recommendation_agent: RecommendationAgent = Depends(get_recommendation_agent),
    guardrail: GuardrailAgent = Depends(get_guardrail_agent),
) -> RecommendResponse:
    session_id = touch_session(conn, request.session_id)

    outcome = run_recommendation(
        conn,
        retrieval_agent,
        recommendation_agent,
        guardrail,
        request.profile,
        request.candidate_insurers,
        session_id,
    )

    return RecommendResponse(
        response_id=outcome.response_id,
        session_id=session_id,
        shortlist=outcome.shortlist,
        guardrail_verdict=outcome.guardrail_verdict,
        disclaimer=outcome.disclaimer,
    )


@router.post("/recommend/portability", response_model=PortabilityResponse)
def portability(
    request: PortabilityRequest,
    recommendation_agent: RecommendationAgent = Depends(get_recommendation_agent),
) -> PortabilityResponse:
    advice = recommendation_agent.advise_portability(request.months_on_current_plan, request.candidate_waiting_period_months)
    return PortabilityResponse(advice=advice)
