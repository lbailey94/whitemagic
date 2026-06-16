import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { ExternalLink, FileText, Beaker } from "lucide-react";
import {
  FIELD_CONCLUSIONS,
  FIELD_MAP_UPDATED,
  FIELD_SIGNALS,
  ROADMAP_UPDATES,
} from "@/lib/field-map";

export const metadata = {
  title: "Research & Publications — WhiteMagic Labs",
  description:
    "Cross-domain technology convergence research spanning AI governance, cognitive architectures, and agentic safety. 18 domains, 371 source files, one epistemic standard. Not to be confused with AllenAI's PreScience benchmark for scientific contribution forecasting.",
};

interface Publication {
  title: string;
  authors: string;
  venue: string;
  year: string;
  status: "published" | "submitted" | "in-prep";
  abstract: string;
  links: { label: string; href: string }[];
  tags: string[];
}

interface Benchmark {
  name: string;
  description: string;
  status: "live" | "in-development" | "planned";
  metrics: { label: string; value: string }[];
  href: string;
}

const PUBLICATIONS: Publication[] = [
  {
    title: "Karma Ledger: A Runtime Audit Substrate for Declared-vs-Actual Side Effects in Agent Tool Use",
    authors: "WhiteMagic Labs",
    venue: "arXiv cs.AI",
    year: "2026",
    status: "in-prep",
    abstract:
      "We introduce Karma Ledger, a runtime substrate for measuring declaration-actual fidelity in multi-agent tool use. For each tool call, the benchmark compares the agent's declared state diff against the empirical state diff, with fidelity scored as 1 - normalized edit distance. Planned validation will compare scores against human judgment and downstream task outcomes across file, browser, API, database, and shell operations.",
    links: [
      { label: "arXiv (coming)", href: "#" },
    ],
    tags: ["agent safety", "evaluation", "benchmark", "MCP"],
  },
];

const BENCHMARKS: Benchmark[] = [
  {
    name: "Karma Ledger Benchmark",
    description:
      "Runtime audit benchmark evaluating declared-vs-actual side effects in agent tool use. Planned task suite across file, browser, API, database, and shell operations.",
    status: "in-development",
    metrics: [
      { label: "Tasks", value: "Planned" },
      { label: "Tool categories", value: "5" },
      { label: "Model families", value: "3" },
      { label: "License", value: "MIT" },
    ],
    href: "/open-source",
  },
];

export default function ResearchPage() {
  return (
    <>
      <PageHeader
        eyebrow="Research"
        title="Cross-domain research for the agentic era"
        lede="18 research domains, 371 source files, one epistemic standard — from agent governance to convergence analysis."
      />

      <section className="container-site py-16">
        {/* Research Overview */}
        <div className="mb-16 rounded-2xl border border-border bg-surface-alt p-6 md:p-8">
          <h2 className="mb-4 font-head text-2xl font-semibold text-ink">
            The Nature of This Work
          </h2>
          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <p className="leading-relaxed text-muted">
                WhiteMagic Labs operates at the intersection of{" "}
                <strong className="text-fg">agent governance</strong>,{" "}
                <strong className="text-fg">cross-domain synthesis</strong>, and{" "}
                <strong className="text-fg">predictive convergence analysis</strong>.
                The research corpus spans 18 domains — from AI safety and energy
                systems to indigenous wisdom and sacred geometry — processed
                through a Rust-based semantic pipeline (CODEX) that extracts,
                chunks, embeds, and indexes the entire body of work.
              </p>
              <p className="mt-4 leading-relaxed text-muted">
                The distinctive feature is <strong className="text-fg">synthesis
                across domains that don&apos;t normally talk to each other</strong>.
                When a solar physicist, a geopolitical analyst, and an AI
                researcher all point to the same window for unrelated reasons —
                that&apos;s signal. The CODEX pipeline&apos;s convergence detector
                flags these structural resonances for human review.
              </p>
            </div>
            <div>
              <p className="leading-relaxed text-muted">
                On the engineering side, WhiteMagic ships working code: a
                cognitive OS with 487 callable tools, 28 Gana meta-tools,
                persistent holographic memory, and an 8-stage governance
                pipeline — all MIT-licensed with 2,423 passing tests. Every
                technique deployed for clients has been pressure-tested inside
                that codebase first.
              </p>
              <p className="mt-4 leading-relaxed text-muted">
                The convergence research (Convergence 2026, May 2 Window,
                Survival Guide) maps technological, ontological, and esoteric
                thresholds as a single pattern — not as separate domains. The{" "}
                <Link href="/sphere" className="text-lavender hover:underline">
                  3D Knowledge Sphere
                </Link>{" "}
                visualizes all 10,768 semantic nodes from this corpus, and the{" "}
                <Link href="/library" className="text-lavender hover:underline">
                  Research Library
                </Link>{" "}
                provides searchable access to all 371 source files.
              </p>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatBlock label="Research Domains" value="18" />
            <StatBlock label="Source Files" value="371" />
            <StatBlock label="Semantic Nodes" value="10.8K" />
            <StatBlock label="Test Suite" value="2,423" />
          </div>
        </div>

        {/* Active Research */}
        <div className="mb-16">
          <div className="mb-8 flex items-center gap-3">
            <Beaker className="h-5 w-5 text-lavender" />
            <h2 className="font-head text-2xl font-semibold text-ink">
              Active Research
            </h2>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-6 md:p-8">
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <span className="rounded-full bg-lavender-bg px-2.5 py-0.5 text-xs font-medium text-lavender">
                Runtime Audit
              </span>
              <span className="rounded-full bg-lavender-bg px-2.5 py-0.5 text-xs font-medium text-lavender">
                Multi-Agent Safety
              </span>
              <span className="rounded-full bg-lavender-bg px-2.5 py-0.5 text-xs font-medium text-lavender">
                Evaluation Science
              </span>
            </div>

            <h3 className="mb-3 font-head text-xl font-semibold text-ink">
              Karma Ledger: Declaration Fidelity in Agent Tool Use
            </h3>

            <p className="mb-6 max-w-prose leading-relaxed text-muted">
              Current AI safety benchmarks test task success (LoCoMo) or memory
              accuracy (LongMemEval-S), but neither tests whether an agent's
              description of its actions matches reality. Karma Ledger measures
              <strong> side-effect fidelity</strong> — the degree to which
              declared tool-use effects match empirical observations. This is a
              prerequisite for any oversight mechanism in multi-agent systems.
            </p>

            <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard label="Tasks" value="Planned" />
              <StatCard label="Tool categories" value="5" />
              <StatCard label="Model families" value="3" />
              <StatCard label="Validation" value="Planned" />
            </div>

            <div className="flex flex-wrap gap-3">
              <Link href="/open-source" className="btn-primary">
                <ExternalLink className="mr-2 h-4 w-4" />
                Explore the source
              </Link>
              <span className="inline-flex items-center rounded-full bg-surface-alt px-3 py-1.5 text-sm text-muted">
                <FileText className="mr-2 h-4 w-4" />
                arXiv preprint in preparation
              </span>
            </div>
          </div>
        </div>

        {/* Convergence Research */}
        <div className="mb-16">
          <div className="mb-8 flex items-center gap-3">
            <FileText className="h-5 w-5 text-lavender" />
            <h2 className="font-head text-2xl font-semibold text-ink">
              Convergence Research
            </h2>
          </div>

          <p className="mb-6 max-w-prose text-muted">
            Cross-domain analysis mapping technological, ontological, and
            esoteric thresholds. These documents synthesize signals from 18
            research domains into actionable frameworks. See also the{" "}
            <Link href="/library" className="text-lavender hover:underline">
              CODEX Research Library
            </Link>{" "}
            for the full source corpus.
          </p>

          <div className="grid gap-4 md:grid-cols-3">
            <ResearchCard
              title="Convergence 2026"
              tag="The Great Crossroads"
              description="AGI cognitive shift, Fusion energy reset, UAP ontological shock, and the September 23 celestial alignment — mapped as a single phase shift of civilization."
              href="/research/convergence-2026"
              tags={["AGI", "Fusion", "UAP", "Sept 23"]}
            />
            <ResearchCard
              title="May 2 Window"
              tag="The 144-Day Countdown"
              description="Vesta opposition, Contact Modalities XPO, and the precise 144-day mathematical bridge to September 23 — the ignition phase before the revelation."
              href="/research/may-2-window"
              tags={["Vesta", "144 days", "Contact XPO"]}
            />
            <ResearchCard
              title="Survival Guide 2026"
              tag="Practical Resonance"
              description="Mesh networking, micro-generation, skill sovereignty, and the Unix 1,777,777,777 sovereignty moment — autonomy over fear."
              href="/research/survival-guide-2026"
              tags={["Mesh", "Solar", "SDR", "Seeds"]}
            />
          </div>

          <div className="mt-6 rounded-xl border border-border bg-surface p-5">
            <h3 className="mb-3 font-head text-base font-semibold text-ink">
              18 Research Domains
            </h3>
            <div className="flex flex-wrap gap-2">
              {[
                "Astro", "Earth", "Energy & Physics", "FIR & Society",
                "Genetics", "History", "Indigenous Wisdom", "Lost Civ",
                "Magic & the Occult", "Magisters", "Neuromancy", "Philosophy",
                "Prophecies", "Psi", "Sacred Geometry", "Sages & Alchemy",
                "Space", "Spirituality & Healing",
              ].map((domain) => (
                <span
                  key={domain}
                  className="rounded-full bg-surface-alt px-3 py-1 text-xs text-muted"
                >
                  {domain}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="mb-16 rounded-2xl border border-border bg-surface-alt p-6 md:p-8">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="mb-2 font-mono text-xs uppercase tracking-widest text-lavender">
                Field map · updated {FIELD_MAP_UPDATED}
              </p>
              <h2 className="font-head text-2xl font-semibold text-ink">
                Where recent agent infrastructure points WhiteMagic now
              </h2>
            </div>
            <Link
              href="/timeline"
              className="text-sm font-medium text-lavender hover:text-lavender-dark"
            >
              View timeline →
            </Link>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {FIELD_CONCLUSIONS.map((item) => (
              <ConclusionCard key={item.title} {...item} />
            ))}
          </div>

          <div className="mt-8 grid gap-4 lg:grid-cols-3">
            {FIELD_SIGNALS.map((signal) => (
              <SignalCard key={signal.title} signal={signal} />
            ))}
          </div>
        </div>

        <div className="mb-16">
          <div className="mb-8 flex items-center gap-3">
            <FileText className="h-5 w-5 text-lavender" />
            <h2 className="font-head text-2xl font-semibold text-ink">
              Updated roadmap
            </h2>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {ROADMAP_UPDATES.map((block) => (
              <article
                key={block.horizon}
                className="rounded-xl border border-border bg-surface p-5"
              >
                <p className="mb-2 font-mono text-xs uppercase tracking-wider text-lavender">
                  {block.horizon}
                </p>
                <h3 className="mb-3 font-head text-lg font-semibold text-ink">
                  {block.title}
                </h3>
                <ul className="space-y-2 text-sm text-muted">
                  {block.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>

        {/* Publications */}
        <div className="mb-16">
          <div className="mb-8 flex items-center gap-3">
            <FileText className="h-5 w-5 text-lavender" />
            <h2 className="font-head text-2xl font-semibold text-ink">
              Publications
            </h2>
          </div>

          <div className="space-y-6">
            {PUBLICATIONS.map((pub) => (
              <article
                key={pub.title}
                className="rounded-xl border border-border bg-surface p-6"
              >
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <StatusBadge status={pub.status} />
                  {pub.tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full bg-surface-alt px-2 py-0.5 text-xs text-dim"
                    >
                      {tag}
                    </span>
                  ))}
                </div>

                <h3 className="mb-2 font-head text-lg font-semibold text-ink">
                  {pub.title}
                </h3>
                <p className="mb-3 text-sm text-muted">
                  {pub.authors} · {pub.venue} · {pub.year}
                </p>
                <p className="mb-4 max-w-prose text-sm leading-relaxed text-muted">
                  {pub.abstract}
                </p>

                <div className="flex flex-wrap gap-3">
                  {pub.links.map((link) => (
                    <a
                      key={link.label}
                      href={link.href}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center text-sm font-medium text-lavender hover:text-lavender-dark"
                    >
                      {link.label}
                      <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
                    </a>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </div>

        {/* Benchmarks */}
        <div className="mb-16">
          <div className="mb-8 flex items-center gap-3">
            <Beaker className="h-5 w-5 text-lavender" />
            <h2 className="font-head text-2xl font-semibold text-ink">
              Benchmarks
            </h2>
          </div>

          <div className="space-y-6">
            {BENCHMARKS.map((b) => (
              <article
                key={b.name}
                className="rounded-xl border border-border bg-surface p-6"
              >
                <div className="mb-3 flex items-center gap-2">
                  <BenchmarkStatus status={b.status} />
                  <h3 className="font-head text-lg font-semibold text-ink">
                    {b.name}
                  </h3>
                </div>
                <p className="mb-4 max-w-prose text-sm leading-relaxed text-muted">
                  {b.description}
                </p>
                <dl className="mb-4 flex flex-wrap gap-x-8 gap-y-3 border-y border-border-light py-4">
                  {b.metrics.map((m) => (
                    <div key={m.label}>
                      <dt className="text-xs uppercase tracking-wider text-dim">
                        {m.label}
                      </dt>
                      <dd className="font-head text-lg font-semibold text-ink">
                        {m.value}
                      </dd>
                    </div>
                  ))}
                </dl>
                <a
                  href={b.href}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center text-sm font-medium text-lavender hover:text-lavender-dark"
                >
                  View benchmark
                  <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
                </a>
              </article>
            ))}
          </div>
        </div>

        {/* Research Principles */}
        <div className="rounded-2xl border border-border bg-surface-alt p-8">
          <h2 className="mb-4 font-head text-xl font-semibold text-ink">
            Research principles
          </h2>
          <ul className="space-y-3 text-muted">
            <li className="flex gap-3">
              <span className="text-lavender">1.</span>
              <span>
                <strong className="text-fg">Reproducibility first</strong> —
                Every benchmark includes a Docker environment, pinned
                dependencies, and a run script that produces the same numbers on
                any machine.
              </span>
            </li>
            <li className="flex gap-3">
              <span className="text-lavender">2.</span>
              <span>
                <strong className="text-fg">Negative results published</strong>{" "}
                — If a hypothesis fails, we publish the failure and why. This is
                as valuable as a success.
              </span>
            </li>
            <li className="flex gap-3">
              <span className="text-lavender">3.</span>
              <span>
                <strong className="text-fg">Open data, open code</strong> — MIT
                license for code; CC-BY for data. No paywalls, no registration
                gates.
              </span>
            </li>
            <li className="flex gap-3">
              <span className="text-lavender">4.</span>
              <span>
                <strong className="text-fg">Community-validated</strong> —
                Benchmarks are not final until external labs have reproduced the
                results and provided feedback.
              </span>
            </li>
          </ul>
        </div>

        {/* CTA */}
        <div className="mt-16 text-center">
          <h2 className="mb-4 font-head text-2xl font-semibold text-ink">
            Fund this research
          </h2>
          <p className="mx-auto mb-6 max-w-prose text-muted">
            WhiteMagic Labs is a solo-founded research lab with zero institutional
            backing. Every dollar goes directly to open-source infrastructure that
            makes agent behavior more measurable, auditable, and reproducible.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href="/grants" className="btn-primary">
              See funding opportunities
            </Link>
            <Link href="/contact" className="btn-secondary">
              Sponsor this work
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border-light bg-surface-alt p-4 text-center">
      <div className="font-head text-2xl font-semibold text-ink">{value}</div>
      <div className="text-xs uppercase tracking-wider text-dim">{label}</div>
    </div>
  );
}

function ConclusionCard({ title, body }: { title: string; body: string }) {
  return (
    <article className="rounded-xl border border-border bg-surface p-5">
      <h3 className="mb-2 font-head text-lg font-semibold text-ink">
        {title}
      </h3>
      <p className="text-sm leading-relaxed text-muted">{body}</p>
    </article>
  );
}

function SignalCard({ signal }: { signal: (typeof FIELD_SIGNALS)[number] }) {
  return (
    <article className="rounded-xl border border-border-light bg-surface p-5">
      <p className="mb-2 font-mono text-xs uppercase tracking-wider text-lavender">
        {signal.area}
      </p>
      <h3 className="mb-3 font-head text-base font-semibold text-ink">
        {signal.title}
      </h3>
      <div className="space-y-3 text-sm text-muted">
        <p>
          <strong className="text-fg">External:</strong> {signal.external}
        </p>
        <p>
          <strong className="text-fg">WhiteMagic:</strong> {signal.whitemagic}
        </p>
        <p>
          <strong className="text-fg">Conclusion:</strong> {signal.consequence}
        </p>
      </div>
      <a
        href={signal.source.url}
        target="_blank"
        rel="noreferrer"
        className="mt-4 inline-flex items-center text-xs font-medium text-lavender hover:text-lavender-dark"
      >
        {signal.source.label}
        <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
      </a>
    </article>
  );
}

function StatusBadge({ status }: { status: Publication["status"] }) {
  const styles = {
    published: "bg-green-100 text-green-700",
    submitted: "bg-blue-100 text-blue-700",
    "in-prep": "bg-amber-100 text-amber-700",
  };
  const labels = {
    published: "Published",
    submitted: "Submitted",
    "in-prep": "In Preparation",
  };
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}

function BenchmarkStatus({ status }: { status: Benchmark["status"] }) {
  const styles = {
    live: "bg-green-100 text-green-700",
    "in-development": "bg-blue-100 text-blue-700",
    planned: "bg-surface-alt text-muted",
  };
  const labels = {
    live: "Live",
    "in-development": "In Development",
    planned: "Planned",
  };
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}

function ResearchCard({
  title,
  tag,
  description,
  href,
  tags,
}: {
  title: string;
  tag: string;
  description: string;
  href: string;
  tags: string[];
}) {
  return (
    <Link
      href={href}
      className="group flex flex-col rounded-xl border border-border bg-surface p-5 transition hover:border-lavender hover:bg-lavender-bg"
    >
      <p className="mb-1 font-mono text-[10px] uppercase tracking-wider text-lavender">
        {tag}
      </p>
      <h3 className="mb-2 font-head text-lg font-semibold text-ink transition group-hover:text-lavender-dark">
        {title}
      </h3>
      <p className="mb-3 flex-1 text-sm leading-relaxed text-muted">
        {description}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {tags.map((t) => (
          <span
            key={t}
            className="rounded bg-surface-alt px-1.5 py-0.5 font-mono text-[10px] text-dim"
          >
            {t}
          </span>
        ))}
      </div>
    </Link>
  );
}

function StatBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4 text-center">
      <div className="font-head text-2xl font-semibold text-ink">{value}</div>
      <div className="text-xs uppercase tracking-wider text-dim">{label}</div>
    </div>
  );
}
