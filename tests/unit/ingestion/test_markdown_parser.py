from datetime import date
from pathlib import Path

from ingestion.chunking.models import DocumentMeta
from ingestion.parsers.markdown_parser import MarkdownParser

SAMPLE_MD = """\
# Title

## Section 1: Waiting Periods

<!-- clause: CL-WAIT-INITIAL -->
There is an initial waiting period of 30 days.

<!-- clause: CL-WAIT-TABLE -->
### PED Table

| Condition | Waiting Period |
|-----------|-----------------|
| Diabetes  | 24 months       |
| Cataract  | 12 months       |
"""


def _meta() -> DocumentMeta:
    return DocumentMeta(
        insurer="Test Insurer",
        product_name="Test Plan",
        doc_version="v1.0",
        effective_date=date(2026, 1, 1),
    )


def test_parses_clause_markers_into_blocks(tmp_path: Path):
    md_path = tmp_path / "policy_wording.md"
    md_path.write_text(SAMPLE_MD)

    doc = MarkdownParser().parse(md_path, _meta())

    assert [b.clause_id for b in doc.blocks] == ["CL-WAIT-INITIAL", "CL-WAIT-TABLE"]

    prose_block = doc.blocks[0]
    assert prose_block.block_type == "prose"
    assert "30 days" in prose_block.text
    assert prose_block.section_title == "Section 1: Waiting Periods"

    table_block = doc.blocks[1]
    assert table_block.block_type == "table"
    assert table_block.table_header == ["Condition", "Waiting Period"]
    assert table_block.table_rows == [["Diabetes", "24 months"], ["Cataract", "12 months"]]
    # the ### heading inside the block overrides the section title
    assert table_block.section_title == "PED Table"
