# Memory & Data Architecture — PolicyMitra

What the system remembers, at which layer, for how long, under what consent basis. Companion docs: `PRD.md`, `agents.md`.

## Layers

### 1. Knowledge Base (long-term, shared, non-personal)
The indexed corpus of insurer documents (chunks + embeddings + metadata) from the ingestion skill in `skills.md`. Versioned by document effective date — an answer must always be traceable to which document version produced it, since insurers revise wordings and a stale waiting-period figure is a real accuracy risk. Refreshed on a scheduled crawl/re-ingest, not loaded once and left alone.

### 2. Session Memory (conversation-level, short-lived)
Turn history and any slots extracted mid-conversation (age, city, ailment mentioned) — scoped to the current chat session. Lets the Router Agent avoid re-asking for information already given. Default TTL: session end, or a fixed window (e.g., 24h) for continuity across a refresh. Not persisted to a user profile unless the user explicitly saves it (Layer 3).

### 3. User Profile Memory (cross-session, opt-in)
Saved profile fields (age, dependents, city tier, budget, PED flags) letting a returning user skip re-entering intake for future recommendations. **Opt-in only** — a user must explicitly choose to save a profile; nothing here is written by default from a session. Health-related fields are the most sensitive data the system touches — see §5.

### 4. Agent-Mode Client Notes (B2B, per-agent)
For Module 3: a licensed agent's own notes on their clients — belongs to the agent's book of business, not the end client's own account. Scoped per agent login, never shared across agents, never used to train or improve the shared Knowledge Base.

## 5. Data Retention & Deletion

- Health-related disclosures (PED mentions, ailment questions) deserve the same handling discipline as a legally "sensitive" category even though the DPDP Act doesn't formally carve one out (see `PRD.md` §12). Collecting and processing this data needs a clear, specific consent basis and purpose limitation — don't collect more than the recommendation/Q&A flow actually needs, and don't repurpose it later without fresh consent.
- Build deletion-on-request as a first-class feature, not an afterthought: a user (or agent, for their client notes) can delete their Profile Memory (Layer 3) or Client Notes (Layer 4) entirely, and this should cascade through any cache or derived index — not just the primary record.
- Session Memory (Layer 2) should auto-expire; don't let "temporary" conversation context quietly become permanent by never being cleared.
- The Knowledge Base (Layer 1) contains no personal data — it's insurer-published documents — so it's exempt from these constraints, but keep it in a clearly separate store from Layers 2–4 so a deletion request can't accidentally touch it, or miss touching what it should.
- Every breach must be reportable under the DPDP Act regardless of materiality — design the retention/audit approach here assuming disclosure may be required, not just for "serious" incidents.

## 6. What NOT to Persist

- Full policy numbers, PAN, or Aadhaar numbers, even if a user pastes them into chat — redact before storing, if storing the conversation at all.
- Raw free-text health disclosures beyond the session, unless the user has explicitly opted into Profile Memory — prefer storing the extracted structured flag (`has_diabetes: true`) over the verbatim sentence where possible; it's more useful for ranking and less sensitive to hold onto.

## 7. Caching & Audit Log

- **Embedding cache**: cache chunk embeddings — Layer 1 is static between re-ingests, no need to recompute.
- **Response cache**: common FAQs ("what is a waiting period") can be cached at the answer level, but re-validate the cited source is still current before serving a cached answer.
- **Audit log**: every response logs which chunk IDs were used to generate it (see the Guardrail Agent in `agents.md`). This is separate from Session/Profile memory — an internal debugging/compliance trail, not user-facing — and can be retained on its own, longer policy, since it's useful for regression testing and dispute review independent of how long a given user's session or profile data lives.
