from datetime import date

from ingestion.chunking.clause_chunker import chunk_prose
from ingestion.chunking.models import DocumentMeta, RawBlock


def _meta() -> DocumentMeta:
    return DocumentMeta(
        insurer="Test Insurer",
        product_name="Test Plan",
        doc_version="v1.0",
        effective_date=date(2026, 1, 1),
    )


def test_short_block_is_a_single_chunk():
    block = RawBlock(
        clause_id="CL-SHORT",
        section_title="Section",
        block_type="prose",
        text="This is a short clause with one sentence.",
    )
    chunks = chunk_prose(block, _meta())
    assert len(chunks) == 1
    assert chunks[0].metadata.clause_id == "CL-SHORT"


def test_long_block_splits_at_sentence_boundaries_not_mid_sentence():
    sentence = "This is a filler sentence used to pad the clause text out. "
    long_text = sentence * 50  # well over the 300-token threshold
    block = RawBlock(
        clause_id="CL-LONG",
        section_title="Section",
        block_type="prose",
        text=long_text.strip(),
    )
    chunks = chunk_prose(block, _meta())

    assert len(chunks) > 1
    for i, chunk in enumerate(chunks, start=1):
        assert chunk.metadata.clause_id == f"CL-LONG#{i}"
        # never split mid-sentence: every chunk ends with sentence punctuation
        assert chunk.text_content.rstrip().endswith(".")
