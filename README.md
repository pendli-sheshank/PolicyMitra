# PolicyMitra

A RAG assistant for Indian health insurance with three modules: a policy FAQ/claims explainer
(Module 1), a plan recommendation engine (Module 2, informational-only), and an agent copilot
(Module 3, B2B drafting). Full product spec in `docs/PRD.md`; system design in `docs/agents.md`,
`docs/skills.md`, `docs/memory.md`; implementation decisions in `docs/architecture.md`.

## Status

All three modules are implemented and working end-to-end in this environment against a real
local Postgres + pgvector instance and a small synthetic 3-insurer corpus. Verified results:

- Retrieval recall@5: **94.7%** (18/19 golden questions)
- Offline numeric-presence accuracy: **92.9%**
- Recommendation ranking accuracy: **100%** (4/4 hand-worked scenarios)
- 48/48 tests passing (36 unit, 12 integration)
- Full Q&A / Recommend / Compare / Agent-Copilot flows verified in a real browser

No LLM API key is required to run ingestion, retrieval, comparison, recommendation, or the eval
suite — generation-dependent steps (Q&A answers, drafting) return a clean `503` without one, and
start working the moment a key is added (see `docs/architecture.md` #11).

### Choosing an LLM provider

The system supports two interchangeable providers, selected purely via `.env` — no code changes:

| Provider | `.env` variables | Notes |
|---|---|---|
| Anthropic (default) | `ANTHROPIC_API_KEY`, `CLAUDE_MODEL` | Preferred automatically if both keys are set. |
| OpenRouter | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | One key, any model in [OpenRouter's catalog](https://openrouter.ai/models) (OpenAI, Google, Meta, Mistral, Anthropic, and more). |

Set `LLM_PROVIDER=anthropic` or `LLM_PROVIDER=openrouter` to force a specific provider explicitly;
leave it blank to auto-detect (see `docs/architecture.md` #12).

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY/VOYAGE_API_KEY locally if you have them; never commit .env

# Postgres + pgvector (adjust for your OS/package manager)
sudo apt-get install -y postgresql-16-pgvector
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';"
sudo -u postgres psql -c "CREATE DATABASE policymitra;"

python3 -m db.migrate
python3 -m ingestion.cli --insurer-dir corpus/insurers/arogya_shield --embedder local
python3 -m ingestion.cli --insurer-dir corpus/insurers/suraksha_health --embedder local
python3 -m ingestion.cli --insurer-dir corpus/insurers/nirvana_care --embedder local
```

Or use the `Makefile` targets: `make setup`, `make db-up`, `make migrate`, `make ingest`.

## Running

```bash
make api         # FastAPI on :8000
cd frontend && npm install && npm run dev   # Next.js on :3000
```

## Testing & Eval

```bash
make test-unit          # 36 tests, no DB/network needed
make test-integration   # 12 tests, real Postgres test DB, real corpus
make retrieval-eval      # recall@5 against the golden set
make eval                # full acceptance gate — recall@5, numeric-presence, recommendation ranking
                          # (+ LLM-judged faithfulness automatically, if ANTHROPIC_API_KEY is set)
```

`make eval` is the acceptance gate referenced in `CLAUDE.md`: it must be run before merging any
change to chunking, retrieval, or agent prompts, and fails the build if retrieval recall@5 drops
below 90%.

## Repo Layout

```
docs/            PRD, agents, skills, memory, architecture-decisions
db/              schema migrations, connection helper
corpus/          synthetic insurer documents (fictional, for dev/testing)
ingestion/       parsing + table-aware chunking + embedding pipeline
retrieval/       hybrid (BM25 + pgvector) search, reranking
agents/          Router, Retrieval, Q&A, Recommendation, Comparison, Drafting, Guardrail
  prompts/       versioned prompt files
api/             FastAPI app
eval/            golden sets + eval harness
frontend/        Next.js chat/recommend/compare/agent-copilot UI
tests/           unit + integration tests
```
