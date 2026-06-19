export const WM_FACTS = {
  version: "22.2.4",
  verifiedDate: "June 19, 2026",
  linesShort: "180K",
  linesLong: "180,000",
  callableTools: "490",
  dispatchTools: "462",
  ganaTools: "28",
  testsPassing: "2503",
  testsSkipped: "2",
  testsFailing: "0",
  languages: "8",
  // Performance benchmarks (June 2026)
  perfMedianMs: "29-33",
  perfP95Ms: "36-55",
  perfP99Ms: "38-86",
  perfSuccessRate: "100",
  perfMemoryMB: "0-0.18",
  perfThroughputRps: "29.38",
  benchmarkDate: "June 16, 2026",
  // Recent changes
  mcpApiBridgeFixed: true,
  bridgeModulesRecovered: 25,
  bridgeModulesNote: "13 core/bridge/* modules ported from SD card archive, 10 more surfaced, mcp_api_bridge crash fixed",
} as const;

export const WM_FACT_TEXT = {
  toolSurface: `${WM_FACTS.callableTools} callable tools (${WM_FACTS.dispatchTools} dispatch + ${WM_FACTS.ganaTools} PRAT Gana meta-tools)`,
  testSuite: `${WM_FACTS.testsPassing} passing tests, ${WM_FACTS.testsSkipped} skipped, ${WM_FACTS.testsFailing} failures`,
  shortPassingSuite: `${WM_FACTS.testsPassing} passing tests with zero failures`,
  mcpSurface: `${WM_FACTS.callableTools} callable tools across ${WM_FACTS.ganaTools} Gana meta-tools`,
  // Performance text
  perfSummary: `${WM_FACTS.perfMedianMs}ms median latency, ${WM_FACTS.perfP95Ms}ms P95, ${WM_FACTS.perfSuccessRate}% success rate`,
  perfComparison: `3-10x faster than typical MCP implementations (29-33ms vs 100-300ms)`,
  perfFull: `Median: ${WM_FACTS.perfMedianMs}ms | P95: ${WM_FACTS.perfP95Ms}ms | P99: ${WM_FACTS.perfP99Ms}ms | Success: ${WM_FACTS.perfSuccessRate}% | Memory: ${WM_FACTS.perfMemoryMB}MB | Throughput: ${WM_FACTS.perfThroughputRps} req/s`,
} as const;
