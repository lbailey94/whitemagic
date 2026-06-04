export const WM_FACTS = {
  version: "22.2.0",
  verifiedDate: "June 03, 2026",
  linesShort: "178K",
  linesLong: "178,000",
  callableTools: "484",
  dispatchTools: "456",
  ganaTools: "28",
  testsPassing: "2379",
  testsSkipped: "0",
  testsFailing: "0",
  languages: "7",
} as const;

export const WM_FACT_TEXT = {
  toolSurface: `${WM_FACTS.callableTools} callable tools (${WM_FACTS.dispatchTools} dispatch + ${WM_FACTS.ganaTools} PRAT Gana meta-tools)`,
  testSuite: `${WM_FACTS.testsPassing} passing tests, ${WM_FACTS.testsSkipped} skipped, ${WM_FACTS.testsFailing} failures`,
  shortPassingSuite: `${WM_FACTS.testsPassing} passing tests with zero failures`,
  mcpSurface: `${WM_FACTS.callableTools} callable tools across ${WM_FACTS.ganaTools} Gana meta-tools`,
} as const;
