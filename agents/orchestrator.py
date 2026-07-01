"""Orchestrates Router -> Retrieval -> Specialist -> [Drafting] -> Guardrail
-> User, matching agents.md's flow. Every call writes an audit entry
regardless of the Guardrail verdict (agents.md: "always log it")."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

import psycopg
from pydantic import BaseModel

from agents.audit import write_audit_entry
from agents.base import Citation
from agents.comparison_agent import ComparisonAgent, ComparisonTable, PlanIdentifier
from agents.drafting_agent import DraftingAgent, DraftOutput
from agents.guardrail_agent import GuardrailAgent
from agents.numeric_extraction import CITATION_TAG_PATTERN
from agents.qa_agent import NOT_FOUND_MESSAGE, QAAgent
from agents.recommendation_agent import (
    PlanFactSheet,
    Profile,
    RankedPlan,
    RecommendationAgent,
    build_fact_sheet,
)
from agents.retrieval_agent import RetrievalAgent
from agents.router_agent import RouterAgent
from retrieval.models import RetrievalFilters

STANDARD_DISCLAIMER = (
    "This information is for general awareness only and is not a substitute for reading "
    "your actual policy document or consulting a licensed insurance advisor."
)

GuardrailVerdictLiteral = Literal["pass", "repaired", "blocked"]


class QAOutcome(BaseModel):
    response_id: UUID
    answer: str
    not_found: bool
    citations: list[Citation]
    confidence: float | None
    guardrail_verdict: GuardrailVerdictLiteral
    disclaimer: str = STANDARD_DISCLAIMER


class RecommendationOutcome(BaseModel):
    response_id: UUID
    shortlist: list[RankedPlan]
    guardrail_verdict: GuardrailVerdictLiteral
    disclaimer: str = STANDARD_DISCLAIMER


class ComparisonOutcome(BaseModel):
    response_id: UUID
    table: ComparisonTable
    disclaimer: str = STANDARD_DISCLAIMER


class DraftingOutcome(BaseModel):
    response_id: UUID
    draft: DraftOutput
    guardrail_verdict: GuardrailVerdictLiteral
    disclaimer: str = STANDARD_DISCLAIMER


def run_qa(
    conn: psycopg.Connection,
    router: RouterAgent,
    retrieval_agent: RetrievalAgent,
    qa_agent: QAAgent,
    guardrail: GuardrailAgent,
    message: str,
    known_slots: dict | None = None,
    session_id: UUID | None = None,
) -> QAOutcome:
    known_slots = known_slots or {}
    router_output = router.route(message, [], known_slots)

    filters = RetrievalFilters(insurer=router_output.slots.get("insurer"))
    retrieval_result = retrieval_agent.retrieve(conn, message, filters=filters, known_slots=router_output.slots)

    agent_result = qa_agent.answer(message, retrieval_result)

    chunk_lookup = {c.clause_id: c.text_content for c in retrieval_result.chunks}
    verdict = guardrail.check(agent_result.output, agent_result.chunk_ids_used, chunk_lookup)

    chunks_by_clause_id = {c.clause_id: c for c in retrieval_result.chunks}
    cited_clause_ids = sorted(set(CITATION_TAG_PATTERN.findall(verdict.final_text)))
    citations = [
        Citation(
            clause_id=cid,
            chunk_id=chunk.chunk_id,
            insurer=chunk.insurer,
            product_name=chunk.product_name,
            doc_version=chunk.doc_version,
            excerpt=chunk.text_content,
        )
        for cid in cited_clause_ids
        if (chunk := chunks_by_clause_id.get(cid)) is not None
    ]
    not_found = agent_result.output == NOT_FOUND_MESSAGE

    response_id = write_audit_entry(
        conn,
        module="qa",
        query_text=message,
        response_text=verdict.final_text,
        chunk_ids_used=agent_result.chunk_ids_used,
        guardrail_verdict=verdict.verdict,
        guardrail_detail=[d.model_dump() for d in verdict.detail],
        confidence_score=agent_result.confidence,
        session_id=session_id,
    )

    return QAOutcome(
        response_id=response_id,
        answer=verdict.final_text,
        not_found=not_found,
        citations=citations,
        confidence=agent_result.confidence,
        guardrail_verdict=verdict.verdict,
    )


def run_recommendation(
    conn: psycopg.Connection,
    retrieval_agent: RetrievalAgent,
    recommendation_agent: RecommendationAgent,
    guardrail: GuardrailAgent,
    profile: Profile,
    candidate_insurers: list[str],
    session_id: UUID | None = None,
) -> RecommendationOutcome:
    fact_sheets: list[PlanFactSheet] = [
        build_fact_sheet(conn, retrieval_agent, insurer, profile) for insurer in candidate_insurers
    ]
    ranked = recommendation_agent.recommend(profile, fact_sheets)

    # Guardrail checks the full set of rationale/trade-off text against a
    # chunk_lookup merged across ALL fact sheets, since a trade-off sentence
    # can cite another plan's clause_id (docs/architecture.md's recommendation notes).
    merged_lookup: dict[str, str] = {}
    for sheet in fact_sheets:
        merged_lookup.update(sheet.clause_text_lookup())

    combined_text = " ".join(f"{plan.one_line_rationale} {plan.trade_off_vs_top_pick or ''}".strip() for plan in ranked)
    all_chunk_ids = [cid for plan in ranked for cid in plan.supporting_chunk_ids]
    verdict = guardrail.check(combined_text, all_chunk_ids, merged_lookup)

    response_id = write_audit_entry(
        conn,
        module="recommendation",
        query_text=f"profile={profile.model_dump()} candidates={candidate_insurers}",
        response_text=verdict.final_text,
        chunk_ids_used=all_chunk_ids,
        guardrail_verdict=verdict.verdict,
        guardrail_detail=[d.model_dump() for d in verdict.detail],
        confidence_score=None,
        session_id=session_id,
    )

    return RecommendationOutcome(response_id=response_id, shortlist=ranked, guardrail_verdict=verdict.verdict)


def run_comparison(
    conn: psycopg.Connection,
    retrieval_agent: RetrievalAgent,
    comparison_agent: ComparisonAgent,
    plans: list[PlanIdentifier],
    session_id: UUID | None = None,
) -> ComparisonOutcome:
    table = comparison_agent.compare(conn, retrieval_agent, plans)

    all_chunk_ids = [cid for row in table.rows for ids in row.source_chunk_ids.values() for cid in ids]
    response_id = write_audit_entry(
        conn,
        module="comparison",
        query_text=f"plans={[p.insurer for p in plans]}",
        response_text=str(table.model_dump()),
        chunk_ids_used=all_chunk_ids,
        guardrail_verdict="pass",  # comparison rows quote retrieved text verbatim; no generation step to guard
        guardrail_detail=[],
        confidence_score=None,
        session_id=session_id,
    )
    return ComparisonOutcome(response_id=response_id, table=table)


def run_drafting(
    conn: psycopg.Connection,
    drafting_agent: DraftingAgent,
    guardrail: GuardrailAgent,
    channel: Literal["email", "whatsapp"],
    source_text: str,
    source_chunk_ids: list[UUID],
    chunk_text_lookup: dict[str, str],
    agent_id: str,
    agent_notes: str | None = None,
    session_id: UUID | None = None,
) -> DraftingOutcome:
    draft = drafting_agent.draft(channel, source_text, source_chunk_ids, agent_notes)

    verdict = guardrail.check(draft.body, source_chunk_ids, chunk_text_lookup)
    draft.body = verdict.final_text

    response_id = write_audit_entry(
        conn,
        module="drafting",
        query_text=f"channel={channel}",
        response_text=draft.body,
        chunk_ids_used=source_chunk_ids,
        guardrail_verdict=verdict.verdict,
        guardrail_detail=[d.model_dump() for d in verdict.detail],
        confidence_score=None,
        session_id=session_id,
        agent_id=agent_id,
    )

    return DraftingOutcome(response_id=response_id, draft=draft, guardrail_verdict=verdict.verdict)
