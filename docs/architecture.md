# Architecture Decision Log — PolicyMitra

Companion to `PRD.md`, `agents.md`, `skills.md`, `memory.md`. Records concrete implementation decisions made while turning those specs into code, especially judgment calls where the spec left room for interpretation.

## Decisions

1. **Synthetic corpus source format**: hand-authored Markdown (`meta.yaml` + `policy_wording.md` per insurer) using `<!-- clause: ID -->` markers and pipe-tables, instead of real/synthetic PDFs. This is fully deterministic to parse and lets us demonstrate the "table row never splits mid-chunk" quality bar (skills.md) convincingly without wrestling with PDF table extraction for content we're authoring ourselves. `ingestion/parsers/pdf_parser.py` exists as an interface-compatible stub for when real insurer PDFs are added later.

2. **Embedding dimension fixed at 384**, matching the no-API-key local fallback embedder (`local_hash_embedder.py`, a deterministic hash-based embedding). `kb.embeddings.embedding` is `VECTOR(384)`. Swapping to a real provider (e.g. Voyage, 1024-dim) later requires `ALTER TABLE kb.embeddings ALTER COLUMN embedding TYPE VECTOR(n)` plus a full re-embed — pgvector requires a fixed dimension per column, this isn't solvable generically without knowing the real provider's dimension in advance.

3. **BM25 side implemented as Postgres native full-text search** (`tsvector`/`ts_rank_cd`) rather than a separate `rank_bm25` in-process index or OpenSearch. Chunks already live in Postgres; a second index would need to stay in sync on every re-ingest for no real benefit at this scale.

4. **Hybrid merge via Reciprocal Rank Fusion (RRF)**, not weighted score-sum — BM25 `ts_rank_cd` and pgvector cosine similarity aren't on comparable scales, and RRF (rank-based) avoids an arbitrary normalization constant.

5. **Citation contract is our own `[clause_id]` bracket-tag convention**, not a direct binding to Anthropic's Citations API response shape. The Q&A prompt instructs the model to tag every factual sentence with `[clause_id]`; Guardrail parses these tags mechanically. This keeps Guardrail's verification logic independent of the exact grounding API used — upgradeable to native Citations API spans later without changing the verification contract.

6. **Guardrail's numeric verification (steps 1–4: extract, citation-presence check, citation-membership check, normalized-value comparison) requires no LLM call at all** — pure regex/string matching. Only the *repair* step (rephrasing a single failed sentence) needs a live LLM. This means the core safety property ("never let an unverified number through") holds even with `NullLLMClient`: no key means no repair attempt, straight to a hard-coded redaction — a stricter, safer degrade, not a weaker one.

7. **Recommendation Agent ranking is deterministic Python** (`_score_plan()`), not LLM-driven. The LLM only phrases the one-line rationale/trade-off text, constrained to reference numbers already extracted by code. Guardrail still re-verifies those numbers independently. This structurally enforces the "every number must trace to a chunk, never the model's prior knowledge" requirement rather than relying on prompting alone.

8. **Session Memory TTL enforced without `pg_cron`** (unverified as installed in the target environment): a `mem.expire_sessions()` SQL function is called lazily on every session read, plus a standalone `api/jobs/expire_sessions.py` script that can be cron'd in a real deployment.

9. **Agent (Module 3) identity is a placeholder header** (`X-Agent-Id`), not a real auth system — explicitly out of scope for this build. Every Layer-4 query filters by this identity server-side so cross-agent data leakage is structurally impossible even without real auth, but the identity itself is not verified/authenticated.

10. **Frontend is a single-page Next.js app** (App Router) with a mode switch (Chat / Recommend / Compare / Agent Copilot) rather than separate routes — the four flows are simple enough that client-side tab state is sufficient, avoiding routing complexity the spec doesn't call for.

11. **LLM/embedding clients are pluggable**: `agents/llm_client.py::get_llm_client()` returns a real `AnthropicClient` when `ANTHROPIC_API_KEY` is set, else a `NullLLMClient` that raises a typed `LLMNotConfiguredError` (never crashes). The API layer converts this to a clean `503`. The eval harness and Router/Q&A agents have explicit no-key degrade paths (keyword-fallback routing, offline numeric-traceability checks) so the system is meaningfully testable before any key is added.

12. **OpenRouter added as a second LLM provider**, alongside Anthropic, so a user can point the whole system at any model in OpenRouter's catalog (OpenAI, Google, Meta, Mistral, Anthropic itself, and others) via one API key. Selection logic in `get_llm_client()`: an explicit `LLM_PROVIDER=anthropic|openrouter` env var wins; if unset, `ANTHROPIC_API_KEY` is preferred when both are set (keeps prior default behavior unchanged for existing users), else `OPENROUTER_API_KEY`, else `NullLLMClient`. `OpenRouterClient` talks to OpenRouter's OpenAI-compatible `/chat/completions` endpoint directly via `httpx` (no extra SDK dependency) and returns the same `LLMResponse` shape as `AnthropicClient`, so every agent (`RouterAgent`, `QAAgent`, `RecommendationAgent`, `DraftingAgent`, `GuardrailAgent`'s repair step) works unchanged regardless of which provider is active — the choice is entirely a `.env` concern, never an agent-code concern. An explicit `LLM_PROVIDER` with its key missing degrades to `NullLLMClient` rather than silently falling back to the other provider, since that would violate the principle of least surprise for a user who deliberately chose a provider.
