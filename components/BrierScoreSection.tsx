"use client";

import { Target, TrendingUp, AlertTriangle } from "lucide-react";

const BENCH_ROW = [
  { name: "WhiteMagic Labs (stated)", bs: "0.0958", bi: "69.0%", bss: "-0.302", highlight: true },
  { name: "WhiteMagic Labs (behavioral)", bs: "0.0507", bi: "77.5%", bss: "0.797", highlight: true },
  { name: "ForecastBench superforecasters", bs: "0.086", bi: "70.6%", bss: "—", highlight: false },
  { name: "Grok 4.20 (Preview)", bs: "0.102", bi: "68.0%", bss: "—", highlight: false },
  { name: "GPT-5 / o3 ensemble", bs: "~0.110", bi: "~66.8%", bss: "—", highlight: false },
  { name: "Uninformed baseline (p=0.5)", bs: "0.250", bi: "50.0%", bss: "0.0", highlight: false },
];

export function BrierScoreSection() {
  return (
    <section className="border-y border-border-light bg-surface py-16">
      <div className="container-site mx-auto max-w-4xl space-y-10">

        <div>
          <p className="mb-2 font-mono text-xs uppercase tracking-widest text-lavender">
            Brier scoring · updated July 17, 2026
          </p>
          <h2 className="font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
            Calibration against the gold standard.
          </h2>
          <p className="mt-3 max-w-2xl text-muted">
            The Brier score measures how close probability forecasts are to reality.
            The Brier Index rescales it to 0–100% for intuitive reading.
            WhiteMagic is scored against the same benchmark used by the Forecasting Research Institute
            to rank superforecasters and LLMs.
          </p>
        </div>

        {/* Score cards */}
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-border bg-surface-alt p-5">
            <Target className="mb-3 h-5 w-5 text-lavender" />
            <p className="font-head text-3xl font-bold text-ink">0.0958</p>
            <p className="mt-0.5 text-sm font-medium text-fg">Brier score</p>
            <p className="mt-1 text-xs text-dim">Lower is better. 0.25 = random guessing.</p>
          </div>
          <div className="rounded-2xl border border-border bg-surface-alt p-5">
            <TrendingUp className="mb-3 h-5 w-5 text-lavender" />
            <p className="font-head text-3xl font-bold text-ink">69.0%</p>
            <p className="mt-0.5 text-sm font-medium text-fg">Brier Index (stated)</p>
            <p className="mt-1 text-xs text-dim">Behavioral recalibration ≈ 77.5%. Superforecasters ≈ 70.6%.</p>
          </div>
          <div className="rounded-2xl border border-border bg-surface-alt p-5">
            <AlertTriangle className="mb-3 h-5 w-5 text-amber-400" />
            <p className="font-head text-3xl font-bold text-ink">−0.302</p>
            <p className="mt-0.5 text-sm font-medium text-fg">Calibration gap</p>
            <p className="mt-1 text-xs text-dim">Negative = underconfident. Predicted lower than reality.</p>
          </div>
        </div>

        {/* Benchmark table */}
        <div>
          <h3 className="mb-4 font-head text-lg font-semibold text-ink">
            Benchmark comparison — stated & behavioral scores (May 2026)
          </h3>
          <div className="overflow-hidden rounded-2xl border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface">
                  <th className="px-5 py-3 text-left font-mono text-xs uppercase tracking-wider text-dim">Entity</th>
                  <th className="px-5 py-3 text-center font-mono text-xs uppercase tracking-wider text-dim">Brier score</th>
                  <th className="px-5 py-3 text-center font-mono text-xs uppercase tracking-wider text-dim">Brier Index</th>
                  <th className="px-5 py-3 text-center font-mono text-xs uppercase tracking-wider text-dim">Skill score</th>
                </tr>
              </thead>
              <tbody>
                {BENCH_ROW.map((f, i) => (
                  <tr
                    key={f.name}
                    className={
                      f.highlight
                        ? "border-b border-lavender/20 bg-lavender/5"
                        : i % 2 === 0
                        ? "border-b border-border/50 bg-surface/50"
                        : "border-b border-border/50"
                    }
                  >
                    <td className={`px-5 py-3 ${f.highlight ? "font-semibold text-ink" : "text-muted"}`}>
                      {f.name}
                    </td>
                    <td className={`px-5 py-3 text-center font-mono text-xs ${f.highlight ? "text-lavender" : "text-muted"}`}>
                      {f.bs}
                    </td>
                    <td className={`px-5 py-3 text-center font-mono text-xs ${f.highlight ? "text-lavender" : "text-muted"}`}>
                      {f.bi}
                    </td>
                    <td className={`px-5 py-3 text-center font-mono text-xs ${f.highlight ? "text-lavender" : "text-muted"}`}>
                      {f.bss}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-dim">
            Source: Forecasting Research Institute, ForecastBench leaderboard (March 2026).
            Brier Index = (1 − √BS) × 100%. WhiteMagic score is computed from the same SQLite prediction ledger
            used for the prescience audit — not an estimate.
          </p>
        </div>

        {/* Honest caveat */}
        <div className="rounded-2xl border border-dashed border-border bg-surface-alt p-5 text-sm text-muted">
          <p className="mb-1 font-mono text-xs uppercase tracking-widest text-lavender">Calibration caveat</p>
          <p>
            All 23 closed predictions resolved <em>positive</em> (outcome = 1). This means the Brier decomposition
            cannot compute meaningful resolution or uncertainty — there is no variance in outcomes to measure against.
            The Brier score is therefore driven entirely by reliability: how close your confidence levels were to 1.0.
            A negative calibration gap (−0.283) indicates you were systematically <strong>underconfident</strong> —
            predicting 0.55–0.80 on events that all happened. With falsified claims, the calibration curve would be
            more informative. The 69.0% Brier Index is legitimate, but the decomposition is structurally incomplete
            until the track record includes misses.
          </p>
        </div>
      </div>
    </section>
  );
}
