import { Hero } from "@/components/Hero";
import { ServiceCard } from "@/components/ServiceCard";
import { FIELD_CONCLUSIONS, FIELD_MAP_UPDATED } from "@/lib/field-map";
import { WM_FACTS, WM_FACT_TEXT } from "@/lib/facts";
import { Server, Shield, Plug } from "lucide-react";

const SERVICES = [
  {
    icon: Server,
    title: "Private AI Deployment",
    blurb:
      "Local or on-prem AI with persistent memory, tool use, and multi-tenant isolation. Your data stays on your hardware, under your compliance regime.",
    priceHint: "Engagement · $15–50k",
    href: "/services/private-ai-deployment",
  },
  {
    icon: Shield,
    title: "Agent Governance",
    blurb:
      "Runtime guardrails for autonomous agents: policy enforcement, identity, audit, approval workflows. Addresses the OWASP LLM Top 10 (v1.1, covers agentic AI).",
    priceHint: "Engagement · $10–30k",
    href: "/services/agent-governance",
  },
  {
    icon: Plug,
    title: "MCP Engineering",
    blurb:
      "Production-grade Model Context Protocol servers — tools, transports, middleware, and governance. For teams building serious agent infrastructure.",
    priceHint: "Contract · $100–150/hr",
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
              The market standardized transport. WhiteMagic focuses on evidence.
            </h2>
            <p className="mt-4 text-muted">
              MCP, A2A, OpenAI Agents, OpenTelemetry, x402, and the EU AI Act
              all point in the same direction: teams need governed agents whose
              actions can be constrained, traced, and explained.
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
            Consulting where the research meets production.
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
              I built the lab before I offered the service.
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
              made the expensive mistakes on his own time.
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              <a href="/timeline" className="btn-primary">
                See the timeline →
              </a>
              <a
                href="https://github.com/whitemagic-ai/whitemagic"
                className="btn-ghost"
                target="_blank"
                rel="noreferrer"
              >
                View on GitHub
              </a>
            </div>
          </div>
        </div>
      </section>

      <section className="container-site py-24">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="mb-5 font-head text-3xl font-semibold tracking-tight text-ink md:text-4xl">
            Ready to make agent behavior auditable?
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
