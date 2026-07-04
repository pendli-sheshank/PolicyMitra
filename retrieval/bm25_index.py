"""BM25 keyword search via SQLite FTS5 — chunks already live in SQLite and
re-syncing a separate in-process index on every re-ingest buys nothing at
this scale (see docs/architecture.md #3). The kb_chunks_fts virtual table
uses porter stemming, mirroring the stemming the previous Postgres 'english'
text-search config applied."""

from __future__ import annotations

import re
import sqlite3
from uuid import UUID

from retrieval.models import RetrievalFilters

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Mirrors the effect of Postgres's 'english' stopword list closely enough for
# this corpus. With OR-semantics (see below) leaving stopwords in would flood
# every chunk into the candidate set with diluted BM25 scores.
_STOPWORDS = frozenset("""a an and are as at be been but by can could do does for from had has have
    how i if in into is it its me my no not of on or our so than that the their
    them then there these they this to under was we what when where which who
    will with would you your""".split())


def _fts_match_expression(query: str) -> str:
    """Build an FTS5 MATCH expression that behaves like the old OR-rewritten
    tsquery: score on ANY matching term (real BM25 behaviour) instead of
    requiring every query term to appear in a short, specific chunk. Terms are
    double-quoted so FTS5 operator syntax in user text (-, NEAR, *) is inert.
    """
    terms = [t for t in _TOKEN_RE.findall(query.lower()) if t not in _STOPWORDS]
    return " OR ".join(f'"{t}"' for t in dict.fromkeys(terms))


def bm25_search(
    conn: sqlite3.Connection, query: str, k: int, filters: RetrievalFilters | None = None
) -> list[tuple[UUID, float]]:
    filters = filters or RetrievalFilters()
    match = _fts_match_expression(query)
    if not match:
        return []

    conditions = ["d.is_current = 1"]
    params: dict = {"match": match, "k": k}

    if filters.insurer:
        conditions.append("d.insurer = :insurer")
        params["insurer"] = filters.insurer
    if filters.product_name:
        conditions.append("d.product_name = :product_name")
        params["product_name"] = filters.product_name

    # FTS5 bm25() is smaller-is-better; negate so callers keep the
    # higher-is-better contract the RRF fusion in hybrid.py expects.
    sql = f"""
        SELECT c.chunk_id, -bm25(kb_chunks_fts) AS score
        FROM kb_chunks_fts
        JOIN kb_chunks c ON c.rowid = kb_chunks_fts.rowid
        JOIN kb_documents d ON c.doc_id = d.doc_id
        WHERE kb_chunks_fts MATCH :match
          AND {" AND ".join(conditions)}
        ORDER BY bm25(kb_chunks_fts)
        LIMIT :k
    """
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [(UUID(row[0]), float(row[1])) for row in cur.fetchall()]
