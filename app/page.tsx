import { Hero } from "@/components/Hero";
import { ServiceCard } from "@/components/ServiceCard";
import { FIELD_CONCLUSIONS, FIELD_MAP_UPDATED } from "@/lib/field-map";
import { WM_FACTS, WM_FACT_TEXT } from "@/lib/facts";
import { Server, Shield, Plug, Globe } from "lucide-react";
import Link from "next/link";

const SERVICES = [
  {
    icon: Server,
    title: "Private AI Deployment",
    blurb:
      "Local or on-prem AI with persistent memory, tool use, and multi-tenant isolation. Your data stays on your hardware, under your compliance regime.",
    href: "/services/private-ai-deployment",
  },
  {
    icon: Shield,
    title: "Agent Governance",
    blurb:
      "Runtime guardrails for autonomous agents: policy enforcement, identity, audit, approval workflows. Addresses the OWASP LLM Top 10 (v1.1, covers agentic AI).",
    href: "/services/agent-governance",
  },
  {
    icon: Plug,
    title: "MCP Governance & Scale",
    blurb:
      "MCP governance, tool compression, and observability at scale. For teams with 10+ servers who need audit, compression, and middleware — not another tutorial.",
    href: "/services/mcp-engineering",
  },
];

export default function HomePage() {
  return (
    <>
      <Hero />

      <section className="border-b border-border-light bg-surface-alt py-16">
        <div className="container-site grid gap-8 md:grid-cols-[0.9fr_1.4fr]">
          <div>
            <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
              2026 field map · updated {FIELD_MAP_UPDATED}
            </p>
            <h2 className="font-head text-3xl font-semibold tracking-tight text-ink">
              The lab saw the pattern before the market named it.
            </h2>
            <p className="mt-4 text-muted">
              MCP, A2A, OpenAI Agents, OpenTelemetry, x402, and the EU AI Act
              all converged on the same pattern: agents need memory, governance,
              and audit. WhiteMagic had working implementations of each before
              the standards existed.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {FIELD_CONCLUSIONS.map((item) => (
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
      </section>

      <section className="container-site py-20">
        <div className="mb-12 max-w-prose">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            Applied work
          </p>
          <h2 className="font-head text-3xl font-semibold tracking-tight text-ink md:text-4xl">
            Lab output: working systems, not position papers.
          </h2>
        </div>
        <div className="grid gap-5 md:grid-cols-3">
          {SERVICES.map((s) => (
            <ServiceCard key={s.title} {...s} />
          ))}
        </div>
      </section>

      <section className="border-y border-border-light bg-surface-alt py-20">
        <div className="container-site grid gap-10 md:grid-cols-[1fr_1.2fr]">
          <div>
            <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
              Proof
            </p>
            <h2 className="font-head text-3xl font-semibold tracking-tight text-ink md:text-4xl">
              I built the prescience engine before anyone asked for it.
            </h2>
          </div>
          <div className="space-y-5 text-muted">
            <p className="leading-relaxed">
              <strong className="text-fg">WhiteMagic</strong> is a{" "}
              {WM_FACTS.linesLong}-line open-source cognitive OS for AI agents —{" "}
              {WM_FACT_TEXT.toolSurface}, polyglot architecture with
              Rust production accelerators, persistent
              holographic memory, an 8-stage governance pipeline, and{" "}
              {WM_FACT_TEXT.shortPassingSuite} (verified{" "}
              {WM_FACTS.verifiedDate}). I designed, built, and shipped
              it solo.
            </p>
            <p className="leading-relaxed">
              Every technique I deploy for clients has been pressure-tested
              inside that codebase first. You get a consultant who has already
              made the expensive mistakes on my own time.
            </p>
            <p className="leading-relaxed">
              Behind the code is a cross-domain research program — 18 domains,
              371 source files, processed through a Rust semantic pipeline into
              a{" "}
              <a
                href="/sphere"
                className="text-lavender hover:underline"
              >
                3D Knowledge Sphere
              </a>{" "}
              of 10,768 interconnected nodes. The convergence analysis (AGI,
              Fusion, UAP, celestial alignments) maps thresholds most people
              treat as separate into a single pattern. See the{" "}
              <a
                href="/research"
                className="text-lavender hover:underline"
              >
                research
              </a>{" "}
              or browse the{" "}
              <a
                href="/library"
                className="text-lavender hover:underline"
              >
                library
              </a>
              .
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              <a href="/timeline" className="btn-primary">
                See the timeline →
              </a>
              <a href="/open-source" className="btn-ghost">
                Explore the source →
              </a>
            </div>
          </div>
        </div>
      </section>

      <section className="border-b border-border-light bg-surface-alt py-20">
        <div className="container-site grid gap-10 md:grid-cols-[1fr_1.2fr]">
          <div>
            <div className="mb-3 flex items-center gap-3">
              <Globe className="h-5 w-5 text-lavender" />
              <p className="font-mono text-xs uppercase tracking-widest text-lavender">
                Knowledge Sphere
              </p>
            </div>
            <h2 className="font-head text-3xl font-semibold tracking-tight text-ink md:text-4xl">
              10,768 nodes. One pattern.
            </h2>
            <p className="mt-4 text-muted">
              The CODEX pipeline processes the entire research corpus — 371
              library files, AI conversations, and 18 research domains — into a
              semantic knowledge graph you can explore in 3D.
            </p>
          </div>
          <div className="flex items-center justify-center">
            <Link
              href="/sphere"
              className="group flex flex-col items-center rounded-2xl border border-border bg-surface p-8 text-center transition hover:border-lavender hover:bg-lavender-bg"
            >
              <Globe className="mb-4 h-12 w-12 text-lavender transition group-hover:scale-110" />
              <h3 className="mb-2 font-head text-xl font-semibold text-ink">
                Explore the Sphere
              </h3>
              <p className="text-sm text-muted">
                Drag to rotate · Scroll to zoom · Hover for details
              </p>
              <span className="mt-4 font-mono text-xs uppercase tracking-wider text-lavender transition group-hover:text-lavender-dark">
                Open visualization →
              </span>
            </Link>
          </div>
        </div>
      </section>

      <section className="container-site py-24">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="mb-5 font-head text-3xl font-semibold tracking-tight text-ink md:text-4xl">
            Ready to see what's coming?
          </h2>
          <p className="mb-8 text-lg text-muted">
            Thirty-minute conversation. No pitch deck, no pressure — just a
            grounded look at what you&apos;re building and whether this lab&apos;s
            patterns can help.
          </p>
          <a href="/contact" className="btn-primary">
            Start a conversation →
          </a>
        </div>
      </section>
    </>
  );
}
