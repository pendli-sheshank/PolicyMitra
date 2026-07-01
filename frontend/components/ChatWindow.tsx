"use client";

import { useState } from "react";
import { ApiError, askQuestion, type QAResponse } from "../lib/api";
import CitationChip from "./CitationChip";

interface Turn {
  role: "user" | "assistant";
  text: string;
  response?: QAResponse;
  error?: string;
}

export default function ChatWindow() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(false);

  async function send() {
    if (!input.trim() || loading) return;
    const message = input.trim();
    setInput("");
    setTurns((t) => [...t, { role: "user", text: message }]);
    setLoading(true);
    try {
      const response = await askQuestion(message, sessionId);
      setSessionId(response.session_id);
      setTurns((t) => [...t, { role: "assistant", text: response.answer, response }]);
    } catch (err) {
      const detail = err instanceof ApiError ? JSON.stringify(err.body) : String(err);
      setTurns((t) => [...t, { role: "assistant", text: "", error: detail }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
        {turns.length === 0 && (
          <p style={{ color: "#888" }}>
            Ask a policy question, e.g. &quot;What is the waiting period for cataract under Arogya Shield?&quot;
          </p>
        )}
        {turns.map((turn, i) => (
          <div key={i} style={{ marginBottom: 12, textAlign: turn.role === "user" ? "right" : "left" }}>
            <div
              style={{
                display: "inline-block",
                maxWidth: "80%",
                background: turn.role === "user" ? "#0d6efd" : "#f1f3f5",
                color: turn.role === "user" ? "white" : "black",
                borderRadius: 12,
                padding: "8px 12px",
              }}
            >
              {turn.error ? <span style={{ color: "#dc3545" }}>Error: {turn.error}</span> : turn.text}
            </div>
            {turn.response && turn.response.citations.length > 0 && (
              <div style={{ marginTop: 4 }}>
                {turn.response.citations.map((c) => (
                  <CitationChip key={c.chunk_id} citation={c} />
                ))}
              </div>
            )}
            {turn.response && (
              <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>
                guardrail: {turn.response.guardrail_verdict}
                {turn.response.confidence != null && ` · confidence ${turn.response.confidence.toFixed(2)}`}
              </div>
            )}
          </div>
        ))}
        {loading && <div style={{ color: "#888" }}>Thinking…</div>}
      </div>
      <div style={{ display: "flex", borderTop: "1px solid #ddd", padding: 8 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask about a policy…"
          style={{ flex: 1, padding: 8, border: "1px solid #ccc", borderRadius: 6 }}
        />
        <button onClick={send} disabled={loading} style={{ marginLeft: 8, padding: "8px 16px" }}>
          Send
        </button>
      </div>
    </div>
  );
}
