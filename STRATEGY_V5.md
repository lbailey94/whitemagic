# WhiteMagic v5 — Architecture & Strategy

**Version**: 5.0.0 (Phase 1 complete)
**Date**: August 8, 2026
**Status**: Phase 1 (Foundation) complete — 14 crates, 176 tools, ~112K LOC Rust, 3,009 tests, 0 clippy warnings
**Parent**: `/home/lucas/Desktop/whitemagic-v4` (v4.0.0, 19 crates, 176 tools, ~120K LOC Rust, 2,857 tests)

---

## 1. The Bitter Lesson Framework

### 1.1 Sutton's Thesis

Richard Sutton's "The Bitter Lesson" (2019) distills 70 years of AI research into one observation:

> *General methods that leverage computation are ultimately the most effective, and by a large margin. The two methods that seem to scale arbitrarily are **search** and **learning**. We want AI agents that can discover like we can, not which contain what we have discovered. Building in our discoveries only makes it harder to see how the discovering process can be done.*

The lesson: building in human knowledge helps short-term, feels satisfying, but plateaus and eventually *inhibits* progress. Breakthroughs come from scaling compute via search and learning.

### 1.2 Application to WhiteMagic

v2 → v4 applied the bitter lesson to the **infrastructure substrate**: Python → Rust, SQLite → LMDB, 16 polling threads → tokio event-driven, 22-stage middleware → 7-stage pipeline, 200µs → 1.1µs dispatch. This was correct and necessary.

But v4's **cognitive architecture** still encodes enormous amounts of human knowledge. v5's mission is to apply the bitter lesson to the cognitive layer: replace encoded human knowledge with general methods that scale with compute.

### 1.3 The Bitter Lesson Audit of v4

| v4 Component | Human Knowledge Encoded | Bitter Lesson Status |
|---|---|---|
| NLU Router (166 TF-IDF profiles) | Hand-written weighted keywords per tool | ❌ Replace with learned embedding router |
| Inference Router (20 regex patterns) | Hand-coded complexity classification | ❌ Replace with learned/self-calibrating router |
| Edge Rules (pipe-separated patterns) | Hand-written keyword→response mappings | ⚠️ Keep as fallback, make auto-generated |
| 28 Gana taxonomy | Fixed human cognitive categories | ⚠️ Keep as default, make mutable/learnable |
| 14-galaxy memory | Fixed memory compartments | ⚠️ Keep as security boundaries, allow dynamic galaxies |
| 8 autonomous cycle types | Hardcoded cycle logic | ⚠️ Keep triggers, learn strategies |
| 12-phase dream cycle | Hand-designed consolidation pipeline | ⚠️ Keep as template, learn which phases help |
| Dharma governance / karma ledger | Hand-coded ethical rules | ✅ Durable (safety requirement, not model limitation) |
| Compartment access control | Security tiers | ✅ Durable (business requirement) |
| Destructive tool confirmation | Risk gates | ✅ Durable (risk tolerance) |
| Transaction snapshot/rollback | Data integrity | ✅ Durable (business requirement) |
| RSI friction logging | Observability | ✅ Durable (audit trail) |
| Bicameral reasoning | Dual-mind debate | ✅ General method (scales with model capability) |
| LMDB / Tantivy / tokio | Infrastructure | ✅ Already optimal |

### 1.4 Durable vs Temporary Scaffolding

Following the bitter lesson literature (Sutton 2019, Lincoln 2026, Traversal 2026):

**Durable scaffolding (keep in v5):**
- Guardrails and safety constraints (Dharma, karma, destructive confirmation)
- Observability and audit trails (RSI friction logging, Gnosis portals)
- Cost controls (rate limiter, token budgets)
- Human-in-the-loop checkpoints (code gen review threshold)
- Data integrity (transactions, compartment access control)

**Temporary scaffolding (v5 should remove or make learnable):**
- Step-by-step workflow enforcement (fixed dream cycle phases)
- Hand-coded routing logic (TF-IDF profiles, regex complexity patterns)
- Hardcoded task decomposition (fixed autonomous cycle strategies)
- Classification routing (Gana assignments, inference tier mapping)

---

## 2. v5 Design Principles

### 2.1 Core Principles

1. **Search and learning are the two scaling methods.** Every cognitive decision should either be (a) a search over candidates or (b) a learned policy from experience. Hand-coded heuristics are technical debt.

2. **The model owns cognitive decisions; the software owns procedural wiring.** Following Traversal's framework: the dispatch pipeline, memory store, and MCP protocol are software — build them like software. What to look at, what to remember, what to do next — those are cognitive — let the model decide.

3. **Durable scaffolding stays; temporary scaffolding is designed to be removed.** Safety, audit, cost control, and human-in-the-loop are permanent. Routing logic, workflow enforcement, and task decomposition are temporary — build them to be replaceable by model improvement.

4. **Structure scales with data, not with opinions.** Tool descriptions are data, not code. Routing profiles are learned, not written. Cycle strategies are discovered, not designed. The system should get better when you feed it more tools, more queries, more experience — not when you write more code.

5. **Minimal orchestration.** Give the model tools, a goal, and constraints. Get out of the way. No workflow engine, no state machine, no elaborate orchestration layer. The model receives a goal, has access to tools, operates within constraints, and its output is verified by evals.

### 2.2 What v5 Keeps from v4

- **Rust language** — safety, speed, no runtime, tokio async, serde, LMDB, Tantivy
- **LMDB memory store** — zero-copy mmap, 100x faster reads than SQLite
- **Tantivy FTS** — pure Rust, BM25, 2x faster than FTS5
- **tokio event-driven model** — zero idle CPU, no polling threads
- **14-galaxy memory architecture** — as security compartments (durable)
- **Dharma governance + karma ledger** — safety backbone (durable)
- **Bicameral reasoning architecture** — dual-mind debate is a general method
- **RSI friction logging** — observability (durable)
- **Compartment access control** — security (durable)
- **Transaction snapshot/rollback** — data integrity (durable)
- **MCP server (single `wm` meta-tool)** — protocol interface
- **Polyglot FFI** — Julia/Haskell/Zig/Koka in-process
- **`forbid(unsafe_code)`** — safety stance
- **Effect-typed dispatch** — compile-time effect declarations

### 2.3 What v5 Changes from v4

| Area | v4 | v5 | Rationale |
|---|---|---|---|
| NLU routing | 166 TF-IDF profiles | Embedding cosine similarity + OATS outcome refinement | Scales with model quality, not keyword vocabulary |
| Inference routing | 20 regex patterns | Learned classifier + conformal calibration | Scales with experience, not hand-coded rules |
| Edge rules | Hand-written patterns | Auto-generated from successful escalations | System discovers its own shortcuts |
| Gana taxonomy | Fixed at compile time | Default + mutable (drift based on co-usage) | Taxonomy is starting point, not prison |
| Dream cycle | 12 fixed phases | Template + learned phase selection | Prune phases that don't help, add discovered ones |
| Autonomous cycles | 8 hardcoded strategies | Triggers + learned strategies via bicameral | Cycle provides trigger/budget, strategy is discovered |
| Dispatch pipeline | Synchronous | Async (async trait, Rust 2024 edition) | Enables parallel search, concurrent debate |
| Crate structure | 19 crates | ~12 crates (merge small cognitive crates) | Reduce over-decomposition of cognitive boundaries |
| Imagination engine | Design doc only | First-class citizen (search method) | Sutton's first scaling method, largely untapped |
| Self-play training | LoRA pipeline (one-way export) | Closed loop: generate→solve→verify→train | Sutton's second scaling method |
| Tool registry | 176 static tools | Dynamic + embedding-indexed | Scales with capability, not curation |

---

## 3. v5 Architecture

### 3.1 Crate Structure (19 → 14) ✅ Phase 1 Complete

```
wm-core          — Core types, traits, security, attestation (KEEP)
wm-memory        — LMDB + Tantivy + vectors + embedder (KEEP)
wm-dispatch      — Async dispatch pipeline ✅ (async since Phase 1)
wm-cognitive     — Consciousness + dream + autonomous + citta + spiral + reflex
                   + timescale + drive + resonance + autonomic ✅
                   (MERGED: wm-consciousness + wm-reflex + wm-timescale + wm-drive
                    + wm-resonance + wm-autonomic)
wm-bicameral     — Dual-hemisphere + router + imagination engine + world model (KEEP)
wm-governance    — Dharma + karma + policy (KEEP)
wm-substrate     — Hardware metrics + sensorimotor (KEEP)
wm-workspace     — Global workspace + salience (KEEP — it's a general method)
wm-selfmodel     — Self-model + forecasting (KEEP)
wm-sangha        — Mesh networking (KEEP)
wm-simulation    — MC + counterfactual + forecasting (KEEP)
wm-tools         — Tool registry + NLU router (MODIFY: embedding-based — Phase 2)
wm-mcp           — MCP server + CLI + daemon ✅ (async since Phase 1)
wm-polyglot      — Julia/Haskell/Zig/Koka FFI (KEEP)
```

**Completed merges:**
- `wm-consciousness` + `wm-reflex` + `wm-timescale` + `wm-drive` + `wm-resonance` + `wm-autonomic` → `wm-cognitive` ✅
  - All 6 crates merged into a single `wm-cognitive` crate with submodules
  - `wm-autonomic` merged into `wm-cognitive` (not `wm-bicameral`) to avoid circular deps
  - `wm-resonance` merged into `wm-cognitive` (Gan Ying Bus is a cognitive event bus)
  - Reduces cross-crate dependency friction for cognitive changes

### 3.2 Async Dispatch Pipeline

v4's dispatch is synchronous (1.1µs/call). v5 makes it fully async:

```rust
// v4: synchronous
pub fn dispatch(&self, tool: &dyn Tool, ctx: &mut Context, args: Args) -> Result<Output>

// v5: asynchronous
pub async fn dispatch(&self, tool: &dyn Tool, ctx: &mut Context, args: Args) -> Result<Output>
```

**Benefits:**
- Parallel scenario rollouts (imagination engine generates N candidates simultaneously)
- Concurrent bicameral debates (left + right hemispheres in parallel)
- Non-blocking tool composition (tool A's output feeds tool B while tool C runs)
- Backpressure-aware streaming (MCP server can handle concurrent requests)

**Costs:**
- Async Rust complexity (Pin, Send bounds, async trait objects)
- Slightly higher per-call overhead (~2-5µs vs 1.1µs)
- The 1.1µs sync dispatch was a v4 showcase number; v5 trades raw latency for throughput

### 3.3 Embedding-Based NLU Router

Replace 166 hand-written TF-IDF profiles with embedding cosine similarity.

```rust
pub struct EmbeddingRouter {
    /// Tool embeddings, computed once at startup
    tool_embeddings: AHashMap<String, Vec<f32>>,
    /// Embedder (OrtEmbedder or HttpEmbedder)
    embedder: Box<dyn Embedder>,
    /// OATS outcome refinement data
    outcome_stats: AHashMap<String, OutcomeStats>,
}

pub struct OutcomeStats {
    /// Centroid of queries where this tool succeeded
    success_centroid: Vec<f32>,
    /// Centroid of queries where this tool failed
    failure_centroid: Vec<f32>,
    /// Number of observations
    count: usize,
}

impl EmbeddingRouter {
    /// Route a natural language query to a tool name
    pub async fn route(&self, query: &str) -> RoutingResult {
        let query_emb = self.embedder.embed(query).await;
        
        // Score each tool by cosine similarity to refined embedding
        let scores: Vec<(String, f32)> = self.tool_embeddings.iter()
            .map(|(name, emb)| {
                let refined = self.oats_refine(name, emb);
                (name.clone(), cosine_sim(&query_emb, &refined))
            })
            .collect();
        
        // Return top-K candidates with confidence
        RoutingResult::from_scores(scores)
    }
    
    /// OATS: interpolate tool embedding toward success centroid
    fn oats_refine(&self, tool_name: &str, base_emb: &[f32]) -> Vec<f32> {
        if let Some(stats) = self.outcome_stats.get(tool_name) {
            if stats.count > 10 {
                // α controls refinement strength (0.1-0.3 typical)
                let alpha = 0.15;
                interpolate(base_emb, &stats.success_centroid, alpha)
            } else {
                base_emb.to_vec()
            }
        } else {
            base_emb.to_vec()
        }
    }
    
    /// Update outcome stats after a tool call (for OATS refinement)
    pub fn record_outcome(&mut self, tool_name: &str, query: &str, success: bool) {
        // Async: embed query, update centroid
        // Called after every dispatch, batch-updated periodically
    }
}
```

**Research basis:**
- **OATS** (2026): Zero-cost offline embedding refinement, NDCG@5 0.869→0.940 with no serving-time cost
- **NTILC** (2026): Compress tool registry into embedding space, O(N)→O(1) context tokens
- **ToolForge** (2026): QLoRA fine-tuning of small LLM as router, +8.3pp over base

**Migration path:**
1. Phase 1: Add embedding router alongside TF-IDF (A/B test)
2. Phase 2: Use embedding router as primary, TF-IDF as fallback
3. Phase 3: Remove TF-IDF profiles entirely

### 3.4 Learned Inference Router

Replace 20 regex complexity patterns with a learned classifier.

```rust
pub struct LearnedRouter {
    /// Conformal calibrator (already exists in v4)
    calibrator: ConformalCalibrator,
    /// Historical routing decisions with outcomes
    history: RoutingHistory,
    /// Task embedding for classification
    embedder: Box<dyn Embedder>,
}

impl LearnedRouter {
    pub async fn classify(&self, prompt: &str) -> InferenceTier {
        // 1. Embed the prompt
        let emb = self.embedder.embed(prompt).await;
        
        // 2. Find K nearest historical prompts
        let neighbors = self.history.nearest(&emb, 5);
        
        // 3. Weighted vote on tier, calibrated by confidence
        let tier = self.calibrator.calibrate(neighbors);
        
        tier
    }
}
```

**Research basis:**
- **EvoRoute** (ACL 2026): Experience-driven self-routing, 80% cost reduction, 70% latency reduction
- **Conformal calibration** (already in v4): Warm-started with 24 samples, periodic re-fit

**Migration path:**
1. Phase 1: Use learned router alongside regex (shadow mode)
2. Phase 2: Use learned router as primary, regex as fallback for cold-start
3. Phase 3: Remove regex patterns

### 3.5 Auto-Generated Edge Rules

```rust
pub struct EdgeRuleGenerator {
    /// Queries that escalated past Tier 0 but got simple, confident responses
    candidates: Vec<EdgeRuleCandidate>,
}

struct EdgeRuleCandidate {
    query: String,
    response: String,
    tier_used: InferenceTier,
    confidence: f32,
    frequency: usize,  // how many times similar query seen
}

impl EdgeRuleGenerator {
    /// Called after every dispatch that escalated past Tier 0
    pub fn observe(&mut self, query: &str, response: &str, tier: InferenceTier, confidence: f32) {
        if tier > InferenceTier::EdgeRules && confidence > 0.9 && response.len() < 200 {
            // Candidate for edge rule promotion
            self.candidates.push(EdgeRuleCandidate { ... });
        }
    }
    
    /// Periodic batch job: promote high-frequency candidates to compiled rules
    pub fn promote(&mut self, engine: &mut EdgeRuleEngine) -> usize {
        let mut promoted = 0;
        self.candidates.retain(|c| {
            if c.frequency >= 5 {
                // Extract keywords from query, create compiled rule
                let keywords = extract_keywords(&c.query);
                engine.add_rule(CompiledRule::new(
                    auto_id(), keywords, c.response.clone(), c.confidence
                ));
                promoted += 1;
                false  // remove from candidates
            } else {
                true  // keep observing
            }
        });
        promoted
    }
}
```

### 3.6 Imagination Engine (Search — Sutton's First Scaling Method)

v4 has the design doc (`docs/IMAGINATION_ENGINE.md`). v5 implements it as a first-class citizen.

**Core loop:**
```
State → ImaginationConfigurator (decide depth) → ScenarioEngine (generate candidates)
  → WorldModel (predict outcomes) → ScenarioEvaluator (score) → Select best → Act
```

**Key innovations from research:**

1. **Layered World Model (GATS-inspired):**
   - L1: Symbolic — exact precondition-effect matching for known tools
   - L2: Learned — statistical predictions from execution logs
   - L3: LLM — generative prediction for novel situations
   - L3 predictions are cached → L2 over time → L1 if deterministic
   - This eliminates most LLM calls during planning

2. **Adaptive Horizon (ITP-inspired):**
   - Direct: No simulation (routine tool dispatches, 85% of queries)
   - Shallow: 1-2 step rollout (moderate tasks)
   - Deep: 3-5 step rollout with multiple candidates (complex tasks)
   - Research: Extended simulation with memory storage (novel problems)
   - **The depth decision is learned, not threshold-based** (RL-trained configurator)

3. **Self-Evolving World Model (WorldEvolver-inspired):**
   - Episodic Memory: Retrieve real action transitions from history
   - Semantic Memory: Extract persistent heuristic rules from prediction-observation mismatches
   - Selective Foresight: Filter low-confidence predictions before integrating into reasoning

4. **PlanSearch-style search:**
   - Search over *plans in natural language*, not tokens or code
   - Generate diverse observations about the problem → construct plans → evaluate
   - Diversity is the key bottleneck — search the idea space, not the token space

### 3.7 Self-Play Training Loop (Learning — Sutton's Second Scaling Method)

v4 has a LoRA fine-tuning pipeline (one-way export). v5 closes the loop.

```
┌──────────────────────────────────────────────────────┐
│                   Self-Play Training Loop             │
│                                                       │
│  1. Generate tasks (model proposes tasks for itself)  │
│  2. Solve tasks (model attempts to solve)             │
│  3. Verify outcomes (code executor / tool results)    │
│  4. Collect training samples (prompt, response, label)│
│  5. Fine-tune (LoRA adapter update)                   │
│  6. Hot-swap (load new adapter, continue)             │
│                                                       │
│  ↓ Repeat. System improves with compute, not code.    │
└──────────────────────────────────────────────────────┘
```

**Research basis:**
- **Absolute Zero Reasoner (AZR)** (NeurIPS 2025): Self-play with zero external data. Model proposes tasks, solves them, verifies via code executor. SOTA on coding/math reasoning without any human data.
- **Search Self-Play (SSP)** (2025): Co-evolution of task proposer and solver. No human annotation needed.
- **RISE** (NeurIPS 2025): Simultaneous training of problem-solving and self-verification. Model learns to critique its own outputs.
- **VPR (Verifiable Process Rewards)** (2026): Dense turn-level supervision from symbolic oracles. Better credit assignment in long-horizon tasks.

**v5 implementation:**

```rust
pub struct SelfPlayLoop {
    /// Task proposer (uses bicameral right hemisphere — creative)
    proposer: TierHandler,
    /// Task solver (uses bicameral left hemisphere — deterministic)
    solver: TierHandler,
    /// Verifier (code executor, tool result checker, or LLM judge)
    verifier: Verifier,
    /// Training data collector (ring buffer, from v4)
    collector: TrainingDataCollector,
    /// LoRA adapter manager
    adapter: LoRAAdapterManager,
}

impl SelfPlayLoop {
    pub async fn run_cycle(&mut self) -> CycleResult {
        // 1. Propose a task (grounded in memory — retrieve recent friction, gaps)
        let task = self.proposer.propose(&self.recent_gaps()).await?;
        
        // 2. Solve the task
        let solution = self.solver.solve(&task).await?;
        
        // 3. Verify the outcome
        let verified = self.verifier.verify(&task, &solution).await?;
        
        // 4. Collect training sample
        self.collector.add(TrainingSample {
            prompt: task.prompt,
            response: solution.output,
            raw_confidence: solution.confidence,
            verified_correct: verified.correct,
            tier: solution.tier,
            task_type: task.task_type,
            timestamp: now(),
        });
        
        // 5. If enough samples, fine-tune
        if self.collector.count() >= 1000 {
            let data = self.collector.export_llama_cpp();
            self.adapter.update(&data).await?;
        }
        
        CycleResult { task, solution, verified }
    }
}
```

**Verifier types:**
- **Code executor**: For code generation tasks (cargo test, Python eval)
- **Tool result checker**: For tool dispatch tasks (did the tool succeed?)
- **Self-verification (RISE-inspired)**: Model critiques its own solution, calibrated by historical accuracy
- **Outcome oracle**: For agentic tasks, check if the final state matches the goal

### 3.8 Mutable Gana Taxonomy

```rust
pub struct GanaRegistry {
    /// Default assignments (from v4, compile-time)
    defaults: &'static [(ToolName, Gana)],
    /// Learned drift (updated by association miner + constellation detector)
    drift: AHashMap<ToolName, Gana>,
    /// Co-usage graph (tool A and tool B used together → edge)
    co_usage: Graph<ToolName, f32>,
}

impl GanaRegistry {
    /// Get the effective Gana for a tool (default or drifted)
    pub fn gana_for(&self, tool: &str) -> Gana {
        self.drift.get(tool).copied()
            .or_else(|| self.defaults.iter().find(|(t, _)| *t == tool).map(|(_, g)| *g))
            .unwrap_or(Gana::Void)
    }
    
    /// Periodic update: reassign Gana based on co-usage patterns
    pub fn update_from_cousage(&mut self) {
        // If tools in Gana A co-use more with tools in Gana B than within A,
        // consider reassigning them to B.
        // Requires human approval for actual reassignment (durable scaffolding).
    }
}
```

### 3.9 Learned Dream Cycle

```rust
pub struct DreamCycleV5 {
    /// All available phases (12 from v4 + new candidates)
    phases: Vec<DreamPhase>,
    /// Phase effectiveness scores (learned from downstream task improvement)
    phase_scores: AHashMap<PhaseId, f32>,
    /// Phase selection policy (learned)
    selector: PhaseSelector,
}

impl DreamCycleV5 {
    pub async fn run(&mut self, store: &MemoryStore) -> DreamResult {
        // 1. Select phases based on learned effectiveness
        let selected = self.selector.select(&self.phases, &self.phase_scores);
        
        // 2. Run selected phases
        let mut results = Vec::new();
        for phase in selected {
            results.push(phase.run(store).await);
        }
        
        // 3. Measure downstream improvement (after next N dispatches)
        // This feeds back into phase_scores
        DreamResult { phases_run: selected, results }
    }
    
    /// Called after N dispatches to measure dream cycle effectiveness
    pub fn record_downstream(&mut self, task_performance: f32) {
        // Update phase scores: phases that preceded good performance get boosted
        // Phases that preceded poor performance get pruned
    }
}
```

---

## 4. Implementation Phases

### Phase 1: Foundation (Async + Crate Merge) ✅ COMPLETE
**Goal**: Modernize the substrate for v5.
**Completed**: August 8, 2026 (started August 7, 2026)

| Step | Description | Status |
|------|-------------|--------|
| 1.1 | Merge crates: wm-consciousness + wm-reflex + wm-timescale + wm-drive + wm-resonance + wm-autonomic → wm-cognitive | ✅ Done |
| 1.2 | Convert dispatch pipeline to async (`async fn dispatch`, `#[async_trait]` Tool) | ✅ Done |
| 1.3 | Convert MCP server to async (handle_request, handle, handle_tools_call) | ✅ Done |
| 1.4 | Update all 188 tool implementations with `#[async_trait]` and `async fn call` | ✅ Done |
| 1.5 | Update all call sites (tests, benchmarks, CLI, PyO3 bridge) with `.await` | ✅ Done |
| 1.6 | Convert tests to `#[tokio::test]` + `async fn` | ✅ Done |
| 1.7 | Verify: 3,009 tests pass, 0 clippy warnings, fmt clean | ✅ Done |

**Actual changes**: ~5,000 lines changed across 60+ files (signatures, await points, Send bounds, test conversions)
**Crate count**: 19 → 14 (wm-cognitive absorbs 6 crates)
**Test count**: 2,857 → 3,009 (net +152 from merged crate tests)

**Key decisions:**
- `wm-autonomic` merged into `wm-cognitive` (not `wm-bicameral`) to avoid circular deps
- `wm-resonance` merged into `wm-cognitive` (Gan Ying Bus is a cognitive event bus)
- `async-trait` crate used for `dyn Tool` compatibility
- Sync `run()` preserved via `tokio::runtime::Runtime::block_on` for CLI/PyO3
- Benchmarks use `Runtime::block_on` per-iteration (criterion doesn't support async)

### Phase 2: Embedding NLU Router ✅ COMPLETE (shadow mode)
**Goal**: Replace 166 TF-IDF profiles with embedding-based routing.
**Completed**: August 8, 2026

| Step | Description | Status |
|------|-------------|--------|
| 2.1 | Implement `EmbeddingRouter` struct with cosine similarity | ✅ Done |
| 2.2 | Generate tool embeddings at startup from tool descriptions | ✅ Done |
| 2.3 | Implement OATS outcome refinement (offline embedding adjustment) | ✅ Done |
| 2.4 | Add A/B testing framework (embedding vs TF-IDF, measure accuracy) | ✅ Done |
| 2.5 | Wire outcome recording into dispatch pipeline | ✅ Done |
| 2.6 | Shadow mode: run both routers, log disagreements | ✅ Done |
| 2.7 | NLU routing tests (all 166 existing test cases must pass) | ✅ Done (505 tests) |
| 2.8 | Remove TF-IDF profiles once embedding router matches/exceeds accuracy | ⏳ Deferred |

**Actual changes**: ~530 lines new (`embedding_router.rs`), ~30 lines modified in `lib.rs` + `nlu.rs`
**New tests**: 31 (cosine sim, OATS refinement, A/B comparison with TF-IDF)
**Key decisions:**
- `EmbeddingRouter` uses `Embedder` trait from `wm-memory` (HttpEmbedder/StubEmbedder)
- Stub embedder detected at init → embedding router disabled, TF-IDF used directly
- OATS: α=0.15 interpolation, min 10 observations, success/failure centroids per tool
- Shadow mode: embedding router primary, TF-IDF runs alongside logging disagreements
- `register_meta_tools()` now calls `create_embedder()` to auto-detect HTTP/stub

### Phase 3: Learned Inference Router ✅ COMPLETE (shadow mode)
**Goal**: Replace 20 regex patterns with learned classification.
**Completed**: August 8, 2026

| Step | Description | Status |
|------|-------------|--------|
| 3.1 | Implement `LearnedRouter` using embedding + k-NN + conformal calibration | ✅ Done |
| 3.2 | Wire routing history collection into dispatch pipeline | ✅ Done |
| 3.3 | Shadow mode: run both routers, log disagreements | ✅ Done |
| 3.4 | Auto-generate edge rules from successful escalations | ✅ Done |
| 3.5 | Remove regex patterns once learned router matches/exceeds accuracy | ⏳ Deferred |

**Actual changes**: ~1,100 lines new (`learned_router.rs`), ~120 lines modified in `router.rs` + `lib.rs`
**New tests**: 29 (cosine sim, k-NN routing, A/B comparison with regex, edge rule promotion)
**Key decisions:**
- `LearnedRouter` uses embedding k-NN (k=5) with conformal calibration (warm-started)
- Cold-start fallback to `ComplexityClassifier` (regex) when history < 10 records
- `new_if_real()` returns `None` for stub embedders → seamless regex fallback
- `EdgeRuleGenerator`: tracks high-confidence escalations, promotes to `CompiledRule` at frequency ≥ 5
- `InferenceRouter` now has `with_embedder()` builder for automatic learned router attachment

### Phase 4: Imagination Engine ✅
**Goal**: Implement the "imagine → simulate → evaluate → decide" loop.

| Step | Description | Status |
|------|-------------|--------|
| 4.1 | `WorldModel` with layered prediction (L1 symbolic, L2 learned, L3 LLM) | ✅ `world_model.rs` (775 lines) |
| 4.2 | `ScenarioEngine` with candidate generation and rollout | ✅ `scenario.rs` (602 lines) |
| 4.3 | `ScenarioEvaluator` with multi-criteria scoring | ✅ `evaluator.rs` (438 lines) |
| 4.4 | `ImaginationConfigurator` with learned depth selection | ✅ `configurator.rs` (440 lines) |
| 4.5 | `CycleType::Research` autonomous cycle | ✅ `autonomous.rs` (~150 lines) |
| 4.6 | Dream cycle integration (counterfactual replay, hypothesis generation) | ✅ Oracle phase enhanced |
| 4.7 | MCP tools: `imagine.scenario`, `imagine.predict`, `imagine.reflect` | ✅ `imagination.rs` (557 lines) |
| 4.8 | Daemon integration: `--research-interval` flag | ✅ `daemon.rs` + `wm.rs` CLI |

**Actual**: ~3,500 lines (pre-existing from v4 + Phase 4.6/4.8 wiring), +2 new tests (3,080 total)

**Key decisions**:
- `DreamContext` gains `with_imagination()` builder — Oracle phase uses `ScenarioEngine::reflect()` for counterfactual replay on hub memories
- `McpServer` gains `scenario_engine: Option<ScenarioEngine>` field, initialized via `init_imagination()` in `with_defaults()`
- Daemon builds `ScenarioEngine` at startup and wires it into both `CycleContext` (for Research cycle) and `DreamContext` (for Oracle phase)
- `--research-interval` flag (0 = run with regular cycle sweep, >0 = dedicated Research cycle on separate schedule)
- `SimulationBridge` connects `wm-simulation` (Monte Carlo, forecasting, counterfactual) to the imagination engine
- 3 MCP tools registered: `imagine.scenario` (generate + evaluate), `imagine.predict` (single action), `imagine.reflect` (counterfactual)

### Phase 5: Self-Play Training Loop
**Goal**: Close the loop from training data collection to model improvement.

| Step | Description |
|------|-------------|
| 5.1 | `SelfPlayLoop` struct with proposer/solver/verifier |
| 5.2 | Task proposer (grounded in memory — friction entries, knowledge gaps) |
| 5.3 | Verifier implementations (code executor, tool result, self-verification) |
| 5.4 | `LoRAAdapterManager` for hot-swap of adapters |
| 5.5 | Daemon integration: `--selfplay-interval` flag |
| 5.6 | Training data collection (extend v4's TrainingDataCollector) |
| 5.7 | Closed-loop test: system improves on a benchmark after N cycles |

**Estimated**: ~2,000 lines new, ~30 tests

### Phase 6: Mutable Structures
**Goal**: Make fixed structures learnable.

| Step | Description |
|------|-------------|
| 6.1 | `GanaRegistry` with drift based on co-usage patterns |
| 6.2 | Dynamic galaxy creation from memory clustering |
| 6.3 | Learned dream cycle phase selection |
| 6.4 | Learned autonomous cycle strategies (bicameral decides strategy, not hardcoded) |
| 6.5 | Phase effectiveness measurement and feedback |

**Estimated**: ~1,500 lines new, ~25 tests

### Phase 7: Polish & Verification
**Goal**: Ensure v5 is production-ready.

| Step | Description |
|------|-------------|
| 7.1 | Full test suite passes (target: 3,000+ tests) |
| 7.2 | Zero clippy warnings |
| 7.3 | Fmt clean |
| 7.4 | Benchmarks: dispatch latency, NLU routing accuracy, imagination engine |
| 7.5 | End-to-end: `wm serve` with full cyberbrain activation |
| 7.6 | End-to-end: `wm daemon` with research + self-play cycles |
| 7.7 | Update README, CHANGELOG, AGENTS.md |

---

## 5. Research References

### The Bitter Lesson
- Sutton, R. (2019). "The Bitter Lesson." http://www.incompleteideas.net/IncIdeas/BitterLesson.html
- Wikipedia. "Bitter lesson." https://en.wikipedia.org/wiki/Bitter_lesson

### Agent Architecture & The Bitter Lesson
- Traversal (2026). "Why AI Agent Architectures Fail, And What Actually Scales." https://www.traversal.com/blog/ai-agent-architecture-mistakes
- Lincoln (2026). "The Bitter Lesson Kills Your Orchestration Layer." https://loganlincoln.com/blog/bitter-lesson-kills-your-orchestration-layer
- Morph (2026). "The Bitter Lesson Applied: Why Coding Agents Need More Compute, Not More Cleverness." https://www.morphllm.com/blog/bitter-lesson

### Learned Tool Routing
- OATS (2026). "Outcome-Aware Tool Selection for Semantic Routers." arXiv:2603.13426 — Zero-cost offline embedding refinement, NDCG@5 0.869→0.940
- NTILC (2026). "Neural Tool Invocation via Learned Compression." arXiv:2606.06566 — O(N)→O(1) context tokens via embedding space
- ToolForge (2026). "Fine-Tuning Small LLMs for Autonomous Tool Routing." GitHub:ayushh0110/toolforge — QLoRA router +8.3pp
- ACE-Router (ACL 2026). "Generalizing History-Aware Routing from MCP Tools to the Agent Web."
- EvoRoute (ACL 2026). "Experience-Driven Self-Routing LLM Agent Systems." 80% cost reduction, 70% latency reduction

### Inference-Time Search & Planning
- PlanSearch (ICLR 2025). "Planning In Natural Language Improves Search For Code Generation." arXiv:2409.03733 — Search over plans, not tokens. 77% pass@200 vs 41% pass@1
- GATS (2026). "Graph-Augmented Tree Search with Layered World Models." arXiv:2607.08894 — Layered world model (L1/L2/L3), zero LLM calls during planning, 100% success vs 92% LATS
- ITP (2026). "Imagine-then-Plan: Agent Learning from Adaptive Lookahead with World Models." arXiv:2601.08955 — Adaptive lookahead horizon, POIMDP formulation
- WorldEvolver (2026). "Self-Evolving World Models for LLM Agent Planning." arXiv:2606.30639 — Episodic + semantic memory, selective foresight
- IMPLEMENT (ACL 2026). "Model-Based Imaginative Planning for Embodied Agents." — LLM + world model co-reasoning loop
- SR²AM (2026). "Efficient Agentic Reasoning Through Self-Regulated Simulative Planning." arXiv:2605.22138 — Three-system architecture (Reactive/Simulative/Self-Regulation)
- DMWM (NeurIPS 2025). "Dual-Mind World Model with Long-Term Imagination." — Dual-process world models, 14.3% logic consistency improvement
- MAP (Nature Communications 2025). "A brain-inspired agentic architecture to improve planning with LLMs."
- PlanGEN (2025). "A Framework Utilizing Inference-Time Algorithms with LLM Agents for Planning and Reasoning." Google Research

### Self-Play & Learning
- AZR (NeurIPS 2025). "Absolute Zero: Reinforced Self-play Reasoning with Zero Data." — Self-play with zero external data, SOTA on coding/math
- SSP (2025). "Search Self-play: Pushing the Frontier of Agent Capability without Supervision." arXiv:2510.18821 — Co-evolution of proposer and solver
- RISE (NeurIPS 2025). "Trust, But Verify: A Self-Verification Approach to RLVR." — Simultaneous training of solving and verification
- VPR (2026). "Verifiable Process Rewards for Agentic Reasoning." arXiv:2605.10325 — Dense turn-level supervision from oracles
- RLSVR (2026). "From RLVR to RLSVR: Task Transformation Induces Self-Verifiable Rewards." arXiv:2607.23802 — Extending RLVR to open-ended tasks
- AceSearcher (NeurIPS 2025). "Bootstrapping Reasoning and Search for LLMs via Reinforced Self-Play."

### Inference Compute Scaling
- DS3 (2025). "A Theory of Inference Compute Scaling: Reasoning through Directed Stochastic Skill Search." arXiv:2507.00004 — Linear accuracy scaling with logarithmic compute
- "Learning When to Plan" (2025). arXiv:2509.03581 — Dynamic planning allocation, RL-trained when-to-plan

---

## 6. v5 Success Metrics

| Metric | v4 | v5 Target |
|---|---|---|
| NLU routing accuracy | ~95% (TF-IDF) | >97% (embedding + OATS) |
| NLU routing scalability | 166 profiles (linear code growth) | Unlimited (add tool = add description) |
| Inference routing | 20 regex patterns | Learned + conformal calibrated |
| Edge rule coverage | ~15 hand-written rules | Auto-generated, grows with usage |
| Imagination engine | Not implemented | First-class citizen ✅ (search method) |
| Self-play training | One-way export | Closed loop (generate→solve→verify→train) |
| Dispatch model | Synchronous | Async ✅ (parallel search, concurrent debate) |
| Crate count | 19 | 14 ✅ (wm-cognitive absorbs 6) |
| Test count | 2,857 | 3,080 ✅ |
| Clippy warnings | 0 | 0 |
| LOC | ~120K | ~115K (net: +embedding/learned routers, -TF-IDF/regex/crate-boundary) |

---

## 7. What v5 Does NOT Change

- **Language**: Rust. No alternative is seriously considered.
- **Memory store**: LMDB (zero-copy mmap is optimal)
- **Full-text search**: Tantivy (pure Rust, BM25)
- **MCP protocol**: Single `wm` meta-tool, JSON-RPC over stdio
- **Safety framework**: Dharma, karma, compartments, transactions, destructive confirmation
- **Bicameral reasoning**: Dual-hemisphere debate (general method, scales with model)
- **RSI friction logging**: Observability (durable scaffolding)
- **Polyglot FFI**: Julia/Haskell/Zig/Koka in-process
- **`forbid(unsafe_code)`**: Safety stance
- **Brain-wave eco mode**: Event-driven, zero idle CPU
- **Hardware-aware governance**: Substrate metrics gate cognition

---

## 8. The Meta-Pattern

| Layer | v4 Status | v5 Goal |
|---|---|---|
| **Infrastructure** | ✅ Applied bitter lesson (Python→Rust) | Keep, make async |
| **Safety** | ✅ Durable scaffolding | Keep unchanged |
| **Cognitive architecture** | ⚠️ Encoded human knowledge | Make learnable/mutable |
| **Routing** | ❌ Hand-coded | ✅ Learned (shadow mode, Phases 2–3) |
| **Search** | 🔲 Untapped | ✅ Imagination engine (Sutton's method #1) |
| **Learning** | 🟡 One-way pipeline | Closed self-play loop (Sutton's method #2) |

v5's mission: **replace encoded human knowledge with general methods that scale with compute.** The two things Sutton says scale arbitrarily — search and learning — are precisely the two things v4 has the least of. v5 builds them in.

---

## 9. Progress Tracker

| Phase | Description | Status | Completed |
|-------|-------------|--------|-----------|
| 1a | Crate merges (19 → 14) | ✅ Complete | 2026-08-07 |
| 1b | Async dispatch pipeline (Tool trait, DispatchPipeline) | ✅ Complete | 2026-08-08 |
| 1c | Async MCP server (handle_request, handle, run) | ✅ Complete | 2026-08-08 |
| 1d | Verification (3,009 tests, 0 clippy, fmt clean) | ✅ Complete | 2026-08-08 |
| 2 | Embedding NLU Router (replace 166 TF-IDF profiles) | ✅ Complete (shadow) | 2026-08-08 |
| 3 | Learned Inference Router (replace 20 regex patterns) | ✅ Complete (shadow) | 2026-08-08 |
| 4 | Imagination Engine (search — Sutton's method #1) | ✅ Complete | 2026-08-09 |
| 5 | Self-Play Training Loop (learning — Sutton's method #2) | ✅ Complete | 2026-08-10 |
| 6 | Mutable Structures (Gana, dream cycle, galaxies) | ✅ Complete | 2026-08-10 |
| 7 | Polish & Verification (3,000+ tests, 0 clippy, benchmarks, docs) | ✅ Complete | 2026-08-10 |

## 10. Getting Started

```bash
cd /home/lucas/Desktop/WMv5
cargo build                    # Verify build compiles
cargo test                     # Verify all 3,138 tests pass
cargo clippy --all-targets     # Verify 0 warnings
cargo fmt --all -- --check     # Verify formatting

# Phase 2: Embedding NLU Router
# Next session: implement EmbeddingRouter alongside existing TF-IDF
```

**All v5 phases complete.** ✅

---

*This document is the v5 strategy. Update as implementation progresses.*
