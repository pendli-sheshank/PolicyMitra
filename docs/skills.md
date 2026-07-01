# Skill Map — PolicyMitra

Trigger → process → output → quality bar, for each discrete capability the system needs. Companion docs: `PRD.md`, `agents.md`, `memory.md`.

---

### Skill: Document Ingestion & Table-Aware Chunking
- **Trigger**: new or revised insurer PDF (policy wording, prospectus, CIS) added to the corpus.
- **Process**: parse preserving table structure — do not flatten tables to plain text, since waiting periods and sub-limits live in tables and naive splitting destroys row/column relationships. Chunk by clause/section boundary, not fixed token count. Attach metadata (insurer, product name, doc version, effective date, page, clause ID) to every chunk.
- **Output**: indexed chunks in the hybrid store, structured as custom-content documents so citation grounding maps back to your own chunk boundaries rather than an automatic sentence split.
- **Quality bar**: a table row (e.g., "Cataract — sub-limit ₹40,000") retrieves as a coherent unit, never split mid-row.

### Skill: Hybrid Retrieval
- **Trigger**: any query from the Retrieval Agent.
- **Process**: BM25 keyword search (catches exact clause numbers, plan names, medical terms) + dense semantic search, merged and reranked.
- **Output**: top-k ranked chunks with scores.
- **Quality bar**: recall@5 ≥90% on the golden eval set (`PRD.md` §11).

### Skill: Grounded Q&A with Citation
- **Trigger**: Module 1 question with retrieved chunks available.
- **Process**: answer using only retrieved content; attach clause-level citation to every factual sentence.
- **Output**: cited answer, or an explicit "not in the documents I have."
- **Quality bar**: 100% of numeric claims traceable to a cited chunk (enforced by the Guardrail Agent).

### Skill: Waiting Period / Sub-limit Lookup
- **Trigger**: question names a specific ailment, procedure, or condition category ("diabetes," "cataract," "maternity").
- **Process**: retrieve the relevant clause/table row for the named insurer/plan; surface both the waiting period and any applicable sub-limit or co-pay together, since users usually need both at once.
- **Output**: structured fact (duration/amount) + citation.

### Skill: Premium & Plan Comparison
- **Trigger**: comparison or recommendation request naming 2+ plans, or a profile-based recommendation.
- **Process**: pull comparable fields across plans (premium band, sum insured options, waiting periods, room-rent cap, co-pay, key exclusions) into a common schema before comparing — insurers don't use identical terminology, so this skill owns the normalization step.
- **Output**: comparison table + rationale.

### Skill: Portability/Renewal Advisory
- **Trigger**: user mentions an existing policy nearing renewal, or asks about switching insurers.
- **Process**: check accrued waiting-period credit (IRDAI portability rules preserve time served against PED waiting periods when porting within the window), compare against a candidate new plan's terms.
- **Output**: plain-language "port or stay" reasoning with the specific waiting-period math shown, not just a recommendation.

### Skill: Multi-lingual Support (Phase 3)
- **Trigger**: query in Hindi/regional language, or explicit language preference.
- **Process**: translate query for retrieval (source documents are English), generate answer, translate response — or rely on strong native multilingual grounding if quality allows skipping the round-trip.
- **Output**: answer in the user's language; citation still points to the (English) source clause.

### Skill: Agent-Mode Client Summary Drafting
- **Trigger**: agent-copilot user requests a client-ready summary from a comparison or Q&A result.
- **Process**: reformat structured comparison/Q&A output into email or WhatsApp-appropriate prose; preserve all cited facts unchanged.
- **Output**: draft message, explicitly labeled as pending agent review.
