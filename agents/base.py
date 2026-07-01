"""Common types shared by every agent: the LLMClient protocol, its
typed "not configured" error, and the result envelope every agent returns."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel


class LLMResponse(BaseModel):
    text: str
    raw: Any = None


class LLMClient(Protocol):
    def complete(self, system: str, messages: list[dict], max_tokens: int = 1024) -> LLMResponse: ...


class LLMNotConfiguredError(Exception):
    """Raised by NullLLMClient when no API key is present. Callers must catch
    and degrade (or let it propagate to the API layer's 503 handler) — never
    let it crash the process."""


class Citation(BaseModel):
    clause_id: str
    chunk_id: UUID
    insurer: str
    product_name: str
    doc_version: str
    excerpt: str


class AgentResult(BaseModel):
    output: Any
    chunk_ids_used: list[UUID] = []
    confidence: float | None = None
    needs_clarification: bool = False
    clarification_question: str | None = None
