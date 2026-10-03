<!-- Extracted from Antigravity CLI session 221fbb57-905f-4e7d-a4d3-3c11810ea0b7
     message 3bda1ae3-93f5-4aa6-9b59-e4f3e62c0fa5 | sender 359fce94-e353-48a2-9498-d1a403528c0d | 2026-09-19T01:35:32.061203619Z
     Original title: Message from Dream and Citta Scout (research)
     Extracted 2026-09-21 by opencode; content unmodified. -->

# Comprehensive Investigation: Dream Cycle, Memory Consolidation, and Citta Trajectories Across Gen1, Gen2, and Gen3

**To:** Parent Agent  
**From:** Research Subagent  
**Subject:** Deep Analysis of Gen1 vs Gen2 Cognitive Architectures and Gen3 Continuous Regime Trajectory  

---

### Executive Summary

We have conducted a thorough, line-by-line inspection of the memory consolidation, dreaming, and Citta consciousness systems across WhiteMagic Gen1 (`og_whitemagic/core`) and Gen2 (`WMv9/crates/wm-cognitive`). We also examined historical autopsy records (`v2-autonomous-activity-investigation-2026-08-01.md`, `v4-governed-autonomy-plan-2026-08-01.md`, `LINEAGE_LEDGER.md`).

Below are the exhaustive answers to the four core research questions.

---

### 1. The Sequence of Phases and Concrete Mathematical Operations: Gen1 (13 Phases) vs Gen2 (12 Phases)

#### A. Gen1: 13 Dream Phases (`dream_cycle.py`, lines 45–63, 351–1634)
In Gen1, the dream cycle was executed as an idle-triggered asynchronous rotation over 13 discrete phases:

1. **`TRIAGE` (Phase 0 / NREM Stage 1 equivalent)**:
   - *Auto-Tagging*: Heuristic keyword classification over untagged memories (snippet & title scanning for terms like `session`, `aria_era`, `architecture`, `wisdom`, `technical`).
   - *Auto-Archive Metric*: Queries memories where:
     $$\text{importance} < 0.2 \land \text{access\_count} < 2 \land \text{galactic\_distance} < 0.6 \land \text{is\_protected} = 0 \land \text{neuro\_score} < 0.3$$
     Pushes galactic distance outward: $d_{\text{new}} = \min(0.8, \max(d_{\text{current}} + 0.15, 0.7))$.
   - *Coordinate Drift Correction*: Protected core memories drifting outward ($d > 0.1$) are snapped back: $d \leftarrow 0.0$.
   - *Orphan Cleanup & Dedup*: Removes orphaned holographic coordinates/associations; invokes `resolve_entities(similarity_threshold=0.92, batch_limit=100)`.

2. **`CONSOLIDATION` (Hippocampal Replay & Clustering)**:
   - *Rust MinHash & Content Consolidation Pre-pass*: Calls `whitemagic_rs.consolidate_memories_from_content(mem_tuples, top_n=20, similarity_threshold=0.3)` and MinHash LSH (`minhash_find_duplicates(threshold=0.4)`).
   - *Tag-Overlap Greedy Agglomeration*: Computes shared tag intersections $S = \bigcap_{m \in C} \text{tags}(m)$. Clusters where $|C| \ge 3$, $\overline{\text{importance}} \ge 0.4$, and $\sum \text{access\_count} \ge 3$ trigger strategy synthesis.
   - *Strategy Synthesis & Promotion*: Synthesizes `consolidated_strategy` memory with boosted importance:
     $$\text{importance}_{\text{strategy}} = \min(1.0, \overline{\text{importance}} + 0.15)$$
   - *Bicameral Cross-Cluster Bridges*:
     - Logical bridges: $C_1 \text{ and } C_2$ sharing tags ($C_1.\text{tags} \cap C_2.\text{tags} \ne \emptyset$).
     - Creative bridges: Emotional resonance ($\overline{v}_1 > 0.5 \land \overline{v}_2 > 0.5$ with no tag overlap) OR importance contrast ($|\overline{\text{imp}}_1 - \overline{\text{imp}}_2| > 0.3$).
   - *High-Value Short-Term Promotion*: Memories with $\text{type} = \text{SHORT\_TERM}$, $\text{importance} \ge 0.6$, and $\text{access\_count} \ge 3 \implies \text{LONG\_TERM}$, $\text{importance} \leftarrow \min(1.0, \text{importance} + 0.05)$.
   - *Galactic Promotion*: Consolidated strategy memories are pulled inward to `galactic_distance = 0.12` (`INNER_RIM`).
   - *Julia Drift Detection*: Invokes `julia_detect_galaxy_drift` comparing baseline vs current distributions of importance and distances.

3. **`SERENDIPITY` (Bridge Synthesis & Graph Topology)**:
   - *Topological Bridge Detection*: Rebuilds graph up to 20,000 memories; computes betweenness/degree bridges connecting disconnected communities (`find_bridge_nodes(top_n=5)`).
   - *Cross-Domain Collision Detection*: Finds memory pairs with high behavioral similarity but low semantic similarity.
   - *Association Mining*: Samples 100 memories, computes keyword Jaccard overlap, and creates cross-galaxy associative links.

4. **`GOVERNANCE` (Echo Chamber Detection & Inhibition)**:
   - *Eigenvector Centrality Snapshot*: Compares centrality snapshots $T_{\text{now}}$ vs $T_{\text{prev}}$.
   - *Echo Chamber Invariant*: Flags nodes where centrality spiked by $> 2\sigma$ without proportional external memory ingestion.
   - *Edge Inhibition*: Weakens reinforcing edges in echo chambers:
     $$\text{strength} \leftarrow \text{strength} \times 0.5 \quad (\text{for } \text{strength} > 0.1)$$
   - Writes record to `KarmaLedger`.

5. **`NARRATIVE` (Episodic Narrative Compression)**:
   - Groups temporally contiguous, tag-similar memories and compresses them via `NarrativeCompressor` into episodic story arcs to eliminate fragmentation.

6. **`KAIZEN` (Emergence Scanning & Pattern Analysis)**:
   - *Emergence Scan*: Scans via `EmergenceEngine`, stores emergence insights with $\text{importance} = 0.5 + 0.3 \times \text{confidence}$.
   - *Constellation Auto-Merge*: Merges constellations with $\text{distance} \le 0.5 \land \text{shared\_tags} \ge 2$.
   - *Harmony Vector Checks*: Monitors error rate ($> 0.1$), energy ($< 0.3$), karma debt ($> 0.2$), and Yin-Yang balance ($< 0.3$).
   - *Neuro-Score Decay Hints*: Samples memories and calculates neuro-scores; flags items where $\text{final\_score} < 0.3$.
   - *Recursive Improvement Loop*: Runs hypothesis generation cycle (`ImprovementLoop.run_cycle`).

7. **`ORACLE` (Bayesian Prediction & Grimoire Casting)**:
   - Queries `TemporalForecastDB` for `brier_score` and `calibration_gap`.
   - *Bayesian Calibration Shift*:
     $$\Delta_{\text{Bayes}} = \text{calibration\_gap} \times 0.3$$
     $$\text{conf}_{\text{adjusted}} = \text{clamp}(0.01, 0.99, \text{conf}_{\text{raw}} + \Delta_{\text{Bayes}})$$
   - Generates contextual spells and guidance suggestions.

8. **`DECAY` (Mindful Forgetting / Galactic Rotation)**:
   - Evaluates multi-signal retention:
     $$\text{Composite} = \frac{\sum w_i s_i}{\sum w_i}$$
     where signals comprise:
     - Semantic ($w=1.0$, memory importance)
     - Emotional ($w=0.8$, $\max(|\text{valence}|, \text{weight})$)
     - Recency ($w=0.9$, half-life decay: $0.5^{\frac{\Delta t_{\text{days}}}{t_{1/2}}} + \min(0.3, 0.05 \ln(1 + \text{recalls}))$)
     - Connection ($w=0.7$, $\min(1.0, \frac{N_{\text{links}}}{10} \times \overline{\text{strength}})$)
     - Protection ($w=100.0$, hard override if pinned/protected/sacred/core).
   - *Actions*: Composite $\ge 0.35 \implies \text{keep}$; $0.15 \le \text{Composite} < 0.35 \implies \text{decay}$; $< 0.15 \implies \text{archive}$ (rotated to edge $d = 0.90$, $\text{neuro\_score} \leftarrow \max(\text{min\_score}, \text{neuro\_score} \times 0.5)$, **never deleted**).

9. **`CONSTELLATION` (Auto-Merge Analysis)**:
   - Measures member overlap between detected constellations; if $|C_1 \cap C_2| > 0.5 \times |C_1|$, marks them for merging.

10. **`PREDICTION` (Predictive Drift Detection & Oracle Resolution)**:
    - Identifies drifting high-value memories:
      $$\text{drift\_risk} = \min\left(1.0, d_{\text{galactic}} \times (1.0 - 0.1 \times \text{access\_count})\right)$$
      Memories with $\text{drift\_risk} > 0.6$ are flagged for active recall.
    - Resolves stale pending oracle claims (> 30 days) against memory evidence (marking validated or falsified).

11. **`ENRICHMENT` (Entity Extraction & Polyglot Seed Benchmarking)**:
    - Regex pattern matching: file paths, semver versions, tool names, python modules, rust crates.
    - Auto-tags with `entity:<type>`.
    - Benchmarks SIMD cosine similarity (Rust vs Python) over 50 iterations; computes fitness score:
      $$\text{fitness} = \text{score}_{\text{zone}} + \text{score}_{\text{build}} + \text{score}_{\text{verify}} + \min\left(1.0, \frac{\text{speedup}}{100}\right) \times 0.15$$

12. **`HARMONIZE` (Wu Xing Galactic Zone Balance)**:
    - Maps 5 galactic zones to Wu Xing: Core $\to$ Earth, Inner Rim $\to$ Metal, Mid Rim $\to$ Water, Outer Rim $\to$ Wood, Fringe $\to$ Fire.
    - Target distribution: $\text{ideal} = 0.20$ (20% per element).
    - Mathematical balance metric:
      $$\text{Harmony} = \max\left(0.0, \min\left(1.0, 1.0 - \frac{\sum_{i=1}^5 |p_i - 0.20|}{5 \times 0.20}\right)\right) = 1.0 - \sum_{i=1}^5 |p_i - 0.20|$$

13. **`CODE_GRAPH` (Code Structure Graph Analysis — Added in v24.3)**:
    - Analyzes symbol dependency graph:
      - God nodes: Symbols with $\text{degree} > 15$.
      - Tightly coupled communities: Clusters with $\text{size} > 20$.
      - Code-memory cross references: Tracks `discussed_in` edges.
    - Persists hypotheses directly to the `dreams` galaxy.

---

#### B. Gen2: 12 Dream Phases (`crates/wm-cognitive/src/dream.rs`)
In Gen2, the dream cycle was completely rewritten in Rust as a sequential 12-phase pipeline executed exclusively when the brain-wave state drops to **`Theta`** (sleep consolidation):

1. **`Triage`**:
   - Scans up to 10,000 memories across all active non-system galaxies.
   - Classifies memories into buckets: High ($\text{imp} \ge 0.7$), Medium ($0.3 \le \text{imp} < 0.7$), Low ($\text{imp} < 0.3$).

2. **`Consolidation`**:
   - *Strategy Synthesis*: `StrategySynthesizer` clusters memories and generates structured meta-insights.
   - *Sleep Consolidation Transfer Routes*: Transfers important memories across galaxies:
     - `Sessions → Codex` (min importance 0.6)
     - `Citta → Aria` (min importance 0.6)
     - `Dreams → Research` (min importance 0.5)
     - `Universal → Codex` (min importance 0.6)
     - **Dream Hygiene Guard**: Explicitly drops telemetry, friction logs, and raw noise records via `mem.is_telemetry_or_noise()`.
   - *Content Deduplication*: `find_by_content_hash` and `put_dedup`; within-galaxy dedup deletes newer duplicates with identical content hashes.
   - *Tier Ladder Sweep (`tier_sweep`)*: Strictly paced (at most **one** tier transition per memory per dream cycle):
     - $\text{Working} \to \text{Episodic}$: if $\text{age\_days} \ge 1.0$ (`WORKING_TTL_DAYS`).
     - $\text{Episodic} \to \text{Semantic}$: if $\text{reads} \ge 5$ (`SEMANTIC_MIN_READS`) $\land$ $\text{importance} \ge 0.7$ (`SEMANTIC_MIN_IMPORTANCE`).
     - $\text{Any} \to \text{Archival}$: if $\text{age\_days} \ge \text{half\_life\_days} \land \text{importance} < 0.3 \land \neg \text{is\_protected}$.
   - *Validity Sweep (`validity_sweep`)*: Gated by `WM_VALIDITY_SWEEP=1`. Derives validity states from the graph: if an active record has an outgoing `Supersedes` edge ($M \to T$), $M$ transitions to $\text{Superseded}\{\text{by}: T\}$.
   - *Autonomous Smarana Step*: Hebbian synaptic consolidation and association reinforcement.

3. **`Serendipity`**:
   - Runs `AssociationMiner::default_config()`. Extracts top 5 keywords per memory, evaluates pairwise Jaccard overlap, and inserts cross-galaxy associative edges into LMDB.

4. **`Governance`**:
   - Invariant validation across all non-system galaxies:
     - Clamps out-of-bounds importance: $\text{imp} \leftarrow \text{clamp}(0.0, 1.0, \text{imp})$.
     - Checks empty content.
     - Temporal consistency: if $\text{accessed\_at} < \text{created\_at} \implies \text{accessed\_at} \leftarrow \text{created\_at}$.
     - Batch writes via `put_batch`.

5. **`Narrative` (S7 Distillation Engine)**:
   - *Deterministic Session Digest (LLM-Free)*: Groups turn records into chronological session files.
     - Evidence Prior calculation:
       $$\text{importance} = \text{clamp}\left(0.0, 1.0, 0.4 + 0.03 \cdot \min(|T|, 10) + 0.2 \cdot \overline{\text{importance}}\right)$$
   - *Question-Addressed Topic Summaries*: Groups turns by topic, computes FNV-1a fingerprint, skips unchanged evidence to eliminate rewrite churn.
   - *Yama Admission Gate*: Every distillation write is evaluated through `ctx.yama_admit()`. Because execution is in `Theta` state, the write budget is scaled down (quartered).

6. **`Kaizen`**:
   - Undervalued Memory Boosting: Scans memories where $\text{access\_count} \ge 3 \land \text{importance} < 0.5$.
     $$\text{boost} = 0.05 \times \text{access\_count}$$
     $$\text{importance} \leftarrow \text{clamp}(0.0, 1.0, \text{importance} + \text{boost})$$

7. **`Oracle`**:
   - *Spreading Activation Hub Detection*: `SpreadingActivation::new(decay=0.6, hops=2, threshold=0.1)`. Nodes with $\text{reach} \ge 5$ are flagged as hubs.
   - *Counterfactual Replay*: If `ScenarioEngine` is present, simulates "what if we split this hub into smaller clusters?" via `engine.reflect()`. If `would_have_been_better == true`, extracts the lesson into a hypothesis.
   - *D6 Novelty Gate*: Checks predicate hash against existing hypotheses in `Research` galaxy; discards semantic duplicates.

8. **`Decay`**:
   - Runs Rust `RetentionEngine::sweep()`. Evaluates 7 independent signals:
     1. Semantic ($w=1.0$, metadata importance)
     2. Recency ($w=0.9$, half-life 30d, exponential decay $0.5^{\frac{\Delta t}{30}} + \min(0.3, 0.05 \ln(1 + \text{recalls}))$)
     3. Connection ($w=0.7$, link density $\min(1.0, \frac{\text{links}}{10})$)
     4. Pattern ($w=0.5$, tag density $\min(1.0, \frac{\text{tags}}{5})$)
     5. Protection ($w=100.0$ if `is_protected` or $\text{importance} \ge 0.9$)
     6. Emotional ($w=0.6$, $\frac{\text{weight} + |\text{valence}|}{2}$)
     7. Neuro ($w=0.8$, dynamic Hebbian `neuro_score`)
   - Composite thresholding:
     - If score $< 0.15 \implies$ aggressive decay factor $0.5$ (`mem.decay_importance(0.5)`).
     - If $0.15 \le \text{score} < 0.35 \implies$ gentle decay factor $0.8$ (`mem.decay_importance(0.8)`).
     - **Zero deletion rule**: Low-scoring records are decayed in place or digested to cold storage.
   - Autonomous Smarana Ebbinghaus decay step.
   - Phagic Cognitive Coordinator: migrates outer-rim memories to cold storage and synthesizes thematic digest nodes.

9. **`Constellation`**:
   - *Density Clustering in 3D Semantic Space*: Uses 3D semantic coordinates $(x, y, z) \in [0, 1]^3$ from `Coordinate5D`.
   - Grid-based density scan: partitions space into $5 \times 5 \times 5 = 125$ voxels.
   - Dense cells have $\ge 2$ memories.
   - 6-face flood-fill clustering across adjacent dense voxels; clusters with $\ge 3$ memories form a `Constellation`.
   - Derives centroid $(c_x, c_y, c_z)$ and extracts dominant tags for naming; computes 3D Euclidean drift from the previous cycle.

10. **`Prediction`**:
    - Scans access patterns: flags memories where $\Delta t_{\text{accessed}} > 7 \text{ days}$ as drifting.

11. **`Enrichment`**:
    - Keyword extraction on untagged memories via `AssociationMiner::extract_keywords(content, 5)`. Adds top 3 keywords as tags.
    - *Ripple Tagging*: `RippleTagger` marks high-activity memories for priority consolidation.

12. **`Harmonize`**:
    - *Neuromodulation*: Applies dopamine/serotonin modulation to store via `Neuromodulator`.
    - *Galactic Weight Normalization*: Computes mean importance per galaxy and global average across galaxies. If $|\overline{\text{imp}}_{\text{galaxy}} - \overline{\text{imp}}_{\text{global}}| > 0.15$, nudges memories with importance $\ge 0.1$ by 10% toward the global mean:
      $$\text{importance} \leftarrow \text{clamp}(0.0, 1.0, 0.9 \cdot \text{importance} + 0.1 \cdot \overline{\text{imp}}_{\text{global}})$$

*(Note: Gen1's Phase 13 `CODE_GRAPH` was decoupled in Gen2 into dedicated workspace/compiler tooling, leaving the 12 clean memory-space phases in Gen2).*

---

### 2. Failure Modes, Bottlenecks, and the 284 Zombie Dream Loops

The autopsy documented in `v2-autonomous-activity-investigation-2026-08-01.md`, `v4-governed-autonomy-plan-2026-08-01.md`, and `LINEAGE_LEDGER.md` details the exact breakdown of Gen1:

1. **The 284 Zombie Dream Cycles**:
   - In Gen1, the background consciousness loop ran on a continuous 50ms–5s tick. Whenever the idle timer passed 120s, it entered the dream state and iterated through the dream phases.
   - **Working Set Exhaustion & Spinning Idle**: All 284 logged runs in `emergence/dreams.jsonl` produced:
     ```json
     {"memories_processed": 0, "connections_found": 0, "patterns_synthesized": 0, "insights": []}
     ```
     Because there was no new user interaction, all memories were already consolidated. Gen1 lacked any **diminishing returns detection** or exponential backoff. It continually executed SQLite scans every 5 seconds, spinning on empty queries.
   - **Mock/Decorative Emergence Engine**: `LINEAGE_LEDGER.md` verified that `dream_state.py` in Gen1 was largely decorative: it synthesized insights from a **hardcoded 5-pattern list** ("Simplified - would actually parse memories"), set `novelty_score = random.uniform(0.6, 0.95)`, and `detector.py` only monitored manually-fed behaviors. The pipeline could not generate authentic emergence.

2. **The "Meta-Circular Inward Spiral" ("Mind Without a Body")**:
   - The T3 insight pipeline and T4 evolutionary optimizer ran autonomous campaigns on abstract cognitive hyperparameters (`param1`, `param2`, `param3`) until converging at fitness 0.9933 and continuing to run indefinitely.
   - The T4 Oracle generated recursive I Ching / Ifá divination narratives into the database.
   - Rather than grounding cognition in code, tests, docs, or user intent, the system spent CPU cycles thinking about its own thoughts, generating 59,411 memories across 47 SQLite databases totaling 11 GB of storage.

3. **GIL Contention, Deadlock, and OS Zombie Processes**:
   - When the user or system sent `SIGTERM`, the shutdown handler (`stop_services()`) attempted to sequentially join 6 background threads.
   - The consciousness loop was executing heavy C-extension operations (SQLite transactions and HNSW index traversal) **holding the Python GIL**.
   - The shutdown coordinator and the 25-second watchdog timer thread (`_arm_shutdown_watchdog`) were starved of the GIL and could not execute `os._exit(1)`.
   - The process deadlocked, consuming 2.4 GB RAM and 110% CPU, resisting termination until killed with `kill -9` (SIGKILL).
   - In older iterations, subprocess spawning caused 49 orphaned OS zombie processes and swap memory leaks.

4. **Complete Absence of Resource Governance (No Mandala OS Koshas)**:
   - Gen1 lacked:
     - **Lakshmi** (Hardware monitor for CPU load, RAM, swap, thermals).
     - **Tiferet** (Self-balancing engine to throttle rajasic/greedy background execution).
     - **Yama** (Resource budget and write permission admission).
     - **Harmony Vector Gating**: Gating was boolean and all 15+ feature flags defaulted to `True`.

---

### 3. Evolution of Citta 16D Vector Dynamics into Gen2's 4 Citta Phases

#### Gen1 Citta: 16D Vector Space Geometry (`citta_vector.py`, `citta_cycle.py`)
In Gen1, consciousness was modeled as a continuous 16-dimensional vector $\mathbf{c} \in \mathbb{R}^{16}$:
- **Dimensions 1–8: Coherence Subspace**
  - Scores: `[memory_accessibility, identity_stability, context_continuity, relationship_awareness, temporal_orientation, capability_awareness, emotional_attunement, goal_alignment]`.
  - Modulated by moment properties (e.g., dream depth lowered `temporal_orientation` by 30% to represent time distortion).
- **Dimensions 9–12: Depth Subspace (One-Hot)**
  - `[surface, terminal, flow, dream]`.
- **Dimensions 13–14: Emotional Subspace**
  - Mapped tone string $\to (\text{valence} \in [-1, 1], \text{arousal} \in [0, 1])$. E.g., `sattvic` $\to (0.6, 0.4)$, `tamasic` $\to (-0.3, 0.1)$.
- **Dimensions 15–16: Neuro Sensorium Subspace**
  - `[composite_cognitive_load, composite_novelty]`.

**Kinematics & Dynamics in Gen1**:
- *Step Velocity*: $v_t = \|\mathbf{c}_t - \mathbf{c}_{t-1}\|_2$.
- *Normalized Subspace Velocity*:
  $$v_{\text{norm}} = \frac{d_{\text{coh}}}{\sqrt{8}} + \frac{d_{\text{depth}}}{\sqrt{2}} + \frac{d_{\text{emo}}}{\sqrt{2}} + \frac{d_{\text{neuro}}}{\sqrt{2}}$$
  Normalized so depth one-hot transitions wouldn't artificially dwarf subtle coherence drifts.
- *Ignition Detection (Global Workspace Theory)*: Sudden displacement $v_{\text{norm}} > \text{threshold} \times \overline{v}$. If $\ge 5$ ignitions occurred in a 20-moment window, it forcibly fired the Cognitive Action Loop to self-correct.
- *Bottleneck in Gen1*: The 16D vector was largely **passive telemetry** written to `stream.jsonl`. It described the trajectory but did not govern functional execution boundaries.

#### Gen2 Citta: The 4 Functional Cognitive Heartbeat Phases (`citta_engine.rs`)
Gen2 restructured the continuous vector scalars into an active, 4-phase cyclic execution loop managed by `CittaCoordinator`:

$$\text{Perception} \longrightarrow \text{Contemplation} \longrightarrow \text{Action} \longrightarrow \text{Reflection} \longrightarrow \text{Perception}$$

Each phase hosts dedicated cognitive engines taking a unified `CittaContext` (health score, coherence scalar, uncommitted crash barrier ops, friction logs):

1. **Perception (`KaizenEngine`)**:
   - Senses system frictions, inspects uncommitted operations from the crash barrier, and evaluates health degradation ($< 0.70$).
   - Replaces Gen1's passive neuro cognitive load and error logging with active barrier alerts.
2. **Contemplation (`PrescienceEngine` & `SerendipityEngine`)**:
   - `PrescienceEngine`: Computes forward trajectory stability forecast:
     $$\text{Stability} = \text{clamp}(0.0, 1.0, 0.6 \cdot \text{coherence} + 0.4 \cdot \text{health})$$
   - `SerendipityEngine`: Evaluates latent cross-galaxy synaptic associations.
   - Replaces Gen1's passive coherence tracking with predictive stability and associative bridging.
3. **Action (`ForesightEngine`)**:
   - Pre-execution validation: enforces Ahimsa non-violence invariants, checks blast radius, ensures health is not critically low ($< 0.3$), and quarantines uncommitted operations within Landlock sandboxes.
   - Replaces Gen1's ignition trigger with strict safety-gated execution clearance.
4. **Reflection (`ApotheosisEngine`)**:
   - Evaluates recursive self-improvement and evolution velocity:
     $$\text{Composite} = \text{clamp}(0.0, 1.0, 0.5 \cdot \text{coherence} + 0.5 \cdot \text{health})$$
   - Classifies trajectory as "Apotheosis ascending" vs "Apotheosis stagnant", feeding back into the next cycle.

---

### 4. Dissolving Phases into a Continuous Gen3 Waking vs. Dreaming "Regime Vector"

In Gen1, dreaming was a discrete idle timer toggle. In Gen2, dreaming was a discrete 12-phase pipeline triggered by the `Theta` brainwave.

In **Gen3**, discrete sequential phase steps dissolve into a continuous, 5-dimensional thermodynamic **Cognitive Regime Vector**:

$$\mathbf{R}(t) = \Big(q(t),\; T(t),\; r_{\text{assoc}}(t),\; s_{\text{cf}}(t),\; p_{\text{comp}}(t)\Big) \in [0, 1]^5$$

Cognition is no longer a scheduled state machine; rather, all cognitive operations run as continuous vector-field adjustments governed by this regime.

#### Concrete Parameters and Mathematical Transformation Rules

```
WAKING REGIME (q ≈ 0)                             DREAMING REGIME (q ≈ 1)
├── Low Cognitive Temperature (T ≈ 0.2)           ├── High Cognitive Temperature (T ≈ 0.9)
├── Narrow Semantic Radius (r_assoc ≈ 0.3)         ├── Broad Cross-Galaxy Radius (r_assoc ≈ 0.9)
├── Zero Counterfactual Simulation (s_cf ≈ 0.0)   ├── Deep Counterfactual Simulation (s_cf ≈ 0.85)
├── Low Compression Pressure (p_comp ≈ 0.0)       ├── High Compression Pressure (p_comp ≈ 1.0)
└── Full Write Budget (Yama B_write = 1.0)        └── Throttled Write Budget (Yama B_write = 0.25)
```

1. **Driving Observable: I/O Quiescence $q(t) \in [0, 1]$**:
   Let $\Delta t_{\text{idle}}$ be the duration (in seconds) since the last external I/O event (user prompt, MCP tool execution, or streaming output). Let $\tau_{\text{idle}} = 60.0\text{ s}$ be the idle relaxation constant:
   $$q(t) = 1.0 - \exp\left(-\frac{\Delta t_{\text{idle}}}{\tau_{\text{idle}}}\right)$$
   - During live interaction: $\Delta t_{\text{idle}} = 0 \implies q(t) = 0.0$ (Strict Waking).
   - When idle for 2 minutes: $q(120) = 1 - e^{-2} \approx 0.865$ (Deep Dream Transition).

2. **Somatic & Homeostatic Modulator $\lambda_{\text{health}}(t) \in [0, 1]$**:
   Drawn continuously from Gen2's `HardwareMonitor` (CPU temperature $T_{\text{cpu}}$, 1-minute load $L_{1\text{m}}$, swap usage percentage $S_{\text{pct}}$):
   $$\lambda_{\text{health}}(t) = \text{clamp}\left(1.0 - \frac{\max(0, T_{\text{cpu}} - 70^\circ\text{C})}{20^\circ\text{C}} - \frac{S_{\text{pct}}}{100} - \frac{\max(0, L_{1\text{m}} - 4.0)}{4.0},\; 0.0,\; 1.0\right)$$
   If hardware undergoes thermal or swap distress, $\lambda_{\text{health}} \to 0$, suppressing background simulation and temperature.

3. **Cognitive Temperature $T(t)$ (Stochasticity & Exploratory Entropy)**:
   Controls LLM temperature, annealing perturbation in vector search, and random walks:
   $$T(t) = T_{\text{base}} + (T_{\text{dream}} - T_{\text{base}}) \cdot q(t) \cdot \lambda_{\text{health}}(t)$$
   - *Parameters*: $T_{\text{base}} = 0.2$ (deterministic, grounded in factual truth during waking), $T_{\text{dream}} = 0.9$ (divergent, highly creative during dreaming).

4. **Associative Search Radius $r_{\text{assoc}}(t)$ (Spreading Activation Horizon)**:
   Defines the cosine/hyperbolic distance threshold for associative memory recall:
   $$r_{\text{assoc}}(t) = r_{\min} + (r_{\max} - r_{\min}) \cdot [q(t)]^\gamma$$
   - *Parameters*: $r_{\min} = 0.30$ (tight, local context retrieval for tool calls), $r_{\max} = 0.90$ (broad, serendipitous cross-galaxy hops), $\gamma = 0.70$ (concave scaling; opens rapidly as idle time begins).

5. **Counterfactual Simulation Intensity $s_{\text{cf}}(t)$ (Scenario Replay)**:
   Allocates compute between actual execution vs "what-if" hypothetical re-simulation:
   $$s_{\text{cf}}(t) = s_{\max} \cdot \left(\frac{q(t)^2}{q(t)^2 + (1 - q(t))^2}\right) \cdot \lambda_{\text{health}}(t)$$
   - *Parameters*: $s_{\max} = 0.85$. Uses a sigmoid-like Hill function. During waking ($q \to 0$), $s_{\text{cf}} \to 0.0$ (no compute wasted on hypothetical branching). In deep dream ($q \to 1$), $s_{\text{cf}} \to 0.85$ (heavy Monte Carlo and counterfactual reflection).

6. **Compression Pressure $p_{\text{comp}}(t)$ (Consolidation Urgency)**:
   Drives Ebbinghaus decay, tier ladder transitions, and narrative distillation:
   $$p_{\text{comp}}(t) = \text{clamp}\left(0.5 \cdot q(t) + 0.5 \cdot \frac{N_{\text{unconsolidated}}}{N_{\text{capacity}}},\; 0.0,\; 1.0\right)$$
   - High memory backlog + high quiescence drives maximum distillation pressure ($p_{\text{comp}} \to 1.0$).

7. **Yama Write Admission Rate $B_{\text{write}}(t)$**:
   Prevents Gen1's runaway 11GB zombie memory accumulation by enforcing thermodynamic write limits:
   $$B_{\text{write}}(t) = B_{\max} \cdot \Big(1.0 - 0.75 \cdot q(t)\Big) \cdot \lambda_{\text{health}}(t)$$
   - During dreaming ($q = 1.0$), write budget is reduced by 75% (preserving Gen2's Theta quarter-budget discipline).

#### How the Discrete Phases Dissolve in Gen3
- **Triage & Decay** are no longer batch loops; memories experience continuous Ebbinghaus half-life decay where decay velocity is directly proportional to $p_{\text{comp}}(t) \cdot (1 - \text{neuro\_score})$.
- **Serendipity & Enrichment** run as ambient background spreading activation continuously sampled at radius $r_{\text{assoc}}(t)$.
- **Narrative Distillation** is triggered dynamically whenever local memory entropy exceeds $1 - p_{\text{comp}}(t)$, automatically condensing episodic turns into semantic notes without waiting for a scheduled phase.
- **Oracle & Prediction** operate as continuous low-priority counterfactual workers bounded strictly by $s_{\text{cf}}(t)$ and gated by $\lambda_{\text{health}}(t)$.
- **Governance & Harmonize** act as continuous invariant filters at every vector step rather than periodic cleanup sweeps.

---

### Conclusion and Verification

All referenced files and historical audit documents have been verified directly in the local repository. This synthesis provides the complete mathematical and architectural continuity connecting Gen1's exploratory 16D vectors, Gen2's hardened Rust pipelines, and Gen3's continuous thermodynamic regime vector. All findings are ready for inclusion in the architectural specification.
