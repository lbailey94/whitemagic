import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { ServiceCard } from "@/components/ServiceCard";
import { WipGuard } from "@/components/WipGuard";
import { ArrowRight, Plug, Server, Shield } from "lucide-react";
import { FIELD_CONCLUSIONS, FIELD_MAP_UPDATED } from "@/lib/field-map";

export const metadata = {
  title: "Services — WhiteMagic Labs",
  description:
    "Private AI deployment, agent governance, and MCP engineering for teams turning agent autonomy into auditable infrastructure.",
};

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

export default function ServicesPage() {
  return (
    <WipGuard>
      <PageHeader
        eyebrow="Services"
        title="Governed agent infrastructure, built from shipped code."
        lede="Every engagement starts with a 30-minute discovery call. The center of gravity is evidence: policy, audit, observability, and deployment choices your team can defend."
      />
      <section className="container-site py-16">
        <div className="grid gap-5 md:grid-cols-3">
          {SERVICES.map((s) => (
            <ServiceCard key={s.title} {...s} />
          ))}
        </div>

        <div className="mt-20 rounded-2xl border border-border bg-surface-alt p-8 md:p-12">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            2026 field map · updated {FIELD_MAP_UPDATED}
          </p>
          <h2 className="mb-6 font-head text-2xl font-semibold tracking-tight text-ink">
            What changed in the market
          </h2>
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
    </WipGuard>
  );
}
