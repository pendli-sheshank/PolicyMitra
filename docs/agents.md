# Agent Architecture — PolicyMitra

Defines the AI agents that make up the *product* (not to be confused with `CLAUDE.md`, which instructs whichever coding agent builds the repo). Companion docs: `PRD.md` (why), `skills.md` (capability map), `memory.md` (state/data design).

## Design Philosophy

A thin **Router Agent** classifies intent and hands off to one of a small number of **specialist agents**, each with a narrow, well-defined job. Every specialist's output passes through a single **Guardrail Agent** before reaching the user. Keep the graph shallow — resist adding agents until a specialist's prompt is genuinely doing two unrelated jobs.

## Agent Directory

### 1. Router Agent
- **Purpose**: classify the incoming message — FAQ/claims question, recommendation request, comparison request, agent-copilot drafting request, or out-of-scope.
- **Input**: raw message + conversation history (last N turns, `memory.md` §2).
- **Output**: intent label + extracted slots (insurer name, ailment, profile fields already mentioned).
- **Model tier**: small/fast — classification, not creativity.
- **Fallback**: low confidence → ask one disambiguating question rather than guess the route.

### 2. Retrieval Agent
- **Purpose**: given a query (plus slots from the Router), run hybrid search (BM25 + dense) over the document index, then rerank.
- **Input**: query, optional insurer/plan filter.
- **Output**: top-k chunks with source metadata (insurer, doc, page, clause ID).
- **Notes**: a retrieval function, not a generative call, aside from an optional query-rewrite step for vague questions.

### 3. Q&A Agent (Module 1)
- **Purpose**: answer a policy question strictly from retrieved chunks.
- **Input**: query + retrieved chunks, passed to the LLM as citation-enabled documents.
- **Output**: answer with inline citation to chunk/clause, or an explicit "not found in the documents I have."
- **Prompting guideline**: answer only from what's in the provided chunks — never fill gaps from general knowledge of "how health insurance usually works." A plausible generic answer is worse than admitting a gap.
- **Implementation note**: use the LLM's native citation grounding rather than a "please cite your source" instruction — it returns machine-checkable spans tied to the exact chunks you passed in, which the Guardrail Agent can verify programmatically instead of trusting the model's self-report.

### 4. Recommendation Agent (Module 2)
- **Purpose**: rank candidate plans against a user profile and explain trade-offs.
- **Input**: structured profile (age, dependents, city tier, PED flags, budget) + retrieved plan-level facts (waiting periods, sub-limits, premium bands).
- **Output**: ranked shortlist (3–5), each with a one-line rationale and the specific trade-off vs. the #1 pick.
- **Guardrail interaction**: every number shown must trace to a retrieved chunk, never to the model's prior knowledge of "typical" values.

### 5. Comparison Agent (Module 3)
- **Purpose**: side-by-side table for 2–4 named plans on request (used by both consumers and agents).
- **Input**: plan names/IDs.
- **Output**: structured table (waiting periods, room-rent cap, co-pay, sub-limits, network hospital count if available) + optional prose summary for agent-mode drafting.

### 6. Drafting Agent (Module 3, agent-copilot only)
- **Purpose**: turn a comparison or Q&A result into a client-ready message (email/WhatsApp tone).
- **Input**: comparison/Q&A output + channel + optional agent notes about the client.
- **Output**: draft message, clearly marked as a draft for the agent to review — never auto-sent.
- **Note**: the human agent remains the accountable party; this agent drafts, it doesn't advise the end client directly.

### 7. Guardrail Agent
- **Purpose**: the last gate before any output reaches a user. Two checks:
  1. **Numeric-claim verification** — every ₹/%/day figure in the draft must match its cited source chunk.
  2. **Scope check** — flag if an answer drifts from "explain the policy" toward "you should buy this" in a way that reads as individualized advice rather than information.
- **Behavior on failure**: strip or flag the unverified claim and regenerate that specific portion — never silently pass a failure through, and always log it (`memory.md` §7, audit log).

## Inter-Agent Flow

```
User message
  -> Router Agent (classify)
    -> Retrieval Agent (fetch grounding chunks)
      -> [Q&A | Recommendation | Comparison] Agent (generate)
        -> Drafting Agent (agent-copilot mode only)
          -> Guardrail Agent (verify)
            -> User
```

## Failure Modes & Fallbacks

- Low retrieval confidence → Q&A Agent says so explicitly, never guesses.
- Ambiguous insurer/plan reference (two similarly named plans) → Router Agent asks one clarifying question before routing.
- Guardrail rejects a numeric claim → regenerate that specific claim from source; don't silently drop the whole answer.
- Retrieval returns nothing relevant → surface "not in my current document set" rather than falling back to general knowledge.
