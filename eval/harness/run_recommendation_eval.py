"""Offline (no LLM key needed) recommendation ranking check: builds real
fact sheets via retrieval (local embedder, no LLM), then calls the agent's
pure-Python `_score_plan()`/`recommend()` directly against hand-worked
scenarios — ranking is deterministic code, so this is 100% checkable
without a live LLM key (see docs/PRD.md §11)."""

from __future__ import annotations

from pathlib import Path

import yaml

from agents.recommendation_agent import Profile, RecommendationAgent, build_fact_sheet
from agents.retrieval_agent import RetrievalAgent
from db.connection import get_connection
from ingestion.embedding import get_default_embedder
from retrieval.reranker import LexicalOverlapReranker

SCENARIOS_PATH = Path(__file__).parent.parent / "golden_set" / "recommendation_scenarios.yaml"


def load_scenarios() -> list[dict]:
    return yaml.safe_load(SCENARIOS_PATH.read_text())


def run() -> dict:
    scenarios = load_scenarios()
    retrieval_agent = RetrievalAgent(get_default_embedder(), reranker=LexicalOverlapReranker())
    recommendation_agent = RecommendationAgent(llm_client=None)  # ranking is pure code, no LLM needed

    hits = 0
    per_scenario = []

    with get_connection() as conn:
        for scenario in scenarios:
            profile = Profile(**scenario["profile"])
            fact_sheets = [
                build_fact_sheet(conn, retrieval_agent, insurer, profile) for insurer in scenario["candidate_insurers"]
            ]
            ranked = recommendation_agent.recommend(profile, fact_sheets)
            actual_order = [plan.insurer for plan in ranked]
            expected_order = scenario["expected_rank_order"]
            hit = actual_order == expected_order
            hits += int(hit)
            per_scenario.append(
                {
                    "id": scenario["id"],
                    "hit": hit,
                    "expected": expected_order,
                    "actual": actual_order,
                }
            )

    total = len(scenarios)
    accuracy = hits / total if total else 0.0
    return {"accuracy": accuracy, "total": total, "hits": hits, "per_scenario": per_scenario}


def main() -> None:
    report = run()
    print(f"recommendation ranking accuracy: {report['accuracy']:.2%} ({report['hits']}/{report['total']})")
    for s in report["per_scenario"]:
        status = "OK" if s["hit"] else "MISS"
        print(f"  [{status}] {s['id']}: expected={s['expected']} actual={s['actual']}")


if __name__ == "__main__":
    main()
