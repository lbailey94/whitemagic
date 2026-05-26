"use client";
import { PRESCIENCE_PENDING, type PendingClaim } from "@/lib/data/prescience";
import { Clock, TrendingUp, AlertCircle } from "lucide-react";

const STATUS_STYLES: Record<PendingClaim["status"], string> = {
  arriving: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  pending: "bg-sky-500/10 text-sky-400 border-sky-500/30",
  contested: "bg-rose-500/10 text-rose-400 border-rose-500/30",
};

const STATUS_LABELS: Record<PendingClaim["status"], string> = {
  arriving: "arriving",
  pending: "pending",
  contested: "contested",
};

const CONFIDENCE_DOTS: Record<PendingClaim["confidence"], number> = {
  high: 3,
  medium: 2,
  low: 1,
};

export function PendingList() {
  const arriving = PRESCIENCE_PENDING.filter((p) => p.status === "arriving");
  const pending = PRESCIENCE_PENDING.filter((p) => p.status === "pending");
  const contested = PRESCIENCE_PENDING.filter((p) => p.status === "contested");

  return (
    <section className="border-y border-border-light bg-surface py-16">
      <div className="container-site mx-auto max-w-4xl space-y-10">

        {/* Header */}
        <div>
          <p className="mb-2 font-mono text-xs uppercase tracking-widest text-amber-400">
            Pending / arriving · {PRESCIENCE_PENDING.length} open forecasts
          </p>
          <h2 className="font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
            The world is heading here. No validation event yet.
          </h2>
          <p className="mt-3 max-w-2xl text-sm text-muted">
            These predictions have verifiable source timestamps but no clean independent validation event — so they score{" "}
            <strong className="text-ink">0 points</strong> under the conservative methodology. When validation arrives, each moves to the confirmed claims table with its full lead-time score.
          </p>
        </div>

        {/* Stats row */}
        <div className="grid gap-3 sm:grid-cols-3">
          <StatTile icon={TrendingUp} label="Arriving" count={arriving.length} color="text-amber-400" />
          <StatTile icon={Clock} label="Pending" count={pending.length} color="text-sky-400" />
          <StatTile icon={AlertCircle} label="Contested" count={contested.length} color="text-rose-400" />
        </div>

        {/* Honest caveat */}
        <div className="rounded-2xl border border-dashed border-border bg-surface-alt p-4 text-sm text-muted">
          <span className="mr-2 font-mono text-xs uppercase tracking-widest text-amber-400">How scoring works</span>
          A claim only earns points when two conditions are met: (1) a verifiable source timestamp, and (2) an independently verifiable public validation event by a credible external entity. &ldquo;Arriving&rdquo; means the trend is clearly confirmed but no single clean validation event has occurred yet. &ldquo;Pending&rdquo; means the direction is plausible but uncertain.
        </div>

        {/* Cards */}
        <div className="space-y-3">
          {PRESCIENCE_PENDING.map((claim) => (
            <PendingCard key={claim.claim} claim={claim} />
          ))}
        </div>
      </div>
    </section>
  );
}

function StatTile({
  icon: Icon,
  label,
  count,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  count: number;
  color: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-border bg-surface-alt p-4">
      <Icon className={`h-5 w-5 flex-shrink-0 ${color}`} />
      <div>
        <p className={`text-xl font-bold ${color}`}>{count}</p>
        <p className="text-xs text-dim">{label}</p>
      </div>
    </div>
  );
}

function PendingCard({ claim }: { claim: PendingClaim }) {
  const dots = CONFIDENCE_DOTS[claim.confidence];
  return (
    <div className="rounded-2xl border border-border bg-surface-alt p-5 transition-colors hover:border-amber-500/30">
      <div className="mb-3 flex flex-wrap items-start gap-2">
        <span
          className={`rounded-full border px-2.5 py-0.5 font-mono text-xs ${STATUS_STYLES[claim.status]}`}
        >
          {STATUS_LABELS[claim.status]}
        </span>
        <span className="rounded-full border border-border bg-surface px-2.5 py-0.5 font-mono text-xs text-dim">
          src: {claim.when}
        </span>
        <span className="ml-auto flex items-center gap-0.5" title={`confidence: ${claim.confidence}`}>
          {Array.from({ length: 3 }).map((_, i) => (
            <span
              key={i}
              className={`inline-block h-1.5 w-1.5 rounded-full ${i < dots ? "bg-amber-400" : "bg-border"}`}
            />
          ))}
        </span>
        <span className="font-mono text-xs text-dim">0 pts</span>
      </div>

      <h3 className="mb-2 font-head text-base font-semibold text-ink">{claim.claim}</h3>
      <p className="mb-3 text-sm text-muted">{claim.direction}</p>

      <p className="font-mono text-xs text-dim">
        <span className="mr-1 text-amber-400/70">src</span>
        {claim.source}
      </p>
    </div>
  );
}
