import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
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
      "A 170K-line polyglot platform: persistent holographic memory, 374 MCP tools across 28 categories, 8-stage governance pipeline, 11 languages with Rust and Zig acceleration. The lab where every technique used in client engagements gets pressure-tested first.",
    stats: [
      { label: "Lines", value: "170K" },
      { label: "MCP tools", value: "374" },
      { label: "Tests passing", value: "1,318" },
      { label: "Languages", value: "11" },
    ],
    status: "Active",
    href: "https://github.com/whitemagic-ai/whitemagic",
    license: "MIT",
  },
  {
    name: "agent-guardrails",
    tagline: "Runtime governance middleware for AI agents",
    description:
      "A focused extraction of the governance layer from WhiteMagic. Policy engine, append-only audit ledger, RBAC, approval workflows, kill switch. Framework-agnostic — drops into LangChain, CrewAI, Google ADK, or custom stacks. Addresses the OWASP Agentic Top 10 with deterministic, sub-millisecond policy evaluation.",
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
        title="Everything I can share, I share."
        lede="The work behind the services. MIT-licensed, publicly audit-able, and the first-party source for every technique I deploy in engagements."
      />

      <section className="container-site py-16">
        <div className="space-y-6">
          {PROJECTS.map((p) => (
            <ProjectCard key={p.name} project={p} />
          ))}
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
