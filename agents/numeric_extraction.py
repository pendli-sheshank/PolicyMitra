"""Regex-based numeric-claim extraction and verification — the mechanical
core of the Guardrail Agent. Deliberately dependency-free: steps here need
no LLM call at all, so the Guardrail's core safety property holds even with
NullLLMClient (see docs/architecture.md #6).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

NUMERIC_PATTERN = re.compile(
    r"(₹\s?[\d,]+(?:\.\d+)?|Rs\.?\s?[\d,]+(?:\.\d+)?|INR\s?[\d,]+(?:\.\d+)?"
    r"|\d+(?:\.\d+)?\s?%|\d+\s?(?:day|days|month|months|year|years))",
    re.IGNORECASE,
)
# ':' is allowed so multi-plan contexts (recommendation, comparison) can embed
# insurer-qualified tags like "Suraksha_Health_Insurance::CL-PREMIUM-TABLE#5_00_000" —
# a bare clause_id is only unique WITHIN one insurer's document, and two
# insurers can (and in this corpus do) share the same clause_id for
# structurally analogous clauses.
CITATION_TAG_PATTERN = re.compile(r"\[([A-Za-z0-9_\-:#]+)\]")

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_DURATION_UNIT_RE = re.compile(r"(day|days|month|months|year|years)", re.IGNORECASE)
_DIGITS_RE = re.compile(r"[\d.]+")
_CURRENCY_MARKER_RE = re.compile(r"₹|rs\.?|inr", re.IGNORECASE)


@dataclass(frozen=True)
class NormalizedClaim:
    kind: str  # "inr" | "percent" | "duration"
    value: str  # normalized numeric string, e.g. "100000", "12"
    unit: str | None = None  # for duration: always the plural form ("days"/"months"/"years")


def normalize_numeric_token(token: str) -> NormalizedClaim:
    """Strips currency symbols/commas/formatting so "₹1,00,000", "Rs. 100000",
    and "INR 1,00,000" all normalize to the same NormalizedClaim, and "1
    month"/"24 months" normalize to the same unit for comparison."""
    token = token.strip()

    if "%" in token:
        digits = _DIGITS_RE.search(token)
        return NormalizedClaim(kind="percent", value=(digits.group() if digits else token))

    duration_match = _DURATION_UNIT_RE.search(token)
    if duration_match and not _CURRENCY_MARKER_RE.search(token):
        digits = _DIGITS_RE.search(token)
        unit = duration_match.group().lower()
        if not unit.endswith("s"):
            unit += "s"
        return NormalizedClaim(kind="duration", value=(digits.group() if digits else token), unit=unit)

    cleaned = re.sub(r"[₹,]", "", token)
    cleaned = re.sub(r"(?i)^\s*(rs\.?|inr)\s*", "", cleaned).strip()
    digits = _DIGITS_RE.search(cleaned)
    return NormalizedClaim(kind="inr", value=(digits.group() if digits else cleaned))


def split_into_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


@dataclass
class SentenceClaim:
    sentence: str
    numeric_tokens: list[str] = field(default_factory=list)
    citation_tags: list[str] = field(default_factory=list)


def extract_sentences_with_claims(text: str) -> list[SentenceClaim]:
    claims = []
    for sentence in split_into_sentences(text):
        numeric_tokens = [m.group(0) for m in NUMERIC_PATTERN.finditer(sentence)]
        citation_tags = CITATION_TAG_PATTERN.findall(sentence)
        claims.append(SentenceClaim(sentence=sentence, numeric_tokens=numeric_tokens, citation_tags=citation_tags))
    return claims


class Verdict(StrEnum):
    PASS = "pass"
    FAIL_UNCITED = "fail_uncited"
    FAIL_HALLUCINATED_CITATION = "fail_hallucinated_citation"
    FAIL_MISMATCH = "fail_mismatch"


@dataclass
class VerificationResult:
    sentence: str
    verdict: Verdict
    detail: str | None = None


def verify_claim(claim: SentenceClaim, chunk_lookup: dict[str, str]) -> VerificationResult:
    """chunk_lookup maps clause_id -> the exact retrieved chunk text it came
    from (only clause_ids actually retrieved/used this turn should be keys
    here — anything else is by definition a hallucinated citation)."""

    if not claim.numeric_tokens:
        return VerificationResult(sentence=claim.sentence, verdict=Verdict.PASS)

    if not claim.citation_tags:
        return VerificationResult(claim.sentence, Verdict.FAIL_UNCITED, "numeric claim with no citation tag")

    unknown_tags = [tag for tag in claim.citation_tags if tag not in chunk_lookup]
    if unknown_tags:
        return VerificationResult(
            claim.sentence,
            Verdict.FAIL_HALLUCINATED_CITATION,
            f"clause_id(s) not in the retrieved set: {unknown_tags}",
        )

    cited_text = " ".join(chunk_lookup[tag] for tag in claim.citation_tags)
    cited_numeric_claims = {normalize_numeric_token(m.group(0)) for m in NUMERIC_PATTERN.finditer(cited_text)}

    for token in claim.numeric_tokens:
        if normalize_numeric_token(token) not in cited_numeric_claims:
            return VerificationResult(
                claim.sentence,
                Verdict.FAIL_MISMATCH,
                f"claimed {token!r} does not match any figure in the cited source text",
            )

    return VerificationResult(claim.sentence, Verdict.PASS)
