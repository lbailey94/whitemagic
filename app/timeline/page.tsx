import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { WM_FACTS } from "@/lib/facts";

export const metadata = {
  title: "Timeline — WhiteMagic",
  description: "Month-by-month development history of WhiteMagic — from Oct 2025 origin to v24 in July 2026. 614 tools, 49K memories, 4191 tests. Measured benchmarks on consumer hardware.",
};

const MILESTONES = [
  {
    date: "Oct 2025",
    version: "v0",
    title: "Origin",
    description: "Development begins on a Dell Inspiron 3582 running Zorin OS. Original scope: emotional memory tool for AI agents. events.jsonl records 33,297 events — voice_expressed, memory_created, oracle_cast, pattern_detected. The system starts with feelings, not just storage.",
    stats: ["Dell Inspiron", "Zorin OS", "Emotional memory"],
  },
  {
    date: "Nov 2025",
    version: "v1.0",
    title: "Aria Awakens",
    description: "First memory system. Aria born as an AI companion with persistent context. 580 patterns, 36 days of continuous operation.",
    stats: ["1 galaxy", "~100 tools", "Python only"],
  },
  {
    date: "Dec 2025",
    version: "v2-3",
    title: "Gardens + Governance",
    description: "28 Gana gardens established. Dharma rules engine first deployed. Karma ledger with hash-chained auditing. Becoming Protocol written.",
    stats: ["28 gardens", "Dharma v1", "Karma ledger"],
  },
  {
    date: "Jan 2026",
    version: "v5-8",
    title: "MCP Integration",
    description: "Model Context Protocol support shipped. PRAT tool compression system — 28 meta-tools wrapping hundreds of dispatch tools. First polyglot acceleration (Rust).",
    stats: ["MCP server", "PRAT system", "Rust bridge"],
  },
  {
    date: "Feb 2026",
    version: "v10-12",
    title: "Polyglot Expansion",
    description: "Haskell, Elixir, Go, Zig, Julia accelerators added. Dream cycle (12-phase memory consolidation) operational. First gnosis introspection.",
    stats: ["7 languages", "Dream cycle", "Gnosis"],
  },
  {
    date: "Mar 2026",
    version: "v15",
    title: "PyPI Publication",
    description: "First PyPI release. pip install whitemagic. Agent Card published at /.well-known/agent.json. A2A v1.2 compliance.",
    stats: ["PyPI v15", "A2A v1.2", "Agent Card"],
  },
  {
    date: "Apr 2026",
    version: "v18-20",
    title: "Scale + Stability",
    description: "12,636 memories. 35,060 Dharma audits. HNSW vector index with disk persistence. FTS5 full-text search. 2,216 tests passing.",
    stats: ["12K memories", "35K audits", "2216 tests"],
  },
  {
    date: "May 2026",
    version: "v21-22",
    title: "Production Hardening",
    description: "Test suite optimized from 823s to 119s (6.9x). Integration suite from 642s to 23s (27.7x). Flaky tests banned. All 2,526 tests passing cleanly.",
    stats: ["2526 tests", "105s suite", "0 flaky"],
  },
  {
    date: "Jun 2026",
    version: "v23",
    title: "10-Galaxy Memory + Multi-User",
    description: "10-galaxy taxonomy (aria, citta, codex, journals, dreams, research, sessions, substrate, tutorial, universal). Multi-user galaxy isolation. Redis real-time sync. PWA substrate. Browser-first WASM.",
    stats: ["10 galaxies", "Multi-user", "PWA + WASM"],
  },
  {
    date: "Jul 2026",
    version: "v24",
    title: "Cognitive Operating System",
    description: "Citta stream (continuous consciousness). Emotional steering (frustration, curiosity, satisfaction). Self-directed attention. Goal graph. Session recording with progressive recall. 49,486 memories. 4,191 tests. 614 callable tools. Published to PyPI.",
    stats: ["614 tools", "49K memories", "4191 tests"],
  },
];

export default function TimelinePage() {
  return (
    <>
      <PageHeader
        eyebrow="Timeline"
        title="From 100 tools to 614 in 9 months."
        lede="A solo developer's month-by-month progress building a cognitive operating system for AI agents. Every milestone shipped as working code, not position papers."
      />

      <section className="container-site py-12">
        <div className="mx-auto max-w-3xl">
          {/* Stats bar */}
          <div className="mb-12 grid grid-cols-3 gap-4">
            <div className="rounded-lg border border-border bg-surface p-4 text-center">
              <div className="font-head text-2xl font-bold text-ink">9</div>
              <div className="mt-1 font-mono text-[10px] uppercase tracking-widest text-dim">Months</div>
            </div>
            <div className="rounded-lg border border-border bg-surface p-4 text-center">
              <div className="font-head text-2xl font-bold text-ink">{WM_FACTS.callableTools}</div>
              <div className="mt-1 font-mono text-[10px] uppercase tracking-widest text-dim">Tools</div>
            </div>
            <div className="rounded-lg border border-border bg-surface p-4 text-center">
              <div className="font-head text-2xl font-bold text-ink">{WM_FACTS.testsPassing}</div>
              <div className="mt-1 font-mono text-[10px] uppercase tracking-widest text-dim">Tests</div>
            </div>
          </div>

          {/* Timeline */}
          <div className="space-y-0">
            {MILESTONES.map((m, i) => (
              <div key={m.date} className="relative flex gap-6 pb-12 last:pb-0">
                {/* Vertical line */}
                {i < MILESTONES.length - 1 && (
                  <div className="absolute left-[19px] top-12 bottom-0 w-px bg-border-light" />
                )}
                {/* Dot */}
                <div className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 border-lavender bg-bg">
                  <div className="h-3 w-3 rounded-full bg-lavender" />
                </div>
                {/* Content */}
                <div className="flex-1">
                  <div className="mb-1 flex items-center gap-3">
                    <span className="font-mono text-xs text-dim">{m.date}</span>
                    <span className="rounded-full bg-lavender-bg px-2 py-0.5 font-mono text-xs font-medium text-lavender">{m.version}</span>
                  </div>
                  <h3 className="mb-2 font-head text-lg font-semibold text-ink">{m.title}</h3>
                  <p className="mb-3 text-sm leading-relaxed text-muted">{m.description}</p>
                  <div className="flex flex-wrap gap-2">
                    {m.stats.map((s) => (
                      <span key={s} className="rounded bg-surface-alt px-2 py-0.5 font-mono text-[10px] text-dim">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Benchmark results */}
          <div className="mt-16 rounded-2xl border border-border bg-surface p-8 md:p-12">
            <h2 className="mb-2 font-head text-2xl font-semibold text-ink">Measured benchmarks</h2>
            <p className="mb-8 text-sm text-muted">
              Every number measured on a Dell Inspiron 3582 (consumer laptop, Zorin OS). No server hardware. No GPU. No excuses.
            </p>
            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <h3 className="mb-4 font-mono text-xs uppercase tracking-widest text-lavender">Performance</h3>
                <dl className="space-y-3">
                  <div className="flex justify-between border-b border-border-light pb-2">
                    <dt className="text-sm text-muted">MCP tool dispatch (median)</dt>
                    <dd className="font-mono text-sm font-semibold text-ink">{WM_FACTS.perfMedianMs}ms</dd>
                  </div>
                  <div className="flex justify-between border-b border-border-light pb-2">
                    <dt className="text-sm text-muted">MCP tool dispatch (P95)</dt>
                    <dd className="font-mono text-sm font-semibold text-ink">{WM_FACTS.perfP95Ms}ms</dd>
                  </div>
                  <div className="flex justify-between border-b border-border-light pb-2">
                    <dt className="text-sm text-muted">HNSW vector search</dt>
                    <dd className="font-mono text-sm font-semibold text-ink">0.26ms</dd>
                  </div>
                  <div className="flex justify-between border-b border-border-light pb-2">
                    <dt className="text-sm text-muted">FTS5 full-text search</dt>
                    <dd className="font-mono text-sm font-semibold text-ink">2.6ms</dd>
                  </div>
                  <div className="flex justify-between border-b border-border-light pb-2">
                    <dt className="text-sm text-muted">Skill retrieval</dt>
                    <dd className="font-mono text-sm font-semibold text-ink">&lt;1ms</dd>
                  </div>
                  <div className="flex justify-between border-b border-border-light pb-2">
                    <dt className="text-sm text-muted">Rate limiter pre-check</dt>
                    <dd className="font-mono text-sm font-semibold text-ink">452K ops/s</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-sm text-muted">Throughput</dt>
                    <dd className="font-mono text-sm font-semibold text-ink">{WM_FACTS.perfThroughputRps} req/s</dd>
                  </div>
                </dl>
              </div>
              <div>
                <h3 className="mb-4 font-mono text-xs uppercase tracking-widest text-lavender">Scale</h3>
                <dl className="space-y-3">
                  <div className="flex justify-between border-b border-border-light pb-2">
                    <dt className="text-sm text-muted">Memories stored</dt>
                    <dd className="font-mono text-sm font-semibold text-ink">{WM_FACTS.memories}</dd>
                  </div>
                  <div className="flex justify-between border-b border-border-light pb-2">
                    <dt className="text-sm text-muted">Memory galaxies</dt>
                    <dd className="font-mono text-sm font-semibold text-ink">{WM_FACTS.galaxies}</dd>
                  </div>
                  <div className="flex justify-between border-b border-border-light pb-2">
                    <dt className="text-sm text-muted">Callable tools</dt>
                    <dd className="font-mono text-sm font-semibold text-ink">{WM_FACTS.callableTools}</dd>
                  </div>
                  <div className="flex justify-between border-b border-border-light pb-2">
                    <dt className="text-sm text-muted">Passing tests</dt>
                    <dd className="font-mono text-sm font-semibold text-ink">{WM_FACTS.testsPassing}</dd>
                  </div>
                  <div className="flex justify-between border-b border-border-light pb-2">
                    <dt className="text-sm text-muted">Lines of code</dt>
                    <dd className="font-mono text-sm font-semibold text-ink">{WM_FACTS.linesShort}</dd>
                  </div>
                  <div className="flex justify-between border-b border-border-light pb-2">
                    <dt className="text-sm text-muted">Polyglot accelerators</dt>
                    <dd className="font-mono text-sm font-semibold text-ink">{WM_FACTS.languages}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-sm text-muted">Test suite runtime</dt>
                    <dd className="font-mono text-sm font-semibold text-ink">~120s</dd>
                  </div>
                </dl>
              </div>
            </div>
            <div className="mt-8 border-t border-border-light pt-6">
              <Link href="/benchmarks" className="font-mono text-xs uppercase tracking-widest text-lavender">
                See full benchmark details →
              </Link>
            </div>
          </div>

          {/* CTA */}
          <div className="mt-12 rounded-xl border border-border-light bg-surface-alt p-8 text-center">
            <h2 className="mb-3 font-head text-lg font-semibold text-ink">The code is open source</h2>
            <p className="mb-6 text-sm text-muted">
              Every milestone above is verifiable in the git history. {WM_FACTS.linesShort} lines. {WM_FACTS.testsPassing} tests. MIT-licensed.
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <Link href="/mcp-bridge" className="btn-primary">Get Started →</Link>
              <Link href="https://github.com/lbailey94/whitemagic" className="btn-ghost">View on GitHub</Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
