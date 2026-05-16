import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { JsonLd } from "@/components/JsonLd";
import { serviceLd } from "@/lib/jsonld";
import { WM_FACTS, WM_FACT_TEXT } from "@/lib/facts";
import { Prose } from "@/components/Prose";
import { ArrowRight, Check } from "lucide-react";
import { FIELD_MAP_UPDATED, FIELD_SIGNALS } from "@/lib/field-map";

export const metadata = {
  title: "MCP Engineering — WhiteMagic Labs",
  description:
    "Production-grade Model Context Protocol server engineering. Tools, transports, middleware, governance. For teams building serious agent infrastructure.",
};

const CAPABILITIES = [
  "MCP server architecture — stdio and Streamable HTTP transports, stateless or persistent",
  "Tool design with strict schemas, idempotency, stable error codes",
  "Middleware pipelines — auth, rate limiting, audit, sanitization",
  "Multi-server gateways and tool federation",
  "OpenTelemetry-compatible trace design for tools, sessions, and side-effect audit events",
  "Integration with Claude, Cursor, Windsurf, VS Code + Copilot, and custom clients",
  "Performance tuning — sub-second handshakes, streaming responses, connection pooling",
  `Tool compression strategies for large tool catalogs (${WM_FACTS.callableTools} callable-tool deployments)`,
  "Testing, observability, and production runbooks",
];

const FORMATS = [
  {
    title: "Time-and-materials",
    body: "$100–150/hr, typical 10–30 hr/week. Good for teams with an existing backlog who need senior MCP expertise without full-time cost.",
  },
  {
    title: "Fixed-scope sprint",
    body: "$15–40k for a defined deliverable — a production MCP server, a gateway migration, a governance retrofit. 2–6 week window.",
  },
  {
    title: "Retainer",
    body: "$8–15k/month for ongoing architecture review, escalation support, and PR review. Best once a relationship is established.",
  },
];

const MCP_SIGNALS = FIELD_SIGNALS.filter(
  (signal) => signal.area === "Protocols" || signal.area === "Observability",
);

export default function Page() {
  return (
    <>
      <JsonLd data={serviceLd("mcp-engineering")} />
      <PageHeader
        eyebrow="Service · MCP Engineering"
        title="Production-grade MCP, built right the first time."
        lede="Model Context Protocol servers that scale, stay auditable, and don't wake you up at 3am. For teams betting real infrastructure on agent tooling."
      />

      <section className="container-site grid gap-16 py-16 lg:grid-cols-[1.4fr_0.8fr]">
        <Prose>
          <h2>Why this is trickier than it looks</h2>
          <p>
            MCP is no longer just a local bridge for a chat client. The
            protocol surface is moving toward production concerns: Streamable
            HTTP, authorization, registries, load-balanced sessions, and
            enterprise audit expectations. That makes the boring details matter.
          </p>
          <p>
            When an enterprise adopts MCP seriously, all of those become
            visible at once: auth, idempotency, schema drift, unstructured
            errors, observability, tool-catalog bloat, and side effects that no
            one recorded. I&apos;ve already worked through those trade-offs in a
            repository that exposes {WM_FACT_TEXT.mcpSurface}, handshakes in
            under a second, and passes {WM_FACTS.testsPassing} tests.
          </p>

          <h2>How I work with teams</h2>
          <p>
            Three common shapes, pick whatever matches your situation:
          </p>
          <ul>
            {FORMATS.map((f) => (
              <li key={f.title}>
                <strong>{f.title}</strong> — {f.body}
              </li>
            ))}
          </ul>

          <h2>Before we talk</h2>
          <p>
            If you&apos;re in the very early stages — still deciding if
            MCP is the right protocol at all — I&apos;m happy to have
            that conversation, but know that my honest answer is
            sometimes &quot;not yet.&quot; I&apos;m not interested in
            building infrastructure you&apos;ll regret. If your team
            already has working agents and you&apos;re feeling the
            limits, we have a lot to talk about.
          </p>
        </Prose>

        <aside className="space-y-8 lg:sticky lg:top-24 lg:self-start">
          <div className="rounded-2xl border border-border bg-surface p-6">
            <div className="mb-4 font-mono text-xs uppercase tracking-widest text-lavender">
              Field map · {FIELD_MAP_UPDATED}
            </div>
            <ul className="space-y-4 text-sm">
              {MCP_SIGNALS.map((signal) => (
                <li key={signal.title}>
                  <div className="font-medium text-ink">{signal.area}</div>
                  <div className="text-muted">{signal.consequence}</div>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-6">
            <div className="mb-4 font-mono text-xs uppercase tracking-widest text-lavender">
              At a glance
            </div>
            <dl className="space-y-3 text-sm">
              <Row label="Hourly" value="$100–150/hr" />
              <Row label="Fixed sprint" value="$15–40k" />
              <Row label="Retainer" value="$8–15k/mo" />
              <Row label="Stack" value="Python, TypeScript" />
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
              Proof
            </div>
            <p className="text-sm leading-relaxed text-muted">
              Author of WhiteMagic — a {WM_FACTS.linesShort}-line open-source
              MCP platform with {WM_FACTS.callableTools} tools,{" "}
              {WM_FACTS.ganaTools} Gana meta-tools, 8-stage middleware
              pipeline, Rust production accelerators, and a {WM_FACTS.testsPassing}-test
              passing suite (0 failures).
            </p>
            <Link
              href="https://github.com/whitemagic-ai/whitemagic"
              className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-lavender hover:text-lavender-dark"
            >
              GitHub →
            </Link>
          </div>
        </aside>
      </section>

      <section className="border-t border-border-light bg-surface-alt py-16">
        <div className="container-site max-w-3xl">
          <h2 className="mb-8 font-head text-2xl font-semibold tracking-tight text-ink">
            Capabilities
          </h2>
          <ul className="space-y-3">
            {CAPABILITIES.map((item) => (
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
