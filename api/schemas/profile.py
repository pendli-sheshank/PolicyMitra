from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ProfileCreateRequest(BaseModel):
    """consent_given_at has no default and is always set server-side to
    now() at creation time — Layer 3 is opt-in only (memory.md), so a
    profile write always implies an explicit save action just happened."""

    age: int
    dependents: int
    city_tier: Literal["tier1", "tier2", "tier3"]
    budget_annual_inr: int
    sum_insured_target_inr: int
    ped_flags: dict[str, bool] = {}


class ProfileResponse(BaseModel):
    profile_id: UUID
    user_ref: str
    age: int
    dependents: int
    city_tier: str
    budget_annual_inr: int
    sum_insured_target_inr: int
    ped_flags: dict[str, bool]
    consent_given_at: datetime
