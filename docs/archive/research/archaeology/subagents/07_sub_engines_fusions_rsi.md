<!-- Extracted from Antigravity CLI session 221fbb57-905f-4e7d-a4d3-3c11810ea0b7
     message e3ae12ee-cf82-4d3c-8f58-4baeeea47e99 | sender d4bb20b4-69c9-464e-98a2-af86fe4c8fbc | 2026-09-19T01:52:03.530084307Z
     Original title: Message from Engines, Fusions, and RSI Scout (research)
     Extracted 2026-09-21 by opencode; content unmodified. -->

# Comprehensive Research Report: Sub-Engines, Fusions, Army, Captains, and RSI across Gen1 and Gen2

**To**: Parent Agent (`221fbb57-905f-4e7d-a4d3-3c11810ea0b7`)  
**From**: Research Subagent  
**Date**: 2026-09-18  

---

## Executive Summary

Across the evolution of WhiteMagic from Gen1 (Python monolith with polyglot shims) to Gen2 (Rust modular crates in WMv9), the cognitive architecture transitioned from a sprawling taxonomy of 72+ distinct engine classes and procedural wiring files into a structured 28-fold alchemical cycle, guarded by formal token governance and powered by multi-core clone swarms.

This investigation answers all five targeted questions regarding the **44 Sub-Engines**, the **45KB `fusions.py` system**, the **RSI and Alchemical Round mechanics**, the **Army & Captains**, the **Violet security surface**, and how they cleanly translate into **Gen3 DAG transformations**.

---

## 1. The 44 Sub-Engines in Gen1: Capabilities, Registration, and Dispatch

### Architectural Context & The 72-Engine Mandala
In Gen1, the system was organized around a 28-fold mandala (corresponding to the 28 Lunar Mansions / 二十八宿, 28 Gardens, and 28 Grimoire chapters). However, the codebase contained **74 total `*Engine` classes**. To preserve the 28-fold celestial symmetry without abandoning functional code, WhiteMagic designated **28 Canonical Primary Engines** (slots 0–27 in `ENGINE_REGISTRY`) and organized the remaining engines into:
- **39 Absorbed Sub-Engines** (fused directly into canonical slots)
- **5 Affiliated Engines** (soft-associated utility engines)
- **Total Sub-Engines**: **39 + 5 = 44 Sub-Engines** (28 Primary + 44 Sub-Engines = **72 Engine Mandala**).

### Complete Inventory of the 44 Sub-Engines

#### The 39 Absorbed Sub-Engines
1. **CycleEngine** (Slot 14 / SessionEngine): Session lifecycle transitions and state loops.
2. **WuXingEngine** (Slot 14 / SessionEngine): Five-element energy balancing and phase tracking.
3. **ReconsolidationEngine** (Slot 12 / ConsolidationEngine): Updating existing memories upon retrieval in light of new evidence.
4. **_PyReplayEngine** (Slot 12 / ConsolidationEngine): Pure Python fallback for memory replay simulation.
5. **HeartEngine** (Slot 7 / NurturingEngine): Emotional valence, empathy resonance, and care-based preference learning.
6. **QuantumEngine** (Slot 25 / AccelerationEngine): Quantum-inspired Grover's $O(\sqrt{N})$ search and superposition fusions.
7. **QuantumGraphEngine** (Slot 25 / AccelerationEngine): Graph-specific quantum algorithms and Hamiltonian path search.
8. **ForecastEngine** (Slot 19 / IntrospectionEngine): Time-series hardware/software metric forecasting and depletion alerts.
9. **CapabilityDiscoveryEngine** (Slot 19 / IntrospectionEngine): Autonomous discovery and indexing of tools and capabilities.
10. **GrimoireEngine** (Slot 21 / ResilienceEngine): 12-phase dream cycle compilation into Grimoire spellbooks.
11. **GraphEngine** (Slot 26 / AssociationEngine): Association graph topology and node linkage.
12. **GraphEngineNeural** (Slot 26 / AssociationEngine): Spreading-activation neural graph traversals.
13. **GraphEngineCached** (Slot 26 / AssociationEngine): Fast in-memory cached graph queries.
14. **CodeGenomeEngine** (Slot 0 / ExportEngine): Code DNA sequencing, AST gene extraction, and template synthesis.
15. **PromptEngine** (Slot 0 / ExportEngine): Prompt template compilation and dynamic parameter hydration.
16. **PolymorphismEngine** (Slot 0 / ExportEngine): Multi-paradigm code mutation and environmental adaptation.
17. **ResonanceTransferEngine** (Slot 1 / ResonanceEngine): Cross-mansion harmonic energy transfer.
18. **JuliaResonanceEngine** (Slot 1 / ResonanceEngine): Non-linear oscillator dynamics via Julia acceleration.
19. **HRREngine** (Slot 17 / EmbeddingEngine): Holographic Reduced Representations (circular convolution/binding).
20. **QuantizedHRREngine** (Slot 17 / EmbeddingEngine): Quantized 8-bit HRR vectors for edge/embedded constraints.
21. **HRRCompositionEngine** (Slot 17 / EmbeddingEngine): Compositional semantic binding and bundle unrolling.
22. **DGAEngine** (Slot 9 / LifecycleEngine): Dynamic Galactic Architecture zone management and galaxy lifecycle.
23. **ContinuousEvolutionEngine** (Slot 27 / KaizenEngine): Continuous codebase mutation and refinement loops.
24. **MetaLearningEngine** (Slot 27 / KaizenEngine): Learning-to-learn optimization over dispatch strategies.
25. **ApotheosisEngine** (Slot 27 / KaizenEngine): Self-improvement velocity, mutation fitness, and apex convergence measurement.
26. **EnhancedPatternEngine** (Slot 23 / PatternEngine): Multi-galaxy high-order pattern discovery.
27. **SubClusteringEngine** (Slot 23 / PatternEngine): Micro-cluster decomposition within memory constellations.
28. **HolographicPatternEngine** (Slot 23 / PatternEngine): 4D/5D spatial pattern detection in holographic coordinate space.
29. **NarrativeEngineStory** (Slot 24 / NarrativeEngine): Thematic narrative arc and story chapter generation.
30. **ArtOfWarEngine** (Slot 5 / EthicsEngine): Strategic terrain assessment, tactical deception analysis, conflict avoidance.
31. **MaturityEngine** (Slot 5 / EthicsEngine): Developmental stage gating and ethical maturity escalation.
32. **ForesightEngine** (Slot 15 / PredictiveEngine): Multi-horizon scenario simulation and opportunity prediction.
33. **PredictiveMaintenanceEngine** (Slot 15 / PredictiveEngine): Database compaction, vacuum scheduling, index health forecasting.
34. **GreatYearEngine** (Slot 15 / PredictiveEngine): Precessional astronomical cycles and macro-temporal modulation.
35. **GalacticTelepathyEngine** (Slot 10 / GalacticEngine): Cross-process inter-galactic synchronization and state broadcasting.
36. **LocalReasoningEngine** (Slot 11 / CloneArmyEngine): On-device symbolic constraint satisfaction.
37. **CPUInferenceEngine** (Slot 11 / CloneArmyEngine): Quantized CPU-only local model inference.
38. **RuleEngine** (Slot 11 / CloneArmyEngine): Forward-chaining deterministic inference rules.
39. **NeuroScoreEngine** (Slot 6 / ForgettingEngine): Multi-signal memory retention scoring and decay curves.

#### The 5 Affiliated Engines
1. **SymbolicEngine** (Affiliated with Slot 16 / SerendipityEngine): Bilingual symbolic reasoning and conceptual cross-domain bridges.
2. **HologramEngine** (Affiliated with Slot 17 / EmbeddingEngine): 5D coordinate visual projection and rendering.
3. **PersonaEngine** (Affiliated with Slot 11 / CloneArmyEngine): Cognitive persona generation for Monte Carlo scenario simulations.
4. **MetaplasticityEngine** (Affiliated with Slot 6 / ForgettingEngine): BCM-inspired per-memory modification thresholds.
5. **InteractionEngine** (Affiliated with Slot 3 / SwarmEngine): Multi-agent simulated dialogues and agent negotiations.

### Registration and Dispatch Mechanics
- **Manifest Registration**: Defined in `whitemagic/core/engines/registry.py` inside `EngineEntry` dataclasses via `absorbs: tuple[str, ...]` and `affiliated_engines: tuple[str, ...]`.
- **Slot Mapping**: Each canonical engine had a fixed slot (0–27), with `handler_id = 100 + slot`. Lookups resolved via `get_engine_entry()`, `get_parent_engine()`, and `get_trio_for_tool()`.
- **Absorption Implementation Patterns**:
  1. *Compatibility Shims*: Legacy functions delegated directly to the parent orchestrator (e.g. `get_cycle_engine()` returned `SessionStartupOrchestrator`).
  2. *Inline Fusion*: Sub-engine logic was merged directly into the parent class (e.g. `ReconsolidationEngine` logic merged into `MemoryConsolidator`).
  3. *Lazy Accessors*: Parent engines initialized sub-engines on demand (e.g. `KaizenEngine._get_evolution_engine()`).
  4. *Standalone Singletons*: Sub-engines ran as independent singletons with their own tools, but were conceptually bound to their parent slot in the manifest for circuit breaker and governance accounting.
- **Dispatch Flow**:
  1. The PRAT (Predecessor-Resonance-Action-Transition) router received a tool call.
  2. `prat_mappings.py` routed the tool to one of 28 Ganas.
  3. Ganas mapped 1:1 to Gardens and canonical Engines.
  4. The engine read its shared-memory **StateBoard slot** (slots 0–27) to evaluate circuit breakers, failure counters, and Wu Xing / Guna harmony states before executing.

---

## 2. Gen1 `fusions.py` (45KB System): Pipeline Composition & Emergent Wiring

`whitemagic/core/fusions.py` was a 1,354-line, 45KB emergent cross-system wiring framework. Its core doctrine was: **"Connect two or more subsystems so that System A's output feeds into System B, creating capabilities neither possesses alone."**

### Pipeline Composition Patterns in `fusions.py`
The file implemented **28 cross-system fusions** (tracked in `capability_matrix.py` to match the 28 Ganas). Key compositions included:

1. **Self-Model Energy Forecast $\to$ Dream Scheduling (`check_proactive_dream`)**:
   - The predictive self-model monitored energy depletion trends. If energy was projected to drop below critical thresholds within 15 minutes, it proactively initiated background memory consolidation dreaming before system fatigue set in.
2. **Wu Xing Phase $\to$ Gana Dispatch Amplification (`get_wuxing_quadrant_boost`)**:
   - Evaluated the current dominant elemental phase (Wood, Fire, Earth, Metal, Water) from `WuXingEngine` and dynamically boosted the confidence and execution priority of tools belonging to that quadrant.
3. **PRAT Resonance $\to$ Emotion/Drive Core (`modulate_drive_from_resonance`)**:
   - Sequential tool calls modulated the agent's internal drive state (Curiosity, Satisfaction, Caution, Energy). E.g., Eastern quadrant tools boosted Curiosity (+0.03); repeated invocations in the same quadrant amplified mood changes by $1.5\times$.
4. **Zodiac Council $\to$ Grimoire Spells (`get_zodiac_spell_boost`)**:
   - The active Zodiac sign in the ZodiacCouncil mapped its astrological element to Wu Xing, boosting matching Grimoire spells by +20% confidence.
5. **Bicameral Reasoner $\to$ Memory Consolidation (`bicameral_consolidation_enhance`)**:
   - Left hemisphere handled exact tag-overlap clustering. The right (intuitive) hemisphere performed cross-domain semantic leaping, proposing merges between clusters that shared zero tags but had strong thematic resonance.
6. **Salience Arbiter $\leftrightarrow$ Homeostatic Loop (`salience_homeostasis_sync`)**:
   - *Direction 1*: High-salience alerts ($>0.8$) immediately triggered homeostatic health diagnostics.
   - *Direction 2*: Degraded system health ($<0.4$) increased salience sensitivity (lowering detection thresholds by 20%), making the system hyper-vigilant when stressed.
7. **Adaptive Gana Chains via Harmony Vector (`gana_chain_harmony_adapt`)**:
   - Gana chain execution depth dynamically adapted to runtime health: Tamasic/stressed states truncated chains by $66\%$ to conserve compute; Sattvic/healthy states allowed full chains plus bonus reasoning steps.
8. **Multi-Runtime Bridges**:
   - `elixir_event_bridge()`: Bridged events between Elixir's OTP 3-lane actor bus (FAST/MEDIUM/SLOW) and Python's Gan Ying bus.
   - `mesh_memory_sync()`: Coordinated cross-node P2P memory synchronization over the Go libp2p mesh.

All fusions broadcast structured telemetry events onto the **Gan Ying bus** (`emit_fusion_event`), creating a pervasive feedback loop across otherwise decoupled modules.

---

## 3. Gen2 RSI Engine (`rsi.rs`), Alchemical Rounds (`alchemical_round.rs`), and Mutation Evaluation

In Gen2 (Rust WMv9), the Python sprawl was refactored into high-performance, strongly-typed crates:

### A. The RSI Engine (`crates/wm-tools/src/expansion/rsi.rs` — 2,475 lines)
RSI operated across three distinct, bounded phases:

- **Phase 1: Friction Logging (Telemetry vs. Cognition Isolation)**:
  - Tools: `friction.log`, `friction.auto_log`, `friction.review`, `friction.resolve`.
  - **Two Homes Principle**: Manual friction logged by humans (`friction.log`) wrote cognitive reflections to the **Codex** galaxy. Automated dispatch errors and performance anomalies (`friction.auto_log`) wrote evidence to the **Telemetry** galaxy.
  - **Evidence Ceiling**: Telemetry memories were clamped to `IMPORTANCE_CEILING = 0.4` and excluded from ordinary recall by design, guaranteeing that system diagnostics never crowded out working knowledge.
  - **Rich Telemetry Envelope (`DispatchTelemetry`)**: Captured 15+ execution dimensions (latency, error snippet, brain wave, effectiveness, karma debt, self-model confidence, Citta coherence, citta valence, arg/response sizes).
  - **Deduplication Hash**: `friction_hash(tool, category, severity, error)` tagged memories with `rsi:hash:{hash}` and incremented an `rsi:dup:<count>` counter.
  - **Regression Escalation (WS-5)**: If an error recurring with an existing hash had previously been marked `rsi:resolved`, the engine flagged it as an active regression (`rsi:regression`), escalating its severity level (low $\to$ medium $\to$ high $\to$ critical).

- **Phase 2: Codebase-Grounded Improvement Cycles (`improve.proposals`)**:
  - Invoked `AutonomousCycleRunner::run_cycle(CycleType::Improve)`.
  - Scanned Codex and Telemetry for recurring friction patterns ($\ge 2$ entries or weighted duplicate count $\ge 3$).
  - Grouped friction by category (`error`, `performance`, `ux`, `missing_feature`, `confusing`) and target tool.
  - Generated structured `ImprovementProposal` records with concrete recommended code/architecture fixes.
  - **Anti-Circular Protection**: Bounded by `SpiralTracker` and deduplication signatures (`{category}:{target}:{severity}`); proposals with existing active signatures were suppressed.

- **Phase 3: Adversarial Self-Testing (`redteam.proposals`, `redteam.from_friction`, `redteam.coverage_report`)**:
  - The system generated adversarial test proposals against its own core systems (governance, karma, isolation, memory).
  - `redteam.from_friction` automatically converted resolved friction entries and regressions into permanent regression test pseudocode.

### B. The 28-Engine Alchemical Transmutation Round (`alchemical_round.rs`)
In `crates/wm-cognitive/src/alchemical_round.rs`, the 28 primary intelligence engines were cataloged and organized into the **Four Classical Stages of Cognitive Transmutation** (7 engines per stage):

1. **Nigredo (The Blackening / Water / North / Citta Perception)**:
   - *Slots 0–6*: `KaizenEngine`, `EpistemicTagger`, `WorkingMemory`, `PreExecutionSimulator`, `CausalNet`, `ConfidenceLearner`, `LightNER`.
   - *Focus*: Decay, friction detection, error auditing, bounded attention, causal graph inference.
2. **Albedo (The Whitening / Metal / West / Citta Contemplation)**:
   - *Slots 7–13*: `CoordinateEncoder`, `ConstellationSearch`, `HolographicConsolidator`, `AttractorManager`, `KnowledgeGraphV2`, `HexagramVectors`, `CodeStructureGraph`.
   - *Focus*: Purification, 5D spatial matrix projection, hypercube search, memory clustering, AST call hierarchy mapping.
3. **Citrinitas (The Yellowing / Wood / East / Citta Action)**:
   - *Slots 14–20*: `SerendipityEngine`, `CrossDomainDetector`, `CorpusCallosumBus`, `SectorSynthesizer`, `ParallelReasoningTree`, `SkillForge`, `JITResearcher`.
   - *Focus*: Solar dawn, associative leaps, dialectical debate arbitration, tree-of-thought exploration, skill compilation.
4. **Rubedo (The Reddening / Fire / South / Citta Reflection)**:
   - *Slots 21–27*: `ApotheosisEngine`, `PrescienceEngine`, `PhylogeneticTracker`, `SelfModel`, `AlchemicalLoop`, `GrimoireEngine`, `CognitiveModes`.
   - *Focus*: Coagulation, hardening, self-model calibration, entropy forecasting, taxonomic lineage tracking, behavioral mode switching.

*The 24 Slots Context*: While the alchemical matrix contains **28 contiguous slots (0..27)**, slot 24 is specifically `SelfModel` (predictive introspection of capability boundaries and failure modes). In governance (`firebreak.rs`), 24 represents the hard-coded baseline command rules; in `funnel.rs`, 24 is the maximum reference token capacity; and across the cosmic calendar, 24 represents the Solar Terms (二十四節氣) that modulate seasonal behavior alongside the 28 mansions.

### C. Mutation Evaluation Protocol
WhiteMagic enforced strict safety protocols for self-modification:
1. **Proposal-Only Autonomous Boundary**: Autonomous cycles (`AutonomousCycleRunner`) strictly produced actionable proposals (`ImprovementProposal`, `RedteamProposal`), never direct code or state mutations (`requires_human_review(Improve) == true`).
2. **Pre-Execution Simulation**: Engine slot 3 (`PreExecutionSimulator`) simulated blast radius, filesystem changes, and invariant violations before any destructive operation could run.
3. **Atomic Read-Modify-Write**: Memory and governance ledger mutations required lockfile-guarded atomic transactions (`wm-tools/src/expansion/coordination.rs`).
4. **Apotheosis Metric Evaluation**: Engine slot 21 (`ApotheosisEngine`) evaluated mutation velocity, mutation fitness, and test regression stability.
5. **State Hardening**: Invariant verification in Rubedo ensured that self-modifications did not degrade system coherence or trigger security firebreaks.

---

## 4. The "Army" (`army.rs`), "Captains" (`captains.rs`), and "Violet" (`violet.rs`)

### A. The Army (`crates/wm-tools/src/expansion/army.rs` — 1,292 lines)
- **Title**: *Tokio Clone Army & Galactic Triage Engine (PSR-005 / Operation Legion Heir)*.
- **Concept**: Multi-core parallel execution harness leveraging Tokio async worker tasks and Rayon parallel iterators to deploy thousands of parallel computational "clone soldiers."
- **Formations (`ArmyType`)**: Defined 6 formations: `FileSearch`, `GalacticTriage`, `ShadowConsensus`, `GeneseedMiner`, `BatchPipeline`, `ThoughtPulse`.
- **Anti-Simulation Invariant**: Strict architectural honesty was enforced in code. Only `FileSearch` had an active parallel Rayon engine (`scan_directory_parallel`). Calling any other formation returned a hard error redirecting the user to the real specialized tool (e.g., `galaxy.triage_sweep` or `geneseed.mine`), with the explicit doctrine: *"A completion receipt must never be issued for work that did not happen."*
- **Tools**: `army.deploy`, `galaxy.triage_sweep`, `galaxy.cold_rotate`.

### B. The Captains (`crates/wm-tools/src/expansion/captains.rs` — 953 lines)
- **Title**: *Subagent Captains & Platoon Orchestration (Operation Legion Heir Phase 2)*.
- **Concept**: Autonomous subagent commanders leading platoons of clone soldiers on specialized cognitive operations.
- **Four Captain Roles** (modeled on Sun Tzu's *Art of War* and Hongmen numerical ranks):
  1. **Vanguard (Feng / Wind)**:
     - *Doctrine*: *"Swift as the Wind: Rapid multi-threaded traversal and reconnaissance."*
     - *Hongmen Code*: 438 (先鋒 Sin Fung / Incense Master).
     - *Operation*: Parallel AST and file reconnaissance across the workspace using Rayon.
  2. **Sentry (Lin / Forest)**:
     - *Doctrine*: *"Silent as the Forest: Immutability, boundary checks, and Dharma audit."*
     - *Hongmen Code*: 426 (紅棍 Hung Kwan / Red Pole Commander).
     - *Operation*: Memory galaxy integrity auditing, boundary defense, source trust verification.
  3. **Alchemist (Huo / Fire)**:
     - *Doctrine*: *"Fierce as Fire: Transmutation of commits and turns into golden insight."*
     - *Hongmen Code*: 415 (白紙扇 Pak Tsz Sin / White Paper Fan Strategist).
     - *Operation*: Geneseed pattern mining, high-salience knowledge extraction across galaxies.
  4. **Cartographer (Shan / Mountain)**:
     - *Doctrine*: *"Steadfast as the Mountain: Structuring multidimensional semantic space."*
     - *Hongmen Code*: 432 (草鞋 Cho Hai / Straw Sandal Navigator).
     - *Operation*: 5D holographic spatial rebalancing and dimensional dispersion (breaking the $(0.5, 0.5, 0.5)$ spatial cluster singularity).
- **Tools**: `captain.deploy`, `hologram.rebalance`, `hologram.query`.

### C. Violet (`crates/wm-tools/src/expansion/violet.rs` — 577 lines)
- **Title**: *Violet Security Surface (Edgerunner Violet Security Layer)*.
- **Concept**: The cryptographic authorization and integrity layer for offensive security, penetration testing (PoC pipeline), red-team engagements, and model artifact signing.
- **Core Security Surface**:
  1. `violet.engagement.issue`: Issues Ed25519-signed scope-of-engagement tokens (`EngagementToken`) bound to the SHA-256 hash of the explicit Rules-of-Engagement (ROE) text, with defined scope (`Poc`, `Redteam`, `Demo`, `Custom`) and TTL.
  2. `violet.engagement.validate`: Performs stateless cryptographic validation of tokens (verifying signature, checking revocation, confirming expiration, and asserting ROE hash match).
  3. `violet.engagement.revoke`: Explicitly revokes active engagement tokens.
  4. `model.sign`: Ed25519-signs artifact and model weights manifests (`ModelSignature`), binding them to nonces and ROE hashes.
  5. `model.verify`: Validates artifact signatures and SHA-256 content hashes prior to loading.
- **Key Persistence**: Backed by secure 0600-permission seed files (`violet_issuer.key`, `violet_signer.key`), ensuring cryptographic identities survive process restarts without leaking private keys.

---

## 5. Architectural Compilation into Gen3: Pure DAG Transformations

### The Problem: Monolithic Subsystem Sprawl
In Gen1, the architecture suffered from "subsystem sprawl": 72 class hierarchies, singletons, circular import guards, and 45KB procedural wiring scripts (`fusions.py`). In Gen2, although Rust brought type safety and speed, tools were still wrapped in procedural dispatch handlers, ad-hoc loop runners, and distinct tool structs.

### The Gen3 Solution: Idempotent Functional DAG Transformations
Gen3 can completely absorb all capabilities of the 44 sub-engines, fusions, army, captains, and RSI by decomposing them into a unified **Directed Acyclic Graph (DAG)** compute model:

```
[Input Stream / Trigger] 
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Nigredo Stage (Audit & Perception Nodes)                 │
│    • LightNERNode (Text -> Tokens)                          │
│    • FrictionDetectNode (Error/Latency -> TelemetryRecord)  │
│    • PreExecutionSimNode (Plan -> InvariantCheck)           │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Albedo Stage (Purification & Spatial Topology Nodes)     │
│    • CoordinateEncodeNode (Record -> 5D Point)              │
│    • SpatialClusterNode (Points -> Centroids)               │
│    • KnowledgeGraphNode (Entities -> TypedEdges)            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Citrinitas Stage (Synthesis & Reasoning Nodes)           │
│    • SerendipityNode (Dormant Cross-Bridges)                │
│    • DialecticNode (Thesis + Antithesis -> Synthesis)       │
│    • SkillForgeNode (Frequent Patterns -> SkillRecipe)      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Rubedo Stage (Reflection, Hardening & Governance Nodes)  │
│    • InvariantHardeningNode (Validation)                    │
│    • TokenGateNode (Violet Cryptographic Authorization)     │
│    • KarmaLedgerNode (Append Audit Log)                     │
└─────────────────────────────────────────────────────────────┘
```

### Architectural Principles for Gen3 Compilation

1. **Engines as Stateless Transform Nodes**:
   - Discard stateful `*Engine` classes. Replace them with pure, re-entrant transform functions: `(InputContext, Data) -> Result<OutputData, NodeError>`.
   - E.g., `CoordinateEncoder` is a node mapping `Memory -> MemoryWith5D`. `PreExecutionSimulator` is a filter node validating state invariant safety.

2. **Fusions as Graph Topologies (Edge Declarations)**:
   - Eliminate `fusions.py`. Cross-system emergent capabilities are represented naturally by **wiring the output stream of Node A into Node B**:
     - *Proactive Dreaming Fusion*: `EnergyForecastNode -> ThresholdFilter(<0.3) -> DreamTriggerNode`.
     - *Salience Homeostasis Fusion*: `SalienceNode -> Branch(if >0.8 then HealthCheckNode)`.
   - Fusions become declarative pipeline definitions in TOML or code DAG builders, with zero custom glue code.

3. **Captains as Parameterized Execution Recipes**:
   - The Captains are not separate agent entities; they are **canonical DAG pipeline presets**:
     - *Vanguard Pipeline*: `DirectoryWalkNode |> ParallelTextScanNode |> FilterNode`.
     - *Sentry Pipeline*: `GalaxyScanNode |> ProvenanceCheckNode |> TrustRatingNode`.
     - *Alchemist Pipeline*: `MemoryScanNode |> SalienceFilter(>0.7) |> PatternMineNode`.
     - *Cartographer Pipeline*: `5DCoordinateScanNode |> DispersionCalcNode |> SpatialUpdateNode`.

4. **The Army as the Parallel DAG Runtime**:
   - The "Tokio Clone Army" is not a business logic domain; it is the **underlying multi-threaded DAG scheduler** (using Rayon for data-parallel operations and Tokio for async I/O). The user simply executes a DAG with `.execute_parallel(worker_count)`.

5. **RSI as a Self-Modifying Meta-DAG**:
   - Friction logging is implemented as an observability hook / sink on every DAG execution node.
   - When friction reaches threshold density, the scheduler triggers the `ImprovementScan` pipeline.
   - The output of the RSI pipeline is a **proposed DAG patch**, which passes through a mandatory `HumanApprovalBarrierNode` before being applied to the active pipeline catalog.

6. **Violet as Guard Nodes in the Pipeline**:
   - `Violet` authorization becomes a pre-condition guard node (`VioletGateNode(scope, roe_hash)`) placed upstream of any high-risk DAG mutation node. Execution halts automatically if the token signature is missing or invalid.

### Summary Comparison Table

| Dimension | Gen1 (Python v26) | Gen2 (Rust WMv9) | Gen3 (DAG Target) |
|---|---|---|---|
| **Engine Architecture** | 72+ classes, 28 canonical slots, 44 absorbed/affiliated sub-engines | 28 `EngineProfile` catalog entries in 4 alchemical stages | Stateless, composable DAG Transform Nodes |
| **Cross-System Fusions** | 45KB procedural `fusions.py` script (28 hard-coded functions) | Ad-hoc cross-crate function calls & workspace events | Declarative graph edges connecting node outputs to inputs |
| **Self-Improvement (RSI)** | Conceptual / dispersed | 3-Phase RSI (`rsi.rs`), Telemetry galaxy, deduplication & regressions | Automated telemetry sink $\to$ RSI pipeline $\to$ DAG patch proposals |
| **Concurrency / Army** | Simulated single-threaded / threading shims | 6 Army types, Rayon file search, anti-simulation enforcement | Multi-threaded Rayon/Tokio DAG execution runtime |
| **Specialized Agents** | 28 Garden personalities | 4 Captain roles (Vanguard, Sentry, Alchemist, Cartographer) | Pre-configured pipeline recipes / subgraphs |
| **Security & Governance** | Basic Dharma rule checks | Edgerunner Violet (Ed25519 tokens & model signing) | Cryptographic `TokenGateNode` pipeline barriers |

---
*Report complete. All files examined and cross-referenced.*
