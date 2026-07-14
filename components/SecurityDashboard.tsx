"use client";

import { useEffect, useState } from "react";

interface SecurityStatus {
  status: string;
  event_bus: {
    enabled: boolean;
    total_events: number;
    subscribers: number;
    recent_events: Array<{
      event_type: string;
      source: string;
      severity: string;
      timestamp: string;
      detail: string;
    }>;
  };
  hermit_crab: {
    state: string;
    threat_score: number;
  };
  transaction_firewall: {
    enabled: boolean;
    fail_closed: boolean;
    approved: number;
    blocked: number;
  };
  engagement_tokens: {
    active: number;
    revoked: number;
  };
  mcp_integrity: {
    verified: boolean;
    drift_events: number;
  };
  vuln_kb: {
    persistent: boolean;
    total_patterns: number;
    categories: Record<string, number>;
  };
  audit_signer: {
    available: boolean;
    key_id: string | null;
  };
  zodiac_ledger: {
    chain_valid: boolean;
    total_entries: number;
    signed_entries: number;
  };
}

const severityColors: Record<string, string> = {
  critical: "text-red-400 bg-red-950/50 border-red-800",
  high: "text-orange-400 bg-orange-950/50 border-orange-800",
  medium: "text-yellow-400 bg-yellow-950/50 border-yellow-800",
  low: "text-blue-400 bg-blue-950/50 border-blue-800",
  info: "text-slate-400 bg-slate-950/50 border-slate-800",
};

const stateColors: Record<string, string> = {
  open: "text-green-400 bg-green-950/50 border-green-800",
  guarded: "text-yellow-400 bg-yellow-950/50 border-yellow-800",
  withdrawn: "text-red-400 bg-red-950/50 border-red-800",
  mediating: "text-purple-400 bg-purple-950/50 border-purple-800",
};

function StatCard({
  label,
  value,
  sublabel,
  accent = "default",
}: {
  label: string;
  value: string | number;
  sublabel?: string;
  accent?: "default" | "green" | "red" | "yellow" | "blue";
}) {
  const accentMap = {
    default: "text-slate-100",
    green: "text-green-400",
    red: "text-red-400",
    yellow: "text-yellow-400",
    blue: "text-blue-400",
  };
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <div className={`mt-2 text-2xl font-bold ${accentMap[accent]}`}>
        {value}
      </div>
      {sublabel && (
        <div className="mt-1 text-xs text-slate-500">{sublabel}</div>
      )}
    </div>
  );
}

export function SecurityDashboard() {
  const [data, setData] = useState<SecurityStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStatus() {
      try {
        const res = await fetch("/api/security/status");
        const json = await res.json();
        setData(json);
      } catch {
        // Use fallback data from API
      } finally {
        setLoading(false);
      }
    }
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-500">
        Loading security posture...
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-500">
        Unable to load security data. Is the MCP server running?
      </div>
    );
  }

  const hcState = (data.hermit_crab?.state || "open").toLowerCase();
  const txEnabled = data.transaction_firewall?.enabled ?? false;
  const ledgerValid = data.zodiac_ledger?.chain_valid ?? true;
  const signerAvailable = data.audit_signer?.available ?? false;

  return (
    <div className="space-y-8">
      {/* Top stat cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        <StatCard
          label="HermitCrab State"
          value={hcState.toUpperCase()}
          sublabel={`Threat: ${((data.hermit_crab?.threat_score || 0) * 100).toFixed(0)}%`}
          accent={
            hcState === "open" ? "green" :
            hcState === "guarded" ? "yellow" :
            hcState === "withdrawn" ? "red" : "default"
          }
        />
        <StatCard
          label="Tx Firewall"
          value={txEnabled ? "ACTIVE" : "OFF"}
          sublabel={`${data.transaction_firewall?.approved || 0} approved / ${data.transaction_firewall?.blocked || 0} blocked`}
          accent={txEnabled ? "green" : "red"}
        />
        <StatCard
          label="Active Tokens"
          value={data.engagement_tokens?.active || 0}
          sublabel={`${data.engagement_tokens?.revoked || 0} revoked`}
          accent="blue"
        />
        <StatCard
          label="Vuln Patterns"
          value={data.vuln_kb?.total_patterns || 0}
          sublabel={data.vuln_kb?.persistent ? "SQLite persisted" : "In-memory"}
          accent={data.vuln_kb?.persistent ? "green" : "yellow"}
        />
      </div>

      {/* Second row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        <StatCard
          label="Security Events"
          value={data.event_bus?.total_events || 0}
          sublabel={`${data.event_bus?.subscribers || 0} subscribers`}
        />
        <StatCard
          label="MCP Integrity"
          value={data.mcp_integrity?.verified ? "VERIFIED" : "DRIFT"}
          sublabel={`${data.mcp_integrity?.drift_events || 0} drift events`}
          accent={data.mcp_integrity?.verified ? "green" : "red"}
        />
        <StatCard
          label="Ledger Entries"
          value={data.zodiac_ledger?.total_entries || 0}
          sublabel={`${data.zodiac_ledger?.signed_entries || 0} Ed25519 signed`}
          accent={ledgerValid ? "green" : "red"}
        />
        <StatCard
          label="Audit Signer"
          value={signerAvailable ? "AVAILABLE" : "OFFLINE"}
          sublabel={data.audit_signer?.key_id ? `Key: ${data.audit_signer.key_id.slice(0, 8)}...` : "No key loaded"}
          accent={signerAvailable ? "green" : "yellow"}
        />
      </div>

      {/* Recent security events feed */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-6">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Recent Security Events
        </h3>
        {(data.event_bus?.recent_events || []).length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-600">
            No recent security events. System is quiet.
          </p>
        ) : (
          <div className="space-y-2">
            {(data.event_bus?.recent_events || []).slice(0, 20).map((event, i) => (
              <div
                key={i}
                className={`flex items-center gap-3 rounded border px-3 py-2 text-sm ${
                  severityColors[event.severity?.toLowerCase()] || severityColors.info
                }`}
              >
                <span className="font-mono text-xs text-slate-500">
                  {event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : "--:--:--"}
                </span>
                <span className="font-medium">{event.event_type}</span>
                <span className="text-slate-400">from {event.source}</span>
                {event.detail && (
                  <span className="ml-auto truncate text-xs text-slate-500">{event.detail}</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* HermitCrab state visualization */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-6">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          HermitCrab Protection State
        </h3>
        <div className="flex items-center gap-2">
          {["open", "guarded", "withdrawn", "mediating"].map((state) => (
            <div
              key={state}
              className={`flex-1 rounded-lg border px-4 py-3 text-center text-sm font-medium capitalize ${
                hcState === state
                  ? stateColors[state] || severityColors.info
                  : "border-slate-800 bg-slate-900/30 text-slate-600"
              }`}
            >
              {state}
            </div>
          ))}
        </div>
        <div className="mt-3 text-center text-xs text-slate-500">
          Threat Score: {((data.hermit_crab?.threat_score || 0) * 100).toFixed(1)}%
        </div>
      </div>

      {/* Zodiac Ledger integrity */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-6">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Zodiac Ledger — Cryptographic Provenance
        </h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className={`text-lg font-bold ${ledgerValid ? "text-green-400" : "text-red-400"}`}>
              {ledgerValid ? "VALID" : "BROKEN"}
            </div>
            <div className="text-xs text-slate-500">SHA-256 Chain</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-slate-200">
              {data.zodiac_ledger?.signed_entries || 0}
            </div>
            <div className="text-xs text-slate-500">Ed25519 Signed</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-slate-200">
              {data.zodiac_ledger?.total_entries || 0}
            </div>
            <div className="text-xs text-slate-500">Total Entries</div>
          </div>
        </div>
      </div>
    </div>
  );
}
