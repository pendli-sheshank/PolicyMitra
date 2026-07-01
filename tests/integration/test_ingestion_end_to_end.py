"""Runs the real pipeline against the real synthetic corpus (via the
session-scoped conftest fixture) and spot-checks the table-aware chunking
quality bar end-to-end against a real Postgres+pgvector instance."""

from __future__ import annotations


def test_all_three_insurers_ingested(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT insurer, count(*) FROM kb.documents GROUP BY insurer")
        rows = dict(cur.fetchall())
    assert set(rows) == {
        "Arogya Shield General Insurance",
        "Suraksha Health Insurance",
        "Nirvana Care Insurance",
    }


def test_cataract_row_retrieves_as_one_coherent_chunk_per_insurer(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT text_content FROM kb.chunks
            WHERE clause_id = 'CL-WAIT-PED-TABLE#Cataract' AND chunk_type = 'table_row'
            """)
        rows = [r[0] for r in cur.fetchall()]

    assert len(rows) == 3  # one per insurer, never split mid-row
    for text in rows:
        assert "Cataract" in text
        assert "months" in text
        assert "₹" in text
        assert text.endswith(".")


def test_embeddings_are_populated_for_every_chunk(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM kb.chunks")
        chunk_count = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM kb.embeddings")
        embedding_count = cur.fetchone()[0]
    assert chunk_count > 0
    assert chunk_count == embedding_count
