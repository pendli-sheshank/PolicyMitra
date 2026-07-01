"""Real embedding provider (Voyage AI), used when VOYAGE_API_KEY is set.

Voyage's models default to a 1024-dim output, which does NOT match the
384-dim schema used by LocalHashEmbedder (see docs/architecture.md #2).
Using this embedder against the existing kb.embeddings table requires
widening the column first:
    ALTER TABLE kb.embeddings ALTER COLUMN embedding TYPE VECTOR(1024);
and re-ingesting, since pgvector requires one fixed dimension per column.
"""

from __future__ import annotations

import os

import httpx

VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"


class VoyageEmbedderNotConfiguredError(Exception):
    pass


class VoyageEmbedder:
    name = "voyage-3"
    dim = 1024

    def __init__(self, api_key: str | None = None, model: str = "voyage-3"):
        self.api_key = api_key or os.environ.get("VOYAGE_API_KEY")
        if not self.api_key:
            raise VoyageEmbedderNotConfiguredError("VOYAGE_API_KEY is not set.")
        self.model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = httpx.post(
            VOYAGE_API_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"input": texts, "model": self.model},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]
