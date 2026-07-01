"use client";

import { useState } from "react";
import { ApiError, compare, type CompareResponse } from "../lib/api";

const INSURERS = ["Arogya Shield General Insurance", "Suraksha Health Insurance", "Nirvana Care Insurance"];

export default function ComparisonTableView() {
  const [selected, setSelected] = useState<string[]>([INSURERS[0], INSURERS[1]]);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function toggle(insurer: string) {
    setSelected((prev) => (prev.includes(insurer) ? prev.filter((i) => i !== insurer) : [...prev, insurer]));
  }

  async function submit() {
    setLoading(true);
    setError(null);
    try {
      const response = await compare(selected.map((insurer) => ({ insurer })));
      setResult(response);
    } catch (err) {
      setError(err instanceof ApiError ? JSON.stringify(err.body) : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h3>Compare Plans</h3>
      <div>
        {INSURERS.map((insurer) => (
          <label key={insurer} style={{ marginRight: 12 }}>
            <input type="checkbox" checked={selected.includes(insurer)} onChange={() => toggle(insurer)} /> {insurer}
          </label>
        ))}
      </div>
      <button onClick={submit} disabled={loading || selected.length < 2} style={{ marginTop: 8 }}>
        {loading ? "Comparing…" : "Compare"}
      </button>
      {selected.length < 2 && <p style={{ fontSize: 12, color: "#888" }}>Select 2-4 plans.</p>}
      {error && <p style={{ color: "#dc3545" }}>{error}</p>}
      {result && (
        <table style={{ marginTop: 16, borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              <th style={{ border: "1px solid #ddd", padding: 8, textAlign: "left" }}>Field</th>
              {result.table.plans.map((p) => (
                <th key={p.insurer} style={{ border: "1px solid #ddd", padding: 8, textAlign: "left" }}>
                  {p.insurer}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.table.rows.map((row) => (
              <tr key={row.field}>
                <td style={{ border: "1px solid #ddd", padding: 8, fontWeight: 600 }}>{row.field}</td>
                {result.table.plans.map((p) => (
                  <td key={p.insurer} style={{ border: "1px solid #ddd", padding: 8, fontSize: 13 }}>
                    {row.values[p.insurer]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
