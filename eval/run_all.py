"""The eval acceptance gate (CLAUDE.md non-negotiable #2): run before
merging any change to chunking, retrieval, or agent prompts. Runs without an
LLM key (recall@5, numeric-presence, recommendation ranking accuracy);
LLM-judged faithfulness switches on automatically the moment GEMINI_API_KEY
is set — nothing else needs to change. A reachable DATABASE_URL is required
(the corpus lives in Postgres)."""

from __future__ import annotations

import os
import sys

from eval.harness import report, run_faithfulness_eval, run_recommendation_eval, run_retrieval_eval

RECALL_GATE = 0.90


def main() -> None:
    results: dict = {}

    results["retrieval_recall@5"] = run_retrieval_eval.run()
    results["numeric_presence_offline"] = run_faithfulness_eval.run_offline_numeric_check()
    results["recommendation_ranking"] = run_recommendation_eval.run()

    if os.environ.get("GEMINI_API_KEY"):
        results["llm_judged_faithfulness"] = run_faithfulness_eval.run_llm_judge()
    else:
        results["llm_judged_faithfulness"] = "SKIPPED (no GEMINI_API_KEY)"

    report.write(results)

    recall = results["retrieval_recall@5"]["recall_at_k"]
    print(f"\nretrieval recall@5: {recall:.2%} (gate: {RECALL_GATE:.0%})")
    if recall < RECALL_GATE:
        print("FAIL: retrieval recall@5 is below the acceptance gate.")
        sys.exit(1)

    print("PASS: acceptance gate met.")
    sys.exit(0)


if __name__ == "__main__":
    main()
