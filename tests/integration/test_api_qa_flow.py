"""FastAPI TestClient integration tests against the real test database. Only
imports api.main after the session fixture has pointed DATABASE_URL at the
test DB, so api/deps.py's connections resolve correctly."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz(conn):
    from api.main import app

    client = TestClient(app)
    response = client.get("/api/v1/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_qa_endpoint_never_returns_a_server_crash(conn):
    from api.main import app

    client = TestClient(app)
    response = client.post(
        "/api/v1/qa",
        json={"message": "What is the waiting period for cataract under Arogya Shield?"},
    )
    # Without an LLM key this is a clean 503; with one it would be 200 —
    # either way, never a 500 (docs/architecture.md #11).
    assert response.status_code in (200, 503)


def test_compare_endpoint_works_without_any_llm_key(conn):
    from api.main import app

    client = TestClient(app)
    plans = [
        {"insurer": "Arogya Shield General Insurance"},
        {"insurer": "Suraksha Health Insurance"},
    ]
    response = client.post("/api/v1/compare", json={"plans": plans})

    assert response.status_code == 200
    body = response.json()
    assert len(body["table"]["rows"]) > 0
    room_rent_row = next(r for r in body["table"]["rows"] if r["field"] == "room_rent_cap")
    assert "Room Category Limit" in room_rent_row["values"]["Arogya Shield General Insurance"]


def test_compare_rejects_fewer_than_two_plans():
    from api.main import app

    client = TestClient(app)
    response = client.post("/api/v1/compare", json={"plans": [{"insurer": "Arogya Shield General Insurance"}]})
    assert response.status_code == 422
