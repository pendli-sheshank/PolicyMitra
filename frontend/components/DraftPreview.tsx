"use client";

import { useState } from "react";
import { ApiError, draft, type DraftResponse } from "../lib/api";

export default function DraftPreview() {
  const [agentId, setAgentId] = useState("agent-demo");
  const [channel, setChannel] = useState<"email" | "whatsapp">("whatsapp");
  const [sourceText, setSourceText] = useState("");
  const [result, setResult] = useState<DraftResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit() {
    setLoading(true);
    setError(null);
    try {
      const response = await draft(channel, sourceText, [], {}, agentId);
      setResult(response);
    } catch (err) {
      setError(err instanceof ApiError ? JSON.stringify(err.body) : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h3>Agent Copilot: Draft Client Message</h3>
      <p style={{ fontSize: 13, color: "#666" }}>
        The human agent remains the accountable party — every draft is explicitly pending review below, and there
        is no send action anywhere in this UI.
      </p>
      <label style={{ display: "block", marginTop: 8 }}>
        Agent ID
        <input value={agentId} onChange={(e) => setAgentId(e.target.value)} style={{ display: "block" }} />
      </label>
      <label style={{ display: "block", marginTop: 8 }}>
        Channel
        <select
          value={channel}
          onChange={(e) => setChannel(e.target.value as "email" | "whatsapp")}
          style={{ display: "block" }}
        >
          <option value="whatsapp">WhatsApp</option>
          <option value="email">Email</option>
        </select>
      </label>
      <label style={{ display: "block", marginTop: 8 }}>
        Source content (from a Q&amp;A or comparison result)
        <textarea
          value={sourceText}
          onChange={(e) => setSourceText(e.target.value)}
          rows={4}
          style={{ display: "block", width: "100%" }}
        />
      </label>
      <button onClick={submit} disabled={loading || !sourceText.trim()} style={{ marginTop: 8 }}>
        {loading ? "Drafting…" : "Draft message"}
      </button>
      {error && <p style={{ color: "#dc3545" }}>{error}</p>}
      {result && (
        <div style={{ marginTop: 16, border: "2px solid #dc3545", borderRadius: 8, padding: 12 }}>
          <div
            style={{
              background: "#f8d7da",
              color: "#842029",
              padding: "4px 8px",
              borderRadius: 4,
              display: "inline-block",
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            DRAFT — PENDING AGENT REVIEW, NOT SENT
          </div>
          {result.draft.subject && (
            <p>
              <strong>Subject:</strong> {result.draft.subject}
            </p>
          )}
          <p style={{ whiteSpace: "pre-wrap" }}>{result.draft.body}</p>
          <p style={{ fontSize: 11, color: "#888" }}>guardrail: {result.guardrail_verdict}</p>
        </div>
      )}
    </div>
  );
}
