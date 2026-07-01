from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, field_validator

from agents.comparison_agent import ComparisonTable, PlanIdentifier


class CompareRequest(BaseModel):
    session_id: UUID | None = None
    plans: list[PlanIdentifier]

    @field_validator("plans")
    @classmethod
    def validate_plan_count(cls, plans: list[PlanIdentifier]) -> list[PlanIdentifier]:
        if not 2 <= len(plans) <= 4:
            raise ValueError("A comparison requires between 2 and 4 plans.")
        return plans


class CompareResponse(BaseModel):
    response_id: UUID
    session_id: UUID
    table: ComparisonTable
    disclaimer: str
