"""Fully offline recall@5 check against the golden Q&A set — no LLM needed.
See docs/skills.md "Hybrid Retrieval" quality bar: recall@5 >= 90%.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from db.connection import get_connection
from ingestion.embedding import get_default_embedder
from retrieval.hybrid import hybrid_search
from retrieval.models import RetrievalFilters
from retrieval.reranker import LexicalOverlapReranker

GOLDEN_SET_PATH = Path(__file__).parent.parent / "golden_set" / "qa_pairs.yaml"


def load_golden_set() -> list[dict]:
    return yaml.safe_load(GOLDEN_SET_PATH.read_text())


def run(k: int = 5) -> dict:
    golden_set = load_golden_set()
    embedder = get_default_embedder()
    reranker = LexicalOverlapReranker()

    total = 0
    hits = 0
    per_question = []

    with get_connection() as conn:
        for item in golden_set:
            if item.get("expected_not_found"):
                continue  # nothing to check recall against for a deliberate "not found" case
            total += 1
            filters = RetrievalFilters(insurer=item.get("insurer"))
            result = hybrid_search(conn, item["question"], embedder, k=k, filters=filters, reranker=reranker)
            retrieved_clause_ids = {c.clause_id for c in result.chunks}
            expected = set(item["expected_clause_ids"])
            hit = bool(expected & retrieved_clause_ids)
            hits += int(hit)
            per_question.append(
                {
                    "id": item["id"],
                    "hit": hit,
                    "expected": sorted(expected),
                    "retrieved": sorted(retrieved_clause_ids),
                }
            )

    recall_at_k = hits / total if total else 0.0
    return {
        "recall_at_k": recall_at_k,
        "k": k,
        "total": total,
        "hits": hits,
        "per_question": per_question,
    }


def main() -> None:
    report = run()
    print(f"recall@{report['k']}: {report['recall_at_k']:.2%} ({report['hits']}/{report['total']})")
    for q in report["per_question"]:
        status = "OK" if q["hit"] else "MISS"
        print(f"  [{status}] {q['id']}: expected={q['expected']} retrieved={q['retrieved']}")


if __name__ == "__main__":
    main()
