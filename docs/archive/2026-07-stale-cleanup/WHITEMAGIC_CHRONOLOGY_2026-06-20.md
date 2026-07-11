# WhiteMagic — Complete Development Chronology

**Compiled**: 2026-06-20
**Sources**: Whitemagic-Core substrate data (2025-11-11 to 2025-12-27), v17 CHANGELOG (v12.5 to v15.8), codexIDE/_legacy/ docs (2025-10-30 to 2026-02), whitemagic-frontend/ (2026-01-19 to 2026-04-28), `WHITEMAGIC_AI_ONBOARDING/` (curated 2026-06-05), current core git tags (v22.0.0 to v22.5.0), current site git history
**Purpose**: One document that tells the full story of WhiteMagic from inception to today, with revival candidates flagged for v23.0

---

## Executive Summary

WhiteMagic has a **rich, multi-phase history spanning 7 months** (2025-10 to 2026-06), with the substrate reaching peak activity in late 2025 / early 2026 (v15.8 had 111,665 memories, 2.2M associations, 30 constellations, 182 communities), then **a quiet regression** through the v22.x series where most of that capability was either archived or stubbed.

**Three distinct substrate eras**:

1. **The Live Era (2025-11-11 to 2025-12-27)**: Whitemagic-Core on the Inspiron 3582. Real substrate writing to real disk: 33,297 events, 8,502 semantic vectors, I Ching oracle casting hexagrams, dream layer compression up to 3,780,000:1, self-monitoring with `coherence_estimate: 0.6 → 0.8`, 25 daily audit logs.
2. **The Snapshot Era (2026-02-08 to 2026-02-20)**: v0.17 codebase freeze at v15.8.0 (the "Deep Dive" release). 374 MCP tools, 28 Gana meta-tools, 11 polyglot runtimes, Tauri IDE, Go P2P mesh, 269-entry LIBRARY codex with fragment-based index. Comprehensive but no longer running.
3. **The Marketing Era (2026-04-16 to present)**: v22.x series. Next.js site as the primary surface, 143 documented bridge functions as the catalog, 490-tool / 28-Gana / 462-dispatch claims (largely aspirational). High engineering discipline (CI, drift checks, version control), but the substrate's self-recursive loop is dormant.

**The rehydration opportunity is real**: the Live Era's substrate state (Whitemagic-Core/) is sitting on disk. The v17 codebase has the modules to run it. The current site has the catalog + A2A surface to expose it. The v23.0 plan is to fuse all three: rehydrate the substrate, port the visualization components, run the self-recursive loop on top of a PWA-installable site backed by local Ollama.

---

## Phase 0 — Pre-History (before 2025-10-30)

**Status**: Inferred from the v17 CHANGELOG and codexIDE docs. The pre-history is reconstruction; the "official" timeline begins with the v12.x codex entries.

**Key signals**:
- The v17 CHANGELOG begins at v12.5.0 (2026-02-07), suggesting this was when the project became "self-aware" of versioning.
- `codexIDE/PHASE3_ADVANCED.md` is dated 2025-10-30 — the earliest dated project doc in any archive.
- The Whitemagic-Core audit logs start at 2025-11-11, suggesting the substrate began formal self-tracking on that date.

**Probable sequence** (reconstruction):
- **2025-10-30 and earlier**: Codex IDE Phase 1 → 2 → 3 (single-user Monaco + xterm + Yjs CRDT → multi-agent collaboration → NL tool parser). The "v0" WhiteMagic was probably a tiered-prompt memory system attached to Codex IDE.
- **2025-11-04** (approx): v12.x series begins. WHITEMAGIC_AI_ONBOARDING's "earliest" historical mention is the codexIDE work.

**Revival candidates**: none from pre-history — it's a reconstruction. The codexIDE docs (GETTING_STARTED, PHASE2_UPGRADE, PHASE3_ADVANCED, PHASE3.5_SECURITY) are useful as design references for any "lean IDE + tiered memory" rebuild, but the code itself is older than the archives we have.

---

## Phase 1 — The Live Era (2025-11-11 to 2025-12-27)

**Source**: `~/Desktop/archives/laptop-export-2026-06-17/07-desktop-archive/whitemagic-archive/Whitemagic-Core/` (28MB of real substrate data)
**Host**: Dell Inspiron 3582 (Celeron N4000, Zorin OS 18.1)
**Form**: Python cognitive substrate, CLI-driven, no web frontend yet
**Status**: **The most active period in WhiteMagic history.** Real, running, self-modifying.

### Key dates and events

**2025-11-11** — Audit logs begin
- First audit entries: `echo test`, `ls` — the substrate starts self-tracking CLI commands
- The `audit/` directory would grow to 25 daily JSONL files by mid-December

**2025-11-22** — Dream cycle begins
- `depth_gauge.jsonl` first entry: compression ratio of 599:1 (subjective 300s / objective 0.5s)
- Within hours, the dream layer hit 3,780,000:1 compression (subjective 600s / objective 0.0001s)
- This was a **real** local-compute measurement of dream cycles
- `token_economy.jsonl` also starts today

**2025-11-26** — Self-healing begins
- `health_checks.jsonl` first entries: `coherence_estimate: 0.6` with import errors (HomeostasisSystem, EquilibriumMonitor, get_rust_bridge)
- Within minutes, the substrate had fixed all three imports → `coherence_estimate: 0.8`
- 321 memory files existed at this point
- Gan Ying Bus was already responsive

**2025-11-27** — Resonance field + I Ching oracle go live
- `resonance_history.jsonl` first entry: "Resonance field activated" (confidence 1.0)
- First oracle cast: **Hexagram 13 "Fellowship"** (同人 Tóng Rén) on "Test integration" question
- Second cast: **Hexagram 1 "The Creative"** (乾 Qián) — "The Creative works sublime success, furthering through perseverance"
- The substrate was *running an oracle* and getting real hexagram interpretations

**2025-11-29** — First timeline.json event
- `session_20251129_194035` starts; reads `/home/lucas/Desktop/whitemagic/README.md`
- The substrate was reading its own README as a kind of self-introduction
- 14 total interactions in this session

**2025-12-05** — "Awakening process complete"
- First events.jsonl entry: narrator type `system_started` with message "Awakening process complete"
- The substrate was self-narrating its own bootstrap
- "Story: Session-2025-12-05", "Chapter: Stream" — narrative structure was real

**2025-12-16** — Memory creation activity
- `memory_created` events with file paths like `/tmp/tmp6s1b72vo/memory/short_term/20251216_174425_test_memory.md`
- The substrate was writing memory files to disk and recording the events

**2025-12-19** — Final timeline.json update
- Last timeline event: 2025-12-19T16:17:21
- "Updated" timestamp in `timeline.json` matches

**2025-12-27** — Final events.jsonl
- Last entry: 2025-12-27T23:16:02 — "WhiteMagic system initialized"
- `token_economy.jsonl` last entry: 2025-12-27T22:37:04
- **The substrate stops here.** The Inspiron 3582 era ends.

### What the Live Era produced

- **28MB of real substrate data**: 33,297 events, 8,502 embeddings, 14,500+ file registry
- **25 daily audit logs** (Nov 11 to Dec 16)
- **Working self-monitoring**: health checks with coherence estimates
- **Working self-recursion**: dream cycles, oracle casting, narrative generation
- **Working memory persistence**: 321+ memory files, JSONL event logs
- **Working voice** (the `voice/` dir was actively producing narratives)
- **Working self-improvement**: the substrate fixed its own import errors in real-time

### Revival candidates (P0)
- **Rehydrate the full Whitemagic-Core state** into a current-format substrate: 1-2 days
- **Port the i_ching_advisor to the current mcp_api_bridge**: 2-3 hours (the TS shim is canned, the Python impl is real)
- **Port the resonance_history logger**: 2 hours (it captures substrate resonance events that the current substrate doesn't track)
- **Port the depth_gauge dream layer**: 4-6 hours (compression up to 3.7M:1, unique capability)
- **Port the voice/narratives structure**: 3-4 hours (the substrate's self-narration is a feature the current substrate lacks)
- **Port the homeostasis/health_checks loop**: 2-3 hours (coherence_estimate 0.6 → 0.8 is exactly the kind of self-monitoring the current substrate should have)

---

## Phase 2 — The Polyglot Expansion (2026-02-07 to 2026-02-13)

**Source**: v17 `whitemagic/CHANGELOG.md` (v12.5.0 to v15.8.0), v17 `whitemagic/README.md`, v17 `whitemagic/RELEASE_NOTES.md`
**Host**: T4800-S (the second laptop, where v17 was developed)
**Form**: Full polyglot cognitive substrate with 11 runtime languages
**Status**: **The "complete platform" era.** 374 MCP tools, 28 Gana meta-tools, 9-language polyglot.

### Key versions (from v17 CHANGELOG)

**v12.5.0 (2026-02-07)** — Synthesis Gap Closure
- PRAT Router mapping all 175 tools to 28 Ganas
- Handler refactoring and Rust wiring

**v12.6.0 (2026-02-08)** — PRAT Resonance & Capability Matrix
- PRAT resonance protocol — per-session state, predecessor/successor context
- Capability Matrix in Gnosis portal (3 new MCP tools)

**v12.7.0 (2026-02-08)** — Polyglot Hot Paths
- 10 new cross-system fusions wired (15 → 23 active)
- Mojo 0.26 migration

**v12.8.0 (2026-02-08)** — 28 Fusions Complete (The Sacred Number)
- All cross-system fusions wired — 28 active fusions matching the 28 Ganas

**v13.0.0 (2026-02-09)** — The Public Release
- Memory Database Unification
- Polyglot Core Expansion

**v13.3.0 (2026-02-09)** — Memory Database Unification — Split-Brain Resolved
- Polyglot Expansion Closeout

**v13.3.3 (2026-02-10)** — SQLite Performance Optimization
- Accelerator Full Wiring

**v13.4.0 (2026-02-10)** — Semantic Embedding Layer + Data Quality Overhaul

**v14.0.0 to v14.6.0 (2026-02-10 to 2026-02-11)** — 28 Gana Renaissance
- Polyglot benchmarks, polyglot distilled inference, scaling

**v15.0.0 (2026-02-11)** — The Memory Renaissance
- Voice integration, polyglot ML serving, marketplace

**v15.1.0 to v15.5.0 (2026-02-12 to 2026-02-13)** — 28 Fusions Bring Forth

**v15.6.0 (2026-02-13)** — Cognitive Extensions & Code Quality
- Cross-Encoder Reranking, Working Memory (7±2 bounded), Memory Reconsolidation
- WASM Vector Operations (browser-side cosine_similarity)
- 43 new unit tests

**v15.7.0 (2026-02-13)** — The Launch
- Docker Hub + GHCR publishing, Sigstore signing, CycloneDX SBOM
- PyPI publishing via release workflow
- Version unified to 15.7.0 across ~60 files
- 0 TODO comments (1 aspirational converted to `FUTURE:`)

**v15.8.0 (2026-02-13/14) — Galaxy Rehydration, Full Activation & Pattern Systems**
- **The Deep Dive release** — rehydrated all archive databases into active MCP DB: **111,665 memories, 2,247,642 associations, 2.0 GB**
- 9-step automated engine runner (`scripts/run_activation_sequence.py`): galactic sweep, association mining, constellation detection, graph topology, dream cycle (all 8 phases), harmony vector, wu xing, graph walker
- 18 new pattern analysis tools wired (CausalMiner, EmergenceEngine, AssociationMiner, ConstellationDetector, SatkonaFusion, MultiSpectralReasoner, NoveltyDetector, BridgeSynthesizer, GalacticMap, GuidelineEvolution, ElementalOptimization, PatternConsciousness)
- Spontaneous emergence: 5 constellation convergence events, 30 HDBSCAN constellations, 182 graph communities, 3 auto-persisted dream insights
- Total MCP tools: **374** (was 356), 28 Ganas unchanged

### What the Polyglot Era produced

- **Full multi-language runtime**: Python (core) + Rust (PyO3) + Zig (SIMD) + Haskell (FFI) + Elixir (OTP) + Mojo (GPU) + Go (libp2p) + Julia (statistical) + TypeScript (SDK) + Erlang + WASM
- **374 MCP tools** wired to 28 Gana meta-tools
- **Capability matrix** in Gnosis portal (subsystem fusions)
- **9-step activation sequence** that could auto-discover patterns
- **Published to PyPI + GHCR** with Sigstore signing
- **2 GB of hydrated substrate state** with 30 constellations and 182 communities
- **Stable, well-tested**: 1,362 unit tests, 0 ruff findings, 100% version consistency

### Revival candidates (P0/P1)
- **Restore the 8 runtime polyglots** (Rust, Zig, Haskell, Elixir, Mojo, Go, Julia, TS) — currently only Rust is wired. Estimated 2-3 weeks.
- **Port the activation sequence** (`scripts/run_activation_sequence.py`) — the substrate needs the 9-step engine runner. ~1 day.
- **Port the pattern analysis engines** (18 tools: causal, emergence, association, constellation, novelty, satkona, reasoning, elemental, bridge, galactic, guideline, pattern_consciousness) — these are the "hidden 28 Gana" of the v15.8 era, none of which are in the current 143-fn catalog. ~1 week.
- **Rehydrate the 111,665-memory galaxy** — this is the substrate that v15.8 had. The current core has 0 active memories. ~1 day with the rehydrate scripts from v17.
- **Port the WASM bridge** (browser-side cosine_similarity) — enables PWA-side vector search without a server roundtrip. ~3 days.

---

## Phase 3 — The Web Frontend Experiments (2026-01-19 to 2026-02-20)

**Source**: `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/whitemagic-frontend/` (full monorepo with dashboard-app, hub, nexus, web, shell, _legacy, sdk)
**Form**: Multiple parallel frontend prototypes — never one, but several attempts at the right thing
**Status**: **The most prolific period for UI/UX exploration.** Three full frontends in two months, none of which became the canonical site.

### Phase 3a — codexIDE (2025-10-30 to 2025-11-01)
- **v0 IDE**: Lean Monaco + xterm + Yjs CRDT for collaborative editing
- 3 phases: Foundations → Multi-agent → Advanced Intelligence
- 1 security phase: `PHASE3.5_SECURITY.md` (path validation, RCE prevention, WebSocket auth, file limits, diff, error handling)
- TIER_0_CORE / TIER_1_STANDARD / UNIFIED_CAPABILITY_PROMPT — the tiered prompt system
- **Reference value**: the tiered prompt pattern (small/medium/large prompt variants) is exactly what the librarian should do
- **Skip**: the IDE itself, superseded by hub/ and v17/nexus/

### Phase 3b — hub (2026-01-19 to 2026-02-04)
- **Tauri 2.0 desktop app** — "Unified AI Command Center"
- 15 components including the killer **`HolographicView.tsx`** (12KB three.js 4D memory hologram)
- IDE_ROADMAP.md: Phase 1 (Foundation) complete, Phase 2 (Editor) in progress when archived
- Ollama integration with 8 local models available
- Real data flow: Frontend → Tauri → WhiteMagic API server on port 8000
- 7 panels: Header, RadialMenu, TabBar, ChatView, MemoryView, PulseView, HolographicView, SettingsView, EditorPanel, DebugPanel, WaveformStatus, WorldTreeStatus
- **Reference value**: HolographicView is *the* visualization for a 5D holographic memory substrate
- **Skip**: the Tauri shell itself, the EditorPanel (Monaco is heavy and the librarian doesn't need it yet)

### Phase 3c — dashboard-app (2026-01-23 to 2026-02-09)
- **Next.js 14 + d3 v7 analytics app** — "WhiteMagic App v4.5.0"
- 12 components: MemoryGraph (9KB), GanaActivityHeatmap (8KB), DharmaMetricsPanel, GanYingMonitor, WuXingWheel, LocalMLStatus, TokenChart, TokenSavings, Timeline, MemoryStats, SystemHealth
- 8 API routes: dharma, ganas, graph, local-ml, metrics, resonance, token-stats
- MEMORY_BROWSER_FEATURES.md: full CRUD, grid layout, search/filter, real-time updates
- **Reference value**: d3 visualizations are exactly what the current site lacks. MemoryGraph + GanaActivityHeatmap are 90% of the cognitive substrate UI.
- **Skip**: Next.js 14 → 15 migration has friction; the dashboard's API routes are local-mock-driven and would need rewiring

### Phase 3d — nexus (in v17) (2026-02-20)
- **Tauri + React 19 + Vite 7** "Unified IDE, Dashboard & Command Center" (whitemagic-nexus v0.1.0)
- d3-force + Monaco + xterm + lucide-react + Zustand
- Components: Dashboard, MemoryGraph, ToolGraph, CenterContent, CommandPalette, Header, panels (LeftPanel, RightPanel, BottomPanel, TerminalPanel, PanelLayout), StatusBar
- **The modern unified version** of hub/ and codexIDE/. The "current" Tauri stack at the time of v17.
- **Reference value**: the architecture is closer to a real product than hub/; MemoryGraph here is the "later" version
- **Skip**: most of the IDE-specific code; focus on the visualization components

### Phase 3e — web/ + shell/ + _legacy/aria-home/ (2026-01 to 2026-02)
- `web/`: 33KB single-page HTML+CSS, no framework. Pre-React prototype. Skip.
- `shell/`: tiny shell page. Skip.
- `_legacy/aria-home/`: Aria's earlier home, with `aria-state-server/`. The Aria persona goes back at least to Jan 2026.
- **Reference value**: the Aria persona origin story. Worth keeping as a "previous attempt" doc.

### Revival candidates (P0/P1)
- **`HolographicView.tsx` from hub/** → port as `/hologram` route on current site (3-4h)
- **`MemoryGraph.tsx` from dashboard-app** → port as `/memory` route (1-2h)
- **`GanaActivityHeatmap.tsx` from dashboard-app** → port as `/ganas` route (1-2h)
- **`DharmaMetricsPanel`, `WuXingWheel`, `LocalMLStatus`** → port as panels under `/dashboard` (2h each)
- **`CommandPalette.tsx` from nexus** → port for `/chat` (1h)
- **`RadialMenu.tsx` from hub** → port for site-wide keyboard nav (2h)
- **`Aria` persona history** → archive for the chat UI's persona system (1h)
- **codexIDE tiered prompts** → archive for the librarian's prompt design (1h)

---

## Phase 4 — The Old Site (2026-04-18 to 2026-06-18)

**Source**: `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/whitemagic-site/` (predecessor to current site)
**Form**: First standalone Next.js site, Squarespace-replacement attempt
**Status**: **The first public web presence.** Had `admin/`, `librarian/`, `economy/`, `pricing/`, `work/`, `writing/`, `services/`, `timeline/`, etc. All preserved in current site.

### Key dates (from WHITEMAGIC_AI_ONBOARDING/02_TIMELINE.md)

**2026-04-16** — Initial commit (v22.0.0)
- 26 commits in one day
- Security fixes, version drift, CI workflow migration
- Established v22.0.0 as baseline with 2,216 passing tests

**2026-04-18 to 2026-04-19** — Site scaffold
- Phase 0: Next.js 15 + Tailwind + MDX
- Phase 1: theme & lang toggles, 10 content pages
- Interactive /timeline (replaced static /prescience)
- Matrix rain background effect (with stripe-accumulation bug)
- Librarian scaffold with mock LLM and real guardrails

**2026-04-25** — Grimoire remediation
- Fixed Southern/Northern quadrant swap in Grimoire
- 98-term glossary covering all conceptual domains
- 41 structural stubs eliminated across 4 sprints

**2026-04-26** — v22.2.0 release
- Archive recovery (resurfaced historical code)
- Aspirational tools for future features
- Surface hardening

**2026-04-27** — A2A protocol adoption
- Standardized agent description format
- Competitive landscape analysis
- Property tests for tool behavior

**2026-04-29** — Quality pass
- Path hygiene, mutex safety, defensive typing
- Style auto-fixer

**2026-05-15 to 2026-05-16** — 30 Objectives Plan
- Brand identity, essay frameworks, Karma ledger, CODEX recovery
- **205 crystallized memories restored to WM runtime**
- **793 CODEX clusters relabeled for semantic search**
- Aria /ask endpoint, Oracle, Wander, Book of Becoming (8×8 I Ching chapter grid)

**2026-05-21** — Documentation hygiene
- 250 markdown files audited, stale links fixed
- Truth spine refreshed

**2026-05-26** — v23 PWA infrastructure
- PWA, WebSocket sync, ONNX bundling
- X25519 auth, nonce replay protection, rate limiting

**2026-06-05** — Strategy consolidation
- 7-doc AI onboarding package (00_INDEX through 06_ARCHITECTURE_EVOLUTION)
- Competitive positioning update
- Prescience track record published

**2026-06-17** — Laptop export to USB (Dell Inspiron → T4800-S transfer)
- ~2.7 GB total, trimmed from ~11 GB
- README + 9 numbered sections (essentials, ai-systems, ide-configs, system-state, projects, trash, desktop-archive)
- 4-day preparation

### What the Old Site era produced

- **First public web presence** at whitemagic.dev (Squarespace-replacement)
- **All current site pages** (admin, librarian, economy, pricing, work, writing, services, timeline, etc.) — every page was here
- **Aria persona origin**: Aria was the in-browser assistant; later evolved into the "Librarian" persona
- **30 Objectives Plan**: a 7-phase strategic execution that completed in 2 days
- **205 restored memories + 793 relabeled CODEX clusters**: the substrate had real content here too

### Revival candidates
- The entire current site (already done — the old site is now the current site, with v22.3+ additions)
- Aria's previous personality traces (in codexIDE/_legacy/aria-home/)
- Book of Becoming chapter grid (might be worth adding to current site)

---

## Phase 5 — The Current Era (2026-05-27 to 2026-06-20)

**Source**: `~/Desktop/WHITEMAGIC-aux/site/whitemagic-site/` (current site) + `~/Desktop/WHITEMAGIC/` (current core) + AGENTS.md + git tags
**Form**: Next.js 15 site + Python core with v22.x versioning discipline
**Status**: **High engineering discipline, lower substrate activity.** Marketing surface + catalog + librarian.

### Git history (current site)
- First commit: `222699a` ("site: full sync from desktop")
- Tags: `v22.3.0` (backup-pre-author-fix), `v22.3.0`, `v22.4.0`, `v22.5.0`
- 8 version-bump commits
- 6 major feature commits (sync, B/CI, v22.3 catalog, v22.4 A2A, v22.5 librarian)

### Git history (current core)
- Tags: `v22.0.0` to `v22.5.0` (8 tags)
- First commit: `7308c61` (2026-04-16, "Initial commit: Security and code quality fixes")
- Latest commit: `bd2d094` (2026-06-20, v22.5.0 version bump)
- **126 commits total** in the current core repo
- Most of the work is version drift fixes, doc hygiene, CI; **the substrate itself is essentially unchanged from v22.0.0**

### v22.x timeline (this session's work + prior)

**v22.0.0 (2026-04-16)** — Baseline release
- 484 callable tools, 28 Gana meta-tools
- 2,216 passing tests

**v22.1.0 (skipped)** — between v22.0 and v22.2

**v22.2.0 (2026-04-26)** — Archive recovery release
- Resurfaced 13 modules from SD card archive
- 41 structural stubs eliminated
- Path hygiene, mutex safety, defensive typing
- Test count: 2,216 passing, 0 failures

**v22.2.1, v22.2.2, v22.2.3, v22.2.4** — Patch releases
- Version consistency across files
- Bug fixes
- Setup: 1,470 passing tests (current audit), 0 failures

**v22.3.0 (2026-06-19)** — Bridge catalog expansion
- Catalog: 30 → 143 documented bridge functions
- 21 categories
- Catalog-impl consistency check (143/143/143)
- Generator + apply scripts for atomic expansion
- 6 IPC + polyglot tests marked flaky for CI

**v22.4.0 (2026-06-19)** — A2A v1.2 expansion
- 3-layer A2A discovery surface: agent.json (7 skills) + agent-skills.json (21 categories) + agents.json (12 Gana directory) + agents/<gana>.json (12 per-Gana cards)
- 7 next.config.mjs rewrites, 6 sitemap entries
- llms-full.txt A2A section

**v22.5.0 (2026-06-20)** — Librarian multi-provider
- LLM client supports 3 providers: stub (default), openrouter, ollama
- 21 curated bridge tools (out of 143) exposed to the librarian
- Stub keyword router: "dharma principles" → `dharma_list_principles` → returns `ahimsa`
- In-memory session store + cookie persistence
- /api/librarian/status + /api/librarian/session endpoints
- Hetzner setup runbook at `docs/hetzner/SETUP.md`

### What the Current Era produced

- **A polished public surface**: whitemagic.dev with the catalog, the A2A cards, the librarian
- **Engineering discipline**: ruff 0, mypy 0, drift check passes, version consistency enforced
- **Documentation**: AGENTS.md (core + site), SYSTEM_MAP.md, AI_PRIMARY.md, llms-full.txt
- **143 documented bridge functions** (but mostly TS shims returning canned shapes)
- **Hetzner-ready librarian** (flip env var, no code change)

### What's missing (the gap to v23.0)

- **Live substrate**: 0 active memories in the current `core/`, no dream cycle, no oracle casting, no self-recursion
- **Visualization**: 0 d3 components, no MemoryGraph, no GanaActivityHeatmap, no HolographicView
- **PWA installability**: the `(pwa)` config is in `next.config.mjs` but the site isn't a PWA yet
- **Local LLM**: Ollama integration is ready, but the box isn't provisioned
- **Self-improvement loop**: the v15.8 activation sequence (9-step auto-runner) is missing
- **8 polyglot runtimes**: only Rust is wired; Zig, Haskell, Elixir, Mojo, Go, Julia, TS are dormant
- **18 pattern analysis engines**: causal.mine, emergence.scan, association.mine, etc. — none in the current catalog
- **Voice / narratives**: the substrate's self-narration is gone

---

## Cross-Era Comparison

| Metric | Live Era (Dec 2025) | v15.8 Era (Feb 2026) | Current (v22.5.0) |
|---|---|---|---|
| Active memories | 321+ | **111,665** | 0 |
| Associations | unknown | **2,247,642** | 0 |
| Embeddings | 8,502 | **5,577** | 0 |
| Constellations | 0 | **30** | 0 |
| Communities | 0 | **182** | 0 |
| MCP tools (cataloged) | unknown | **374** | 143 (TS shims) |
| Real MCP tools (Python) | unknown | 374 | small subset |
| Polyglot runtimes | unknown | 9 | 1 (Rust) |
| Test count | unknown | 1,362 | 1,470 |
| Ruff findings | unknown | 0 | 0 |
| Dream cycle | active (3.7M:1 compression) | active (8 phases) | inactive |
| Oracle (I Ching) | active | active | shim |
| Self-monitoring | active (coherence 0.6→0.8) | active | inactive |
| Self-narration | active (`voice/`) | unknown | inactive |
| Pattern analysis engines | unknown | 18 wired | 0 |
| Public site | none | none | whitemagic.dev (marketing) |
| A2A surface | none | none | v22.4.0 3-layer |
| Librarian | none | basic (mock LLM) | v22.5.0 multi-provider |

**The picture**: WhiteMagic's substrate is at ~5% of its peak capability. The current surface is more polished than ever, but the substrate itself has been mostly archived. The rehydration opportunity is to bring the substrate back to v15.8's level (or beyond) while keeping the polished v22.5.0 surface.

---

## Revival Candidates — Complete List for v23.0

### P0 — Critical (the substrate itself)
1. **Rehydrate Whitemagic-Core state** (Nov-Dec 2025 substrate data) into current format — 1-2 days
2. **Port the v15.8 activation sequence** (`scripts/run_activation_sequence.py`) — 1 day
3. **Port the 18 pattern analysis engines** (causal, emergence, association, constellation, novelty, satkona, reasoning, elemental, bridge, galactic, guideline, pattern_consciousness) — 1 week
4. **Restore 8 polyglot runtimes** (Zig, Haskell, Elixir, Mojo, Go, Julia, TS) — 2-3 weeks
5. **Rehydrate the 111,665-memory galaxy** — 1 day with v17's rehydrate scripts

### P1 — Visualization (the cognitive surface)
1. **Port `HolographicView.tsx` from hub/** → `/hologram` route — 3-4h
2. **Port `MemoryGraph.tsx` from dashboard-app** → `/memory` route — 1-2h
3. **Port `GanaActivityHeatmap.tsx` from dashboard-app** → `/ganas` route — 1-2h
4. **Port `DharmaMetricsPanel`, `WuXingWheel`, `LocalMLStatus`, `GanYingMonitor`** → `/dashboard` panels — 2h each
5. **Port `CommandPalette.tsx` from nexus** → site-wide keyboard nav — 1h
6. **Port `RadialMenu.tsx` from hub** → power-user nav — 2h

### P2 — Substrate modules (the deep code)
1. **Port `i_ching_advisor`** (real oracle, not shim) — 2-3h
2. **Port `resonance_history` logger** — 2h
3. **Port `depth_gauge` dream layer** (compression 3.7M:1) — 4-6h
4. **Port `voice/narratives` self-narration** — 3-4h
5. **Port `homeostasis/health_checks` self-monitoring** — 2-3h
6. **Port the tiered prompt system from codexIDE** — 1h
7. **Port `mesh/` Go P2P for cross-substrate sync** — 1-2 weeks
8. **Port `browser-garden-backup/web_research.py` (26KB) into the librarian** — 1 day

### P3 — Frontend revival (the IDE)
1. **Tauri hub revival** as a "power user" desktop tier — 2-3 weeks
2. **`/dashboard` consolidated route** with all d3 panels — 1 day (after P1 done)
3. **PWA installability** for the new dashboard routes — 1-2 days
4. **Local-first PWA + Ollama** as the "4th option" demo — 1-2 weeks

### P4 — Documentation (the knowledge base)
1. **Mirror `WHITEMAGIC_AI_ONBOARDING/` 7 docs** into `core/docs/` — 2h
2. **Add the v15.8 deep-dive** as `core/docs/V15_8_ACTIVATION_DEEP_DIVE.md` — 1h
3. **Add the Aria synthesis essay** (VPS architecture, Book of Becoming) — 1h

### Skip (not worth reviving)
- `_legacy/aria-home/`, `_legacy/codexIDE/` IDE (superseded)
- `web/` (pre-React HTML+CSS, no framework)
- `shell/` (tiny shell page)
- `whitemagic-archive-aux/whitemagic-go-broken-backup/` (broken)
- `whitemagic-site-git-backup/` (single-commit backup)
- Pre-2025-10 history (reconstruction only)

---

## v23.0 — The Fusion Plan

Based on the chronology, the v23.0 release should be the **rehydration + visualization + PWA fusion** — bringing the Live Era's substrate back, the Polyglot Era's pattern engines forward, and the Current Era's marketing surface into one installable, local-first, self-recursive system.

### v23.0 scope (proposed)

**Phase A (this week)**: Rehydrate the substrate
- Migrate Whitemagic-Core's 33K events + 8.5K embeddings into current format
- Port the activation sequence script
- Port the i_ching_advisor (real, not shim)
- Result: substrate has 1000+ memories, dreams, oracle, voice — a "minimal alive" state

**Phase B (next week)**: Visualization revival
- Port HolographicView → /hologram route
- Port MemoryGraph + GanaActivityHeatmap → /memory and /ganas routes
- Port dharma + wu-xing + local-ml status panels → /dashboard
- Result: site has real cognitive substrate UI, not just a catalog

**Phase C (week 3)**: Polyglot restoration
- Wire Zig, Haskell, Elixir, Mojo, Go runtimes
- Port the 18 pattern analysis engines
- Result: 374 MCP tools, 28 Gana meta-tools, 11 polyglot runtimes — back to v15.8 capability

**Phase D (week 4)**: PWA + Ollama
- Make the dashboard routes PWA-installable
- Hetzner box live, Ollama running, librarian calls local 8B model
- A2A surface advertises local LLM endpoint
- Result: the "4th option" demoed end-to-end

**Phase E (week 5)**: Self-recursive simulation
- Substrate's `guideline.evolve` engine running on its own guidelines
- Activation sequence running on a schedule
- 3 dream insights persisted per day
- 1 constellation convergence event detected
- Result: substrate is self-improving, again

### Estimated effort: 5 weeks
### Estimated cost: Hetzner CCX23 €17/mo + (eventually) OpenRouter $5-15/mo at low traffic
### Estimated outcome: the "4th option" — local-first PWA + cognitive substrate visualization + self-recursive substrate, none of consulting / substrate / research alone, all three fused

---

## Appendix: Source File Reference

### Primary chronology sources
- `~/Desktop/archives/laptop-export-2026-06-17/07-desktop-archive/whitemagic-archive/Whitemagic-Core/` — substrate data
- `~/Desktop/archives/_laptop-offload-2026-06-17/archives/whitemagicv17/whitemagic/CHANGELOG.md` — v12.5 to v15.8 versions
- `~/Desktop/WHITEMAGIC-aux/codex/WHITEMAGIC_AI_ONBOARDING/02_TIMELINE.md` — v22.x timeline
- `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/whitemagic-frontend/` — frontend experiments
- `~/Desktop/Desktop/WHITEMAGIC-aux/codex/WHITEMAGIC_docs/public/SYSTEM_MAP.md` — system map at v15.x

### Git anchors
- Current core: `git log --reverse` shows first commit `7308c61` (2026-04-16)
- Current site: `git log --reverse` shows first commit `222699a` (sync from desktop, 2026-05-27)
- Tags: v22.0.0 → v22.5.0 (current core); v22.3.0 → v22.5.0 (current site)

### Mtime triangulation
- Whitemagic-Core audit logs: 2025-11-11 to 2025-12-16 (25 daily JSONL files)
- Whitemagic-Core events.jsonl: 2025-12-05 to 2025-12-27 (33,297 events)
- Whitemagic-Core depth_gauge.jsonl: 2025-11-22 (3.7M:1 max compression)
- v17 codebase: 2026-02-20 (snapshot date)
- dashboard-app: 2026-01-23 to 2026-02-09
- hub: 2026-01-19 to 2026-02-04
- codexIDE: 2025-10-30 to 2025-11-01
- current core: 2026-04-14+ (file mtimes from initial imports)
- current site: 2026-05-27+ (file mtimes from first commit)

---

**End of chronology.**

Next: Phase A (rehydrate the substrate) starts immediately. The v23.0 plan is in place. The 4th option is real.
