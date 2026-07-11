"use client";

import { useState, useEffect } from "react";

interface WanderStep {
  step: number;
  id: string;
  label: string;
  source: string;
  link_strength: number;
  tokens: number;
  preview: string;
  narration: string;
}

interface WanderResult {
  mode: string;
  seed: string;
  summary: string;
  steps: number;
  path: WanderStep[];
  error?: string;
}

const SUGGESTED_SEEDS = [
  "consciousness",
  "AI governance",
  "water systems",
  "energy",
  "meditation",
  "game theory",
  "spirituality",
  "agent safety",
  "fusion",
  "sacred geometry",
  "cyberbrain",
  "harmony",
  "teleology",
  "UAP",
  "resonance",
];

export function WanderTrail() {
  const [seed, setSeed] = useState("");
  const [steps, setSteps] = useState(8);
  const [diversity, setDiversity] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<WanderResult | null>(null);
  const [error, setError] = useState("");
  const [expandedStep, setExpandedStep] = useState<number | null>(null);
  const [history, setHistory] = useState<WanderResult[]>([]);

  const doWander = async (overrideSeed?: string) => {
    const s = overrideSeed || seed;
    if (!s.trim()) return;
    setLoading(true);
    setError("");
    setExpandedStep(null);
    try {
      const res = await fetch(
        `/api/aria/wander?seed=${encodeURIComponent(s)}&steps=${steps}&diversity=${diversity}`,
      );
      const data = (await res.json()) as WanderResult;
      if (data.error) setError(data.error);
      else {
        setResult(data);
        setHistory((prev) => [data, ...prev].slice(0, 5));
      }
    } catch {
      setError("Wander request failed");
    } finally {
      setLoading(false);
    }
  };

  const randomWander = () => {
    const randomSeed =
      SUGGESTED_SEEDS[Math.floor(Math.random() * SUGGESTED_SEEDS.length)];
    setSeed(randomSeed);
    doWander(randomSeed);
  };

  const sourceColors: Record<string, string> = {
    library: "text-blue-400",
    conversations: "text-green-400",
    research: "text-orange-400",
  };

  return (
    <div className="rounded-2xl border border-border bg-surface p-6">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-head text-lg font-semibold text-ink">
            Wander Trail
          </h3>
          <p className="mt-1 text-sm text-muted">
            Start with an idea and follow semantic links through the knowledge
            sphere. Each step reveals how concepts connect across domains.
          </p>
        </div>
        <button
          onClick={randomWander}
          className="shrink-0 rounded-lg border border-border bg-surface-alt px-3 py-1.5 font-mono text-xs text-lavender transition hover:bg-lavender-bg"
        >
          Random Wander
        </button>
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <input
          type="text"
          value={seed}
          onChange={(e) => setSeed(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && doWander()}
          placeholder="consciousness, AI governance, water systems..."
          className="flex-1 rounded-lg border border-border bg-surface-alt px-3 py-2 font-mono text-sm text-ink placeholder:text-dim focus:border-lavender focus:outline-none"
        />
        <select
          value={steps}
          onChange={(e) => setSteps(Number(e.target.value))}
          className="rounded-lg border border-border bg-surface-alt px-3 py-2 font-mono text-sm text-ink"
        >
          {[3, 5, 8, 12, 20].map((n) => (
            <option key={n} value={n}>
              {n} steps
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 font-mono text-xs text-muted">
          <input
            type="checkbox"
            checked={diversity}
            onChange={(e) => setDiversity(e.target.checked)}
            className="accent-lavender"
          />
          diverse sources
        </label>
        <button
          onClick={() => doWander()}
          disabled={loading || !seed.trim()}
          className="rounded-lg bg-lavender px-4 py-2 font-mono text-sm text-white transition hover:bg-lavender/80 disabled:opacity-50"
        >
          {loading ? "Wandering..." : "Wander"}
        </button>
      </div>

      {/* Suggested seeds */}
      <div className="mt-3 flex flex-wrap gap-1.5">
        <span className="font-mono text-[10px] text-dim">Try:</span>
        {SUGGESTED_SEEDS.slice(0, 8).map((s) => (
          <button
            key={s}
            onClick={() => {
              setSeed(s);
              doWander(s);
            }}
            className="rounded bg-surface-alt px-1.5 py-0.5 font-mono text-[10px] text-muted transition hover:text-lavender"
          >
            {s}
          </button>
        ))}
      </div>

      {error && (
        <p className="mt-3 font-mono text-sm text-red-500">{error}</p>
      )}

      {result && result.path && (
        <div className="mt-6">
          <div className="mb-4 rounded-lg border border-lavender/30 bg-lavender-bg/10 p-3">
            <p className="font-mono text-xs text-lavender">{result.summary}</p>
            <p className="mt-1 font-mono text-[10px] text-dim">
              Seed: &ldquo;{result.seed}&rdquo; · {result.steps} steps ·{" "}
              diversity: {result.path.some((p, i) => i > 0 && p.source !== result.path[i - 1].source) ? "yes" : "no"}
            </p>
          </div>

          <div className="space-y-2">
            {result.path.map((p, idx) => (
              <div
                key={p.step}
                className={`rounded-lg border transition ${
                  expandedStep === idx
                    ? "border-lavender bg-lavender-bg/10"
                    : "border-border bg-surface-alt/50 hover:border-lavender/30"
                }`}
              >
                <button
                  onClick={() =>
                    setExpandedStep(expandedStep === idx ? null : idx)
                  }
                  className="flex w-full items-center gap-2 p-3 text-left"
                >
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-lavender/20 font-mono text-[10px] text-lavender">
                    {p.step}
                  </span>
                  <span className="font-mono text-xs font-semibold text-ink">
                    {p.label}
                  </span>
                  <span
                    className={`font-mono text-[10px] ${sourceColors[p.source] || "text-dim"}`}
                  >
                    {p.source}
                  </span>
                  <span className="ml-auto font-mono text-[10px] text-muted">
                    ×{p.link_strength.toFixed(2)} · {p.tokens}t
                  </span>
                  <span className="font-mono text-[10px] text-dim">
                    {expandedStep === idx ? "▾" : "▸"}
                  </span>
                </button>

                {expandedStep === idx && (
                  <div className="border-t border-border px-3 pb-3">
                    <p className="mt-2 font-mono text-[11px] text-lavender">
                      {p.narration}
                    </p>
                    <pre className="mt-2 max-h-[200px] overflow-y-auto whitespace-pre-wrap rounded border border-border bg-surface p-2 font-mono text-[10px] leading-relaxed text-fg">
                      {p.preview}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Wander history */}
      {history.length > 1 && (
        <div className="mt-6 border-t border-border pt-4">
          <h4 className="mb-2 font-mono text-xs font-semibold text-dim">
            Recent Wanders
          </h4>
          <div className="space-y-1">
            {history.slice(1).map((h, i) => (
              <button
                key={i}
                onClick={() => {
                  setResult(h);
                  setSeed(h.seed);
                }}
                className="flex w-full items-center justify-between rounded px-2 py-1 font-mono text-[10px] text-muted transition hover:bg-surface-alt hover:text-fg"
              >
                <span>&ldquo;{h.seed}&rdquo; → {h.steps} steps</span>
                <span className="text-dim">{h.summary.slice(0, 60)}…</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
