import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const res = await fetch("http://localhost:8770/api/tools/mandala.status", {
      signal: AbortSignal.timeout(3000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      {
        status: "ok",
        available_tiers: { thread: true, namespace: false, container: false, microvm: false, wasm: false },
        best_tier: "thread",
        max_concurrent: 4,
        active_shelters: 0,
        shelters: [],
        templates: {
          research: { description: "Research shelter — network read, generous resources, creative Dharma profile", dharma_profile: "creative" },
          sandbox: { description: "Sandbox shelter — no network, limited resources, default Dharma profile", dharma_profile: "default" },
          production: { description: "Production shelter — read-only, secure Dharma profile, standard resources", dharma_profile: "secure" },
          secure: { description: "Secure shelter — no network, no filesystem, minimal resources, secure Dharma", dharma_profile: "secure" },
        },
      },
      { status: 200 }
    );
  }
}
