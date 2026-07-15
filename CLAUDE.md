# CLAUDE.md

Instructions for Claude Code (or any coding agent) working in this repository. Read this first. Product context lives in `PRD.md`; system design lives in `agents.md`, `skills.md`, `memory.md` — read whichever is relevant to the task at hand before writing code.

> Note: the requested filename `Create.md` is assumed to mean this file — Claude Code's conventional repo-instructions file — renamed accordingly. Say the word if a separate step-by-step build/creation guide was actually intended instead; easy to add alongside this one.

## What this project is

PolicyMitra: a RAG assistant for Indian health insurance with three modules — FAQ/claims explainer, plan recommender, agent copilot. Full spec in `PRD.md`.

## Repo Structure (proposed)

```
/ingestion       - PDF parsing, table-aware chunking, embedding pipeline
/retrieval       - hybrid search (BM25 + dense), reranking
/agents          - Router, Q&A, Recommendation, Comparison, Drafting, Guardrail
  /prompts       - versioned prompt files, not inline strings
/api             - FastAPI app, routes per module
/eval            - golden Q&A set + eval harness (run before every prompt/retrieval change)
/frontend        - chat UI
/docs            - PRD.md, agents.md, skills.md, memory.md (this set)
```

## Setup

```bash
make setup    # venv + pip install
make ingest   # chunk + embed the synthetic corpus into Postgres (kb.* schema)
make api      # FastAPI on :8000 — applies the schema automatically on first connection
```

The backend is **Postgres + pgvector** — a Supabase project in the default deployment.
`DATABASE_URL` is required (use the Supabase *session-pooler* DSN; the direct DB host is
IPv6-only). Chat LLM is Google Gemini (`GEMINI_API_KEY`), embeddings are OpenAI
`text-embedding-3-small` (`OPENAI_API_KEY`); without keys the system degrades cleanly
(503 on generative endpoints, offline hash embedder) — see `.env.example` for every
variable. Secrets come from real env vars (e.g. Codespaces secrets) or a local `.env` —
never commit `.env`. `make reset-db` drops and re-applies the four PolicyMitra schemas;
integration tests need `TEST_DATABASE_URL` (a disposable database). If you change or add
an embedding provider, re-run `make ingest` — query-time and ingest-time embedders must
match.

## Non-negotiables (read before touching prompts or retrieval)

1. **Never let generated numbers (₹, %, days) reach a user unless they're traceable to a retrieved chunk.** Enforced by the Guardrail Agent in `/agents` — don't bypass it, even in a quick test script.
2. **Run `/eval` against the golden set before merging any change to chunking, retrieval, or agent prompts.** A prompt tweak that "sounds better" but drops faithfulness is a regression, not an improvement.
3. **Table-aware chunking is not optional.** If you touch `/ingestion`, verify a known table (e.g., a sub-limit table) still retrieves as an intact unit — see `skills.md` for the exact quality bar.
4. **Don't add new storage of user input** without checking `memory.md` §5 first — especially anything health-related. No silent new "let's just log this for debugging" tables.
5. **Module 2 stays informational-only** (no purchase/issuance flow, no commission logic) until the regulatory question in `PRD.md` §12 is deliberately revisited — don't add a "buy now" button as a drive-by feature.

## Code Style

- Python: `black` + `ruff`, type hints on public functions.
- Prompts live in `/agents/prompts/` as versioned files, not inline strings — makes eval diffing sane.
- Commit messages: conventional commits (`feat:`, `fix:`, `docs:`, `eval:`).

## Testing

- Unit tests per module (`pytest`).
- The `/eval` golden-set run is the acceptance gate for anything touching retrieval or generation — a faithfulness-score drop is a blocking failure, not a warning.

## Where to look first for common tasks

- Adding a new insurer's documents → `/ingestion`, then re-run `/eval` to confirm nothing regressed.
- Changing how an answer is worded → the prompt file in `/agents/prompts/`, not the agent's Python logic.
- Adding a new question type → check `skills.md` first; it may already be a defined skill to extend rather than a new one to build.
