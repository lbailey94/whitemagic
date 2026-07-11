import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const res = await fetch(
      "http://localhost:8770/api/tools/mandala.templates",
      { signal: AbortSignal.timeout(3000) }
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      {
        status: "success",
        templates: {
          research: {
            capabilities: ["network_read", "fs_read:/tmp", "fs_write:/tmp"],
            limits: { timeout_s: 600, max_memory_mb: 2048, max_cpu_s: 120, max_disk_mb: 1000 },
            dharma_profile: "creative",
            description: "Research shelter — network read, generous resources, creative Dharma profile",
          },
          sandbox: {
            capabilities: ["fs_write:/tmp"],
            limits: { timeout_s: 60, max_memory_mb: 512, max_cpu_s: 30, max_disk_mb: 100 },
            dharma_profile: "default",
            description: "Sandbox shelter — no network, limited resources, default Dharma profile",
          },
          production: {
            capabilities: ["network_read", "fs_read:/data"],
            limits: { timeout_s: 300, max_memory_mb: 1024, max_cpu_s: 60, max_disk_mb: 500 },
            dharma_profile: "secure",
            description: "Production shelter — read-only, secure Dharma profile, standard resources",
          },
          secure: {
            capabilities: [],
            limits: { timeout_s: 30, max_memory_mb: 256, max_cpu_s: 15, max_disk_mb: 50 },
            dharma_profile: "secure",
            description: "Secure shelter — no network, no filesystem, minimal resources, secure Dharma",
          },
        },
      },
      { status: 200 }
    );
  }
}
