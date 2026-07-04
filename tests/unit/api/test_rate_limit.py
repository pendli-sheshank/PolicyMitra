"""Rate-limit middleware behaviour, exercised against a stub app (no DB)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.rate_limit import RateLimitMiddleware


def _make_client(limit: int = 3) -> TestClient:
    app = FastAPI()

    @app.get("/api/v1/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/api/v1/thing")
    def thing() -> dict:
        return {"ok": True}

    @app.get("/outside")
    def outside() -> dict:
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, limit=limit)
    return TestClient(app)


def test_requests_within_limit_pass() -> None:
    client = _make_client(limit=3)
    for _ in range(3):
        assert client.get("/api/v1/thing").status_code == 200


def test_request_over_limit_gets_429_with_retry_after() -> None:
    client = _make_client(limit=3)
    for _ in range(3):
        client.get("/api/v1/thing")
    response = client.get("/api/v1/thing")
    assert response.status_code == 429
    assert response.json()["error"] == "rate_limited"
    assert int(response.headers["retry-after"]) >= 1


def test_health_is_exempt() -> None:
    client = _make_client(limit=2)
    for _ in range(10):
        assert client.get("/api/v1/healthz").status_code == 200


def test_paths_outside_api_prefix_are_exempt() -> None:
    client = _make_client(limit=2)
    for _ in range(10):
        assert client.get("/outside").status_code == 200


def test_window_slides(monkeypatch) -> None:
    import api.rate_limit as rl

    now = [1000.0]
    monkeypatch.setattr(rl.time, "monotonic", lambda: now[0])

    client = _make_client(limit=2)
    assert client.get("/api/v1/thing").status_code == 200
    assert client.get("/api/v1/thing").status_code == 200
    assert client.get("/api/v1/thing").status_code == 429

    now[0] += 61.0  # advance past the 60s window
    assert client.get("/api/v1/thing").status_code == 200


def test_clients_are_limited_independently() -> None:
    client = _make_client(limit=1)
    assert client.get("/api/v1/thing", headers={"x-forwarded-for": "10.0.0.1"}).status_code == 200
    assert client.get("/api/v1/thing", headers={"x-forwarded-for": "10.0.0.2"}).status_code == 200
    assert client.get("/api/v1/thing", headers={"x-forwarded-for": "10.0.0.1"}).status_code == 429
