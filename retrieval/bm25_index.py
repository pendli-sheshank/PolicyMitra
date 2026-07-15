"""BM25-style keyword search via Postgres native full-text search
(tsvector/ts_rank_cd), not a separate in-process index — chunks already live
in Postgres and re-syncing a second index on every re-ingest buys nothing
at this scale (see docs/architecture.md #3)."""

from __future__ import annotations

from uuid import UUID

import psycopg

from retrieval.models import RetrievalFilters


def bm25_search(
    conn: psycopg.Connection, query: str, k: int, filters: RetrievalFilters | None = None
) -> list[tuple[UUID, float]]:
    filters = filters or RetrievalFilters()
    conditions = ["d.is_current = true"]
    params: dict = {"query": query, "k": k}

    if filters.insurer:
        conditions.append("d.insurer = %(insurer)s")
        params["insurer"] = filters.insurer
    if filters.product_name:
        conditions.append("d.product_name = %(product_name)s")
        params["product_name"] = filters.product_name

    # plainto_tsquery ANDs every remaining lexeme together, which almost never
    # matches a short, specific chunk against a multi-word natural-language
    # question (a chunk would need to contain every query term). Real BM25
    # scores on ANY matching term, weighted by frequency — so we rewrite the
    # AND-tsquery into an OR-tsquery (' & ' -> ' | ') before ranking.
    # normalization=1 then divides the rank by document length (log-scaled),
    # so a short, specific table_row chunk outranks a long table_block chunk
    # that happens to contain the same matched terms diluted among other rows.
    sql = f"""
        SELECT c.chunk_id, ts_rank_cd(c.fts, q.tsq, 1) AS score
        FROM kb.chunks c
        JOIN kb.documents d ON c.doc_id = d.doc_id
        CROSS JOIN LATERAL (
            SELECT to_tsquery(
                'english',
                regexp_replace(plainto_tsquery('english', %(query)s)::text, ' & ', ' | ', 'g')
            ) AS tsq
        ) q
        WHERE {" AND ".join(conditions)}
          AND c.fts @@ q.tsq
        ORDER BY score DESC
        LIMIT %(k)s
    """
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [(row[0], float(row[1])) for row in cur.fetchall()]
