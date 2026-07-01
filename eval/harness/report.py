"""Writes eval/run_all.py's aggregated results to a markdown + JSON report,
so eval runs are reviewable and diffable over time (CLAUDE.md: run before
every prompt/retrieval change)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

REPORT_DIR = Path(__file__).parent.parent / "reports"


def write(results: dict) -> Path:
    REPORT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = REPORT_DIR / f"eval_{timestamp}.json"
    md_path = REPORT_DIR / f"eval_{timestamp}.md"

    json_path.write_text(json.dumps(results, indent=2, default=str))

    lines = [f"# PolicyMitra Eval Report — {timestamp}", ""]
    for key, value in results.items():
        if isinstance(value, dict) and "recall_at_k" in value:
            lines.append(f"- **{key}**: recall@{value['k']} = {value['recall_at_k']:.2%} ({value['hits']}/{value['total']})")
        elif isinstance(value, dict) and "accuracy" in value:
            lines.append(f"- **{key}**: {value['accuracy']:.2%} ({value['hits']}/{value['total']})")
        elif isinstance(value, dict) and "average_score" in value:
            lines.append(f"- **{key}**: average score {value['average_score']}")
        else:
            lines.append(f"- **{key}**: {value}")
    md_path.write_text("\n".join(lines))

    print(f"\nReport written to {md_path}")
    return md_path
