# Polyglot Neuro-Upgrades: Comprehensive Strategy

**Version**: 1.0
**Date**: 2026-07-01
**Status**: Research complete, implementation planned for 2026-07-02
**Author**: Lucas Bailey + Aria (WhiteMagic cognitive architecture)

---

## Executive Summary

This document maps findings from current neuroscience research to WhiteMagic's polyglot cognitive architecture. We identify seven neuro-inspired upgrade pathways, each grounded in published computational neuroscience, and assign implementation to the polyglot language best suited for the computational characteristics of that system.

**Current state**: Three cognitive systems implemented (spreading activation, galaxy gating, sleep consolidation) with Rust acceleration core. 7 polyglot languages operational (Rust, Go, Elixir, Koka, Zig, Julia, Haskell).

**Target state**: 10 cognitive systems with full polyglot acceleration, biologically faithful dynamics, and integrated tool dispatch.

---

## 1. Neuroscience Research Findings

### 1.1 Spreading Activation & Memory Priming

**Key findings**:
- Spreading activation through association graphs is the dominant model for associative memory recall (Anderson, Collins & Loftus lineage)
- Activation decays exponentially with distance (hop count), modulated by edge strength (synaptic weight analog)
- Cross-context priming occurs when activation spreads across semantic categories — the "priming effect" can persist for seconds to minutes
- In biological systems, spreading activation is modulated by neuromodulators (dopamine strengthens, serotonin regulates)

**WhiteMagic status**: ✅ Implemented in `spreading_activation.py` + Rust `activation.rs`
**Gap**: No neuromodulatory regulation — activation spread is uniform regardless of emotional state or reward context

### 1.2 Sleep Consolidation & Hippocampal Replay

**Key findings (2024-2025)**:
- **Yang et al. (Science, 2024)**: Awake sharp-wave ripples (SWRs) act as "memory tags" 🏷️ — experiences tagged by awake ripples are selectively consolidated during subsequent sleep. This is a selection mechanism, not just passive replay.
- **Jahnke et al. (PLOS Comp Bio, 2024)**: Spontaneous ripples consolidate a sparse backbone (strongest synapses only), while evoked ripples generalize the memory (potentiate weak synapses too). Dendritic excitability is the key modulator.
- **Nature Neuroscience (2024)**: Hippocampal replay is used for planning, not just consolidation. Forward replays from current state improve decision-making via actor-critic-like PFC updates.
- **Nature Communications (2025)**: Replay can occur WITHOUT ripples — they are distinct processes. Ripples selectively tag a subset of replays for consolidation broadcast.
- **Disinhibition model (2025)**: Sleep-modulated disinhibition (reduced inhibition during slow-wave sleep) enables replay. Cortical disinhibition enables memory transfer from hippocampus.

**WhiteMagic status**: ✅ Basic consolidation implemented in `sleep_consolidation.py`
**Gaps**:
- No ripple tagging mechanism (awake experience selection)
- No replay simulation (sequence reactivation)
- No disinhibition model (state-dependent consolidation gating)
- No planning replay (forward simulation for decision-making)

### 1.3 Context-Dependent Gating & Thalamic Control

**Key findings**:
- **Thalamic Reticular Nucleus (TRN)** acts as the "gatekeeper" to cortex — inhibitory shell that filters thalamus→cortex information flow
- **EmGate model (PLOS Comp Bio)**: Amygdala→TRN pathway mediates emotionally-salient attentional selection. Three sources of inhibition (TRN, cortex, amygdala) provide selectivity + flexibility.
- **Prefrontal cortex (PFC) top-down control**: PFC projections to TRN selectively favor relevant stimuli by inhibiting competing thalamic relay cells. This is the biological basis for context-dependent gating.
- **Pulvinar nucleus**: Provides contextual modulation to cortical computations — gates effective connectivity between cortical areas based on attention/working memory demands.
- **Murray et al. (Science Advances, 2024)**: Context-dependent computation in PFC emerges from recurrent dynamics — linear dynamical systems fitted to PFC activity reveal context-dependent integration of sensory inputs.

**WhiteMagic status**: ✅ Basic galaxy gating implemented in `galaxy_gating.py` with 5 contexts
**Gaps**:
- No emotional salience modulation (amygdala analog)
- No dynamic context switching based on ongoing activity
- No multi-level gating (TRN → cortex → PFC hierarchy)
- No attentional competition between galaxy access requests

### 1.4 Predictive Coding & Prediction Error

**Key findings (2024-2025)**:
- **Predictive Coding Networks (PCNs)**: The brain generates predictions at each hierarchical level and propagates prediction errors upward. Learning minimizes prediction errors via local Hebbian plasticity.
- **Inference Learning (IL)**: PCN training algorithm that is more biologically plausible than backprop — uses only locally available information. With sufficient parallelization, can be more efficient than backprop.
- **Bidirectional PC (2025)**: The brain uses both generative (top-down prediction) and discriminative (bottom-up recognition) inference simultaneously. bPC models outperform unidirectional models.
- **Temporal PC**: Extends PC to dynamic sequences — learns transition dynamics and can reproduce motion-sensitive receptive fields.
- **Active Inference**: Predictive coding + action selection — the brain selects actions to minimize expected prediction error (free energy principle).

**WhiteMagic status**: ❌ Not implemented
**Potential**: Could dramatically improve memory relevance scoring — predict what memories will be needed based on current context, and use prediction error to prioritize surprising/novel information.

### 1.5 Global Workspace & Conscious Access

**Key findings**:
- **Global Neuronal Workspace (GNW)**: Consciousness arises when information is "broadcast" across distributed brain networks via a global workspace. Attention selects what enters the workspace.
- **Predictive GNW (2020-2025)**: Integrates predictive coding with GNW — the workspace itself generates predictions, and conscious access is gated by prediction error.
- **Adversarial testing (Nature, 2025)**: Direct comparison of GNW theory vs Integrated Information Theory (IIT) — GNW better explains conscious access dynamics, IIT better explains spatial integration.
- **Fame in the Brain**: "Attention selects and amplifies specific signals, allowing them to enter the workspace (and thus be conscious); while consciousness and working memory are intimately related because attended working memory items are conscious and use the global workspace for broadcast."

**WhiteMagic status**: Partial — the `GanYingBus` event broadcast system is structurally similar to a global workspace, but lacks the attentional selection and amplification dynamics.
**Potential**: A formal global workspace could manage which memories are "actively held" vs "passively stored" — the cognitive equivalent of working memory vs long-term memory.

### 1.6 Neuromodulation & Memory Prioritization

**Key findings**:
- **Dopamine**: Strengthens memories by marking them as reward-predicting or behaviorally important. Phasic dopamine = prediction error signal. Tonic dopamine = average reward rate.
- **Norepinephrine**: Regulates arousal and attention — high NE = focused attention, low NE = broad exploration. Modulates signal-to-noise ratio in cortical processing.
- **Serotonin**: Regulates patience and waiting behavior. Tonic serotonin tracks average punishment rate. Phasic serotonin carries prediction error for punishment.
- **Neuromodulator-dependent synaptic tagging (PMC)**: Neuromodulators trigger synaptic tagging and capture (STC) — retroactively marking which synapses were active during important events. This is the molecular basis for memory prioritization.
- **Unified neuromodulation model (PLOS Comp Bio, 2025)**: Maps how neuromodulation reshapes neuron types across Cortex, Striatum, Hippocampus, Thalamus, and Cerebellum.

**WhiteMagic status**: ❌ Not implemented
**Potential**: A neuromodulation system could dynamically adjust memory prioritization based on "emotional state" — high-dopamine states strengthen reward-related memories, high-norepinephrine states focus on detail, high-serotonin states promote patience in search.

---

## 2. Upgrade Pathways

### 2.1 Awake Ripple Tagging (Experience Selection)

**Biological basis**: Yang et al. (Science, 2024) — awake SWRs tag experiences for later consolidation.

**Implementation**: When a memory is accessed or created with high emotional valence or importance, "tag" it with a ripple marker. During the next consolidation cycle, tagged memories are prioritized for transfer.

**Language**: **Elixir** — the actor model maps perfectly to this. Each galaxy is an actor; ripple tagging is a message sent to the galaxy actor. The consolidation actor polls for tagged memories.

**Key components**:
- `RippleTag` struct: {memory_id, galaxy, timestamp, valence, importance}
- `RippleTagger` GenServer: monitors memory creation/access, tags high-salience events
- `ConsolidationScheduler`: polls tagged memories during "sleep" cycles
- Integration with existing `sleep_consolidation.py` — tagged memories get priority in transfer pathways

### 2.2 Replay Simulation (Sequence Reactivation)

**Biological basis**: Hippocampal replay reactivates sequence memories during sleep/rest. Forward replay supports planning; reverse replay supports credit assignment.

**Implementation**: During consolidation, select tagged memories and "replay" them — re-activate their association subgraphs, strengthen edges along the replayed path, and generate new associations between co-replayed memories.

**Language**: **Haskell** — replay is fundamentally a sequence traversal through a graph. Haskell's lazy evaluation enables infinite replay streams. Monadic computation maps to the sequential nature of replay. The state monad tracks which edges have been strengthened.

**Key components**:
- `replaySequence`: takes a tagged memory and walks its association subgraph
- `strengthenReplayedEdges`: STDP-like plasticity — edges traversed during replay are strengthened
- `coReplayAssociations`: memories co-replayed (same replay session) get new association edges
- `forwardReplay`: from current state → likely future states (planning)
- `reverseReplay`: from reward → preceding states (credit assignment)

### 2.3 Disinhibition Model (State-Dependent Consolidation)

**Biological basis**: Sleep-modulated disinhibition (2025 model) — reduced inhibition during slow-wave sleep enables replay and memory transfer.

**Implementation**: A "sleep state" variable that modulates galaxy gating weights. During "sleep" mode, cross-galaxy barriers are lowered (disinhibition), allowing consolidation pathways to activate. During "wake" mode, normal gating applies.

**Language**: **Koka** — algebraic effects are purpose-built for state-dependent computation. The "sleep/wake" state is an effect handler that modulates galaxy access. Koka's effect system can express "this computation requires disinhibition" as a typed effect.

**Key components**:
- `SleepState` effect: `Wake` | `LightSleep` | `DeepSleep` | `REM`
- `withDisinhibition`: effect handler that lowers cross-galaxy barriers
- State transitions: Wake → LightSleep → DeepSleep → REM → LightSleep → Wake
- Integration with `galaxy_gating.py` — sleep state modulates context weights

### 2.4 Predictive Coding for Memory Relevance

**Biological basis**: Predictive coding networks (PCNs) — the brain predicts what it will need and uses prediction error to prioritize surprising information.

**Implementation**: For each incoming query/context, predict which memories will be relevant based on past access patterns. Memories with high prediction error (surprising given the context) get boosted priority. This is the cognitive equivalent of "surprise-driven attention."

**Language**: **Rust** — PCN inference is matrix-heavy computation (layered predictions + error propagation). Rust's SIMD capabilities and zero-copy arrays make it ideal for real-time predictive coding. The existing `embedding_simd.rs` infrastructure can be extended.

**Key components**:
- `PredictiveCoder`: hierarchical model that predicts memory access patterns
- `PredictionError`: difference between predicted and actual memory relevance
- `surpriseScore`: prediction error → memory priority boost
- Integration with `core_access.py` — prediction error modulates search ranking
- Training: online learning from access patterns (Hebbian-style local updates)

### 2.5 Global Workspace (Working Memory Management)

**Biological basis**: GNW theory — a central workspace broadcasts selected information across distributed networks. Attention controls workspace access.

**Implementation**: A `GlobalWorkspace` that holds the currently-active memory set (working memory analog). Memories in the workspace are "broadcast" to all galaxies for parallel processing. The workspace has limited capacity (4-7 items, mirroring human working memory capacity).

**Language**: **Go** — goroutines + channels are ideal for broadcast patterns. Each galaxy runs as a goroutine listening on a workspace channel. The workspace broadcasts to all channels simultaneously. Go's select statement handles competition for workspace slots.

**Key components**:
- `Workspace` struct: holds 4-7 active memory references
- `BroadcastChannel`: fan-out to all galaxy goroutines
- `AttentionSelector`: competition function that selects which memories enter workspace
- `WorkspaceEviction`: Miller's law — old items evicted when new ones arrive
- Integration with `GanYingBus` — workspace state published as events

### 2.6 Neuromodulation System (Emotional State Modulation)

**Biological basis**: Dopamine, norepinephrine, serotonin modulate memory prioritization, attention focus, and exploration vs exploitation.

**Implementation**: A `Neuromodulator` system with three virtual chemicals:
- **Dopamine**: boosts memories with high reward salience. Increases during successful recall. Strengthens associations along rewarded paths.
- **Norepinephrine**: modulates signal-to-noise in search. High NE = focused search (fewer results, higher precision). Low NE = broad exploration (more results, lower threshold).
- **Serotonin**: regulates consolidation patience. High serotonin = longer consolidation cycles, more thorough transfer. Low serotonin = rapid but shallow consolidation.

**Language**: **Julia** — differential equations for neuromodulator dynamics (decay, release, receptor binding). Julia's JIT makes ODE solving fast. The existing `self_model_forecast.jl` provides infrastructure for stateful simulation.

**Key components**:
- `NeuromodulatorState`: {dopamine, norepinephrine, serotonin} levels
- `ModulatorDynamics`: ODEs for release, decay, and receptor occupancy
- `applyModulation`: modulates spreading activation, gating, and consolidation parameters
- `RewardSignal`: triggers dopamine release on successful recall
- `ArousalSignal`: triggers norepinephrine release based on task difficulty

### 2.7 Thalamic Gating (Attentional Competition)

**Biological basis**: TRN gates thalamus→cortex information flow. Amygdala→TRN pathway mediates emotional salience. PFC→TRN mediates top-down attention.

**Implementation**: An enhanced gating system with three levels:
1. **TRN level**: Hard gate — blocks galaxies from being accessed at all (e.g., archive galaxy is always gated)
2. **Cortex level**: Soft gate — modulates search result weights (current `galaxy_gating.py`)
3. **PFC level**: Context gate — selects which galaxies are "relevant" for current task

**Language**: **Zig** — the TRN is a low-level filter that needs to be extremely fast (sub-millisecond). Zig's compile-time code generation and zero-overhead abstractions make it ideal for high-frequency gating checks. The existing `libwhitemagic-zig.a` provides the build infrastructure.

**Key components**:
- `TRNGate`: compile-time-generated lookup table for galaxy access permissions
- `AmygdalaSalience`: emotional valence → salience score for each galaxy
- `PFCContext`: top-down context signal that overrides default gating
- `GatingPipeline`: TRN → Cortex → PFC three-level gating cascade
- Integration with `galaxy_gating.py` — Zig handles the fast path, Python handles configuration

---

## 3. Polyglot Language Assignment Summary

| System | Language | Rationale | Priority |
|--------|----------|-----------|----------|
| Spreading activation | **Rust** ✅ | Priority queue, SIMD, zero-copy | Done |
| Galaxy gating (basic) | **Rust** ✅ | Simple weight multiplication | Done |
| Sleep consolidation | **Python** ✅ | SQLite I/O, orchestration | Done |
| Awake ripple tagging | **Elixir** | Actor model = galaxy actors, GenServer for tagging | P1 |
| Replay simulation | **Haskell** | Lazy sequences, state monad for STDP | P1 |
| Disinhibition model | **Koka** | Algebraic effects for state-dependent computation | P2 |
| Predictive coding | **Rust** | Matrix-heavy, SIMD, real-time inference | P2 |
| Global workspace | **Go** | Goroutines + channels for broadcast | P2 |
| Neuromodulation | **Julia** | ODEs for dynamics, JIT for speed | P3 |
| Thalamic gating | **Zig** | Compile-time gates, sub-ms latency | P3 |

---

## 4. Implementation Roadmap

### Phase 1: Experience Selection & Replay (P1)
**Estimated**: 2-3 sessions

1. **Elixir ripple tagging bridge** (`bridges/elixir/ripple_bridge.exs`)
   - GenServer that monitors memory creation via JSON stdio
   - Tags high-salience memories (importance > 0.7 or emotional_valence > 0.6)
   - Exposes `ripple.tag`, `ripple.get_tagged`, `ripple.clear` via JSON protocol
   - Python dispatcher in `whitemagic_polyglot`

2. **Haskell replay engine bridge** (`bridges/haskell/replay_bridge.hs`)
   - Takes tagged memory IDs + galaxy DB paths
   - Walks association subgraphs (loaded via JSON input)
   - Applies STDP-like strengthening (Hebbian: co-active edges strengthened)
   - Generates co-replay associations between memories in same replay session
   - Exposes `replay.forward`, `replay.reverse`, `replay.strengthen` via JSON protocol

3. **Integration with sleep consolidation**
   - `sleep_consolidation.py` calls ripple bridge to get tagged memories
   - Tagged memories get priority in consolidation pathways
   - Replay engine called during consolidation to strengthen associations

4. **Tests**: Unit tests for each bridge + integration tests for the full cycle

### Phase 2: Predictive Coding & Global Workspace (P2)
**Estimated**: 3-4 sessions

1. **Rust predictive coding module** (`wm-core/src/predictive.rs`)
   - Hierarchical prediction model for memory access patterns
   - Online learning from access history (Hebbian local updates)
   - Prediction error → surprise score → search ranking boost
   - SIMD-accelerated matrix operations

2. **Go global workspace bridge** (`bridges/go/workspace_bridge.go`)
   - HTTP/gRPC server with channel-based broadcast
   - 4-7 slot working memory with LRU eviction
   - Attention competition function (salience-weighted)
   - Integration with GanYingBus event system

3. **Koka disinhibition model** (`bridges/koka/disinhibition.kk`)
   - Effect handlers for sleep/wake states
   - State transitions: Wake → LightSleep → DeepSleep → REM
   - Modulates galaxy gating weights during sleep states
   - Integration with `galaxy_gating.py`

4. **Tests**: Unit tests for each component + integration with existing cognitive systems

### Phase 3: Neuromodulation & Thalamic Gating (P3)
**Estimated**: 2-3 sessions

1. **Julia neuromodulation bridge** (`bridges/julia/neuromod_bridge.jl`)
   - ODE system for dopamine/norepinephrine/serotonin dynamics
   - Release functions triggered by reward/arousal/stress signals
   - Decay dynamics with receptor occupancy
   - Exposes `neuro.state`, `neuro.release`, `neuro.modulate` via JSON protocol

2. **Zig thalamic gating bridge** (`bridges/zig/trn_gate.zig`)
   - Compile-time-generated gate lookup tables
   - Three-level gating cascade: TRN → Cortex → PFC
   - Sub-millisecond gate evaluation
   - Exposes `gate.check`, `gate.update`, `gate.context` via JSON protocol

3. **Integration**: Neuromodulators modulate spreading activation decay rate, gating thresholds, and consolidation depth. Thalamic gating provides the fast-path filter before Python gating.

4. **Tests**: Unit tests + integration with full cognitive stack

---

## 5. Architecture Diagram (Post-Implementation)

```
                    ┌─────────────────────────────────────────────┐
                    │          Global Workspace (Go)               │
                    │    4-7 active memories, broadcast to all     │
                    └────────────────────┬────────────────────────┘
                                         │ broadcast
                    ┌────────────────────▼────────────────────────┐
                    │          GanYingBus (Python)                 │
                    │    Event bus + cognitive orchestration       │
                    └────────────────────┬────────────────────────┘
                                         │
         ┌───────────────────────────────┼───────────────────────────┐
         │                               │                           │
┌────────▼─────────┐          ┌──────────▼──────────┐    ┌──────────▼──────────┐
│  TRN Gate (Zig)  │          │  Galaxy Gating      │    │  Neuromodulation    │
│  Sub-ms filter   │          │  (Python + Rust)    │    │  (Julia)            │
│  Hard gate       │          │  Context masks      │    │  Dopamine/NE/5HT    │
└────────┬─────────┘          └──────────┬──────────┘    └──────────┬──────────┘
         │                               │                           │
         └───────────────────────────────┼───────────────────────────┘
                                         │
                    ┌────────────────────▼────────────────────────┐
                    │     Spreading Activation (Rust + Python)     │
                    │     Cross-galaxy priming with decay          │
                    └────────────────────┬────────────────────────┘
                                         │
                    ┌────────────────────▼────────────────────────┐
                    │     Predictive Coding (Rust)                 │
                    │     Surprise-driven relevance scoring        │
                    └────────────────────┬────────────────────────┘
                                         │
                    ┌────────────────────▼────────────────────────┐
                    │     Galaxy Memory Stores (SQLite)            │
                    │     10 galaxies × N memories each            │
                    └────────────────────┬────────────────────────┘
                                         │
         ┌───────────────────────────────┼───────────────────────────┐
         │                               │                           │
┌────────▼─────────┐          ┌──────────▼──────────┐    ┌──────────▼──────────┐
│  Ripple Tagging  │          │  Replay Engine      │    │  Sleep              │
│  (Elixir)        │          │  (Haskell)          │    │  Consolidation      │
│  Experience      │          │  Sequence           │    │  (Python)           │
│  selection       │          │  reactivation       │    │  Cross-galaxy       │
│  SWR tagging     │          │  STDP strengthening │    │  transfer           │
└──────────────────┘          └─────────────────────┘    └─────────────────────┘
         │                               │                           │
         └───────────────────────────────┼───────────────────────────┘
                                         │
                    ┌────────────────────▼────────────────────────┐
                    │     Disinhibition Model (Koka)               │
                    │     Sleep/wake state → gating modulation     │
                    │     State-dependent computation              │
                    └─────────────────────────────────────────────┘
```

---

## 6. Key Research References

1. **Yang, W. et al.** (2024). "Selection of experience for memory by hippocampal sharp wave ripples." *Science* 383, 1478-1483. — Awake SWRs tag experiences for sleep consolidation.
2. **Jahnke, S. et al.** (2024). "Differences in the consolidation by spontaneous and evoked ripples in the presence of active dendrites." *PLOS Comp Bio*. — Spontaneous vs evoked ripples produce different consolidation patterns.
3. **Nature Neuroscience** (2024). "A recurrent network model of planning explains hippocampal replay and human behavior." — Replay for planning, not just consolidation.
4. **Nature Communications** (2025). "Replay without sharp wave ripples in a spatial memory task." — Ripples and replay are dissociable processes.
5. **PLOS Comp Bio** (2025). "Sleep-modulated disinhibition enables replay for memory consolidation." — Disinhibition drives consolidation.
6. **PLOS Comp Bio** (2016). "The Emotional Gatekeeper: A Computational Model of Attentional Selection." — Amygdala→TRN pathway for emotional attention.
7. **Nature** (2013). "Context-dependent computation by recurrent dynamics in prefrontal cortex." — PFC context-dependent gating.
8. **Science Advances** (2024). "Inferring context-dependent computations through linear dynamical systems." — PFC dynamics as context-dependent linear systems.
9. **arXiv** (2024). "Predictive Coding Networks and Inference Learning: Tutorial and Survey." — PCN survey, IL vs backprop.
10. **arXiv** (2025). "Bidirectional predictive coding." — Generative + discriminative PC simultaneously.
11. **PNAS** (2022). "A model of autonomous interactions between hippocampus and neocortex." — Computational model of hippocampal-cortical consolidation.
12. **Frontiers** (2024). "Memory consolidation from a reinforcement learning perspective." — RL framework for consolidation.
13. **PMC** (2022). "Neuromodulator-dependent synaptic tagging and capture." — STC mechanism for memory prioritization.
14. **PLOS Comp Bio** (2025). "A unified model library maps how neuromodulation reshapes the brain." — Cross-region neuromodulation model.
15. **Nature** (2025). "Adversarial testing of global neuronal workspace and integrated information theory." — GNW vs IIT direct comparison.

---

## 7. Tomorrow's Session Priorities

### Immediate (polyglot neuro-upgrades)
1. **Phase 1, Step 1**: Elixir ripple tagging bridge — GenServer + JSON stdio protocol
2. **Phase 1, Step 2**: Haskell replay engine — sequence traversal + STDP strengthening
3. **Phase 1, Step 3**: Integration with existing `sleep_consolidation.py`

### Beyond polyglot (user's question)

Based on the current state of the project, here are the highest-value non-polyglot focuses for tomorrow:

1. **Wire cognitive systems into tool dispatch** — The three systems we built tonight (spreading activation, galaxy gating, sleep consolidation) are implemented but not yet exposed as MCP tools. They need:
   - Tool handlers in `tools/handlers/`
   - Dispatch entries in `dispatch_memory.py`
   - PRAT mappings (likely `gana_winnowing_basket` for activation, `gana_room` for gating, `gana_abundance` for consolidation)
   - NLU routing patterns in `meta_tool.py`
   - Registry definitions

2. **Forgotten Diamonds from the evolution audit** — The Phase 4 audit identified 6 high-value unimplemented features:
   - ONNX embedding model in browser (WASM substrate ready)
   - Resonance models ported to WASM
   - 4-tier Dharma evaluation
   - Visual timeline component
   - ARIA CANON essays with epistemic tags
   - MandalaOS v0.1 spec

3. **Default galaxy cleanup** — The default galaxy still has 12,737 memories. Now that we have 10 purpose-specific galaxies + archive, the default galaxy should be analyzed and its memories distributed to appropriate galaxies. This would complete the galactic migration.

4. **Cognitive integration testing** — Once the cognitive systems are wired into dispatch, we need end-to-end tests that verify the full cognitive pipeline: query → context detection → galaxy gating → spreading activation → predictive coding → search → consolidation scheduling.

My recommendation: Start with **wiring the cognitive systems into tool dispatch** (1), then move to **Phase 1 polyglot neuro-upgrades** (Elixir + Haskell bridges). The wiring is prerequisite for the polyglot bridges to be callable from the MCP interface.
