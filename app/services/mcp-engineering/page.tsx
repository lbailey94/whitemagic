import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { Prose } from "@/components/Prose";
import { ArrowRight, Check } from "lucide-react";

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
  "Integration with Claude, Cursor, Windsurf, VS Code + Copilot, and custom clients",
  "Performance tuning — sub-second handshakes, streaming responses, connection pooling",
  "Tool compression strategies for large tool catalogs (375+ tool deployments)",
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

export default function Page() {
  return (
    <>
      <PageHeader
        eyebrow="Service · MCP Engineering"
        title="Production-grade MCP, built right the first time."
        lede="Model Context Protocol servers that scale, stay auditable, and don't wake you up at 3am. For teams betting real infrastructure on agent tooling."
      />

      <section className="container-site grid gap-16 py-16 lg:grid-cols-[1.4fr_0.8fr]">
        <Prose>
          <h2>Why this is trickier than it looks</h2>
          <p>
            MCP is new enough that most servers in production right now
            are hobby-grade. They work until they don&apos;t: auth is a
            single shared key, tools aren&apos;t idempotent, errors are
            unstructured strings, nothing is audited, and every Claude
            session starts by paying 30 seconds of handshake tax because
            the server loads the world on boot.
          </p>
          <p>
            When an enterprise adopts MCP seriously, all of those become
            visible at once. I&apos;ve already made those mistakes — on
            my own time, in my own repository, with a server that now
            exposes 374 tools across 28 categories, handshakes in under
            a second, and passes 1,300+ tests. That&apos;s the muscle
            memory you get.
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
              Author of WhiteMagic — a 170K-line open-source MCP server
              with 374 tools, 28 meta-categories, 8-stage middleware
              pipeline, 11-language polyglot stack, and a passing test
              suite.
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
