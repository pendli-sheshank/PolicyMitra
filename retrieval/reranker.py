"""Pluggable reranker: LexicalOverlapReranker needs no LLM/key and is the
default; LLMReranker is the real path when an LLM client is configured."""

from __future__ import annotations

import json
import re
from typing import Any, Protocol

from retrieval.models import RetrievedChunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Small stopword list so a chunk doesn't get overlap credit purely for
# containing "the"/"is"/etc. — keeps the overlap signal about actual content.
_STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "what",
    "which",
    "who",
    "whom",
    "this",
    "that",
    "these",
    "those",
    "for",
    "of",
    "to",
    "in",
    "on",
    "at",
    "under",
    "by",
    "with",
    "and",
    "or",
    "do",
    "does",
    "did",
    "how",
    "many",
    "much",
}


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS}


def _min_max_normalize(values: list[float]) -> list[float]:
    if not values:
        return values
    lo, hi = min(values), max(values)
    if hi == lo:
        return [1.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


class Reranker(Protocol):
    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]: ...


class LexicalOverlapReranker:
    """Blends the existing fused (RRF) score with query/chunk token overlap.

    RRF scores are tiny (~0.01-0.03, rank-based) while raw overlap ratios are
    0-1 — blending them directly lets overlap silently dominate. Min-max
    normalizing the RRF scores across the candidate set first puts both
    signals on a comparable scale before the 50/50 blend.
    """

    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        qtokens = _tokens(query)
        if not qtokens or not chunks:
            return chunks

        normalized_rrf = _min_max_normalize([c.score for c in chunks])

        scored: list[tuple[float, RetrievedChunk]] = []
        for chunk, rrf_norm in zip(chunks, normalized_rrf, strict=True):
            ctokens = _tokens(chunk.text_content)
            overlap = len(qtokens & ctokens) / len(qtokens)
            blended = 0.5 * rrf_norm + 0.5 * overlap
            scored.append((blended, chunk))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        result = []
        for blended_score, chunk in scored:
            chunk.score = blended_score
            result.append(chunk)
        return result


class LLMReranker:
    """Asks the configured LLM to score relevance 0-1 per candidate, batched.
    Requires a configured LLMClient (agents/llm_client.py) — only used when a
    real GEMINI_API_KEY is present."""

    def __init__(self, llm_client: Any):
        self.llm_client = llm_client

    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not chunks:
            return chunks

        numbered = "\n".join(f"{i}. {c.text_content}" for i, c in enumerate(chunks))
        system = (
            "You score how relevant each numbered passage is to the query, on a 0.0-1.0 scale. "
            "Respond with ONLY a JSON array of numbers, e.g. [0.9, 0.1, 0.4], in the same order."
        )
        message = f"Query: {query}\n\nPassages:\n{numbered}"
        response = self.llm_client.complete(system=system, messages=[{"role": "user", "content": message}])

        try:
            scores = json.loads(response.text.strip())
        except (json.JSONDecodeError, AttributeError):
            return chunks

        for chunk, score in zip(chunks, scores, strict=False):
            chunk.score = float(score)
        return sorted(chunks, key=lambda c: c.score, reverse=True)
