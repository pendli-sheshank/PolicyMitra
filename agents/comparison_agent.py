"""Comparison Agent (Module 3, also usable standalone): side-by-side table
for 2-4 named plans.

Normalization (skills.md "Premium & Plan Comparison"): insurers don't use
identical terminology for the same concept (Arogya Shield's "Room Category
Limit" vs Suraksha's "Accommodation Charges Limit" vs Nirvana's "Room Rent
Sub-limit"). Rather than matching on each insurer's own header vocabulary,
every field is queried by a fixed, insurer-agnostic concept string
(FIELD_QUERIES below) via retrieval — the normalization happens by querying
for the *concept*, not the label, so each insurer's own clause surfaces
under the same comparison row regardless of what they call it.
"""

from __future__ import annotations

from uuid import UUID

import psycopg
from pydantic import BaseModel

from agents.retrieval_agent import RetrievalAgent
from retrieval.models import RetrievalFilters

FIELD_QUERIES: dict[str, str] = {
    "premium_band": "annual premium sum insured age",
    "sum_insured_options": "sum insured options family floater",
    "waiting_period_initial": "initial waiting period",
    "room_rent_cap": "room rent limit accommodation charges category",
    "co_pay": "co-payment co-pay percentage",
    "network_hospital_count": "network hospitals cashless treatment",
}

NOT_FOUND_TEXT = "Not found in documents"


class PlanIdentifier(BaseModel):
    insurer: str
    product_name: str | None = None


class ComparisonRow(BaseModel):
    field: str
    values: dict[str, str]
    source_chunk_ids: dict[str, list[UUID]]


class ComparisonTable(BaseModel):
    plans: list[PlanIdentifier]
    rows: list[ComparisonRow]


class ComparisonAgent:
    def compare(self, conn: psycopg.Connection, retrieval_agent: RetrievalAgent, plans: list[PlanIdentifier]) -> ComparisonTable:
        if not 2 <= len(plans) <= 4:
            raise ValueError("Comparison requires between 2 and 4 plans.")

        rows = [self._build_field_row(conn, retrieval_agent, plans, field, query) for field, query in FIELD_QUERIES.items()]
        rows.append(self._build_exclusions_row(conn, retrieval_agent, plans))

        return ComparisonTable(plans=plans, rows=rows)

    def _build_field_row(
        self,
        conn: psycopg.Connection,
        retrieval_agent: RetrievalAgent,
        plans: list[PlanIdentifier],
        field: str,
        query: str,
    ) -> ComparisonRow:
        values: dict[str, str] = {}
        source_chunk_ids: dict[str, list[UUID]] = {}

        for plan in plans:
            filters = RetrievalFilters(insurer=plan.insurer)
            result = retrieval_agent.retrieve(conn, query, filters=filters, k=1)
            if result.chunks:
                chunk = result.chunks[0]
                values[plan.insurer] = chunk.text_content
                source_chunk_ids[plan.insurer] = [chunk.chunk_id]
            else:
                values[plan.insurer] = NOT_FOUND_TEXT
                source_chunk_ids[plan.insurer] = []

        return ComparisonRow(field=field, values=values, source_chunk_ids=source_chunk_ids)

    def _build_exclusions_row(
        self, conn: psycopg.Connection, retrieval_agent: RetrievalAgent, plans: list[PlanIdentifier]
    ) -> ComparisonRow:
        values: dict[str, str] = {}
        source_chunk_ids: dict[str, list[UUID]] = {}

        for plan in plans:
            filters = RetrievalFilters(insurer=plan.insurer)
            result = retrieval_agent.retrieve(conn, "exclusions not covered", filters=filters, k=3)
            exclusion_chunks = [c for c in result.chunks if c.clause_id.startswith("CL-EXCL")]
            values[plan.insurer] = "; ".join(c.text_content for c in exclusion_chunks) or NOT_FOUND_TEXT
            source_chunk_ids[plan.insurer] = [c.chunk_id for c in exclusion_chunks]

        return ComparisonRow(field="key_exclusions", values=values, source_chunk_ids=source_chunk_ids)
