"""Deterministic, dependency-free embedder used when no OPENAI_API_KEY is
configured (see docs/architecture.md #2 and #11). This is a feature-hashing
bag-of-words embedding (the classic "hashing trick") — not a learned
semantic embedding, but it captures word overlap well enough to be a
meaningful dense signal for a small, distinct-vocabulary corpus, and it
keeps the rest of the retrieval/eval pipeline fully runnable offline.

Dimension fixed at 1536 to match kb.embeddings.embedding VECTOR(1536),
which is sized for the production embedder (OpenAI text-embedding-3-small);
pgvector allows one fixed dimension per column, so the fallback conforms.
"""

from __future__ import annotations

import hashlib
import math
import re

DIM = 1536
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _preprocess(text: str) -> str:
    return text.lower().replace("₹", " inr ").replace("%", " percent ")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(_preprocess(text))


def _hash_token(token: str) -> tuple[int, float]:
    digest = hashlib.md5(token.encode("utf-8")).digest()
    idx = int.from_bytes(digest[:4], "big") % DIM
    sign = 1.0 if digest[4] % 2 == 0 else -1.0
    return idx, sign


class LocalHashEmbedder:
    name = "local_hash_v2"
    dim = DIM

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * DIM
        for token in _tokenize(text):
            idx, sign = _hash_token(token)
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
