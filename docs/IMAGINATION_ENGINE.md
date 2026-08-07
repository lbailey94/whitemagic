# WhiteMagic v4 — Imagination Engine Design & Implementation Plan

**Created**: August 7, 2026
**Status**: Design document, pending implementation

---

## 1. Motivation

v4 has built substantial simulation, prediction, and pattern-matching infrastructure,
but these systems are **siloed** — they exist as standalone crates/tools that aren't
wired into the cognitive loop. The system can remember and reason, but it cannot
*imagine*, *simulate futures*, or *research novel solutions*.

The goal: enable v4 to think ahead, imagine different scenarios, evaluate them, and
choose the best course of action — the same way humans use mental simulation to plan,
create, and discover.

---

## 2. Research Findings

### 2.1 SR²AM — Self-Regulated Simulative Reasoning (2026)

**Paper**: "Efficient Agentic Reasoning Through Self-Regulated Simulative Planning"
(Deng et al., arXiv:2605.22138)

**Key insight**: Decompose deliberation into three interacting systems:
- **System I — Reactive Execution**: fast, intuitive, direct action (v4's edge rules + Tier 0)
- **System II — Simulative Reasoning**: predicts consequences of proposed actions through
  a world model, providing unified planning across diverse tasks
- **System III — Self-Regulation**: a learned configurator decides *when* and *how deeply*
  to plan

**Results**: SR²AM-v0.1-8B competitive with 120–355B systems while using 25–95% fewer
reasoning tokens. RL increases average planning horizon by 22.8% while planning frequency
grows only 2.0% — the model learns to *plan further ahead*, not *more often*.

**v4 mapping**:
- System I → `EdgeRuleHandler` (Tier 0, zero-token) + `InferenceRouter` fast path
- System II → **NEW: ScenarioEngine** (this proposal)
- System III → **NEW: ImaginationConfigurator** (this proposal) — decides when to simulate

### 2.2 ITP — Imagine-then-Plan (2026)

**Paper**: "Imagine-then-Plan: Agent Learning from Adaptive Lookahead with World Models"
(Liu et al., arXiv:2601.08955)

**Key insight**: Agents should "mentally rehearse" possible futures before committing
actions. Introduces **adaptive lookahead** — dynamically scales imagination horizon K
based on task complexity and estimated progress. Formulates this as a **POIMDP**
(Partially Observable and Imaginable MDP).

**Two variants**:
- **ITP-I** (training-free): At each step, (1) decide horizon K, (2) roll out K steps
  in world model, (3) reflect on imagined trajectory, (4) act.
- **ITP-R** (reinforcement-trained): Learns *when* and *how long* to imagine via a
  K-head predictor trained with A2C.

**v4 mapping**: ITP-I maps directly to v4's architecture — the bicameral engine can
serve as both the world model and the reflector. No training needed; we use prompt
engineering.

### 2.3 DMWM — Dual-Mind World Model (NeurIPS 2025)

**Paper**: "DMWM: Dual-Mind World Model with Long-Term Imagination"
(Wang et al., NeurIPS 2025 spotlight)

**Key insight**: Dual-process theory applied to world models. System 1 (RSSM-based)
handles fast intuitive state transitions; System 2 (logic-integrated neural network)
guides imagination through hierarchical logical reasoning. Inter-system feedback
ensures logical consistency.

**Results**: 14.3% improvement in logic consistency, 5.5-fold trial efficiency,
120% improvement in reliable imagination over extended horizons.

**v4 mapping**: v4's bicameral engine IS a dual-mind system (left=analytical,
right=creative). The missing piece is the "world model" — a function that predicts
"what happens if I take action X in state Y."

### 2.4 MAP — Modular Agentic Planner (Nature Communications 2025)

**Paper**: "A brain-inspired agentic architecture to improve planning with LLMs"
(Nature Communications, 2025)

**Key insight**: PFC-inspired modular decomposition: conflict monitoring, state
prediction, state evaluation, task decomposition, task coordination. LLMs can do
each function in isolation but struggle to coordinate them autonomously.

**v4 mapping**: v4 already has conflict monitoring (Dharma gate), task decomposition
(autonomous cycles), and coordination (daemon). Missing: **state prediction** and
**state evaluation** as explicit modules.

### 2.5 SimuRA — World-Model-Driven Simulative Reasoning (2025)

**Paper**: "SimuRA: A World-Model-Driven Simulative Reasoning Architecture"
(arXiv:2507.23773)

**Key insight**: Incorporate world model for planning via simulation. LLM as world
model substrate, using natural language as discrete hierarchical representation.
Up to 124% higher task completion rates vs black-box autoregressive baseline.

### 2.6 SynWorld — Virtual Scenario Synthesis (ACL 2025)

**Paper**: "SynWorld: Virtual Scenario Synthesis for Agentic Action Knowledge Refinement"
(Fang et al., ACL 2025)

**Key insight**: Agents synthesize possible scenarios with multi-step action invocation
and perform **MCTS exploration** to refine action knowledge in new environments.

### 2.7 Mental Simulation in Deep Learning (ICLR 2020, still relevant)

**Paper**: "Analogues of mental simulation and imagination in deep learning"
(ICLR 2020)

**Key insight**: Mental simulation = model-based methods. Decision-time planning
(MCTS rollouts), background planning (value iteration), and their deep learning
approximations. The combinatorial explosion of possible futures is the core challenge.

---

## 3. Architecture Design

### 3.1 Overview

The Imagination Engine connects v4's existing siloed systems into a unified cognitive
loop that can **imagine → simulate → evaluate → decide**.

```
                    ┌─────────────────────────────────┐
                    │     ImaginationConfigurator      │  (System III)
                    │  "Should I simulate? How deep?"  │
                    └────────┬───────────┬────────────┘
                             │           │
                    ┌────────▼──┐   ┌───▼────────────┐
                    │  Reactor  │   │  ScenarioEngine │  (System II)
                    │ (System I)│   │  "What if...?"  │
                └───┘  Direct   │   │                 │
                    │  action   │   │  ┌────────────┐ │
                    └───────────┘   │  │ WorldModel │ │
                                    │  │ (LLM-based)│ │
                                    │  └──────┬─────┘ │
                                    │         │       │
                                    │  ┌──────▼─────┐ │
                                    │  │  Evaluator │ │
                                    │  │ (score     │ │
                                    │  │  outcomes) │ │
                                    │  └──────┬─────┘ │
                                    └─────────┼───────┘
                                              │
                                    ┌─────────▼─────────┐
                                    │  Memory Integration│
                                    │  - Store scenarios │
                                    │  - Retrieve priors │
                                    │  - Pattern match   │
                                    └───────────────────┘
```

### 3.2 Core Components

#### A. WorldModel (new, in `wm-bicameral`)

A text-based world model that predicts the next state given a current state and
proposed action. Uses the bicameral engine's LLM hemispheres:

```rust
pub struct WorldModel {
    /// Left hemisphere (analytical, deterministic) for state prediction
    left: Arc<dyn TierHandler>,
    /// Right hemisphere (creative, stochastic) for alternative generation
    right: Arc<dyn TierHandler>,
}

pub struct PredictedState {
    /// Natural language description of predicted outcome
    pub description: String,
    /// Confidence in prediction (0.0–1.0)
    pub confidence: f32,
    /// Key changes from current state
    pub changes: Vec<String>,
    /// Risk factors identified
    pub risks: Vec<String>,
    /// Goal progress estimate (0.0–1.0)
    pub goal_progress: f32,
}

impl WorldModel {
    /// Predict the outcome of taking `action` in `state`
    pub fn predict(&self, state: &str, action: &str, goal: &str) -> PredictedState;

    /// Roll out K steps of imagination
    pub fn rollout(&self, state: &str, actions: &[String], goal: &str) -> Vec<PredictedState>;
}
```

**Design rationale**: Following ITP and SimuRA, the LLM itself serves as the world
model in language space. No separate training needed — we use prompt engineering
with the existing bicameral hemispheres. Left hemisphere (SmolLM2, temp 0.2) for
deterministic state prediction; right hemisphere (Llama 3.2, temp 0.7) for generating
diverse alternative scenarios.

#### B. ScenarioEngine (new, in `wm-bicameral`)

Generates candidate actions, simulates their outcomes, and scores them:

```rust
pub struct ScenarioEngine {
    world_model: WorldModel,
    evaluator: ScenarioEvaluator,
    config: ScenarioConfig,
}

pub struct Scenario {
    /// The proposed action/plan
    pub action: String,
    /// Predicted outcome trajectory
    pub trajectory: Vec<PredictedState>,
    /// Overall quality score (0.0–1.0)
    pub score: f32,
    /// Estimated risk (0.0–1.0)
    pub risk: f32,
    /// Estimated novelty (0.0–1.0)
    pub novelty: f32,
    /// Rationale for this scenario
    pub rationale: String,
}

pub struct ScenarioConfig {
    /// Number of candidate actions to generate
    pub n_candidates: usize,
    /// Maximum imagination horizon (steps to look ahead)
    pub max_horizon: usize,
    /// Whether to use creative hemisphere for candidates
    pub use_creative: bool,
    /// Minimum novelty threshold to include a scenario
    pub min_novelty: f32,
}

impl ScenarioEngine {
    /// Generate and evaluate scenarios for a given state and goal
    pub fn imagine(&self, state: &str, goal: &str, memory_context: &str)
        -> Vec<Scenario>;

    /// Select the best scenario from candidates
    pub fn select_best(&self, scenarios: &[Scenario]) -> Option<&Scenario>;
}
```

#### C. ScenarioEvaluator (new, in `wm-bicameral`)

Scores predicted outcomes using multiple criteria:

```rust
pub struct ScenarioEvaluator {
    /// Historical success rate of similar actions (from memory)
    success_rate: f32,
    /// Weight for goal progress
    pub goal_weight: f32,
    /// Weight for risk avoidance
    pub risk_weight: f32,
    /// Weight for novelty/exploration
    pub novelty_weight: f32,
}

impl ScenarioEvaluator {
    /// Score a scenario's predicted trajectory
    pub fn score(&self, trajectory: &[PredictedState], goal: &str) -> f32;

    /// Assess novelty by comparing to historical patterns
    pub fn novelty(&self, action: &str, memory_context: &str) -> f32;
}
```

#### D. ImaginationConfigurator (new, in `wm-bicameral`)

System III — decides when and how deeply to simulate:

```rust
pub enum DeliberationMode {
    /// Direct action — no simulation needed (simple/routine tasks)
    Direct,
    /// Shallow simulation — 1-2 steps ahead (moderate complexity)
    Shallow,
    /// Deep simulation — 3-5 steps ahead with multiple candidates (complex/novel)
    Deep,
    /// Research mode — extended simulation with memory storage (novel problems)
    Research,
}

pub struct ImaginationConfigurator {
    /// Complexity threshold for shallow mode
    pub shallow_threshold: f32,
    /// Complexity threshold for deep mode
    pub deep_threshold: f32,
    /// Complexity threshold for research mode
    pub research_threshold: f32,
}

impl ImaginationConfigurator {
    /// Decide deliberation mode based on task complexity, novelty, and stakes
    pub fn decide(&self, task: &str, novelty: f32, stakes: f32) -> DeliberationMode;
}
```

**Design rationale**: Directly inspired by SR²AM's configurator (System III). The
key insight is that not every task needs simulation — routine tool dispatches should
go direct (System I), while novel/complex problems trigger imagination (System II).

#### E. CycleType::Research (new, in `wm-consciousness`)

A new autonomous cycle that uses the imagination engine for creative exploration:

```rust
// In autonomous.rs CycleType enum:
Research,  // Form hypotheses, simulate outcomes, store findings

// Research cycle:
// 1. Identify knowledge gaps from memory (unanswered questions, low-confidence areas)
// 2. Form hypotheses using bicameral engine (left: analytical, right: creative)
// 3. Simulate each hypothesis using ScenarioEngine
// 4. Score outcomes, select most promising
// 5. Store findings as MemoryType::Hypothesis in Codex galaxy
// 6. Log to Substrate galaxy
```

#### F. Dream Cycle Integration

Add simulation phases to the existing 12-phase dream cycle:

- **Phase 13: Counterfactual Replay** — For recent important decisions, run
  counterfactual simulation ("what would have happened if we chose X instead?")
  using `CounterfactualEstimator` from `wm-simulation`
- **Phase 14: Hypothesis Generation** — Use the bicameral engine to generate
  novel hypotheses from the day's memory patterns, simulate them, and store
  promising ones as `MemoryType::Hypothesis`

#### G. Expanded Self-Model Metrics

Add cognitive metrics alongside the existing hardware metrics:

```rust
// In wm-selfmodel/src/metrics.rs MetricKind:
ToolEffectiveness,      // Per-task-type tool success rate
ReasoningQuality,       // Bicameral debate outcome quality
NoveltyRate,            // How often system encounters new situations
ImaginationAccuracy,    // How often predicted outcomes match actual
HypothesisSuccess,      // How many stored hypotheses were validated
```

---

## 4. Implementation Plan

### Phase I: World Model & Scenario Engine (wm-bicameral)

**Goal**: Build the core "imagine → simulate → evaluate" loop.

| Step | Component | Description |
|------|-----------|-------------|
| I.1 | `world_model.rs` | `WorldModel` struct with `predict()` and `rollout()` using existing `TierHandler` trait |
| I.2 | `scenario.rs` | `Scenario`, `ScenarioConfig`, `ScenarioEngine` with `imagine()` and `select_best()` |
| I.3 | `evaluator.rs` | `ScenarioEvaluator` with multi-criteria scoring (goal progress, risk, novelty) |
| I.4 | `configurator.rs` | `ImaginationConfigurator` with `DeliberationMode` decision logic |
| I.5 | `lib.rs` exports | Export all new types from `wm-bicameral` |
| I.6 | Tests | Unit tests for each component (predict, rollout, score, novelty, decide) |

**Estimated**: ~1,500 lines, 30 tests

### Phase II: Research Cycle & Memory Integration (wm-consciousness)

**Goal**: Wire the imagination engine into the autonomous cycle framework.

| Step | Component | Description |
|------|-----------|-------------|
| II.1 | `CycleType::Research` | New cycle variant in `autonomous.rs` |
| II.2 | `run_research()` | Cycle implementation: identify gaps → form hypotheses → simulate → store |
| II.3 | `MemoryType::Hypothesis` | New memory type for storing research findings |
| II.4 | Dream cycle integration | Add counterfactual replay + hypothesis generation phases |
| II.5 | Tests | Cycle tests with mock memory store |

**Estimated**: ~800 lines, 15 tests

### Phase III: Self-Model Expansion (wm-selfmodel)

**Goal**: Track cognitive metrics, not just hardware metrics.

| Step | Component | Description |
|------|-----------|-------------|
| III.1 | New `MetricKind` variants | ToolEffectiveness, ReasoningQuality, NoveltyRate, ImaginationAccuracy, HypothesisSuccess |
| III.2 | `record_cognitive()` | Method on `SelfModel` to record cognitive metrics |
| III.3 | `forecast_cognitive()` | Forecast cognitive trends (e.g., "imagination accuracy improving over time") |
| III.4 | Alert rules | Cognitive alert rules (e.g., "novelty rate too low → suggest research cycle") |
| III.5 | Tests | Tests for new metrics, forecasts, and alerts |

**Estimated**: ~500 lines, 12 tests

### Phase IV: MCP Tools & Daemon Integration (wm-tools, wm-mcp)

**Goal**: Expose imagination capabilities as tools and wire into daemon.

| Step | Component | Description |
|------|-----------|-------------|
| IV.1 | `imagine.scenario` tool | Generate scenarios for a given state + goal |
| IV.2 | `imagine.predict` tool | Predict outcome of a specific action |
| IV.3 | `imagine.reflect` tool | Counterfactual reflection on past decisions |
| IV.4 | NLU routing | Add routing profiles for imagination tools |
| IV.5 | Daemon integration | Add `research_interval` to `DaemonConfig`, wire `CycleType::Research` |
| IV.6 | CLI flag | `wm daemon --research-interval 3600` |
| IV.7 | Tests | Tool tests, NLU routing tests, daemon config tests |

**Estimated**: ~600 lines, 15 tests

### Phase V: Simulation Wiring (wm-simulation ↔ wm-bicameral)

**Goal**: Connect the existing MC/counterfactual/forecasting infrastructure to the
scenario engine.

| Step | Component | Description |
|------|-----------|-------------|
| V.1 | MC-based outcome sampling | Use `MonteCarloSimulator` to sample multiple possible outcomes per action |
| V.2 | Counterfactual evaluation | Use `CounterfactualEstimator` for "did this decision cause that outcome?" |
| V.3 | Forecast-based priors | Use `Forecaster` to provide prior expectations for scenario evaluation |
| V.4 | Sensitivity analysis | Use `SensitivityAnalyzer` to identify which factors most influence outcomes |
| V.5 | Tests | Integration tests between simulation and scenario engine |

**Estimated**: ~400 lines, 10 tests

### Phase VI: Pattern Matching Integration

**Goal**: Use existing pattern-matching systems to inform scenario evaluation.

| Step | Component | Description |
|------|-----------|-------------|
| VI.1 | Constellation-based novelty | Use `ConstellationDetector` to assess whether a scenario is in familiar territory |
| VI.2 | Strategy-informed evaluation | Use `StrategySynthesizer` patterns as priors for scenario scoring |
| VI.3 | Neural dynamics for scenario activation | Use `SpreadingActivation` to retrieve relevant memories for scenario context |
| VI.4 | Predictive coding for surprise | Use `SurpriseGate` to flag unexpected predicted outcomes for deeper analysis |
| VI.5 | Tests | Integration tests |

**Estimated**: ~400 lines, 10 tests

---

## 5. Total Estimates

| Phase | Lines | Tests | Crates |
|-------|-------|-------|--------|
| I: World Model & Scenario Engine | ~1,500 | ~30 | wm-bicameral |
| II: Research Cycle & Memory | ~800 | ~15 | wm-consciousness |
| III: Self-Model Expansion | ~500 | ~12 | wm-selfmodel |
| IV: MCP Tools & Daemon | ~600 | ~15 | wm-tools, wm-mcp |
| V: Simulation Wiring | ~400 | ~10 | wm-bicameral, wm-simulation |
| VI: Pattern Matching Integration | ~400 | ~10 | wm-consciousness, wm-bicameral |
| **Total** | **~4,200** | **~92** | |

---

## 6. Key Design Decisions

### 6.1 LLM as World Model (no separate training)

Following ITP and SimuRA, we use the existing bicameral LLM hemispheres as the world
model in language space. No separate model training needed — prompt engineering with
the existing SmolLM2 (left, deterministic) and Llama 3.2 (right, creative) suffices.

### 6.2 Adaptive Horizon (SR²AM-inspired)

The `ImaginationConfigurator` decides deliberation depth:
- **Direct**: Edge rules handle it (85% of queries, zero-token)
- **Shallow**: 1-2 step rollout (moderate tasks)
- **Deep**: 3-5 step rollout with multiple candidates (complex tasks)
- **Research**: Extended simulation with memory storage (novel problems)

This avoids the inefficiency of always-on simulation while ensuring deep planning
when needed.

### 6.3 Memory-Grounded Imagination

Scenarios are grounded in retrieved memories:
- `SpreadingActivation` finds relevant historical context
- `ConstellationDetector` assesses whether we're in familiar territory
- `StrategySynthesizer` provides pattern-based priors
- `CounterfactualEstimator` evaluates "did this decision cause that outcome?"

### 6.4 Hypothesis as First-Class Memory

New `MemoryType::Hypothesis` for storing research findings. Hypotheses can be:
- Validated (confirmed by subsequent experience)
- Invalidated (contradicted by subsequent experience)
- Pending (not yet tested)

This creates a feedback loop: imagination generates hypotheses → experience validates
them → validated hypotheses improve future imagination.

### 6.5 Dual-Mind Consistency (DMWM-inspired)

Following DMWM's inter-system feedback:
- Left hemisphere (System 1) generates fast intuitive predictions
- Right hemisphere (System 2) generates creative alternative scenarios
- Consensus gate checks for logical consistency between the two
- If they disagree, deeper simulation is triggered

---

## 7. Implementation Order

Phases can be partially parallelized:

```
Phase I (core engine) ──────┬───► Phase IV (tools & daemon)
                            │
Phase II (research cycle) ──┤
                            │
Phase III (self-model) ─────┤
                            │
Phase V (simulation) ───────┤
                            │
Phase VI (patterns) ────────┘
```

**Recommended order**: I → II → V → III → VI → IV

Phase I is the foundation. Phase II wires it into the autonomous cycle framework.
Phase V connects the existing simulation infrastructure. Phase III adds cognitive
metrics. Phase VI connects pattern matching. Phase IV exposes everything as tools.

---

## 8. Verification

- `cargo build` — all crates compile
- `cargo test` — all existing + ~92 new tests pass
- `cargo clippy --all-targets` — zero warnings
- `cargo fmt --all -- --check` — clean
- Manual: `wm daemon --research-interval 60` should trigger research cycles
- Manual: `wm(route="imagine.scenario")` should generate scenarios
