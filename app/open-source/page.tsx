import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { WM_FACTS, WM_FACT_TEXT } from "@/lib/facts";
import { ArrowRight, Book, Shield, Brain, Database, Zap, Code, Terminal } from "lucide-react";

export const metadata = {
  title: "Docs — WhiteMagic",
  description: "WhiteMagic v25.1.0 documentation — 860 callable tools, 14-galaxy memory, Dharma governance, citta stream, 7 polyglot accelerators. MIT-licensed, local-first.",
};

const DOC_SECTIONS = [
  {
    icon: Terminal,
    title: "Getting Started",
    description: "Install, configure, and verify WhiteMagic in 60 seconds.",
    links: [
      { label: "Install Guide", href: "/mcp-bridge" },
      { label: "MCP Config Examples", href: "https://github.com/lbailey94/whitemagic/blob/main/docs/guides/MCP_CONFIG_EXAMPLES.md" },
      { label: "Quickstart Guide", href: "https://github.com/lbailey94/whitemagic/blob/main/QUICKSTART.md" },
    ],
  },
  {
    icon: Database,
    title: "Memory System",
    description: "14-galaxy taxonomy, 6D holographic coordinates, FTS5 + HNSW search, galactic lifecycle, session recording.",
    links: [
      { label: "Memory Architecture", href: "https://github.com/lbailey94/whitemagic/blob/main/docs/architecture/" },
      { label: "Galaxy Taxonomy", href: "https://github.com/lbailey94/whitemagic/blob/main/AI_PRIMARY.md" },
      { label: "Session Recording", href: "https://github.com/lbailey94/whitemagic/blob/main/docs/guides/" },
    ],
  },
  {
    icon: Shield,
    title: "Governance",
    description: "Dharma rules engine, Karma ledger, 8-stage dispatch pipeline, RBAC, rate limiting, circuit breakers.",
    links: [
      { label: "Governance Overview", href: "/governance" },
      { label: "Dharma Rules", href: "https://github.com/lbailey94/whitemagic/blob/main/docs/architecture/" },
      { label: "Karma Ledger API", href: "https://github.com/lbailey94/whitemagic/blob/main/docs/KARMA_LEDGER_API.md" },
    ],
  },
  {
    icon: Brain,
    title: "Consciousness",
    description: "Citta stream, emotional steering, self-directed attention, goal graph, dream cycle, gnosis introspection.",
    links: [
      { label: "Consciousness Architecture", href: "https://github.com/lbailey94/whitemagic/blob/main/AI_PRIMARY.md" },
      { label: "Dream Cycle", href: "https://github.com/lbailey94/whitemagic/blob/main/docs/architecture/" },
      { label: "Citta Bridge", href: "https://github.com/lbailey94/whitemagic/blob/main/docs/architecture/" },
    ],
  },
  {
    icon: Zap,
    title: "Polyglot Acceleration",
    description: "Rust SIMD, Haskell inference, Elixir orchestration, Go networking, Zig compute, Julia numerical.",
    links: [
      { label: "Polyglot Strategy", href: "https://github.com/lbailey94/whitemagic/blob/main/docs/architecture/" },
      { label: "Rust Bridge", href: "https://github.com/lbailey94/whitemagic/tree/main/core/whitemagic-rust" },
    ],
  },
  {
    icon: Code,
    title: "API Reference",
    description: "860 callable tools, 28 Gana meta-tools, Python API, CLI, MCP server.",
    links: [
      { label: "AI Primary Spec", href: "https://github.com/lbailey94/whitemagic/blob/main/AI_PRIMARY.md" },
      { label: "PRAT Guide", href: "https://github.com/lbailey94/whitemagic/blob/main/docs/PRAT_GUIDE.md" },
      { label: "llms.txt", href: "/llms.txt" },
    ],
  },
];

export default function OpenSourcePage() {
  return (
    <>
      <PageHeader
        eyebrow="Documentation"
        title="WhiteMagic v25.1.0"
        lede={`${WM_FACT_TEXT.toolSurface}. ${WM_FACT_TEXT.testSuite}. ${WM_FACT_TEXT.memorySurface}. 7 polyglot accelerators. MIT-licensed, local-first.`}
      />

      <section className="container-site py-12">
        <div className="mx-auto max-w-4xl">
          {/* Stats bar */}
          <div className="mb-12 grid grid-cols-2 gap-4 md:grid-cols-4">
            {[
              { label: "Callable Tools", value: WM_FACTS.callableTools },
              { label: "Tests Passing", value: WM_FACTS.testsPassing },
              { label: "Memories", value: WM_FACTS.memories },
              { label: "Languages", value: WM_FACTS.languages },
            ].map((stat) => (
              <div key={stat.label} className="rounded-lg border border-border bg-surface p-4 text-center">
                <div className="font-head text-2xl font-bold text-ink">{stat.value}</div>
                <div className="mt-1 font-mono text-[10px] uppercase tracking-widest text-dim">{stat.label}</div>
              </div>
            ))}
          </div>

          {/* Doc sections */}
          <div className="grid gap-6 md:grid-cols-2">
            {DOC_SECTIONS.map((section) => {
              const Icon = section.icon;
              return (
                <article key={section.title} className="rounded-xl border border-border bg-surface p-6">
                  <div className="mb-3 flex items-center gap-3">
                    <Icon className="h-5 w-5 text-lavender" />
                    <h3 className="font-head text-lg font-semibold text-ink">{section.title}</h3>
                  </div>
                  <p className="mb-4 text-sm leading-relaxed text-muted">{section.description}</p>
                  <ul className="space-y-2">
                    {section.links.map((link) => (
                      <li key={link.href}>
                        <Link
                          href={link.href}
                          className="inline-flex items-center gap-1 text-sm text-lavender hover:underline"
                        >
                          <ArrowRight className="h-3 w-3" />
                          {link.label}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </article>
              );
            })}
          </div>

          {/* GitHub CTA */}
          <div className="mt-12 rounded-xl border border-border-light bg-surface-alt p-8 text-center">
            <h2 className="mb-3 font-head text-xl font-semibold text-ink">Browse the source</h2>
            <p className="mb-6 text-sm text-muted">
              {WM_FACTS.linesShort} lines of code. {WM_FACTS.testsPassing} tests. MIT-licensed. Your data never leaves your machine.
            </p>
            <Link
              href="https://github.com/lbailey94/whitemagic"
              className="btn-primary inline-flex"
            >
              GitHub Repository →
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
