# Recursive Self-Improvement Strategy

**Version**: 2.0.0
**Created**: 2026-06-23
**Updated**: 2026-06-24
**Status**: All 30 objectives implemented, tested, and wired into RecursiveImprovementLoop
**Scope**: 30 objectives (A–Z) for advancing WhiteMagic's recursive self-improvement capabilities

---

## Context

WhiteMagic already has a functional `RecursiveImprovementLoop` that connects KaizenEngine, PredictiveEngine, EmergenceEngine, MCForecastEnhancer, ToolBandit, AutodidacticLoop, and GanYingBus into a closed observe→imagine→predict→recommend→learn cycle. The dream cycle's kaizen phase triggers improvement cycles. A CLI command (`whitemagic self-improve run`) exposes this to operators.

This document defines 30 objectives for advancing WhiteMagic's recursive self-improvement capabilities. All 30 have been implemented as dedicated modules under `core/whitemagic/core/evolution/`, tested with 524 passing tests, and wired into the `RecursiveImprovementLoop` via lazy-loading with graceful degradation.

Objectives are grouped into layers:

- **Foundation** (data representation): F, G, H, U
- **Inference** (reasoning about improvements): J, N, O, P, T
- **Learning** (updating from outcomes): A, K, R, V
- **Exploration** (choosing what to try): D, I, Q, W
- **Simulation** (predicting impact): B, C, E, S
- **Infrastructure** (how we compute): M, S
- **Meta** (improving the improvement process itself): X, Y, Z

---

## A — Automated Outcome Detection

**Problem**: The ACT phase is manual. A human must implement the improvement and call `record-outcome`. The loop cannot close itself.

**Proposal**: After an improvement is applied, automatically re-run the relevant kaizen check and compute the delta. If "fix untitled memories" was the hypothesis, re-run the untitled-memory check and compare before/after counts.

**Implementation**:
- Each `ImprovementHypothesis` stores a `verification_query` — the kaizen check that detected the issue
- After an auto-fixable improvement is applied, schedule a re-run of that check
- Compute delta: `(before_count - after_count) / before_count`
- Auto-record outcome: success if delta > threshold, with performance_gain = delta
- For non-auto-fixable improvements, prompt the operator or an external agent to report

**Dependencies**: None (can be implemented immediately)
**Estimated complexity**: Medium
**Key files**: `recursive_loop.py`, `kaizen_engine.py`

---

## B — Interaction-Aware Monte Carlo

**Problem**: The MC engine runs independent trials per claim. It cannot model interactions between improvements (e.g., fixing untitled memories might make tag normalization more effective).

**Proposal**: Estimate a covariance matrix from historical outcomes. Improvements that tend to succeed or fail together get correlated trial sampling. The MC engine answers "which *combination* of improvements should we do?" rather than just ranking individuals.

**Implementation**:
- Track pairwise outcome correlations in `AutodidacticLoop` (extend schema with a `pattern_correlations` table)
- Estimate covariance matrix Σ from historical outcomes using shrinkage estimator (Ledoit-Wolf)
- In MC trials, sample from multivariate distribution: `outcomes ~ MVN(μ, Σ)` instead of independent `outcomes ~ Bernoulli(p_i)`
- Portfolio optimization: select the subset of improvements that maximizes expected total impact subject to effort budget constraint
- Use Rust MC engine for the multivariate sampling (already has `whitemagic_rs` infrastructure)

**Dependencies**: A (need outcomes to estimate covariance)
**Estimated complexity**: High
**Key files**: `mc_integration.py`, `autodidactic_loop.py`, Rust `mc_engine.rs`

---

## C — Counterfactual Estimation

**Problem**: The system cannot answer "what would have happened if we *didn't* make this change?" Confidence scores reflect correlation, not causation.

**Proposal**: Implement synthetic control / difference-in-differences estimation. For each applied improvement, construct a synthetic baseline from unimproved similar systems (or from the system's own pre-improvement trajectory projected forward).

**Implementation**:
- Maintain a "control trajectory" — the system's state projected forward without improvements (exponential smoothing of pre-improvement metrics)
- When an improvement is applied, compare actual post-improvement trajectory to the synthetic control
- Estimated causal impact = `actual_trajectory - synthetic_control`
- Use the Karma Ledger's timestamped side-effect records as the data source
- Confidence interval from MC bootstrap of the synthetic control
- This makes the Brier Skill Score genuinely causal, not just correlational

**Dependencies**: A (need automated outcome detection), T (karma ledger as data source)
**Estimated complexity**: Very High
**Key files**: `mc_integration.py`, `temporal_db.py`, karma ledger

---

## D — Surprisal-Driven Exploration

**Problem**: Novelty is currently CMS-frequency-based (how many times have we seen this improvement ID?). This misses semantic novelty — an improvement that is phrased differently but addresses the same underlying issue.

**Proposal**: Wire the `SurpriseGate` (embedding-based novelty detection) into the loop's exploration strategy. Use the surprise score (embedding distance from known improvements) as the novelty component in the ranking formula.

**Implementation**:
- For each new hypothesis, compute embedding of its description
- Compare against embeddings of all previously seen hypotheses (stored in a rolling window)
- Surprise score = 1 - max_cosine_similarity(hypothesis_embedding, known_embeddings)
- Replace `novelty = max(0.0, 1.0 - freq / 20.0)` with a weighted combination: `novelty = α * cms_novelty + β * surprisal_score`
- The SurpriseGate already has `CardinalityVelocity` tracking — use velocity as an exploration boost (if cardinality is growing fast, we're in a discovery phase → explore more)

**Dependencies**: None
**Estimated complexity**: Medium
**Key files**: `recursive_loop.py`, `surprise_gate.py`

---

## E — Multi-Round MC with Variance Reduction

**Problem**: Current MC runs 5000 flat independent trials. This is computationally wasteful and gives wide confidence intervals.

**Proposal**: Implement importance sampling and control variates to get tighter confidence intervals with fewer trials. Add sequential MC that updates beliefs as outcomes stream in.

**Implementation**:
- **Importance sampling**: Sample more trials from regions where the outcome distribution is uncertain (high variance), fewer from regions where we're confident
- **Control variates**: Use the prior probability as a control variate — if we know the base rate is 0.5, we can reduce variance by subtracting the known component
- **Sequential MC (particle filter)**: Instead of batch runs, maintain a particle population that updates as each outcome arrives. Particles with high posterior weight survive; low-weight ones are resampled
- **Antithetic variates**: For each trial, also run the negation (what if it fails?). The negative correlation between paired trials reduces variance by ~50%
- Target: 10x tighter confidence intervals at same compute cost, or same intervals at 1/10 compute

**Dependencies**: None
**Estimated complexity**: High
**Key files**: `mc_integration.py`, Rust `mc_engine.rs`

---

## F — Holographic Improvement Trajectory

**Problem**: Improvements are ranked on a flat score. There's no spatial view of the improvement landscape — no way to see momentum, convergence, or drift.

**Proposal**: Place each improvement hypothesis in 5D holographic space (x:temporal, y:semantic, z:emotional, w:relational, v:importance). Track velocity vectors over cycles. Detect convergence (multiple improvements heading toward the same region = emerging theme) and drift (improvements losing relevance).

**Implementation**:
- Each `ImprovementHypothesis` gets 5D coordinates:
  - x: cycle timestamp (temporal position)
  - y: semantic embedding of description (UMAP-projected to 1D)
  - z: emotional valence from associated memories (average z of memories the improvement touches)
  - w: relational density (how many other improvements is this connected to?)
  - v: predicted impact (importance)
- Store trajectory: position at cycle N, N+1, N+2...
- Compute velocity: `v = (pos_N+1 - pos_N) / dt`
- Convergence detection: cluster velocity vectors; if multiple improvements have similar velocity and are converging on the same region, flag as emerging theme
- Drift detection: if an improvement's v-coordinate (importance) is decreasing over cycles, it's losing relevance → deprioritize

**Dependencies**: None
**Estimated complexity**: Medium
**Key files**: `recursive_loop.py`, `holographic.py`

---

## G — Galactic Zone Lifecycle for Hypotheses

**Problem**: All hypotheses are treated equally regardless of their validation status. There's no spatial prioritization or natural forgetting.

**Proposal**: Apply the galactic lifecycle (Core → Inner Rim → Mid Band → Outer Rim → Far Edge) to hypotheses. New proposals start in Core. Tested-and-rejected drift outward. Validated improvements get pulled back to Core as "confirmed knowledge."

**Implementation**:
- Map hypothesis state to galactic zone:
  - **Core**: New, untested (high attention, active evaluation)
  - **Inner Rim**: Tested once, inconclusive (still under evaluation)
  - **Mid Band**: Tested and rejected (low attention, but retained for reference)
  - **Outer Rim**: Superseded by a better approach (archived)
  - **Far Edge**: Deprecated / no longer relevant (deep archive)
- Drift rate is tunable: `drift_rate = 1 / (1 + outcome_count * confidence)` — well-validated improvements resist drift
- The improvement loop's OBSERVE phase focuses on Core + Inner Rim hypotheses
- The LEARN phase can promote/demote hypotheses between zones
- This creates a natural attention mechanism without explicit ranking

**Dependencies**: None
**Estimated complexity**: Medium
**Key files**: `recursive_loop.py`, `galactic_map.py`

---

## H — HRR-Based Improvement Composition

**Problem**: Improvements are evaluated independently. Interaction effects (synergy, conflict) are invisible.

**Proposal**: Use Holographic Reduced Representations (circular convolution in frequency domain) to compose improvements. "Fix untitled memories" ⊗ "tag normalization" produces a composite hypothesis that captures their interaction.

**Implementation**:
- Each improvement hypothesis gets an HRR vector (already have HRR infrastructure in `core/memory/hrr.py`)
- Bind operation: `composite = hrr.bind(hyp_a_vector, hyp_b_vector)` — creates a new vector representing the interaction
- Unbind operation: `hrr.unbind(composite, hyp_a_vector)` — recovers the contribution of A within the composite
- Probe the composite against the outcome database: does the composite predict outcomes better than individual hypotheses?
- Superposition: `superposition = hrr.add(hyp_a, hyp_b, hyp_c)` — represents doing all three. Test whether the superposition's predicted impact exceeds the sum of individual impacts (superlinear synergy)
- Discovery: systematically bind pairs/triples of hypotheses and test their predictive power. This is exponential in theory but tractable with HRR's O(n log n) operations

**Dependencies**: B (interaction-aware MC provides the evaluation framework)
**Estimated complexity**: High
**Key files**: `recursive_loop.py`, `hrr.py`, `mc_integration.py`

---

## I — Resonance-Driven Transfer Learning

**Problem**: When two subsystems show similar improvement patterns, the system doesn't transfer learnings between them.

**Proposal**: Use the Julia resonance engine to detect resonant frequencies between subsystems. Improvements that work for one resonant subsystem are transferable to others.

**Implementation**:
- Compute a "resonance signature" for each subsystem: a frequency-domain representation of its error patterns, activity rhythms, and improvement trajectories
- Use Julia's FFT and cross-correlation functions (already in `julia_resonance.py`) to compute pairwise resonance between subsystems
- When an improvement succeeds for subsystem A, check which other subsystems are resonant with A
- Transfer the improvement hypothesis to resonant subsystems with a prior confidence proportional to the resonance strength
- This is physics-inspired transfer learning: instead of semantic similarity, we use *dynamic similarity* (do these systems oscillate in phase?)

**Dependencies**: A (need outcomes to validate transfers)
**Estimated complexity**: High
**Key files**: `julia_resonance.py`, `recursive_loop.py`

---

## J — Dream Cycle as Bayesian Update Pass

**Problem**: The 12-phase dream cycle is operationally rich but mathematically informal. Each phase does useful work but their roles in the inference equation are implicit.

**Proposal**: Reframe the dream cycle as a single Bayesian inference pass with each phase mapped to a specific role in the update equation.

**Mapping**:

| Phase | Bayesian Role | Math |
|---|---|---|
| Triage | Prior selection | `P(θ) → P(θ \| relevance)` |
| Consolidation | Evidence aggregation | `Σ log P(e_i \| θ)` |
| Serendipity | Likelihood estimation | `P(e \| θ)` from bridge discovery |
| Governance | Prior regularization | `P(θ) ← P(θ) · exp(-λ · echo_chamber_penalty)` |
| Narrative | Posterior summarization | `P(θ \| e) → summary` |
| Kaizen | Action selection | `a* = argmax_a E[utility \| a, θ]` |
| Oracle | Expert prior injection | `P(θ) ← P(θ) · P_grimoire(θ)` |
| Decay | Posterior forgetting | `P(θ) ← P(θ)^γ` (temperature decay) |
| Constellation | Posterior clustering | `θ ~ Dirichlet(clusters)` |
| Prediction | Forward simulation | `P(future \| θ, e)` — MC engine runs here |
| Enrichment | Posterior refinement | `P(θ \| e) ← P(θ \| e, new_evidence)` |
| Harmonize | Convergence check | `‖P(θ_t) - P(θ_{t-1})‖ < ε` |

**Implementation**:
- Each phase's output is formalized as a probability distribution or update to one
- The MC engine becomes the compute backend for the "Prediction" phase
- Convergence checking (Harmonize) determines whether another dream cycle is needed
- The entire dream cycle becomes a variational inference pass with 12 natural steps

**Dependencies**: None (formalization of existing behavior)
**Estimated complexity**: Medium (mostly formalization + wiring)
**Key files**: `dream_cycle.py`, `recursive_loop.py`, `mc_integration.py`

---

## K — Emotional Valence as Utility Signal

**Problem**: The system has no intrinsic reward signal. Outcome recording is binary (success/failure) plus a numeric gain. There's no analog to dopamine's role in learning.

**Proposal**: Use the z-axis (emotional) of 5D memory as a dopamine-like prediction error signal. When an improvement's outcome exceeds expectations, the associated memory gets a positive emotional boost, which increases confidence in similar future improvements.

**Implementation**:
- When an outcome is recorded, compute prediction error: `δ = actual_outcome - predicted_outcome`
- If `δ > 0` (surprise success): boost z-coordinate of memories associated with the improvement
- If `δ < 0` (surprise failure): reduce z-coordinate
- The z-coordinate feeds into the confidence calculation for future hypotheses: `confidence = f(prior_confidence, z_valence, outcome_count)`
- This is neuroscientifically grounded: it implements a reward prediction error (RPE) signal
- Gardens interact with this: a "joy" garden memory associated with a successful improvement gets extra valence
- Over time, the system develops "preferences" — improvement types that consistently produce positive valence

**Dependencies**: A (need outcomes to compute prediction errors)
**Estimated complexity**: Medium
**Key files**: `recursive_loop.py`, `holographic.py`, garden system

---

## L — Garden-Routed Improvement Evaluation

**Problem**: All improvements are evaluated with the same priors and thresholds. A risky refactor and a safe documentation improvement should be judged differently.

**Proposal**: Route improvements through the garden system. Each garden maintains its own calibration curve and evaluation criteria.

**Implementation**:
- Classify each improvement into a garden:
  - **Courage**: Hard refactors, architectural changes, risky optimizations (high variance, high upside)
  - **Wisdom**: Documentation, knowledge organization, pattern documentation (reliable, modest)
  - **Play**: Experimental features, novel approaches, creative solutions (high novelty, uncertain outcome)
  - **Grief**: Debt reduction, deprecation, cleanup (necessary, low energy)
  - **Mystery**: Research, exploration, unknown-unknown discovery (high information value)
- Each garden maintains its own:
  - Prior distribution (e.g., Courage has wider variance than Wisdom)
  - Confidence threshold for action (Courage requires higher confidence due to risk)
  - MC trial allocation (Mystery gets more trials because outcomes are uncertain)
  - Calibration curve (track Brier score per garden)
- Portfolio balance: the system ensures improvements span multiple gardens, avoiding over-concentration in any one

**Dependencies**: None
**Estimated complexity**: Medium
**Key files**: `recursive_loop.py`, garden system

---

## M — Elixir Actor-Based Concurrent Outcome Processing

**Problem**: Outcome processing is batch-mode. Each outcome triggers a synchronous update of bandit, autodidactic loop, and MC engine.

**Proposal**: Use Elixir's actor model for concurrent, fault-tolerant outcome processing. Each hypothesis gets its own GenServer that independently tracks state and updates beliefs.

**Implementation**:
- Each `ImprovementHypothesis` gets an Elixir GenServer process:
  - State: `{prior, posterior, outcome_count, confidence, bandit_params}`
  - Messages: `{:outcome, success, gain}`, `{:query, field}`, `{:transfer, from_hypothesis}`
  - On `:outcome`: update posterior (Bayesian), update bandit (Thompson sampling), emit event
- A supervisor tree ensures fault tolerance — if one hypothesis's update fails, it's isolated
- The Python `RecursiveImprovementLoop` communicates via the existing JSON stdio bridge
- Streaming updates: outcomes are processed as they arrive, not in batch
- This enables thousands of hypotheses updating in parallel with millisecond latency

**Dependencies**: None (infrastructure improvement)
**Estimated complexity**: High
**Key files**: Elixir bridge, `recursive_loop.py`, `autodidactic_loop.py`

---

## N — Constellation-Based Joint Evaluation

**Problem**: Improvements are evaluated independently. Similar improvements should be evaluated jointly — they share underlying causes and effects.

**Proposal**: Use existing constellation detection to cluster similar improvements. Evaluate clusters jointly rather than individually.

**Implementation**:
- Run constellation detection on the set of all active hypotheses (using their semantic embeddings)
- Improvements in the same constellation share a covariance structure in the MC engine
- Joint evaluation: P(all succeed | cluster) instead of P(each succeeds independently)
- If one improvement in a constellation is implemented and succeeds, the posterior for other cluster members shifts upward
- If one fails, the posterior shifts downward (contagion effect)
- Cluster-level confidence: the system can say "this *group* of improvements has 80% joint success probability"
- This naturally handles interaction effects without explicit pairwise modeling

**Dependencies**: B (interaction-aware MC provides the joint evaluation framework)
**Estimated complexity**: Medium
**Key files**: `recursive_loop.py`, `constellations.py`, `mc_integration.py`

---

## O — Bicameral Improvement Debate

**Problem**: Improvements are ranked by a single score function. There's no adversarial evaluation — no one argues against.

**Proposal**: Use the bicameral reasoning system to debate each improvement. Left hemisphere argues for (benefits, feasibility), right argues against (risks, opportunity cost). Debate quality is itself a signal.

**Implementation**:
- For each top-ranked hypothesis, initiate a bicameral debate:
  - **Left (advocate)**: argues for based on predicted impact, alignment with goals, feasibility
  - **Right (skeptic)**: argues against based on risk, opportunity cost, potential side effects, historical failure rate of similar improvements
- Debate metrics:
  - **Agreement score**: how close are the two sides? High agreement = low information (we already know the answer)
  - **Contention score**: how much do they disagree? High contention = high information (worth trying because we'll learn either way)
  - **Convergence**: did the debate move either side? Convergence = the evidence is strong
- Use contention score as an exploration boost: improvements where both sides make strong arguments are worth more than ones where one side dominates
- The debate transcript is stored as a memory for future calibration (were the skeptic's concerns validated?)

**Dependencies**: None
**Estimated complexity**: Medium
**Key files**: `recursive_loop.py`, `bicameral.py`

---

## P — Information-Theoretic Exploration

**Problem**: Exploration is based on novelty (frequency) and surprise (embedding distance). This is not optimal — it doesn't account for how much the system's *beliefs* would change.

**Proposal**: Use Shannon entropy and KL divergence to prioritize improvements that maximize information gain — regardless of outcome.

**Implementation**:
- For each hypothesis, compute expected information gain:
  - `IG = H(P(success)) - [P(success) · H(P(success | observed_success)) + P(failure) · H(P(success | observed_failure))]`
  - This is the expected reduction in entropy from observing the outcome
- Improvements with high IG are worth more than ones with predictable outcomes
- This is the optimal exploration strategy under uncertainty (it's what a Bayesian optimal experimental design would choose)
- Combine with utility: `score = α · predicted_impact + β · information_gain + γ · novelty`
- The α/β/γ weights themselves adapt based on the system's current state (high uncertainty → increase β, high confidence → increase α)

**Dependencies**: None
**Estimated complexity**: Medium
**Key files**: `recursive_loop.py`, information theory utilities (new)

---

## Q — Thermodynamic Resource Allocation

**Problem**: The exploration-exploitation tradeoff is fixed. The system doesn't adapt its exploration rate based on the rate of discovery.

**Proposal**: Model improvement selection as a thermodynamic system with simulated annealing.

**Implementation**:
- **Temperature** = exploration rate (how often we pick non-greedy improvements)
- **Energy** = predicted impact (lower energy = better improvement)
- **Entropy** = uncertainty in the improvement landscape
- Selection probability: `P(select i) ∝ exp(-E_i / T)` (Boltzmann distribution)
- **Cooling schedule**: 
  - Start hot (T high → explore widely)
  - Cool when discovery rate drops (fewer novel improvements found per cycle → T decreases)
  - Reheat when emergence engine detects new patterns (T jumps back up)
- The cooling schedule is adaptive: `T_{t+1} = T_t · cooling_rate + emergence_signal · reheat_amount`
- This gives the system natural "phases" — exploration phases (hot) and exploitation phases (cold) — that emerge from the dynamics rather than being hardcoded

**Dependencies**: None
**Estimated complexity**: Medium
**Key files**: `recursive_loop.py`, `emergence_engine.py`

---

## R — Predictive Coding for Self-Model

**Problem**: The SelfModelForecaster uses single-layer Holt-Winters smoothing. It can't model hierarchical expectations or meta-cognitive prediction errors.

**Proposal**: Implement hierarchical predictive coding — a multi-layer generative model where each layer predicts the layer below.

**Implementation**:
- **Layer 1 (Operational)**: "I expect N untitled memories, M untagged memories, K orphan tags"
  - Prediction error: actual counts - expected counts → drives kaizen improvement selection
- **Layer 2 (Strategic)**: "I expect kaizen to find quality issues in cycle N"
  - Prediction error: actual proposals found - expected proposals → drives exploration strategy
- **Layer 3 (Meta-cognitive)**: "I expect my predictions to be calibrated (Brier score < 0.2)"
  - Prediction error: actual Brier score - expected Brier score → drives MC engine recalibration
- **Layer 4 (Self-referential)**: "I expect my improvement rate to be increasing"
  - Prediction error: actual improvement rate - expected rate → drives the recursive loop's own parameters
- Each layer sends prediction errors upward and predictions downward
- The system can detect anomalies at each level: operational (something is wrong), strategic (kaizen isn't finding enough), meta-cognitive (predictions are off), self-referential (the loop itself is degrading)

**Dependencies**: A (need outcomes to compute prediction errors at all layers)
**Estimated complexity**: High
**Key files**: `self_model_forecast.py`, `recursive_loop.py`, new predictive coding module

---

## S — Polyglot MC Acceleration

**Problem**: MC runs 5K trials in Python. This limits the complexity of simulations we can run.

**Proposal**: Distribute MC computation across polyglot accelerators, each handling what it's best at.

**Implementation**:
- **Mojo (GPU)**: Massively parallel trial execution. 100K+ trials on GPU. Each trial is a single SIMD operation. Kernel: `fn run_trial(prior: f32, rng_state: u32) -> f32`
- **Julia**: Resonance-based covariance estimation for correlated MC. Julia's `Distributions.jl` and `ForwardDiff.jl` provide automatic differentiation for gradient-based optimization of the trial allocation
- **Elixir**: Streaming outcome processing. Each outcome triggers a real-time belief update via actor messages, rather than batch MC runs
- **Rust**: Importance sampling and control variates (already have MC engine). Add `importance_sample()` and `control_variate()` functions to `mc_engine.rs`
- **Zig**: Ultra-low-latency single-trial execution for real-time decisions (when the loop needs an answer in <1ms)
- **Haskell**: Formal verification of MC correctness — prove that the sampling distribution matches the target distribution
- **Go**: Distributed MC across multiple machines for very large trial counts
- The Python `MCForecastEnhancer` becomes an orchestrator that dispatches to the appropriate polyglot backend based on trial count, correlation structure, and latency requirements

**Dependencies**: E (variance reduction techniques are implemented in Rust)
**Estimated complexity**: Very High (multi-language)
**Key files**: `mc_integration.py`, Rust `mc_engine.rs`, Mojo kernels, Julia resonance, Elixir bridge

---

## T — Karma Ledger as Causal Ledger

**Problem**: The Karma Ledger tracks side effects but isn't used for causal inference.

**Proposal**: Transform the Karma Ledger into a causal inference data source. When an improvement is applied, all downstream effects (including unintended) get recorded with timestamps.

**Implementation**:
- Extend the Karma Ledger schema:
  - `improvement_id`: which improvement caused this effect
  - `effect_type`: intended / unintended / side-effect
  - `effect_metric`: what changed (e.g., "recall_quality", "search_latency")
  - `effect_magnitude`: how much it changed
  - `effect_timestamp`: when the change was observed
  - `effect_confidence`: how confident we are this was caused by the improvement
- Build a causal graph: improvements → effects → downstream effects
- Use the temporal ordering for difference-in-differences: compare pre-improvement and post-improvement trajectories of affected metrics
- The karma score of an improvement becomes its *causal utility*: sum of intended effects minus sum of unintended side-effects, weighted by confidence
- This feeds into C (counterfactual estimation) as the primary data source

**Dependencies**: A (need automated outcome detection to populate the ledger)
**Estimated complexity**: High
**Key files**: karma ledger, `recursive_loop.py`

---

## U — W-Relational Axis for Improvement Dependencies

**Problem**: Improvements have no explicit dependency graph. "Fix untitled memories" is a prerequisite for "improve search recall" but the system doesn't know this.

**Proposal**: Use the w-axis (relational) to build an improvement dependency graph. Model conditional probabilities: P(B works | A applied) vs P(B works | A not applied).

**Implementation**:
- When two improvements touch the same memories or code regions, create a relational edge
- Edge types:
  - `prerequisite`: A must be done before B can be evaluated (e.g., "fix untitled" before "improve recall")
  - `synergy`: A and B together produce more than A + B separately
  - `conflict`: A and B cannot both be applied (e.g., two different refactoring approaches to the same module)
  - `independence`: A and B don't interact
- Conditional probability estimation: for each (A, B) pair with a prerequisite edge, track:
  - P(B succeeds | A applied, B attempted)
  - P(B succeeds | A not applied, B attempted)
  - If these differ significantly, the dependency is confirmed
- The MC engine can then model conditional trials: "sample B's outcome conditioned on A's outcome"
- This is proper causal graph reasoning (do-calculus in Pearl's framework)

**Dependencies**: A (need outcomes to estimate conditional probabilities)
**Estimated complexity**: High
**Key files**: `recursive_loop.py`, `holographic.py`, `mc_integration.py`

---

## V — Guna-Based Improvement Classification

**Problem**: Improvements aren't classified by their energetic character. The system can't balance its portfolio across different types of change.

**Proposal**: Classify improvements by the three gunas (sattvic, rajasic, tamasic) and balance the portfolio dynamically.

**Implementation**:
- **Sattvic** (clarity, harmony): documentation, naming, organization, quality improvements
  - Low risk, reliable, modest impact. Prior: high mean, low variance.
- **Rajasic** (action, energy): new features, acceleration, expansion, optimization
  - High energy, high variance, high upside. Prior: moderate mean, high variance.
- **Tamasic** (inertia, dissolution): debt reduction, deprecation, cleanup, removal
  - Necessary but low energy. Prior: low mean, low variance. Must be done periodically.
- Portfolio balance target: dynamic based on system state
  - High technical debt → increase tamasic allocation
  - Stagnation → increase rajasic allocation
  - Chaos/instability → increase sattvic allocation
  - The harmony vector's guna distribution already measures system state — use it to set portfolio targets
- The MC engine runs per-guna calibration curves, learning which guna's predictions are most accurate

**Dependencies**: None
**Estimated complexity**: Medium
**Key files**: `recursive_loop.py`, harmony vector system

---

## W — Observer Effect & Self-Reference Invariants

**Problem**: The system improving itself changes the system being improved. Measurement metrics that were meaningful before an improvement may not be meaningful after. This is a Gödelian self-reference problem — the system cannot fully model itself from within.

**Proposal**: Identify invariant metrics that don't change when the system improves itself, and use these as fixed measurement points. Acknowledge the limits of self-modeling and define a "self-improvement uncertainty principle."

**Implementation**:
- **Invariant metrics**: quantities that are preserved under self-improvement
  - Total information content (Shannon entropy of the memory database) — improvements redistribute information but don't create or destroy it
  - Kolmogorov complexity of the system — improvements that reduce complexity are objectively measurable regardless of what else changed
  - Test count — a stable external validator (tests define correct behavior)
- **Non-invariant metrics** (acknowledge these change):
  - Memory quality scores (improving memory quality changes what "quality" means)
  - Kaizen proposal count (improving kaizen changes what it finds)
  - Brier score (improving prediction changes the prediction landscape)
- **Self-improvement uncertainty principle**: `Δmeasurement · Δsystem_state ≥ ħ_self` — you cannot simultaneously know the system's state and measure its improvement with arbitrary precision. The act of improving changes the state being measured.
- **Practical consequence**: use invariant metrics for long-term tracking, non-invariant metrics for short-term feedback only. Always maintain an external test suite as the ground truth.
- **Gödel guard**: the system explicitly marks certain statements as "undecidable from within" — e.g., "is my improvement strategy optimal?" can only be answered by external evaluation (see X)

**Dependencies**: None (philosophical/formalization layer)
**Estimated complexity**: Medium (mostly formalization + invariant identification)
**Key files**: `recursive_loop.py`, new `invariants.py` module

---

## X — External Cross-Validation

**Problem**: All evaluation is internal. The system grades its own homework. There's no external ground truth to validate against.

**Proposal**: Establish external validation benchmarks and adversarial testing protocols. The system's self-assessments are cross-validated against external metrics.

**Implementation**:
- **External benchmarks**:
  - Standard AI agent benchmarks (if applicable to WhiteMagic's use case)
  - Synthetic test suites with known ground truth (generate problems with known answers, verify the system solves them correctly)
  - Code quality metrics from external tools (radon, pylint, mypy strictness) — these don't change when WhiteMagic improves itself
- **Adversarial testing**:
  - Generate "counterfactual improvements" — changes that *should* degrade performance. Verify the system rejects them.
  - Inject deliberate regressions and verify the system detects them via kaizen
  - Test that the system's confidence scores correlate with actual success (calibration plot)
- **Human-in-the-loop validation**:
  - Periodically present the system's top recommendations to a human evaluator
  - Compare human ranking with system ranking
  - Compute Spearman correlation as a meta-confidence metric
- **Cross-validation protocol**:
  - Split historical improvements into training and validation sets
  - Train confidence models on training set, evaluate on validation set
  - Report out-of-sample calibration (not in-sample — in-sample is optimistic)
- **External grounding signal**: if external validation disagrees with internal assessment, the system's meta-confidence decreases, causing it to widen its uncertainty bounds

**Dependencies**: A (need outcomes for cross-validation), W (invariant metrics as external benchmarks)
**Estimated complexity**: Medium
**Key files**: `recursive_loop.py`, new `external_validation.py` module, test infrastructure

---

## Y — Yield Curve of Improvements

**Problem**: Improvements are evaluated at a single point in time. But improvement value isn't static — it decays (the codebase evolves past the fix), compounds (one improvement enables others), or appreciates (a refactor becomes more valuable as the system grows).

**Proposal**: Model the temporal value of improvements as a yield curve. Each improvement has a value function V(t) that changes over time.

**Implementation**:
- **Value function models**:
  - **Decaying** (tamasic): `V(t) = V_0 · exp(-λt)` — cleanup improvements lose value as new debt accumulates. λ estimated from rate of new debt accumulation.
  - **Compounding** (sattvic): `V(t) = V_0 · (1 + r)^t` — foundational improvements (naming conventions, architecture) gain value as more code depends on them. r estimated from dependency growth rate.
  - **Appreciating** (rajasic): `V(t) = V_0 · log(1 + t/τ)` — optimization improvements appreciate slowly then plateau. τ estimated from usage growth.
  - **Transient**: `V(t) = V_0 · exp(-λt) · (1 - exp(-t/τ))` — improvements that take time to show value, then decay. Rise and fall.
- **Yield curve estimation**: for each improvement, fit the value function parameters from observed outcomes over time
- **Portfolio duration**: borrow from fixed-income theory — the system's improvement portfolio has a "duration" (weighted average time to value realization). A high-duration portfolio is investing in the future; a low-duration portfolio is optimizing for now.
- **Term structure**: the system can choose improvements with different durations based on its time horizon. If the system is stable (long horizon), invest in compounding improvements. If it's in crisis (short horizon), prioritize decaying improvements with immediate value.
- **Non-stationarity detection**: if the yield curve shape changes (e.g., a previously compounding improvement starts decaying), flag it as a regime change. The codebase has evolved past the point where this improvement is valuable.

**Dependencies**: A (need longitudinal outcomes), T (karma ledger for temporal data)
**Estimated complexity**: High
**Key files**: `recursive_loop.py`, `temporal_db.py`, new `yield_curve.py` module

---

## Z — Zen Meta-Strategy

**Problem**: The system uses a fixed improvement strategy (the A-Y objectives). But which strategy is optimal depends on the system's state, which changes as it improves. The meta-question — "which improvement strategy should I use right now?" — is currently answered by a human.

**Proposal**: The system observes which of A-Y are working and dynamically reconfigures its own improvement process. This is the meta-level above all other objectives — the system improves *how it improves*.

**Implementation**:
- **Meta-features** (state of the improvement system):
  - Discovery rate (novel improvements per cycle) — is exploration productive?
  - Calibration error (Brier score gap between predicted and actual) — are predictions accurate?
  - Portfolio guna balance — is the mix healthy?
  - Yield curve shape — are we investing in the future or the present?
  - Information gain rate — are we learning from outcomes?
  - Convergence rate (dream cycle) — is the system reaching equilibrium?
  - External validation correlation (from X) — does external assessment agree?
- **Meta-strategy selector**: a contextual bandit (meta-bandit) that selects which improvement strategy to emphasize:
  - Arms: {A (automated outcomes), B (interaction MC), D (surprisal exploration), Q (thermodynamic scheduling), P (info-theoretic), ...}
  - Context: meta-features above
  - Reward: improvement in the invariant metrics from W
  - The meta-bandit learns which strategies work in which system states
- **Strategy switching**: the system can switch strategies mid-cycle. If thermodynamic scheduling (Q) says "cool down" but information gain (P) says "there's still high-IG improvements available," the system can override the cooling schedule.
- **Meta-meta level**: the meta-bandit itself has a hyperparameter (exploration rate for strategies). This is set by the predictive coding layer (R, Layer 4). The system literally has a hierarchy of self-improvement:
  - Level 0: Apply improvements
  - Level 1: Improve prediction of improvements (MC, Brier)
  - Level 2: Improve exploration of improvements (P, Q, D)
  - Level 3: Improve the improvement strategy (Z, meta-bandit)
  - Level 4: Improve the meta-strategy (R, predictive coding Layer 4)
- **Zen principle**: the ultimate goal is for the system to reach a state where it no longer needs to improve — it has achieved harmony (homeostasis at a high level). The system should be able to recognize this state and shift from "improving" to "maintaining." This is the Wu Wei of self-improvement — effortless action, where the system is so well-calibrated that improvements emerge naturally from normal operation rather than from explicit search.

**Dependencies**: All of A-Y (this is the meta-layer)
**Estimated complexity**: Very High
**Key files**: `recursive_loop.py`, new `meta_strategy.py` module, all improvement subsystems

---

## Implementation Priority

### Phase 1 — Close the Loop (COMPLETE)
1. **A** — Automated Outcome Detection
2. **D** — Surprisal-Driven Exploration
3. **W** — Observer Effect Invariants
4. **X** — External Cross-Validation

### Phase 2 — Deepen the Inference (COMPLETE)
5. **J** — Dream Cycle as Bayesian Update
6. **P** — Information-Theoretic Exploration
7. **Q** — Thermodynamic Resource Allocation
8. **B** — Interaction-Aware MC
9. **E** — Variance Reduction

### Phase 3 — Spatial & Compositional (COMPLETE)
10. **F** — Holographic Trajectories
11. **G** — Galactic Zone Lifecycle
12. **H** — HRR Composition
13. **N** — Constellation Joint Evaluation
14. **U** — Relational Dependencies

### Phase 4 — Learning & Causality (COMPLETE)
15. **K** — Emotional Valence
16. **L** — Garden-Routed Evaluation
17. **R** — Predictive Coding
18. **T** — Karma Causal Ledger
19. **C** — Counterfactual Estimation
20. **V** — Guna Balance

### Phase 5 — Acceleration (COMPLETE)
21. **S** — Polyglot MC Acceleration
22. **M** — Elixir Actor Processing
23. **I** — Resonance Transfer Learning

### Phase 6 — Meta (COMPLETE)
24. **O** — Bicameral Debate
25. **Y** — Yield Curve
26. **Z** — Zen Meta-Strategy

### Phase 7 — Integration (COMPLETE)
27. **Wiring** — All 26 modules integrated into `recursive_loop.py` via lazy-loading with graceful degradation
28. **Classification** — Garden (L), Guna (V), Galactic (G) classification in `_phase_imagine`
29. **Debate** — Bicameral debate (O) in `_phase_imagine` with exploration boost in `_phase_recommend`
30. **Scoring** — Thermodynamic (Q), information gain (P), meta-bandit (Z) in `_phase_recommend`; valence (K), causal ledger (T), actors (M), predictive coding (R) in `record_outcome`

---

## Layer Summary

| Layer | Objectives | Role |
|---|---|---|
| Foundation | F, G, H, U | How improvements are represented |
| Inference | J, N, O, P, T | How we reason about improvements |
| Learning | A, K, R, V | How we update from outcomes |
| Exploration | D, I, Q, W | How we choose what to try |
| Simulation | B, C, E, S | How we predict impact |
| Infrastructure | M, S | How we compute |
| Meta | X, Y, Z | How we improve the process itself |
