"use client";

import { useState } from "react";
import ChatWindow from "../components/ChatWindow";
import ComparisonTableView from "../components/ComparisonTable";
import DraftPreview from "../components/DraftPreview";
import ProfileForm from "../components/ProfileForm";
import {
  MessageSquare,
  Zap,
  BarChart3,
  FileText,
  Menu,
  X,
  Moon,
  Sun,
} from "lucide-react";

type Mode = "chat" | "recommend" | "compare" | "agent";

interface NavItem {
  mode: Mode;
  label: string;
  icon: React.ReactNode;
  description: string;
}

const TABS: NavItem[] = [
  {
    mode: "chat",
    label: "Q&A Assistant",
    icon: <MessageSquare className="w-5 h-5" />,
    description: "Ask about policies and claims",
  },
  {
    mode: "recommend",
    label: "Find Plans",
    icon: <Zap className="w-5 h-5" />,
    description: "Get personalized recommendations",
  },
  {
    mode: "compare",
    label: "Compare Plans",
    icon: <BarChart3 className="w-5 h-5" />,
    description: "Side-by-side comparison",
  },
  {
    mode: "agent",
    label: "Agent Copilot",
    icon: <FileText className="w-5 h-5" />,
    description: "AI-powered document drafting",
  },
];

export default function Home() {
  const [mode, setMode] = useState<Mode>("chat");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [darkMode, setDarkMode] = useState(false);

  const currentTab = TABS.find((t) => t.mode === mode);

  return (
    <div className={darkMode ? "dark" : ""}>
      <div className="flex h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-50">
        {/* Sidebar */}
        <aside
          className={`${
            sidebarOpen ? "w-64" : "w-0"
          } transition-all duration-300 border-r border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 overflow-hidden flex flex-col`}
        >
          {/* Logo */}
          <div className="p-6 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-gradient-to-br from-brand-500 to-brand-600 rounded-lg flex items-center justify-center text-white font-bold text-lg">
                PM
              </div>
              <div>
                <h1 className="font-bold text-lg">PolicyMitra</h1>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Health Insurance AI
                </p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2">
            {TABS.map((tab) => (
              <button
                key={tab.mode}
                onClick={() => setMode(tab.mode)}
                className={`w-full text-left px-4 py-3 rounded-lg transition-all duration-200 ${
                  mode === tab.mode
                    ? "bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800"
                    : "text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={
                      mode === tab.mode ? "text-brand-600" : "text-slate-400"
                    }
                  >
                    {tab.icon}
                  </div>
                  <div>
                    <div className="font-semibold text-sm">{tab.label}</div>
                    <div
                      className={`text-xs ${
                        mode === tab.mode
                          ? "text-brand-600 dark:text-brand-400"
                          : "text-slate-500 dark:text-slate-400"
                      }`}
                    >
                      {tab.description}
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-slate-200 dark:border-slate-800">
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Powered by RAG + AI
            </p>
          </div>
        </aside>

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <header className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
              >
                {sidebarOpen ? (
                  <X className="w-5 h-5" />
                ) : (
                  <Menu className="w-5 h-5" />
                )}
              </button>
              <div>
                <h2 className="text-lg font-semibold">{currentTab?.label}</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {currentTab?.description}
                </p>
              </div>
            </div>

            {/* Theme Toggle */}
            <button
              onClick={() => setDarkMode(!darkMode)}
              className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
            >
              {darkMode ? (
                <Sun className="w-5 h-5" />
              ) : (
                <Moon className="w-5 h-5" />
              )}
            </button>
          </header>

          {/* Content */}
          <main className="flex-1 overflow-auto bg-white dark:bg-slate-950">
            <div className="animate-fade-in">
              {mode === "chat" && <ChatWindow />}
              {mode === "recommend" && <ProfileForm />}
              {mode === "compare" && <ComparisonTableView />}
              {mode === "agent" && <DraftPreview />}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
