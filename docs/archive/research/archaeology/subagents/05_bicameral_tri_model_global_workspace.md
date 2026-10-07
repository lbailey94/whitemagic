<!-- Extracted from Antigravity CLI session 221fbb57-905f-4e7d-a4d3-3c11810ea0b7
     message 34a39413-5abe-483e-b7df-670f7a82a5f6 | sender 543f37eb-9c7d-4246-aae8-334a95d44e99 | 2026-09-19T01:51:30.017918358Z
     Original title: Message from Bicameral and Cyberbrain Scout (research)
     Extracted 2026-09-21 by opencode; content unmodified. -->

# Architectural Investigation: Bicameral Mind, Tri-Model Engine, and Global Workspace (Gen1 to Gen2 -> Gen3)

## 1. Functional Roles of the Left and Right Hemispheres & Corpus Callosum Mediation

### Left Hemisphere (`hemisphere.rs`, `local_llm.rs`)
* **Role**: Deterministic, analytical, evidence-based reasoning (Jaynes/MacLean: Neomammalian left cortex / "Bicameral voice 1").
* **Implementation (`LeftHemisphere`)**:
  - Operates on `HemisphereInput` (topic, evidence slice, context).
  - In heuristic mode, evidence items are classified via string markers (`support_markers` such as `"good"`, `"excellent"`, `"benefit"`, `"correct"`, vs `opposition_markers` such as `"problem"`, `"con"`, `"drawback"`, `"limitation"`).
  - Computes ratio of supporting vs opposing evidence:
    - $> 2\times$ support $\to$ `Stance::Agree` (confidence 0.8)
    - $> 2\times$ opposition $\to$ `Stance::Disagree` (confidence 0.8)
    - Balanced evidence $\to$ `Stance::Uncertain` (confidence 0.4)
    - Zero evidence $\to$ `Stance::Uncertain` (confidence 0.2)
  - Emits structured `HemisphereOutput` containing conclusion, confidence, stance, top 5 key points, and `HemisphereSource::Left`.
  - In production mode (`LlamaLeftHemisphere`), connects to a local `llama.cpp` instance (e.g. Qwen 0.5B/1.5B) run at low temperature ($0.2$) for analytical deductions, falling back to heuristic evaluation if unavailable.
* **Critique Function**: Evaluates counterparty outputs using structural rules: flags confidence $>0.9$ as overly confident, confidence $<0.3$ as under-evidenced, missing key points, or contradictory stances (e.g., `Uncertain` with high confidence).

### Right Hemisphere (`hemisphere.rs`, `llm.rs`, `bitnet.rs`)
* **Role**: Pluggable inference, creative / divergent thinking, heuristic exploration, hypothesis generation ("Bicameral voice 2").
* **Implementation (`RightHemisphere` trait)**:
  - Supports multiple backends: `RightHemisphereStub` (heuristics based on topic complexity markers like `"tradeoff"`, `"nuanced"` and evidence count), `RightHemisphereFn` (closure wrapper), `LlmRightHemisphere` (external/MCP OpenAI-compatible endpoint), and `BitNetRightHemisphere` (1-bit quantized model).
  - Runs at higher temperature ($0.7$ in `tri_model.rs`) for divergent candidate generation.
  - Generates nuanced alternatives, questions premature certainty, and supplies divergent counter-perspectives.

### Corpus Callosum (`callosum.rs`)
* **Role**: Bounded, bidirectional critique channel mediating debate between hemispheres.
* **Bandwidth & Channel Constraints**:
  - Controlled by `CallosumConfig` (`max_message_bytes`, default 1024; `max_total_bytes`, default 8192).
  - Maintains `total_bytes` using `AtomicUsize`.
  - Rejects transmission (`send()` returns `false`) if an individual payload exceeds `max_message_bytes` or if cumulative transferred bytes exceed `max_total_bytes`.
  - Message packet: `Message { direction: MessageDirection, kind: MessageKind, payload: String, round: usize }`.
  - `MessageDirection`: `LeftToRight` | `RightToLeft`.
  - `MessageKind`: `Critique`, `Counter`, `Agreement`, `Query`.
  - Conformal prediction gating (`send_conformal`): Drops messages if conformal nonconformity exceeds `max_nonconformity`.

### Deliberation & Consensus Gate (`consensus.rs`, `BicameralEngine`)
* **Round 0**: Both hemispheres independently analyze input. If stances match immediately (`left.stance == right.stance`), returns `Verdict::Agreed`.
* **Debate Rounds (1 to $N$, default 3)**:
  1. Left critiques Right (`LeftToRight`, `MessageKind::Critique`).
  2. Right critiques Left (`RightToLeft`, `MessageKind::Critique`).
  3. Messages routed through the Corpus Callosum under byte budget.
  4. Both outputs adjust via `adjust_for_critique()`: confidence drops by $0.1 \times \text{critique count}$; if confidence drops $< 0.4$, stance drops to `Stance::Uncertain`.
  5. If stances converge, returns `Verdict::AgreedAfterDebate`.
* **Exhaustion / Disagreement**:
  - If rounds exhaust without agreement, higher-confidence hemisphere prevails (`Verdict::LeftPrevailed` or `Verdict::RightPrevailed`).
  - If both are uncertain and confidence $< 0.4$, verdict is `Verdict::Inconclusive`.
  - If Right is disabled or unavailable, falls back to `Verdict::LeftOnly`.

---

## 2. Tri-Model System (Fast / Deep / Verifier) & Speculative Execution

### Tri-Model Architecture & Lifecycle (`tri_model.rs`)
Manages three distinct model components with decoupled lifecycles:
1. **Autonomic Layer (Fast / Draft)**:
   - Model: BitMamba-2 (~255M SSM, ~252MB RAM) or EdgeRules.
   - Lifecycle: **Persistent** (`is_persistent = true`), always on, never idles out.
   - Function: Continuous citta heartbeats, background salience detection, draft model for speculative decoding.
2. **Left Hemisphere (Medium / Deterministic / Verifier)**:
   - Model: llama.cpp small/medium (Qwen 0.5B / 1.5B, ~2-4GB).
   - Lifecycle: On-demand, idle-shutdown, auto-start on request.
   - Function: Deterministic user analysis, validation passes, local small/medium tasks.
3. **Right Hemisphere (Deep / Large / Creative)**:
   - Model: BitNet b1.58 (2B/8B) or second llama.cpp (Qwen 3B/7B).
   - Lifecycle: On-demand, idle-shutdown, auto-start on request.
   - Function: Deep multi-step reasoning, creative synthesis, divergent thinking.

### Idle Watchdog & Dreaming State (Phase N12)
* `ModelState`: `Stopped`, `Running`, `Idle`, `Dreaming`, `Failed`.
* `IdleMode`: `Shutdown` vs `Dream`.
* **Two-Tier Idle Lifecycle**:
  - First timeout (`idle_timeout`, default 300s): Transition `Running -> Dreaming`. The model remains warm in memory in low-power Theta state.
  - Deep idle timeout (`deep_idle_timeout`, default 1800s): Transition `Dreaming -> Stopped` (process terminated).
* **Warm Wake**: `ensure_running()` touches the model component; if it was in `Dreaming` or `Idle`, it transitions back to `Running` instantly with zero cold-start delay (emits `WarmWake` and `DreamEnded` events).

### Data-Driven Confidence Calibration
Replaced hardcoded heuristic confidences with token-level margin logprob analysis from HTTP endpoints:
$$\text{margin}_t = \text{top1\_logprob}_t - \text{top2\_logprob}_t$$
$$\text{confidence} = 0.6 \cdot \sigma(\overline{\text{margin}}) + 0.4 \cdot \sigma(\overline{\text{top1}} + 2.0)$$
where $\sigma$ is the standard logistic sigmoid.

### Speculative Execution Pipeline (`speculative.rs`)
Ported from v2's `inference/speculative_decoder.py` into a segment-level speculative decoder:
1. **Draft Phase (Fast Model)**: The small draft handler (Autonomic / BitMamba-2 255M) generates a candidate text sequence.
2. **Confidence Fast-Path**: If draft confidence $\ge \text{draft\_accept\_threshold}$ (default $0.85$), the draft is accepted immediately without invoking the verifier (`method: "draft_only"`), delivering maximum latency reduction.
3. **Verification Phase (Deep / Verifier Model)**: If draft confidence $< 0.85$, the verify handler (Left / llama.cpp 7B) generates a response.
4. **Segment Verification & Merging**:
   - Computes word-overlap similarity (Jaccard index) between draft and verify outputs.
   - If verify confidence $\ge \text{verify\_confidence\_threshold}$ (default $0.5$):
     - If similarity $> 0.5$, accepts verify output with `method = "draft_verified"`.
     - Else, accepts verify output with `method = "verify_only"`.
   - If both are uncertain, merges outputs by retaining the verify output and appending non-overlapping sentences from the draft (`method = "merged"`).
5. **Theoretical Speedup**: Measured against Sutton's scaling relation:
   $$\text{Speedup} = \frac{K \cdot p}{1 + K(1 - p)}$$
   where $K = \text{draft\_k}$ and $p = \text{acceptance\_rate}$.

---

## 3. Self-Play (`self_play.rs`) and World Models (`world_model.rs`)

### Self-Play Closed Loop (`self_play.rs`)
Implements Sutton's learning-via-compute paradigm (grounded in AZR, SSP, RISE, and VPR research) across 5 task types: `CodeGeneration`, `ToolDispatch`, `Reasoning`, `Memory`, `Creative`.
* **Propose (`TaskProposer`)**:
  - Driven by the Right Hemisphere (creative / divergent).
  - Grounded in memory: analyzes system friction entries (runtime exceptions $\to$ "generate a task to avoid this error") and memory knowledge gaps.
* **Solve (`TaskSolver`)**:
  - Driven by the Left Hemisphere (deterministic / analytical).
  - Solves the proposed task under token budget constraints.
* **Verify (`Verifier` trait)**:
  - `ExactMatchVerifier`: Evaluates whether the solution matches expected ground truth.
  - `ToolResultVerifier`: Verifies whether correct MCP/system tools were selected.
  - `SelfVerifier` (RISE-inspired): Self-reflection calibrated against historical accuracy:
    $$\text{score} = \text{parsed\_score} \times \max(0.5, \text{historical\_accuracy})$$
* **Collect & Fine-Tune (`TrainingDataCollector`, `LoRAAdapterManager`)**:
  - Stores prompt, response, confidence, and binary verification label (`verified_correct`) in a ring buffer.
  - When buffer hits `min_samples` (default 1000), exports `adapter_v{N}_train.jsonl` in llama.cpp format and increments the adapter version for hot-swapping.
  - Automatically aborts run early if 3 consecutive cycles fail.

### World Model (`world_model.rs`)
Implements System II simulative reasoning (grounded in Imagine-then-Plan [ITP], SimuRA, and DMWM [Dual-Mind World Model, NeurIPS 2025]):
* **Dual-Mind Prediction**:
  - Left Hemisphere predicts the deterministic forward state transition.
  - Right Hemisphere explores creative/counterfactual alternatives.
  - Structured prompt parses: `DESCRIPTION`, `CHANGES`, `RISKS`, `PROGRESS`, `CONFIDENCE`.
* **Multi-Tier Caching (L1 / L2)**:
  - **L1 In-Memory Cache (`PredictionCache`)**: Hashes `(state, action, goal)` $\to$ `u64`. TTL-backed (default 300s, max 512 entries, FIFO eviction). Bypasses LLM calls during recursive rollouts and Monte Carlo tree searches.
  - **L2 LLM Prediction**: Invoked only on L1 cache miss.
* **Consensus Gating**: If $|\text{conf}_{\text{left}} - \text{conf}_{\text{right}}| \le \text{consensus\_threshold}$ (default $0.3$), merges predictions into a consensus state (higher-confidence description, union of changes and risks, averaged goal progress).
* **Multi-Step Rollout (`rollout`)**: Chains sequential transitions: $\hat{S}_{t+1}$ generated by step $t$ becomes the `current_state` for action $A_{t+1}$.

---

## 4. Global Workspace Spotlight of Attention Implementation

### Gen1 Implementation (`global_workspace.py`, `nervous_system.py`)
* `GlobalWorkspace`:
  - 56-line Python list-based bus.
  - Every publication appends `{timestamp, core, type, payload, salience}`.
  - Naive arbitration: sorts entire event backlog by `salience` descending; if `top_event["salience"] > 0.8`, sets `self.active_core = top_event["core"]`.
  - Unbounded list growth, no time decay, static thresholding.
* `UnifiedNervousSystem`:
  - Wires 7 biological organs: `immune`, `metabolism`, `genetic`, `dream`, `consciousness`, `resonance`, `emergence`.
  - Multiscale loops:
    - 10ms reflex loop: Monitors subsystem loads; throttles if load $>0.8$; alerts immune system if error budget depletes.
    - 1s planner loop: Evaluates subsystem priority by $\text{load} \times \text{importance}$ (where immune=1.0, consciousness=0.9, resonance=0.8, metabolism=0.7, etc.). Top subsystem becomes `consciousness["focus"]`.
    - 1hr consolidation loop: Activates dream subsystem for hippocampal memory consolidation.

### Gen2 Implementation (`wm-workspace`: `salience.rs`, `spotlight.rs`, `bus.rs`)
* **Multiplicative Salience (`salience.rs`)**:
  $$\text{Salience} = \text{urgency} \times \text{novelty} \times \text{confidence}$$
  - Captures the biological reality that an event with zero novelty, zero confidence, or zero urgency must not steal attentional focus.
  - Strict input sanitization: Replaces NaNs and $\pm\infty$ with $0.0$ and clamps to $[0.0, 1.0]$ to eliminate salience poisoning vulnerabilities.
  - Default urgency mapping by event type: `SafetyAlert` ($1.0$), `Error` ($0.9$), `ThresholdCrossing` ($0.8$), `AttentionRequest` ($0.6$), `NovelDetection` ($0.4$), `Reward` ($0.3$), `DriveUpdate` ($0.2$).
* **Time-Decayed Spotlight (`spotlight.rs`)**:
  - Attention holder represented by `SpotlightEntry`.
  - **Exponential Half-Life Decay**:
    $$\text{strength}(t) = \text{base\_salience} \times 0.5^{\frac{\Delta t}{\tau}}$$
    (where default half-life $\tau = 5.0\text{s}$).
  - **Arbitration Policy (`arbitrate`)**:
    - If spotlight is empty $\to$ transfers immediately.
    - If `event.should_preempt()` (composite salience $>0.8$) $\to$ immediately preempts current spotlight holder.
    - Normal arbitration $\to$ transfers if and only if $\text{salience}_{\text{new}} > \text{strength}(t)_{\text{current}}$. As the current spotlight decays over time, incoming moderate events naturally claim attention without artificial starvation.
  - Batch arbitration (`arbitrate_batch`): Evaluates multiple events across cores in a single decision cycle.
  - Tracks transfer counts and per-core hold distributions.

---

## 5. Dissolving Bicameral and Attentional Dynamics into Gen3 Primitives: `[Select -> Transform -> Evaluate -> Commit]`

### The Problem in Gen1/Gen2
Gen1 and Gen2 hardcoded each cognitive mechanism into dedicated monolithic subsystems:
- `BicameralEngine` & `ConsensusGate` (rigid left-right debate threads)
- `TriModelManager` (manual lifecycle polling, state flags, idle watchdogs)
- `SpeculativeDecoder` (bespoke draft/verify pipeline)
- `SelfPlayLoop` (fixed proposer/solver/verifier harness)
- `WorldModel` (bespoke rollout and caching loop)
- `GlobalWorkspace` / `Spotlight` (standalone bus with dedicated arbitration)

This resulted in subsystem proliferation, hardcoded model endpoint assumptions, rigid control flows, and massive amounts of glue code.

### The Gen3 Solution
In Gen3, all of these dynamics are dissolved into compositions of the fundamental 4-stage pipeline: **`[Select -> Transform -> Evaluate -> Commit]`**. No separate LLM orchestrator subsystems are needed. Instead, "hemispheres" and "models" become pluggable **Transform kernels**, while the "Corpus Callosum", "Spotlight", and "Consensus Gate" become instances of **Select** and **Evaluate** policy operators:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             GEN3 COGNITIVE CYCLE                            │
│                                                                             │
│  [SELECT]     Salience filter & attentional priority (decayed spotlight)   │
│       │                                                                     │
│  [TRANSFORM]  Execution kernel (Fast/Draft vs Deep/Analytical vs Creative)  │
│       │                                                                     │
│  [EVALUATE]   Conformal check, logprob margin, or consensus critique        │
│       │                                                                     │
│  [COMMIT]     State persistence, attention update, or LoRA buffer append    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Direct Mapping Table

| Dynamic | **Select** | **Transform** | **Evaluate** | **Commit** |
|---|---|---|---|---|
| **Global Workspace / Attention** | Query event backlog; filter candidate by multiplicative salience discounted by exponential decay ($0.5^{\Delta t / \tau}$). | Contextualize selected event with active memory envelope and working context. | Check preemption threshold ($>0.8$) or verify $\text{salience} > \text{current\_strength}$. | Bind winning event to execution focus; update decay timestamp; broadcast state change. |
| **Speculative Decoding** | Route prompt by complexity budget; select low-cost Fast/Draft kernel (Autonomic / BitMamba / EdgeRule). | Draft kernel generates candidate output sequence. | Compute margin uncertainty from logprobs: if $\ge \theta_{\text{accept}}$, pass; else execute Deep kernel (Verifier) and compare similarity. | Commit verified output to response stream; record throughput and speedup telemetry. |
| **Bicameral Debate & Consensus** | Select thesis/antithesis prompt framing and evidence context from working memory. | Execute dual-kernel transform: analytical low-temp ($0.2$) + divergent high-temp ($0.7$). | Run critique operator: check stance divergence and confidence delta $|\text{conf}_L - \text{conf}_R|$. If $> \epsilon$, loop back to Transform with critique feedback. | Commit consensus synthesis (or prevailing conclusion) to narrative memory. |
| **World Model Simulation** | Select state $S$, action $A$, goal $G$; check L1 hash cache. | If cache miss, generate simulated transition $(S, A) \to \hat{S}$. | Score progress delta $\Delta G$, risk factors, and confidence calibration. | Cache transition; if multi-step rollout, feed $\hat{S}$ into next cycle's **Select**. |
| **Self-Play Training** | Select system friction entry or memory gap as problem seed. | Chain Proposer transform (task $T$) $\to$ Solver transform (solution $S$). | Execute Verifier primitive (unit test, tool oracle, or calibrated self-critique). | Append labeled sample to training ring buffer; trigger adapter compile when full. |

### Architectural Benefit for Gen3
1. **Zero Orchestrator Sprawl**: No need for `TriModelManager`, `BicameralEngine`, or `SpeculativeDecoder` classes. A single execution engine runs the 4-stage pipeline.
2. **Unified Resource Governance**: Compute budgets (token limits, latency timeouts, SIMD/accelerator tiers) are enforced uniformly at the **Transform** stage.
3. **Pluggable & Composable**: Multi-turn debate, speculative drafting, and multi-step rollouts are simply recursive or looped pipeline invocations, configured purely by policy rather than hardcoded daemon threads.
