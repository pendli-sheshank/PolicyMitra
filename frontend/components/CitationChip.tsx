"use client";

import { useState } from "react";
import type { Citation } from "../lib/api";

export default function CitationChip({ citation }: { citation: Citation }) {
  const [open, setOpen] = useState(false);

  return (
    <span style={{ position: "relative", display: "inline-block", marginRight: 4 }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          fontSize: 11,
          background: "#e7f1ff",
          border: "1px solid #b6d4fe",
          borderRadius: 12,
          padding: "2px 8px",
          cursor: "pointer",
        }}
      >
        {citation.insurer.split(" ")[0]} · {citation.clause_id}
      </button>
      {open && (
        <div
          style={{
            position: "absolute",
            zIndex: 10,
            top: "120%",
            left: 0,
            width: 280,
            background: "white",
            border: "1px solid #ccc",
            borderRadius: 6,
            padding: 8,
            fontSize: 12,
            boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          }}
        >
          <strong>{citation.insurer}</strong> — {citation.product_name} ({citation.doc_version})
          <p style={{ marginTop: 4 }}>{citation.excerpt}</p>
        </div>
      )}
    </span>
  );
}
