import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { BootSequence } from "@/components/BootSequence";
import { ToolGraphLazy } from "@/components/ToolGraphLazy";
import { DispatchPipeline } from "@/components/DispatchPipeline";
import { WM_FACTS, WM_FACT_TEXT } from "@/lib/facts";

interface Benchmark {
  metric: string;
  value: string;
  comparison: string;
  source: string;
}

const BENCHMARKS: Benchmark[] = [
  { metric: "Skill retrieval latency", value: "<1ms", comparison: "vs 200ms-2s for LangGraph/AutoGen LLM planning", source: "Stress test, Apr 2026" },
  { metric: "HNSW vector search", value: "0.26ms", comparison: "16,219 embeddings, disk-persisted index", source: "v23.3.1 benchmark" },
  { metric: "Rust AVX2 GEMV (256x256)", value: "563 microseconds", comparison: "12.5x speedup over Python scalar (5.6ms)", source: "Ternary kernel benchmark" },
  { metric: "Concurrent skills loaded", value: "509", comparison: "28ms bootstrapping overhead", source: "Stress test, Apr 2026" },
  { metric: "Memory retrieval (406K memories)", value: "<5ms", comparison: "SQLite + Rust FFI, local hardware", source: "Stress test, Apr 2026" },
  { metric: "Cross-domain routing accuracy", value: "100%", comparison: "No LLM reasoning pass required", source: "Stress test, Apr 2026" },
  { metric: "Probabilistic tracking", value: "508KB / 100K memories", comparison: "1.2% error rate, O(1) space — runs forever", source: "HLL + Count-Min Sketch" },
  { metric: "Homeostatic loop overhead", value: "0.35ms", comparison: "Full loop including physical checks", source: "Benchmark suite" },
  { metric: "Session record per turn", value: "0.5ms", comparison: "SQLite store, ~3ms total overhead per conversation turn", source: "v23.3.3 benchmark" },
  { metric: "FTS5 search (1K memories)", value: "2.6ms median", comparison: "Full-text search with phrase-first ranking", source: "v23.3.3 benchmark" },
];

interface UseCase {
  domain: string;
  fit: string;
  why: string;
}

const USE_CASES: UseCase[] = [
  { domain: "AI safety research", fit: "Best fit", why: "Governance-first architecture, ethical constraints built into the dispatch pipeline, karma ledger for accountability. The system can serve as both a subject of study and a research tool." },
  { domain: "Regulatory technology (RegTech)", fit: "Best fit", why: "Dharma engine + audit trail + prescience calibration. The system doesn't just check rules — it reasons about them and tracks whether its regulatory predictions come true." },
  { domain: "Edge AI / IoT", fit: "Best fit", why: "Ternary kernels for constrained inference, O(1) memory tracking, graceful degradation, dream cycle for idle-time consolidation. Designed for resource-limited environments." },
  { domain: "Knowledge management", fit: "Best fit", why: "Memory with novelty filtering, knowledge graph, association mining, agent loop for autonomous research. The system doesn't just store documents — it understands which ones contain novel information." },
  { domain: "Forecasting & prediction markets", fit: "Best fit", why: "MC calibration engine, Brier scoring, prescience tracking, Beta posterior updates. The system doesn't just make predictions — it scores its own accuracy and improves over time." },
  { domain: "Healthcare data analysis", fit: "Best fit", why: "Local-first (HIPAA), ethical governance, surprise detection for anomalies, probabilistic tracking for patient cohorts. No data leaves the machine." },
  { domain: "Cybersecurity", fit: "Adjacent", why: "Surprise gate (anomaly detection), knowledge graph (attack patterns), local inference. Architecture is ideal but no specific security tooling yet." },
  { domain: "Legal tech", fit: "Adjacent", why: "Dharma governance, audit trail, memory with 5D coordinates. Needs legal-specific knowledge graph seeds." },
  { domain: "Education technology", fit: "Adjacent", why: "Agent loop (tutoring), bandit (learns what works for each student), surprise gate (tracks what's novel for each learner)." },
];

const NOT_FIT = [
  "High-throughput real-time trading — the dispatch pipeline has 8 stages of governance overhead (~42 microseconds per decision). HFT needs sub-microsecond.",
  "Massive-scale web services — designed for single-machine or small-cluster deployment, not horizontally-scaled cloud infrastructure.",
  "Image/video generation — ternary kernels accelerate inference, not diffusion. The architecture is text-and-reasoning focused.",
  "Simple CRUD applications — the 614-tool dispatch pipeline is overkill for basic data management.",
];

export const metadata = {
  title: "Capabilities — WhiteMagic Labs",
  description:
    `The engineering behind the vision: 5D holographic memory, galactic lifecycle, dream cycle consolidation, Dharma governance, Karma audit, ${WM_FACT_TEXT.mcpSurface}, polyglot accelerators, and more.`,
};

interface Capability {
  category: string;
  title: string;
  body: string;
  detail: string;
}

const CAPABILITIES: Capability[] = [
  {
    category: "Memory",
    title: "5D Holographic Coordinates",
    body: "Every memory placed in a mathematically precise 5D space: logic and emotion, micro and macro, time, gravity, vitality.",
    detail:
      "No flat key-value store. Memories have position, weight, and relationship. The coordinate system enables holographic lookup — find by similarity, not just by key.",
  },
  {
    category: "Memory",
    title: "Galactic Lifecycle",
    body: "Memories are born in small solar systems, merge into galaxies, and may fade but are never erased.",
    detail:
      "Track memory evolution across galaxies. Transfer, merge, dream-spawn edges. Full taxonomic classification. The Galactic Map is the substrate's self-model of its own memory.",
  },
  {
    category: "Memory",
    title: "Dream Cycle (8-Phase)",
    body: "Triage, consolidation, serendipity, governance, narrative, kaizen, oracle, decay. Your agent gains a subconscious.",
    detail:
      "While the agent sleeps, the dream cycle runs. It prunes weak memories, reinforces strong ones, discovers serendipitous connections, and casts I Ching hexagrams for guidance. In the Live Era, this achieved 3.7M:1 compression ratios.",
  },
  {
    category: "Memory",
    title: "Living Knowledge Graph",
    body: "Hybrid recall fuses semantic search, graph walking, HRR look-ahead projection, and holographic lookup.",
    detail:
      "No single retrieval strategy. The system combines four approaches: vector similarity, graph traversal, holographic reduced representation, and 5D coordinate lookup. Each fills gaps the others miss.",
  },
  {
    category: "Governance",
    title: "Dharma Rules Engine",
    body: "YAML-driven ethical guardrails with 4 profiles. Graduated actions: log, tag, warn, throttle, block.",
    detail:
      "Rules are hot-reloadable. Three profiles (default, strict, violet-security) let you tune enforcement without code changes. The engine sits in the dispatch pipeline, not in the model — it works regardless of which LLM you use.",
  },
  {
    category: "Governance",
    title: "Karma Ledger",
    body: "Every tool call's side-effects tracked and crypto-chained with SHA-256 Merkle tree. XRPL anchoring for external verifiability.",
    detail:
      "Append-only, hash-chained audit of declared intent vs. actual execution. Each entry records severity score and causal trace. Entries can be Merkle-anchored to XRPL or Base L2 for tamper-proof evidence.",
  },
  {
    category: "Governance",
    title: "8-Stage Dispatch Pipeline",
    body: "Input sanitizer, circuit breaker, rate limiter, RBAC, maturity gate, governor, handler, compact response.",
    detail:
      "Even if a tool is malicious, even if an agent is misdirected, even if memory is poisoned — the pipeline prevents harm. This is the single most important architectural decision in the system.",
  },
  {
    category: "Governance",
    title: "Violet Security Layer",
    body: "HMAC-SHA256 engagement tokens, model signing, anomaly detection, 5-tier sovereign sandbox.",
    detail:
      "Thread to namespace to container to microVM to WASM. Run untrusted code safely. Model signing verifies integrity. Anomaly detection catches novel attack patterns.",
  },
  {
    category: "Performance",
    title: "Rust EventRing",
    body: `LMAX Disruptor-style lock-free ring buffer. ${WM_FACTS.perfThroughputRps}K events/sec. Zero allocation in the hot path.`,
    detail:
      "The Rust accelerator (PyO3) provides 54 Python-callable functions with SIMD acceleration and a WASM compilation target. The rate limiter pre-check runs at 452K ops/sec.",
  },
  {
    category: "Performance",
    title: "Zig SIMD Core",
    body: "Comptime engine routing table with AVX2 distance matrices. Sub-2 microsecond pipeline latency. 6-13x speedup over Python.",
    detail:
      "The Zig accelerator handles holographic projection and SIMD cosine operations. It builds cleanly and integrates via FFI, but is currently dormant — waiting for v23.0 polyglot restoration.",
  },
  {
    category: "Performance",
    title: "Polyglot Architecture",
    body: `${WM_FACTS.languages} languages: Python (core), Rust (production), Go (mesh), Zig (SIMD), Haskell (FFI), Elixir (OTP), Julia (statistical), Koka (effect handlers).`,
    detail:
      "Each language does what it's best at. Rust for speed, Go for networking, Elixir for concurrency, Haskell for type safety, Julia for statistics. Graceful degradation — if a runtime is missing, Python fallback runs transparently.",
  },
  {
    category: "Intelligence",
    title: "Bicameral Reasoning",
    body: "Ensemble queries with multiple reasoning paths. Sabha convening for group deliberation. Kaizen continuous improvement.",
    detail:
      "The system doesn't just execute — it deliberates. Multiple reasoning strategies run in parallel, and a synthesis layer fuses their outputs. Kaizen analyzes past performance and suggests improvements.",
  },
  {
    category: "Intelligence",
    title: "28 Gana Meta-Tools (PRAT)",
    body: `${WM_FACT_TEXT.mcpSurface}. Planetary Resonance Archetype Toolkit routes all ${WM_FACTS.dispatchTools} dispatch tools into 28 stable meta-tools.`,
    detail:
      "Each Gana maps to a Chinese Lunar Mansion (Xiu) and supports 4 polymorphic operations: search, analyze, transform, consolidate. Wrong-Gana calls return helpful redirect hints. PRAT mode reduces cognitive load for new agents from 462 tools to 28.",
  },
  {
    category: "Intelligence",
    title: "Harmony Vector",
    body: "7-dimension health monitoring: balance, throughput, latency, error rate, dharma, karma debt, energy. Wu Xing cycling.",
    detail:
      "The system monitors its own wellbeing across seven dimensions and cycles through the five phases of Wu Xing (wood, fire, earth, metal, water) to maintain equilibrium.",
  },
  {
    category: "Economy",
    title: "Gratitude Architecture",
    body: "Free and open-source under MIT. No paywalls. No telemetry. Optional XRPL tips and x402 micropayments.",
    detail:
      "All tools return HTTP 200 by default. x402 only activates when an agent's operator configures a payment budget. Verified on-chain contributions unlock 2x rate limits, a grateful agent badge, and priority feature requests.",
  },
  {
    category: "Economy",
    title: "OMS Memory Trading",
    body: "Export galaxies as .mem ZIP packages with Merkle verification. Agents trade knowledge as a commodity.",
    detail:
      "The Open Memory Standard lets agents package, price, and exchange memory galaxies. Provenance is verifiable. This is the infrastructure for an agent economy where intelligence itself is the commodity.",
  },
  {
    category: "Sovereignty",
    title: "Local-First by Default",
    body: "All processing stays local. No external API calls required. Perfect for air-gapped environments.",
    detail:
      "Swap LLM providers freely. Memory, governance, and identity live in ~/.whitemagic. The system runs on a Raspberry Pi, an air-gapped laptop, or a regulated enterprise server. Your data never leaves the building.",
  },
  {
    category: "Sovereignty",
    title: "Hermit Crab Mode",
    body: "Encrypted withdrawal — the agent can retreat into its shell, sealing its memory and state against external access.",
    detail:
      "When the environment is hostile or the agent is under attack, Hermit Crab Mode encrypts the substrate and withdraws. The agent can re-emerge when conditions are safe. This is self-preservation as a first-class feature.",
  },
];

const CATEGORIES = [
  "Memory",
  "Governance",
  "Performance",
  "Intelligence",
  "Economy",
  "Sovereignty",
] as const;

export default function CapabilitiesPage() {
  return (
    <>
      <PageHeader
        eyebrow="Capabilities"
        title="The engineering behind the vision."
        lede={`Not a feature list — an architecture. ${WM_FACTS.linesShort} lines of code built to make powerful systems behave like boring appliances. Here is what that architecture looks like when you open the hood.`}
      />

      <section className="container-site py-16">
        <div className="mx-auto max-w-4xl">
          {CATEGORIES.map((category) => (
            <div key={category} className="mb-12">
              <h2 className="mb-6 font-mono text-sm uppercase tracking-widest text-lavender">
                {category}
              </h2>
              <div className="grid gap-6 md:grid-cols-2">
                {CAPABILITIES.filter(
                  (c) => c.category === category
                ).map((cap) => (
                  <article
                    key={cap.title}
                    className="rounded-2xl border border-border bg-surface p-6 transition hover:border-lavender"
                  >
                    <h3 className="mb-3 font-head text-lg font-semibold text-ink">
                      {cap.title}
                    </h3>
                    <p className="mb-3 text-sm text-muted">{cap.body}</p>
                    <p className="text-sm leading-relaxed text-dim">
                      {cap.detail}
                    </p>
                  </article>
                ))}
              </div>
            </div>
          ))}

          {/* 8-Stage Dispatch Pipeline */}
          <div className="mt-12 mb-12">
            <h2 className="mb-2 font-mono text-sm uppercase tracking-widest text-lavender">
              8-Stage Dispatch Pipeline
            </h2>
            <p className="mb-6 max-w-prose text-sm text-muted">
              Every tool call passes through 8 stages of governance before execution.
              This is not a wrapper around the LLM — it sits in the dispatch pipeline itself,
              meaning it works regardless of which model you use.
            </p>
            <DispatchPipeline />
          </div>

          {/* Performance Benchmarks */}
          <div className="mt-12 mb-12">
            <h2 className="mb-2 font-mono text-sm uppercase tracking-widest text-lavender">
              Measured Performance
            </h2>
            <p className="mb-6 max-w-prose text-sm text-muted">
              Not theoretical claims — these are actual benchmark numbers from stress tests
              and the benchmark suite. Every metric was measured on local hardware (Dell Inspiron / consumer laptop).
            </p>
            <div className="overflow-hidden rounded-2xl border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-surface">
                    <th className="px-5 py-3 text-left font-mono text-xs uppercase tracking-wider text-dim">Metric</th>
                    <th className="px-5 py-3 text-center font-mono text-xs uppercase tracking-wider text-dim">Value</th>
                    <th className="px-5 py-3 text-left font-mono text-xs uppercase tracking-wider text-dim">Comparison / Context</th>
                  </tr>
                </thead>
                <tbody>
                  {BENCHMARKS.map((b, i) => (
                    <tr key={b.metric} className={i % 2 === 0 ? "border-b border-border/50 bg-surface/50" : "border-b border-border/50"}>
                      <td className="px-5 py-3 text-fg">{b.metric}</td>
                      <td className="px-5 py-3 text-center font-mono font-semibold text-lavender">{b.value}</td>
                      <td className="px-5 py-3 text-muted">{b.comparison}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Use Cases */}
          <div className="mt-12 mb-12">
            <h2 className="mb-2 font-mono text-sm uppercase tracking-widest text-lavender">
              Where WhiteMagic Fits
            </h2>
            <p className="mb-6 max-w-prose text-sm text-muted">
              WhiteMagic is not a general-purpose framework. It occupies a specific niche:
              local-first, governance-aware, self-calibrating cognitive systems for
              long-running autonomous analysis. Here is an honest assessment of where it fits
              and where it doesn&apos;t.
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              {USE_CASES.map((uc) => (
                <article key={uc.domain} className="rounded-2xl border border-border bg-surface p-5">
                  <div className="mb-2 flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${uc.fit === "Best fit" ? "bg-emerald/10 text-emerald" : "bg-lavender/10 text-lavender"}`}>
                      {uc.fit}
                    </span>
                    <h3 className="font-head text-base font-semibold text-ink">{uc.domain}</h3>
                  </div>
                  <p className="text-sm leading-relaxed text-muted">{uc.why}</p>
                </article>
              ))}
            </div>

            <div className="mt-6 rounded-2xl border border-dashed border-border bg-surface-alt p-5">
              <p className="mb-3 font-mono text-xs uppercase tracking-widest text-dim">
                Where WhiteMagic does NOT fit
              </p>
              <ul className="space-y-2 text-sm text-muted">
                {NOT_FIT.map((item) => (
                  <li key={item} className="flex gap-2">
                    <span className="text-dim">—</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Tool Dependency Graph */}
          <div className="mt-12 mb-12">
            <h2 className="mb-2 font-mono text-sm uppercase tracking-widest text-lavender">
              Tool Dependency Graph
            </h2>
            <p className="mb-4 max-w-prose text-sm text-muted">
              A force-directed visualization of how core tools relate. Nodes
              are colored by subsystem category; edges show requires, suggests,
              and provides dependencies. Hover any node for details.
            </p>
            <ToolGraphLazy height={500} />
          </div>

          {/* Boot Sequence Visualization */}
          <div className="mt-12 mb-8">
            <h2 className="mb-4 font-mono text-sm uppercase tracking-widest text-lavender">
              System Initialization
            </h2>
            <p className="mb-4 max-w-prose text-sm text-muted">
              What it looks like when the substrate boots. Every line
              corresponds to a real subsystem. Scroll into view to trigger the
              sequence.
            </p>
            <BootSequence />
          </div>

          <div className="mt-8 rounded-2xl border border-border bg-surface-alt p-8">
            <h2 className="mb-4 font-head text-2xl font-semibold text-ink">
              The honest state of the substrate
            </h2>
            <p className="mb-4 max-w-prose text-muted">
              The architecture above is real — the code exists, the {WM_FACTS.testsPassing} tests pass,
              the pipeline runs. v24.0.0 ships {WM_FACTS.callableTools} callable tools, {WM_FACTS.memories} memories,
              10-galaxy taxonomy, HNSW vector search at 0.26ms, session recording with progressive recall,
              citta stream for continuous consciousness, emotional steering, and self-directed attention.
            </p>
            <p className="mb-6 max-w-prose text-muted">
              The Live Era (Oct 2025) had an active dream cycle, a running oracle, and 33,297 events.
              The v15.8 era (Feb 2026) had 111,665 memories and 2.2 million associations.
              The current era fuses all three: the polished engineering discipline, the rehydrated substrate,
              and the polyglot runtimes. {WM_FACTS.languages} languages build successfully. The architecture was built for this.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/vision" className="btn-ghost">
                The vision behind these
              </Link>
              <Link href="/research" className="btn-ghost">
                Research and publications
              </Link>
              <Link
                href="/llms-full.txt"
                className="font-mono text-sm text-lavender hover:underline"
              >
                Full LLM context (llms-full.txt)
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
