import { PageHeader } from "@/components/PageHeader";
import { getBudget } from "@/lib/librarian/budget";
import { DHARMA_RULES_PUBLIC } from "@/lib/librarian/dharma";
import { RATE_LIMITS_PUBLIC } from "@/lib/librarian/rate-limit";
import { DEFAULT_MODEL } from "@/lib/librarian/llm";
import { recentKarma, karmaStats } from "@/lib/librarian/karma";
import { TOOL_NAMES } from "@/lib/librarian/tools";
import { listRecentContactRequests } from "@/lib/contact";
import { isNotifyConfigured } from "@/lib/notify";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Admin — WhiteMagic Labs",
  robots: { index: false, follow: false },
};

/**
 * Admin / Librarian monitoring.
 *
 * Gated by Basic-Auth middleware (`middleware.ts`) when
 * `ADMIN_PASSWORD_HASH` is set. Exposes only aggregate counters, ledger
 * entries, and contact submissions — no conversation content.
 */
export default async function AdminPage() {
  const [budget, karma, stats, contacts] = await Promise.all([
    getBudget(),
    recentKarma(50),
    karmaStats(),
    listRecentContactRequests(25),
  ]);
  const adminGated = !!process.env.ADMIN_PASSWORD_HASH;
  const kvConfigured = !!(
    process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN
  );
  const openrouterConfigured = !!process.env.OPENROUTER_API_KEY;
  const killSwitch = process.env.LIBRARIAN_DISABLED === "1";
  const notifyConfigured = isNotifyConfigured();

  return (
    <>
      <PageHeader
        eyebrow="Admin"
        title="Librarian status."
        lede="Monthly budget, guardrails, environment, and the public Karma ledger — every tool the Librarian has invoked. Aggregate only; no conversation content is recorded."
      />

      <section className="container-site py-10">
        <div className="grid gap-4 md:grid-cols-3">
          <StatCard
            label="Monthly spend"
            value={`$${budget.spentUsd.toFixed(4)}`}
            hint={`of $${budget.capUsd.toFixed(2)} (${budget.percentUsed.toFixed(1)}%)`}
            tone={
              budget.exceeded
                ? "danger"
                : budget.alertThreshold
                  ? "warn"
                  : "ok"
            }
          />
          <StatCard
            label="OpenRouter key"
            value={openrouterConfigured ? "Configured" : "Missing (mock mode)"}
            hint={`Default model: ${DEFAULT_MODEL}`}
            tone={openrouterConfigured ? "ok" : "warn"}
          />
          <StatCard
            label="Upstash KV"
            value={kvConfigured ? "Configured" : "In-memory fallback"}
            hint={
              kvConfigured
                ? "Production-ready"
                : "Rate limits reset on restart"
            }
            tone={kvConfigured ? "ok" : "warn"}
          />
          <StatCard
            label="Kill switch"
            value={killSwitch ? "Active (Librarian disabled)" : "Inactive"}
            hint="Set LIBRARIAN_DISABLED=1 in env to disable"
            tone={killSwitch ? "warn" : "ok"}
          />
          <StatCard
            label="Tool calls · last hour"
            value={String(stats.lastHour)}
            hint={`${stats.total} recorded total`}
            tone="info"
          />
          <StatCard
            label="Daily / session limits"
            value={`${RATE_LIMITS_PUBLIC.dailyPerIp} / ${RATE_LIMITS_PUBLIC.perSession}`}
            hint="per IP / per session"
            tone="info"
          />
          <StatCard
            label="Email notifications"
            value={notifyConfigured ? "Configured (Resend)" : "Disabled"}
            hint={
              notifyConfigured
                ? "Contact submissions emailed on arrival"
                : "Set RESEND_API_KEY + CONTACT_NOTIFY_EMAIL to enable"
            }
            tone={notifyConfigured ? "ok" : "warn"}
          />
          <StatCard
            label="Admin gate"
            value={adminGated ? "Basic Auth active" : "Un-gated (dev)"}
            hint={
              adminGated
                ? "ADMIN_PASSWORD_HASH set; middleware enforcing"
                : "Set ADMIN_PASSWORD_HASH in env to enable"
            }
            tone={adminGated ? "ok" : "warn"}
          />
        </div>

        <h2 className="mb-4 mt-12 font-head text-xl font-semibold text-ink">
          Tools the Librarian can invoke ({TOOL_NAMES.length})
        </h2>
        <div className="mb-10 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {TOOL_NAMES.map((name) => (
            <div
              key={name}
              className="rounded border border-border-light/60 px-3 py-2"
            >
              <p className="font-mono text-xs text-fg">{name}</p>
              <p className="mt-0.5 font-mono text-[10px] text-muted">
                {stats.byTool[name] ?? 0} invocation
                {(stats.byTool[name] ?? 0) === 1 ? "" : "s"} recorded
              </p>
            </div>
          ))}
        </div>

        <h2 className="mb-4 font-head text-xl font-semibold text-ink">
          Karma Ledger · last 50 tool calls
        </h2>
        <p className="mb-3 text-sm text-muted">
          Every tool invocation is recorded here with tool name, args preview
          (first 120 chars), result kind, duration, and a session fingerprint
          (not session id). Mirrors the Karma Ledger primitive in WhiteMagic
          core — eating our own dogfood in public.
        </p>
        {karma.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border-light py-8 text-center text-sm text-muted">
            No tool calls recorded yet. Ask the Librarian something on
            /librarian to populate this.
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-border-light">
            <table className="w-full text-sm">
              <thead className="bg-surface-alt text-left text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-3 py-2 font-medium">When</th>
                  <th className="px-3 py-2 font-medium">Tool</th>
                  <th className="px-3 py-2 font-medium">Args (preview)</th>
                  <th className="px-3 py-2 font-medium">Result kind</th>
                  <th className="px-3 py-2 font-medium">ms</th>
                  <th className="px-3 py-2 font-medium">Session</th>
                </tr>
              </thead>
              <tbody>
                {karma.map((e) => (
                  <tr
                    key={e.id}
                    className="border-t border-border-light align-top"
                  >
                    <td className="px-3 py-2 font-mono text-[10px] text-muted">
                      {timeAgo(e.timestamp)}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">{e.tool}</td>
                    <td className="px-3 py-2 font-mono text-[10px] text-muted">
                      {e.argsPreview || "{}"}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${
                          e.resultKind === "error"
                            ? "bg-red-100 text-red-800 dark:bg-red-950/40 dark:text-red-200"
                            : "bg-lavender/10 text-lavender"
                        }`}
                      >
                        {e.resultKind}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-[10px] text-muted">
                      {e.durationMs}
                    </td>
                    <td className="px-3 py-2 font-mono text-[10px] text-muted">
                      {e.sessionIdHash ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <h2 className="mb-4 mt-12 font-head text-xl font-semibold text-ink">
          Contact submissions · last {contacts.length}
        </h2>
        <p className="mb-3 text-sm text-muted">
          Unified feed of messages from both the{" "}
          <code className="font-mono text-xs">/contact</code> form and the
          Librarian&apos;s <code className="font-mono text-xs">submit_contact_request</code>{" "}
          tool. 90-day retention.
        </p>
        {contacts.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border-light py-8 text-center text-sm text-muted">
            No contact submissions yet.
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-border-light">
            <table className="w-full text-sm">
              <thead className="bg-surface-alt text-left text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-3 py-2 font-medium">When</th>
                  <th className="px-3 py-2 font-medium">Source</th>
                  <th className="px-3 py-2 font-medium">Email</th>
                  <th className="px-3 py-2 font-medium">Topic</th>
                  <th className="px-3 py-2 font-medium">Summary</th>
                  <th className="px-3 py-2 font-medium">Ref</th>
                </tr>
              </thead>
              <tbody>
                {contacts.map((c) => (
                  <tr
                    key={c.reference}
                    className="border-t border-border-light align-top"
                  >
                    <td className="px-3 py-2 font-mono text-[10px] text-muted">
                      {timeAgo(c.timestamp)}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${
                          c.source === "librarian"
                            ? "bg-lavender/10 text-lavender"
                            : "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200"
                        }`}
                      >
                        {c.source}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">{c.email}</td>
                    <td className="px-3 py-2 text-xs">{c.topic}</td>
                    <td className="max-w-md px-3 py-2 text-xs text-muted">
                      {c.summary}
                    </td>
                    <td className="px-3 py-2 font-mono text-[10px] text-muted">
                      {c.reference}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <h2 className="mb-4 mt-12 font-head text-xl font-semibold text-ink">
          Dharma rules on visitor input ({DHARMA_RULES_PUBLIC.length})
        </h2>
        <div className="overflow-hidden rounded-lg border border-border-light">
          <table className="w-full text-sm">
            <thead className="bg-surface-alt text-left text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-2 font-medium">Rule</th>
                <th className="px-4 py-2 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {DHARMA_RULES_PUBLIC.map((r) => (
                <tr key={r.name} className="border-t border-border-light">
                  <td className="px-4 py-2 font-mono text-xs">{r.name}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        r.action === "block"
                          ? "bg-red-100 text-red-800 dark:bg-red-950/40 dark:text-red-200"
                          : "bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
                      }`}
                    >
                      {r.action}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

type StatTone = "ok" | "warn" | "danger" | "info";

function StatCard({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint: string;
  tone: StatTone;
}) {
  const toneClasses: Record<StatTone, string> = {
    ok: "border-emerald-300/40 bg-emerald-50/30 dark:bg-emerald-950/20",
    warn: "border-amber-300/40 bg-amber-50/30 dark:bg-amber-950/20",
    danger: "border-red-300/40 bg-red-50/30 dark:bg-red-950/20",
    info: "border-border-light bg-surface",
  };
  return (
    <div className={`rounded-xl border p-5 ${toneClasses[tone]}`}>
      <p className="mb-1 font-mono text-xs uppercase tracking-widest text-muted">
        {label}
      </p>
      <p className="mb-1 font-head text-2xl font-semibold text-ink">{value}</p>
      <p className="text-xs text-muted">{hint}</p>
    </div>
  );
}

function timeAgo(ts: number): string {
  const diff = Date.now() - ts;
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}
