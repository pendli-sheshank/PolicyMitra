"""Router Agent: classifies intent + extracts slots. Falls back to
deterministic keyword routing when no LLM key is configured (see
docs/architecture.md #11), so the rest of the pipeline stays testable."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from agents.base import LLMClient, LLMNotConfiguredError

PROMPT_PATH = Path(__file__).parent / "prompts" / "router_v1.md"

Intent = Literal["faq_claims", "recommendation", "comparison", "drafting", "out_of_scope", "clarify"]


class RouterOutput(BaseModel):
    intent: Intent
    confidence: float
    slots: dict = {}
    clarification_question: str | None = None
    degraded: bool = False  # true when the keyword fallback (no LLM) produced this output


# Maps a short alias a user is likely to type to the exact insurer name as
# stored in kb.documents.insurer — retrieval filters on an exact match, so
# the slot must carry the canonical name, not whatever alias matched.
_INSURER_ALIASES = {
    "arogya shield": "Arogya Shield General Insurance",
    "suraksha health": "Suraksha Health Insurance",
    "nirvana care": "Nirvana Care Insurance",
}

_KEYWORD_RULES: list[tuple[Intent, list[str]]] = [
    ("drafting", ["draft", "email this", "whatsapp message", "client-ready", "write a message"]),
    ("comparison", ["compare", " vs ", "versus", "side by side", "side-by-side"]),
    ("recommendation", ["recommend", "which plan", "best plan", "suggest a plan", "should i buy"]),
]


class RouterAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def route(self, message: str, history: list[dict], known_slots: dict) -> RouterOutput:
        try:
            return self._route_with_llm(message, known_slots)
        except LLMNotConfiguredError:
            return self._keyword_fallback_route(message, known_slots)

    def _route_with_llm(self, message: str, known_slots: dict) -> RouterOutput:
        system = PROMPT_PATH.read_text()
        context = f"Known slots so far: {json.dumps(known_slots)}\n\nMessage: {message}"
        response = self.llm_client.complete(system=system, messages=[{"role": "user", "content": context}])
        data = json.loads(response.text)
        return RouterOutput(**data)

    def _keyword_fallback_route(self, message: str, known_slots: dict) -> RouterOutput:
        lower = message.lower()
        slots = dict(known_slots)

        for alias, canonical_name in _INSURER_ALIASES.items():
            if alias in lower:
                slots["insurer"] = canonical_name

        for intent, keywords in _KEYWORD_RULES:
            if any(kw in lower for kw in keywords):
                return RouterOutput(intent=intent, confidence=0.6, slots=slots, degraded=True)

        return RouterOutput(intent="faq_claims", confidence=0.5, slots=slots, degraded=True)
