"""Drafting Agent (Module 3, agent-copilot only): turns a comparison/Q&A
result into a client-ready email/WhatsApp message. Output is always
explicitly marked as a draft pending the human agent's review — the `status`
field is hard-locked, never settable by a caller, and no send action exists
anywhere in this codebase (agents.md: "never auto-sent")."""

from __future__ import annotations

from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from agents.base import LLMClient

PROMPT_PATH = Path(__file__).parent / "prompts" / "drafting_v1.md"


class DraftOutput(BaseModel):
    channel: Literal["email", "whatsapp"]
    subject: str | None
    body: str
    status: Literal["draft_pending_review"] = "draft_pending_review"
    source_chunk_ids: list[UUID]


class DraftingAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def draft(
        self,
        channel: Literal["email", "whatsapp"],
        source_text: str,
        source_chunk_ids: list[UUID],
        agent_notes: str | None = None,
    ) -> DraftOutput:
        system = PROMPT_PATH.read_text()
        context = f"Channel: {channel}\nSource content (facts to preserve unchanged):\n{source_text}"
        if agent_notes:
            context += f"\n\nAgent's notes about this client (tone only, not new facts): {agent_notes}"

        # LLMNotConfiguredError intentionally propagates to the API's 503 handler.
        response = self.llm_client.complete(system=system, messages=[{"role": "user", "content": context}])

        subject: str | None = None
        body = response.text.strip()
        if channel == "email":
            lines = body.split("\n", 1)
            if len(lines) == 2 and len(lines[0]) < 120:
                subject, body = lines[0].strip(), lines[1].strip()

        return DraftOutput(channel=channel, subject=subject, body=body, source_chunk_ids=source_chunk_ids)
