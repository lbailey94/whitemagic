# WhiteMagic Frontend & Archive Inventory

**Date**: 2026-06-20
**Scope**: All whitemagic-related artifacts on the laptop, plus UI/visualization/local-model integration candidates
**Goal**: Identify what can be folded back into the current site + cognitive substrate

---

## TL;DR — what to weave back in

| Priority | Artifact | Why | Effort |
|---|---|---|---|
| 🔴 **P0** | `whitemagic-frontend/dashboard-app/app/components/MemoryGraph.tsx` | 9KB d3 force-directed memory graph — the visualization the current site lacks | Port 1-2h |
| 🔴 **P0** | `whitemagic-frontend/dashboard-app/app/components/GanaActivityHeatmap.tsx` | 8KB d3 Gana activity heatmap (28-Gana quadrant) | Port 1-2h |
| 🔴 **P0** | `whitemagic-frontend/hub/src/components/HolographicView.tsx` | 12KB three.js 4D memory hologram — exactly the 5D/4D visualization the cognitive substrate is missing | Port 3-4h |
| 🟠 **P1** | `whitemagic-frontend/hub/src/components/MemoryView.tsx` | 12KB memory explorer | Port 2-3h |
| 🟠 **P1** | `whitemagic-frontend/dashboard-app/app/components/{DharmaMetricsPanel,GanYingMonitor,WuXingWheel,LocalMLStatus}.tsx` | dharma + gan-ying + wu-xing + local-ML status panels | Port 2h each |
| 🟡 **P2** | `whitemagic-frontend/hub/src/components/{PulseView,SettingsView,EditorPanel,DebugPanel,ChatView}.tsx` | Tauri desktop app components (radial menu, monaco editor, etc.) | Future desktop |
| 🟢 **P3** | `whitemagic-frontend/hub/` (Tauri 2.0 app) | Full desktop client; can be the "PWA fallback" for desktop | Big lift |
| 🟡 **P2** | `whitemagic-frontend/dashboard-app/` (Next.js 14) | Working analytics app; the substrate *was* visualized, and v4.5 had this | Future port |
| 🟡 **P2** | `whitemagic-codex` (8 Rust crates) | codex-chunk, -consolidate, -core, -embed, -export, -extract, -index. The indexer that produced the LIBRARY codex | Review for integration |
| 🟢 **P3** | `whitemagicv17` (full v0.17 codebase) | 22 dirs of Python, full IDE, 7 polyglot runtimes. The "before" snapshot | Reference only |
| 🟢 **P3** | `Whitemagic-Core/` (live substrate data) | 33,297 events, 8,502 semantic vectors, real cognitive state from 2025-12 | Reference + revival source |
| 🟡 **P2** | `WHITEMAGIC_AI_ONBOARDING/` (00_INDEX–06_ARCHITECTURE_EVOLUTION + data/) | Comprehensive AI-handover docs with git history, artifact catalog, architecture evolution | Onboard any new agent |
| 🟢 **P3** | `whitemagic-frontend/_legacy/aria-home/` + `_legacy/codexIDE/` + `_legacy/nexus/` | Earlier iterations — reference for "what didn't work" | Skip |
| 🟢 **P3** | `whitemagic-archive-aux/whitemagic-frontend/_legacy/aria-home/aria-state-server/` | Even older state server — superseded by current librarian | Skip |
| ⚪ **Skip** | `whitemagic-archive-aux/whitemagic-go-broken-backup/` | "broken-backup" — kept as a curiosity | Skip |
| ⚪ **Skip** | `whitemagic-archive-aux/whitemagic-frontend/web/` (HTML+CSS, no framework) | Pre-React single-page site, ~2024 design | Skip |
| ⚪ **Skip** | `whitemagic-archive-aux/whitemagic-frontend/shell/` | Tiny shell page, no components | Skip |
| ⚪ **Skip** | `WHITEMAGIC-aux/site/whitemagic-site-git-backup/` (pre-refactor backup) | One-commit backup, superseded | Skip |
| ⚪ **Skip** | `~/_private_journal-LIBRARY` (266 files, 24MB) | Personal journal library — not whitemagic | Skip |

---

## 1. The Big Three — what to revive first

### 1.1 `whitemagic-frontend/dashboard-app/` — v4.5.0 Next.js analytics app

**Path**: `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/whitemagic-frontend/dashboard-app/`
**Version**: whitemagic-app 4.5.0
**Stack**: Next.js 14 + React 18 + d3 v7 + lucide-react + Tailwind
**Status**: Self-contained working app. The `app/page.tsx` (7.8KB) and 12 components (8KB-9KB each) are the gold.

**Components** (all client-side d3 / canvas):
- `MemoryGraph.tsx` (9KB) — force-directed graph of memory/tag/topic nodes
- `GanaActivityHeatmap.tsx` (8KB) — 28-Gana activity by quadrant (east/south/west/north)
- `DharmaMetricsPanel.tsx` (6.5KB) — dharma metrics dashboard
- `GanYingMonitor.tsx` (7.8KB) — gan-ying event monitor
- `LocalMLStatus.tsx` (7.7KB) — local ML model status panel
- `WuXingWheel.tsx` (3KB) — 5-element balance wheel
- `TokenChart.tsx`, `TokenSavings.tsx`, `Timeline.tsx`, `MemoryStats.tsx`, `SystemHealth.tsx`

**API routes** (8 endpoints under `app/api/`):
- `dharma/`, `ganas/`, `graph/`, `local-ml/`, `metrics/`, `resonance/`, `token-stats/`

**Why this matters**: The current site has the catalog (143 functions) but no visualization of the substrate. The dashboard-app *is* the visualization of the substrate. It's a 2024-2025 era app that already has the conceptual surface area (dharma + ganas + memory + tokens + local ML) — exactly what the cognitive substrate thesis needs to be demoable.

**Effort to revive**: 2-3 hours to port as a `/dashboard` route on the current site. The API routes can be kept simple (mock data + bridge function calls) and the components can be ported with minor prop changes (d3 v7 → d3 v7 is the same; React 18 → React 19 is backward compat).

### 1.2 `whitemagic-frontend/hub/` — Tauri 2.0 desktop app

**Path**: `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/whitemagic-frontend/hub/`
**Version**: whitemagic-hub 7.4.0
**Stack**: Vite + React 18 + @react-three/fiber + @tauri-apps/api v2 + Monaco Editor + xterm + Tailwind
**Status**: Phase 1 (Foundation) was complete per the `IDE_ROADMAP.md`. Phase 2 (Editor) was in progress.

**The killer component**: `HolographicView.tsx` (12KB) uses three.js to render 4D memory coordinates as a holographic cluster graph. This is *the* visualization for a "5D holographic memory" substrate. It renders `Cluster` objects with `center: [x, y, z, w]` (4D!) and `Attractor` objects with mass + event horizon — exactly the language of 5D holographic memory.

**Other components** (15 total):
- `HolographicView.tsx` (12KB, three.js) — **THE prize**
- `MemoryView.tsx` (12KB) — memory explorer
- `PulseView.tsx` (14KB) — system pulse dashboard
- `SettingsView.tsx` (12KB) — settings UI
- `EditorPanel.tsx` (9KB) — Monaco editor
- `DebugPanel.tsx` (10KB) — service health
- `ChatView.tsx` (6.5KB) — chat
- `HolographicCore` sub-component — the 3D rendering core
- `RadialMenu.tsx` (4KB) — radial navigation
- Plus `Header`, `TabBar`, `WaveformStatus`, `WorldTreeStatus`

**Tauri config**: `src-tauri/tauri.conf.json` for desktop packaging, with `Cargo.toml`.

**Why this matters**: The hub was the actual IDE/desktop vision. It's not a marketing surface — it's where you'd run the substrate. A Tauri shell wrapping the current site + a holographic view would be a "PWA + desktop" deployment. Or just port the HolographicView into the site as `/hologram`.

**Effort to revive**: 4-6 hours to extract HolographicView + MemoryView and port as Next.js client components. The Tauri shell itself is a separate project (could be revived later).

### 1.3 `whitemagic-frontend/dashboard-app/MEMORY_BROWSER_FEATURES.md` + `IMPROVEMENTS.md` + `PREVIEW_GUIDE.md`

**Path**: same as 1.1
**Status**: Living product spec from when the dashboard was being designed.

**Why this matters**: These docs describe the *product intent* of the dashboard, including specific UX patterns (grid layout, type filter, tag display, real-time search, CRUD modals). If we revive the dashboard, these are the spec to follow.

---

## 2. The Cognitive Substrate — real historical data

### 2.1 `Whitemagic-Core/` (Inspiron 3582 era, ~Oct-Dec 2025)

**Path**: `~/Desktop/archives/laptop-export-2026-06-17/07-desktop-archive/whitemagic-archive/Whitemagic-Core/`
**Status**: Live cognitive substrate state from 2025-11-29 to 2025-12-19.

**Contents** (60+ files, 28MB total):
- `events.jsonl` (24MB, 33,297 events) — voice_expressed, memory_created, system_started, oracle_cast, pattern_detected, memory_recalled
- `awareness.jsonl` (123KB) — self-aware snapshots scanning 14,500+ files at 6M+ lines
- `depth_gauge.jsonl` (62KB) — dream layer compression ratios up to 3.7M:1
- `health_checks.jsonl` (6KB) — coherence 0.6 → 0.8 over time
- `resonance_history.jsonl` (189KB) — resonance events
- `token_economy.jsonl` (208KB) — token usage
- `seen_registry.json` (558KB) — 14,500+ file registry
- `whitemagic.db` (131KB) — SQLite substrate database
- `embeddings/` (8,502 local semantic vectors, all-MiniLM-L6-v2)
- `audit/` (25 daily audit logs, Nov-Dec 2025)
- `akashic/` (bloom-condition seed memories)
- `emotional_memories/` + `emotional_memory/` (narrative timeline)
- `transcripts/` (4 conversation transcripts)
- `voice/` (voice output samples)
- `terminals/` + `terminal_sessions/`
- `config.yaml` (power tier, hybrid search, PROD profile)

**Why this matters**: This is the *real historical substrate* — actual running data, not documentation. It has the structure that the current `core/` is trying to replicate (`memory_v2/`, `cache/`, `temporal/`, etc.). The data could be:
- **Reviewed** for patterns (what worked, what didn't)
- **Anonymized and loaded** as demo data for the dashboard
- **Migrated** to the current substrate format

**Effort**: 1 hour to inventory; 1 day to migrate useful parts (memory, embeddings, audit) to current substrate; 1 week to fully integrate.

### 2.2 `whitemagicv17/` (v0.17 of the codebase)

**Path**: `~/Desktop/archives/_laptop-offload-2026-06-17/archives/whitemagicv17/`
**Status**: Snapshot of the v0.17 codebase (Feb 20 2026).

**Contents**: 22 top-level dirs, 55 subdirs in `whitemagic/`. Has a more complete Python package than the current `core/`.

**Notable additions vs current core**:
- `agents/`, `ai/`, `automation/`, `cascade/`, `cli/`, `continuity/`, `edge/`, `emergence/`, `execution/`, `grimoire/`, `hardware/`, `immune/`, `inference/`, `local_ml/`, `maintenance/`, `marketplace/`, `mesh/`, `oms/`, `oracle/`, `orchestration/`, `parallel/`
- 7 polyglot runtimes: `whitemagic/` (Python), `whitemagic-go/`, `whitemagic-julia/`, `whitemagic-mojo/`, `whitemagic-rust/`, `whitemagic-zig/`, plus `elixir/`, `haskell/`, `mesh/` (Go)

**Also**:
- `nexus/` (Tauri desktop IDE, React 19 + Vite 7 + d3-force + Monaco + xterm)
- `mesh/` (Go P2P, libp2p + pubsub + WebRTC + QUIC + Redis + RQ)
- `whitemagic-mojo/` (Mojo language port)
- `sdk/typescript/` (TypeScript SDK for the substrate)
- `tests/`, `eval/`, `examples/`, `docs/`
- `examples/`, `eval/`, `tests/`

**Why this matters**: v0.17 is the "everything you had working" snapshot. Has docs/, examples/, an SDK, an IDE, polyglot, etc. If we want to revive the cognitive substrate properly, v0.17 is the most complete reference.

**Effort**: 1-2 days to diff against current `core/`, identify what's missing, and port back.

### 2.3 `WHITEMAGIC_AI_ONBOARDING/` (00_INDEX–06_ARCHITECTURE_EVOLUTION + data/)

**Path**: `~/Desktop/WHITEMAGIC-aux/codex/WHITEMAGIC_AI_ONBOARDING/`
**Status**: 7 markdown docs + 7 data files. Generated 2026-06-05.

**Docs** (all 13-26KB):
- `00_INDEX.md` (13KB) — master index with reading guides
- `01_PROJECT_OVERVIEW.md` (19KB) — what WhiteMagic is, core concepts, architecture
- `02_TIMELINE.md` (23KB) — chronological history from inception to present
- `03_GIT_HISTORY.md` (20KB) — commit patterns, version evolution, milestones
- `04_CONVERSATION_INSIGHTS.md` (26KB) — key decisions from extracted conversations
- `05_ARTIFACT_CATALOG.md` (25KB) — all artifacts with summaries and locations
- `06_ARCHITECTURE_EVOLUTION.md` (27KB) — how the system changed over time

**Data files**:
- `data/git_timeline.txt`, `data/version_tags.txt`, `data/commits_by_month.txt`
- `data/file_changes.txt` (50KB), `data/artifact_timeline.txt` (10KB)
- `data/merge_history.txt`, `data/version_commits.txt`

**Why this matters**: This is the *best onboarding doc for any AI agent joining the project*. If we want to onboard a new developer or a Hetzner-managed AI agent to Whitemagic, this is the canonical entry point. Worth mirroring in `whitemagic.dev/llms-full.txt` or as a separate `AGENT_HANDBOOK.md` in the public site.

**Effort**: 1 hour to skim + 1-2 hours to integrate the most useful parts into the site.

### 2.4 `whitemagic-codex/00_source/LIBRARY/` (269 entries, 24MB)

**Path**: `~/Desktop/WHITEMAGIC-aux/codex/whitemagic-codex/00_source/LIBRARY/`
**Status**: Real corpus of source material with fragment-codex index.

**Contents**:
- 269 `.txt` files (e.g., "AI Game Theory Insights.txt" 77KB, "AI Habitat Design Review.txt" 60KB, "Aquarian Exodus Concept Mapping.txt" 63KB)
- `.fragment/lexical/text.bin` and `inverted.bin` — a fragment-based inverted index
- `.fragment/manifest.json` (50KB) — the index manifest

**Why this matters**: This is the substrate's actual *content*. The cognitive substrate was trained on / ingesting / distilling this material. If the new substrate wants to feel like the old substrate, it should be fed the same corpus.

**Effort**: 2-3 days to integrate via the fragment-codex (or use the existing Python `fragment` package referenced in `~/Desktop/WHITEMAGIC-aux/experiments/whitemagic-labs-aux/fragment/`).

### 2.5 `whitemagic-codex/` (8 Rust crates)

**Path**: `~/Desktop/WHITEMAGIC-aux/codex/whitemagic-codex/`
**Crates**:
- `codex-chunk`, `codex-consolidate`, `codex-core`, `codex-embed`, `codex-export`, `codex-extract`, `codex-index`

**Why this matters**: This is the *indexer* that produced the LIBRARY codex. If we want to rebuild the corpus index, this is the engine.

**Effort**: 1-2 weeks to integrate (Rust → Python bindings, or rewrite in Python).

---

## 3. The Auxiliary Tooling

### 3.1 `browser-garden-backup/` (browser automation stack)

**Path**: `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/browser-garden-backup/`
**Files**:
- `actions.py` (22KB)
- `cdp.py` (12KB) — Chrome DevTools Protocol client
- `distiller.py` (11KB) — content distillation
- `web_research.py` (26KB) — research pipeline
- `screenshot.py` (6.7KB)
- `__init__.py` (1.5KB)

**Why this matters**: This is a *real* web research + browser automation stack. The current `lib/librarian/web_research.py` is a thinner version. If we want to revive the `gana_extended_net` "search the web" Gana, this is the engine.

**Effort**: 1 day to port into `core/whitemagic/core/bridge/`.

### 3.2 `whitemagicv17/mesh/` (Go P2P mesh)

**Path**: `~/Desktop/archives/_laptop-offload-2026-06-17/archives/whitemagicv17/whitemagic/mesh/`
**Files**:
- `gossip.go` (16KB) — libp2p gossip protocol
- `agent_stream.go` (10KB) — agent streaming
- `main.go` (6.4KB)
- `go.mod` (4.7KB), `go.sum` (30KB)
- `proto/` (protobuf definitions)

**Why this matters**: The "agentic / autonomous AI economy" pivot requires *peer-to-peer* between substrate instances. This is the Go stack for distributed substrate gossip. Per the `mesh/pixi.toml` and the README, this was a real working stack on T4800-S (the other laptop).

**Effort**: 1-2 weeks to revive + add to the deployment. Could be a Hetzner-side service that connects multiple substrate instances.

### 3.3 `whitemagic-archive-aux/whitemagic-go-broken-backup/`

**Path**: `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/whitemagic-go-broken-backup/`
**Status**: A "broken" backup of an earlier Go attempt. Kept for reference, but superseded by the v17 mesh/ work.

**Effort**: Skip. Use v17 mesh/ instead.

### 3.4 `IDE-Data/` (conversation history)

**Path**: `~/Desktop/archives/laptop-export-2026-06-17/01-ai-systems/`
**Size**: 1.5GB
**Contents**: Codex, Gemini, Codeium/Windsurf cascade, Antigravity, Windsurf, Kilo

**Why this matters**: Per the README, this is "the most valuable intellectual property on the laptop" — 49MB of Codex sessions, 254MB of Gemini chats, 299MB of Codeium/Windsurf cascade data, etc. Not Whitemagic code per se, but conversations *about* Whitemagic, decisions made, AI feedback.

**Effort**: Skip for this session (too large to dig into in 90 min). Worth a separate investigation if we want to understand the project's history.

---

## 4. The State Directory

### 4.1 `~/.whitemagic/` (live state, 36 subdirs)

**Path**: `/home/lucas/.whitemagic/`
**Subdirs** (20+): agents, artifacts, autodidactic, benchmarks, cache, data, dharma, dreams, economy, ensemble, extensions, forecasting, gratitude, harmony, identity, inbox, keys, knowledge, learning, logs, matrix, plugins, restoration, security, tasks, terminal, voice, wisdom, ...

**Why this matters**: This is the *current* live state of the substrate. Different shape from `Whitemagic-Core/` (which was the 2025-12 Inspiron era). Has new dirs: `restoration/`, `forecasting/`, `autodidactic/`, `inbox/`, `plugins/`, `extensions/`, `terminal/`, `ensemble/`. These represent new directions the substrate has been exploring.

**Files of interest**:
- `galaxies.json` (1.6KB) — galaxy map (small, but probably hand-curated)
- `seen_registry.json` (558KB) — 14,500+ file registry (same one as Whitemagic-Core, presumably copied)

**Effort**: 1 hour to inventory; can be the basis for "what's running now" documentation.

### 4.2 `.whitemagic/harmony` + `matrix` + `payments` + `dreams` etc.

Smaller per-domain state dirs. The 12,288-byte size of `dreams` is unusual — suggests heavy content there.

---

## 5. The Frontend Evolution

WhiteMagic's frontend has gone through several iterations:

1. **`web/`** (Feb 2026, in `whitemagic-frontend/`) — 33KB HTML + 21KB CSS, no framework. Pre-React. Skip.
2. **`shell/`** (Feb 2026) — tiny shell page, no components. Skip.
3. **`_legacy/nexus`** (Feb 2026) — first Tauri + React attempt, 264KB. Skip.
4. **`nexus/`** (Feb 2026, in `whitemagicv17/`) — Tauri + React 19 + d3-force + Monaco. The current "modern" version. **Port key components**.
5. **`hub/`** (Jan-Apr 2026) — Tauri 2.0 + React 18 + three.js. The "WhiteMagic IDE" with HolographicView. **Port HolographicView**.
6. **`dashboard-app/`** (Jan-Apr 2026) — Next.js 14 + d3 v7. The "WhiteMagic App" with MemoryGraph, GanaActivityHeatmap, etc. **Port MemoryGraph + GanaActivityHeatmap**.
7. **Current site** (`whitemagic-site`, May 2026-now) — Next.js 15 + d3 (not used yet). Marketing + catalog + librarian. **Add visualizations from 5+6**.

The current site is a marketing surface. The earlier iterations had real substrate visualization. **The right move is to bring the substrate visualizations (1.1, 1.2) into the current site as new routes** — `/dashboard`, `/hologram`, `/memory`, etc.

---

## 6. The "Where It All Lived" Map

```
~/Desktop/
├── WHITEMAGIC/                                    # current core (v22.5.0, 24 dirs, 960 source files)
├── WHITEMAGIC-aux/
│   ├── codex/
│   │   ├── WHITEMAGIC_AI_ONBOARDING/              # 7 docs (00-06) + 7 data files (best onboarding)
│   │   ├── whitemagic-codex/                      # 8 Rust crates (codex-*), Cargo.toml
│   │   │   └── 00_source/LIBRARY/                 # 269 corpus files + fragment index (24MB)
│   │   └── WHITEMAGIC_docs/                       # public/ SYSTEM_MAP.md (48KB), competitive positioning, sefirotic gana mapping
│   ├── experiments/
│   │   └── whitemagic-labs-aux/                    # fragment/, edge-chat/, STRATA/, laptop-optimizer/
│   ├── site/
│   │   ├── whitemagic-site/                       # CURRENT LIVE SITE (v22.5.0)
│   │   ├── whitemagic-site-git-backup/            # pre-refactor backup (1 commit), skip
│   │   ├── whitemagic-archive-aux/
│   │   │   ├── whitemagic-frontend/               # THE BIG ONE: dashboard-app, hub, nexus, web, shell, sdk, _legacy
│   │   │   │   ├── dashboard-app/                 # v4.5.0 Next.js 14 + d3 (the visualization app)
│   │   │   │   ├── hub/                          # Tauri 2.0 desktop (HolographicView etc.)
│   │   │   │   ├── nexus/                         # older Tauri app
│   │   │   │   ├── _legacy/                       # aria-home, codexIDE, older nexus
│   │   │   │   ├── web/                           # pre-React HTML/CSS
│   │   │   │   ├── shell/                         # tiny shell
│   │   │   │   ├── sdk/                           # SDK
│   │   │   │   └── PHASE_0_PLAN.md, ARCHITECTURE.md
│   │   │   ├── whitemagic-go-broken-backup/       # skip
│   │   │   ├── whitemagic-site/                   # OLD v1 site (pre-current)
│   │   │   ├── browser-garden-backup/             # web_research.py (26KB) + cdp.py + distiller.py
│   │   │   └── archive/, AGENTS.md
│   └── site-ops-backups/                          # Vercel deploy backups
├── archives/
│   ├── laptop-export-2026-06-17/
│   │   ├── 07-desktop-archive/
│   │   │   ├── whitemagic-archive/
│   │   │   │   ├── Whitemagic-Core/               # 28MB real substrate data (33K events, 8K vectors)
│   │   │   │   ├── SharedWorkspace-SyncHub/        # syncthing + Flask + Redis + RQ
│   │   │   │   ├── Whitemagic-P2P-Go/             # distributed substrate gossip
│   │   │   │   └── README.md
│   │   │   ├── ide-workspace-archive/             # Antigravity, VSCode, Windsurf
│   │   │   └── whitemagic-toolchains/             # Haskell-Stack, Rust-Cargo
│   │   ├── 01-ai-systems/                         # 1.5GB conversation history (Codex, Gemini, etc.)
│   │   └── README.md
│   └── _laptop-offload-2026-06-17/
│       └── archives/
│           ├── whitemagicv17/                     # FULL v0.17 codebase (Feb 2026)
│           │   ├── whitemagic/                     # 22 dirs of Python + 7 polyglot runtimes
│           │   ├── nexus/                         # Tauri + React 19 IDE
│           │   ├── mesh/                          # Go P2P
│           │   ├── sdk/                           # TypeScript SDK
│           │   ├── docs/                          # API_REFERENCE, ARCHITECTURE, etc.
│           │   └── ...
│           ├── aria-backups/                      # skip
│           ├── CODEX-pipeline/                    # 1.1GB (skip)
│           ├── desktop-LIBRARY/                   # 266 files (24MB, personal)
│           ├── _private_journal-LIBRARY/           # 266 files (24MB, personal)
│           └── ...
└── vercel-deploy/                                 # Hetzner checklist, MCP submission templates
```

---

## 7. The 4th Option (per your deferral)

You said the "true answer will be a fourth option we haven't realized yet, something that is a fusion of the three yet none of them."

Based on what's in the archive, here's what that 4th option looks like:

**"Local-first PWA + cognitive substrate visualization"**

- The site is a PWA (the current site has `(pwa)` in next.config.mjs — the foundation is there)
- The librarian runs against a local model (Ollama on Hetzner, $17/mo)
- The PWA installs to the user's machine, syncs state to a tiny local DB
- The cognitive substrate is visualized: MemoryGraph, GanaActivityHeatmap, HolographicView all as PWA routes
- A Tauri desktop wrapper is the "power user" tier
- The P2P mesh (Go from v17) connects multiple substrate instances

This is *consulting* (you'd sell this as a service), *substrate* (it's open-source, forkable, PWA-installable), and *research lab* (the visualizations are the research contribution). It fuses all three because the user is the one who decides which mode to use.

**The archaeology tells you the path**: you *had* the visualizations (dashboard-app, hub), you *had* the P2P (mesh/), you *had* the local ML integration (LocalMLStatus, Tauri commands), and you *had* the v0.17 with the full polyglot runtime. Bringing these back to the current site + making it installable is the 4th option.

---

## 8. Recommended action plan (in priority order)

### This session (90 min)
1. **Port `MemoryGraph.tsx` from dashboard-app** to `app/memory/page.tsx` (1.5h)
2. **Stub out** the dharma/ganas/local-ml API routes with mock data (30 min)

### Next session (3-4 hours)
3. **Port `GanaActivityHeatmap.tsx`** to `app/ganas/page.tsx`
4. **Port `HolographicView.tsx`** to `app/hologram/page.tsx` (3D three.js + 4D coordinates)
5. **Add `/dashboard`** as the consolidated substrate visualization route
6. **Update sitemap + llms-full.txt** with the new routes
7. **Tag v22.6.0** as "first visualization revival"

### After Hetzner (1 week)
8. Wire the dashboard to live Ollama + bridge functions
9. Migrate useful data from `Whitemagic-Core/` (events, embeddings) to current substrate
10. Add PWA installability for the new dashboard routes

### Future
11. Revive `whitemagicv17/mesh/` Go P2P for cross-substrate sync
12. Revive Tauri `hub/` as the "power user" desktop tier
13. Integrate `browser-garden-backup/web_research.py` into the librarian

---

## 9. Decision

The archives confirm the 4th option is real and achievable. The pieces are sitting on disk. The site just needs to grow new routes that show the substrate, not just list it.

If you want, I can start with step 1 (port MemoryGraph) right now. It's a 90-minute task that would land v22.6.0 as "the site now visualizes the cognitive substrate, not just catalogs it."

Otherwise, this inventory is the document to reference for the next several sessions.
