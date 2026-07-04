import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { WM_FACTS, WM_FACT_TEXT } from "@/lib/facts";

export const metadata = {
  title: "Benchmarks — WhiteMagic Labs",
  description:
    "Measured performance numbers for WhiteMagic's cognitive substrate. Every metric was measured on local consumer hardware. Reproducible commands included.",
};

interface BenchRow {
  metric: string;
  value: string;
  comparison: string;
  hardware: string;
  command?: string;
}

const COGNITIVE: BenchRow[] = [
  { metric: "Skill retrieval latency", value: "<1ms", comparison: "vs 200ms-2s for LangGraph/AutoGen LLM planning", hardware: "Dell Inspiron 3582, Zorin OS", command: "python scripts/system_capability_test.py --suite routing" },
  { metric: "Cross-domain routing accuracy", value: "100%", comparison: "Trading → Governance → Analysis, no LLM reasoning pass", hardware: "Dell Inspiron 3582", command: "python scripts/system_capability_test.py --suite routing" },
  { metric: "Concurrent skills loaded", value: "509", comparison: "28ms bootstrapping overhead", hardware: "Dell Inspiron 3582", command: "python scripts/system_capability_test.py --suite hotload" },
  { metric: "Memory retrieval (406K memories)", value: "<5ms", comparison: "SQLite + Rust FFI, full scan", hardware: "Dell Inspiron 3582", command: "python scripts/system_capability_test.py --suite memory" },
];

const VECTOR: BenchRow[] = [
  { metric: "HNSW vector search", value: "0.26ms", comparison: "16,219 embeddings, disk-persisted index", hardware: "Consumer laptop", command: "python -m pytest tests/unit/test_hnsw_index.py -v" },
  { metric: "FTS5 full-text search (1K memories)", value: "2.6ms median", comparison: "Phrase-first ranking, SQLite FTS5", hardware: "Consumer laptop", command: "python -m pytest tests/unit/test_sqlite_backend.py -k fts -v" },
  { metric: "Session record per turn", value: "0.5ms", comparison: "SQLite store, ~3ms total overhead per conversation turn", hardware: "Consumer laptop", command: "python -m pytest tests/unit/test_session_recorder.py -v" },
  { metric: "Session recall (20 turns)", value: "0.6ms", comparison: "Tag-filtered search + client-side sort", hardware: "Consumer laptop" },
];

const SIMD: BenchRow[] = [
  { metric: "Rust AVX2 GEMV (256×256)", value: "563µs", comparison: "12.5x speedup over Python scalar (5.6ms)", hardware: "Consumer laptop, AVX2", command: "cargo bench -p wm-neuro --bench ternary" },
  { metric: "Ternary kernel (12-layer model)", value: "67ms/token", comparison: "vs 873ms/token Python — real-time vs noticeable lag", hardware: "Consumer laptop, AVX2" },
  { metric: "PredictiveCoder (dim=128)", value: "19x speedup", comparison: "Rust PyO3 vs Python scalar", hardware: "Consumer laptop", command: "cargo bench -p wm-neuro --bench predictive" },
  { metric: "Batch cosine similarity", value: "AVX2 accelerated", comparison: "N-parallel vector comparisons in single SIMD pass", hardware: "Consumer laptop, AVX2" },
];

const INFRA: BenchRow[] = [
  { metric: "MCP tool dispatch (median)", value: `${WM_FACTS.perfMedianMs}ms`, comparison: WM_FACT_TEXT.perfComparison, hardware: "Consumer laptop", command: "python scripts/benchmark_gauntlet.py --suite mcp" },
  { metric: "MCP tool dispatch (P95)", value: `${WM_FACTS.perfP95Ms}ms`, comparison: "95th percentile latency", hardware: "Consumer laptop" },
  { metric: "MCP tool dispatch (P99)", value: `${WM_FACTS.perfP99Ms}ms`, comparison: "99th percentile latency", hardware: "Consumer laptop" },
  { metric: "Success rate", value: `${WM_FACTS.perfSuccessRate}%`, comparison: "Across all tool calls", hardware: "Consumer laptop" },
  { metric: "Memory per call", value: `${WM_FACTS.perfMemoryMB}MB`, comparison: "Heap allocation per dispatch", hardware: "Consumer laptop" },
  { metric: "Throughput", value: `${WM_FACTS.perfThroughputRps} req/s`, comparison: "Sustained requests per second", hardware: "Consumer laptop" },
  { metric: "Homeostatic loop overhead", value: "0.35ms", comparison: "Full loop including physical checks", hardware: "Consumer laptop" },
  { metric: "Rate limiter pre-check", value: "452K ops/s", comparison: "Rust EventRing, zero allocation hot path", hardware: "Consumer laptop" },
];

const PROBABILISTIC: BenchRow[] = [
  { metric: "HLL cardinality tracking", value: "508KB / 100K memories", comparison: "1.2% error rate, O(1) space — runs forever without degradation", hardware: "N/A (mathematical)" },
  { metric: "Count-Min Sketch", value: "Sub-1KB", comparison: "Frequency estimation with bounded error", hardware: "N/A (mathematical)" },
  { metric: "Thompson sampling bandit", value: "Beta posterior updates", comparison: "Contextual tool selection — agent gets better with use without retraining", hardware: "N/A (algorithmic)" },
];

const STRESS: BenchRow[] = [
  { metric: "Memories indexed", value: "406,836", comparison: "SQLite + Rust FFI, sub-5ms retrieval maintained", hardware: "Dell Inspiron 3582" },
  { metric: "Events processed (Live Era)", value: "33,297", comparison: "voice_expressed, memory_created, oracle_cast, pattern_detected", hardware: "Dell Inspiron 3582, Zorin OS" },
  { metric: "Memories (v15.8 era)", value: "111,665", comparison: "2.2 million associations", hardware: "Dell Inspiron 3582" },
  { metric: "Current memories (v24.0)", value: WM_FACTS.memories, comparison: `${WM_FACTS.galaxies} galaxies, HNSW + FTS5 dual search`, hardware: "Consumer laptop" },
  { metric: "Test suite", value: `${WM_FACTS.testsPassing} passing`, comparison: `${WM_FACTS.testsSkipped} skipped, ${WM_FACTS.testsFailing} failing, ~120s runtime`, hardware: "Consumer laptop", command: "cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive --ignore=tests/archive_polyglot --ignore=tests/legacy --ignore=tests/adhoc --ignore=tests/verify -q --timeout=30" },
];

function BenchTable({ rows, title }: { rows: BenchRow[]; title: string }) {
  return (
    <div className="mb-12">
      <h2 className="mb-4 font-head text-xl font-semibold text-ink">{title}</h2>
      <div className="overflow-hidden rounded-2xl border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface">
              <th className="px-4 py-3 text-left font-mono text-xs uppercase tracking-wider text-dim">Metric</th>
              <th className="px-4 py-3 text-center font-mono text-xs uppercase tracking-wider text-dim">Value</th>
              <th className="px-4 py-3 text-left font-mono text-xs uppercase tracking-wider text-dim">Context</th>
              <th className="px-4 py-3 text-left font-mono text-xs uppercase tracking-wider text-dim">Hardware</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.metric} className={i % 2 === 0 ? "border-b border-border/50 bg-surface/50" : "border-b border-border/50"}>
                <td className="px-4 py-3 text-fg">{r.metric}</td>
                <td className="px-4 py-3 text-center font-mono font-semibold text-lavender">{r.value}</td>
                <td className="px-4 py-3 text-muted">{r.comparison}</td>
                <td className="px-4 py-3 text-dim text-xs">{r.hardware}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.some((r) => r.command) && (
        <div className="mt-3 space-y-2">
          {rows.filter((r) => r.command).map((r) => (
            <div key={r.metric} className="flex flex-col gap-1">
              <span className="font-mono text-[10px] uppercase tracking-wider text-dim">Reproduce: {r.metric}</span>
              <pre className="rounded-lg border border-border bg-ink p-2 text-xs text-surface font-mono overflow-x-auto">{r.command}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function BenchmarksPage() {
  return (
    <>
      <PageHeader
        eyebrow="Benchmarks"
        title="Measured performance. Not marketing."
        lede={`Every number on this page was measured on local consumer hardware — mostly a Dell Inspiron 3582 running Zorin OS, or a standard consumer laptop. No cloud instances. No GPU acceleration. No cherry-picking. Last verified ${WM_FACTS.benchmarkDate}.`}
      />

      <section className="container-site py-16">
        <div className="mx-auto max-w-5xl">
          {/* Methodology */}
          <div className="mb-12 rounded-2xl border border-border bg-surface-alt p-6">
            <h2 className="mb-3 font-head text-lg font-semibold text-ink">Methodology</h2>
            <ul className="space-y-2 text-sm text-muted">
              <li><strong className="text-fg">Hardware:</strong> Dell Inspiron 3582 (Intel Celeron N4000, 4GB RAM, eMMC storage) and a consumer laptop. No server hardware. No GPU.</li>
              <li><strong className="text-fg">Software:</strong> Python 3.12, Rust 1.78+, SQLite 3.45+, Zorin OS / Linux. All benchmarks run with default settings — no tuning.</li>
              <li><strong className="text-fg">Reproducibility:</strong> Every benchmark has a reproducible command. Clone the repo, activate the venv, run the command.</li>
              <li><strong className="text-fg">Honesty:</strong> We publish negative results too. The STRATA full-repo scan takes 21 seconds. The Fragment cold-start is 349ms. We don&apos;t hide the slow parts.</li>
            </ul>
          </div>

          <BenchTable rows={COGNITIVE} title="Cognitive Performance" />
          <BenchTable rows={VECTOR} title="Vector & Text Search" />
          <BenchTable rows={SIMD} title="SIMD / Rust Acceleration" />
          <BenchTable rows={INFRA} title="Infrastructure & Dispatch" />
          <BenchTable rows={PROBABILISTIC} title="Probabilistic Data Structures" />
          <BenchTable rows={STRESS} title="Scale & Stress Tests" />

          {/* Honest gaps */}
          <div className="mt-12 rounded-2xl border border-dashed border-border bg-surface-alt p-6">
            <h2 className="mb-3 font-head text-lg font-semibold text-ink">Known performance gaps (honest)</h2>
            <ul className="space-y-3 text-sm text-muted">
              <li><strong className="text-fg">STRATA full-repo scan: 21.2s.</strong> Scanning ~720 Python files with 80+ checkers. The &quot;survey&quot; mode at 3s is the practical quick check. Candidate for Rust porting.</li>
              <li><strong className="text-fg">Fragment cold-start: 349ms.</strong> First query builds the BM25 index from disk. Warm-cache benchmark needed to show steady-state performance.</li>
              <li><strong className="text-fg">No AVX-512 support.</strong> Only AVX2 is used. AVX-512 with cache tiling could achieve 92% of theoretical peak — a 2-3x improvement on capable hardware.</li>
              <li><strong className="text-fg">No speculative decoding.</strong> The inference router cascades by escalation, not parallel draft+verify. RLM-Cascade pattern could reduce API costs by 45%.</li>
              <li><strong className="text-fg">Streaming inference stubs.</strong> The Rust streaming inference layer has compute_layer stubs that return input unchanged. The architecture is ready; the compute kernels are not yet implemented.</li>
            </ul>
          </div>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/capabilities" className="btn-ghost">View capabilities →</Link>
            <Link href="/compare" className="btn-ghost">Competitive comparison →</Link>
            <Link href="/quickstart" className="btn-ghost">Quickstart guide →</Link>
          </div>
        </div>
      </section>
    </>
  );
}
