# PolicyMitra

A RAG assistant for Indian health insurance with three modules: a policy FAQ/claims explainer
(Module 1), a plan recommendation engine (Module 2, informational-only), and an agent copilot
(Module 3, B2B drafting). Full product spec in `docs/PRD.md`; system design in `docs/agents.md`,
`docs/skills.md`, `docs/memory.md`; implementation decisions in `docs/architecture.md`.

## Status

All three modules are implemented and working end-to-end against an **embedded SQLite
database** (no server, no credentials, no required `.env`) and a small synthetic 3-insurer
corpus. Verified results:

- Retrieval recall@5: **94.7%** (18/19 golden questions) — unchanged across the
  Postgres→SQLite migration
- Offline numeric-presence accuracy: **92.9%**
- Recommendation ranking accuracy: **100%** (4/4 hand-worked scenarios)
- 62/62 tests passing (50 unit, 12 integration)

No LLM API key is required to run ingestion, retrieval, comparison, recommendation, or the eval
suite — generation-dependent steps (Q&A answers, drafting) return a clean `503` without one, and
start working the moment a key is added (see `docs/architecture.md` #11).

### Choosing an LLM provider

The system supports two interchangeable providers, selected purely via environment variables —
no code changes:

| Provider | Variables | Notes |
|---|---|---|
| Anthropic (default) | `ANTHROPIC_API_KEY`, `CLAUDE_MODEL` | Preferred automatically if both keys are set. |
| OpenRouter | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | One key, any model in [OpenRouter's catalog](https://openrouter.ai/models). |

Set `LLM_PROVIDER=anthropic` or `LLM_PROVIDER=openrouter` to force a provider explicitly;
leave it blank to auto-detect (see `docs/architecture.md` #12).

## Setup

Three commands. No database server, no `sudo`, no `.env` required:

```bash
make setup    # venv + pip install
make ingest   # parses + chunks + embeds the synthetic corpus into data/policymitra.db
make api      # FastAPI on :8000 (auto-creates/migrates the DB file if missing)
```

Frontend:

```bash
cd frontend && npm install && npm run dev   # Next.js on :3000
```

The SQLite database lives at `data/policymitra.db` (git-ignored; override with
`POLICYMITRA_DB`). `make reset-db` deletes it for a fresh start; `make migrate` applies the
schema explicitly (also happens automatically on first connection).

Requires SQLite ≥ 3.35 with FTS5 (any standard Python 3.11+ build; on Debian that means
bookworm or newer — the devcontainer image is already set accordingly).

## GitHub Codespaces

Create a codespace and everything is set up automatically by
`.devcontainer/postCreateCommand.sh`: venv, dependencies, DB migration, corpus ingestion,
frontend `npm install`, and `frontend/.env.local` pointing at the forwarded API URL.

- **LLM keys**: add `ANTHROPIC_API_KEY` (and optionally `OPENROUTER_API_KEY`,
  `VOYAGE_API_KEY`) as Codespaces secrets (*Settings → Codespaces → Secrets*) instead of a
  `.env` file — real environment variables always take precedence and never touch disk.
- **Port visibility**: the browser loads the frontend from the forwarded `-3000` origin and
  calls the API on the forwarded `-8000` origin, so port 8000 must be reachable. Setup makes
  it public best-effort; if API calls fail with an opaque error that looks like CORS, check
  the Ports panel and set port 8000's visibility to Public
  (`gh codespace ports visibility 8000:public -c "$CODESPACE_NAME"`).

## Security defaults

- **Zero stored credentials** — embedded SQLite means no DB passwords anywhere (nothing for
  secret scanners to flag, nothing to rotate).
- **Restrictive CORS** — localhost plus the Codespaces forwarded frontend origin only; never
  a wildcard (`api/main.py::_cors_origins`).
- **Rate limiting** — per-IP sliding window on `/api/v1/*` (default 30 req/min, health
  endpoint exempt), tunable via `RATE_LIMIT_PER_MINUTE`, `0` disables (`api/rate_limit.py`).

## Testing & Eval

```bash
make test-unit          # 50 tests, no DB needed
make test-integration   # 12 tests, temp SQLite file + real corpus
make retrieval-eval     # recall@5 against the golden set
make eval               # full acceptance gate — recall@5, numeric-presence, recommendation
                        # ranking (+ LLM-judged faithfulness if ANTHROPIC_API_KEY is set)
```

`make eval` is the acceptance gate referenced in `CLAUDE.md`: it must be run before merging any
change to chunking, retrieval, or agent prompts, and fails the build if retrieval recall@5 drops
below 90%.

## Repo Layout

```
docs/            PRD, agents, skills, memory, architecture-decisions
db/              schema migrations, SQLite connection helper
corpus/          synthetic insurer documents (fictional, for dev/testing)
ingestion/       parsing + table-aware chunking + embedding pipeline
retrieval/       hybrid (FTS5 BM25 + brute-force cosine) search, reranking
agents/          Router, Retrieval, Q&A, Recommendation, Comparison, Drafting, Guardrail
  prompts/       versioned prompt files
api/             FastAPI app (+ rate limiting middleware)
eval/            golden sets + eval harness
frontend/        Next.js chat/recommend/compare/agent-copilot UI
tests/           unit + integration tests
data/            embedded SQLite database (git-ignored, auto-created)
```
