const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface Citation {
  clause_id: string;
  chunk_id: string;
  insurer: string;
  product_name: string;
  doc_version: string;
  excerpt: string;
}

export interface QAResponse {
  response_id: string;
  session_id: string;
  answer: string;
  not_found: boolean;
  citations: Citation[];
  confidence: number | null;
  guardrail_verdict: "pass" | "repaired" | "blocked";
  disclaimer: string;
}

export interface Profile {
  age: number;
  dependents: number;
  city_tier: "tier1" | "tier2" | "tier3";
  ped_flags: Record<string, boolean>;
  budget_annual_inr: number;
  sum_insured_target_inr: number;
}

export interface RankedPlan {
  insurer: string;
  product_name: string;
  rank: number;
  score: number;
  one_line_rationale: string;
  trade_off_vs_top_pick: string | null;
  supporting_chunk_ids: string[];
}

export interface RecommendResponse {
  response_id: string;
  session_id: string;
  shortlist: RankedPlan[];
  guardrail_verdict: string;
  disclaimer: string;
}

export interface PlanIdentifier {
  insurer: string;
  product_name?: string | null;
}

export interface ComparisonRow {
  field: string;
  values: Record<string, string>;
  source_chunk_ids: Record<string, string[]>;
}

export interface ComparisonTable {
  plans: PlanIdentifier[];
  rows: ComparisonRow[];
}

export interface CompareResponse {
  response_id: string;
  session_id: string;
  table: ComparisonTable;
  disclaimer: string;
}

export interface DraftOutput {
  channel: "email" | "whatsapp";
  subject: string | null;
  body: string;
  status: "draft_pending_review";
  source_chunk_ids: string[];
}

export interface DraftResponse {
  response_id: string;
  draft: DraftOutput;
  guardrail_verdict: string;
  disclaimer: string;
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(`API error ${status}`);
    this.status = status;
    this.body = body;
  }
}

async function post<T>(path: string, body: unknown, headers: Record<string, string> = {}): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new ApiError(res.status, data);
  }
  return data as T;
}

export function askQuestion(message: string, sessionId?: string, insurerFilter?: string) {
  return post<QAResponse>("/api/v1/qa", {
    message,
    session_id: sessionId ?? null,
    insurer_filter: insurerFilter ?? null,
  });
}

export function getRecommendation(profile: Profile, candidateInsurers: string[], sessionId?: string) {
  return post<RecommendResponse>("/api/v1/recommend", {
    profile,
    candidate_insurers: candidateInsurers,
    session_id: sessionId ?? null,
  });
}

export function compare(plans: PlanIdentifier[], sessionId?: string) {
  return post<CompareResponse>("/api/v1/compare", { plans, session_id: sessionId ?? null });
}

export function draft(
  channel: "email" | "whatsapp",
  sourceText: string,
  sourceChunkIds: string[],
  chunkTextLookup: Record<string, string>,
  agentId: string,
  agentNotes?: string,
) {
  return post<DraftResponse>(
    "/api/v1/draft",
    {
      channel,
      source_text: sourceText,
      source_chunk_ids: sourceChunkIds,
      chunk_text_lookup: chunkTextLookup,
      agent_notes: agentNotes ?? null,
    },
    { "X-Agent-Id": agentId },
  );
}
