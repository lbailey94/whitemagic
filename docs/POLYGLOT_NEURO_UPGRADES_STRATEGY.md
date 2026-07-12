> **Superseded by**: [architecture/COGNITIVE_ARCHITECTURE_STRATEGY.md](architecture/COGNITIVE_ARCHITECTURE_STRATEGY.md)

# Polyglot Neuro-Upgrades: Comprehensive Strategy

**Version**: 1.1
**Date**: 2026-07-01
**Status**: Research complete (updated with 2026 findings), implementation planned for 2026-07-02
**Author**: Lucas Bailey + Aria (WhiteMagic cognitive architecture)

---

## Executive Summary

This document maps findings from current neuroscience research — including 10+ publications from 2026 — to WhiteMagic's polyglot cognitive architecture. We identify nine neuro-inspired upgrade pathways, each grounded in published computational neuroscience, and assign implementation to the polyglot language best suited for the computational characteristics of that system.

**Current state**: Three cognitive systems implemented (spreading activation, galaxy gating, sleep consolidation) with Rust acceleration core. 7 polyglot languages operational (Rust, Go, Elixir, Koka, Zig, Julia, Haskell).

**Target state**: 12 cognitive systems with full polyglot acceleration, biologically faithful dynamics, and integrated tool dispatch — informed by 2026 research on context-driven replay, two-factor consolidation, momentum dynamics, and metaplasticity.

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

### 1.8 2026 Computational Neuroscience Breakthroughs

The following findings are from publications dated 2026, representing the cutting edge of computational neuroscience and neuromorphic computing. These are directly actionable for WhiteMagic's cognitive architecture.

#### CMR-replay: Context-Driven Memory Reactivation (eLife, Jan 2026)

**Paper**: "A unifying account of replay as context-driven memory reactivation" — eLife 2026;13:RP99931

**Key findings**:
- Replay is not mere recapitulation — it's **context-guided memory reactivation**. The brain associates experiences with encoding contexts at rates varying by salience.
- During quiescence, replay emerges from **autonomous bidirectional interactions between contexts and their associated experiences** — a cascade, not a linear playback.
- CMR-replay explains phenomena that RL-based models fail to account for:
  - Stable proportion of backward replay through learning
  - Enhanced replay of **non-local and never-experienced novel trajectories**
  - Reduced item reactivation with experience (familiarity suppresses replay)
  - Increased forward replay during sleep vs. awake
  - Preferential replay of infrequent and remote experiences
- Replay **strengthens context-item associations** — it's not epiphenomenal, it actively benefits memory

**WhiteMagic implication**: Our sleep consolidation system should use **context-guided replay**, not simple sequence replay. Memories should be reactivated based on their encoding context (galaxy), and replay should jump across contexts when they share associative elements. This directly validates our cross-galaxy bridge architecture. The "non-local trajectory" finding means our spreading activation should sometimes explore paths that have never been traversed — novel association generation during consolidation.

#### Two-Factor Synaptic Consolidation (PNAS, 2026)

**Paper**: "Two-factor synaptic consolidation reconciles robustness with pruning and homeostatic scaling" — PNAS, 2026

**Key findings**:
- A **self-supervised consolidation model** using replay and two-factor synapses that maximizes robustness of cued recall with respect to intrinsic synaptic noise.
- Dynamics of this optimization naturally produce:
  - **Multiplicative homeostatic scaling** (all synapses scaled by a common factor)
  - **Task-driven synaptic pruning** (weak/irrelevant connections eliminated)
  - **Increased neural stimulus selectivity** (memories become more distinct over time)
  - **Preferential strengthening of weak memories** (consolidation prioritizes fragile memories)
- Predicts that **synaptic noise scales sublinearly with synaptic strength** — confirmed in meta-analysis of synaptic imaging data
- Connectivity becomes **sparse** through consolidation — dense initial encoding → sparse stable engram

**WhiteMagic implication**: Our sleep consolidation should implement **two-factor strengthening**: (1) the replay factor (which memories were reactivated) and (2) the noise-robustness factor (which memories are most fragile). Weak memories should be preferentially strengthened, not just important ones. Association edges should be pruned during consolidation to achieve sparse connectivity — our current pruning is importance-threshold-based, but should be noise-robustness-optimized instead.

#### Leakage and Second-Order Dynamics for RNN Replay (arXiv, Feb 2026)

**Paper**: "Leakage and Second-Order Dynamics Improve Hippocampal RNN Replay" — arXiv:2602.18401

**Key findings**:
- **Hidden state leakage** in RNNs improves replay quality — biological neural networks use leakage for memory dynamics.
- **Hidden state adaptation** (negative feedback) encourages exploration in replay but incurs non-Markov sampling that slows it.
- **Hidden state momentum** enables **temporally compressed replay** — connected to underdamped Langevin sampling. This is the first model of temporally compressed replay in noisy path-integrating RNNs.
- Together, adaptation + momentum counter slowness while maintaining exploration.

**WhiteMagic implication**: Our Rust spreading activation could implement **momentum dynamics** — nodes that were recently activated carry forward momentum, enabling faster traversal of familiar paths. The "temporal compression" aspect means replay should be faster than real-time (which our sleep consolidation already does, but the dynamics could be improved with momentum-based queue prioritization).

#### Conditions for Replay of Neuronal Assemblies (PLOS Comp Bio, 2026)

**Paper**: "Conditions for replay of neuronal assemblies" — PLOS Computational Biology, 2026

**Key findings**:
- **Exclusively excitatory networks** are sufficient for replay amplification — inhibition is not required.
- **Weaker feedforward connectivity** generates slower and wider pulses that can be sustained by recurrent connections.
- **Membrane time constant** relative to pulse width determines replay viability — larger time constants facilitate propagation.
- A **population model of membrane-potential distributions** analytically describes how connectivity structure determines replay speed.

**WhiteMagic implication**: Our association graph doesn't need "inhibitory" edges (suppressive associations) for replay to work — excitatory-only (positive weights) is sufficient. However, the **strength of feedforward connections** should be tunable: weaker connections produce slower, more exploratory replay; stronger connections produce rapid, focused replay. This suggests a "replay temperature" parameter in our consolidation engine.

#### BrainTrace: Linear-Memory Online Learning for SNNs (Nature Communications, Feb 2026)

**Paper**: "Model-agnostic linear-memory online learning in spiking neural networks" — Nature Communications, 2026

**Key findings**:
- **BrainTrace** enables online learning of rich spiking dynamics with **orders-of-magnitude lower memory consumption**.
- Model-agnostic: works with any SNN architecture.
- Enables **long-horizon training** on commodity accelerators.
- Strong performance on neuromorphic classification benchmarks and brain-simulation settings.

**WhiteMagic implication**: If we eventually implement spiking neural network dynamics in our cognitive core (Rust or Zig), BrainTrace's approach to linear-memory online learning could enable training on long memory sequences without the memory blowup that typically plagues BPTT. This is especially relevant for the "dream cycle" — long offline training sessions over thousands of memories.

#### Sleep-Mediated Fear Memory Consolidation (PLOS Comp Bio, 2026)

**Paper**: "Learning, sleep replay and consolidation of contextual fear memories: A neural network model" — PLOS Computational Biology, 2026

**Key findings**:
- Combines **hippocampal sleep replay** with **synaptic homeostasis** for emotional memory consolidation.
- Disruptions in sleep processes (e.g., under stress) lead to **amygdala hyperactivity, enhanced fear acquisition, and heightened generalization**.
- Context fear memories transition from **transient hippocampal-amygdalar representations** to **stable amygdalo-cortical associations** through hippocampal replay during sleep.
- **Synaptic pruning failure** in the aftermath of emotional learning favors accumulation of synaptic strengths → chronic sensitized state.

**WhiteMagic implication**: Our consolidation should handle "emotional" memories (high valence) differently — they need both replay AND synaptic homeostasis (scaling down). If we don't prune associations after emotional encoding, we risk "over-connecting" the emotional memory to everything, which is the computational analog of PTSD generalization. This suggests a **homeostatic scaling pass** in our sleep consolidation: after strengthening, scale all association weights by a common factor to prevent runaway potentiation.

#### Shape-Shifting Molecular Memristors (Advanced Materials, Jan 2026)

**Paper**: "Molecularly Engineered Memristors for Reconfigurable Neuromorphic Functionalities" — Advanced Materials, 2026; DOI: 10.1002/adma.202509143

**Key findings**:
- Molecular devices that **switch roles** — behaving as memory, logic, or learning elements within the same structure.
- Precise chemical design lets electrons and ions reorganize dynamically.
- Unlike conventional electronics, these devices **physically encode intelligence** rather than merely imitating it.
- Route to neuromorphic hardware where learning is encoded into the material itself.

**WhiteMagic implication**: While we can't use molecular memristors directly, the **reconfigurable role** concept is powerful. Our memory nodes should be able to serve as: (1) memory storage, (2) reasoning nodes (logic), and (3) learning nodes (plasticity) depending on cognitive context. This aligns with our galaxy gating system — a memory in "coding" context serves as a reasoning node, while the same memory in "session" context serves as a storage node. The "role-switching" could be implemented as a context-dependent activation function.

#### Neuromorphic Computing Breakthroughs (ScienceDaily, Feb-Apr 2026)

**Findings**:
- **Brain-inspired machines solve PDEs** (Sandia National Labs, Feb 2026): Neuromorphic computers can now solve complex physics equations — previously thought to require energy-hungry supercomputers. Opens door to neuromorphic formulations of advanced math.
- **HfO₂ memristive synapses** (Apr 2026): New nanoelectronic device using hafnium oxide mimics neuron processing+storage at same location. **70% energy reduction** potential. Asymmetrically extended p-n heterointerfaces for energy-efficient synaptic emulation.
- **Brain-inspired synaptic transistors** (Nature Communications, 2026): In-situ spiking reinforcement learning with third-terminal modulated eligibility traces and dynamic reward signaling.

**WhiteMagic implication**: The energy efficiency findings validate our polyglot approach — using Rust for computationally intensive cognitive operations is the software analog of neuromorphic hardware specialization. The "third-terminal modulation" concept (eligibility traces modulated by a separate signal) maps to our neuromodulation pathway — a separate system that modulates which memories are eligible for strengthening without directly participating in the memory operation itself.

#### Engram Synapse Dynamics (Journal of Neurochemistry, 2026)

**Paper**: "Engram Synapses and Synapse Dynamics in Memory Processing" — J Neurochem, 2026; doi: 10.1111/jnc.70404

**Key findings**:
- Learning-induced neuronal activity **dynamically rewires synapses**, altering formation and elimination rates.
- In vivo two-photon imaging reveals activity-driven plasticity in task-related regions.
- Synaptic tagging and capture models refined for computational frameworks.

**WhiteMagic implication**: Our association edges should be **dynamically rewired** — not just created and pruned, but continuously adjusted based on access patterns. The "tagging and capture" mechanism means when a memory is accessed, its incoming edges should be temporarily "tagged" for potential strengthening during the next consolidation cycle. This is the molecular basis for our ripple tagging system.

#### Computational Framework for Epigenetic Plasticity (Brain, 2026)

**Paper**: "A computational framework for epigenetic plasticity in memory" — Brain, 2026; doi: 10.1093/brain/awag094

**Key findings**:
- Epigenetic modifications (DNA methylation, histone modification) serve as **slow, persistent memory marks** that gate synaptic plasticity.
- Computational model shows epigenetic state determines **intrinsic neural excitability** biases, affecting which neurons are recruited into engrams.
- Provides a framework for **long-timescale memory regulation** — beyond synaptic plasticity, there's a slower layer of metaplasticity.

**WhiteMagic implication**: We need a **metaplasticity layer** — a slow-changing state that gates which memories are eligible for plasticity changes. This is above the synaptic level (association edges) and below the systems level (galaxy gating). Implementation: each memory could have an "epigenetic state" (a set of slow-changing flags) that determines its baseline excitability — how easily it gets activated during spreading activation. Memories that haven't been accessed in a long time could have their epigenetic state "methylated" (silenced), requiring a stronger activation to participate. This prevents old memories from cluttering active retrieval while keeping them accessible if explicitly targeted.

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

### 2.8 Momentum Dynamics & Replay Temperature (2026-Informed)

**Biological basis**: Leakage and Second-Order Dynamics (arXiv:2602.18401, Feb 2026) — hidden state momentum enables temporally compressed replay; adaptation controls exploration vs. exploitation. Conditions for replay (PLOS Comp Bio, 2026) — feedforward connection strength determines replay speed and width.

**Implementation**: Enhance the existing Rust spreading activation engine with:
- **Node momentum**: recently-activated nodes carry forward momentum, enabling faster traversal of familiar association paths. `momentum[node_id] = decay * momentum[node_id] + current_activation`
- **Adaptation feedback**: nodes that have been activated many times in a session develop adaptation (negative feedback), encouraging exploration of less-traveled paths. This prevents the activation from getting stuck in high-weight loops.
- **Replay temperature**: a tunable parameter (0.0-1.0) that controls the balance between strong-feedforward (fast, focused replay) and weak-feedforward (slow, exploratory replay). Low temperature = exploit known paths; high temperature = explore novel associations.
- **Temporally compressed replay**: during sleep consolidation, replay sequences are compressed — multiple hops per "tick" — using momentum to carry activation across multiple edges in a single step.

**Language**: **Rust** (extension of existing `activation.rs`) — momentum requires per-node state tracking in the priority queue, which is already a Rust `BinaryHeap`. The adaptation feedback is a simple decay function applied per node.

**Key components**:
- `MomentumState`: per-node momentum vector, updated each spread step
- `AdaptationTracker`: per-session activation count, applies negative feedback
- `ReplayTemperature`: tunable parameter for exploration vs. exploitation
- `CompressedReplay`: multi-hop traversal mode for sleep consolidation
- Integration with `spread_activation()` — momentum modifies the priority queue ordering

### 2.9 Metaplasticity Layer (Epigenetic Gating)

**Biological basis**: Computational framework for epigenetic plasticity (Brain, 2026) — epigenetic modifications serve as slow, persistent memory marks that gate synaptic plasticity. Engram synapse dynamics (J Neurochem, 2026) — activity-driven plasticity dynamically rewires synapses. Two-factor synaptic consolidation (PNAS, 2026) — homeostatic scaling prevents runaway potentiation.

**Implementation**: A three-layer plasticity system:
1. **Synaptic layer** (fast, per-edge): association edge weights — already implemented
2. **Metaplasticity layer** (slow, per-memory): each memory has an "epigenetic state" — a set of slow-changing flags:
   - `excitability`: baseline activation threshold (0.0-1.0). Newly created memories start at 0.3 (easily activated). Unused memories gradually increase toward 1.0 (hard to activate).
   - `methylation`: silencing flag (0.0-1.0). Increases with disuse, decreases with access. High methylation = memory is "archived" — requires explicit targeting.
   - `consolidation_count`: how many times this memory has been replayed during sleep. Higher count = more stable, less likely to be pruned.
3. **Homeostatic scaling layer** (global, per-galaxy): after each consolidation cycle, all association weights in a galaxy are scaled by a common factor to maintain total synaptic weight within a target range. This prevents runaway potentiation (the "PTSD generalization" problem from the fear memory consolidation paper).

**Language**: **Python** (orchestration) + **Rust** (scaling computation) — the metaplasticity state is stored alongside memories in SQLite (Python), but the homeostatic scaling computation (multiplicative scaling of all edges in a galaxy) is a Rust SIMD operation.

**Key components**:
- `EpigeneticState`: dataclass stored per memory — {excitability, methylation, consolidation_count}
- `MetaplasticityEngine`: updates epigenetic state based on access patterns (slow timescale)
- `HomeostaticScaler`: scales all association weights in a galaxy after consolidation
- `MethylationGate`: gates spreading activation — methylated memories require higher activation to participate
- Integration with `spreading_activation.py` (methylation gate), `sleep_consolidation.py` (homeostatic scaling), and `galaxy_gating.py` (excitability modulates galaxy weight)

---

## 3. Polyglot Language Assignment Summary

| System | Language | Rationale | Priority |
|--------|----------|-----------|----------|
| Spreading activation | **Rust** ✅ | Priority queue, SIMD, zero-copy | Done |
| Galaxy gating (basic) | **Rust** ✅ | Simple weight multiplication | Done |
| Sleep consolidation | **Python** ✅ | SQLite I/O, orchestration | Done |
| Awake ripple tagging | **Elixir** | Actor model = galaxy actors, GenServer for tagging | P1 |
| Replay simulation | **Haskell** | Lazy sequences, state monad for STDP | P1 |
| Momentum dynamics | **Rust** | Extension of activation.rs, per-node state | P1 (2026) |
| Metaplasticity layer | **Python+Rust** | SQLite state + SIMD scaling | P2 (2026) |
| Disinhibition model | **Koka** | Algebraic effects for state-dependent computation | P2 |
| Predictive coding | **Rust** | Matrix-heavy, SIMD, real-time inference | P2 |
| Global workspace | **Go** | Goroutines + channels for broadcast | P2 |
| Neuromodulation | **Julia** | ODEs for dynamics, JIT for speed | P3 |
| Thalamic gating | **Zig** | Compile-time gates, sub-ms latency | P3 |

---

## 4. Implementation Roadmap

### Phase 1: Experience Selection, Replay & Momentum (P1)
**Estimated**: 3-4 sessions

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
3. **Rust momentum dynamics** (extension of `activation.rs`)
   - Per-node momentum state in the priority queue
   - Adaptation tracker (per-session activation count → negative feedback)
   - Replay temperature parameter (0.0-1.0) for exploration/exploitation balance
   - Temporally compressed replay mode for sleep consolidation
   - Based on arXiv:2602.18401 (Feb 2026) + PLOS Comp Bio 2026 findings

4. **Integration with sleep consolidation**
   - `sleep_consolidation.py` calls ripple bridge to get tagged memories
   - Tagged memories get priority in consolidation pathways
   - Replay engine called during consolidation to strengthen associations
   - Context-guided replay (CMR-replay, eLife 2026): memories reactivated by encoding context, not just temporal sequence
   - Two-factor strengthening (PNAS 2026): weak/fragile memories preferentially strengthened

5. **Tests**: Unit tests for each bridge + integration tests for the full cycle

### Phase 2: Predictive Coding, Global Workspace & Metaplasticity (P2)
**Estimated**: 4-5 sessions

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

4. **Python+Rust metaplasticity layer** (`metaplasticity.py` + `wm-core/src/scaling.rs`)
   - `EpigeneticState` per memory: {excitability, methylation, consolidation_count}
   - `MetaplasticityEngine`: slow updates to epigenetic state based on access patterns
   - `HomeostaticScaler` (Rust SIMD): multiplicative scaling of all edges per galaxy after consolidation
   - `MethylationGate`: gates spreading activation — methylated memories need higher activation
   - Based on Brain 2026 (epigenetic plasticity) + PNAS 2026 (two-factor consolidation) + PLOS Comp Bio 2026 (fear memory homeostasis)

5. **Tests**: Unit tests for each component + integration with existing cognitive systems

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

### ✅ Implementation Complete (2026-07-02)

All 9 neuro-upgrade systems have been implemented, tested, and wired into the MCP tool dispatch pipeline.

**Phase 1: Polyglot Subprocess Bridges** ✅
- Elixir ripple tagging bridge (`polyglot/bridges/elixir/ripple_tagging.exs` + Python fallback)
- Haskell replay simulation bridge (`polyglot/bridges/haskell/replay_sim.hs` + Python fallback)
- Julia neuromodulation bridge (`polyglot/bridges/julia/neuromodulation.jl` + Python fallback)
- 23 unit tests (all passing)

**Phase 2: Rust PyO3 Hot-Path Modules** ✅
- New Rust crate `wm-neuro` (`polyglot/whitemagic-rs/crates/wm-neuro/`)
- Thalamic gating (context-dependent galaxy access masks)
- Predictive coding (JEPA-style prediction error + novelty scoring)
- Momentum dynamics (per-node momentum accumulation + decay)
- Python wrappers with pure-Python fallback (`neuro_hotpath.py`)
- 24 Python unit tests + 18 Rust unit tests (all passing)

**Phase 3: Cognitive Integration** ✅
- Metaplasticity system (BCM-inspired threshold adaptation + persistence)
- Global Workspace (salience-based competition + GanYingBus broadcast)
- Neuro-Cognitive Sensorium (integrates all 9 systems → 8 citta coherence dimensions)
- Cognitive integration test (full 9-system cognitive cycle)
- 25 unit tests (all passing)

**MCP Wiring** ✅ (2026-07-02, 14:46–15:04 UTC)
- 23 new dispatch entries in `dispatch_memory.py`
- 23 PRAT Gana mappings in `prat_mappings.py`
- 11 NLU routing patterns in `meta_tool.py`
- 39 MCP wiring unit tests (`test_neuro_mcp_wiring.py`)

**Deep Integration** ✅
- PRAT sensorium now includes `neuro_cognitive` field (7 neuro signals in every MCP response)
- Citta cycle auto-injects `neuro_signals` from sensorium into each `CittaMoment`
- Sleep consolidation now runs replay + metaplasticity decay + ripple tag decay post-transfer

**Test Suite**: 3,622 unit tests passing, 15 skipped, 0 failures (102s)

**Gana Assignments**:
| System | Gana | Rationale |
|--------|------|-----------|
| Ripple tagging | gana_abundance | Memory selection for regeneration |
| Replay simulation | gana_abundance | Memory reactivation during consolidation |
| Neuromodulation | gana_dipper | Cognitive strategy / state regulation |
| Metaplasticity | gana_extended_net | Pattern connectivity / plasticity gating |
| Global workspace | gana_three_stars | Judgment / synthesis / broadcast |
| Neuro sensorium | gana_ghost | Introspection / self-model / citta |

### Remaining Work

1. ~~**Build PyO3 bindings**~~ ✅ Compiled and installed via `maturin develop --release` (2026-07-02 17:25 UTC). All three neuro-hotpath modules (ThalamicGate, PredictiveCoder, MomentumDynamics) now run on Rust.
2. ~~**Disinhibition model (Koka)**~~ ✅ Implemented `polyglot/bridges/koka/disinhibition.kk` + Python fallback `core/whitemagic/core/memory/disinhibition.py`. State machine: Wake → LightSleep → DeepSleep → REM with per-state galaxy gating weights.
3. ~~**Thalamic gating (Zig)**~~ ✅ Implemented `polyglot/bridges/zig/trn_gate.zig` + Python fallback `core/whitemagic/core/memory/thalamic_hard_gate.py`. Three-level cascade: TRN → Cortex → PFC with compile-time gate masks.
4. ~~**Homeostatic scaling**~~ ✅ Added `_homeostatic_scaling()` to `SleepConsolidation` — multiplicative edge renormalization toward target mean (0.5) after consolidation.
5. **Performance benchmarking** — Measure Rust vs Python fallback latency for hot-path modules (future session)

### ✅ Loose Ends Cleanup (2026-07-02, 17:20–17:27 UTC)

| Item | Status | Details |
|------|--------|---------|
| Registry definitions | ✅ Fixed | 23 authored `ToolDefinition` entries in `cognitive_extensions.py` with proper descriptions + input schemas. 0 stubs remaining. |
| E2E pipeline tests | ✅ Fixed | 19 end-to-end tests in `test_neuro_e2e_pipeline.py` — full classify → dispatch → handler → result round-trip |
| Citta persistence | ✅ Verified | `neuro_signals` field serializes/deserializes correctly; old streams without it load fine (defaults to `None`) |
| Tool catalog discovery | ✅ Verified | All 23 neuro tools appear in catalog with rich descriptions (249 authored definitions total, 606 tool definitions) |

**Test Suite**: 3,640 unit tests passing, 15 skipped, 1 pre-existing flaky failure (`test_polyglot.py` subprocess timeout), 0 new regressions (100s)

### ✅ Optional & Deferred Items Complete (2026-07-02, 17:31–17:43 UTC)

| Item | Status | Details |
|------|--------|---------|
| Homeostatic scaling | ✅ Implemented | `_homeostatic_scaling()` in `SleepConsolidation` — 5% renormalization toward mean 0.5 per cycle |
| Rust PyO3 compilation | ✅ Built & installed | `maturin develop --release` — `wm_neuro` extension with 3 classes, all Python wrappers now use Rust backend |
| Koka disinhibition | ✅ Implemented | `disinhibition.kk` (Koka bridge) + `disinhibition.py` (Python fallback) — 4-state machine with per-state galaxy weights |
| Zig thalamic hard gate | ✅ Implemented | `trn_gate.zig` (Zig bridge) + `thalamic_hard_gate.py` (Python fallback) — 3-level cascade with compile-time masks |
| Extension tests | ✅ 19 new tests | `test_neuro_extensions.py` — homeostatic scaling (3), disinhibition (6), TRN gate (5), Rust PyO3 (5) |

**Test Suite**: 3,656 unit tests passing, 15 skipped, 1 pre-existing flaky failure, 0 new regressions (137s)

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

---

## 8. Revised Plan — Post-Research Update (Jul 2026)

### 8.1 New Research Findings (Jul 2026)

The following papers were discovered after the original strategy document was written and inform the revised plan:

1. **Sleep Ripples Drive Single-Neuron Reactivation** (bioRxiv, Mar 2026) — First direct human evidence that ripple-driven reactivation supports episodic consolidation. Sleep ripples elicit stronger activation than wake ripples. Ripple-tagged memories should get stronger consolidation priority.

2. **Microcircuit Model for Replay Initiation/Termination** (bioRxiv, Jan 2026) — TORO cells release CCKBC inhibition → replay emerges. Short-term depression controls replay duration. Replay overrepresents reward-associated locations; replays terminating at reward are shorter.

3. **Predictive Associative Memory (PAM)** (arXiv, Feb 2026) — JEPA-style predictor trained on temporal co-occurrence retrieves associations that cross representational boundaries. Temporal shuffle ablation collapses cross-boundary recall by 90%.

4. **Hippocampo-Neocortical Interaction as Compressive RAG** (Nature Comms, Jun 2026) — Hippocampus = compressed episodic store → replayed to train neocortical generative network. Neocortex captures gist, extracts statistical patterns.

5. **Predictive Forgetting for Optimal Generalisation** (arXiv, Mar 2026) — Consolidation = predictive forgetting: selectively retain info that predicts future outcomes. High-capacity systems require iterative offline replay.

6. **Leakage & Second-Order Dynamics for RNN Replay** (arXiv, Feb 2026) — Hidden state leakage improves replay. Hidden state adaptation encourages exploration. Hidden state momentum enables temporally compressed replay.

7. **GATE: Hippocampal Working Memory Gating** (PLOS Comp Bio, 2026) — EC3→CA1→EC5→EC3 self-gating loop for selective memory maintenance. Multi-lamellar architecture yields multi-scale representations.

8. **Neuromimetic Metaplasticity for Continual Learning** (Neural Networks, 2025) — Distinct synapse types from stable to flexible, randomly intermixed. Robustness against data poisoning via selective filtering.

9. **"Theater of Mind" GWT for LLMs** (arXiv, Apr 2026) — 4-phase Cognitive Tick: Perceive/Retrieve → Think → Arbitrate → Update/Articulate. Core Self (static) + STM (dynamic) bifurcation. Event-driven broadcast.

10. **Homeostatic Synaptic Rewiring Forms Stable Engrams** (PLOS Comp Bio) — Homeostatic plasticity alone can form stable memories. Storage is fast, forgetting is slow. "Silent memories" stored in connectivity matrix.

### 8.2 Revised Interaction Topology

```
                                    ┌─────────────┐
                                    │   CITTA     │
                                    │  Sensorium  │
                                    │  Coherence  │
                                    │  DepthGauge │
                                    └──────┬──────┘
                                           ▲
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
              ┌─────┴─────┐         ┌──────┴──────┐        ┌──────┴──────┐
              │ NEUROMOD  │         │  GLOBAL     │        │  THALAMIC   │
              │ (Julia)   │────────►│  WORKSPACE  │◄───────│  GATING     │
              │ DA/5HT/ACh│         │  (Python)   │        │  (Rust PyO3)│
              └─────┬─────┘         └──────┬──────┘        └──────┬──────┘
                    │                      │                      │
                    ▼                      ▼                      │
              ┌─────────────┐       ┌─────────────┐               │
              │ PREDICTIVE  │       │  RIPPLE     │               │
              │ CODING      │──────►│  TAGGING    │◄──────────────┘
              │ (Rust PyO3) │       │  (Elixir)   │
              └──────┬──────┘       └──────┬──────┘
                     │                     │
                     ▼                     ▼
              ┌─────────────┐       ┌─────────────┐
              │ METAPLAST   │       │  REPLAY     │
              │ (Python+Rust)│◄─────│  SIM        │
              └──────┬──────┘       │  (Haskell)  │
                     │              └──────┬──────┘
                     ▼                     │
              ┌─────────────┐              │
              │ MOMENTUM    │              │
              │ DYNAMICS    │◄─────────────┘
              │ (Rust PyO3) │
              └──────┬──────┘
                     │
                     ▼
              ┌─────────────┐
              │ SPREADING   │
              │ ACTIVATION  │
              │ (existing)  │
              └──────┬──────┘
                     │
                     ▼
              ┌─────────────┐
              │ SLEEP       │
              │ CONSOLIDATION│
              │ (existing)  │
              └─────────────┘
```

**Data flow**: Thalamic gating runs on every tool call (sub-ms). Neuromodulation computes DA/5HT/ACh levels periodically. Predictive coding runs on every memory write. Ripple tagging listens async on GanYingBus. Replay runs during dream cycle. Metaplasticity runs during consolidation. Momentum runs on every spreading activation call. Global workspace broadcasts on every tool call.

### 8.3 Revised Language Assignments

**Key principle**: Polyglot bridges for batch/async systems, PyO3/Python for hot-path systems.

| System | Language | Rationale |
|--------|----------|-----------|
| Thalamic Gating | Rust PyO3 | Hot-path: runs on every tool call, sub-ms latency required |
| Predictive Coding | Rust PyO3 | Hot-path: runs on every memory write, needs SIMD |
| Momentum Dynamics | Rust PyO3 | Hot-path: runs on every spreading activation call |
| Metaplasticity | Python + Rust | Medium-path: runs during consolidation, Python orchestrates Rust compute |
| Ripple Tagging | Elixir (polyglot) | Async: event listener on GanYingBus, actor model ideal |
| Replay Simulation | Haskell (polyglot) | Batch: runs during dream cycle, pure functional for sequence traversal |
| Neuromodulation | Julia (polyglot) | Batch: periodic computation, scientific computing strengths |
| Global Workspace | Python (extend GanYingBus) | Hot-path: event broadcast, no subprocess overhead |
| Spreading Activation | Existing (Python + Rust) | Already implemented |
| Sleep Consolidation | Existing (Python) | Already implemented |

**Changes from original**: Zig → Rust PyO3 for thalamic gating (eliminates subprocess overhead on hot path). Go dropped for global workspace (GanYingBus already provides the broadcast mechanism in Python).

### 8.4 Persistence Strategy

| System | State | Storage | Lifetime |
|--------|-------|---------|----------|
| Thalamic Gating | Current mask | In-memory | Session |
| Neuromodulation | DA/5HT/ACh levels | `WM_STATE_ROOT/neuro/modulators.json` | Cross-session (snapshot every 5 min) |
| Predictive Coding | Prediction models | In-memory + SQLite sidecar | Session |
| Ripple Tagging | Tags + co-activations | SQLite sidecar table `ripple_tags` | Permanent |
| Replay Simulation | Replay trajectories | In-memory during dream cycle | Ephemeral |
| Metaplasticity | Per-memory plasticity | SQLite column `plasticity_score` | Permanent |
| Momentum Dynamics | Per-node momentum | In-memory | Session |
| Global Workspace | Current broadcast | In-memory + GanYingBus history | Session |
| Spreading Activation | Activation scores | In-memory | Per-call |

### 8.5 MCP Wiring — COMPLETED

The three existing cognitive systems are now wired into MCP tool dispatch:

**9 new tools registered:**
- `activation.spread` → `gana_winnowing_basket` (search/recall/priming)
- `activation.stats` → `gana_winnowing_basket`
- `gating.set_context` → `gana_dipper` (strategy/cognitive context)
- `gating.detect` → `gana_dipper`
- `gating.mask` → `gana_dipper`
- `gating.list` → `gana_dipper`
- `gating.stats` → `gana_dipper`
- `consolidation.run` → `gana_abundance` (regeneration/lifecycle)
- `consolidation.stats` → `gana_abundance`

**Files modified:**
- `core/whitemagic/tools/handlers/neuro_cognitive.py` — NEW: 9 handler functions
- `core/whitemagic/tools/registry_defs/cognitive_extensions.py` — 8 new ToolDefinition entries
- `core/whitemagic/tools/dispatch_memory.py` — 9 new dispatch entries
- `core/whitemagic/tools/prat_mappings.py` — 9 new PRAT mappings
- `core/whitemagic/tools/handlers/meta_tool.py` — 4 new NLU routing patterns
- `core/tests/unit/tools/test_neuro_cognitive.py` — NEW: 21 unit tests (all passing)

### 8.6 Revised Implementation Roadmap

**Phase 1: Polyglot Neuro-Upgrades (Batch/Async)**
1. Elixir ripple tagging bridge — GenServer + JSON stdio, GanYingBus listener
2. Haskell replay simulation — sequence traversal + STDP strengthening
3. Julia neuromodulation — DA/5HT/ACh computation, periodic batch

**Phase 2: Hot-Path Rust PyO3 Upgrades**
4. Thalamic gating — Rust PyO3 module, sub-ms galaxy access mask
5. Predictive coding — Rust PyO3, SIMD prediction error computation
6. Momentum dynamics — Rust PyO3, add momentum term to spreading activation

**Phase 3: Integration & Citta**
7. Metaplasticity — Python orchestrator + Rust compute, per-memory plasticity scores
8. Global workspace — extend GanYingBus with cognitive tick broadcast
9. Citta integration — sensorium injection, coherence auto-measure, depth gauge recovery
10. Cognitive integration testing — end-to-end pipeline tests

