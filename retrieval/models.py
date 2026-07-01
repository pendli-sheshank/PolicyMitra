from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class RetrievalFilters(BaseModel):
    insurer: str | None = None
    product_name: str | None = None


class RetrievedChunk(BaseModel):
    chunk_id: UUID
    doc_id: UUID
    clause_id: str
    chunk_type: str
    text_content: str
    table_context: str | None
    insurer: str
    product_name: str
    doc_version: str
    effective_date: date
    section_title: str | None
    score: float = 0.0


class RetrievalResult(BaseModel):
    query: str
    chunks: list[RetrievedChunk]

    @property
    def top_confidence(self) -> float:
        return self.chunks[0].score if self.chunks else 0.0
