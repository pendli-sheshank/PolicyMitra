"""Parser protocol: every source-format parser turns a document + its
meta.yaml sidecar into a RawDocument of RawBlocks, ready for chunking."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ingestion.chunking.models import DocumentMeta, RawDocument


class Parser(Protocol):
    def parse(self, path: Path, meta: DocumentMeta) -> RawDocument: ...
