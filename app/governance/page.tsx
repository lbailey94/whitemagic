import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { Prose } from "@/components/Prose";
import { Shield, Scale, AlertTriangle, FileCheck, GitBranch, Lock } from "lucide-react";

export const metadata = {
  title: "Governance — WhiteMagic",
  description: "Dharma rules engine, Karma ledger, 8-stage dispatch pipeline. Ethical governance for AI agents — graduated actions, hash-chained auditing, RBAC, rate limiting, circuit breakers.",
};

const PIPELINE_STAGES = [
  { name: "Input Sanitizer", description: "Strip injection attempts, validate schemas, normalize encoding" },
  { name: "Circuit Breaker", description: "Track failure rates, open on threshold, auto-recovery" },
  { name: "Rate Limiter", description: "Token bucket per tool, per user, per session" },
  { name: "RBAC", description: "Role-based access control with permission profiles" },
  { name: "Maturity Gate", description: "Check agent maturity stage before allowing advanced operations" },
  { name: "Governor", description: "Dharma rules evaluation — LOG, TAG, WARN, THROTTLE, BLOCK" },
  { name: "Handler", description: "Execute the tool with sanitized, authorized, governed input" },
  { name: "Compact Response", description: "Envelope the result, record to Karma ledger, emit telemetry" },
];

const DHARMA_ACTIONS = [
  { level: "LOG", description: "Record the call, take no action. Default for all operations." },
  { level: "TAG", description: "Annotate the memory with a governance tag for future reference." },
  { level: "WARN", description: "Emit a warning to the agent and the audit log." },
  { level: "THROTTLE", description: "Reduce the agent's rate limit for this tool." },
  { level: "BLOCK", description: "Refuse the call entirely. Record to Karma ledger as a violation." },
];

export default function GovernancePage() {
  return (
    <>
      <PageHeader
        eyebrow="Governance"
        title="Dharma. Karma. Harmony."
        lede="Every tool call passes through an 8-stage pipeline. Every side effect is hash-chained to a Karma ledger. Every policy is YAML-driven and hot-reloadable. Consent is the default."
      />

      <section className="container-site py-12">
        <div className="mx-auto max-w-4xl">
          {/* 8-stage pipeline */}
          <h2 className="mb-6 font-head text-2xl font-semibold text-ink">8-Stage Dispatch Pipeline</h2>
          <p className="mb-8 text-sm text-muted">
            Every single tool call — all 860 of them — passes through these 8 stages. No shortcuts, no bypasses.
          </p>
          <div className="mb-12 space-y-3">
            {PIPELINE_STAGES.map((stage, i) => (
              <div key={stage.name} className="flex items-start gap-4 rounded-lg border border-border bg-surface p-4">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-lavender font-mono text-sm font-bold text-white">
                  {i + 1}
                </div>
                <div>
                  <h3 className="font-medium text-ink">{stage.name}</h3>
                  <p className="text-sm text-muted">{stage.description}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Dharma rules */}
          <h2 className="mb-6 font-head text-2xl font-semibold text-ink">Dharma Rules Engine</h2>
          <p className="mb-6 text-sm text-muted">
            YAML-driven policy with graduated actions. Hot-reloadable — update rules without restarting the server.
          </p>
          <div className="mb-12 grid gap-4 md:grid-cols-2">
            {DHARMA_ACTIONS.map((action) => (
              <div key={action.level} className="rounded-lg border border-border bg-surface p-4">
                <div className="mb-1 font-mono text-sm font-bold text-lavender">{action.level}</div>
                <p className="text-sm text-muted">{action.description}</p>
              </div>
            ))}
          </div>

          {/* Karma ledger */}
          <h2 className="mb-6 font-head text-2xl font-semibold text-ink">Karma Ledger</h2>
          <div className="mb-12 rounded-xl border border-border bg-surface p-6">
            <p className="mb-4 text-sm text-muted">
              Every tool call's side effects are recorded in an append-only, hash-chained ledger.
              Each entry links to the previous one via SHA-256, creating a tamper-evident audit trail.
            </p>
            <pre className="rounded-lg border border-border-light bg-ink p-4 text-xs text-surface font-mono overflow-x-auto">
{`{
  "entry_id": 4207,
  "timestamp": "2026-07-03T20:34:27.141Z",
  "tool": "create_memory",
  "action": "LOG",
  "hash": "sha256(prev_hash + entry_data)",
  "prev_hash": "a1b2c3...",
  "agent_id": "aria",
  "dharma_profile": "standard"
}`}
            </pre>
          </div>

          {/* Harmony Vector */}
          <h2 className="mb-6 font-head text-2xl font-semibold text-ink">Harmony Vector</h2>
          <p className="mb-6 text-sm text-muted">
            7-dimension health metric that tracks system balance:
          </p>
          <ul className="mb-12 space-y-2 text-sm text-muted">
            <li><strong className="text-ink">Safety</strong> — no blocked calls, no violations</li>
            <li><strong className="text-ink">Performance</strong> — latency within bounds</li>
            <li><strong className="text-ink">Coherence</strong> — memory consistency across galaxies</li>
            <li><strong className="text-ink">Coverage</strong> — tool surface utilization</li>
            <li><strong className="text-ink">Calibration</strong> — prediction accuracy</li>
            <li><strong className="text-ink">Maturity</strong> — agent development stage</li>
            <li><strong className="text-ink">Consent</strong> — all operations authorized</li>
          </ul>

          {/* CTA */}
          <div className="rounded-xl border border-border-light bg-surface-alt p-8 text-center">
            <h3 className="mb-3 font-head text-lg font-semibold text-ink">Explore the governance code</h3>
            <p className="mb-6 text-sm text-muted">
              Dharma rules, Karma ledger, and the full 8-stage pipeline are all in the open-source repo.
            </p>
            <Link
              href="https://github.com/lbailey94/whitemagic/tree/main/core/whitemagic/core/governance"
              className="btn-primary inline-flex"
            >
              Browse governance source →
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
