import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { Heart, Gift, ArrowRight, Server, Shield, Plug } from "lucide-react";
import { WM_FACTS } from "@/lib/facts";

export const metadata = {
  title: "Economy & Services — WhiteMagic",
  description: "Free and open source (MIT). Gratitude-driven economics. Optional enterprise services for private AI deployment, agent governance, and MCP engineering.",
};

const SERVICES = [
  {
    icon: Server,
    title: "Private AI Deployment",
    blurb:
      "Local or on-prem AI with persistent memory, tool use, and multi-tenant isolation. Your data stays on your hardware, under your compliance regime. We help you run it, not rent it to you.",
  },
  {
    icon: Shield,
    title: "Agent Governance",
    blurb:
      "Runtime guardrails for autonomous agents: policy enforcement, identity, audit, approval workflows. Addresses the OWASP LLM Top 10 (v1.1, covers agentic AI) with evidence your team can inspect.",
  },
  {
    icon: Plug,
    title: "MCP Governance & Scale",
    blurb:
      "MCP governance, tool compression, and observability at scale. For teams with 10+ servers who need audit, compression, and middleware — not another tutorial, and not a black box.",
  },
];

export default function EconomyPage() {
  return (
    <>
      <PageHeader
        eyebrow="Economy & Services"
        title="Free as in freedom. Funded by gratitude."
        lede="WhiteMagic is MIT-licensed and free to use. No SaaS tier, no telemetry, no API keys. If it helps you build something, you can support the work — or not. No gatekeeping."
      />

      <section className="container-site py-12">
        <div className="mx-auto max-w-4xl space-y-12">
          {/* The model — single large panel */}
          <div className="rounded-2xl border border-border bg-surface p-8 md:p-12">
            <h2 className="mb-6 font-head text-2xl font-semibold text-ink">The economic model</h2>
            <div className="grid gap-8 md:grid-cols-3">
              <div>
                <div className="mb-3 flex items-center gap-2">
                  <Gift className="h-5 w-5 text-lavender" />
                  <h3 className="font-medium text-ink">Free</h3>
                </div>
                <p className="text-sm leading-relaxed text-muted">
                  {WM_FACTS.callableTools} tools. {WM_FACTS.memories} memories. {WM_FACTS.testsPassing} tests. MIT-licensed. pip install whitemagic[mcp]. No strings. Unlimited memories. All features. Forever.
                </p>
              </div>
              <div>
                <div className="mb-3 flex items-center gap-2">
                  <Heart className="h-5 w-5 text-lavender" />
                  <h3 className="font-medium text-ink">Gratitude</h3>
                </div>
                <p className="text-sm leading-relaxed text-muted">
                  Voluntary contributions via GitHub Sponsors, PayPal, or crypto. No tiers, no perks, no gatekeeping. x402 micropayments for AI agents. XRPL tip jar for humans.
                </p>
              </div>
              <div>
                <div className="mb-3 flex items-center gap-2">
                  <ArrowRight className="h-5 w-5 text-lavender" />
                  <h3 className="font-medium text-ink">Enterprise</h3>
                </div>
                <p className="text-sm leading-relaxed text-muted">
                  Custom deployment, integration, and support. Multi-user galaxy isolation, Redis real-time sync, per-user SQLite namespaces. Contact directly. No SLA templates, just real work.
                </p>
              </div>
            </div>
          </div>

          {/* Why not SaaS — single large panel */}
          <div className="rounded-2xl border border-border bg-surface p-8 md:p-12">
            <h2 className="mb-4 font-head text-2xl font-semibold text-ink">Why not SaaS?</h2>
            <div className="space-y-4 text-muted">
              <p>
                WhiteMagic is local-first. Your AI&apos;s memory lives on your machine, not in our cloud.
                A SaaS model would require us to host your data — which defeats the entire premise.
              </p>
              <p>
                The techniques in WhiteMagic (holographic memory, Dharma governance, citta stream)
                are research outputs. They should be available to everyone, not gated behind a
                subscription. MIT license ensures that.
              </p>
              <p>
                If you need help deploying, integrating, or customizing WhiteMagic for your
                use case, that&apos;s where enterprise engagement comes in. The code is free;
                the expertise is not.
              </p>
            </div>
          </div>

          {/* Services — single large panel with inline content */}
          <div className="rounded-2xl border border-border bg-surface p-8 md:p-12">
            <h2 className="mb-2 font-head text-2xl font-semibold text-ink">Enterprise services</h2>
            <p className="mb-8 text-sm text-muted">
              Every engagement starts with a 30-minute conversation. The center of gravity is evidence: policy, audit, observability, and deployment choices your team can defend. If the fit is not right, we&apos;ll say so.
            </p>
            <div className="space-y-8">
              {SERVICES.map((s) => (
                <div key={s.title} className="border-l-2 border-lavender/30 pl-6">
                  <div className="mb-2 flex items-center gap-3">
                    <s.icon className="h-5 w-5 text-lavender" />
                    <h3 className="font-head text-lg font-semibold text-ink">{s.title}</h3>
                  </div>
                  <p className="text-sm leading-relaxed text-muted">{s.blurb}</p>
                </div>
              ))}
            </div>
            <div className="mt-8">
              <Link href="/contact" className="btn-primary">
                Start a conversation
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>

          {/* Funding channels — single large panel */}
          <div className="rounded-2xl border border-border bg-surface p-8 md:p-12">
            <h2 className="mb-6 font-head text-2xl font-semibold text-ink">Support the work</h2>
            <div className="grid gap-6 md:grid-cols-2">
              <a
                href="https://github.com/sponsors/lbailey94"
                className="group rounded-xl border border-border bg-surface-alt p-6 transition hover:border-lavender"
              >
                <h3 className="mb-2 font-head text-lg font-semibold text-ink">GitHub Sponsors</h3>
                <p className="text-sm text-muted">Recurring or one-time. Directly supports development.</p>
                <span className="mt-3 inline-flex items-center gap-1 text-sm text-lavender">
                  Sponsor → <ArrowRight className="h-3 w-3" />
                </span>
              </a>
              <Link
                href="/fund"
                className="group rounded-xl border border-border bg-surface-alt p-6 transition hover:border-lavender"
              >
                <h3 className="mb-2 font-head text-lg font-semibold text-ink">Other channels</h3>
                <p className="text-sm text-muted">PayPal, crypto, XRPL, and other ways to support.</p>
                <span className="mt-3 inline-flex items-center gap-1 text-sm text-lavender">
                  See all options → <ArrowRight className="h-3 w-3" />
                </span>
              </Link>
            </div>
          </div>

          {/* CTA */}
          <div className="rounded-2xl border border-border-light bg-surface-alt p-8 text-center md:p-12">
            <h2 className="mb-3 font-head text-lg font-semibold text-ink">Use it first. Pay if it helps.</h2>
            <p className="mb-6 text-sm text-muted">
              No demos, no sales calls, no &quot;book a meeting to see pricing.&quot; Install it. Try it. If it works for you, support the work.
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <Link href="/mcp-bridge" className="btn-primary">Get Started →</Link>
              <Link href="/contact" className="btn-ghost">Contact</Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
