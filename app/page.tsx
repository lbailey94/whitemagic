"use client";

import { useState, useEffect } from "react";
import { AnimatedTriquetra } from "@/components/AnimatedTriquetra";
import { CopyButton } from "@/components/CopyButton";
import { ThemeToggle } from "@/components/ThemeToggle";

function BreathingSilhouette({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 200 200"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className={`triquetra-breathing text-lavender ${className || ""}`}
    >
      <g className="triquetra-spin">
        <circle cx="100" cy="76.9" r="40" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.3" />
        <circle cx="80" cy="111.55" r="40" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.3" />
        <circle cx="120" cy="111.55" r="40" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.3" />
        <circle cx="100" cy="100" r="2.5" fill="currentColor" opacity="0.15" />
      </g>
    </svg>
  );
}

const INSTALL_CMD = `pip install whitemagic[mcp]`;

const MCP_CONFIG = `{
  "mcpServers": {
    "whitemagic": {
      "command": "python3",
      "args": ["-m", "whitemagic.run_mcp_lean"],
      "env": { "WM_MCP_PRAT": "2" }
    }
  }
}`;

const AGENT_SURFACES = [
  { path: "/llms.txt", label: "llms.txt" },
  { path: "/.well-known/agent.json", label: "agent.json" },
  { path: "/server.json", label: "MCP server.json" },
  { path: "/mcp-registry.json", label: "MCP registry" },
  { path: "/api/manifest.json", label: "API manifest" },
  { path: "/api/prescience.json", label: "Prescience track record" },
  { path: "/robots.txt", label: "robots.txt" },
  { path: "/sitemap.xml", label: "sitemap.xml" },
];

export default function HomePage() {
  const [phase, setPhase] = useState<"breathing" | "spawned">("breathing");
  const [triKey, setTriKey] = useState(0);
  const [showConfig, setShowConfig] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setPhase("spawned"), 2400);
    return () => clearTimeout(t);
  }, []);

  return (
    <main className="relative z-10 flex min-h-screen flex-col items-center justify-center overflow-hidden">
      {/* Sigil */}
      <div
        onClick={() => setTriKey((k) => k + 1)}
        className="cursor-pointer transition-transform duration-300 hover:scale-[1.02] active:scale-[0.98]"
        title="點擊重播 · Click to replay"
      >
        {phase === "breathing" ? (
          <BreathingSilhouette className="h-[60vh] w-[60vh] max-w-[520px]" />
        ) : (
          <AnimatedTriquetra
            key={triKey}
            rainbow
            rainbowSpeed={8}
            className="h-[60vh] w-[60vh] max-w-[520px] opacity-90"
          />
        )}
      </div>

      {/* Wordmark + tagline */}
      <div className="z-10 mt-8 flex flex-col items-center px-4 text-center">
        <p className="font-zh text-lg text-dim md:text-xl">白術</p>
        <h1 className="font-head text-2xl font-bold tracking-tight text-ink md:text-3xl">
          WhiteMagic
        </h1>
        <p className="mt-1 font-zh text-sm text-dim md:text-base">AI 智能體的認知操作系統</p>
        <p className="mt-2 font-mono text-xs uppercase tracking-[0.3em] text-dim">
          Cognitive OS for AI Agents
        </p>
      </div>

      {/* Install command */}
      <div className="z-10 mt-8 flex flex-col items-center gap-3 px-4">
        <p className="font-zh text-[10px] text-dim/50">安裝</p>
        <div className="flex items-center gap-2 rounded-lg border border-border-light bg-surface/80 px-4 py-2.5 backdrop-blur-sm">
          <code className="font-mono text-sm text-fg">$ {INSTALL_CMD}</code>
          <CopyButton text={INSTALL_CMD} />
        </div>
        <button
          onClick={() => setShowConfig((v) => !v)}
          className="font-mono text-[10px] uppercase tracking-widest text-dim transition hover:text-fg"
        >
          <span className="font-zh text-[10px] text-dim/50">MCP 配置</span>
          {showConfig ? "hide" : "show"} MCP config
        </button>
        {showConfig && (
          <pre className="max-w-md rounded-lg border border-border-light bg-surface/80 p-4 text-left font-mono text-xs text-muted backdrop-blur-sm">
            {MCP_CONFIG}
          </pre>
        )}
      </div>

      {/* Agent surfaces — minimal links for crawlers/agents */}
      <div className="z-10 mt-12 flex flex-col items-center gap-2 px-4">
        <p className="font-zh text-[10px] text-dim/40">機器可讀接口</p>
        <div className="flex flex-wrap items-center justify-center gap-3">
        {AGENT_SURFACES.map((s) => (
          <a
            key={s.path}
            href={s.path}
            className="font-mono text-[10px] uppercase tracking-wide text-dim/60 transition hover:text-lavender"
          >
            {s.label}
          </a>
        ))}
        </div>
      </div>

      {/* PWA install link */}
      <div className="z-10 mt-8 flex flex-col items-center gap-2">
        <a
          href="/app"
          className="rounded-lg border border-lavender bg-lavender/10 px-6 py-2.5 font-mono text-xs uppercase tracking-wider text-lavender transition hover:bg-lavender/20"
        >
          <span className="font-zh text-[10px] text-lavender/60 mr-2">本地操作系統</span>
          Launch Local OS →
        </a>
        <p className="font-mono text-[9px] text-dim/40 max-w-xs text-center">
          WASM-powered memory, governance, karma — runs entirely in your browser
        </p>
      </div>

      {/* Theme toggle — bottom right */}
      <div className="fixed bottom-4 right-4 z-50">
        <ThemeToggle />
      </div>

      {/* Version footer */}
      <div className="z-10 mt-12 flex flex-col items-center pb-8 text-center">
        <p className="font-zh text-[10px] text-dim/40">白魔法實驗室 · MIT 開源 · 盧卡斯·貝利 製作</p>
        <p className="font-mono text-[10px] text-dim/40">v24.0.1 · MIT · Built by Lucas Bailey</p>
      </div>
    </main>
  );
}
