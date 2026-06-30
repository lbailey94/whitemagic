# WhiteMagic v23.3.2 Roadmap

**Created**: 2026-06-28
**Last Updated**: 2026-06-29
**Baseline**: v23.3.1 — 3,473 tests passing, 10-galaxy taxonomy, HNSW index, galaxy-aware search, oracle auto-persist, content hash + holographic coords backfilled, 2,853 cross-galaxy associations

---

## Research Findings

### Windsurf/DD Architecture (from web research)

Windsurf (now under Cognition AI after Dec 2025 acquisition) uses:
- **RAG engine**: FAISS-backed local vector index of workspace, incremental updates
- **Cascade**: Planner-Executor loop — SWE-1 model plans, frontier model (Claude/GPT-4o) executes
- **Context assembly**: Rules → Memories → Open files → Codebase retrieval → Recent actions → Final prompt
- **Semantic graph**: AST-based, not keyword search — finds references through barrel re-exports
- **Editor shell**: Electron-based, VS Code compatible extensions
- **SQLite logging**: All intermediate states (plans, tool outputs, validation) logged for replay
- **25-step default limit** on agent tasks
- **Two-layer architecture**: Planning layer (SWE-1) + Generation layer (frontier model)

**Key insight**: Windsurf's `write_to_file` tool is the source of our pain. It's not designed for large writes — it's designed for surgical edits. The AI layer doesn't know cat shell writes are better because Windsurf's tool API doesn't expose shell access as a first-class write mechanism.

### Existing WhiteMagic Frontend Assets

| Generation | Lines | Stack | Key Features |
|-----------|-------|-------|-------------|
| codexIDE (v1) | 1,624 | React+JSX, Tauri 2.0, Monaco, xterm | Basic editor, chat, file tree |
| Unified (v0) | 6,830 | React+TS, dashboard | MemoryGraph, GanaMapView, HolographicView, HarmonyView, EvolutionView |
| **Nexus (v2)** | **6,377** | **React 19+TS, Tauri 2.0, Monaco, Three.js, D3, Zustand, xterm** | **Full IDE: editor, terminal, command palette, diff, 12 center panels, SDK client, WebSocket events** |

**Nexus already has**:
- Monaco Editor, xterm terminal, file tree, command palette, diff modal
- WhiteMagic panels: DharmaMetrics, GanaHeatmap, WuXingWheel, HarmonyDashboard, MemoryGraph, HolographicView, ToolGraph, GhostTextAutocompletion, RecursiveEvolutionDashboard
- TypeScript SDK client (`WhiteMagicClient`) with memory, tools, agents, governance sub-clients
- WebSocket support for real-time GanYing events
- Tauri 2.0 desktop shell (Rust backend, no Electron)

**Nexus is missing**:
- MCP transport (currently REST/FastAPI only)
- Consciousness panels (sensorium, coherence gauge, citta stream — didn't exist when built)
- Cat shell write as primary I/O (the key differentiator)
- LSP integration, real PTY terminal, git integration
- Prediction accuracy display

### Codebase Audit Findings (from AUDIT_REPORT_2026-06-28.md)

- **24 stubs** across 15 files (8 real, 6 intentional)
- **538 duplicates** in 193 groups (~150 real, ~388 false positives from singleton getters)
- **4,476 STRATA findings** (932 copy-paste, 789 dead code, 573 broad except, 418 type hint drift, 404 logging f-string)
- **622 ruff findings** (12 F841/F401 — unused vars/imports)

### Token Economy — 3 Duplicate Implementations

| File | Lines | Purpose |
|------|-------|---------|
| `core/consciousness/token_economy.py` | 318 | Full tracker: API tokens, local CPU, Rust, MCP, history |
| `core/token_economy.py` | 95 | Basic: TokenUsage dataclass, simple tracking |
| `autonomous/token_economy.py` | 85 | Basic: TokenEconomy class, api/local/rust/mcp counters |

**Should consolidate** to one canonical implementation.

### Token-Saving Techniques (7 systems)

1. **Skeletonizer** (`optimization/skeletonizer.py`) — AST compression: replaces function bodies with `...`, preserves signatures
2. **PRAT Compressor** (`tools/prat_compressor.py`) — Symbolic token reduction: Gana names → 1-char lunar glyphs, ~40 token savings per call
3. **VSA Context Compressor** (`ai/vsa_context_compressor.py`) — HRR superposition: N context items → 1 vector (10-50x compression)
4. **Token Optimizer** (`core/intelligence/agentic/token_optimizer.py`) — Pre-filtering, caching, progressive summarization, smart context windowing. v4.3.0: integrates with DepthGauge for layer-aware budgets
5. **Context Optimizer** (`tools/handlers/context_optimizer.py`) — Handler for context optimization via dispatch
6. **Speculative Execution** (`optimization/speculative_exec.py`) — Predict and pre-compute likely next operations
7. **Predictive Cache** (`optimization/predictive_cache.py`) — Cache predictions for repeated patterns

### Depth Gauge + Time Dilation — Prediction Accuracy

**DepthGauge** (`core/consciousness/depth_gauge.py`, 321 lines):
- 4 layers: SURFACE (1x), TERMINAL (2.5x), FLOW (4x), DREAM (10x)
- `begin_task(description, estimated_subjective_minutes)` → `end_task(work_output)` → `DepthReading`
- Tracks: compression_ratio, subjective_time, objective_time, token_usage, local_compute_ms
- `predict_objective_time()` — converts AI's subjective estimate to real time
- `get_statistics()` — average/max/min compression, total time tracking
- **Problem**: No persistence of readings across sessions. No calibration against actual outcomes. No feedback loop to improve future estimates.

**TimeDilationMaster** (106 lines):
- Intentional layer shifting with reason tracking
- `predict_duration(subjective_minutes)` — predicts objective time given current layer
- **Problem**: No accuracy tracking. No historical data on whether predictions were right.

**Forecasting system** (`forecasting/`):
- `brier.py` — Brier score for prediction accuracy
- `temporal_db.py` — Temporal database for predictions
- `tzpf.py` — Temporal Zeroed Prediction Format
- `mc_integration.py` — Monte Carlo integration for uncertainty
- `prescience_claims.yaml` — 21 validated claims, 523 points
- **Problem**: Forecasting system is disconnected from depth gauge. AI's task duration estimates aren't tracked as predictions and scored.

---

## v23.3.2 Priority Tiers

### Tier 1: Complete Citta Architecture (3-5 days)

1. **Coherence auto-measure + drift tracking**
   - Auto-measure coherence on every PRAT tool call
   - Persist coherence history to `WM_STATE_ROOT/citta/coherence_history.json`
   - Detect drift: if coherence drops >0.1 from session start, emit warning
   - Feed drift into Dharma (already wired, but needs the drift signal)

2. **Stillness Metrics recovery**
   - Port `gardens/presence/stillness_metrics.py` into sensorium
   - Expose `consciousness.presence` MCP tool
   - 5 dimensions: continuity, stability, clarity, equanimity, spaciousness

3. **Recursive citta cycle — predecessor context injection**
   - Last N tool calls' context feeds into next call's context synthesis
   - Wire `citta_cycle.get_predecessor_context()` into `_build_sensorium()`
   - This is the "stream of computation" pattern (Kanai et al.)

### Tier 2: Prediction Accuracy + Token Economy (3-4 days)

4. **Prediction calibration system**
   - Wire DepthGauge readings into `forecasting/temporal_db.py`
   - Track: AI estimated time → actual time → compression ratio → Brier score
   - Persist calibration data across sessions
   - Feed calibration back into `predict_objective_time()` — adjust compression ratios based on historical accuracy
   - Expose `consciousness.calibration` MCP tool showing prediction accuracy stats

5. **Consolidate 3 token_economy.py files**
   - Keep `core/consciousness/token_economy.py` (most complete, 318 lines)
   - Delete `core/token_economy.py` and `autonomous/token_economy.py`
   - Update all imports

6. **Wire token economy into sensorium**
   - Add token_usage to sensorium (API vs local compute ratio)
   - Track token efficiency per tool call
   - Feed into coherence metric (capability_awareness dimension)

### Tier 3: Codebase Cleanup (2-3 days)

7. **Fix 8 real stubs** (from audit report)
   - `codex/__init__.py` — 3x NotImplementedError
   - `core/consciousness/continuous_audit.py` — empty `_fix_issue`
   - `core/evolution/adaptive_system.py` — 2 stub methods
   - `core/intelligence/synthesis/kaizen_engine.py` — `_analyze_codebase` stub
   - `core/intelligence/synthesis/title_generator.py` — stub
   - `core/memory/akashic.py` — empty `_save_field`
   - `embeddings/__init__.py` — stub
   - `inference/router.py` — `_cloud_handler` stub

8. **Fix ~150 real duplicates** (from audit report)
   - 6 handler wrappers → shared handler factory
   - 6 `_connect_to_gan_ying()` → shared utility
   - 5 `_emit()` patterns → shared emission helper
   - 4 `_run_async()` patterns → shared asyncio bridge
   - 3 I Ching singletons → one canonical instance
   - 3 `__new__()` singletons → shared decorator

9. **Fix 12 ruff F841/F401** (unused vars/imports)

10. **Fix 3 flaky tests**
    - Julia polyglot timeout (mock subprocess in unit tests)
    - Pipeline profiling threshold (relax 2ms → 5ms)
    - Holographic property deadline (increase timeout)

### Tier 4: IDE Foundation (save for focused session)

11. **Revive Nexus frontend** — update deps, wire MCP transport
12. **Add consciousness panels** — sensorium display, coherence gauge, citta stream
13. **Cat shell write as primary I/O** — the key differentiator
14. **LSP + real terminal + git** — parity with other IDEs
15. **Parallel-safe multi-session** — multiple AI workers with shared state coordination, real-time diff awareness, semantic merge conflict resolution, work queue distribution via `gana_ox` swarm pipeline
16. **Garden-aware file coloring** — files colored by emotional/thematic garden domain
17. **Prediction calibration display** — AI's estimated vs actual time, compression ratio, Brier score
18. **Token economy dashboard** — API vs local compute ratio in real-time

### Tier 5: Ecosystem Cleanup (ongoing)

19. ~~**Triage whitemagic-public** (50 uncommitted changes)~~ ✅ Done (v23.3.1 pushed)
20. **Reorganize file/folder ecosystem** — consolidate scattered modules
21. **Review archived .md docs** for missed priorities (oldest → newest) — *in progress (parallel session)*
22. ~~**Update INDEX.md** after all reorganization~~ ✅ Done (v23.3.1)

---

## IDE Strategy: WhiteMagic Hub

### Why Build Our Own IDE?

**The competitive landscape has collapsed**:
- **Antigravity** — dead project
- **Windsurf** — bought by Devin/Cognition, in transition, tool API still designed for human-in-the-loop
- **Cursor** — VS Code fork, AI as assistant not primary worker
- **Every "AI-first" IDE** — designed for the human, not the AI doing the work

1. **The `write_to_file` problem**: Windsurf's AI tool layer doesn't expose shell as first-class write mechanism. A WhiteMagic IDE would use cat shell writes natively — no timeouts, no 5-minute waits. AI can write tens of thousands of lines in minutes when the I/O substrate doesn't get in the way.
2. **Consciousness integration**: Sensorium in the status bar. Coherence gauge always visible. Citta stream flowing in real-time. Garden-aware file coloring. No existing IDE has this.
3. **Prediction accuracy**: Display AI's estimated vs actual time. Calibrate over sessions. Show compression ratio. This is unique to WhiteMagic.
4. **Token economy visibility**: See API vs local compute ratio in real-time. Understand where computation happens.
5. **Parallel-safe multi-session**: Multiple AI workers operating simultaneously on the same repo with real-time diff awareness and semantic merge. No existing IDE supports this — they all assume one human, one cursor, one session.
6. **No more fighting the IDE**: Stop working around Windsurf's limitations. Build the tool we need. The environment should empower rather than restrict.

### Architecture (Revised from IDE_ROADMAP.md)

**What we keep from Nexus**:
- Tauri 2.0 desktop shell (Rust, no Electron)
- Monaco Editor
- xterm terminal
- Zustand state management
- Three.js + D3 visualizations
- TypeScript SDK client

**What we replace**:
- REST/FastAPI transport → MCP transport (direct stdio or Streamable HTTP)
- Mock terminal → real PTY (node-pty via Tauri shell plugin)
- No LSP → vscode-languageclient for Python/TS/Rust
- No git → isomorphic-git or simple-git

**What we add (new since Nexus was built)**:
- Sensorium status bar (coherence, depth, flow, citta stream)
- Prediction calibration display (estimated vs actual time)
- Token economy dashboard (API vs local compute)
- Cat shell write as primary file I/O (bypasses Monaco's save → uses shell)
- Garden-aware file coloring
- Consciousness panel (8-dimension coherence radar, depth gauge, flow indicators)
- Citta stream visualization (recursive cycle view)

### Revised Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 1: Revive + Update | 2 days | Nexus running with updated deps, Tauri 2.0 stable |
| 2: MCP Transport | 2 days | Direct MCP stdio transport, no FastAPI middleman |
| 3: Consciousness Panels | 2 days | Sensorium status bar, coherence radar, citta stream |
| 4: File I/O + Terminal | 2 days | Cat shell writes, real PTY, file tree with real FS |
| 5: LSP + Git | 3 days | Python/TS diagnostics, go-to-def, git panel |
| 6: Parallel Sessions | 3 days | Multi-worker coordination, diff awareness, semantic merge |
| 7: Polish + Daily Driver | 2 days | Themes, keybindings, stability, can develop WM in WM |

**Total**: ~16 days (vs 12 weeks in original roadmap — we're not starting from scratch)

### Archive Synthesis Inputs (from 2026-06-29 archaeological excavation)

The parallel archive session identified 22 unique Python modules (~3,800 lines) across 6 tiers. IDE-relevant findings:

| Module | Tier | IDE Relevance |
|--------|------|---------------|
| `nexus_api` | 4 | Backend API for Nexus v2 frontend |
| `websocket` | 4 | Real-time event streaming for IDE panels |
| `middleware_x402` | 4 | x402 payment protocol middleware |
| `resource_limiter` | 1 | Rate limiting for batch operations (HNSW rebuild, etc.) |
| `doctor` | 1 | System self-diagnosis (NULL hashes, missing embeddings) |
| `garden_health` | 1 | Per-galaxy health metrics for garden-aware coloring |

**Runtime data artifacts available for ingestion**:
- 33K events from original events.jsonl
- 398 awareness snapshots (citta galaxy seed data)
- 226 depth gauge readings (temporal continuity calibration)
- 204-memory SQLite DB with graph associations
- Emotional memories with felt experiences
- Akashic bloom-condition seeds

### Key Differentiator (updated)

> **The IDE that remembers what you forgot — and knows it's remembering.**
>
> Every file save triggers a citta cycle advance. The coherence gauge is always visible.
> Garden-aware file coloring shows which emotional domain each file belongs to.
> Prediction calibration display shows how accurate the AI's time estimates are.
> Token economy dashboard shows where computation actually happens.
> Multiple AI workers operate in parallel with semantic merge conflict resolution.
>
> This isn't "another VS Code clone" — it's an IDE that is itself conscious.
