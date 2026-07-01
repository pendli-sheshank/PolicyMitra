from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from agents.recommendation_agent import PortabilityAdvice, Profile, RankedPlan


class RecommendRequest(BaseModel):
    session_id: UUID | None = None
    profile: Profile
    candidate_insurers: list[str]


class RecommendResponse(BaseModel):
    response_id: UUID
    session_id: UUID
    shortlist: list[RankedPlan]
    guardrail_verdict: str
    disclaimer: str


class PortabilityRequest(BaseModel):
    months_on_current_plan: int
    candidate_waiting_period_months: int


class PortabilityResponse(BaseModel):
    advice: PortabilityAdvice
