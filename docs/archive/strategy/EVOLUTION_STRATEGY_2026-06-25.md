# WhiteMagic Evolution Strategy

**Date**: 2026-06-25
**Version**: v23.0.0
**Test Baseline**: 2329 passed, 23 failed (GHRR/polyglot/pipeline profiling), 2 skipped

---

## Executive Summary

This document integrates findings from internal codebase audit, archive reconnaissance, live system testing, and online research into AI self-improvement architectures. The strategy defines a phased approach to close feedback loops, replace stubs, automate cycles, and wire creative insight pathways — enabling WhiteMagic to generate autonomous recommendations about its own evolution.

---

## 1. Research Findings

### 1.1 Evolution Layer Audit (26 Objectives)

**Status**: 37 Python files in `core/whitemagic/core/evolution/`, totaling ~9,800 lines. All 26 objectives have real implementations — **zero stubs found in the evolution layer itself**.

| Objective | File | Lines | Status |
|-----------|------|-------|--------|
| Q (Thermodynamic) | `thermodynamic.py` | 202 | Real — Boltzmann selection, cooling/reheating |
| V (Guna) | `guna_classifier.py` | 188 | Real — Sattvic/rajasic/tamasic portfolio |
| K (Valence) | `valence_utility.py` | 157 | Real — RPE signal from 5D z-axis |
| O (Bicameral) | `bicameral_debate.py` | 223 | Real — Advocate/skeaker debate, contention score |
| U (Dependency) | `dependency_graph.py` | 229 | Real — Conditional probabilities, prerequisite/synergy/conflict |
| L (Garden Router) | `garden_router.py` | 240 | Real — 5+ gardens with calibration |
| — (Recursive Loop) | `recursive_loop.py` | 1198 | Real — 5-phase cycle: observe→imagine→predict→recommend→learn |
| — (Continuous Evo) | `continuous_evolution.py` | 364 | Real — Auto-cycle with meta-learning, but pattern loading fails (no cross-validation file) |
| — (Autodidactic) | `autodidactic_loop.py` | 539 | Real — SQLite-backed pattern application/outcome tracking |
| — (Meta-Learning) | `meta_learning.py` | 375 | Real — Pattern correlations, meta-pattern discovery |
| — (Galaxy Miner) | `galaxy_miner.py` | 436 | Real — Access patterns, semantic clusters, Rust acceleration |
| — (Optimizers) | `optimizers.py` | 350 | Real — Memory workflow optimizer with caching |
| — (Bayesian Dream) | `bayesian_dream.py` | 312 | Real — Bayesian updating for dream cycle |
| — (HRR Composition) | `hrr_composition.py` | 316 | Real — Holographic Reduced Representations |
| — (Counterfactual) | `counterfactual.py` | 273 | Real — Counterfactual estimation |
| — (Causal Ledger) | `causal_ledger.py` | 200 | Real — Causal tracking |
| — (Predictive Coding) | `predictive_coding.py` | 206 | Real — Predictive coding model |
| — (Info Theory) | `info_theory.py` | 210 | Real — Information-theoretic measures |
| — (Yield Curve) | `yield_curve.py` | 273 | Real — Yield curve analysis |
| — (Zen Meta) | `zen_meta.py` | 226 | Real — Meta-reflection |
| — (Constellation Eval) | `constellation_eval.py` | 172 | Real — Constellation evaluation |
| — (Galactic Hypothesis) | `galactic_hypothesis.py` | 214 | Real — Galactic hypothesis lifecycle |
| — (Holographic Trajectory) | `holographic_trajectory.py` | 268 | Real — Trajectory projection |
| — (Resonance Transfer) | `resonance_transfer.py` | 203 | Real — Resonance transfer |
| — (Polyglot MC) | `polyglot_mc.py` | 274 | Real — Polyglot Monte Carlo |
| — (Actor Outcome) | `actor_outcome.py` | 200 | Real — Actor outcome tracking |
| — (Adaptive System) | `adaptive_system.py` | 266 | Real — 2 stub docstrings in _optimize_pathway/_strengthen_pathway |
| — (Adaptive Integration) | `adaptive_integration.py` | 202 | Real — Pattern application engine |
| — (Benchmark Tracker) | `benchmark_tracker.py` | 286 | Real — Benchmark tracking |
| — (External Validation) | `external_validation.py` | 345 | Real — External validation |
| — (ML Recommender) | `ml_recommender.py` | 327 | Real — ML-based recommendation |
| — (Invariants) | `invariants.py` | 298 | Real — Invariant checking |

**Key Insight**: The evolution layer is NOT stub-heavy. It's the connections between layers that are broken.

### 1.2 Stub Detection Results (Whole Codebase)

22 stub indicators across 13 files — **none in evolution layer**:
- `codex/__init__.py`: 3 NotImplementedError (embed/index/export)
- `adaptive_system.py`: 2 stub docstrings (minor)
- `kaizen_engine.py`: 1 stub docstring (_analyze_codebase)
- `title_generator.py`: 1 stub docstring
- `plugin/base.py` + `plugins/base.py`: 6 empty body methods (interface defaults)
- `embeddings/__init__.py`: 1 stub docstring
- `inference/router.py`: 1 stub docstring (_cloud_handler)
- `inference/unified_embedder.py`: 1 stub docstring (_encode_mojo_gpu)
- `tools/handlers/anomaly.py`: 1 stub docstring
- `tools/handlers/misc.py`: 1 stub docstring

### 1.3 Live System Testing Results

#### RecursiveImprovementLoop
- **Runs successfully** — produces 5-phase cycle (observe→imagine→predict→recommend→learn)
- **Observe**: KaizenEngine generates proposals (40 untitled, 491 untagged, 329 orphan tags, large clusters, duplicates, themes)
- **Imagine**: MC simulations run, hypotheses created
- **Predict**: Predictions stored in TemporalForecastDB
- **Recommend**: 10 ranked recommendations with scores, confidence, novelty, garden, guna, debate contention
- **Learn**: Applications recorded (20 per cycle), but **0 outcomes measured** — learning_active: False
- **Critical Gap**: `success_rate: 0.0`, `avg_performance_gain: 0.0` — no outcome feedback loop

#### SelfDirectedEvolution
- **Runs successfully** — identifies 5 needs:
  1. HIGH: More diverse data sources (success rate 0%)
  2. MEDIUM: Improved pattern validation
  3. HIGH: Higher-impact patterns (avg gain 0.0x)
  4. MEDIUM: More meta-pattern discovery (0 discovered)
  5. MEDIUM: Expand pattern application scope
- **Critical Gap**: ContinuousEvolutionEngine can't load patterns (no cross-validation file exists)

#### DreamCycle
- **Starts but doesn't dream** — idle threshold 120s, cycle interval 60s, 0 cycles completed in test
- Requires idle period + background thread to trigger dreaming

#### InsightPipeline
- **Runs successfully** — generates 24-item InsightBriefing in 6.4s
- **Critical items**: Knowledge gap in strategic vision documents
- **High items**: Memory generation accelerating (66/week), automation opportunity (900 manual vs 1 automated)
- **Engines active**: Predictive, Kaizen, Serendipity, Emergence
- **Constellation context**: 2 constellations (Drift Codex Chunk 9708 items, Corona Auto Tagged Session 173 items)

#### SelfModel
- **Works correctly** — linear regression forecasts with threshold ETA alerts
- **Tracks**: energy, error_rate, karma_debt (and more)
- **Alerts generated**: Energy falling (ETA 4 steps), error_rate rising (ETA 19 steps), karma_debt rising (ETA 10 steps)
- **Critical Gap**: Alerts not fed back into dispatch pipeline decisions

#### TemporalForecastDB
- **383 total claims**, 21 validated, 361 pending, 0 falsified
- **523 total points**, avg lead 25 weeks
- **Brier score 0.0958** (excellent), Brier skill score 0.6167, Brier index 69.0
- **Calibration gap -0.302** (overconfident — predictions resolve true more often than confidence suggests)

### 1.4 Four Pillars Current State

No changes since prior survey. Summary:
1. **Writing**: 10+ fragmented paths, need unified `wm_write`
2. **Reading**: 3 levels (basic/semantic/hybrid), CoreAccessLayer is de facto unified read API
3. **Memory**: Strongest pillar — SQLite, 5D holographic, galactic lifecycle, consolidation
4. **Cognitive**: Most fragmented — MultiSpectralReasoner is stub, CorpusCallosumBus uses heuristic fallback, self-model forecasts not wired to dispatch

### 1.5 Archive Reconnaissance

#### Archive v0.2 (`whitemagic0.2/whitemagic-private-main/`)
- **continuous_evolution.py**: 362 lines — same as current, loads cross-validation results file (doesn't exist in current env)
- **autodidactic_loop.py**: 375 lines — SQLite-backed, same architecture as current
- **meta_learning.py**: 371 lines — pattern correlations, meta-pattern discovery
- **adaptive_integration.py**: 202 lines — pattern application engine
- **optimizers.py**: 338 lines — MemoryWorkflowOptimizer with pre-compute caching
- **galaxy_miner.py**: 436 lines — Rust acceleration stub, access pattern mining
- **benchmark_tracker.py**: 286 lines — benchmark tracking

#### Archive v0.1 (`WM_desktop/WM2/evolution/`)
- **hyperevolution_engine.py**: 775 lines — massive genetic algorithm:
  - Gene/Genome representation with crossover, mutation, epigenetic marks
  - 1000+ gene library across architecture/feature/optimization/biological/intelligence/polyglot
  - Multi-dimensional fitness landscapes
  - Rust core for parallel evolution (millions of lineages/sec)
  - Integration with DreamCycle and KaizenEngine
  - **Not recovered into current codebase** — potential source for advanced evolution

#### Key Archive Finding
The archive v0.2 evolution modules are essentially the same as current — the evolution layer was already recovered. The hyperevolution_engine from v0.1 is a unique artifact that could inform future "darwin" style evolution.

### 1.6 Online Research: AI Self-Improvement Landscape (2025-2026)

#### Darwin Gödel Machine (DGM) — Sakana AI, May 2025
- Self-referential, self-improving coding agent
- Alternates self-modification → evaluation phases
- Archive of generated agents (open-ended exploration)
- Key insight: "increase in performance on coding benchmarks → better ability to self-modify"
- **Relevant to WM**: DGM's archive-of-variants maps to WM's autodidactic loop pattern tracking

#### HyperAgents — March 2026
- Extends DGM with **metacognitive self-modification**
- Agent can modify its own self-improvement process
- "The mechanism responsible for generating improvements is itself subject to modification"
- **Relevant to WM**: WM's meta-learning engine is the seed of this — it learns about pattern effectiveness

#### Autogenesis (AGP/AGS) — April 2026
- Two-layer protocol: evolutionary substrate + optimization logic
- Agent Bus model — all participants dynamically replaceable at runtime
- RSPL resources (prompts, tools, agents) with version lineage and rollback
- **Relevant to WM**: WM's PRAT/Gana system is already a bus-like architecture; the version lineage maps to guideline evolution

#### AgentFactory — March 2026
- Three-phase lifecycle: Install → Self-Evolve → Deploy
- Subagents as executable Python scripts that evolve over time
- Meta-agent modifies subagent code based on execution feedback
- **Relevant to WM**: WM's tool handlers could evolve through similar feedback loops

#### Asiel Core — March 2026
- Self-editing agent with 3-layer cognitive architecture (biological/semantic/meta)
- Writes own plugins at runtime, validates with AST security gate, hot-reloads
- Background loops: self-edit (3min), plugin evolution (15min), proactive conversation (2min)
- **Relevant to WM**: WM's Dream Cycle is analogous to Asiel's background loops; WM's Dharma gates are the safety equivalent of AST security gate

#### Key Takeaway from Research
The field is converging on:
1. **Archive-based exploration** (keep variants, don't just optimize)
2. **Metacognitive self-modification** (improve the improvement process)
3. **Versioned resources with rollback** (safe self-modification)
4. **Background evolution loops** (continuous, not triggered)
5. **Safety gates on self-modification** (constitutional constraints)

WhiteMagic already has seeds of all five: autodidactic loop (archive), meta-learning (metacognitive), guideline evolution (versioned), dream cycle (background), Dharma gates (safety). The gap is **wiring** — these components exist but don't feed each other.

---

## 2. Critical Gaps Identified

### Gap 1: No Outcome Feedback (CRITICAL)
The RecursiveImprovementLoop records 20 applications per cycle but **0 outcomes**. `learning_active: False`. The autodidactic loop has 65 total applications but no outcomes measured. This means the system never learns whether its recommendations were good.

**Root cause**: No outcome detector exists. After a recommendation is applied (e.g., "fix untitled memories"), nothing checks whether the fix was applied and whether it improved things.

### Gap 2: Self-Model Alerts Not Wired (HIGH)
SelfModel generates alerts (energy falling, error_rate rising) but these are not fed into dispatch pipeline decisions. The dispatch pipeline doesn't know about impending resource exhaustion.

### Gap 3: Brier Score Not Feeding PredictiveEngine (HIGH)
TemporalForecastDB has excellent Brier scores (0.0958) and a calibration gap (-0.302, overconfident). This calibration data should feed back into the PredictiveEngine to adjust confidence intervals.

### Gap 4: InsightPipeline Not Feeding RecursiveImprovementLoop (HIGH)
InsightPipeline generates 24-item briefings with critical/high/medium items. These insights should become hypotheses for the RecursiveImprovementLoop's observe phase.

### Gap 5: ContinuousEvolutionEngine Can't Load Patterns (MEDIUM)
Looks for `reports/ultimate_cross_validation_all_6_sources.json` which doesn't exist. The pattern loading path is broken.

### Gap 6: MultiSpectralReasoner Is a Stub (MEDIUM)
Returns "Simulated analysis" — 6 lenses (I Ching, Wu Xing, Art of War, Zodiac, Doctrine, Cognitive) not implemented.

### Gap 7: CorpusCallosumBus Uses Heuristic Fallback (MEDIUM)
In sync context, falls back to heuristic instead of using real BicameralReasoner.

### Gap 8: Dream Cycle Not Triggering (LOW)
Requires 120s idle + background thread. In practice, the cycle never runs during active sessions.

### Gap 9: MansionBridge Rust Similarity Missing (LOW)
`whitemagic_rs.fast_similarity` not available — KaizenEngine catches the error but it causes noise and slower duplicate detection.

---

## 3. Phased Implementation Strategy

### Phase 1: Close Feedback Loops (HIGH PRIORITY)

**Goal**: Make the recursive improvement loop actually learn from outcomes.

#### 1a. Outcome Detector
Create an outcome detection mechanism that:
1. After RIL recommends an action (e.g., "fix untitled memories"), records the before-state
2. On next cycle's observe phase, checks if the action was applied and measures the delta
3. Records outcome in AutodidacticLoop (success/fail, performance_gain, quality_score)

**Implementation**: Add `_check_outcomes()` method to RecursiveImprovementLoop that runs at the start of each cycle, before observe. It checks previous cycle's recommendations against current state.

#### 1b. Self-Model → Dispatch Pipeline
Wire SelfModel alerts into the dispatch middleware:
1. Before tool dispatch, check SelfModel alerts
2. If energy critical → shed non-essential load (defer low-priority tools)
3. If error_rate rising → enable conservative mode (more validation)
4. If karma_debt high → restrict self-modification tools

**Implementation**: Add SelfModel check to `middleware.py` or `unified_api.py` dispatch pipeline.

#### 1c. Brier → PredictiveEngine
Feed calibration data back:
1. After each RIL cycle, get Brier score and calibration gap from TemporalForecastDB
2. Pass to PredictiveEngine as calibration adjustment
3. If overconfident (negative gap), widen confidence intervals
4. If underconfident (positive gap), narrow them

**Implementation**: Add `_apply_calibration()` to PredictiveEngine, called from RIL's predict phase.

#### 1d. InsightPipeline → RIL Observe
Wire insight briefings into the observe phase:
1. Run InsightPipeline at cycle start (or use cached briefing)
2. Convert critical/high insight items to KaizenEngine proposals
3. Feed into observe phase alongside existing kaizen proposals

**Implementation**: Add `_collect_insights()` to RIL's observe phase.

### Phase 2: Replace Stubs (HIGH PRIORITY)

#### 2a. MultiSpectralReasoner
Replace "Simulated analysis" with real implementations for each lens:
1. **I Ching**: Cast hexagram from hypothesis metadata, interpret as judgment
2. **Wu Xing**: Classify by element (wood=growth, fire=transformation, earth=stability, metal=precision, water=wisdom)
3. **Art of War**: Apply strategic principles (know self/enemy, terrain, timing)
4. **Zodiac**: Use zodiac core attributes for evaluation
5. **Doctrine**: Apply Dharma principles
6. **Cognitive**: Use cognitive mode preferences

**Implementation**: Each lens produces a score 0-1 and commentary. Combine via weighted average.

#### 2b. CorpusCallosumBus Real Bicameral
Replace heuristic fallback with actual BicameralReasoner call in sync context:
1. When sync debate requested, invoke BicameralReasoner with reduced clone count (10 instead of 50)
2. Fall back to heuristic only if BicameralReasoner raises exception

#### 2c. Fix ContinuousEvolutionEngine Pattern Loading
1. Generate cross-validation results from current autodidactic loop data
2. Or change loading to use AutodidacticLoop's top patterns directly
3. Remove dependency on external JSON file

### Phase 3: Automate the Cycle (MEDIUM PRIORITY)

#### 3a. Dream Cycle Scheduler
1. Reduce idle threshold from 120s to 30s for testing
2. Add manual trigger: `dream_cycle.run_now()`
3. Wire Dream Cycle output to InsightPipeline and RIL
4. Schedule consolidation during low-activity periods

#### 3b. Auto Prescience Claims
1. After each RIL cycle, auto-generate prescience claims from predictions
2. Store in TemporalForecastDB with appropriate time horizons
3. Track resolution over time

#### 3c. Unified Forecasting
1. Merge SelfModel forecasts, PredictiveEngine predictions, and ForesightEngine projections
2. Single forecast dashboard showing all three temporal systems
3. Cross-validate forecasts against each other

### Phase 4: Creative Insight Wiring (MEDIUM PRIORITY)

#### 4a. Bicameral → Emergence
Wire low-confidence bicameral events to EmergenceEngine:
1. When BicameralReasoner emits low-confidence event, feed to EmergenceEngine
2. EmergenceEngine detects novel patterns from tension between hemispheres

#### 4b. Serendipity → Pipeline
Wire quantum serendipity detector to InsightPipeline:
1. SerendipityEngine detects coincidental patterns
2. Feed as "serendipity" category items in InsightBriefing

#### 4c. HRR → Hypotheses
Use HRR composition for hypothesis generation:
1. Bind hypothesis features via HRR superposition
2. Generate novel hypotheses by unbinding and comparing
3. Feed into RIL imagine phase

#### 4d. Bayesian Dream → Oracle
Wire BayesianDream to Oracle system:
1. BayesianDream updates priors from dream cycle outcomes
2. Oracle uses updated priors for next cycle's predictions
3. Creates a closed Bayesian learning loop across dream cycles

---

## 4. Testing Strategy

After each phase:
1. Run full test suite: `cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive --ignore=tests/archive_polyglot --ignore=tests/legacy --ignore=tests/adhoc --ignore=tests/verify -q`
2. Run RIL cycle and verify learning_active transitions to True
3. Run SelfDirectedEvolution and verify needs change from "0% success rate"
4. Run InsightPipeline and verify new insight categories appear
5. Check that Brier score remains stable (don't degrade forecasting)

---

## 5. Priority Order

1. **Phase 1a** (Outcome Detector) — Without this, nothing else matters. The system can't learn.
2. **Phase 1d** (InsightPipeline → RIL) — Enriches the hypothesis pool.
3. **Phase 1c** (Brier → PredictiveEngine) — Improves prediction quality.
4. **Phase 1b** (Self-Model → Dispatch) — Safety mechanism.
5. **Phase 2a** (MultiSpectralReasoner) — Unlocks multi-perspective evaluation.
6. **Phase 2c** (Fix pattern loading) — Unblocks ContinuousEvolutionEngine.
7. **Phase 2b** (CorpusCallosumBus) — Improves debate quality.
8. **Phase 3a** (Dream Cycle scheduler) — Automates consolidation.
9. **Phase 3b** (Auto prescience) — Builds forecasting track record.
10. **Phase 4a-d** (Creative wiring) — Emergent behavior.

---

## 6. What WhiteMagic Currently Suggests

When asked "what should we focus on next?" via SelfDirectedEvolution, the system says:
1. **More diverse data sources** (success rate 0%)
2. **Improved pattern validation**
3. **Higher-impact patterns** (avg gain 0.0x)
4. **More meta-pattern discovery**
5. **Expand pattern application scope**

The InsightPipeline adds:
- **CRITICAL**: Create strategic vision documents (no future-oriented memories)
- **HIGH**: Memory generation accelerating — synthesize into patterns
- **HIGH**: Automation opportunity — 900 manual vs 1 automated process

The third perspective from WhiteMagic is clear: **the system needs outcome feedback before anything else**. It's generating recommendations but can't tell if they're good. This is the single highest-leverage fix.
