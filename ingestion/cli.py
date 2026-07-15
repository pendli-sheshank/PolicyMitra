"""CLI: ingest one insurer directory at a time so each is independently
testable. Usage:
    python -m ingestion.cli --insurer-dir corpus/insurers/arogya_shield [--embedder auto]

"auto" picks OpenAI when OPENAI_API_KEY is set, else the offline local
embedder — the same rule the API and eval harness use, so ingest-time and
query-time embeddings always come from the same provider.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ingestion.embedding import get_default_embedder
from ingestion.embedding.base import Embedder
from ingestion.pipeline import run_ingestion


def get_embedder(name: str) -> Embedder:
    if name == "auto":
        return get_default_embedder()
    if name == "local":
        from ingestion.embedding.local_hash_embedder import LocalHashEmbedder

        return LocalHashEmbedder()
    if name == "openai":
        from ingestion.embedding.openai_embedder import OpenAIEmbedder

        return OpenAIEmbedder()
    raise ValueError(f"Unknown embedder: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest one insurer's corpus directory")
    parser.add_argument("--insurer-dir", required=True, type=Path)
    parser.add_argument("--embedder", default="auto", choices=["auto", "local", "openai"])
    args = parser.parse_args()

    embedder = get_embedder(args.embedder)
    count = run_ingestion(args.insurer_dir, embedder)
    print(f"Ingested {count} chunks from {args.insurer_dir} using embedder '{embedder.name}'")


if __name__ == "__main__":
    main()
