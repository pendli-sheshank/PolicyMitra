"""Interface-compatible stub for a future real-PDF parser.

Not implemented in this build (see docs/architecture.md #1) — the synthetic
corpus is authored directly as Markdown, which is deterministic to parse and
lets us demonstrate table-aware chunking without wrestling with PDF table
extraction for content we control ourselves. When real insurer PDFs are
added, implement `parse()` here (e.g. with pdfplumber) to return the same
RawDocument/RawBlock shape as MarkdownParser, and everything downstream
(chunking, embedding, retrieval) works unchanged.
"""

from __future__ import annotations

from pathlib import Path

from ingestion.chunking.models import DocumentMeta, RawDocument


class PdfParser:
    def parse(self, path: Path, meta: DocumentMeta) -> RawDocument:
        raise NotImplementedError(
            "PDF parsing is not implemented in this build. The synthetic corpus "
            "uses MarkdownParser instead — see docs/architecture.md decision #1. "
            "Implement this with a table-aware PDF library (e.g. pdfplumber) when "
            "real insurer PDFs are added to the corpus."
        )
