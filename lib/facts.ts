export const WM_FACTS = {
  version: "24.0.1",
  verifiedDate: "July 5, 2026",
  linesShort: "336K",
  linesLong: "336,000",
  callableTools: "614",
  dispatchTools: "586",
  ganaTools: "28",
  bridgeFunctions: "151",
  testsPassing: "4205",
  testsSkipped: "22",
  testsFailing: "0",
  testsFailingNote: "All tests pass cleanly. Suite runs in ~120s.",
  languages: "7",
  memories: "49,486",
  galaxies: "11",
  // Tiered backend system (v24)
  backendTiers: "3",
  backendTiersDetail: "SQLite (per-galaxy) + DuckDB (analytics) + PostgreSQL (concurrency)",
  // Engine system
  engines: "28",
  engineGardens: "28",
  engineGanas: "28",
  // Prescience
  prescienceClaims: "28",
  prescienceValidated: "21",
  presciencePoints: "523",
  // Session analysis
  sessionsAnalyzed: "59",
  sessionTurns: "36,718",
  // STRATA
  strataFindings: "1,555",
  strataReduction: "58.9%",
  // Security
  securityScore: "85",
  // Performance benchmarks (July 2026)
  perfMedianMs: "29-33",
  perfP95Ms: "36-55",
  perfP99Ms: "38-86",
  perfSuccessRate: "100",
  perfMemoryMB: "0-0.18",
  perfThroughputRps: "29.38",
  benchmarkDate: "July 4, 2026",
} as const;

export const WM_FACT_TEXT = {
  toolSurface: `${WM_FACTS.callableTools} callable tools (${WM_FACTS.dispatchTools} dispatch + ${WM_FACTS.ganaTools} Gana meta-tools)`,
  testSuite: `${WM_FACTS.testsPassing} passing tests, ${WM_FACTS.testsSkipped} skipped, ${WM_FACTS.testsFailing} failures`,
  shortPassingSuite: `${WM_FACTS.testsPassing} passing tests with zero failures`,
  mcpSurface: `${WM_FACTS.callableTools} callable tools across ${WM_FACTS.ganaTools} Gana meta-tools`,
  memorySurface: `${WM_FACTS.memories} memories across ${WM_FACTS.galaxies} galaxies`,
  perfSummary: `${WM_FACTS.perfMedianMs}ms median latency, ${WM_FACTS.perfP95Ms}ms P95, ${WM_FACTS.perfSuccessRate}% success rate`,
  perfComparison: `3-10x faster than typical MCP implementations (29-33ms vs 100-300ms)`,
  perfFull: `Median: ${WM_FACTS.perfMedianMs}ms | P95: ${WM_FACTS.perfP95Ms}ms | P99: ${WM_FACTS.perfP99Ms}ms | Success: ${WM_FACTS.perfSuccessRate}% | Memory: ${WM_FACTS.perfMemoryMB}MB | Throughput: ${WM_FACTS.perfThroughputRps} req/s`,
} as const;
