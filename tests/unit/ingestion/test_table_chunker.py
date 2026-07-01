"""Load-bearing test for skills.md's quality bar: a table row retrieves as a
coherent unit, never split mid-row."""

from datetime import date

from ingestion.chunking.models import DocumentMeta, RawBlock
from ingestion.chunking.table_chunker import chunk_table


def _meta() -> DocumentMeta:
    return DocumentMeta(
        insurer="Test Insurer",
        product_name="Test Plan",
        doc_version="v1.0",
        effective_date=date(2026, 1, 1),
    )


def _table_block() -> RawBlock:
    return RawBlock(
        clause_id="CL-TEST-TABLE",
        section_title="Test Section",
        block_type="table",
        text="Intro sentence.",
        table_header=["Condition", "Waiting Period", "Sub-limit"],
        table_rows=[
            ["Diabetes", "24 months", "₹1,00,000"],
            ["Cataract", "12 months", "₹40,000"],
            ["Cardiac", "36 months", "₹2,00,000"],
        ],
    )


def test_emits_one_table_block_and_one_chunk_per_row():
    chunks = chunk_table(_table_block(), _meta())

    table_block_chunks = [c for c in chunks if c.metadata.chunk_type == "table_block"]
    row_chunks = [c for c in chunks if c.metadata.chunk_type == "table_row"]

    assert len(table_block_chunks) == 1
    assert len(row_chunks) == 3


def test_row_chunk_is_self_contained_and_never_a_fragment():
    chunks = chunk_table(_table_block(), _meta())
    row_chunks = [c for c in chunks if c.metadata.chunk_type == "table_row"]

    cataract_chunk = next(c for c in row_chunks if "Cataract" in c.text_content)
    assert "12 months" in cataract_chunk.text_content
    assert "₹40,000" in cataract_chunk.text_content
    assert cataract_chunk.metadata.clause_id == "CL-TEST-TABLE#Cataract"

    for chunk in row_chunks:
        # every row chunk names its own condition, value, and unit together —
        # a row's text is never truncated mid-cell.
        assert chunk.text_content.startswith(("Diabetes", "Cataract", "Cardiac"))
        assert chunk.text_content.endswith(".")
        assert "₹" in chunk.text_content
        assert "months" in chunk.text_content


def test_table_block_chunk_preserves_intro_and_full_table():
    chunks = chunk_table(_table_block(), _meta())
    table_block = next(c for c in chunks if c.metadata.chunk_type == "table_block")

    assert "Intro sentence." in table_block.text_content
    for label in ("Diabetes", "Cataract", "Cardiac"):
        assert label in table_block.text_content
