"""CLI: ingest one insurer directory at a time so each is independently
testable. Usage:
    python -m ingestion.cli --insurer-dir corpus/insurers/arogya_shield --embedder local
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ingestion.embedding.base import Embedder
from ingestion.embedding.local_hash_embedder import LocalHashEmbedder
from ingestion.pipeline import run_ingestion


def get_embedder(name: str) -> Embedder:
    if name == "local":
        return LocalHashEmbedder()
    if name == "voyage":
        from ingestion.embedding.voyage_embedder import VoyageEmbedder

        return VoyageEmbedder()
    raise ValueError(f"Unknown embedder: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest one insurer's corpus directory")
    parser.add_argument("--insurer-dir", required=True, type=Path)
    parser.add_argument("--embedder", default="local", choices=["local", "voyage"])
    args = parser.parse_args()

    embedder = get_embedder(args.embedder)
    count = run_ingestion(args.insurer_dir, embedder)
    print(f"Ingested {count} chunks from {args.insurer_dir} using embedder '{embedder.name}'")


if __name__ == "__main__":
    main()
