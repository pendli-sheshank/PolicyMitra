"""FastAPI app factory. Loads .env before importing anything that reads
GEMINI_API_KEY / OPENAI_API_KEY / DATABASE_URL at module-import time
(api/deps.py caches the LLM client and embedder once at startup).
load_dotenv never overrides real environment variables, so values supplied
via GitHub Codespaces secrets (or any exported env var) always win over a
.env file."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from agents.base import LLMNotConfiguredError  # noqa: E402
from api.rate_limit import RateLimitMiddleware  # noqa: E402
from api.routes import (  # noqa: E402
    agent_notes,
    audit,
    comparison,
    drafting,
    health,
    profile,
    qa,
    recommendation,
)


def _cors_origins() -> list[str]:
    """Restrictive allow-list, no wildcards: localhost for local dev, plus the
    forwarded frontend origin when running in GitHub Codespaces (both env vars
    are set automatically by Codespaces)."""
    origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    codespace = os.environ.get("CODESPACE_NAME")
    domain = os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN")
    if codespace and domain:
        origins.append(f"https://{codespace}-3000.{domain}")
    return origins


def create_app() -> FastAPI:
    app = FastAPI(title="PolicyMitra API", version="0.1.0")

    # Added before CORSMiddleware: Starlette makes the last-added middleware
    # outermost, so CORS wraps the rate limiter and 429 responses still carry
    # CORS headers (otherwise the browser couldn't read them).
    rate_limit = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "30"))
    if rate_limit > 0:
        app.add_middleware(RateLimitMiddleware, limit=rate_limit)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(LLMNotConfiguredError)
    def llm_not_configured_handler(request: Request, exc: LLMNotConfiguredError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"error": "llm_unavailable", "detail": str(exc)})

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(qa.router, prefix="/api/v1")
    app.include_router(recommendation.router, prefix="/api/v1")
    app.include_router(comparison.router, prefix="/api/v1")
    app.include_router(drafting.router, prefix="/api/v1")
    app.include_router(profile.router, prefix="/api/v1")
    app.include_router(agent_notes.router, prefix="/api/v1")
    app.include_router(audit.router, prefix="/api/v1")

    return app


app = create_app()
