import { PageHeader } from "@/components/PageHeader";
import { getBudget } from "@/lib/librarian/budget";
import {
  DHARMA_RULES_PUBLIC,
} from "@/lib/librarian/dharma";
import { RATE_LIMITS_PUBLIC } from "@/lib/librarian/rate-limit";
import { DEFAULT_MODEL } from "@/lib/librarian/llm";

// Force dynamic rendering so the budget reads live from KV on each request.
export const dynamic = "force-dynamic";

export const metadata = {
  title: "Admin — WhiteMagic Labs",
  robots: { index: false, follow: false },
};

/**
 * Admin / Librarian monitoring.
 *
 * TODO before making this properly gated: add Vercel middleware checking
 * a hashed ADMIN_PASSWORD env var. Currently this page is not secret, but
 * it also exposes only aggregate counters — no conversation content, no
 * visitor IPs — so drive-by discovery is low-risk.
 */
export default async function AdminPage() {
  const budget = await getBudget();
  const kvConfigured = !!(
    process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN
  );
  const openrouterConfigured = !!process.env.OPENROUTER_API_KEY;
  const killSwitch = process.env.LIBRARIAN_DISABLED === "1";

  return (
    <>
      <PageHeader
        eyebrow="Admin"
        title="Librarian status."
        lede="Monthly budget, guardrails, and environment readiness. Aggregate counters only — no conversation content is recorded."
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
            hint={kvConfigured ? "Production-ready" : "Rate limits reset on restart"}
            tone={kvConfigured ? "ok" : "warn"}
          />
          <StatCard
            label="Kill switch"
            value={killSwitch ? "Active (Librarian disabled)" : "Inactive"}
            hint="Set LIBRARIAN_DISABLED=1 in env to disable"
            tone={killSwitch ? "warn" : "ok"}
          />
          <StatCard
            label="Daily IP limit"
            value={`${RATE_LIMITS_PUBLIC.dailyPerIp} msgs`}
            hint="Resets at UTC midnight"
            tone="info"
          />
          <StatCard
            label="Session limit"
            value={`${RATE_LIMITS_PUBLIC.perSession} msgs`}
            hint="2-hour window"
            tone="info"
          />
        </div>

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

function StatCard({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint: string;
  tone: "ok" | "warn" | "danger" | "info";
}) {
  const toneClasses: Record<typeof tone, string> = {
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
