"""Faithfulness checks, split by whether they need a live LLM key.

`run_offline_numeric_check` verifies the golden set's hand-verified numeric
facts are actually present (and correctly formatted for citation) in what
retrieval would hand the Q&A agent as grounding — the prerequisite for
citation-grounded generation to be correct once a real key is added. This
needs no LLM call at all.

`run_llm_judge` generates real answers via the full agent pipeline and asks
the configured LLM (Gemini) to score faithfulness 1-5 — only runs when
GEMINI_API_KEY is set.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from agents.numeric_extraction import NUMERIC_PATTERN, NormalizedClaim, normalize_numeric_token
from db.connection import get_connection
from ingestion.embedding import get_default_embedder
from retrieval.hybrid import hybrid_search
from retrieval.models import RetrievalFilters
from retrieval.reranker import LexicalOverlapReranker

GOLDEN_SET_PATH = Path(__file__).parent.parent / "golden_set" / "qa_pairs.yaml"


def load_golden_set() -> list[dict]:
    return yaml.safe_load(GOLDEN_SET_PATH.read_text())


def _expected_fact_to_claim(fact: dict) -> NormalizedClaim:
    unit = fact["unit"]
    if unit == "percent":
        return NormalizedClaim(kind="percent", value=fact["value"])
    if unit in ("days", "months", "years"):
        return NormalizedClaim(kind="duration", value=fact["value"], unit=unit)
    return NormalizedClaim(kind="inr", value=fact["value"])


def run_offline_numeric_check(k: int = 5) -> dict:
    golden_set = load_golden_set()
    embedder = get_default_embedder()
    reranker = LexicalOverlapReranker()

    total = 0
    hits = 0
    per_question = []

    with get_connection() as conn:
        for item in golden_set:
            expected_facts = item.get("expected_answer_facts") or []
            if item.get("expected_not_found") or not expected_facts:
                continue
            total += 1

            filters = RetrievalFilters(insurer=item.get("insurer"))
            result = hybrid_search(conn, item["question"], embedder, k=k, filters=filters, reranker=reranker)
            retrieved_text = " ".join(c.text_content for c in result.chunks)
            retrieved_claims = {normalize_numeric_token(m) for m in NUMERIC_PATTERN.findall(retrieved_text)}
            expected_claims = {_expected_fact_to_claim(f) for f in expected_facts}

            hit = expected_claims.issubset(retrieved_claims)
            hits += int(hit)
            per_question.append({"id": item["id"], "hit": hit})

    accuracy = hits / total if total else 0.0
    return {
        "metric": "offline_numeric_presence",
        "accuracy": accuracy,
        "total": total,
        "hits": hits,
        "per_question": per_question,
    }


def run_llm_judge() -> dict:
    """Only called by eval/run_all.py when GEMINI_API_KEY is set."""
    from agents.guardrail_agent import GuardrailAgent
    from agents.llm_client import get_llm_client
    from agents.orchestrator import run_qa
    from agents.qa_agent import QAAgent
    from agents.retrieval_agent import RetrievalAgent
    from agents.router_agent import RouterAgent

    llm_client = get_llm_client()
    router = RouterAgent(llm_client)
    qa_agent = QAAgent(llm_client)
    guardrail = GuardrailAgent(llm_client)
    retrieval_agent = RetrievalAgent(get_default_embedder(), reranker=LexicalOverlapReranker(), llm_client=llm_client)

    golden_set = load_golden_set()
    scored = []

    with get_connection() as conn:
        for item in golden_set:
            outcome = run_qa(conn, router, retrieval_agent, qa_agent, guardrail, item["question"])
            judge_prompt = (
                f"Question: {item['question']}\nAnswer: {outcome.answer}\n\n"
                "On a scale of 1-5, how faithful is this answer to a correct, source-grounded response "
                "(5 = every claim traceable and correct, 1 = fabricated or contradicts the source)? "
                "Respond with ONLY the number."
            )
            response = llm_client.complete(
                system="You are grading answer faithfulness for a RAG system.",
                messages=[{"role": "user", "content": judge_prompt}],
            )
            try:
                score = float(response.text.strip())
            except ValueError:
                score = None
            scored.append({"id": item["id"], "score": score, "guardrail_verdict": outcome.guardrail_verdict})

    valid_scores = [s["score"] for s in scored if s["score"] is not None]
    average = sum(valid_scores) / len(valid_scores) if valid_scores else None
    return {"metric": "llm_judged_faithfulness", "average_score": average, "per_question": scored}


def main() -> None:
    report = run_offline_numeric_check()
    print(f"offline numeric-presence accuracy: {report['accuracy']:.2%} ({report['hits']}/{report['total']})")


if __name__ == "__main__":
    main()
