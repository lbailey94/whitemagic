import { Hero } from "@/components/Hero";
import { ServiceCard } from "@/components/ServiceCard";
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
      "Runtime guardrails for autonomous agents: policy enforcement, identity, audit, approval workflows. Addresses the OWASP Agentic Top 10.",
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

      <section className="container-site py-20">
        <div className="mb-12 max-w-prose">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            What I do
          </p>
          <h2 className="font-head text-3xl font-semibold tracking-tight text-ink md:text-4xl">
            Three ways we can work together.
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
              <strong className="text-fg">WhiteMagic</strong> is a 170,000-line
              open-source cognitive OS for AI agents — 374 MCP tools, 11
              languages, persistent holographic memory, an 8-stage governance
              pipeline, and 1,318 passing tests. I designed, built, and shipped
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
            Ready for AI that lives inside your walls?
          </h2>
          <p className="mb-8 text-lg text-muted">
            Thirty-minute discovery call. No pitch deck, no pressure — just a
            conversation about what you&apos;re trying to build and whether
            I&apos;m the right person to help.
          </p>
          <a href="/contact" className="btn-primary">
            Book a discovery call →
          </a>
        </div>
      </section>
    </>
  );
}
