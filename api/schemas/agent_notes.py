from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ClientNoteCreateRequest(BaseModel):
    client_ref: str
    note_content: str
    related_draft_id: UUID | None = None


class ClientNoteResponse(BaseModel):
    note_id: UUID
    agent_id: str
    client_ref: str
    note_content: str
    related_draft_id: UUID | None
    created_at: datetime
    updated_at: datetime
