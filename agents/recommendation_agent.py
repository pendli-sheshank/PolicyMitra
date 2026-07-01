"""Recommendation Agent (Module 2): ranks candidate plans against a profile.

Design (docs/architecture.md #7): ranking is deterministic Python
(`_score_plan`), phrasing of the one-line rationale is the LLM (constrained
to numbers already extracted by code), and Guardrail still re-verifies every
number independently. This structurally enforces "every number must trace
to a retrieved chunk, never the model's prior knowledge" rather than relying
on prompting alone. Stays informational-only — no purchase/issuance flow,
no commission logic (CLAUDE.md non-negotiable #5).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from agents.base import LLMClient, LLMNotConfiguredError
from agents.numeric_extraction import NUMERIC_PATTERN, normalize_numeric_token
from agents.retrieval_agent import RetrievalAgent
from ingestion.chunking.text_utils import slugify
from retrieval.models import RetrievalFilters

# Retrieval alone is not reliable for picking the *exact* premium row: Indian
# digit grouping ("₹5,00,000") tokenizes as separate groups ("5","00","000"),
# so a raw target amount like "500000" shares no tokens with the source row
# and generic chunks (room rent, sum insured) can outrank it. Since our own
# corpus is small, we instead retrieve a generous candidate pool and pick the
# row deterministically by clause_id — the row's citation must still point
# at a real, correctly-matched chunk (accuracy over relying on ranking luck).
_PREMIUM_LOOKUP_K = 25


def _format_inr_grouped(amount: int) -> str:
    """Indian digit grouping: 500000 -> "5,00,000" (matches the corpus's own
    formatting), so the expected clause_id suffix can be computed the same
    way ingestion/chunking/table_chunker.py slugified the original row label."""
    digits = str(amount)
    if len(digits) <= 3:
        return digits
    last3, rest = digits[-3:], digits[:-3]
    groups: list[str] = []
    while len(rest) > 2:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.insert(0, rest)
    return ",".join(groups) + "," + last3


PROMPT_PATH = Path(__file__).parent / "prompts" / "recommendation_v1.md"

_AGE_BAND_RE = re.compile(r"Age\s+(\d+)-(\d+):\s*(₹[\d,]+)")


class Profile(BaseModel):
    age: int
    dependents: int
    city_tier: Literal["tier1", "tier2", "tier3"]
    ped_flags: dict[str, bool] = {}
    budget_annual_inr: int
    sum_insured_target_inr: int


class PlanFactSheet(BaseModel):
    insurer: str
    product_name: str = ""
    premium_inr: int | None = None
    premium_chunk_id: UUID | None = None
    premium_clause_id: str | None = None
    premium_chunk_text: str | None = None
    sum_insured_options_inr: list[int] = []
    ped_waiting_periods_months: dict[str, int] = {}
    ped_sub_limits_inr: dict[str, int] = {}
    ped_chunk_ids: dict[str, UUID] = {}
    ped_clause_ids: dict[str, str] = {}
    ped_chunk_texts: dict[str, str] = {}

    def all_chunk_ids(self) -> list[UUID]:
        ids = list(self.ped_chunk_ids.values())
        if self.premium_chunk_id:
            ids.append(self.premium_chunk_id)
        return ids

    def qualified_clause_id(self, clause_id: str) -> str:
        """clause_id is only unique WITHIN one insurer's document — two
        insurers can (and in this corpus do) share the same clause_id for
        structurally analogous clauses (e.g. both use
        "CL-PREMIUM-TABLE#5_00_000" for their own ₹5,00,000 premium row).
        Recommendation/comparison responses cite facts across multiple
        insurers at once, so citations here are insurer-qualified to stay
        globally unambiguous."""
        return f"{slugify(self.insurer)}::{clause_id}"

    def clause_text_lookup(self) -> dict[str, str]:
        """qualified_clause_id -> the ACTUAL retrieved chunk text (not a
        paraphrase), so the Guardrail verifies rationale numbers against the
        real source, not against a summary this agent just generated from
        the same numbers (which would be a tautological, meaningless check)."""
        lookup: dict[str, str] = {}
        if self.premium_clause_id and self.premium_chunk_text:
            lookup[self.qualified_clause_id(self.premium_clause_id)] = self.premium_chunk_text
        for ailment, clause_id in self.ped_clause_ids.items():
            if ailment in self.ped_chunk_texts:
                lookup[self.qualified_clause_id(clause_id)] = self.ped_chunk_texts[ailment]
        return lookup


class RankedPlan(BaseModel):
    insurer: str
    product_name: str
    rank: int
    score: float
    one_line_rationale: str
    trade_off_vs_top_pick: str | None
    supporting_chunk_ids: list[UUID]


class PortabilityAdvice(BaseModel):
    credited_months: int
    remaining_wait_months: int
    recommendation: Literal["port", "stay_or_wait"]
    explanation: str
    supporting_chunk_ids: list[UUID] = []


def _select_premium_for_age(text: str, age: int) -> int | None:
    for low_s, high_s, amount in _AGE_BAND_RE.findall(text):
        if int(low_s) <= age <= int(high_s):
            return int(normalize_numeric_token(amount).value)
    return None


def build_fact_sheet(conn, retrieval_agent: RetrievalAgent, insurer: str, profile: Profile) -> PlanFactSheet:
    """Pulls plan-level facts via targeted retrieval queries (not raw table
    lookups) so this stays a retrieval-grounded pipeline, per agents.md's
    Recommendation Agent spec: "retrieved plan-level facts", never the
    model's own knowledge of typical premiums/waiting periods."""

    filters = RetrievalFilters(insurer=insurer)
    sheet = PlanFactSheet(insurer=insurer)

    formatted_amount = _format_inr_grouped(profile.sum_insured_target_inr)
    expected_premium_clause_id = f"CL-PREMIUM-TABLE#{slugify('₹' + formatted_amount)}"
    premium_query = f"annual premium sum insured {formatted_amount}"
    premium_result = retrieval_agent.retrieve(conn, premium_query, filters=filters, k=_PREMIUM_LOOKUP_K)

    row = next((c for c in premium_result.chunks if c.clause_id == expected_premium_clause_id), None)
    if row is None:
        # target sum-insured amount isn't offered by this insurer, or wasn't
        # retrieved — fall back to whatever premium row/table did surface,
        # rather than silently reporting no premium at all.
        row = next((c for c in premium_result.chunks if c.chunk_type in ("table_row", "table_block")), None)

    if row is not None:
        sheet.product_name = row.product_name
        premium = _select_premium_for_age(row.text_content, profile.age)
        if premium is None:
            inr_values = [
                int(normalize_numeric_token(m).value)
                for m in NUMERIC_PATTERN.findall(row.text_content)
                if normalize_numeric_token(m).kind == "inr"
            ]
            premium = min(inr_values) if inr_values else None
        sheet.premium_inr = premium
        sheet.premium_chunk_id = row.chunk_id
        sheet.premium_clause_id = row.clause_id
        sheet.premium_chunk_text = row.text_content

    suminsured_result = retrieval_agent.retrieve(conn, "sum insured options", filters=filters, k=2)
    for chunk in suminsured_result.chunks:
        values = [
            int(normalize_numeric_token(m).value)
            for m in NUMERIC_PATTERN.findall(chunk.text_content)
            if normalize_numeric_token(m).kind == "inr"
        ]
        if values:
            sheet.sum_insured_options_inr = sorted(set(values))
            break

    for ailment, flagged in profile.ped_flags.items():
        if not flagged:
            continue
        ped_result = retrieval_agent.retrieve(conn, f"{ailment} waiting period sub-limit", filters=filters, k=3)
        row = next((c for c in ped_result.chunks if c.chunk_type == "table_row"), None)
        if row is None:
            continue
        months = None
        inr = None
        for match in NUMERIC_PATTERN.findall(row.text_content):
            claim = normalize_numeric_token(match)
            if claim.kind == "duration" and claim.unit == "months" and months is None:
                months = int(claim.value)
            elif claim.kind == "inr" and inr is None:
                inr = int(claim.value)
        if months is not None:
            sheet.ped_waiting_periods_months[ailment] = months
        if inr is not None:
            sheet.ped_sub_limits_inr[ailment] = inr
        sheet.ped_chunk_ids[ailment] = row.chunk_id
        sheet.ped_clause_ids[ailment] = row.clause_id
        sheet.ped_chunk_texts[ailment] = row.text_content

    return sheet


def _score_plan(profile: Profile, sheet: PlanFactSheet) -> float:
    """Pure Python, no LLM. Weighted fit across budget (0.4), PED waiting
    period for flagged conditions (0.4), and sum-insured availability (0.2)."""
    score = 0.0
    weight_total = 0.0

    if sheet.premium_inr is not None:
        if sheet.premium_inr <= profile.budget_annual_inr:
            budget_score = 1.0
        else:
            overage_ratio = (sheet.premium_inr - profile.budget_annual_inr) / profile.budget_annual_inr
            budget_score = max(0.0, 1.0 - overage_ratio)
        score += 0.4 * budget_score
        weight_total += 0.4

    flagged = [a for a, has in profile.ped_flags.items() if has]
    if flagged:
        waits = [sheet.ped_waiting_periods_months[a] for a in flagged if a in sheet.ped_waiting_periods_months]
        if waits:
            avg_wait = sum(waits) / len(waits)
            ped_score = max(0.0, 1.0 - avg_wait / 48.0)  # 48 months ~ longest wait seen in this market
            score += 0.4 * ped_score
            weight_total += 0.4

    if sheet.sum_insured_options_inr:
        si_score = 1.0 if profile.sum_insured_target_inr in sheet.sum_insured_options_inr else 0.5
        score += 0.2 * si_score
        weight_total += 0.2

    return score / weight_total if weight_total else 0.0


def _template_rationale(profile: Profile, sheet: PlanFactSheet, is_top: bool) -> str:
    # Every number here is embedded with its own [clause_id] citation tag,
    # each individually traceable to its own source chunk (Guardrail's
    # verify_claim checks each tag's number against that exact chunk's
    # text — see agents/numeric_extraction.py).
    parts = []
    if sheet.premium_inr is not None and sheet.premium_clause_id:
        tag = sheet.qualified_clause_id(sheet.premium_clause_id)
        parts.append(f"premium ₹{sheet.premium_inr:,}/year [{tag}]")
    flagged_with_waits = {
        a: m for a, m in sheet.ped_waiting_periods_months.items() if profile.ped_flags.get(a) and a in sheet.ped_clause_ids
    }
    if flagged_with_waits:
        wait_desc = ", ".join(
            f"{a} wait {m} months [{sheet.qualified_clause_id(sheet.ped_clause_ids[a])}]" for a, m in flagged_with_waits.items()
        )
        parts.append(wait_desc)
    prefix = "Best overall fit" if is_top else "Alternative"
    return f"{prefix}: " + "; ".join(parts) if parts else prefix


def _template_trade_off(sheet: PlanFactSheet, top: PlanFactSheet) -> str | None:
    # Deliberately NOT a computed diff (e.g. "₹3,000/year cheaper") — a
    # subtraction wouldn't appear verbatim in either source chunk, and the
    # Guardrail has no way to verify derived arithmetic. Instead both
    # premiums are stated individually, each with its own citation, so every
    # number in this sentence is independently traceable.
    if not (sheet.premium_inr and sheet.premium_clause_id and top.premium_inr and top.premium_clause_id):
        return None
    sheet_tag = sheet.qualified_clause_id(sheet.premium_clause_id)
    top_tag = top.qualified_clause_id(top.premium_clause_id)
    return (
        f"Premium is ₹{sheet.premium_inr:,}/year [{sheet_tag}], versus "
        f"₹{top.premium_inr:,}/year [{top_tag}] for the top pick, {top.insurer}."
    )


class RecommendationAgent:
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client

    def recommend(self, profile: Profile, fact_sheets: list[PlanFactSheet]) -> list[RankedPlan]:
        scored_sheets = sorted(fact_sheets, key=lambda s: _score_plan(profile, s), reverse=True)
        if not scored_sheets:
            return []

        top = scored_sheets[0]
        ranked: list[RankedPlan] = []
        for i, sheet in enumerate(scored_sheets, start=1):
            is_top = i == 1
            rationale = self._phrase_rationale(profile, sheet, is_top)
            trade_off = None if is_top else _template_trade_off(sheet, top)
            ranked.append(
                RankedPlan(
                    insurer=sheet.insurer,
                    product_name=sheet.product_name,
                    rank=i,
                    score=_score_plan(profile, sheet),
                    one_line_rationale=rationale,
                    trade_off_vs_top_pick=trade_off,
                    supporting_chunk_ids=sheet.all_chunk_ids(),
                )
            )
        return ranked

    def _phrase_rationale(self, profile: Profile, sheet: PlanFactSheet, is_top: bool) -> str:
        if self.llm_client is None:
            return _template_rationale(profile, sheet, is_top)
        try:
            system = PROMPT_PATH.read_text()
            premium_tag = sheet.qualified_clause_id(sheet.premium_clause_id) if sheet.premium_clause_id else None
            ped_tags = {
                a: (m, sheet.qualified_clause_id(sheet.ped_clause_ids[a]))
                for a, m in sheet.ped_waiting_periods_months.items()
                if a in sheet.ped_clause_ids
            }
            facts = (
                f"Insurer: {sheet.insurer}. "
                f"Premium: {sheet.premium_inr} [{premium_tag}]. "
                f"PED waiting periods (months) with citation tag: {ped_tags}."
            )
            response = self.llm_client.complete(system=system, messages=[{"role": "user", "content": facts}])
            return response.text.strip()
        except LLMNotConfiguredError:
            return _template_rationale(profile, sheet, is_top)

    def advise_portability(
        self,
        months_on_current_plan: int,
        candidate_waiting_period_months: int,
        candidate_chunk_id: UUID | None = None,
    ) -> PortabilityAdvice:
        """Pure arithmetic per IRDAI portability rules: time already served
        credits against the new plan's waiting period. No LLM needed for the
        math; only the explanation text could optionally be LLM-phrased."""
        credited = min(months_on_current_plan, candidate_waiting_period_months)
        remaining = max(0, candidate_waiting_period_months - credited)

        if remaining == 0:
            recommendation: Literal["port", "stay_or_wait"] = "port"
            explanation = (
                f"You have already served {credited} months, which fully covers the candidate "
                f"plan's {candidate_waiting_period_months}-month waiting period — porting preserves "
                "full PED coverage immediately."
            )
        else:
            recommendation = "stay_or_wait"
            explanation = (
                f"You have served {credited} of the candidate plan's "
                f"{candidate_waiting_period_months}-month waiting period; {remaining} more month(s) "
                "of waiting would remain after porting."
            )

        return PortabilityAdvice(
            credited_months=credited,
            remaining_wait_months=remaining,
            recommendation=recommendation,
            explanation=explanation,
            supporting_chunk_ids=[candidate_chunk_id] if candidate_chunk_id else [],
        )
