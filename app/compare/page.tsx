import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { WM_FACTS } from "@/lib/facts";

export const metadata = {
  title: "Comparison — WhiteMagic Labs",
  description:
    "Honest feature-by-feature comparison of WhiteMagic vs Mem0, Letta, and standard RAG systems. Where WhiteMagic wins, where it doesn't, and where competitors have advantages.",
};

interface CompareRow {
  capability: string;
  whitemagic: string;
  mem0: string;
  letta: string;
  rag: string;
}

const MEMORY: CompareRow[] = [
  { capability: "Memory architecture", whitemagic: "5D holographic coordinates (temporal, semantic, emotional, relational, importance)", mem0: "Flat vector store with metadata tags", letta: "Agent state + memory blocks, harness-managed", rag: "Linear vector embeddings, no relationships" },
  { capability: "Persistence horizon", whitemagic: "Global — memories persist forever, rotate through galactic lifecycle zones", mem0: "Session or conversation-scoped", letta: "Persistent within a harness deployment", rag: "N/A — stateless retrieval" },
  { capability: "Search modalities", whitemagic: "HNSW vector + FTS5 full-text + graph walking + HRR projection + 5D coordinate lookup", mem0: "Vector similarity only", letta: "Vector + keyword within harness", rag: "Vector similarity only" },
  { capability: "Memory relationships", whitemagic: "Cross-galaxy associations, knowledge graph, 2.2M associations in v15.8 era", mem0: "No relationship tracking", letta: "Limited — within agent context window", rag: "No relationships" },
  { capability: "Decay & consolidation", whitemagic: "8-phase dream cycle: triage, consolidation, serendipity, governance, narrative, kaizen, oracle, decay", mem0: "No decay or consolidation", letta: "No dream cycle", rag: "No decay" },
  { capability: "Emotional encoding", whitemagic: "Emotional valence dimension in 5D coords, 20+ emotional gardens (joy, grief, courage, love)", mem0: "No emotional encoding", letta: "No emotional encoding", rag: "No emotional encoding" },
];

const GOVERNANCE: CompareRow[] = [
  { capability: "Ethical governance", whitemagic: "Dharma rules engine — YAML-driven, 4 profiles, hot-reloadable, 8-stage dispatch pipeline", mem0: "Prompt-based guardrails", letta: "Harness-level tool permissions", rag: "None" },
  { capability: "Audit trail", whitemagic: "Karma ledger — SHA-256 Merkle-chained, XRPL-anchored, append-only", mem0: "Basic logging", letta: "Harness logs", rag: "None" },
  { capability: "Input sanitization", whitemagic: "Shell injection detection, content scanning, internal field stripping", mem0: "No", letta: "No", rag: "No" },
  { capability: "Rate limiting", whitemagic: "Rust EventRing — 452K ops/s pre-check, zero allocation hot path", mem0: "No", letta: "Harness-level", rag: "No" },
  { capability: "Circuit breaker", whitemagic: "Yes — automatic failure detection and recovery", mem0: "No", letta: "No", rag: "No" },
  { capability: "Sandboxing", whitemagic: "5-tier sovereign sandbox: thread → namespace → container → microVM → WASM", mem0: "No", letta: "No", rag: "No" },
];

const PERFORMANCE: CompareRow[] = [
  { capability: "Skill retrieval", whitemagic: "<1ms (Muscle Memory)", mem0: "N/A", letta: "200ms-2s (LLM planning)", rag: "50-500ms (vector search)" },
  { capability: "Vector search", whitemagic: "0.26ms (HNSW, 16K embeddings)", mem0: "50-200ms (cloud API)", letta: "10-50ms (local)", rag: "50-500ms" },
  { capability: "Local-first", whitemagic: "Yes — by default. No cloud required.", mem0: "No — cloud API", letta: "Partial — harness-dependent", rag: "No — cloud-dependent" },
  { capability: "Offline operation", whitemagic: "Full operation including inference (ternary kernels, Ollama integration)", mem0: "No", letta: "Partial", rag: "No" },
  { capability: "Polyglot acceleration", whitemagic: "7 languages: Rust, Go, Zig, Haskell, Elixir, Julia, Koka", mem0: "Python only", letta: "Python only", rag: "Python only" },
  { capability: "Probabilistic tracking", whitemagic: "HLL + Count-Min Sketch — O(1) space, runs forever", mem0: "No", letta: "No", rag: "No" },
];

const COGNITIVE: CompareRow[] = [
  { capability: "Consciousness primitives", whitemagic: "Citta stream, coherence metrics (8 dimensions), Smarana practice, presence quality", mem0: "No", letta: "Agent identity within harness", rag: "No" },
  { capability: "Self-calibrating forecasts", whitemagic: "Brier-scored predictions, 21 validated prescience claims, 523 points", mem0: "No", letta: "No", rag: "No" },
  { capability: "Tool selection learning", whitemagic: "Thompson sampling bandit — Beta posteriors converge with use, no retraining", mem0: "No", letta: "No", rag: "No" },
  { capability: "Metacognitive awareness", whitemagic: "Cardinality-velocity surprise gate — modulates learning rate by novelty", mem0: "No", letta: "No", rag: "No" },
  { capability: "Session continuity", whitemagic: "Session recorder with progressive recall, selective replay, FTS5 search", mem0: "No", letta: "Agent state persistence", rag: "No" },
  { capability: "Dream cycle", whitemagic: "8-phase: triage, consolidation, serendipity, governance, narrative, kaizen, oracle, decay", mem0: "No", letta: "No", rag: "No" },
];

const HONEST_WINS_FOR_COMPETITORS: { competitor: string; advantage: string }[] = [
  { competitor: "Mem0", advantage: "Hosted cloud API — zero setup, zero infrastructure. If you need memory in 5 minutes and don't care about governance, privacy, or local-first, Mem0 is faster to integrate." },
  { competitor: "Mem0", advantage: "Established market presence and documentation. WhiteMagic's docs are thorough but technical; Mem0 has a polished developer experience for quick starts." },
  { competitor: "Letta", advantage: "Deep harness integration. Letta manages the agent runtime itself — tool calling, context windows, model routing. WhiteMagic is a substrate that any agent plugs into, which means Letta has tighter coupling for harness-native agents." },
  { competitor: "Letta", advantage: "Memory models (June 2026) — specialized models for creating durable context that transfers across LLMs. WhiteMagic doesn't yet have model-trained memory compression." },
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

export default function ComparePage() {
  return (
    <>
      <PageHeader
        eyebrow="Comparison"
        title="An honest comparison."
        lede="WhiteMagic is not the right tool for every job. This page compares it against Mem0, Letta, and standard RAG across memory, governance, performance, and cognition — including where competitors have genuine advantages."
      />

      <section className="container-site py-16">
        <div className="mx-auto max-w-5xl">
          <CompareTable rows={MEMORY} title="Memory Architecture" />
          <CompareTable rows={GOVERNANCE} title="Governance & Safety" />
          <CompareTable rows={PERFORMANCE} title="Performance & Deployment" />
          <CompareTable rows={COGNITIVE} title="Cognitive Capabilities" />

          {/* Honest advantages for competitors */}
          <div className="mt-12 rounded-2xl border border-dashed border-border bg-surface-alt p-6">
            <h2 className="mb-4 font-head text-lg font-semibold text-ink">
              Where competitors genuinely win
            </h2>
            <p className="mb-6 text-sm text-muted">
              We don&apos;t pretend WhiteMagic is perfect for every use case. Here are the areas
              where competitors have real, honest advantages.
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              {HONEST_WINS_FOR_COMPETITORS.map((item, i) => (
                <article key={i} className="rounded-xl border border-border bg-surface p-4">
                  <p className="mb-2 font-mono text-xs uppercase tracking-wider text-dim">{item.competitor}</p>
                  <p className="text-sm leading-relaxed text-muted">{item.advantage}</p>
                </article>
              ))}
            </div>
          </div>

          {/* Summary */}
          <div className="mt-12 rounded-2xl border border-border bg-surface p-8">
            <h2 className="mb-4 font-head text-xl font-semibold text-ink">The bottom line</h2>
            <p className="mb-4 text-sm leading-relaxed text-muted">
              <strong className="text-fg">Choose WhiteMagic if</strong> you need local-first operation,
              ethical governance as architecture (not prompts), memory that persists and consolidates,
              consciousness primitives for continuous agents, or you&apos;re building for air-gapped / regulated environments.
            </p>
            <p className="mb-4 text-sm leading-relaxed text-muted">
              <strong className="text-fg">Choose Mem0 if</strong> you need a hosted memory API in 5 minutes
              and don&apos;t need governance, privacy guarantees, or local-first operation.
            </p>
            <p className="mb-4 text-sm leading-relaxed text-muted">
              <strong className="text-fg">Choose Letta if</strong> you want a complete agent harness that
              manages tool calling, context windows, and model routing — and you&apos;re okay being harness-locked.
            </p>
            <p className="text-sm leading-relaxed text-muted">
              <strong className="text-fg">Choose standard RAG if</strong> you just need to search documents
              and ask questions. It&apos;s simpler, well-understood, and has a massive ecosystem.
            </p>
          </div>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/benchmarks" className="btn-ghost">View benchmarks →</Link>
            <Link href="/quickstart" className="btn-ghost">Quickstart guide →</Link>
            <Link href="/faq" className="btn-ghost">FAQ →</Link>
          </div>
        </div>
      </section>
    </>
  );
}
