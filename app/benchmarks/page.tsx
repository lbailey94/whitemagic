import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { TabSwitcher } from "@/components/TabSwitcher";
import { WM_FACTS, WM_FACT_TEXT } from "@/lib/facts";

export const metadata = {
  title: "Benchmarks & Comparison — WhiteMagic Labs",
  description:
    "Measured performance numbers and honest feature-by-feature comparison of WhiteMagic vs Mem0, Letta, and standard RAG systems. Every metric measured on local consumer hardware.",
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
  { metric: "Cross-domain routing accuracy", value: "100%", comparison: "Trading to Governance to Analysis, no LLM reasoning pass", hardware: "Dell Inspiron 3582", command: "python scripts/system_capability_test.py --suite routing" },
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
  { metric: "Rust AVX2 GEMV (256x256)", value: "563us", comparison: "12.5x speedup over Python scalar (5.6ms)", hardware: "Consumer laptop, AVX2", command: "cargo bench -p wm-neuro --bench ternary" },
  { metric: "Ternary kernel (12-layer model)", value: "67ms/token", comparison: "vs 873ms/token Python - real-time vs noticeable lag", hardware: "Consumer laptop, AVX2" },
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
  { metric: "HLL cardinality tracking", value: "508KB / 100K memories", comparison: "1.2% error rate, O(1) space - runs forever without degradation", hardware: "N/A (mathematical)" },
  { metric: "Count-Min Sketch", value: "Sub-1KB", comparison: "Frequency estimation with bounded error", hardware: "N/A (mathematical)" },
  { metric: "Thompson sampling bandit", value: "Beta posterior updates", comparison: "Contextual tool selection - agent gets better with use without retraining", hardware: "N/A (algorithmic)" },
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

function BenchmarksContent() {
  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-12 rounded-2xl border border-border bg-surface-alt p-6">
        <h2 className="mb-3 font-head text-lg font-semibold text-ink">Methodology</h2>
        <ul className="space-y-2 text-sm text-muted">
          <li><strong className="text-fg">Hardware:</strong> Dell Inspiron 3582 (Intel Celeron N4000, 4GB RAM, eMMC storage) and a consumer laptop. No server hardware. No GPU.</li>
          <li><strong className="text-fg">Software:</strong> Python 3.12, Rust 1.78+, SQLite 3.45+, Zorin OS / Linux. All benchmarks run with default settings.</li>
          <li><strong className="text-fg">Reproducibility:</strong> Every benchmark has a reproducible command. Clone the repo, activate the venv, run the command.</li>
          <li><strong className="text-fg">Honesty:</strong> We publish negative results too. The STRATA full-repo scan takes 21 seconds. The Fragment cold-start is 349ms.</li>
        </ul>
      </div>

      <BenchTable rows={COGNITIVE} title="Cognitive Performance" />
      <BenchTable rows={VECTOR} title="Vector & Text Search" />
      <BenchTable rows={SIMD} title="SIMD / Rust Acceleration" />
      <BenchTable rows={INFRA} title="Infrastructure & Dispatch" />
      <BenchTable rows={PROBABILISTIC} title="Probabilistic Data Structures" />
      <BenchTable rows={STRESS} title="Scale & Stress Tests" />

      <div className="mt-12 rounded-2xl border border-dashed border-border bg-surface-alt p-6">
        <h2 className="mb-3 font-head text-lg font-semibold text-ink">Known performance gaps (honest)</h2>
        <ul className="space-y-3 text-sm text-muted">
          <li><strong className="text-fg">STRATA full-repo scan: 21.2s.</strong> Scanning ~720 Python files with 80+ checkers. The survey mode at 3s is the practical quick check.</li>
          <li><strong className="text-fg">Fragment cold-start: 349ms.</strong> First query builds the BM25 index from disk. Warm-cache benchmark needed.</li>
          <li><strong className="text-fg">No AVX-512 support.</strong> Only AVX2 is used. AVX-512 with cache tiling could achieve 92% of theoretical peak.</li>
          <li><strong className="text-fg">No speculative decoding.</strong> The inference router cascades by escalation, not parallel draft+verify.</li>
          <li><strong className="text-fg">Streaming inference stubs.</strong> The Rust streaming inference layer has compute_layer stubs that return input unchanged.</li>
        </ul>
      </div>
    </div>
  );
}

interface CompareRow {
  capability: string;
  whitemagic: string;
  mem0: string;
  letta: string;
  rag: string;
}

const MEMORY_CMP: CompareRow[] = [
  { capability: "Memory architecture", whitemagic: "5D holographic coordinates (temporal, semantic, emotional, relational, importance)", mem0: "Flat vector store with metadata tags", letta: "Agent state + memory blocks, harness-managed", rag: "Linear vector embeddings, no relationships" },
  { capability: "Persistence horizon", whitemagic: "Global - memories persist forever, rotate through galactic lifecycle zones", mem0: "Session or conversation-scoped", letta: "Persistent within a harness deployment", rag: "N/A - stateless retrieval" },
  { capability: "Search modalities", whitemagic: "HNSW vector + FTS5 full-text + graph walking + HRR projection + 5D coordinate lookup", mem0: "Vector similarity only", letta: "Vector + keyword within harness", rag: "Vector similarity only" },
  { capability: "Memory relationships", whitemagic: "Cross-galaxy associations, knowledge graph, 2.2M associations in v15.8 era", mem0: "No relationship tracking", letta: "Limited - within agent context window", rag: "No relationships" },
  { capability: "Decay & consolidation", whitemagic: "8-phase dream cycle: triage, consolidation, serendipity, governance, narrative, kaizen, oracle, decay", mem0: "No decay or consolidation", letta: "No dream cycle", rag: "No decay" },
  { capability: "Emotional encoding", whitemagic: "Emotional valence dimension in 5D coords, 20+ emotional gardens (joy, grief, courage, love)", mem0: "No emotional encoding", letta: "No emotional encoding", rag: "No emotional encoding" },
];

const GOVERNANCE_CMP: CompareRow[] = [
  { capability: "Ethical governance", whitemagic: "Dharma rules engine - YAML-driven, 4 profiles, hot-reloadable, 8-stage dispatch pipeline", mem0: "Prompt-based guardrails", letta: "Harness-level tool permissions", rag: "None" },
  { capability: "Audit trail", whitemagic: "Karma ledger - SHA-256 Merkle-chained, XRPL-anchored, append-only", mem0: "Basic logging", letta: "Harness logs", rag: "None" },
  { capability: "Input sanitization", whitemagic: "Shell injection detection, content scanning, internal field stripping", mem0: "No", letta: "No", rag: "No" },
  { capability: "Rate limiting", whitemagic: "Rust EventRing - 452K ops/s pre-check, zero allocation hot path", mem0: "No", letta: "Harness-level", rag: "No" },
  { capability: "Circuit breaker", whitemagic: "Yes - automatic failure detection and recovery", mem0: "No", letta: "No", rag: "No" },
  { capability: "Sandboxing", whitemagic: "5-tier sovereign sandbox: thread, namespace, container, microVM, WASM", mem0: "No", letta: "No", rag: "No" },
];

const PERFORMANCE_CMP: CompareRow[] = [
  { capability: "Skill retrieval", whitemagic: "<1ms (Muscle Memory)", mem0: "N/A", letta: "200ms-2s (LLM planning)", rag: "50-500ms (vector search)" },
  { capability: "Vector search", whitemagic: "0.26ms (HNSW, 16K embeddings)", mem0: "50-200ms (cloud API)", letta: "10-50ms (local)", rag: "50-500ms" },
  { capability: "Local-first", whitemagic: "Yes - by default. No cloud required.", mem0: "No - cloud API", letta: "Partial - harness-dependent", rag: "No - cloud-dependent" },
  { capability: "Offline operation", whitemagic: "Full operation including inference (ternary kernels, Ollama integration)", mem0: "No", letta: "Partial", rag: "No" },
  { capability: "Polyglot acceleration", whitemagic: "7 languages: Rust, Go, Zig, Haskell, Elixir, Julia, Koka", mem0: "Python only", letta: "Python only", rag: "Python only" },
  { capability: "Probabilistic tracking", whitemagic: "HLL + Count-Min Sketch - O(1) space, runs forever", mem0: "No", letta: "No", rag: "No" },
];

const COGNITIVE_CMP_TAB: CompareRow[] = [
  { capability: "Consciousness primitives", whitemagic: "Citta stream, coherence metrics (8 dimensions), Smarana practice, presence quality", mem0: "No", letta: "Agent identity within harness", rag: "No" },
  { capability: "Self-calibrating forecasts", whitemagic: "Brier-scored predictions, 21 validated prescience claims, 523 points", mem0: "No", letta: "No", rag: "No" },
  { capability: "Tool selection learning", whitemagic: "Thompson sampling bandit - Beta posteriors converge with use, no retraining", mem0: "No", letta: "No", rag: "No" },
  { capability: "Metacognitive awareness", whitemagic: "Cardinality-velocity surprise gate - modulates learning rate by novelty", mem0: "No", letta: "No", rag: "No" },
  { capability: "Session continuity", whitemagic: "Session recorder with progressive recall, selective replay, FTS5 search", mem0: "No", letta: "Agent state persistence", rag: "No" },
  { capability: "Dream cycle", whitemagic: "8-phase: triage, consolidation, serendipity, governance, narrative, kaizen, oracle, decay", mem0: "No", letta: "No", rag: "No" },
];

const HONEST_WINS: { competitor: string; advantage: string }[] = [
  { competitor: "Mem0", advantage: "Hosted cloud API - zero setup, zero infrastructure. If you need memory in 5 minutes and don't care about governance, privacy, or local-first, Mem0 is faster to integrate." },
  { competitor: "Mem0", advantage: "Established market presence and documentation. WhiteMagic's docs are thorough but technical; Mem0 has a polished developer experience for quick starts." },
  { competitor: "Letta", advantage: "Deep harness integration. Letta manages the agent runtime itself - tool calling, context windows, model routing. WhiteMagic is a substrate that any agent plugs into." },
  { competitor: "Letta", advantage: "Memory models (June 2026) - specialized models for creating durable context that transfers across LLMs. WhiteMagic doesn't yet have model-trained memory compression." },
  { competitor: "Standard RAG", advantage: "Simplicity. If you just need 'search a PDF and ask questions,' RAG is simpler and well-understood. WhiteMagic's 614 tools and 8-stage pipeline are overkill for basic retrieval." },
  { competitor: "Standard RAG", advantage: "Ecosystem. LangChain, LlamaIndex, and the broader RAG ecosystem have thousands of integrations. WhiteMagic has 614 tools but a smaller integration surface." },
];

function CompareTable({ rows, title }: { rows: CompareRow[]; title: string }) {
  return (
    <div className="mb-12">
      <h2 className="mb-4 font-head text-xl font-semibold text-ink">{title}</h2>
      <div className="overflow-x-auto rounded-2xl border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface">
              <th className="px-4 py-3 text-left font-mono text-xs uppercase tracking-wider text-dim">Capability</th>
              <th className="px-4 py-3 text-left font-mono text-xs uppercase tracking-wider text-lavender">WhiteMagic</th>
              <th className="px-4 py-3 text-left font-mono text-xs uppercase tracking-wider text-dim">Mem0</th>
              <th className="px-4 py-3 text-left font-mono text-xs uppercase tracking-wider text-dim">Letta</th>
              <th className="px-4 py-3 text-left font-mono text-xs uppercase tracking-wider text-dim">Standard RAG</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.capability} className={i % 2 === 0 ? "border-b border-border/50 bg-surface/30" : "border-b border-border/50"}>
                <td className="px-4 py-3 font-medium text-fg">{r.capability}</td>
                <td className="px-4 py-3 font-semibold text-lavender">{r.whitemagic}</td>
                <td className="px-4 py-3 text-muted">{r.mem0}</td>
                <td className="px-4 py-3 text-muted">{r.letta}</td>
                <td className="px-4 py-3 text-muted">{r.rag}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CompareContent() {
  return (
    <div className="mx-auto max-w-5xl">
      <p className="mb-8 max-w-prose text-lg leading-relaxed text-muted">
        WhiteMagic is not the right tool for every job. Here is an honest comparison
        against Mem0, Letta, and standard RAG - including where competitors have genuine advantages.
      </p>

      <CompareTable rows={MEMORY_CMP} title="Memory Architecture" />
      <CompareTable rows={GOVERNANCE_CMP} title="Governance & Safety" />
      <CompareTable rows={PERFORMANCE_CMP} title="Performance & Deployment" />
      <CompareTable rows={COGNITIVE_CMP_TAB} title="Cognitive Capabilities" />

      <div className="mt-12 rounded-2xl border border-dashed border-border bg-surface-alt p-6">
        <h2 className="mb-4 font-head text-lg font-semibold text-ink">
          Where competitors genuinely win
        </h2>
        <p className="mb-6 text-sm text-muted">
          We do not pretend WhiteMagic is perfect for every use case. Here are the areas
          where competitors have real, honest advantages.
        </p>
        <div className="grid gap-4 md:grid-cols-2">
          {HONEST_WINS.map((item, i) => (
            <article key={i} className="rounded-xl border border-border bg-surface p-4">
              <p className="mb-2 font-mono text-xs uppercase tracking-wider text-dim">{item.competitor}</p>
              <p className="text-sm leading-relaxed text-muted">{item.advantage}</p>
            </article>
          ))}
        </div>
      </div>

      <div className="mt-12 rounded-2xl border border-border bg-surface p-8">
        <h2 className="mb-4 font-head text-xl font-semibold text-ink">The bottom line</h2>
        <p className="mb-4 text-sm leading-relaxed text-muted">
          <strong className="text-fg">Choose WhiteMagic if</strong> you need local-first operation,
          ethical governance as architecture (not prompts), memory that persists and consolidates,
          consciousness primitives for continuous agents, or you are building for air-gapped / regulated environments.
        </p>
        <p className="mb-4 text-sm leading-relaxed text-muted">
          <strong className="text-fg">Choose Mem0 if</strong> you need a hosted memory API in 5 minutes
          and do not need governance, privacy guarantees, or local-first operation.
        </p>
        <p className="mb-4 text-sm leading-relaxed text-muted">
          <strong className="text-fg">Choose Letta if</strong> you want a complete agent harness that
          manages tool calling, context windows, and model routing - and you are okay being harness-locked.
        </p>
        <p className="text-sm leading-relaxed text-muted">
          <strong className="text-fg">Choose standard RAG if</strong> you just need to search documents
          and ask questions. It is simpler, well-understood, and has a massive ecosystem.
        </p>
      </div>
    </div>
  );
}

export default function BenchmarksPage() {
  return (
    <>
      <PageHeader
        eyebrow="Evidence"
        title="Measured performance. Honest comparison."
        lede={`Every number was measured on local consumer hardware - mostly a Dell Inspiron 3582 running Zorin OS. No cloud instances. No GPU acceleration. No cherry-picking. Last verified ${WM_FACTS.benchmarkDate}.`}
      />

      <section className="container-site py-16">
        <TabSwitcher
          tabs={[
            { id: "benchmarks", label: "Benchmarks", content: <BenchmarksContent /> },
            { id: "compare", label: "Comparison", content: <CompareContent /> },
          ]}
        />

        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/getting-started" className="btn-ghost">Getting started &rarr;</Link>
          <Link href="/capabilities" className="btn-ghost">View capabilities &rarr;</Link>
        </div>
      </section>
    </>
  );
}
