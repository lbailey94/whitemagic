import type { Claim } from "@/lib/data/prescience";
export function ClaimCard({ claim }: { claim: Claim }) {
  return (<div className="rounded-2xl border border-border bg-surface p-6 transition hover:border-lavender/30">
    <div className="flex items-start gap-4">
      <claim.icon className="mt-0.5 h-6 w-6 shrink-0 text-lavender" />
      <div className="min-w-0">
        <h3 className="font-head text-lg font-semibold text-ink">{claim.claim}</h3>
        <p className="mt-1 text-sm text-muted">{claim.detail}</p>
        <div className="mt-3 flex flex-wrap gap-3 font-mono text-xs">
          <span className="rounded-full bg-lavender/10 px-3 py-1 text-lavender">Shipped: {claim.when}</span>
          <span className="rounded-full bg-emerald/10 px-3 py-1 text-emerald">Validated: {claim.validated}</span>
          {claim.gap !== "—" && <span className="rounded-full bg-surface-alt px-3 py-1 text-dim">Gap: {claim.gap}</span>}
        </div>
      </div>
    </div>
  </div>);
}