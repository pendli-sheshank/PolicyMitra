"""Guardrail Agent: the last gate before any output reaches a user.

Two checks (agents.md):
1. Numeric-claim verification — every currency/percent/duration figure must
   match its cited source chunk (agents/numeric_extraction.py does the actual
   work; this module orchestrates repair-or-redact around it).
2. Scope check — flag language that drifts from "explain the policy" toward
   individualized "you should buy this" advice.

On failure: repair the specific sentence if an LLM is available and the
repair re-verifies clean; otherwise redact just that sentence. Never
silently pass a failure through. Every verdict is meant to be logged to
audit.responses by the orchestrator, not by this class.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from agents.base import LLMClient, LLMNotConfiguredError
from agents.numeric_extraction import (
    SentenceClaim,
    Verdict,
    extract_sentences_with_claims,
    verify_claim,
)

REPAIR_PROMPT_PATH = Path(__file__).parent / "prompts" / "guardrail_repair_v1.md"

REDACTED_TEXT = "[figure could not be verified against source — removed]"

SCOPE_DRIFT_PHRASES = [
    "you should buy",
    "you should purchase",
    "i recommend you purchase",
    "i recommend buying",
    "best choice for you",
    "you must buy",
    "you need to buy",
]


class GuardrailDetail(BaseModel):
    sentence: str | None
    verdict: str
    detail: str | None = None


class GuardrailVerdict(BaseModel):
    final_text: str
    verdict: Literal["pass", "repaired", "blocked"]
    detail: list[GuardrailDetail] = []


class GuardrailAgent:
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client

    def check(self, response_text: str, chunk_ids_used: list[UUID], chunk_text_lookup: dict[str, str]) -> GuardrailVerdict:
        claims = extract_sentences_with_claims(response_text)
        rebuilt: list[str] = []
        detail: list[GuardrailDetail] = []
        any_repaired = False
        any_blocked = False

        for claim in claims:
            result = verify_claim(claim, chunk_text_lookup)

            if result.verdict == Verdict.PASS:
                rebuilt.append(claim.sentence)
                continue

            detail.append(GuardrailDetail(sentence=result.sentence, verdict=result.verdict.value, detail=result.detail))

            repaired_sentence = self._attempt_repair(claim, chunk_text_lookup)
            if repaired_sentence is not None:
                rebuilt.append(repaired_sentence)
                any_repaired = True
            else:
                rebuilt.append(REDACTED_TEXT)
                any_blocked = True

        final_text, scope_flagged = self._apply_scope_check(" ".join(rebuilt))
        if scope_flagged:
            detail.append(
                GuardrailDetail(
                    sentence=None,
                    verdict="scope_drift",
                    detail="individualized advice language removed",
                )
            )

        if any_blocked:
            verdict: Literal["pass", "repaired", "blocked"] = "blocked"
        elif any_repaired or scope_flagged:
            verdict = "repaired"
        else:
            verdict = "pass"

        return GuardrailVerdict(final_text=final_text, verdict=verdict, detail=detail)

    def _attempt_repair(self, claim: SentenceClaim, chunk_text_lookup: dict[str, str]) -> str | None:
        if self.llm_client is None:
            return None

        cited_text = "\n".join(chunk_text_lookup[tag] for tag in claim.citation_tags if tag in chunk_text_lookup)
        if not cited_text:
            return None

        system = REPAIR_PROMPT_PATH.read_text()
        message = f"Original sentence: {claim.sentence}\n\n" f"Correct source text: {cited_text}"
        try:
            response = self.llm_client.complete(system=system, messages=[{"role": "user", "content": message}])
        except LLMNotConfiguredError:
            return None

        repaired_claims = extract_sentences_with_claims(response.text)
        if not repaired_claims:
            return None

        recheck = verify_claim(repaired_claims[0], chunk_text_lookup)
        if recheck.verdict == Verdict.PASS:
            return repaired_claims[0].sentence
        return None  # failed twice -> caller redacts instead of looping

    def _apply_scope_check(self, text: str) -> tuple[str, bool]:
        flagged = False
        for phrase in SCOPE_DRIFT_PHRASES:
            if phrase in text.lower():
                text = re.sub(
                    re.escape(phrase),
                    "[recommendation-style language removed]",
                    text,
                    flags=re.IGNORECASE,
                )
                flagged = True
        return text, flagged
