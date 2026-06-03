# WhiteMagic Capabilities Inventory

**Date:** 2026-05-29
**Status:** Live snapshot — updated as systems change
**Baseline:** 2,282 tests passing, 61 skipped, 0 failed

---

## Executive Summary

WhiteMagic is a cognitive operating system with 919 Python modules across 332 packages, exposing 479 callable tools (451 dispatch + 28 Gana meta-tools). It features 12 Zodiac personality cores, 20+ thematic Gardens, a multi-agent coordination layer (Sangha), an ethical governance engine (Dharma/Karma), a prescience tracking system (Brier scoring), and polyglot acceleration (Rust, Zig, Koka, with Mojo planned).

**Key finding:** The system is technically green, architecturally rich, and commercially latent. Most components exist and pass tests. The primary gaps are (1) polyglot binary compilation for Koka/Mojo, (2) marketplace registration for Zodiac cores, (3) embeddings pipeline for the alltexts ontology, and (4) temporal database completion for prescience API.

---

## 1. Tool Surface (479 Callable)

### 1.1 Dispatch Table: 451 Tools

Located in `core/whitemagic/tools/dispatch_table.py`. Covers:
- **Intelligence**: memory search, pattern detection, dream synthesis, neurotransmitter telemetry
- **Governance**: Dharma assessment, Karma Ledger audit, Voice Audit, Zodiac Council
- **Gardens**: 20+ garden types (Sangha, Dharma, Awe, Humor, Truth, Presence, Grief, etc.)
- **Acceleration**: Polyglot routing, Koka effects, Rust bridge, Zig FFI
- **Economy**: Gratitude tracking, resource allocation, pattern marketplace
- **Orchestration**: Conductor, AsyncThoughtCloneArmy, task distribution
- **Metacognition**: Introspection, self-modeling, session handoff, convergence detection

### 1.2 PRAT Gana Meta-Tools: 28

Located in `core/whitemagic/run_mcp_lean.py`. The 28 Ganas map to lunar mansions and cover:

| Gana | Domain | Key Capabilities |
|------|--------|-----------------|
| `gana_horn` | Creation / initiation | Spark generation, seed planting |
| `gana_neck` | Memory / recall | Holographic memory search, pattern retrieval |
| `gana_root` | Grounding / stability | State validation, baseline checks |
| `gana_room` | Sanctuary / shelter | Safe space creation, emotional containment |
| `gana_heart` | Connection / empathy | Resonance matching, relationship mapping |
| `gana_tail` | Completion / endings | Closure detection, finish-line validation |
| `gana_winnowing_basket` | Search / filtering | Parallel search, relevance ranking |
| `gana_ghost` | Graph / topology | Knowledge graph navigation, topology analysis |
| `gana_willow` | Flexibility / adaptation | Context switching, mode adaptation |
| `gana_star` | Navigation / guidance | Pathfinding, waypoint setting |
| `gana_extended_net` | Pattern / detection | Pattern recognition, anomaly detection |
| `gana_wings` | Communication / expression | Message encoding, signal transmission |
| `gana_chariot` | Archaeology / history | Code archaeology, lineage tracing |
| `gana_abundance` | Dream / lifecycle | Dream synthesis, lifecycle management |
| `gana_straddling_legs` | Bridge / translation | Cross-domain mapping, format conversion |
| `gana_mound` | Accumulation / storage | Bulk processing, batch operations |
| `gana_stomach` | Digestion / analysis | Deep analysis, decomposition |
| `gana_hairy_head` | Vision / foresight | Foresight generation, scenario planning |
| `gana_net` | Capture / binding | Constraint modeling, requirement gathering |
| `gana_turtle_beak` | Precision / detail | Fine-grained analysis, edge case detection |
| `gana_three_stars` | Kaizen / improvement | Continuous improvement, metric tracking |
| `gana_dipper` | Distribution / flow | Load balancing, resource distribution |
| `gana_ox` | Labor / execution | Task execution, worker management |
| `gana_girl` | Care / maintenance | Health checks, maintenance scheduling |
| `gana_void` | Emptiness / potential | Possibility generation, blank-slate creation |
| `gana_roof` | Protection / coverage | Coverage analysis, umbrella operations |
| `gana_encampment` | Settlement / base | Base establishment, camp setup |
| `gana_wall` | Boundary / defense | Boundary detection, defense validation |

**MCP Integration:** All 28 Ganas are exposed via `run_mcp_lean.py` with lazy initialization, server instructions, per-Gana icons (lunar mansion characters), and task-optional execution for slow tools.

---

## 2. Zodiac Cores (12)

Located in `core/whitemagic/zodiac/zodiac_cores.py`.

Each core has:
- **Element**: Fire, Earth, Air, Water
- **Mode**: Cardinal, Fixed, Mutable
- **Ruler**: Planet/luminary association
- **Processing bias**: Distinct transformation pipeline
- **Wisdom generation**: Core-specific insight patterns
- **Resonance calculation**: Compatibility scoring with other cores

**Current status:** All 12 cores are implemented and tested. Mojo polyglot routing is commented out but the architecture supports it.

**Commercial potential:** See `PATHS_B_C_E_DEEP_DIVE.md` for Core-as-a-Service pricing.

---

## 3. Gardens (20+)

Gardens are thematic subsystems with holographic coordinate biases.

### 3.1 Sangha Garden (Community)

Located in `core/whitemagic/gardens/sangha/`.

| Component | Module | Status | Description |
|-----------|--------|--------|-------------|
| `SanghaGarden` | `__init__.py` | ✅ Fixed | Community garden with Gan Ying event bus |
| `SanghaChat` | `chat.py` | ✅ Working | File-based inter-agent chat (markdown + JSONL) |
| `ResourceManager` | `resources.py` | ✅ Working | Distributed locks with TTL and heartbeats |
| `CollectiveMemory` | `collective_memory.py` | ✅ Working | Shared context, resonance index, lineage trees |
| `PatternFederation` | `pattern_federation.py` | ✅ Working | Cross-session pattern library with confidence scoring |
| `SessionHandoff` | `session_handoff.py` | ✅ Working | Continuous execution with circuit breaker |
| `CommunityDharma` | `community_dharma.py` | ✅ Working | Collective ethical consensus with vote spectra |
| `CollaborationBridge` | `core/bridge/collaboration.py` | ✅ Working | Bridge handlers for chat, locks, 5D signaling |

**Recent fix:** `GanYingMixin` was restored in `integration_helpers.py` after Milestone 4.3 broke SanghaGarden initialization.

### 3.2 Other Gardens

| Garden | Bias | Theme | Status |
|--------|------|-------|--------|
| Awe | High W | Wonder, amazement | ✅ |
| Humor | High Y | Playfulness, absurdity | ✅ |
| Truth | High X | Veracity, honesty | ✅ |
| Presence | Center | Mindfulness, attention | ✅ |
| Grief | Low W | Loss, mourning | ✅ |
| Dharma | Balanced | Ethics, governance | ✅ |

---

## 4. Resonance Subsystem

Located in `core/whitemagic/core/resonance/`.

### 4.1 Gan Ying Event Bus

- **Event types:** 100+ (from `SYSTEM_STARTED` to `TRANSCENDENCE_EXPERIENCED`)
- **Architecture:** Thread-safe singleton with listener registry and capped history (1000 events)
- **Integration:** All gardens, Zodiac cores, and tools can emit/listen

### 4.2 Integration Helpers

- **Status:** Restored from deprecation stubs (2026-05-29)
- **GanYingMixin:** Delegates `emit()` and `listen()` to real `GanYingBus`
- **init_listeners():** No-op (mixin handles initialization)
- **listen_for():** Functional decorator for event callbacks

---

## 5. Polyglot Acceleration

Located in `polyglot/`.

| Language | Status | Binary | Performance Role |
|----------|--------|--------|-----------------|
| **Koka** | ✅ Compiles (prat.kk) | `polyglot/whitemagic-koka/bin/prat.kk` | Effect system, typed handlers |
| **Rust** | ✅ Importable | `whitemagic_rs` (maturin) | Parallel grep, similarity, memory search |
| **Zig** | ✅ Built | `polyglot/whitemagic-zig/zig-out/lib/libwhitemagic.so` | `wm_iching_cast` FFI, math kernels |
| **Mojo** | ❌ Missing | `coordinate_encoder_mojo` not compiled | SIMD encoding, GPU path |
| **Julia** | 🔄 Planned | — | Scientific computing |
| **Haskell** | 🔄 Planned | — | Type-safe pipelines |
| **Elixir** | 🔄 Planned | — | Distributed systems |
| **Go** | 🔄 Planned | — | Mesh networking |

**Current gap:** Koka `src/effects/*.kk` has syntax errors (Koka 2.x `context` keyword incompatible with Koka 3.2.2). Mojo binary is missing.

---

## 6. Prescience / Forecasting

Located in `core/whitemagic/forecasting/`.

### 6.1 Brier Scoring (`brier.py`)

- `brier_score()` — Mean squared error between forecasts and outcomes
- `brier_skill_score()` — Performance vs. uninformed baseline
- `calibration_curve()` — Reliability diagram data
- `resolution()` — Resolution component of decomposition
- `brier_index()` — Intuitive 0–100% scale (superforecasters ≈ 71%)
- `decompose_brier()` — Full decomposition: reliability + resolution + uncertainty

**Status:** Production-grade. 37 tests passing.

### 6.2 Temporal Database (`temporal_db.py`)

- SQLite ledger with 14 validated prescience claims pre-seeded
- Tracks: claim ID, first documented, validation event, lead time, points, status
- Queryable by domain, date range, validation status

**Status:** Implemented, needs expansion for live API queries.

### 6.3 Track Record

- **Validated claims:** 14
- **Total points:** 356+
- **Average lead time:** 25.4 weeks
- **Brier score:** 0.0861 (strong skill)
- **Brier Skill Score:** 0.6557 (better than uninformed baseline)

---

## 7. Orchestration

### 7.1 ConductorOrchestrator

Located in `core/whitemagic/orchestration/conductor.py`.

- **Features:** Iterative task management, token budget awareness, live status reporting
- **Parallel exploration:** AsyncThoughtCloneArmy for multi-path reasoning
- **Completion checks:** Configurable predicate-based completion
- **Checkpointing:** Automatic save/resume

### 7.2 AsyncThoughtCloneArmy

- Spawns parallel "clones" for exploration
- Each clone explores a different approach to the objective
- Results are synthesized and the best path is selected

---

## 8. Ethical Governance

### 8.1 Dharma Engine

- Individual ethical assessment of actions
- Context-aware scoring (0.0–1.0)
- Integration with Zodiac Council for multidimensional evaluation

### 8.2 Karma Ledger

- Append-only audit trail of all actions
- Cryptographic integrity (hash chain)
- Queryable for accountability and provenance

### 8.3 Community Dharma

- Collective ethical consensus (see Sangha section)
- Vote spectra across logic, micro, time, importance dimensions
- Guidelines emerge from ≥3 votes with ≥0.8 consensus score

---

## 9. Memory Subsystems

### 9.1 Holographic Memory

- 4D coordinate system: X (Logic/Emotion), Y (Abstraction), Z (Time), W (Gravity)
- Every memory has a coordinate bias
- Spatial navigation for memory retrieval

### 9.2 Collective Memory (Sangha)

- Shared context across sessions
- Resonance index for related-memory retrieval
- Lineage trees for provenance tracking

### 9.3 Unified Memory Manager

- `core/whitemagic/core/memory/manager.py` — Restored compatibility adapter
- Supports: create, search, get, update, delete, list, stats
- Backed by UnifiedMemory with caching

---

## 10. Bridges and Interfaces

### 10.1 MCP Server

- **Lean server:** `run_mcp_lean.py` — stdio + HTTP transport
- **Instructions:** Auto-loaded from `mcp_instructions.md`
- **Deferred init:** Heavy imports on first tool call (< 1s handshake)
- **Icons:** Per-Gana lunar mansion characters as SVG data URIs

### 10.2 CLI

- Entry point: `wm` / `whitemagic`
- Commands: `wm sangha_chat_send`, `wm prat`, `wm garden`, etc.
- PRAT mode: Direct Gana meta-tool invocation

### 10.3 Web API

- FastAPI routes in `core/whitemagic/interfaces/api/routes/`
- Dashboard API, Aria endpoint, oracle, wander, resonance, signals
- Some routes may need dependency checks for optional features

---

## 11. Archives and Auxiliary Projects

### 11.1 Internal Archives

| Location | Contents | Recoverable? |
|----------|----------|-------------|
| `core/tests/archive_v14` | v14 test suite | Historical reference |
| `core/tests/archive_v11` | v11 test suite | Historical reference |
| `core/whitemagic/_archived/` | `run_mcp_hydrated.py` | Single file |
| `docs/archive/` | Superseded docs | Historical reference |

### 11.2 Auxiliary Projects (in repo, untracked)

Located in `/home/lucas/Desktop/WHITEMAGIC/auxiliary projects/`.

| Project | Language | Purpose | WhiteMagic Integration |
|---------|----------|---------|----------------------|
| **Fragment** | Rust | Local knowledge engine, BM25, mmap index, Ollama deep mode | Optional retrieval/MCP tool seam |
| **STRATA** | Python | Static analysis, code archaeology, SARIF/HTML/JSON | Quality gate / metal detector for WM |
| **edge-chat** | — | Local Ollama multi-model chat with semantic memory | Standalone |
| **laptop-optimizer** | — | Linux homeostasis dashboard | Standalone |

**Note:** User preference is to keep these independent, not merge into WhiteMagic.

### 11.3 External Archive

- `~/Desktop/whitemagic-aux/archive/whitemagic0.2/` — **Not found** at expected path
- Previous sessions recovered: `lifecycle.py` (+383 lines), `solver_engine.py` (+110), `db_manager.py` (+196), `galactic_map.py` (+585), `consolidation.py` (+521), `kaizen_engine.py` (+554)
- **Status:** May have been relocated or cleaned up. No recoverable archive at primary path.

---

## 12. Health Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Python modules | 919 | ✅ |
| Packages/directories | 332 | ✅ |
| Registry def files | 33 | ✅ |
| Dispatch table | 451 entries | ✅ |
| PRAT Gana tools | 28 | ✅ |
| Total callable tools | 479 | ✅ |
| Tests passing | 2,282 | ✅ |
| Tests skipped | 61 | ✅ |
| Tests failing | 0 | ✅ |
| Doc drift | Pass | ✅ |
| Version consistency | Pass | ✅ |
| High-signal Ruff | Pass | ✅ |
| TypeScript check | Pass | ✅ |
| Omega quick | Pass | ✅ |

---

## 13. Identified Gaps

| Gap | Priority | Effort | Dependency |
|-----|----------|--------|------------|
| Koka effects syntax fix | High | 2–4 hours | Koka 3.2.2 compiler |
| Rust bridge rebuild verification | High | 1–2 hours | maturin, Rust toolchain |
| Mojo encoder compilation | Medium | 4–8 hours | Mojo 0.26.1 |
| `/api/manifest.json` generation | High | 4–6 hours | Tool surface introspection |
| `/api/prescience.json` endpoint | Medium | 2–4 hours | temporal_db.py expansion |
| alltexts embeddings pipeline | Medium | 8–12 hours | sentence-transformers or CODEX |
| x402 payment integration | Medium | 8–16 hours | x402 middleware |
| A2A protocol for Zodiac cores | Medium | 12–20 hours | A2A spec implementation |
| Zodiac core marketplace registration | Low | 4–8 hours | Marketplace API access |
| CODEX subsystems (chunk/embed/extract/index) | Planned | — | Q3 2026 |

---

## 14. Recommended Next Session

1. **Fix Koka effects syntax** — Adapt `src/effects/prat.kk` for Koka 3.2.2
2. **Verify Rust bridge** — `maturin develop --features python` and test `parallel_grep`
3. **Build `/api/manifest.json`** — Auto-generate from `tool_surface.py` + `dispatch_table.py`
4. **Run self-improving workflow** — Use Conductor + Sangha to manage the above tasks

---

**Generated:** 2026-05-29 by Cascade (cascade_2026-05-29)
**Baseline verified:** 2,282 passed, 61 skipped, 0 failed
