"""Verifies the comparison agent's core normalization behavior: three
insurers phrasing "room rent cap" completely differently ("Room Category
Limit" / "Accommodation Charges Limit" / "Room Rent Sub-limit") all land
under the same normalized `room_rent_cap` row, each showing its own
original text (docs/skills.md "Premium & Plan Comparison")."""

from datetime import date
from uuid import uuid4

from agents.comparison_agent import FIELD_QUERIES, NOT_FOUND_TEXT, ComparisonAgent, PlanIdentifier
from retrieval.models import RetrievalResult, RetrievedChunk


def _chunk(insurer: str, text: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid4(),
        doc_id=uuid4(),
        clause_id="CL-ROOM-RENT",
        chunk_type="prose",
        text_content=text,
        table_context=None,
        insurer=insurer,
        product_name="Plan",
        doc_version="v1.0",
        effective_date=date(2026, 1, 1),
        section_title=None,
        score=1.0,
    )


class _FakeRetrievalAgent:
    """Duck-typed stand-in for agents.retrieval_agent.RetrievalAgent — returns
    canned results per (insurer, query) so this test needs no DB/network."""

    def __init__(self, data: dict[tuple[str, str], RetrievedChunk]):
        self._data = data

    def retrieve(self, conn, query, filters=None, k=5, known_slots=None):
        insurer = filters.insurer if filters else None
        chunk = self._data.get((insurer, query))
        return RetrievalResult(query=query, chunks=[chunk] if chunk else [])


def test_room_rent_normalizes_across_different_terminology():
    room_rent_query = FIELD_QUERIES["room_rent_cap"]
    data = {
        ("Arogya Shield General Insurance", room_rent_query): _chunk(
            "Arogya Shield General Insurance", "Room Category Limit: 1% of Sum Insured per day."
        ),
        ("Suraksha Health Insurance", room_rent_query): _chunk(
            "Suraksha Health Insurance", "Accommodation Charges Limit: no percentage capping."
        ),
        ("Nirvana Care Insurance", room_rent_query): _chunk(
            "Nirvana Care Insurance",
            "Room Rent Sub-limit: 2% of Sum Insured, capped at ₹5,000/day.",
        ),
    }
    plans = [
        PlanIdentifier(insurer="Arogya Shield General Insurance"),
        PlanIdentifier(insurer="Suraksha Health Insurance"),
        PlanIdentifier(insurer="Nirvana Care Insurance"),
    ]

    table = ComparisonAgent().compare(conn=None, retrieval_agent=_FakeRetrievalAgent(data), plans=plans)

    room_rent_row = next(r for r in table.rows if r.field == "room_rent_cap")
    assert "Room Category Limit" in room_rent_row.values["Arogya Shield General Insurance"]
    assert "Accommodation Charges Limit" in room_rent_row.values["Suraksha Health Insurance"]
    assert "Room Rent Sub-limit" in room_rent_row.values["Nirvana Care Insurance"]


def test_missing_field_falls_back_to_not_found_text():
    plans = [PlanIdentifier(insurer="A"), PlanIdentifier(insurer="B")]
    table = ComparisonAgent().compare(conn=None, retrieval_agent=_FakeRetrievalAgent({}), plans=plans)

    for row in table.rows:
        assert row.values["A"] == NOT_FOUND_TEXT
        assert row.values["B"] == NOT_FOUND_TEXT


def test_compare_requires_between_two_and_four_plans():
    import pytest

    with pytest.raises(ValueError):
        ComparisonAgent().compare(conn=None, retrieval_agent=_FakeRetrievalAgent({}), plans=[PlanIdentifier(insurer="A")])
