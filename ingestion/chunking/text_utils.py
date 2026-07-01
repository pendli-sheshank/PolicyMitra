"""Small text helpers shared by the chunkers. No tokenizer dependency is
added — token_count is an approximate whitespace-split count, which is
sufficient for the max-chunk-size heuristic used here (noted as approximate,
not billing-accurate)."""

from __future__ import annotations

import re

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_SLUG_RE = re.compile(r"[^\w]+")


def approx_token_count(text: str) -> int:
    return len(text.split())


def split_sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s]


def slugify(value: str) -> str:
    return _SLUG_RE.sub("_", value.strip()).strip("_")
