import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const res = await fetch("http://localhost:8770/api/tools/karmic.debt", {
      signal: AbortSignal.timeout(3000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      {
        status: "success",
        total_debt: 0.0,
        total_calls: 0,
        total_mismatches: 0,
        effect_mismatch_count: 0,
        per_tool: {},
      },
      { status: 200 }
    );
  }
}
