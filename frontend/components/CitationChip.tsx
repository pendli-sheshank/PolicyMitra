"use client";

import { useState } from "react";
import { X } from "lucide-react";
import type { Citation } from "../lib/api";

export default function CitationChip({ citation }: { citation: Citation }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setOpen((o) => !o)}
        className="badge bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800 hover:bg-brand-200 dark:hover:bg-brand-800/50 transition-colors"
      >
        <span className="font-medium">
          {citation.insurer.split(" ")[0]} · {citation.clause_id}
        </span>
      </button>

      {open && (
        <div className="absolute z-50 top-full left-0 mt-2 w-80 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg p-4 animate-fade-in">
          {/* Header */}
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-50">
                {citation.insurer}
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                {citation.product_name} · v{citation.doc_version}
              </p>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="p-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              <X className="w-4 h-4 text-slate-500" />
            </button>
          </div>

          {/* Divider */}
          <div className="w-full h-px bg-slate-200 dark:bg-slate-700 mb-3" />

          {/* Excerpt */}
          <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
            {citation.excerpt}
          </p>

          {/* Footer */}
          <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
              Chunk ID: {citation.chunk_id}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
