"use client";

import { useState } from "react";

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

export function WanderTrail() {
  const [seed, setSeed] = useState("");
  const [steps, setSteps] = useState(8);
  const [diversity, setDiversity] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<WanderResult | null>(null);
  const [error, setError] = useState("");

  const doWander = async () => {
    if (!seed.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(
        `/api/aria/wander?seed=${encodeURIComponent(seed)}&steps=${steps}&diversity=${diversity}`,
      );
      const data = (await res.json()) as WanderResult;
      if (data.error) setError(data.error);
      setResult(data);
    } catch {
      setError("Wander request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-2xl border border-border bg-surface p-6">
      <h3 className="font-head text-lg font-semibold text-ink">
        Wander Trail
      </h3>
      <p className="mt-1 text-sm text-muted">
        Start with an idea and follow the links through the knowledge sphere.
        Diversity mode prefers new sources at each step.
      </p>

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
          diverse
        </label>
        <button
          onClick={doWander}
          disabled={loading || !seed.trim()}
          className="rounded-lg bg-lavender px-4 py-2 font-mono text-sm text-white transition hover:bg-lavender/80 disabled:opacity-50"
        >
          {loading ? "Wandering..." : "Wander"}
        </button>
      </div>

      {error && (
        <p className="mt-3 font-mono text-sm text-red-500">{error}</p>
      )}

      {result && result.path && (
        <div className="mt-6">
          <p className="font-mono text-xs text-dim">{result.summary}</p>
          <div className="mt-4 space-y-3">
            {result.path.map((p) => (
              <div
                key={p.step}
                className="rounded-lg border border-border bg-surface-alt/50 p-3 transition hover:border-lavender/30"
              >
                <div className="flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-lavender/20 font-mono text-[10px] text-lavender">
                    {p.step}
                  </span>
                  <span className="font-mono text-xs font-semibold text-ink">
                    {p.label}
                  </span>
                  <span className="font-mono text-[10px] text-dim">
                    {p.source}
                  </span>
                  {p.link_strength < 1 && (
                    <span className="ml-auto font-mono text-[10px] text-muted">
                      ×{p.link_strength.toFixed(2)}
                    </span>
                  )}
                </div>
                <p className="mt-1 font-mono text-[11px] text-muted">
                  {p.narration}
                </p>
                <p className="mt-1 font-mono text-[11px] leading-relaxed text-dim">
                  {p.preview.slice(0, 160)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
