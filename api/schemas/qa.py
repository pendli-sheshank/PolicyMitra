from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from agents.base import Citation


class QARequest(BaseModel):
    session_id: UUID | None = None
    message: str
    insurer_filter: str | None = None


class QAResponse(BaseModel):
    response_id: UUID
    session_id: UUID
    answer: str
    not_found: bool
    citations: list[Citation]
    confidence: float | None
    guardrail_verdict: str
    disclaimer: str
