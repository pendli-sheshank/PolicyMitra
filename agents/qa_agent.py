"""Q&A Agent (Module 1): answers strictly from retrieved chunks, citing via
the [clause_id] bracket-tag convention (docs/architecture.md #5). Explicit
"not found" below the confidence threshold — never guesses."""

from __future__ import annotations

from pathlib import Path

from agents.base import AgentResult, LLMClient
from retrieval.models import RetrievalResult

PROMPT_PATH = Path(__file__).parent / "prompts" / "qa_v1.md"

DEFAULT_CONF_THRESHOLD = 0.35
NOT_FOUND_MESSAGE = "I don't have this in the documents I have."


class QAAgent:
    def __init__(self, llm_client: LLMClient, confidence_threshold: float = DEFAULT_CONF_THRESHOLD):
        self.llm_client = llm_client
        self.confidence_threshold = confidence_threshold

    def answer(self, question: str, retrieved: RetrievalResult) -> AgentResult:
        if not retrieved.chunks or retrieved.top_confidence < self.confidence_threshold:
            return AgentResult(
                output=NOT_FOUND_MESSAGE,
                chunk_ids_used=[],
                confidence=retrieved.top_confidence,
            )

        system = PROMPT_PATH.read_text()
        context = "\n\n".join(f"[{c.clause_id}] {c.text_content}" for c in retrieved.chunks)
        user_content = f"Question: {question}\n\nRetrieved passages:\n{context}"

        # LLMNotConfiguredError is intentionally allowed to propagate here —
        # the API layer converts it to a clean 503 (see docs/architecture.md #11).
        response = self.llm_client.complete(system=system, messages=[{"role": "user", "content": user_content}])

        return AgentResult(
            output=response.text,
            chunk_ids_used=[c.chunk_id for c in retrieved.chunks],
            confidence=retrieved.top_confidence,
        )
