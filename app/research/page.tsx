import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { ExternalLink, FileText, Beaker, Brain, Shield, Database } from "lucide-react";
import { WM_FACTS, WM_FACT_TEXT } from "@/lib/facts";

export const metadata = {
  title: "Research — WhiteMagic",
  description: "WhiteMagic engineering research: Karma Ledger (side-effect fidelity), holographic memory architecture, Dharma governance, citta stream consciousness primitives. MIT-licensed, open source.",
};

const RESEARCH_AREAS = [
  {
    icon: Database,
    title: "Holographic Memory",
    description: "5D coordinate system (emotional, temporal, associative, importance, novelty) for memory storage. 10-galaxy taxonomy with galactic lifecycle — nothing deleted, only rotated outward. FTS5 + HNSW hybrid search.",
    status: "Shipped",
    details: [
      "10 galaxies: aria, citta, codex, journals, dreams, research, sessions, substrate, tutorial, universal",
      "49,429 memories in production",
      "2,853 cross-galaxy associations",
      "0.26ms HNSW search latency",
    ],
  },
  {
    icon: Shield,
    title: "Dharma Governance Engine",
    description: "YAML-driven policy engine with graduated actions (LOG → TAG → WARN → THROTTLE → BLOCK). 8-stage dispatch pipeline. Karma ledger with hash-chained side-effect auditing.",
    status: "Shipped",
    details: [
      "3 Dharma profiles (minimal, standard, strict)",
      "35,060+ audits recorded in production",
      "Sub-millisecond policy evaluation",
      "Hot-reloadable rules (no restart required)",
    ],
  },
  {
    icon: Brain,
    title: "Citta Stream + Consciousness",
    description: "Continuous consciousness tracking with coherence metrics. Emotional steering (frustration, curiosity, satisfaction). Self-directed attention with 7+1 action types. Goal graph for cross-session intention tracking.",
    status: "Shipped",
    details: [
      "22 citta moments auto-persisted",
      "Emotional valence mapping (sattvic, rajasic, tamasic)",
      "7+1 self-directed action types",
      "Dream cycle: 12-phase memory consolidation",
    ],
  },
  {
    icon: Beaker,
    title: "Karma Ledger Benchmark",
    description: "Runtime audit benchmark evaluating declared-vs-actual side effects in agent tool use. Measures whether an agent's description of its actions matches reality — a prerequisite for any oversight mechanism.",
    status: "In Preparation",
    details: [
      "5 tool categories: file, browser, API, database, shell",
      "3 model families planned",
      "Fidelity scored as 1 - normalized edit distance",
      "arXiv preprint in preparation",
    ],
  },
];

const PUBLICATIONS = [
  {
    title: "Karma Ledger: A Runtime Audit Substrate for Declared-vs-Actual Side Effects in Agent Tool Use",
    authors: "Lucas Bailey",
    venue: "arXiv cs.AI",
    year: "2026",
    status: "in-prep" as const,
    abstract: "We introduce Karma Ledger, a runtime substrate for measuring declaration-actual fidelity in multi-agent tool use. For each tool call, the benchmark compares the agent's declared state diff against the empirical state diff, with fidelity scored as 1 - normalized edit distance.",
    tags: ["agent safety", "evaluation", "benchmark", "MCP"],
  },
];

export default function ResearchPage() {
  return (
    <>
      <PageHeader
        eyebrow="Research"
        title="Engineering research, shipped as working code."
        lede={`${WM_FACT_TEXT.toolSurface}. ${WM_FACT_TEXT.testSuite}. ${WM_FACT_TEXT.memorySurface}. Every research finding is pressure-tested inside the WhiteMagic codebase before it's written about.`}
      />

      <section className="container-site py-12">
        <div className="mx-auto max-w-4xl">
          {/* Stats */}
          <div className="mb-12 grid grid-cols-2 gap-4 md:grid-cols-4">
            {[
              { label: "Callable Tools", value: WM_FACTS.callableTools },
              { label: "Tests Passing", value: WM_FACTS.testsPassing },
              { label: "Memories", value: WM_FACTS.memories },
              { label: "Galaxies", value: WM_FACTS.galaxies },
            ].map((s) => (
              <div key={s.label} className="rounded-lg border border-border bg-surface p-4 text-center">
                <div className="font-head text-2xl font-bold text-ink">{s.value}</div>
                <div className="mt-1 font-mono text-[10px] uppercase tracking-widest text-dim">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Research areas */}
          <div className="mb-16 space-y-6">
            {RESEARCH_AREAS.map((area) => {
              const Icon = area.icon;
              return (
                <article key={area.title} className="rounded-xl border border-border bg-surface p-6">
                  <div className="mb-3 flex items-center gap-3">
                    <Icon className="h-5 w-5 text-lavender" />
                    <h2 className="font-head text-xl font-semibold text-ink">{area.title}</h2>
                    <span className={`ml-auto rounded-full px-2.5 py-0.5 text-xs font-medium ${area.status === "Shipped" ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>
                      {area.status}
                    </span>
                  </div>
                  <p className="mb-4 text-sm leading-relaxed text-muted">{area.description}</p>
                  <ul className="grid gap-2 md:grid-cols-2">
                    {area.details.map((d) => (
                      <li key={d} className="flex items-start gap-2 text-sm text-muted">
                        <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-lavender" />
                        {d}
                      </li>
                    ))}
                  </ul>
                </article>
              );
            })}
          </div>

          {/* Publications */}
          <div className="mb-16">
            <div className="mb-6 flex items-center gap-3">
              <FileText className="h-5 w-5 text-lavender" />
              <h2 className="font-head text-2xl font-semibold text-ink">Publications</h2>
            </div>
            <div className="space-y-6">
              {PUBLICATIONS.map((pub) => (
                <article key={pub.title} className="rounded-xl border border-border bg-surface p-6">
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700">In Preparation</span>
                    {pub.tags.map((tag) => (
                      <span key={tag} className="rounded-full bg-surface-alt px-2 py-0.5 text-xs text-dim">{tag}</span>
                    ))}
                  </div>
                  <h3 className="mb-2 font-head text-lg font-semibold text-ink">{pub.title}</h3>
                  <p className="mb-3 text-sm text-muted">{pub.authors} · {pub.venue} · {pub.year}</p>
                  <p className="mb-4 max-w-prose text-sm leading-relaxed text-muted">{pub.abstract}</p>
                </article>
              ))}
            </div>
          </div>

          {/* Principles */}
          <div className="mb-16 rounded-2xl border border-border bg-surface-alt p-8">
            <h2 className="mb-4 font-head text-xl font-semibold text-ink">Research principles</h2>
            <ul className="space-y-3 text-muted">
              <li className="flex gap-3"><span className="text-lavender">1.</span><span><strong className="text-fg">Reproducibility first</strong> — Every benchmark includes a Docker environment, pinned dependencies, and a run script.</span></li>
              <li className="flex gap-3"><span className="text-lavender">2.</span><span><strong className="text-fg">Negative results published</strong> — If a hypothesis fails, we publish the failure and why.</span></li>
              <li className="flex gap-3"><span className="text-lavender">3.</span><span><strong className="text-fg">Open data, open code</strong> — MIT license for code; CC-BY for data. No paywalls.</span></li>
              <li className="flex gap-3"><span className="text-lavender">4.</span><span><strong className="text-fg">Shipped, not speculated</strong> — Research findings are implemented in the codebase before being written about.</span></li>
            </ul>
          </div>

          {/* CTA */}
          <div className="text-center">
            <h2 className="mb-4 font-head text-2xl font-semibold text-ink">Support this research</h2>
            <p className="mx-auto mb-6 max-w-prose text-muted">
              Solo-founded with zero institutional backing. Every contribution goes directly to open-source infrastructure.
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <Link href="/fund" className="btn-primary">Support the work</Link>
              <Link href="/open-source" className="btn-ghost">Browse the source</Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
