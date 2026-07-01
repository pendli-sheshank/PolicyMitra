"""Chunk prose blocks by clause boundary, not fixed token count. A block is
only split further if it exceeds MAX_TOKENS, and then only at sentence
boundaries — never mid-sentence."""

from __future__ import annotations

from ingestion.chunking.models import Chunk, ChunkMetadata, DocumentMeta, RawBlock
from ingestion.chunking.text_utils import approx_token_count, split_sentences

MAX_TOKENS = 300


def chunk_prose(block: RawBlock, meta: DocumentMeta) -> list[Chunk]:
    assert block.block_type == "prose"

    def make_chunk(clause_id: str, text: str) -> Chunk:
        return Chunk(
            text_content=text,
            token_count=approx_token_count(text),
            metadata=ChunkMetadata(
                insurer=meta.insurer,
                product_name=meta.product_name,
                doc_version=meta.doc_version,
                effective_date=meta.effective_date,
                page_number=block.page_number,
                clause_id=clause_id,
                chunk_type="prose",
                section_title=block.section_title,
            ),
        )

    if approx_token_count(block.text) <= MAX_TOKENS:
        return [make_chunk(block.clause_id, block.text)]

    sentences = split_sentences(block.text)
    chunks: list[Chunk] = []
    current: list[str] = []
    current_tokens = 0
    part = 1

    for sentence in sentences:
        stoks = approx_token_count(sentence)
        if current and current_tokens + stoks > MAX_TOKENS:
            chunks.append(make_chunk(f"{block.clause_id}#{part}", " ".join(current)))
            part += 1
            current = []
            current_tokens = 0
        current.append(sentence)
        current_tokens += stoks

    if current:
        chunks.append(make_chunk(f"{block.clause_id}#{part}", " ".join(current)))

    return chunks
