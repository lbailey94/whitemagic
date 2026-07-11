interface PipelineStage {
  num: number;
  name: string;
  role: string;
  detail: string;
  icon: string;
}

const STAGES: PipelineStage[] = [
  { num: 1, name: "Governor", role: "Policy check", detail: "Evaluates request against active governance profile. Can block, tag, or throttle before any processing.", icon: "shield" },
  { num: 2, name: "Input Sanitizer", role: "Injection defense", detail: "Shell injection detection, content scanning, internal field stripping. Exempts known-safe content paths.", icon: "filter" },
  { num: 3, name: "Rate Limiter", role: "Throughput control", detail: "Rust EventRing pre-check at 452K ops/s. Zero allocation in the hot path. Token bucket per tool per user.", icon: "gauge" },
  { num: 4, name: "RBAC", role: "Access control", detail: "Role-based access control. Checks user permissions against tool requirements. Per-galaxy isolation.", icon: "lock" },
  { num: 5, name: "Maturity Gate", role: "Capability check", detail: "Verifies the calling agent has sufficient maturity score to use the requested tool. Prevents unsafe escalation.", icon: "key" },
  { num: 6, name: "Dharma Engine", role: "Ethical reasoning", detail: "YAML-driven ethical guardrails with 4 profiles. Graduated actions: log, tag, warn, throttle, block. Hot-reloadable.", icon: "scale" },
  { num: 7, name: "Handler", role: "Execution", detail: "The actual tool runs. 614 callable tools across 28 Gana meta-tools. ThreadPoolExecutor with 8 workers.", icon: "play" },
  { num: 8, name: "Karma Ledger", role: "Audit trail", detail: "SHA-256 Merkle-chained append-only log. Records declared intent vs actual execution. XRPL-anchorable.", icon: "scroll" },
];

export function DispatchPipeline() {
  return (
    <div className="my-8">
      <div className="flex flex-col gap-2">
        {STAGES.map((stage, i) => (
          <div key={stage.num}>
            <div className="flex items-stretch gap-3">
              {/* Stage number */}
              <div className="flex w-10 flex-shrink-0 flex-col items-center">
                <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-lavender/40 bg-lavender/5 font-mono text-sm font-bold text-lavender">
                  {stage.num}
                </div>
                {i < STAGES.length - 1 && (
                  <div className="mt-1 w-px flex-1 bg-gradient-to-b from-lavender/40 to-lavender/10" />
                )}
              </div>

              {/* Stage content */}
              <div className="flex-1 rounded-xl border border-border bg-surface p-4 transition hover:border-lavender/30">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h3 className="font-head text-sm font-semibold text-ink">
                      {stage.name}
                    </h3>
                    <p className="font-mono text-[10px] uppercase tracking-wider text-dim">
                      {stage.role}
                    </p>
                  </div>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-muted">
                  {stage.detail}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <p className="mt-6 rounded-lg border border-dashed border-border bg-surface-alt p-4 text-xs text-muted">
        Even if a tool is malicious, even if an agent is misdirected, even if memory is poisoned —
        the pipeline prevents harm. This is the single most important architectural decision in the system.
      </p>
    </div>
  );
}
