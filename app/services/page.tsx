import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { ServiceCard } from "@/components/ServiceCard";
import { ArrowRight, Plug, Server, Shield } from "lucide-react";

export const metadata = {
  title: "Services — WhiteMagic Labs",
  description:
    "Private AI deployment, agent governance, and MCP engineering for regulated teams.",
};

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

export default function ServicesPage() {
  return (
    <>
      <PageHeader
        eyebrow="Services"
        title="Three ways we can work together."
        lede="Every engagement starts with a 30-minute discovery call. If I'm not the right fit, I'll say so and try to point you at someone who is."
      />
      <section className="container-site py-16">
        <div className="grid gap-5 md:grid-cols-3">
          {SERVICES.map((s) => (
            <ServiceCard key={s.title} {...s} />
          ))}
        </div>

        <div className="mt-20 rounded-2xl border border-border bg-surface-alt p-8 md:p-12">
          <h2 className="mb-4 font-head text-2xl font-semibold tracking-tight text-ink">
            Not sure which one fits?
          </h2>
          <p className="mb-6 max-w-prose text-muted">
            That&apos;s what the discovery call is for. Tell me what
            you&apos;re trying to build, what constraints you&apos;re under,
            and we&apos;ll figure it out together. No deck, no sales pitch.
          </p>
          <Link href="/contact" className="btn-primary">
            Book a discovery call
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </>
  );
}
