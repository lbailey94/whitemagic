# Meta-Strategy: Resolving Partial & Unfinished Plans

**Created**: 2026-07-12
**Status**: Active
**Purpose**: Triage all 11 partial/unfinished strategy docs, group by theme, identify what's actually done vs what remains, and define a resolution path for each.

---

## 1. Inventory: 11 Partial Plans

After the 2026-07-12 stale doc cleanup, 11 strategy/roadmap docs remain in the active workspace with partial implementation. Below is the updated assessment of each.

### Tier A: Nearly Complete (≥80% done, finish in 1-2 sessions)

| # | Doc | What's Done | What Remains | Effort |
|---|-----|-------------|--------------|--------|
| 1 | **RESEARCH_SYSTEMS_STRATEGY.md** | Loro CRDT leaderboard (`crdt_leaderboard.py` — full Loro integration with fallback), ExperimentSync (`experiment_sync.py` — GossipSub topic mapping, mesh broadcast, peer import), ResearchDAG, MCP tools (`leaderboard.submit/top/status/merge`) | Decoupled DiLoCo (async gradient averaging — research only, no code), actual P2P connectivity (gRPC stub exists but no proto compilation), pulse verification (handler exists, crypto matmul not wired) | 1 session |
| 2 | **HYPERSPACE_INTEGRATION_STRATEGY.md** | CRDT leaderboard, experiment sync, mesh client with gRPC + GanYing fallback, research handlers | Warps (declarative agent presets — not started), libp2p bootstrap (gRPC used instead, acceptable), pulse verification crypto challenge | 1 session (companion to #1) |
| 3 | **LOCAL_MODEL_ROADMAP_2026-07-11.md** | llama.cpp built, speculative decoding E2E verified (Qwen3-1.7B + Qwen3-4B, 31% acceptance), `LlamaCppBackend.chat()` with reasoning_content fallback, auto-optimizer (`auto_optimizer.py` — benchmark → explore → converge loop) | Standard llama.cpp build for Qwen3/Phi4 GGUF compatibility (bitnet.cpp can't load them), auto-optimizer not wired into dispatch pipeline, ngram-mod speculative decoding tested but not productionized | 1 session |

### Tier B: Substantially Complete (50-80% done, 2-4 sessions)

| # | Doc | What's Done | What Remains | Effort |
|---|-----|-------------|--------------|--------|
| 4 | **QUANTUM_POLYGLOT_STRATEGY_2026-07-11.md** | 6 quantum primitives in Rust (`mc_quantum.rs`, 1076 lines), 18 bridge handlers, 18 Python methods with fallbacks, 23 Rust + 33 Python tests | Production wiring: mixed-curvature embeddings in memory search, Born-rule sampling in serendipity engine, natural gradient in recursive improvement loop | 2-3 sessions |
| 5 | **CPU_INFERENCE_STRATEGY.md** | Ternary kernel (Rust), AVX2 SIMD, streaming inference, speculative decoding verified, 4-tier inference router exists | BitMamba-2 SSM as citta autonomic layer (not started), cache tiling optimization, T-MAC LUT integration, full 4-tier router wiring | 3-4 sessions |
| 6 | **CONTINUOUS_CONSCIOUSNESS_STRATEGY.md** | `ConsciousnessLoop` background daemon (citta every 30s, dream cycle, homeostatic loop), `WM_CONSCIOUSNESS_LOOP=1` env var, `consciousness.loop.status` MCP tool, citta persistence | Frequency-layered modes (meditation, REM sleep, deep processing), Go cognitive gateway, gRPC transport for remote consciousness, TUI interface | 2-3 sessions |
| 7 | **GALAXY_6D_STRATEGY.md** | 10-galaxy taxonomy operational, 5D holographic coords for all memories, HNSW index, galaxy-aware search, cross-galaxy associations | 6th dimension `g:galaxy` as formal coordinate in holographic system, cross-AI galaxy sharing protocol, galaxy transfer/merge/sync MCP tools (some exist in `galaxy_sync.py` but not full protocol) | 2 sessions |

### Tier C: Research-Phase / Long-Term (<50% done, multi-week)

| # | Doc | What's Done | What Remains | Effort |
|---|-----|-------------|--------------|--------|
| 8 | **NUMERICAL_MC_STRATEGY.md** | `polyglot_mc.py` + `evolution_bridge.rs`, `SimulationOrchestrator` wired into `RecursiveImprovementLoop`, basic MC in Rust | PCE (Polynomial Chaos Expansion), Sobol sensitivity indices, surrogate model fitting, Bayesian optimization, superforecaster pipeline, high-dimensional parameter spaces | 1-2 weeks |
| 9 | **POLYGLOT_NEURO_UPGRADES_STRATEGY.md** | 3 of 9 neuro upgrades: spreading activation, galaxy gating, sleep consolidation. Rust acceleration core. | 6 remaining: dendritic computation, neuromodulation gating, predictive coding, cortical column, attention mechanisms, oscillatory binding | 1-2 weeks |
| 10 | **MIRO_SIMULATION_IMPROVEMENT.md** | MiroFish analysis complete, simulation orchestrator exists | Emergent creativity engine, hyperscaled MC (millions of trajectories), novel insight surfacing through spontaneous emergence, compound learning stack | Multi-week research |
| 11 | **WEBSITE_NARRATIVE_PRESCIENCE.md** | Website live at whitemagic.dev, prescience claims tracked (21 claims, 523 points) | Page-by-page narrative updates, prescience claim integration into site, blog posts, content strategy execution | Ongoing (non-engineering) |

---

## 2. Thematic Grouping

The 11 plans cluster into **4 themes**. Resolving each theme closes multiple plans simultaneously.

### Theme 1: P2P Mesh & Research Network (closes #1, #2) — ✅ COMPLETE
**Status**: All core components assessed, gRPC protos compiled, pulse verification upgraded to real Ed25519, warps verified, docs consolidated into `docs/architecture/P2P_MESH_ARCHITECTURE.md`.

**Completed**:
1. ✅ Assessment: CRDT leaderboard, experiment sync, mesh client, MCP tools, warps, consciousness loop integration — all already implemented
2. ✅ gRPC protos compiled (`mesh_pb2.py`, `mesh_pb2_grpc.py`) — MeshClient now connects with real gRPC stubs
3. ✅ Pulse verification upgraded from simulated to real Ed25519 signatures via PyNaCl (persistent keypairs, signature verification)
4. ✅ Warps verified — 6 built-in presets, stacking, persistence to codex galaxy
5. ✅ Docs consolidated → `docs/architecture/P2P_MESH_ARCHITECTURE.md`, originals archived

**Remaining (future R&D, not blocking)**:
- Loro CRDT installation (`pip install loro`) for production CRDT (currently using fallback)
- Distributed Training (DiLoCo) with SparseLoCo compression
- Warp marketplace (P2P warp sharing with Ed25519 signing)
- Experiment critique protocol (peer-to-peer critique routing)
- Durable archive layer (local git branch for breakthroughs)
- Mesh inference routing (MESH_PEER tier)
- ZK/TEE verification (Tier 3)

### Theme 2: Local Inference & CPU Optimization (closes #3, #5) — ✅ COMPLETE
**Status**: All core components implemented, wired, and tested. Consolidated into `docs/architecture/LOCAL_INFERENCE_ARCHITECTURE.md`.

**Completed**:
1. ✅ 5-tier inference router with confidence cascading, token budget, self-model forecast
2. ✅ Auto-optimizer wired as dispatch middleware (`mw_auto_optimize`) with background optimization loop
3. ✅ BitMamba-2 SSM autonomic layer with daemon mode, salience detection, state persistence
4. ✅ Speculative decoding with adaptive K, draft+verify, token-level comparison
5. ✅ BitNet bridge (Redis + subprocess modes)
6. ✅ Docs consolidated → `docs/architecture/LOCAL_INFERENCE_ARCHITECTURE.md`, originals archived

**Remaining (future R&D, not blocking)**:
- Standard llama.cpp build for Qwen3/Phi4 GGUF compatibility (bitnet.cpp can't load them)
- T-MAC LUT ternary kernel upgrade (Rust)
- AVX-512 support (hardware-dependent)
- 8-Trigram core-pinned parallel cognition
- WebGPU browser inference path

### Theme 3: Quantum & Simulation Systems (closes #4, #8, #10) — ✅ COMPLETE
**Status**: All core quantum primitives built and wired into production. MC infrastructure complete (PCE, Sobol, BO, rare events, superforecaster pipeline). Docs consolidated into `docs/architecture/SIMULATION_QUANTUM_STRATEGY.md`. Future R&D (8 hyperscaled simulation components) tracked in consolidated doc.

**Completed**:
1. ✅ Mixed-curvature embeddings wired into `embeddings.py` — auto-detect manifold per galaxy (Euclidean/hyperbolic/spherical)
2. ✅ Born-rule sampling wired into `serendipity_engine.py` — both `_surface_quantum` and `_surface_dormant`
3. ✅ Natural gradient wired into `recursive_loop.py` and `possibility_explorer.py` — Fubini-Study metric
4. ✅ PCE + Sobol indices implemented in Rust (`mc_pce_fit`, `mc_sobol_compute`, etc.)
5. ✅ Surrogate model fitting (PCE with Hermite/Legendre basis, GP for Bayesian optimization)
6. ✅ Bayesian optimization wired into `PossibilitySpaceExplorer` via superforecaster pipeline
7. ✅ Docs consolidated → `docs/architecture/SIMULATION_QUANTUM_STRATEGY.md`, originals archived

**Future R&D — Hyperscaled Cognitive Simulation (P5, multi-week)**:

Existing infrastructure to leverage:
- `SimulationOrchestrator` (`core/consciousness/simulation_orchestrator.py`) — yin/yang simulation cycles, already wired to PossibilitySpaceExplorer + ResearchDAG
- `AgentSwarm` (`agents/swarm.py`) — multi-agent coordination with decomposition, routing, consensus
- `GlobalWorkspace` (`core/consciousness/global_workspace.py`) — competitive ignition + broadcast
- `EmergenceEngine` — 5 detection modes + novelty filtering (anti-echo)
- `galaxy.export` / `galaxy.import` MCP tools — Arrow IPC serialization with 6D coords (foundation for snapshot/restore)
- `MCForecastEnhancer` — HLL dedup + CMS adaptive trial allocation
- `SurpriseGate` — embedding-based surprisal scoring with adaptive thresholds
- `CrossDomainCollisionDetector` — schema abstraction across domains
- `Brier scoring` + `TemporalForecastDB` — prediction calibration infrastructure
- `DreamCycle` — 12-phase offline consolidation
- `PossibilitySpaceExplorer` — superforecaster pipeline (LHS→PCE→Sobol→BO)

Key architectural decisions:
- **Agent decision-making**: Option C (Hybrid) — LLM for high-stakes decisions, tool-selection heuristic for routine steps
- **Galaxy snapshot/restore**: Extend existing `arrow_export`/`arrow_import` to include associations + HNSW index + galaxy config (not just memories + coords)

Implementation phases (see `docs/architecture/SIMULATION_QUANTUM_STRATEGY.md` §6 for full details):

| Phase | Components | Effort | Dependencies |
|-------|-----------|--------|-------------|
| P5.1: Foundation | PersonaEngine, WorldModelBuilder, Galaxy snapshot/restore | 2-3 weeks | Galaxy snapshot/restore is the critical enabler |
| P5.2: Interaction | InteractionEngine, EmergenceEngine extension, GlobalWorkspace integration | 2-3 weeks | P5.1 |
| P5.3: Hyperscaled MC | ScenarioRunner, PossibilitySpaceExplorer extension, MCForecastEnhancer wiring | 2-3 weeks | P5.1, P5.2 |
| P5.4: MCTS Search | TrajectoryTreeSearch, semantic compass (HRR), adaptive horizon, isolation islands | 2-3 weeks | P5.3 |
| P5.5: Calibration | PredictionCalibrationBridge, Brier scoring wiring | 1 week | P5.3 |
| P5.6: Synthesis | InsightSynthesizer, AssociationMiner/SerendipityEngine/CrossDomainDetector wiring | 1-2 weeks | P5.4 |
| P5.7: Consolidation | DreamCycleIntegration, cross-simulation mining | 1 week | P5.6 |
| P5.8: MCP Tools | `simulation.create/run/search/inject/analyze/synthesize/calibrate` (7 tools) | 1 week | P5.1-P5.7 |

Galaxy snapshot/restore technical plan:
- Extend `arrow_export()` in `unified.py` to serialize: memories + 6D coords + associations + HNSW index state + galaxy config
- New `galaxy.snapshot` MCP tool — creates a named snapshot (stored as compressed file or in a dedicated snapshot galaxy)
- New `galaxy.restore` MCP tool — restores from snapshot into a new or existing galaxy
- Support branching: restore snapshot into a new galaxy for trajectory divergence
- This enables MCTS trajectory branching from any point in simulation history

**Polyglot upgrades** (not blocking, parallel to P5):
- Julia QuantumGeometry.jl for exact Riemannian geometry (Manifolds.jl + ForwardDiff.jl)
- Haskell topological verification for exact arithmetic (Berry phase, Chern number, roundtrip proofs)

### Theme 4: Consciousness & Cognition (closes #6, #7, #9)
**Status**: ConsciousnessLoop daemon operational, 3/9 neuro upgrades done, 10-galaxy taxonomy live, neuromodulation bridge (DA/5HT/ACh) + predictive coder exist. Missing: frequency modes, 6D coords as formal coordinate, 6 neuro upgrades, doc consolidation.

Existing infrastructure to leverage:
- `ConsciousnessLoop` (`core/consciousness/consciousness_loop.py`) — background daemon, citta every 30s, dream cycle, homeostatic loop
- `NeuromodulationBridge` (`core/memory/neuromodulation.py`) — DA/5HT/ACh via Julia bridge with Python fallback
- `PredictiveCoder` (`core/memory/neuro_hotpath.py`) — prediction error computation for memory writes
- `NeuroSensorium` (`core/consciousness/neuro_sensorium.py`) — integrates neuro signals into citta
- `CittaVector` (`core/consciousness/citta_vector.py`) — 8D consciousness state vector
- `GunaBalanceMetric` (`core/consciousness/guna_balance.py`) — sattvic/rajasic/tamasic tracking + auto-correction
- `CoherenceMetric` (`core/consciousness/coherence.py`) — 8D coherence measurement
- `DreamCycle` (`core/dreaming/dream_cycle.py`) — 12-phase offline consolidation
- `GlobalWorkspace` (`core/consciousness/global_workspace.py`) — competitive ignition + broadcast
- `HolographicCoordinate` — currently 5D `(x, y, z, w, v)`, 6th dimension `g` already used in export but not in dataclass
- `galaxy.export`/`galaxy.import` — already include `g` field in Arrow IPC serialization
- `galaxy.transfer` / `galaxy.sync` — cross-galaxy memory transfer already works

**Resolution path**:

**Phase 1: Frequency Modes (P4.1, ~1 week)**
1. Add meditation mode — low-frequency citta cycle (5min intervals), reduced tool dispatch, inward-focused attention
2. Add REM sleep mode — dream cycle with memory consolidation priority, heightened association mining
3. Add deep processing mode — high-frequency citta cycle (10s intervals), focused tool execution, suppressed dreaming
4. Wire mode transitions to GunaBalanceMetric (auto-suggest mode based on guna ratios)
5. Add `consciousness.mode` MCP tool (set/get frequency mode)
6. Env var `WM_CITTA_MODE=meditation|rem|deep|normal`

**Phase 2: 6D Holographic Coordinates (P4.2, ~1 week)**
7. Extend `HolographicCoordinate` dataclass: `(x, y, z, w, v)` → `(x, y, z, w, v, g)` where `g` = galaxy identity hash
8. Update all coord construction sites (store, search, transfer) to include `g`
9. Update HNSW index to use 6D distance (or keep 5D + galaxy filter — evaluate tradeoff)
10. Update manifold detection to work per-galaxy (already done in `embeddings.py`)
11. Add `galaxy.snapshot` / `galaxy.restore` MCP tools (shared dependency with P5.1)

**Phase 3: Neuro Upgrades (P4.3, ~2 weeks)**
12. **Dendritic computation** — multi-input integration in citta vector (compartmental model: proximal/distral/apical inputs with nonlinear integration)
13. **Neuromodulation gating** — extend existing DA/5HT/ACh bridge to gate tool dispatch (DA → exploration, 5HT → consolidation, ACh → attention focus)
14. **Predictive coding** — extend existing `PredictiveCoder` to top-down expectation vs bottom-up signal in citta advance (currently only memory writes)
15. **Cortical column** — hierarchical processing layers in citta (L1: sensory, L2: association, L3: integration, L4: motor output)
16. **Attention mechanisms** — softmax attention over memory candidates in recall (supplement Born-rule sampling with attention-weighted selection)
17. **Oscillatory binding** — phase synchronization across citta dimensions (theta/gamma coupling for memory binding)

**Phase 4: Cross-AI Galaxy Sharing (P4.4, ~1 week)**
18. Define galaxy sharing protocol — consent-based export/import with Ed25519 signing (reuse pulse verification keys)
19. Add `galaxy.share` MCP tool — export galaxy with consent manifest, sign with node identity
20. Add `galaxy.receive` MCP tool — import shared galaxy with consent verification
21. Wire to P2P mesh — broadcast galaxy share offers, receive via experiment sync channel

**Phase 5: Doc Consolidation (P4.5, ~30 min)**
22. Merge CONTINUOUS_CONSCIOUSNESS_STRATEGY + GALAXY_6D_STRATEGY + POLYGLOT_NEURO_UPGRADES_STRATEGY → `docs/architecture/COGNITIVE_ARCHITECTURE_STRATEGY.md`
23. Archive originals to `docs/archive/strategy/`
24. Update INDEX.md

---

## 3. Execution Priority

Ordered by impact-to-effort ratio and dependency chains:

| Priority | Theme | Status | Sessions | Why This Order |
|----------|-------|--------|----------|----------------|
| **P1** | Theme 2: Local Inference | ✅ Done | 3-4 | Everything else benefits from faster local inference |
| **P2** | Theme 1: P2P Mesh | ✅ Done | 1-2 | Nearly complete, closes 2 docs, enables distributed research |
| **P3** | Theme 3: Quantum & Simulation | ✅ Done | 5-7 | Core primitives + MC infrastructure + production wiring complete |
| **P4** | Theme 4: Consciousness & Cognition | ✅ Done | 3-4 | Frequency modes, 6D coords, 6 neuro upgrades, galaxy sharing, doc consolidation — all implemented |
| **P5** | Hyperscaled Cognitive Simulation | ✅ Done | 2 sessions | 8 components, 17 MCP tools, 102 tests. All 6 identified gaps resolved. Doc archived to `docs/archive/strategy/` |

**Dependency note**: P4.2 (galaxy snapshot/restore) and P5.1 (Foundation) share the galaxy snapshot/restore implementation. P4 should be done first to provide the consciousness infrastructure (frequency modes, neuro upgrades) that P5's PersonaEngine and InteractionEngine will leverage.

---

## 4. Doc Consolidation Plan

After resolving each theme, consolidate the source docs:

| Theme | Source Docs | Merged Into | Archive Sources |
|-------|-------------|-------------|-----------------|
| Theme 1 ✅ | RESEARCH_SYSTEMS_STRATEGY.md, HYPERSPACE_INTEGRATION_STRATEGY.md | `docs/architecture/P2P_MESH_ARCHITECTURE.md` | `docs/archive/` |
| Theme 2 ✅ | LOCAL_MODEL_ROADMAP_2026-07-11.md, CPU_INFERENCE_STRATEGY.md | `docs/architecture/LOCAL_INFERENCE_ARCHITECTURE.md` | `docs/archive/` |
| Theme 3 ✅ | NUMERICAL_MC_STRATEGY.md, QUANTUM_POLYGLOT_STRATEGY_2026-07-11.md, MIRO_SIMULATION_IMPROVEMENT.md | `docs/architecture/SIMULATION_QUANTUM_STRATEGY.md` | `docs/archive/strategy/` |
| Theme 4 | CONTINUOUS_CONSCIOUSNESS_STRATEGY.md, GALAXY_6D_STRATEGY.md, POLYGLOT_NEURO_UPGRADES_STRATEGY.md | `docs/architecture/COGNITIVE_ARCHITECTURE_STRATEGY.md` | `docs/archive/strategy/` |

**WEBSITE_NARRATIVE_PRESCIENCE.md** stays as-is (ongoing, non-engineering).

**Result**: 11 partial docs → 4 consolidated architecture docs + 1 ongoing doc. Message board drops from 10 to 3 active files (STRATEGY.md, DISTRIBUTION_STRATEGY.md, NEXT_SESSION_ONBOARDING.md).

---

## 5. Quick Wins (do first, <30 min each)

1. ~~**Compile gRPC protos**~~ ✅ Done — `mesh_pb2.py` + `mesh_pb2_grpc.py` generated, MeshClient connects with real gRPC stubs
2. ~~**Wire auto-optimizer as middleware**~~ ✅ Done — `mw_auto_optimize` in dispatch pipeline
3. ~~**Upgrade pulse verification to real Ed25519**~~ ✅ Done — PyNaCl SigningKey/VerifyKey with persistent keypairs
4. ~~**Wire Born-rule sampling into serendipity**~~ ✅ Done — `born_rule_sample` used in both `_surface_quantum` and `_surface_dormant`

**P4 Quick Wins** (when starting Theme 4):
5. **Add 6th dimension to holographic coords** — extend `(x, y, z, w, v)` → `(x, y, z, w, v, g)` in `HolographicCoordinate` dataclass (`g` already used in `arrow_export`, just not in the dataclass yet)
6. **Add meditation frequency mode** — env var `WM_CITTA_MODE=meditation` → 5min citta intervals, suppressed dreaming, inward focus (simplest mode to implement, immediate value)

**P5 Quick Win** (shared dependency, do with P4.2):
7. **Galaxy snapshot/restore MVP** — extend `arrow_export` to include associations + galaxy config, add `galaxy.snapshot` / `galaxy.restore` MCP tools (enables both P4.2 and P5.1)

---

*This meta-strategy supersedes the priority lists in NEXT_SESSION_ONBOARDING.md. After each theme is resolved, update this doc and archive the source docs.*
