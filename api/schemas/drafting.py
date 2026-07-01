from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from agents.drafting_agent import DraftOutput


class DraftRequest(BaseModel):
    session_id: UUID | None = None
    channel: Literal["email", "whatsapp"]
    source_text: str
    source_chunk_ids: list[UUID] = []
    # clause_id -> exact retrieved chunk text, so Guardrail can re-verify the
    # draft's numbers against the same source the comparison/Q&A step used.
    chunk_text_lookup: dict[str, str] = {}
    agent_notes: str | None = None


class DraftResponse(BaseModel):
    response_id: UUID
    draft: DraftOutput
    guardrail_verdict: str
    disclaimer: str
