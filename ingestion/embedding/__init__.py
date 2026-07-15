"""Embedding providers and the shared selection rule.

get_default_embedder() is the single place that decides which embedder the
system uses (API, eval harness, ingestion CLI's "auto" mode): OpenAI when
OPENAI_API_KEY is set, else the offline LocalHashEmbedder — mirroring the
LLM-client selection in agents/llm_client.py. Query-time and ingest-time
embedders must match (vectors from different embedders aren't comparable);
routing every caller through this one function is what guarantees that.
"""

from __future__ import annotations

import os

from ingestion.embedding.base import Embedder


def get_default_embedder() -> Embedder:
    if os.environ.get("OPENAI_API_KEY"):
        from ingestion.embedding.openai_embedder import OpenAIEmbedder

        return OpenAIEmbedder()
    from ingestion.embedding.local_hash_embedder import LocalHashEmbedder

    return LocalHashEmbedder()
