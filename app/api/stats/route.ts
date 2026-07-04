import { NextResponse } from "next/server";
import { WM_FACTS } from "@/lib/facts";

export const dynamic = "force-static";

export async function GET() {
  return NextResponse.json({
    version: WM_FACTS.version,
    verifiedDate: WM_FACTS.verifiedDate,
    callableTools: parseInt(WM_FACTS.callableTools),
    dispatchTools: parseInt(WM_FACTS.dispatchTools),
    ganaTools: parseInt(WM_FACTS.ganaTools),
    testsPassing: parseInt(WM_FACTS.testsPassing),
    testsSkipped: parseInt(WM_FACTS.testsSkipped),
    testsFailing: parseInt(WM_FACTS.testsFailing),
    memories: parseInt(WM_FACTS.memories.replace(/,/g, "")),
    galaxies: parseInt(WM_FACTS.galaxies),
    languages: parseInt(WM_FACTS.languages),
    linesOfCode: WM_FACTS.linesLong,
    performance: {
      medianMs: WM_FACTS.perfMedianMs,
      p95Ms: WM_FACTS.perfP95Ms,
      p99Ms: WM_FACTS.perfP99Ms,
      successRate: parseInt(WM_FACTS.perfSuccessRate),
      throughputRps: parseFloat(WM_FACTS.perfThroughputRps),
    },
    license: "MIT",
    repository: "https://github.com/lbailey94/whitemagic",
  });
}
