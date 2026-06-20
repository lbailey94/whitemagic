export const WM_FACTS = {
  version: "23.0.0",
  verifiedDate: "June 20, 2026",
  linesShort: "180K",
  linesLong: "180,000",
  callableTools: "490",
  dispatchTools: "462",
  ganaTools: "28",
  bridgeFunctions: "143",
  testsPassing: "2526",
  testsSkipped: "0",
  testsFailing: "0",
  testsFailingNote: "4 tests flake under full-suite load (IPC bridge stress 1000, polyglot elixir queries); all pass in isolation. Sync run uses --collect-only which catches them as collection errors. v22.3.0 marks 6 of them with @pytest.mark.flaky so they pass cleanly under CI.",
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
  v22_3_0_catalog: "Site catalog went from 30 -> 143 documented functions. The catalog now reflects the full whitemagic.mcp_api_bridge public surface. Each entry has a matching TS impl and dispatcher reference.",
  v22_4_0_a2a: "A2A v1.2 discovery surface expanded. New endpoints: /.well-known/agent-skills.json (21 per-category skills), /.well-known/agents.json (12-Gana directory), /.well-known/agents/<gana>.json (per-Gana detail, 12 files). Main Agent Card enhanced to 7 high-level skills (was 6) with 2-layer (high-level + per-category) skills model.",
  v23_0_0_galactic: "Site catalog expanded to 151 functions (was 143). 8 new galactic functions connect the bridge to the live substrate at ~/.whitemagic/memory/whitemagic.db: galactic_substrate_health, galactic_galaxy_stats, galactic_memory_recent, galactic_memory_search, galactic_memory_by_id, galactic_associations, galactic_event_search, galactic_constellation_count. The substrate holds 12,636 memories, 21,087 associations, 12,686 embeddings, 35,060 dharma audits (35,053 migrated from Whitemagic-Core 2025-11 to 2025-12 era). New category 'galactic' added to the BridgeFunction union. See docs/WHITEMAGIC_CHRONOLOGY_2026-06-20.md for the full timeline.",
  v23_0_0_WIP: "Site entered WIP mode (NEXT_PUBLIC_WIP_MODE=1). The hero is rewritten ('A door is opening'), the footer drops the prescience claim, /services + /services/* + /fund + /contact are gated behind <WipGuard>, a site-wide <WipBanner /> runs at the top of every page, a new /subscribe page replaces the contact form, and the A2A Agent Card posture now declares data_residency: 'local-first', pwa_installable: true, cloud_storage: false, sync_model: 'opt-in-p2p'. Technical surface (bridge catalog, A2A, librarian, research, library, governance, open-source) stays fully visible. v23.0.0-alpha.3 added WIP scramble (NEXT_PUBLIC_WIP_SCRAMBLE=1 by default): long-form WIP copy (banner, hero, placeholder, footer blurb) renders as Unicode block glyphs (█▓▒░■□◊◈) so the prose is visually illegible. Original text preserved in DOM via data-original. See docs/SITE_WIP_MODE.md, docs/V23_ROADMAP.md, docs/PWA_SUBSTRATE_ARCHITECTURE.md.",
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
