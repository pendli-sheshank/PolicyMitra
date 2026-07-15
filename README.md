# PolicyMitra

A RAG assistant for Indian health insurance with three modules: a policy FAQ/claims explainer
(Module 1), a plan recommendation engine (Module 2, informational-only), and an agent copilot
(Module 3, B2B drafting). Full product spec in `docs/PRD.md`; system design in `docs/agents.md`,
`docs/skills.md`, `docs/memory.md`; implementation decisions in `docs/architecture.md`.

## Status

All three modules are implemented and working end-to-end against **Postgres + pgvector**
(a Supabase project in the default deployment) and a small synthetic 3-insurer corpus.

No LLM API key is required to run ingestion, retrieval, comparison, recommendation, or the
offline eval checks — generation-dependent steps (Q&A answers, drafting) return a clean `503`
without one, and start working the moment a key is added (see `docs/architecture.md` #11).

### Providers

| Concern | Provider | Variables | Without a key |
|---|---|---|---|
| Chat LLM | Google Gemini | `GEMINI_API_KEY`, `GEMINI_MODEL` (default `gemini-2.5-flash`) | Generative endpoints return `503`; routing falls back to keywords. |
| Embeddings | OpenAI `text-embedding-3-small` (1536-dim) | `OPENAI_API_KEY`, `OPENAI_EMBED_MODEL` | Offline hash embedder (deterministic, non-semantic — dev/CI only). |

Ingest-time and query-time embedders must match: after adding or removing `OPENAI_API_KEY`,
re-run `make ingest` (dense search is scoped to the active embedder's vectors, so a mismatch
degrades dense recall rather than mixing vector spaces).

## Setup

Requires a Postgres database with the pgvector extension — the default deployment is a
[Supabase](https://supabase.com) project. Set `DATABASE_URL` (in the environment or `.env`)
to the project's **session-pooler** DSN
(`postgresql://postgres.<project-ref>:<password>@aws-<n>-<region>.pooler.supabase.com:5432/postgres`
— the direct `db.<project-ref>.supabase.co` host is IPv6-only), then:

```bash
make setup    # venv + pip install
make ingest   # parses + chunks + embeds the synthetic corpus into Postgres
make api      # FastAPI on :8000 (applies the schema automatically on first connection)
```

Frontend:

```bash
cd frontend && npm install && npm run dev   # Next.js on :3000
```

`make migrate` applies the schema explicitly; `make reset-db` drops the four PolicyMitra
schemas (`kb`, `mem`, `agent`, `audit`) and re-applies everything for a fresh start — it
never touches other schemas in the database.

## GitHub Codespaces

Create a codespace and everything is set up automatically by
`.devcontainer/postCreateCommand.sh`: venv, dependencies, DB migration, corpus ingestion,
frontend `npm install`, and `frontend/.env.local` pointing at the forwarded API URL.

- **Secrets**: add `DATABASE_URL`, `GEMINI_API_KEY`, and `OPENAI_API_KEY` as Codespaces
  secrets (*Settings → Codespaces → Secrets*) instead of a `.env` file — real environment
  variables always take precedence and never touch disk.
- **Port visibility**: the browser loads the frontend from the forwarded `-3000` origin and
  calls the API on the forwarded `-8000` origin, so port 8000 must be reachable. Setup makes
  it public best-effort; if API calls fail with an opaque error that looks like CORS, check
  the Ports panel and set port 8000's visibility to Public
  (`gh codespace ports visibility 8000:public -c "$CODESPACE_NAME"`).

## Security defaults

- **No credentials in the repo** — `DATABASE_URL` (which contains the DB password) and API
  keys live only in real environment variables or a git-ignored `.env`.
- **Restrictive CORS** — localhost plus the Codespaces forwarded frontend origin only; never
  a wildcard (`api/main.py::_cors_origins`).
- **Rate limiting** — per-IP sliding window on `/api/v1/*` (default 30 req/min, health
  endpoint exempt), tunable via `RATE_LIMIT_PER_MINUTE`, `0` disables (`api/rate_limit.py`).

## Testing & Eval

```bash
make test-unit          # no DB needed (provider clients are exercised via mocked HTTP)
make test-integration   # needs TEST_DATABASE_URL — a DISPOSABLE Postgres database whose
                        # kb/mem/agent/audit schemas are reset + re-ingested each run
make retrieval-eval     # recall@5 against the golden set (needs DATABASE_URL + ingested corpus)
make eval               # full acceptance gate — recall@5, numeric-presence, recommendation
                        # ranking (+ LLM-judged faithfulness if GEMINI_API_KEY is set)
```

`make eval` is the acceptance gate referenced in `CLAUDE.md`: it must be run before merging any
change to chunking, retrieval, or agent prompts, and fails the build if retrieval recall@5 drops
below 90%.

## Repo Layout

```
docs/            PRD, agents, skills, memory, architecture-decisions
db/              schema migrations, Postgres/pgvector connection helper
corpus/          synthetic insurer documents (fictional, for dev/testing)
ingestion/       parsing + table-aware chunking + embedding pipeline (OpenAI / offline hash)
retrieval/       hybrid (Postgres FTS BM25-style + pgvector cosine) search, reranking
agents/          Router, Retrieval, Q&A, Recommendation, Comparison, Drafting, Guardrail
  prompts/       versioned prompt files
api/             FastAPI app (+ rate limiting middleware)
eval/            golden sets + eval harness
frontend/        Next.js chat/recommend/compare/agent-copilot UI
tests/           unit + integration tests
```
