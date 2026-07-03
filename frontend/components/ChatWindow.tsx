"use client";

import { useState, useRef, useEffect } from "react";
import { ApiError, askQuestion, type QAResponse } from "../lib/api";
import CitationChip from "./CitationChip";
import { Send, Loader, CheckCircle2, AlertCircle } from "lucide-react";

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
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [turns, loading]);

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
    <div className="flex flex-col h-full bg-gradient-to-b from-slate-50 dark:from-slate-900 to-white dark:to-slate-950">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {turns.length === 0 && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 bg-brand-100 dark:bg-brand-900/30 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <MessageIcon className="w-8 h-8 text-brand-600" />
              </div>
              <h2 className="text-xl font-semibold mb-2">Welcome to PolicyMitra</h2>
              <p className="text-slate-600 dark:text-slate-400 text-sm">
                Ask any question about health insurance policies, claims, waiting periods, and more.
              </p>
              <p className="text-slate-500 dark:text-slate-500 text-xs mt-4">
                Example: &quot;What is the waiting period for cataract under Arogya Shield?&quot;
              </p>
            </div>
          </div>
        )}

        {turns.map((turn, i) => (
          <div
            key={i}
            className={`flex ${turn.role === "user" ? "justify-end" : "justify-start"} animate-slide-in`}
          >
            <div
              className={`max-w-2xl ${
                turn.role === "user"
                  ? "bg-brand-600 text-white rounded-2xl rounded-tr-none"
                  : "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-50 rounded-2xl rounded-tl-none"
              } px-4 py-3`}
            >
              {/* Error State */}
              {turn.error && (
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-red-600">Error</p>
                    <p className="text-xs opacity-75 mt-1">{turn.error}</p>
                  </div>
                </div>
              )}

              {/* Message Text */}
              {!turn.error && (
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <p className="whitespace-pre-wrap text-sm leading-relaxed">{turn.text}</p>
                </div>
              )}

              {/* Citations */}
              {turn.response && turn.response.citations.length > 0 && (
                <div className="mt-4 pt-3 border-t border-white/20 dark:border-slate-700">
                  <p className="text-xs font-semibold opacity-75 mb-2">Sources</p>
                  <div className="flex flex-wrap gap-2">
                    {turn.response.citations.map((c) => (
                      <CitationChip key={c.chunk_id} citation={c} />
                    ))}
                  </div>
                </div>
              )}

              {/* Metadata */}
              {turn.response && (
                <div className="mt-3 pt-3 border-t border-white/20 dark:border-slate-700 flex items-center gap-3">
                  <div className="flex items-center gap-1 text-xs opacity-75">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    {turn.response.guardrail_verdict}
                  </div>
                  {turn.response.confidence != null && (
                    <div className="text-xs opacity-75">
                      Confidence: {(turn.response.confidence * 100).toFixed(0)}%
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading State */}
        {loading && (
          <div className="flex justify-start animate-slide-in">
            <div className="bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-50 rounded-2xl rounded-tl-none px-4 py-3 flex items-center gap-2">
              <Loader className="w-4 h-4 animate-spin" />
              <span className="text-sm">Thinking…</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
        <div className="max-w-4xl mx-auto flex gap-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send())}
            placeholder="Ask about policies, claims, waiting periods…"
            className="input-base flex-1 resize-none max-h-24"
            rows={1}
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            className="btn-primary flex items-center justify-center gap-2 flex-shrink-0 h-10 w-10 p-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function MessageIcon(props: any) {
  return (
    <svg
      {...props}
      fill="currentColor"
      viewBox="0 0 20 20"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M2 5a2 2 0 012-2h12a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V5z" />
      <path d="M2.5 5L10 10.5 17.5 5" stroke="currentColor" strokeWidth="2" fill="none" />
    </svg>
  );
}
