"""Layer 3 User Profile Memory: cross-session, opt-in only. A write here
always means the user just took an explicit save action — consent_given_at
is set server-side to now() on every create/update, never client-supplied
(memory.md: "opt-in only... explicit user action to save")."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_conn
from api.schemas.profile import ProfileCreateRequest, ProfileResponse

router = APIRouter()

_SELECT_COLUMNS = (
    "profile_id, user_ref, age, dependents, city_tier, budget_annual_inr, " "sum_insured_target_inr, ped_flags, consent_given_at"
)


def _row_to_response(row) -> ProfileResponse:
    return ProfileResponse(
        profile_id=row[0],
        user_ref=row[1],
        age=row[2],
        dependents=row[3],
        city_tier=row[4],
        budget_annual_inr=row[5],
        sum_insured_target_inr=row[6],
        ped_flags=row[7],
        consent_given_at=row[8],
    )


@router.post("/profile/{user_ref}", response_model=ProfileResponse)
def save_profile(user_ref: str, request: ProfileCreateRequest, conn: psycopg.Connection = Depends(get_conn)) -> ProfileResponse:
    consent_given_at = datetime.now(UTC)
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO mem.user_profiles
                (user_ref, age, dependents, city_tier, budget_annual_inr, sum_insured_target_inr, ped_flags, consent_given_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_ref) DO UPDATE SET
                age = EXCLUDED.age, dependents = EXCLUDED.dependents, city_tier = EXCLUDED.city_tier,
                budget_annual_inr = EXCLUDED.budget_annual_inr,
                sum_insured_target_inr = EXCLUDED.sum_insured_target_inr,
                ped_flags = EXCLUDED.ped_flags, consent_given_at = EXCLUDED.consent_given_at, updated_at = now()
            RETURNING {_SELECT_COLUMNS}
            """,
            (
                user_ref,
                request.age,
                request.dependents,
                request.city_tier,
                request.budget_annual_inr,
                request.sum_insured_target_inr,
                json.dumps(request.ped_flags),
                consent_given_at,
            ),
        )
        row = cur.fetchone()
    return _row_to_response(row)


@router.get("/profile/{user_ref}", response_model=ProfileResponse)
def get_profile(user_ref: str, conn: psycopg.Connection = Depends(get_conn)) -> ProfileResponse:
    with conn.cursor() as cur:
        cur.execute(f"SELECT {_SELECT_COLUMNS} FROM mem.user_profiles WHERE user_ref = %s", (user_ref,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return _row_to_response(row)


@router.delete("/profile/{user_ref}", status_code=204)
def delete_profile(user_ref: str, conn: psycopg.Connection = Depends(get_conn)) -> None:
    """Hard delete, no soft-delete flag — cascades into mem.recommendation_cache
    via ON DELETE CASCADE (memory.md: deletion-on-request is first-class)."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM mem.user_profiles WHERE user_ref = %s", (user_ref,))
