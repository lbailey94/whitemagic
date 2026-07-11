"use client";

import { useEffect, useState } from "react";
import {
  Shield,
  Globe,
  Lock,
  FlaskConical,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Layers,
  Sparkles,
} from "lucide-react";

interface MandalaStatus {
  status: string;
  available_tiers?: Record<string, boolean>;
  best_tier?: string;
  max_concurrent?: number;
  active_shelters?: number;
  shelters?: Array<{
    name: string;
    tier: string;
    state: string;
    template: string;
    dharma_profile: string;
    capabilities: Record<string, unknown>;
  }>;
  templates?: Record<
    string,
    { description: string; dharma_profile: string }
  >;
}

interface KarmaDebt {
  status: string;
  total_debt?: number;
  total_calls?: number;
  total_mismatches?: number;
  effect_mismatch_count?: number;
  per_tool?: Record<string, { debt: number; calls: number; mismatches: number }>;
}

interface EffectSummary {
  status: string;
  total_tools?: number;
  effect_type_counts?: Record<string, number>;
}

interface TemplateDetails {
  status: string;
  templates?: Record<
    string,
    {
      capabilities: string[];
      limits: Record<string, number>;
      dharma_profile: string;
      description: string;
    }
  >;
}

const EFFECT_COLORS: Record<string, string> = {
  pure: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  local: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  network: "bg-orange-500/20 text-orange-300 border-orange-500/30",
  destructive: "bg-red-500/20 text-red-300 border-red-500/30",
  observation: "bg-green-500/20 text-green-300 border-green-500/30",
};

const DHARMA_BADGE: Record<string, string> = {
  default: "bg-slate-500/20 text-slate-300 border-slate-500/30",
  creative: "bg-purple-500/20 text-purple-300 border-purple-500/30",
  secure: "bg-red-500/20 text-red-300 border-red-500/30",
};

const TEMPLATE_ICONS: Record<string, typeof Shield> = {
  research: FlaskConical,
  sandbox: Globe,
  production: Shield,
  secure: Lock,
};

export function MandalaDashboard() {
  const [status, setStatus] = useState<MandalaStatus | null>(null);
  const [debt, setDebt] = useState<KarmaDebt | null>(null);
  const [effects, setEffects] = useState<EffectSummary | null>(null);
  const [templates, setTemplates] = useState<TemplateDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [statusRes, debtRes, effectsRes, templatesRes] =
          await Promise.all([
            fetch("/api/mandala/status").then((r) => r.json()),
            fetch("/api/mandala/debt").then((r) => r.json()),
            fetch("/api/mandala/effects").then((r) => r.json()),
            fetch("/api/mandala/templates").then((r) => r.json()),
          ]);

        setStatus(statusRes);
        setDebt(debtRes);
        setEffects(effectsRes);
        setTemplates(templatesRes);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="animate-pulse text-muted">
          <Activity className="mx-auto mb-3 h-8 w-8" />
          <p className="font-mono text-sm">Loading MandalaOS dashboard…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-8 text-center">
        <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-red-400" />
        <p className="text-sm text-muted">
          Dashboard data unavailable. Run the MCP server locally to see live
          data.
        </p>
        <p className="mt-2 font-mono text-xs text-fg/40">{error}</p>
      </div>
    );
  }

  const activeShelters = status?.active_shelters ?? 0;
  const totalDebt = debt?.total_debt ?? 0;
  const totalCalls = debt?.total_calls ?? 0;
  const effectMismatches = debt?.effect_mismatch_count ?? 0;
  const totalTools = effects?.total_tools ?? 0;
  const typeCounts = effects?.effect_type_counts ?? {};

  return (
    <div className="space-y-8">
      {/* Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={Layers}
          label="Active Compartments"
          value={activeShelters}
          accent="text-lavender"
        />
        <StatCard
          icon={Activity}
          label="Total Tool Calls"
          value={totalCalls}
          accent="text-blue-400"
        />
        <StatCard
          icon={AlertTriangle}
          label="Karma Debt"
          value={totalDebt.toFixed(2)}
          accent={totalDebt > 5 ? "text-red-400" : "text-green-400"}
        />
        <StatCard
          icon={CheckCircle2}
          label="Effect Mismatches"
          value={effectMismatches}
          accent={effectMismatches > 0 ? "text-orange-400" : "text-green-400"}
        />
      </div>

      {/* Effect Type Distribution */}
      {Object.keys(typeCounts).length > 0 && (
        <div className="rounded-xl border border-border-light bg-surface p-6">
          <h3 className="mb-4 flex items-center gap-2 font-head text-lg font-semibold">
            <Sparkles className="h-5 w-5 text-lavender" />
            Effect Type Distribution
            <span className="ml-auto font-mono text-xs text-muted">
              {totalTools} tools registered
            </span>
          </h3>
          <div className="space-y-3">
            {Object.entries(typeCounts)
              .sort((a, b) => b[1] - a[1])
              .map(([type, count]) => {
                const pct = totalTools > 0 ? (count / totalTools) * 100 : 0;
                return (
                  <div key={type} className="flex items-center gap-3">
                    <span
                      className={`inline-flex items-center rounded-md border px-2 py-0.5 font-mono text-xs ${EFFECT_COLORS[type] ?? "bg-gray-500/20 text-gray-300 border-gray-500/30"}`}
                    >
                      {type}
                    </span>
                    <div className="flex-1">
                      <div className="h-2 overflow-hidden rounded-full bg-border-light">
                        <div
                          className="h-full rounded-full bg-lavender transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                    <span className="w-12 text-right font-mono text-sm text-muted">
                      {count}
                    </span>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Shelter Templates */}
      {templates?.templates && (
        <div className="rounded-xl border border-border-light bg-surface p-6">
          <h3 className="mb-4 flex items-center gap-2 font-head text-lg font-semibold">
            <Shield className="h-5 w-5 text-lavender" />
            Mandala Templates
          </h3>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(templates.templates).map(([name, tmpl]) => {
              const Icon = TEMPLATE_ICONS[name] ?? Shield;
              return (
                <div
                  key={name}
                  className="rounded-lg border border-border-light bg-surface-alt p-4 transition hover:border-lavender/30"
                >
                  <div className="mb-2 flex items-center gap-2">
                    <Icon className="h-4 w-4 text-lavender" />
                    <span className="font-mono text-sm font-semibold">
                      {name}
                    </span>
                  </div>
                  <p className="mb-3 text-xs text-muted">{tmpl.description}</p>
                  <span
                    className={`inline-flex items-center rounded-md border px-2 py-0.5 font-mono text-xs ${DHARMA_BADGE[tmpl.dharma_profile] ?? DHARMA_BADGE.default}`}
                  >
                    dharma: {tmpl.dharma_profile}
                  </span>
                  <div className="mt-3 space-y-1 font-mono text-xs text-fg/50">
                    <div>timeout: {tmpl.limits.timeout_s}s</div>
                    <div>memory: {tmpl.limits.max_memory_mb}MB</div>
                    <div>cpu: {tmpl.limits.max_cpu_s}s</div>
                    <div>disk: {tmpl.limits.max_disk_mb}MB</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Active Compartments */}
      {status?.shelters && status.shelters.length > 0 ? (
        <div className="rounded-xl border border-border-light bg-surface p-6">
          <h3 className="mb-4 flex items-center gap-2 font-head text-lg font-semibold">
            <Activity className="h-5 w-5 text-lavender" />
            Active Compartments
          </h3>
          <div className="space-y-3">
            {status.shelters.map((shelter) => (
              <div
                key={shelter.name}
                className="flex items-center justify-between rounded-lg border border-border-light bg-surface-alt p-4"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-semibold">
                      {shelter.name}
                    </span>
                    {shelter.template && (
                      <span className="rounded bg-lavender/10 px-1.5 py-0.5 font-mono text-xs text-lavender">
                        {shelter.template}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex items-center gap-3 font-mono text-xs text-muted">
                    <span>tier: {shelter.tier}</span>
                    <span>state: {shelter.state}</span>
                  </div>
                </div>
                <span
                  className={`inline-flex items-center rounded-md border px-2 py-0.5 font-mono text-xs ${DHARMA_BADGE[shelter.dharma_profile] ?? DHARMA_BADGE.default}`}
                >
                  {shelter.dharma_profile}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-border-light bg-surface p-6 text-center">
          <Shield className="mx-auto mb-3 h-8 w-8 text-lavender/40" />
          <p className="text-sm text-muted">
            No active mandala compartments. Create one via{" "}
            <code className="font-mono text-xs text-lavender">
              mandala.create
            </code>
            .
          </p>
        </div>
      )}

      {/* Available Tiers */}
      {status?.available_tiers && (
        <div className="rounded-xl border border-border-light bg-surface p-6">
          <h3 className="mb-4 flex items-center gap-2 font-head text-lg font-semibold">
            <Layers className="h-5 w-5 text-lavender" />
            Isolation Tiers
          </h3>
          <div className="flex flex-wrap gap-3">
            {Object.entries(status.available_tiers).map(([tier, available]) => (
              <div
                key={tier}
                className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 font-mono text-xs ${
                  available
                    ? "border-green-500/30 bg-green-500/10 text-green-300"
                    : "border-border-light bg-surface-alt text-muted"
                }`}
              >
                <span
                  className={`h-2 w-2 rounded-full ${available ? "bg-green-400" : "bg-gray-500"}`}
                />
                {tier}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  accent,
}: {
  icon: typeof Shield;
  label: string;
  value: string | number;
  accent: string;
}) {
  return (
    <div className="rounded-xl border border-border-light bg-surface p-5">
      <div className="mb-2 flex items-center gap-2">
        <Icon className={`h-4 w-4 ${accent}`} />
        <span className="font-mono text-xs text-muted">{label}</span>
      </div>
      <p className={`font-head text-2xl font-bold ${accent}`}>{value}</p>
    </div>
  );
}
