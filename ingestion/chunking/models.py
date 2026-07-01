"""Shared data models for the ingestion pipeline: raw parsed blocks -> chunks.

See docs/skills.md "Document Ingestion & Table-Aware Chunking" for the
required metadata fields and quality bar this schema exists to satisfy.
"""

from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class DocumentMeta(BaseModel):
    """Parsed from an insurer's meta.yaml."""

    insurer: str
    product_name: str
    doc_version: str
    effective_date: date


class RawBlock(BaseModel):
    """One clause-marked section of a source document, before chunking."""

    clause_id: str
    section_title: str | None
    block_type: Literal["prose", "table", "heading"]
    text: str = ""
    table_header: list[str] | None = None
    table_rows: list[list[str]] | None = None
    page_number: int | None = None


class RawDocument(BaseModel):
    """A fully parsed source document, ready for chunking."""

    source_path: str
    meta: DocumentMeta
    blocks: list[RawBlock]


class ChunkMetadata(BaseModel):
    insurer: str
    product_name: str
    doc_version: str
    effective_date: date
    page_number: int | None
    clause_id: str
    chunk_type: Literal["prose", "table_row", "table_block", "heading"]
    section_title: str | None


class Chunk(BaseModel):
    chunk_id: UUID | None = None
    doc_id: UUID | None = None
    text_content: str
    table_context: str | None = None
    token_count: int
    metadata: ChunkMetadata
