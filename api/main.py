"""FastAPI app factory. Loads .env before importing anything that reads
ANTHROPIC_API_KEY at module-import time (api/deps.py caches the LLM client
once at startup)."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from agents.base import LLMNotConfiguredError  # noqa: E402
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


def create_app() -> FastAPI:
    app = FastAPI(title="PolicyMitra API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
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
