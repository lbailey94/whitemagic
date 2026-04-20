import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { Prose } from "@/components/Prose";
import { ArrowRight, Check } from "lucide-react";
import { JsonLd } from "@/components/JsonLd";
import { serviceLd } from "@/lib/jsonld";

export const metadata = {
  title: "Agent Governance — WhiteMagic Labs",
  description:
    "Runtime guardrails for autonomous AI agents. Policy enforcement, identity, audit, approval workflows. Maps to the OWASP Agentic Top 10 and EU AI Act obligations.",
};

const INCLUDED = [
  "Audit of your current agent stack against the OWASP Agentic Top 10",
  "Policy engine — declarative rules, graduated responses, sub-millisecond evaluation",
  "Append-only audit ledger with hash-chained integrity",
  "RBAC — role-scoped capability gating for every agent and tool",
  "Approval workflows for high-autonomy actions with quorum logic",
  "Integration with LangChain, CrewAI, Google ADK, or your existing framework",
  "Compliance evidence packaging for SOC2, HIPAA, and EU AI Act mapping",
  "Operator runbook and incident response procedures",
];

const RISKS = [
  { name: "Goal hijacking", mit: "Intent classifier + policy gates" },
  { name: "Tool misuse", mit: "Capability sandboxing & scope gating" },
  { name: "Identity abuse", mit: "Per-agent identity with trust scoring" },
  { name: "Memory poisoning", mit: "Cross-source verification" },
  { name: "Cascading failures", mit: "Circuit breakers & rate limits" },
  { name: "Rogue agents", mit: "Isolation rings & kill switch" },
];

export default function Page() {
  return (
    <>
      <JsonLd data={serviceLd("agent-governance")} />
      <PageHeader
        eyebrow="Service · Agent Governance"
        title="Guardrails that turn autonomy into trust."
        lede="Runtime governance for AI agents: policy enforcement, identity, audit, and approval workflows. Everything your compliance team will ask for — before they ask."
      />

      <section className="container-site grid gap-16 py-16 lg:grid-cols-[1.4fr_0.8fr]">
        <Prose>
          <h2>Why this matters now</h2>
          <p>
            In December 2025 OWASP published the{" "}
            <strong>Top 10 for Agentic Applications</strong> — the first
            formal risk taxonomy for autonomous agents. In August 2026 the
            EU AI Act&apos;s high-risk obligations take effect. Colorado&apos;s
            AI Act is already enforceable. Every major cloud vendor is
            shipping governance toolkits. The question &quot;who governs
            what your agents do&quot; is no longer optional.
          </p>
          <p>
            Most teams deploying agents have model governance (evals,
            bias testing, red-teaming). Almost none have{" "}
            <strong>agent governance</strong> — the layer between
            &quot;the model is fine&quot; and &quot;the agent has production
            access.&quot; That gap is where incidents happen.
          </p>

          <h2>What I deploy</h2>
          <p>
            A framework-agnostic middleware layer that every agent action
            passes through:
          </p>
          <ul>
            <li>
              <strong>Policy engine</strong> — declarative rules evaluated
              at agent runtime with deterministic, sub-millisecond latency
            </li>
            <li>
              <strong>Audit ledger</strong> — every action, with inputs,
              outputs, policy verdicts, and agent identity, hash-chained
              so tampering is detectable
            </li>
            <li>
              <strong>Approval workflows</strong> — high-autonomy actions
              route to human reviewers with configurable quorum rules
            </li>
            <li>
              <strong>Identity & trust</strong> — every agent has a signed
              identity; trust decays on violations and recovers on clean
              operation
            </li>
            <li>
              <strong>Kill switch</strong> — single-operator action to
              halt all agents, isolate specific ones, or roll back to a
              known-good state
            </li>
          </ul>

          <h2>Why me, specifically</h2>
          <p>
            I built this layer — Dharma rules engine, Karma audit ledger,
            eight-stage middleware pipeline — inside WhiteMagic starting
            in late 2025. That&apos;s months before Microsoft released
            their Agent Governance Toolkit and before the OWASP list
            existed. You get a consultant who has already walked the
            design trade-offs on his own time, on his own dime.
          </p>
          <p>
            For teams already committed to Microsoft&apos;s toolkit,
            Databricks Unity AI Gateway, or similar: I can integrate with
            and extend those rather than replace them. The goal is
            governance that works, not governance with my name on it.
          </p>
        </Prose>

        <aside className="space-y-8 lg:sticky lg:top-24 lg:self-start">
          <div className="rounded-2xl border border-border bg-surface p-6">
            <div className="mb-4 font-mono text-xs uppercase tracking-widest text-lavender">
              At a glance
            </div>
            <dl className="space-y-3 text-sm">
              <Row label="Typical engagement" value="$10–30k" />
              <Row label="Timeline" value="3–6 weeks" />
              <Row label="Framework" value="LangChain, CrewAI, ADK, custom" />
              <Row label="Deployment" value="Your infra or ours" />
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
              OWASP Agentic Top 10 coverage
            </div>
            <ul className="space-y-3 text-sm">
              {RISKS.map((r) => (
                <li key={r.name}>
                  <div className="font-medium text-ink">{r.name}</div>
                  <div className="text-muted">{r.mit}</div>
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
