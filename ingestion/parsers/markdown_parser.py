"""Deterministic parser for our hand-authored Markdown policy-wording format.

Convention (see docs/architecture.md #1 for why Markdown, not PDF, for the
synthetic corpus): headings (##/###) update the current section title;
`<!-- clause: ID -->` markers open a new clause-scoped block that runs until
the next marker or heading; pipe-table lines within a block are parsed into
a structured table rather than flattened to plain text.
"""

from __future__ import annotations

import re
from pathlib import Path

from ingestion.chunking.models import DocumentMeta, RawBlock, RawDocument

CLAUSE_MARKER_RE = re.compile(r"^<!--\s*clause:\s*([A-Za-z0-9_\-]+)\s*-->\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _is_separator_line(line: str) -> bool:
    # e.g. "|-------------|-----------|"
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return all(re.fullmatch(r":?-+:?", c) for c in cells) if cells else False


def _split_row(line: str) -> list[str]:
    inner = line.strip().strip("|")
    return [cell.strip() for cell in inner.split("|")]


def _parse_table(lines: list[str]) -> tuple[list[str], list[list[str]]]:
    header = _split_row(lines[0])
    data_lines = lines[2:] if len(lines) > 1 and _is_separator_line(lines[1]) else lines[1:]
    rows = [_split_row(line) for line in data_lines if line.strip()]
    return header, rows


def _finalize_block(clause_id: str, section_title: str | None, content_lines: list[str]) -> RawBlock:
    table_line_idxs = [i for i, ln in enumerate(content_lines) if _is_table_line(ln)]
    intro_lines = [ln for i, ln in enumerate(content_lines) if i not in table_line_idxs]
    intro_text = "\n".join(ln for ln in intro_lines if ln.strip()).strip()

    if table_line_idxs:
        table_lines = [content_lines[i] for i in table_line_idxs]
        header, rows = _parse_table(table_lines)
        return RawBlock(
            clause_id=clause_id,
            section_title=section_title,
            block_type="table",
            text=intro_text,
            table_header=header,
            table_rows=rows,
        )

    prose = "\n".join(ln for ln in content_lines if ln.strip()).strip()
    return RawBlock(clause_id=clause_id, section_title=section_title, block_type="prose", text=prose)


class MarkdownParser:
    def parse(self, path: Path, meta: DocumentMeta) -> RawDocument:
        lines = path.read_text(encoding="utf-8").splitlines()

        blocks: list[RawBlock] = []
        current_section_title: str | None = None
        current_clause_id: str | None = None
        current_lines: list[str] = []

        def flush() -> None:
            if current_clause_id is not None:
                blocks.append(_finalize_block(current_clause_id, current_section_title, current_lines))

        for line in lines:
            heading_match = HEADING_RE.match(line)
            clause_match = CLAUSE_MARKER_RE.match(line)

            if heading_match:
                current_section_title = heading_match.group(2).strip()
                continue

            if clause_match:
                flush()
                current_clause_id = clause_match.group(1)
                current_lines = []
                continue

            if current_clause_id is not None:
                current_lines.append(line)

        flush()

        return RawDocument(source_path=str(path), meta=meta, blocks=blocks)
