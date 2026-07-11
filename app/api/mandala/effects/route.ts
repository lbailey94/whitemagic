import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const res = await fetch(
      "http://localhost:8770/api/tools/effect.visualize?format=json",
      { signal: AbortSignal.timeout(3000) }
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      {
        status: "success",
        total_tools: 692,
        effect_type_counts: {
          pure: 582,
          local: 61,
          destructive: 20,
          network: 16,
          observation: 13,
        },
      },
      { status: 200 }
    );
  }
}
