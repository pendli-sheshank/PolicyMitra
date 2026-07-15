"""Real embedding provider (OpenAI), used when OPENAI_API_KEY is set.

text-embedding-3-small outputs 1536 dimensions, matching
kb.embeddings.embedding VECTOR(1536); pgvector requires one fixed dimension
per column, so switching models means ALTER COLUMN + re-ingest. Called over
REST via httpx — no openai SDK dependency.
"""

from __future__ import annotations

import os

import httpx

OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
DEFAULT_OPENAI_EMBED_MODEL = "text-embedding-3-small"


class OpenAIEmbedderNotConfiguredError(Exception):
    pass


class OpenAIEmbedder:
    dim = 1536

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise OpenAIEmbedderNotConfiguredError("OPENAI_API_KEY is not set.")
        self.model = model or os.environ.get("OPENAI_EMBED_MODEL", DEFAULT_OPENAI_EMBED_MODEL)

    @property
    def name(self) -> str:
        return self.model

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = httpx.post(
            OPENAI_EMBEDDINGS_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"input": texts, "model": self.model},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        # The API may return items out of order; index makes ordering explicit.
        items = sorted(data["data"], key=lambda item: item["index"])
        return [item["embedding"] for item in items]
