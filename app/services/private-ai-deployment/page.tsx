import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { Prose } from "@/components/Prose";
import { ArrowRight, Check } from "lucide-react";
import { JsonLd } from "@/components/JsonLd";
import { serviceLd } from "@/lib/jsonld";

export const metadata = {
  title: "Private AI Deployment — WhiteMagic Labs",
  description:
    "Private AI systems deployed on your infrastructure. Persistent memory, tool use, governance, full audit — your data never leaves the building.",
};

const INCLUDED = [
  "Discovery & requirements workshop — map workflows, compliance, and existing stack",
  "Hardware sizing & procurement guidance (or deployment onto your existing infra)",
  "Local model selection, benchmarking, and fine-tuning where useful",
  "Persistent memory layer — holographic memory, multi-tenant galaxies, audit-grade retention",
  "Tool use via Model Context Protocol — integrate 1-2 of your existing systems",
  "Governance middleware — policy engine, audit ledger, RBAC, approval workflows",
  "Operator training — 2 sessions, recorded, documented",
  "30 days of production support after handoff",
];

const GOOD_FIT = [
  "Law firms, M&A advisors, and legal ops teams handling privileged material",
  "Healthcare organizations with PHI / HIPAA constraints",
  "Fintech, family offices, and regulated financial operators",
  "Defense suppliers or teams working with export-controlled information",
  "Any 50–500 person company where \"data never leaves the building\" is non-negotiable",
];

export default function Page() {
  return (
    <>
      <JsonLd data={serviceLd("private-ai-deployment")} />
      <PageHeader
        eyebrow="Service · Private AI Deployment"
        title="AI that lives inside your walls."
        lede="A complete private AI system — persistent memory, tool use, governance, audit — deployed on hardware you own, under compliance rules you already follow."
      />

      <section className="container-site grid gap-16 py-16 lg:grid-cols-[1.4fr_0.8fr]">
        <Prose>
          <h2>The problem</h2>
          <p>
            Hosted LLM APIs are powerful, but for regulated teams they
            create a gap your compliance team can&apos;t close: privileged
            material flowing out to a third-party inference endpoint,
            opaque retention, shared infrastructure, no audit trail.
            Most enterprise AI stops at &quot;summarize this email&quot; because
            anything deeper runs into legal, InfoSec, or both.
          </p>

          <h2>What you get</h2>
          <p>
            A working private AI system running on your infrastructure,
            with the durability features most teams try to bolt on later
            — baked in from day one:
          </p>
          <ul>
            <li>
              <strong>Persistent, searchable memory.</strong> Your AI
              remembers across sessions and projects, with clean isolation
              between workstreams.
            </li>
            <li>
              <strong>Real tool use.</strong> The model can read from and
              write to your systems via the Model Context Protocol,
              with explicit permission scopes per tool.
            </li>
            <li>
              <strong>Governance & audit.</strong> Every action passes
              through a policy engine and lands in an append-only audit
              ledger. You can answer the question &quot;what did the AI
              actually do yesterday?&quot; in one query.
            </li>
            <li>
              <strong>Multi-tenant from day one.</strong> Matters, clients,
              or departments get isolated memory spaces. Cross-contamination
              is not a configuration — it&apos;s impossible by design.
            </li>
          </ul>

          <h2>How I approach it</h2>
          <p>
            The first week is listening. I want to understand what your
            team actually does hour-by-hour before recommending any
            architecture. Most private-AI projects fail because they
            deploy a chatbot when what the team needed was a
            retrieval-and-drafting pipeline that quietly saves two hours
            a day.
          </p>
          <p>
            From there, most engagements follow a shape: two weeks of
            deployment and integration, one week of operator training,
            30 days of hands-on support as real work flows through the
            system. By week 8 you should be running independently, with
            documentation good enough to hand to your own ops team.
          </p>
        </Prose>

        <aside className="space-y-8 lg:sticky lg:top-24 lg:self-start">
          <div className="rounded-2xl border border-border bg-surface p-6">
            <div className="mb-4 font-mono text-xs uppercase tracking-widest text-lavender">
              At a glance
            </div>
            <dl className="space-y-3 text-sm">
              <Row label="Typical engagement" value="Scoped per project" />
              <Row label="Timeline" value="4–8 weeks" />
              <Row label="Hands-on support" value="30 days post-launch" />
              <Row label="Deployment" value="On-prem or your VPC" />
              <Row label="Licensing" value="Open-source core (MIT)" />
            </dl>
            <Link
              href="/contact"
              className="btn-primary mt-6 w-full justify-center"
            >
              Book a call
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-6">
            <div className="mb-4 font-mono text-xs uppercase tracking-widest text-lavender">
              Good fit for
            </div>
            <ul className="space-y-2 text-sm text-muted">
              {GOOD_FIT.map((f) => (
                <li key={f} className="flex gap-2">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-lavender" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </section>

      <section className="border-t border-border-light bg-surface-alt py-16">
        <div className="container-site max-w-3xl">
          <h2 className="mb-8 font-head text-2xl font-semibold tracking-tight text-ink">
            What&apos;s included
          </h2>
          <ul className="space-y-3">
            {INCLUDED.map((item) => (
              <li key={item} className="flex gap-3 text-muted">
                <Check className="mt-1 h-5 w-5 shrink-0 text-lavender" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-muted">{label}</dt>
      <dd className="font-medium text-ink">{value}</dd>
    </div>
  );
}
