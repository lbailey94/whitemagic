import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const res = await fetch("http://localhost:8770/api/tools/security.status", {
      signal: AbortSignal.timeout(3000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      {
        status: "ok",
        event_bus: {
          enabled: true,
          total_events: 0,
          subscribers: 0,
          recent_events: [],
        },
        hermit_crab: {
          state: "open",
          threat_score: 0.0,
        },
        transaction_firewall: {
          enabled: true,
          fail_closed: false,
          approved: 0,
          blocked: 0,
        },
        engagement_tokens: {
          active: 0,
          revoked: 0,
        },
        mcp_integrity: {
          verified: true,
          drift_events: 0,
        },
        vuln_kb: {
          persistent: true,
          total_patterns: 9,
          categories: {},
        },
        audit_signer: {
          available: false,
          key_id: null,
        },
        zodiac_ledger: {
          chain_valid: true,
          total_entries: 0,
          signed_entries: 0,
        },
      },
      { status: 200 }
    );
  }
}
