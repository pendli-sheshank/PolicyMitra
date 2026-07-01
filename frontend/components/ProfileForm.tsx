"use client";

import { useState } from "react";
import { ApiError, getRecommendation, type Profile, type RecommendResponse } from "../lib/api";

const INSURERS = ["Arogya Shield General Insurance", "Suraksha Health Insurance", "Nirvana Care Insurance"];

export default function ProfileForm() {
  const [profile, setProfile] = useState<Profile>({
    age: 30,
    dependents: 1,
    city_tier: "tier2",
    ped_flags: {},
    budget_annual_inr: 15000,
    sum_insured_target_inr: 500000,
  });
  const [hasDiabetes, setHasDiabetes] = useState(false);
  const [result, setResult] = useState<RecommendResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit() {
    setLoading(true);
    setError(null);
    try {
      const p: Profile = { ...profile, ped_flags: { "Diabetes Mellitus": hasDiabetes } };
      const response = await getRecommendation(p, INSURERS);
      setResult(response);
    } catch (err) {
      setError(err instanceof ApiError ? JSON.stringify(err.body) : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h3>Plan Recommendation</h3>
      <p style={{ fontSize: 13, color: "#666" }}>
        Informational only — not a purchase or issuance flow. Shortlist trade-offs, not a decision made for you.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, maxWidth: 480 }}>
        <label>
          Age
          <input
            type="number"
            value={profile.age}
            onChange={(e) => setProfile({ ...profile, age: Number(e.target.value) })}
          />
        </label>
        <label>
          Dependents
          <input
            type="number"
            value={profile.dependents}
            onChange={(e) => setProfile({ ...profile, dependents: Number(e.target.value) })}
          />
        </label>
        <label>
          City tier
          <select
            value={profile.city_tier}
            onChange={(e) => setProfile({ ...profile, city_tier: e.target.value as Profile["city_tier"] })}
          >
            <option value="tier1">Tier 1</option>
            <option value="tier2">Tier 2</option>
            <option value="tier3">Tier 3</option>
          </select>
        </label>
        <label>
          Budget (₹/year)
          <input
            type="number"
            value={profile.budget_annual_inr}
            onChange={(e) => setProfile({ ...profile, budget_annual_inr: Number(e.target.value) })}
          />
        </label>
        <label>
          Sum insured target (₹)
          <input
            type="number"
            value={profile.sum_insured_target_inr}
            onChange={(e) => setProfile({ ...profile, sum_insured_target_inr: Number(e.target.value) })}
          />
        </label>
        <label>
          Has diabetes (PED)
          <input type="checkbox" checked={hasDiabetes} onChange={(e) => setHasDiabetes(e.target.checked)} />
        </label>
      </div>
      <button onClick={submit} disabled={loading} style={{ marginTop: 12 }}>
        {loading ? "Ranking…" : "Get recommendation"}
      </button>
      {error && <p style={{ color: "#dc3545" }}>{error}</p>}
      {result && (
        <div style={{ marginTop: 16 }}>
          <p style={{ fontSize: 12, color: "#888" }}>guardrail: {result.guardrail_verdict}</p>
          {result.shortlist.map((plan) => (
            <div key={plan.insurer} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 12, marginBottom: 8 }}>
              <strong>
                #{plan.rank} {plan.insurer}
              </strong>{" "}
              — {plan.product_name}
              <p>{plan.one_line_rationale}</p>
              {plan.trade_off_vs_top_pick && (
                <p style={{ fontSize: 12, color: "#666" }}>{plan.trade_off_vs_top_pick}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
