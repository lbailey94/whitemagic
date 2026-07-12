# P5 Integration Strategy: Hyperscaled Cognitive Simulation

**Version**: 2.0
**Date**: July 12, 2026
**Status**: Complete — all 8 components built, 17 MCP tools, 102 tests. All identified gaps resolved.

---

## Overview

P5 is WhiteMagic's hyperscaled cognitive simulation system — 8 components that enable
multi-agent cognitive simulation at Monte Carlo scale. Unlike MiroFish (LLM prompts with
personality descriptions), WM personas are structured cognitive profiles with measurable
internal states that drift over simulation time.

The system explores millions of trajectories through possibility space, detects emergent
patterns across trajectory populations, and synthesizes novel-and-useful insights through
a calibrated pipeline with honest Brier-scored forecasting.

**Prerequisites satisfied**:
- P4.2 (galaxy snapshot/restore) — ✅ implemented, enables world branching
- P4.1 (frequency modes) — ✅ implemented, enables simulation-time control
- P4.3 (neuro upgrades) — ✅ implemented, enriches persona cognitive states

---

## 8 Components

### Component 1: PersonaEngine — Cognitive Agent Generation

**File**: `core/whitemagic/core/simulation/persona_engine.py` (271 lines)
**Status**: ✅ Implemented

Generates diverse cognitive agents with structured profiles:
- Coherence baseline, guna balance (sattvic/rajasic/tamasic), emotional baseline
- Depth layer (0=surface → 4=deepest), capability set, dharma strictness
- Curiosity, adaptability, creativity scores
- 5 preset archetypes: analyst, creative, conservative, explorer, synthesizer
- Mutation cloning for evolutionary simulation
- Natural drift toward baseline over simulation time

**MCP tool**: `simulation.create` (via world creation + persona specs)

### Component 2: WorldModelBuilder — Simulation Environment

**File**: `core/whitemagic/core/simulation/world_model.py` (257 lines)
**Status**: ✅ Implemented

Builds simulation worlds from seed documents:
- Ingests into dedicated `simulation/<name>` galaxy
- Entity extraction (currently regex-based — see Gaps section)
- Simulation rules with Dharma profiles
- Galaxy snapshot/restore for branching trajectories
- Multiple simultaneous world models via galaxy isolation

**MCP tool**: `simulation.create`

### Component 3: InteractionEngine — Multi-Agent Cognitive Simulation

**File**: `core/whitemagic/core/simulation/interaction_engine.py` (290 lines)
**Status**: ✅ Implemented

Simulates agents interacting, debating, and influencing each other:
- 5 action types: speak, query, create, modify, reflect
- Action weights derived from cognitive profile (curiosity → query, creativity → create)
- Dharma governance constrains harmful modifications
- Impact scoring per event, emergence scoring per event
- GlobalWorkspace broadcast for significant events (shifts receiver coherence)
- Persona drift applied per tick

**MCP tool**: `simulation.run` (via ScenarioRunner)

### Component 4: ScenarioRunner — Multi-Trajectory Monte Carlo

**File**: `core/whitemagic/core/simulation/scenario_runner.py` (292 lines)
**Status**: ✅ Implemented

Runs N trials with varied initial conditions:
- Rust-accelerated LHS for 5000+ trials (via PolyglotMCOrchestrator)
- Gaussian random variation for smaller trial counts
- Outcome classification: converged, diverged, oscillating, collapsed
- Comparative analysis: outcome distribution, parameter sensitivity, robustness
- Branching point detection (high-emergence trials)

**MCP tool**: `simulation.run`

### Component 5: TrajectoryTreeSearch — MCTS-Guided Creative Exploration

**File**: `core/whitemagic/core/simulation/trajectory_search.py` (304 lines)
**Status**: ✅ Implemented (cognitive rollouts via InteractionEngine wired)

Structures trajectory search as a tree using novelty-biased MCTS:
- Selection: UCB1 + novelty bonus
- Expansion: branching factor controlled
- Simulation: lightweight rollout (currently random — see Gaps section)
- Backpropagation: value updates up the tree
- Best trajectory extraction by most-visited path

**MCP tool**: `simulation.search`

### Component 6: PredictionCalibrationBridge — Honest Forecasting

**File**: `core/whitemagic/core/simulation/calibration_bridge.py` (210 lines)
**Status**: ✅ Implemented (persisted to TemporalForecastDB)

Every simulation produces calibrated predictions:
- Brier score: (predicted_prob - actual_outcome)²
- Calibration gap: moving average of last 50 Brier scores × 0.1
- Calibration bins: 10 probability ranges with actual occurrence rates
- Scorecard: total/resolved/unresolved, avg Brier, calibration quality

**MCP tool**: `simulation.calibrate`

### Component 7: DreamCycleIntegration — Offline Consolidation

**File**: `core/whitemagic/core/simulation/dream_integration.py` (400 lines)
**Status**: ✅ Implemented

Wires simulation completion to DreamCycle phases:
- 6 phases: consolidation, serendipity, kaizen, oracle, prediction, narrative
- Lazy import of DreamCycle with fallback to simulated phases
- Cross-simulation association mining
- Next-run recommendation generation
- Delegation to real DreamCycle when available

**MCP tool**: `simulation.analyze` (with consolidate=true)

### Component 8: InsightSynthesizer — Emergent Insight Extraction

**File**: `core/whitemagic/core/simulation/insight_synthesizer.py` (389 lines)
**Status**: ✅ Implemented (insights persisted to codex galaxy)

Transforms filtered trajectory patterns into actionable insights:
- Pattern extraction (recurring outcomes)
- Cross-trajectory connection discovery (similar emergence, divergent outcomes)
- Anomaly detection (outlier coherence)
- Strategic insight generation (robustness, calibration quality)
- Composite ranking: novelty (0.3) + impact (0.25) + coherence (0.2) + cross-domain (0.15) + calibration (0.1)
- EmergenceEngine novelty filtering (anti-echo: 1st=full, 2nd=50%+recurring, 3rd+=suppressed)

**MCP tool**: `simulation.synthesize`

---

## Cross-Component Integration Points

### 1. DreamCycle → Simulation Consolidation

`DreamCycleIntegration._run_phase()` delegates to real `DreamCycle` when available, falls back to simulated phases.

- Phase mapping: simulation phases → DreamPhase enum values
- Delegation only used when results contain actual data
- Lazy import via `_try_import_dream_cycle()` avoids circular dependencies

### 2. EmergenceEngine → Insight Novelty Filtering

`InsightSynthesizer._filter_via_emergence_engine()` feeds ranked insights through `EmergenceEngine._filter_novel()`.

- Signature-based novelty detection prevents recursive echo chamber
- `Insight.confidence` adjusted by novelty filtering
- Pass-through when EmergenceEngine unavailable

### 3. PolyglotMCOrchestrator → Rust-Accelerated LHS

`ScenarioRunner.run_scenario()` delegates to `PolyglotMCOrchestrator.latin_hypercube()` when trials ≥ 5000.

- 2D samples (coherence + emotional_state) for initial condition variation
- Clamped to [0.0, 1.0] range
- Gaussian random fallback when Rust bridge unavailable or trials < 5000

---

## End-to-End Pipeline

```
1. SEED: simulation.create
   └── WorldModelBuilder ingests seed documents into simulation galaxy
   └── PersonaEngine generates cognitive agents with archetypes

2. IMAGINE: simulation.run
   └── ScenarioRunner runs N trials with varied initial conditions
   └── InteractionEngine simulates agent interactions per trial
   └── PolyglotMCOrchestrator provides Rust LHS for 5000+ trials

3. SEARCH: simulation.search
   └── TrajectoryTreeSearch explores trajectory space via MCTS
   └── UCB1 + novelty bonus guides creative exploration

4. EVALUATE: simulation.analyze
   └── Outcome distribution, coherence statistics
   └── DreamCycleIntegration runs 6-phase consolidation

5. SYNTHESIZE: simulation.synthesize
   └── InsightSynthesizer extracts patterns, connections, anomalies
   └── EmergenceEngine filters for novelty (anti-echo)
   └── Composite ranking: novelty + impact + coherence + cross-domain + calibration

6. CALIBRATE: simulation.calibrate
   └── PredictionCalibrationBridge records/resolve predictions
   └── Brier scoring validates against reality
   └── Calibration gap feeds back into future predictions
```

---

## MCP Tools (17 total)

### P5 Simulation Tools (8)
| Tool | Purpose | Gana |
|------|---------|------|
| `simulation.create` | Create world with personas, seeds, rules | gana_chariot |
| `simulation.run` | Run Monte Carlo scenario | gana_chariot |
| `simulation.search` | MCTS-guided trajectory search | gana_chariot |
| `simulation.inject` | Inject variables into running simulation | gana_chariot |
| `simulation.analyze` | Analyze results + dream consolidation | gana_winnowing_basket |
| `simulation.synthesize` | Synthesize emergent insights | gana_winnowing_basket |
| `simulation.calibrate` | Record/resolve predictions, scorecard | gana_hairy_head |
| `simulation.pipeline` | End-to-end P5 pipeline (create→run→analyze→synthesize→calibrate) | gana_three_stars |

### Orchestrator Tools (4)
| Tool | Purpose | Gana |
|------|---------|------|
| `simulation.introspect` | Introspective simulation (yin-within-yang) | gana_ghost |
| `simulation.forecast` | External research simulation (yang-within-yin) | gana_chariot |
| `simulation.status` | SimulationOrchestrator status | gana_ghost |
| `simulation.recursive` | Recursive yin/yang cycle | gana_ghost |

### MC Tools (5)
| Tool | Purpose | Gana |
|------|---------|------|
| `mc.surrogate` | GP surrogate fitting | gana_dipper |
| `mc.optimize` | Bayesian optimization | gana_dipper |
| `mc.rare_event` | Rare event probability estimation | gana_dipper |
| `mc.sde` | Stochastic differential equation solver | gana_dipper |
| `mc.superforecaster` | Full superforecaster pipeline | gana_dipper |

---

## Testing

- `test_simulation.py` (589 lines) — unit tests for all 8 components + handler tests
- `test_simulation_wiring.py` (203 lines) — orchestrator delegation + tool registration
- `test_simulation_integration.py` (518 lines) — MC handlers, orchestrator, superforecaster, autoswarm
- **102 tests passing**, 0 failures
- All tests pass with both real DreamCycle (when available) and fallback simulated phases

---

## Known Gaps and Refinement Roadmap

### Gap 1: `simulation.inject` is a no-op stub
**Status**: ✅ Resolved — Wired to ScenarioRunner.inject(), injection_points passed through to InteractionEngine._apply_injection()

### Gap 2: TrajectoryTreeSearch disconnected from ScenarioRunner
**Status**: ✅ Resolved — create_cognitive_rollout() helper uses InteractionEngine for MCTS rollouts; handler supports use_cognitive_rollout option

### Gap 3: No end-to-end pipeline tool
**Status**: ✅ Resolved — simulation.pipeline tool chains create → run → analyze → synthesize → persist → calibrate, registered in dispatch/registry/PRAT/NLU

### Gap 4: CalibrationBridge not persisted
**Status**: ✅ Resolved — record_prediction() and resolve_prediction() now persist to TemporalForecastDB with forecast_db_id metadata

### Gap 5: No multi-galaxy routing
**Status**: ✅ Resolved — DreamCycleIntegration.persist_consolidation() routes by phase: narrative/oracle → dreams, kaizen/prediction → research, others → codex

### Gap 6: Insights not stored as memories
**Status**: ✅ Resolved — InsightSynthesizer.persist_insights() stores top-ranked insights as long-term memories in codex galaxy with full metadata

### Gap 7: Entity extraction is naive regex
**Status**: Future
Uses `re.findall(r'\b[A-Z][a-z]+')` instead of association miner.
**Fix**: Wire to AssociationMiner for proper entity extraction.

### Gap 8: InteractionEngine content is template strings
**Status**: Future
Actions generate hardcoded templates, not cognitive processing.
**Fix**: Wire to inference router for LLM-generated content.

---

## Future Directions

1. **DreamCycle bidirectional**: Simulation → DreamCycle (done). Add DreamCycle → simulation (dream insights seed new scenarios)
2. **EmergenceEngine cross-session**: Persist novelty signatures across sessions
3. **PolyglotMC auto-threshold**: Dynamically adjust 5000-trial threshold based on Rust bridge availability
4. **Insight confidence propagation**: Feed `Insight.confidence` back into DreamCycle consolidation priority
5. **Simulation dashboard**: Next.js visualization for trajectory trees, outcome distributions, calibration scorecards
6. **Hyperscale Julia backend**: Julia QuantumGeometry.jl for exact Riemannian geometry in trajectory evaluation
