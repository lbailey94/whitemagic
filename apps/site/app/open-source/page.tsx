import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { FIELD_CONCLUSIONS, FIELD_MAP_UPDATED } from "@/lib/field-map";
import { WM_FACTS, WM_FACT_TEXT } from "@/lib/facts";
import { Github, ExternalLink } from "lucide-react";

export const metadata = {
  title: "Open Source — WhiteMagic Labs",
  description:
    "Open-source work: WhiteMagic cognitive OS, agent-guardrails governance middleware, and supporting libraries.",
};

interface Project {
  name: string;
  tagline: string;
  description: string;
  stats: { label: string; value: string }[];
  status: "Active" | "Planned" | "Paused";
  href: string;
  license: string;
}

const PROJECTS: Project[] = [
  {
    name: "WhiteMagic",
    tagline: "Cognitive operating system for AI agents",
    description:
      `A ${WM_FACTS.linesShort}-line polyglot platform: persistent 5D holographic memory, ${WM_FACT_TEXT.toolSurface}, 8-stage governance pipeline, ${WM_FACTS.languages} verified polyglot languages (Rust/Go/Zig/Koka/Haskell/Elixir/Julia). The lab where every technique used in client engagements gets pressure-tested first.`,
    stats: [
      { label: "Lines", value: WM_FACTS.linesShort },
      { label: "Callable tools", value: WM_FACTS.callableTools },
      { label: "Tests passing", value: WM_FACTS.testsPassing },
      { label: "Languages", value: WM_FACTS.languages },
    ],
    status: "Active",
    href: "https://github.com/whitemagic-ai/whitemagic",
    license: "MIT",
  },
  {
    name: "agent-guardrails",
    tagline: "Runtime governance middleware for AI agents",
    description:
      "A focused extraction of the governance layer from WhiteMagic. Policy engine, append-only audit ledger, RBAC, approval workflows, kill switch. Framework-agnostic — drops into LangChain, CrewAI, Google ADK, or custom stacks. Addresses the OWASP LLM Top 10 (v1.1, covers agentic AI) with deterministic, sub-millisecond policy evaluation.",
    stats: [
      { label: "Target size", value: "~2K lines" },
      { label: "OWASP Top 10", value: "10/10" },
      { label: "Language", value: "Python" },
    ],
    status: "Planned",
    href: "https://github.com/whitemagic-ai",
    license: "MIT",
  },
];

export default function OpenSourcePage() {
  return (
    <>
      <PageHeader
        eyebrow="Open Source"
        title="Reference implementation first. Services second."
        lede="WhiteMagic is the public substrate behind the lab's claims: memory, tool governance, side-effect audit, and protocol-compatible agent infrastructure."
      />

      <section className="container-site py-16">
        <div className="space-y-6">
          {PROJECTS.map((p) => (
            <ProjectCard key={p.name} project={p} />
          ))}
        </div>

        <div className="mt-16 rounded-2xl border border-border bg-surface-alt p-8">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            2026 field map · updated {FIELD_MAP_UPDATED}
          </p>
          <h2 className="mb-5 font-head text-xl font-semibold text-ink">
            Why this remains open source
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            {FIELD_CONCLUSIONS.slice(0, 2).map((item) => (
              <article
                key={item.title}
                className="rounded-xl border border-border bg-surface p-5"
              >
                <h3 className="mb-2 font-head text-lg font-semibold text-ink">
                  {item.title}
                </h3>
                <p className="text-sm leading-relaxed text-muted">{item.body}</p>
              </article>
            ))}
          </div>
        </div>

        <div className="mt-16 rounded-2xl border border-border bg-surface-alt p-8">
          <h2 className="mb-3 font-head text-xl font-semibold text-ink">
            Why open source?
          </h2>
          <p className="max-w-prose text-muted">
            Because when I show up to a discovery call, you&apos;ve already
            been able to read the code. Because the governance and
            memory patterns I sell are more useful in the world than in
            my repository. Because I&apos;d rather compete on execution
            and honesty than on artificial scarcity.
          </p>
          <Link
            href="/contact"
            className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-lavender hover:text-lavender-dark"
          >
            Want to use this in your org? Let&apos;s talk →
          </Link>
        </div>
      </section>
    </>
  );
}

function ProjectCard({ project }: { project: Project }) {
  const statusStyles = {
    Active: "bg-lavender-bg text-lavender",
    Planned: "bg-surface-alt text-muted",
    Paused: "bg-surface-alt text-dim",
  };

  return (
    <article className="rounded-2xl border border-border bg-surface p-6 md:p-8">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Github className="h-5 w-5 text-muted" />
        <h3 className="font-head text-2xl font-semibold text-ink">
          {project.name}
        </h3>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusStyles[project.status]}`}
        >
          {project.status}
        </span>
        <span className="font-mono text-xs uppercase tracking-wider text-dim">
          {project.license}
        </span>
      </div>
      <p className="mb-3 font-head text-lg text-ink">{project.tagline}</p>
      <p className="mb-6 max-w-prose text-muted">{project.description}</p>

      <dl className="mb-6 flex flex-wrap gap-x-8 gap-y-3 border-y border-border-light py-4">
        {project.stats.map((s) => (
          <div key={s.label}>
            <dt className="text-xs uppercase tracking-wider text-dim">
              {s.label}
            </dt>
            <dd className="font-head text-lg font-semibold text-ink">
              {s.value}
            </dd>
          </div>
        ))}
      </dl>

      <a
        href={project.href}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-2 text-sm font-medium text-lavender hover:text-lavender-dark"
      >
        View on GitHub
        <ExternalLink className="h-3.5 w-3.5" />
      </a>
    </article>
  );
}
