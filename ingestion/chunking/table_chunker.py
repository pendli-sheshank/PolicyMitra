"""Table-aware chunking: the load-bearing piece of skills.md's quality bar —
"a table row (e.g. Cataract — sub-limit ₹40,000) retrieves as a coherent
unit, never split mid-row."

For every table block we emit BOTH:
- one `table_block` chunk (the whole table, for queries needing full
  cross-row context, e.g. comparison)
- one `table_row` chunk PER ROW, synthesized as a self-contained sentence
  using the table's own header labels, so a row never depends on its
  siblings to be meaningful.
"""

from __future__ import annotations

from ingestion.chunking.models import Chunk, ChunkMetadata, DocumentMeta, RawBlock
from ingestion.chunking.text_utils import approx_token_count, slugify


def _render_table_text(header: list[str], rows: list[list[str]], intro: str) -> str:
    lines = [" | ".join(header)]
    lines += [" | ".join(row) for row in rows]
    table_text = "\n".join(lines)
    return f"{intro}\n\n{table_text}" if intro else table_text


def _row_to_sentence(header: list[str], row: list[str]) -> str:
    label = row[0] if row else ""
    parts = [f"{header[i]}: {row[i]}" for i in range(1, min(len(header), len(row)))]
    return f"{label} — {'; '.join(parts)}." if parts else f"{label}."


def chunk_table(block: RawBlock, meta: DocumentMeta) -> list[Chunk]:
    assert block.block_type == "table"
    header = block.table_header or []
    rows = block.table_rows or []

    def base_metadata(clause_id: str, chunk_type: str) -> ChunkMetadata:
        return ChunkMetadata(
            insurer=meta.insurer,
            product_name=meta.product_name,
            doc_version=meta.doc_version,
            effective_date=meta.effective_date,
            page_number=block.page_number,
            clause_id=clause_id,
            chunk_type=chunk_type,  # type: ignore[arg-type]
            section_title=block.section_title,
        )

    chunks: list[Chunk] = []

    full_table_text = _render_table_text(header, rows, block.text)
    chunks.append(
        Chunk(
            text_content=full_table_text,
            table_context=None,
            token_count=approx_token_count(full_table_text),
            metadata=base_metadata(block.clause_id, "table_block"),
        )
    )

    header_line = " | ".join(header)
    for row in rows:
        row_label = row[0] if row else "row"
        row_clause_id = f"{block.clause_id}#{slugify(row_label)}"
        sentence = _row_to_sentence(header, row)
        chunks.append(
            Chunk(
                text_content=sentence,
                table_context=header_line,
                token_count=approx_token_count(sentence),
                metadata=base_metadata(row_clause_id, "table_row"),
            )
        )

    return chunks
