"use client";

import { useState } from "react";
import ChatWindow from "../components/ChatWindow";
import ComparisonTableView from "../components/ComparisonTable";
import DisclaimerBanner from "../components/DisclaimerBanner";
import DraftPreview from "../components/DraftPreview";
import ProfileForm from "../components/ProfileForm";

type Mode = "chat" | "recommend" | "compare" | "agent";

const TABS: { mode: Mode; label: string }[] = [
  { mode: "chat", label: "Q&A" },
  { mode: "recommend", label: "Recommend" },
  { mode: "compare", label: "Compare" },
  { mode: "agent", label: "Agent Copilot" },
];

export default function Home() {
  const [mode, setMode] = useState<Mode>("chat");

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <header
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid #ddd",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <strong>PolicyMitra</strong>
        <nav>
          {TABS.map((tab) => (
            <button
              key={tab.mode}
              onClick={() => setMode(tab.mode)}
              style={{
                marginLeft: 8,
                background: mode === tab.mode ? "#0d6efd" : "#f1f3f5",
                color: mode === tab.mode ? "white" : "black",
              }}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>
      <main style={{ flex: 1, overflow: "auto" }}>
        {mode === "chat" && <ChatWindow />}
        {mode === "recommend" && <ProfileForm />}
        {mode === "compare" && <ComparisonTableView />}
        {mode === "agent" && <DraftPreview />}
      </main>
      <DisclaimerBanner />
    </div>
  );
}
