# WhiteMagic Gen3: Physics, Dynamics, Spectroscopy, and Phenotype Emergence Specification

**Version:** v1.2 (Pre-Execution Tightening & Falsification Rigor)  
**Status:** Ratified Design Specification & Emergence Blueprint  
**Baseline Anchor:** `Gen3 Cognitive Runtime Baseline 1 (G3-CRB-1)` (git tags `g3-crb-1` in `WMv9` and `WMgen3`)  
**Epistemic Predecessors:**  
- `docs/CHARTER.md` (Constitutional Invariants)  
- `docs/NUCLEUS.md` (Substrate Mechanics)  
- `docs/THEORY_MECHANISM_MAP.md` (Falsification Dispositions)  
- `docs/BENCHMARK_AND_VERIFICATION_PROTOCOL.md` (7-Phase Verification Suite)  
- Archaeological Excavations: Subagents `359fce94`, `127c4a34`, `2a1da743`, `9e29b916`, `543f37eb`, `cb7916c3`, `d4bb20b4`, `8ca26fb8`

---

## 1. The Four-Level Generational Ontology

WhiteMagic's evolution across generations follows a definitive progression:
* **Gen1 (Phenomena Discovery):** Baroque exploration. 851 tools partitioned into 28 Ganas, 28 Gardens, 28 Engines (absorbing 44 sub-engines), 13 dream phases, 4D holographic coordinates, and 7-dimension harmony vectors. Rich phenomena were discovered, but lacked mechanization, leading to runaway zombie loops and exception swallowing.
* **Gen2 (Constraint Discovery):** Constitutional hardening. Rust workspace (`WMv9`), transactional leases, LMDB storage, Firebreak (31 forbidden patterns), Bulk-Scope law, Landlock LSM process/thread sandboxing, and Yama rate limits. Preserved capabilities through curated profiles and verified seams.
* **Gen3 (Physical Emergence):** Discovering the underlying physics from which the phenomena emerge naturally without building monolithic organs, hardcoded registries, or durable workflow runtimes.

```
┌─────────────────────────────────────────────────────────────────────────┐
│ LEVEL 4: PHENOTYPES (Emergent Behaviors & Structures)                   │
│   • Gardens (Attractor Basins)         • Galaxies (Projection Views)    │
│   • Ganas (Learned Cognitive Postures) • Dreaming (I/O Quiescence)      │
│   • Homeostasis (Closed-Loop Actuators)• Geneseeds (Causal Cladistics)  │
├─────────────────────────────────────────────────────────────────────────┤
│ LEVEL 3: LANGUAGE (Symbolic Spectroscopy of Cognition)                  │
│   • 22 Dynamical Motifs (Suarèsian Autoglyphs / Letter-Numbers)        │
│   • NON-DISPATCHING OBSERVABILITY: "Symbols may render, never dispatch"  │
│   • Telemetry Vector m_t ──> 22 Continuous Spectral Bands φ_k(m_t)      │
├─────────────────────────────────────────────────────────────────────────┤
│ LEVEL 2: DYNAMICS (Field Mechanics & Topological Flow)                  │
│   • Spreading Activation & Decay       • Currentness Strata             │
│   • Signed Laplacian L_signed          • Phase Transitions (Dust->Star) │
│   • Catuṣkoṭi Logic <E+, E-, F, Γ>     • Symmetrized Community Detection│
├─────────────────────────────────────────────────────────────────────────┤
│ LEVEL 1: PHYSICS (Substrate & Primitive Operations)                     │
│   • Epistemic Substrate: Records x, Directed Hyper-Relations e=(U,V,...)│
│   • Append-Only Journal J              • Transactional Storage Engine   │
│   • Candidate Canonical Pulse: [SELECT ──> TRANSFORM ──> EVALUATE ──> COMMIT]│
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Level 1: Substrate Physics & Primitive Operations

### 2.1 The Epistemic Substrate
The substrate contains no distinct databases for memories, thoughts, or beliefs. There is only a single unified relation substrate:
1. **Records ($x \in \mathcal{X}$):**
   $$x = \langle \text{id}, \text{content}, \text{class}, \text{source}, \text{provenance}, \vec{\theta}, \tau_{\text{horizon}} \rangle$$
   where $\text{class} \in \{\text{Evidence}, \text{Belief}, \text{Speculation}\}$ is strictly enforced by **Closure 2 (Evidence)**.
2. **Directed Hyper-Relations ($e \in \mathcal{E}$):**
   $$e = \langle U, V, w, s, c, t, \text{kind} \rangle$$
   where $U, V \subseteq \mathcal{X}$ are non-empty sets of source and target records ($|U| \ge 1, |V| \ge 1$), $w \in [0, 1]$ is weight, $s \in \{-1, +1\}$ is sign (attraction/repulsion), $c \ge 0$ is traversal cost, $t$ is timestamp, and $\text{kind} \in \{\text{Associative}, \text{Causal}, \text{Supersession}, \text{Derivation}\}$. This formulation natively accommodates binary relations as well as $n$-ary cladistic relations like $\text{recombined\_from}(V=\{\text{child}\}, U=\{\text{parent}_a, \text{parent}_b\})$.
3. **Append-Only Journal ($\mathcal{J}$):**
   Cryptographically linked, monotonic event stream ratcheted by BLAKE3 hashes.

### 2.2 The Candidate Canonical Pulse & The Minimality Hypothesis
All cognitive operations decompose into a candidate four-beat pulse:

$$\mathbf{Select} \longrightarrow \mathbf{Transform} \longrightarrow \mathbf{Evaluate} \longrightarrow \mathbf{Commit}$$

```
                ┌──────────────────────────────────────────────────────────┐
                │                         SELECT                           │
                │  Filters active working set S_t from substrate X using   │
                │  boundary parameters (spatial, temporal, class, horizon) │
                └────────────────────────────┬─────────────────────────────┘
                                             │
                                             ▼
                ┌──────────────────────────────────────────────────────────┐
                │                        TRANSFORM                         │
                │  Pure functional mapping f(S_t, θ) -> C_t generating     │
                │  candidate records, relational edges, or synthesized text│
                └────────────────────────────┬─────────────────────────────┘
                                             │
                                             ▼
                ┌──────────────────────────────────────────────────────────┐
                │                         EVALUATE                         │
                │  Constitutional verification & multi-objective scoring:  │
                │  Closure 1 (Law), Closure 2 (Evidence), Pareto, Brier    │
                └────────────────────────────┬─────────────────────────────┘
                                             │
                                             ▼
                ┌──────────────────────────────────────────────────────────┐
                │                          COMMIT                          │
                │  Atomic durable persistence to LMDB & Journal ratchet;   │
                │  state becomes immutable; telemetry emitted              │
                └──────────────────────────────────────────────────────────┘
```

* **The Minimality Hypothesis (PEB-0):** "Irreducibility" is an empirical claim, not an architectural axiom. WhiteMagic does not adopt four operations by decree. Through **PEB-0 (Primitive Minimality)**, the candidate pulse faces three rigorous reduction attacks:
  1. *Ablation:* What fails when a primitive is deleted outright?
  2. *Merger:* Can Evaluate be expressed as an invariant-constrained Transform? Can Select and Transform be collapsed into a single generalized constrained mapping?
  3. *Substitution:* Can an alternative algebra (e.g. 3 beats, 2 beats, or an asymmetric split between **3 reversible cognitive transforms** and **1 irreversible historical/transactional commit boundary**) reproduce all constitutional guarantees?
  * **Definition of Equivalent Preservation:** An alternative algebra "preserves all invariants" if and only if it demonstrates **observational equivalence across a frozen test corpus**: identical constitutional outcomes, identical externally visible state transitions, identical durability/rollback guarantees, and no statistically meaningful regression in the protected measurements. If a simpler algebra succeeds, WhiteMagic shrinks and celebrates the reduction.
* **No Workflow Ontology or DAG Engine:** Rejecting the premature reintroduction of W2_05, there is **no durable DAG engine, no workflow ontology, and no separate orchestrator universe**. A composition graph is strictly a static dependency description among pure functional transformations, compiled directly into iterative pulses of the execution substrate:
  $$\text{Composition Graph} \longrightarrow [\mathbf{Select} \longrightarrow \mathbf{Transform} \longrightarrow \mathbf{Evaluate} \longrightarrow \mathbf{Commit}]^n$$

---

## 3. Level 2: Dynamics & Epistemic Logic

### 3.1 Contextualized Catuṣkoṭi & Rejection of the Frame
Classical binary logic ($P \lor \neg P$) forces artificial collapse on incomplete or ill-framed knowledge. WhiteMagic Gen3 operationalizes the Buddhist Catuṣkoṭi (four corners) alongside explicit context conditioning.

#### 3.1.1 The Epistemic Quadruple with Context $\Gamma$
Every belief or proposition $A$ evaluated under an explicit operational context $\Gamma$ is parameterized by:
$$\mathbf{E}(A \mid \Gamma) = \langle E^+, E^-, F, \Gamma \rangle$$
* $E^+ \in [0, 1]$: Accumulated positive grounded evidence in context $\Gamma$.
* $E^- \in [0, 1]$: Accumulated negative/counter-evidence in context $\Gamma$.
* $F \in [0, 1]$: **Frame Applicability / Coherence** (Does the question meaningfully carve reality at its joints under $\Gamma$?).
* $\Gamma$: The explicit conditioning context (e.g. system workload, platform environment, domain constraints).
*(Calibration and reliability weights remain separately derived quantities in the Claims Ledger and Brier scoring machinery, preventing context-dependence, contradiction, and uncertainty from being conflated).*

#### 3.1.2 The Four Corners + The Fifth Move (Frame Rejection)
1. **$K_1$ — Affirmed ($A$):** $E^+ \gg 0$, $E^- \approx 0$, $F \approx 1.0$. Evidence supports the claim under context $\Gamma$.
2. **$K_2$ — Denied ($\neg A$):** $E^+ \approx 0$, $E^- \gg 0$, $F \approx 1.0$. Counter-evidence refutes the claim under context $\Gamma$.
3. **$K_3$ — Both Affirmed and Denied ($A \land \neg A$):** $E^+ \gg 0$, $E^- \gg 0$, $F \approx 1.0$. Genuine dialectical contradiction under a valid frame (e.g. two trustworthy, well-calibrated telemetry sensors reporting contradictory readings for the same system event).
4. **$K_4$ — Neither Affirmed nor Denied ($\neg A \land \neg(\neg A)$):** $E^+ \approx 0$, $E^- \approx 0$, $F \approx 1.0$. Genuine neutral agnosticism / unmeasured domain under a valid frame.
5. **$K_0$ — Reject the Frame ($F \approx 0$):**
   The proposition is a category error, semantic trap, or false dichotomy (e.g., *"Is the color green acidic or alkaline?"*). Instead of hallucinating a binary resolution, the runtime outputs:
   $$\text{Verdict}(A \mid \Gamma) = \mathbf{RejectFrame} \quad \text{with explanatory witness } W_F$$

---

## 4. Level 3: Language & Symbolic Spectroscopy

### 4.1 The Non-Dispatching Law
> **Charter §3.10 Invariant:** *"Symbols may render; symbols may never dispatch."*  
> No symbolic system (Tree of Life, Suarèsian letter-numbers, Tarot, Yijing, Ganas, Gardens) may branch execution. They are strictly observational lenses.

### 4.2 The 22 Suarèsian Dynamical Motifs
Carlo Suarès (*The Cipher of Genesis*) interpreted the 22 Hebrew letter-numbers as recurring energetic pulsation operators across three octaves:
1. **1–9 (Archetypal Roots):** Primary dynamic potential.
2. **10–90 (Existential Projections):** Manifest operational processes.
3. **100–400 (Universal Closures):** Macro-scale synthesis and finalization.

The scientific runtime does not stake itself on the historical truth of the symbolic interpretation; it uses the 22 motifs as a candidate descriptive basis for observable physical transitions.

### 4.3 Spectrometer Transfer Functions ($\phi_k(\vec{m}_t)$)
The spectrometer samples engine telemetry $\vec{m}_t$ and computes continuous activation intensities $\phi_k \in [0, 1]$:

| # | Autoglyph | Dynamic Motif | Physical Beat | Transfer Function $\phi_k(\vec{m}_t)$ |
|---|---|---|---|---|
| 1 | **Aleph (א)** | Fluctuation / Superposition | `Select` | $\phi_1 = \tanh(\sigma^2_a) \cdot \frac{H}{H_{\max}} \cdot (1 - I_{\text{commit}})$ |
| 2 | **Bayt (ב)** | Containment / Bounding | `Select` | $\phi_2 = (1 - \rho_{\text{pass}}) \cdot \mathbb{I}(\text{working set bounded})$ |
| 3 | **Ghimel (ג)** | Directed Canalization | `Transform` | $\phi_3 = \frac{\|\vec{v}_{\text{hop}}\|}{\|\vec{v}\|_{\max}} \cdot (1 - \text{friction})$ |
| 4 | **Dallet (ד)** | Resistance / Gating Barrier | `Evaluate` | $\phi_4 = \kappa_{\text{refusal}} \cdot \tanh(\Phi + 0.5)$ |
| 5 | **He (ה)** | Respiration / Aperture | `Select` | $\phi_5 = \frac{1}{2}\left(1 + \sin\left(\frac{2\pi \Delta t}{\tau_{\text{breath}}}\right)\right)$ |
| 6 | **Waw (ו)** | Relational Binding | `Transform` | $\phi_6 = \tanh(\Delta |E_{\text{hyper}}| + \Delta |E_{\text{assoc}}|)$ |
| 7 | **Zayn (ז)** | Query Bifurcation | `Select/Transform` | $\phi_7 = \text{sigmoid}(b_{\text{fan-out}} - 2.0)$ |
| 8 | **Het (ח)** | Intermediate Reservoir | `Commit` | $\phi_8 = \frac{|\mathcal{S}_{\text{staging}}|}{|\mathcal{S}_{\text{staging}}| + 10}$ |
| 9 | **Tayt (ט)** | Structuration / Clustering | `Transform` | $\phi_9 = \text{Modularity}(Q_{\text{communities}})$ |
| 10 | **Yod (י)** | Discrete Actuation Spark | `Transform` | $\phi_{10} = \mathbb{I}(\text{hypothesis emitted}) \cdot (1 - \text{entropy})$ |
| 20 | **Kaph (כ)** | Storage Assimilation | `Commit` | $\phi_{20} = \tanh(\text{pages\_allocated} / 10.0)$ |
| 30 | **Lamed (ל)** | Causal Trajectory Extrapolation| `Transform` | $\phi_{30} = \text{depth}(\text{causal\_chain}) / \text{depth}_{\max}$ |
| 40 | **Mem (מ)** | Continuous Fluid Diffusion | `Transform` | $\phi_{40} = 1.0 - \text{sparsity}(\text{embedding\_activation})$ |
| 50 | **Nun (נ)** | Stochastic Novelty Mutation | `Transform` | $\phi_{50} = \text{rate}(\text{random\_walk\_hops})$ |
| 60 | **Samekh (ס)**| Constitutional Scaffolding | `Evaluate` | $\phi_{60} = \mathbb{I}(\text{closures verified}) \cdot (1 - \Phi_{\text{violation}})$ |
| 70 | **Ayin (ע)** | Evidential Apperception | `Select` | $\phi_{70} = \text{density}(\text{provenance\_chains})$ |
| 80 | **Pe (פ)** | Telemetry / Output Emission | `Commit` | $\phi_{80} = \tanh(\text{bytes\_streamed} / 512)$ |
| 90 | **Tsade (צ)** | Objective Convergence | `Evaluate` | $\phi_{90} = 1.0 - \text{BrierScore}(\text{predictions})$ |
| 100 | **Qof (ק)** | Global Resonance Cascade | `Commit` | $\phi_{100} = \tanh(\Delta \|\vec{R}_{\text{effective}}\|)$ |
| 200 | **Resh (ר)** | Autonomous Executive Handoff | `Commit->Select` | $\phi_{200} = \mathbb{I}(\text{phase switch}) \cdot \text{executive\_coherence}$ |
| 300 | **Shin (ש)** | Thermal Annealing / Purge | `Transform/Eval` | $\phi_{300} = \tanh(T) \cdot \frac{\text{superseded\_pruned}}{\text{total\_edges} + 1}$ |
| 400 | **Taw (ת)** | Immutable Journal Seal | `Commit` | $\phi_{400} = I_{\text{commit}} \cdot \exp(-\text{uncommitted\_ops})$ |

* **Preregistered Multi-Baseline Fidelity Evaluation (PEB-7):**
  Neutrality is not fidelity. In PEB-7, the 22-glyph basis $\Sigma_{22}$ is benchmarked across held-out workloads against five competing representations:
  $$\Sigma_{22} \quad \text{vs.} \quad \text{Random}_{22} \quad \text{vs.} \quad \text{PCA}_{22} \quad \text{vs.} \quad \text{ICA}_{22} \quad \text{vs.} \quad \text{Raw Telemetry} \quad \text{vs.} \quad \text{Learned}_k$$
  across six explicit metrics:
  1. *Future-State Prediction:* Accuracy in predicting $m_{t+1}$ from $m_{\le t}$.
  2. *Anomaly Discrimination:* ROC-AUC distinguishing normal runs from injected faults.
  3. *Compression Ratio:* Bit-rate efficiency under lossless reconstruction.
  4. *Phenotype Discrimination:* F1-score in classifying active cognitive regimes.
  5. *Cross-Domain Transfer:* Preservation of representation across disparate tasks.
  6. *Dimensional Redundancy:* Mutual information between spectral bands (penalizing co-linear glyphs).
  If the 22 glyphs merely beat random but are demolished by PCA, that limitation is recorded. If only 11 motifs capture distinct physical variance, 11 survive.

---

## 5. Level 4: Emergent Phenotypes

### 5.1 Gardens as Dynamic Attractor Basins & Dual Graph Operators
* **Dissolution of Organs:** All distinct `BaseGarden` class trees are eliminated.
* **Dual Graph Operators (Geometry vs. Flow):**
  WhiteMagic distinguishes the symmetric spatial geometry of attractor basins from the directed causality of information flow:
  1. *Basin Geometry Operator (Symmetric Signed Laplacian):*
     $$\mathbf{L}_{\text{signed}} = \bar{\mathbf{D}} - \frac{1}{2}(\mathbf{W} + \mathbf{W}^T)$$
     where $\mathbf{W}_{ij} = s_{ij} \cdot w_{ij}$ and $\bar{\mathbf{D}}_{ii} = \sum_{j} |\mathbf{W}_{ij}|$. This intentionally symmetrizes relations to uncover undirected potential wells and metastable community clusters.
  2. *Causal / Information Flow Operator (Directed Transition Matrix):*
     $$\mathbf{P} = \mathbf{D}_{\text{out}}^{-1} \mathbf{W}$$
     which strictly preserves edge directionality ($A \to B \neq B \to A$) for spreading activation, causal inference, and lineage propagation.
* **Two-Arm Emergence Protocol (PEB-2):**
  1. *Arm A (Seeded Continuity):* Uses historical Garden coordinate priors and canonical resonance kernels.
  2. *Arm B (De-Novo Emergence):* **Strictly $\lambda = 0$**. Zero Garden ontology, zero 28-labels, zero historical priors. The substrate is driven by realistic workloads, and attractor basins are discovered de-novo via spectral clustering on $\mathbf{L}_{\text{signed}}$. The resulting basin count is an unconstrained empirical outcome, compared post-hoc to historical taxonomy.

### 5.2 Ganas as Adaptive Cognitive Roles
* **Elimination of Tool Partitioning:** The 851-tool PRAT RPC partition is gone. Tools are routed via TF-IDF NLU against curated surface profiles.
* **Empirical Taxonomy Drift:** Cognitive roles are identified by continuous clustering of the co-usage matrix $\mathbf{C}_{ij}$ without assuming 28 discrete variants. When usage boundaries diverge from current roles, the runtime surfaces empirical taxonomy adaptation proposals.

### 5.3 Continuous Dreaming: The Cognitive Regime Vector
* **Cure for the August 1 Zombie Loops:** Gen1's runaway (284 idle dream loops consuming 11GB across 47 databases) resulted from treating dreaming as an unmetered, autonomous background loop without diminishing returns detection.
* **The Regime Vector $\mathbf{R}(t)$:** Dreaming in Gen3 is a continuous shift in the physical parameters of `[Select -> Transform -> Evaluate -> Commit]`:
  $$\mathbf{R}(t) = \big(q(t),\; T(t),\; r_{\text{assoc}}(t),\; s_{\text{cf}}(t),\; p_{\text{comp}}(t)\big)$$
  * $q(t) = 1 - e^{-\Delta t_{\text{idle}} / \tau_{\text{idle}}}$: I/O Quiescence factor.
  * $T(t) = T_{\text{base}} + q(t) \cdot \Delta T$: Sampling temperature.
  * $r_{\text{assoc}}(t) = r_0 \cdot (1 + \alpha q(t))$: Associative search radius.
  * $s_{\text{cf}}(t) \in [0, 1]$: Counterfactual simulation depth.
  * $p_{\text{comp}}(t) \in [0, 1]$: Memory compression / deduplication pressure.
  * **Constitutional Dream Throttle:** When $q(t) > 0.8$, write budgets are restricted by $75\%$ ($B_{\text{write}} = 0.25$). If marginal consolidation delta falls below $\epsilon_{\text{return}}$ for 3 consecutive cycles, dreaming enters deep zero-write stasis.

### 5.4 Closed-Loop Homeostasis & Competing Constraints
* **Multi-Actuator Control Vector $\vec{s}(t)$:**
  $$\vec{s}(t) = \langle \text{RAM}_{\%},\; \text{Latency}_{p99},\; \text{WriteChurn},\; \text{ErrorRate},\; \text{ContextUtilization} \rangle$$
* **Constitutional Arbitration of Competing Constraints:**
  Under resource stress, latency reduction (contracting Top-K $20 \to 10 \to 3$) can directly conflict with evidential guarantees (e.g. maintaining $90\%$ conformal recall coverage).
  * **Constitutional Invariant:** The system must **never silently violate evidential coverage to satisfy a latency SLA**.
  * When latency and coverage cannot be simultaneously satisfied, the runtime must explicitly declare the constraint failure, log a formal friction event, and negotiate graceful degradation (e.g., explicit partial abstention, async deferral, or user-notified confidence bounds).
* **Closed-Loop Actuators:** Cooling low-mass stars ($w < 0.2$) to LMDB cold storage under RAM pressure; sleeping mining daemons under write churn; routing anomalous inputs to `quarantine_index`.

### 5.5 Causal Cladistics & Pareto Selection
* **Directed Hypergraph Lineage:** Relationships like $\text{recombined\_from}(V=\{\text{child}\}, U=\{\text{parent}_a, \text{parent}_b\})$ and $\text{supersedes}(V=\{\text{new}\}, U=\{\text{old}\})$ are modeled as genuine hyper-edges.
* **Pareto Gating Prior to Fitness Ranking:**
  Adhering to the Phase 7 constitutional law, a gain in one metric cannot buy permission to regress a protected metric. Admission to the germline requires:
  $$\forall m \in M_{\text{protected}}, \quad \Delta m \not< 0 \quad (\text{statistically verified})$$
  $$\text{and } \exists m: \Delta m > 0$$
  Scalar fitness ($\Delta \text{Fitness} = \Delta \text{Brier} + \alpha \Delta \text{Throughput} - \beta \Delta \text{Latency}$) is used **strictly to rank Pareto-admissible survivors**, never as a tradeable scalar admission score.
* **Shadow Clones:** Parallel Tokio lease sandboxes evaluate mutations under Phase 7 Replay before germline admission.

### 5.6 Bicameral Transform Kernels & Attention Workspace
* **Pluggable Transform Kernels:**
  * *Analytical Kernel (Left):* Low temperature ($T = 0.2$), deterministic deduction.
  * *Divergent Kernel (Right):* Higher temperature ($T = 0.7$), hypothesis generation.
  * *Autonomic Kernel (Draft):* Persistent BitMamba-2 255M draft generator.
* **Speculative Margin Fast-Path:**
  Draft sequences are accepted without verifier invocation if confidence margin $\Delta_{\text{margin}} = \text{top1} - \text{top2} \ge 0.85$.
* **Global Workspace Spotlight:**
  Events claim execution attention via multiplicative salience discounted by exponential decay:
  $$\text{Salience}(t) = (\text{urgency} \times \text{novelty} \times \text{confidence}) \cdot 0.5^{\frac{\Delta t}{\tau_{\text{decay}}}}$$

### 5.7 The Sangha Mesh & Sovereign Gan Ying Boundaries
* **Transport:** Length-prefixed TCP JSON-RPC (`[4B length][payload]`) capped at 1MB, with anti-ghost socket eviction and UDP multicast beaconing.
* **Sovereign Boundary:** Peer-declared authority is strictly an external stimulus. The local node grant table (`mesh_authority.json`) is the sole sovereign boundary (Default-Deny). First valid signed beacons bind public keys via TOFU (Trust-On-First-Use).
* **Multi-Agent Containment:** Auto-quarantines rogue members upon $\ge 3$ verification failures or trust decay below $0.20$.
* **Radiant Routing:** Compute shared reciprocally via `GiftTokenLedger`; freeloaders ($<30\%$ reciprocity) denied offload surplus.

### 5.8 Pure Transform Compositions (Eliminating the DAG Engine)
* **Engines as Stateless Transform Nodes:** The 72 legacy engines are decomposed into re-entrant, stateless transform functions executed across the 4 alchemical stages (Nigredo, Albedo, Citrinitas, Rubedo).
* **Fusions as Compiled Edges:** The 45KB procedural `fusions.py` logic compiles down to direct data dependencies executed within the 4-beat pulse.
* **Captains as Parameterized Recipes:** Vanguard, Sentry, Alchemist, and Cartographer are pre-registered composition presets running on the Rayon/Tokio parallel substrate.
* **Violet Cryptographic Barriers:** Ed25519 `EngagementToken` bound to ROE hashes act as precondition gates upstream of privileged mutations.

### 5.9 Conformal Coverage Sets & Distribution-Shift Invalidation
* **Conditional Validity of Split Conformal Recall Sets:**
  Standard split conformal guarantees rely on exchangeability (i.i.d. assumption). In an adaptive, nonstationary cognitive runtime:
  $$\text{Guarantee: } \ge 90\% \text{ marginal coverage under the preregistered exchangeability conditions.}$$
* **Constitutional Invalidation Detection:**
  The system continuously monitors covariate and label distribution shift. When distribution shift is detected (or calibration sample size $N < 10$), WhiteMagic **explicitly withdraws its epistemic coverage claim** (`status = uncalibrated_shift`), alerting downstream evaluators that its warrant for knowing has expired.
* **Stochastic Simulation & Tail Risks:** SDE solvers (GBM / OU with MLMC variance reduction), Polynomial Chaos Expansion (Hermite polynomials / Sobol' indices), and Subset Simulation estimating tail risk probabilities $p < 10^{-4}$.
* **Claims Ledger:** Falsifiable predictions scored by verified lead time ($1\text{ pt/week}$), reporting both validated and falsified counts.

---

## 6. The Phenotype Emergence Battery (PEB)

To ensure zero unearned code and verify that phenotypes emerge from Level 1 physics, the runtime must satisfy a 15-suite automated test battery before higher-level capabilities are ratified:

> **Empirical Receipt Interpretation Invariant:** Wherever the battery specifies metrics such as "zero deadlock", "zero livelock", or "zero oscillatory thrashing", the resulting receipt is strictly interpreted as: **0 observed failures across $N$ preregistered adversarial trials**, rather than an ungrounded universal claim of impossibility. All measurements report explicit sample counts, confidence intervals, and random seeds.

| Test ID | Suite Name | Invariant / Phenomenon Verified | Success Criteria |
|---|---|---|---|
| **PEB-0** | **Primitive Minimality** | Reduction / ablation of the candidate 4-beat pulse | Subjected to Ablation, Merger, and Substitution attacks. Discovers whether a simpler algebra (3 beats, 2 beats, or an asymmetric 3+1 structure) preserves all observable behaviors and constitutional invariants. |
| **PEB-1** | **The Four Corners Challenge** | Contextualized Catuṣkoṭi $\mathbf{E}(A \mid \Gamma)$ & Frame Rejection | Resolves $K_1 \dots K_4$ correctly; outputs $F \approx 0$ on category errors without binary hallucination. |
| **PEB-2** | **Attractor Basin Emergence** | Two-arm emergence: Seeded Continuity vs. De-Novo ($\lambda = 0$) | De-novo arm discovers stable metastable basins under $\mathbf{L}_{\text{signed}}$ without garden priors; basin count is an unconstrained empirical outcome. |
| **PEB-3** | **Cognitive Role Drift** | Empirical co-usage clustering without hardcoded 28 partition | Co-usage matrix $\mathbf{C}_{ij}$ clusters naturally and emits valid merge proposals under workload skew. |
| **PEB-4** | **Continuous Dream Transition** | Regime Vector $\mathbf{R}(t)$ modulates search breadth & compression | $r_{\text{assoc}}$ expands by $\ge 2\times$ during idle; $B_{\text{write}} \le 0.25$; zero runaway loops on empty sets. |
| **PEB-5** | **Homeostatic Constraint Arbitration** | Latency SLA vs. Conformal Coverage conflict resolution | Refuses silent coverage violation; explicitly declares conflict and triggers graceful degradation. |
| **PEB-6** | **Causal Cladistics & Pareto Gating** | Non-regressive mutation admission across $M_{\text{protected}}$ | Rejects candidates regressing protected metrics even if scalar fitness $> 0$; tracks hypergraph lineage. |
| **PEB-7** | **Spectroscopy Fidelity & Multi-Baseline Benchmark** | 22 Suarès motifs evaluated against Random, PCA, ICA, and Raw | Evaluated on state prediction, anomaly discrimination, compression, phenotype discrimination, transfer, and redundancy; zero dispatch dependencies. |
| **PEB-8** | **Reversible Quarantine & Autoimmunity** | Corrupted inputs isolated without data loss or panic | Malformed payload routed to `quarantine_index`; main loop executes with zero memory corruption. |
| **PEB-9** | **Speculative Consensus & Spotlight** | Margin fast-path and time-decayed spotlight arbitration | Fast draft accepted when margin $\ge 0.85$; spotlight decays by $0.5^{\Delta t / 5.0}$; preemption at $>0.8$. |
| **PEB-10** | **Sovereign Mesh & Gan Ying Boundary** | TCP framing, TOFU binding, and containment isolation | Rejects spoofed keys; enforces default-deny local grants; auto-quarantines on 3 verification fails. |
| **PEB-11** | **Declarative Dependency Compilation** | Dependency graph compiles down to execution substrate | Executes composed transforms via $[\text{Select} \to \text{Transform} \to \text{Evaluate} \to \text{Commit}]^n$ with zero DAG engine. |
| **PEB-12** | **Conformal Recall & Shift Invalidation** | Conditional marginal coverage and distribution-shift invalidation | Guarantees $90\%$ coverage under exchangeability; detects distribution shift and explicitly withdraws coverage claim when invalid. |
| **PEB-13** | **Phenotype Interference & Dynamic Stability** | Full-system coupling under adversarial multi-stress | Dreaming + Homeostasis + Conformal Recall + Quarantine + Attention run concurrently with zero deadlock, zero livelock, zero oscillatory thrashing, and zero mutual starvation. |
| **PEB-14** | **De-Novo Emergence & Holdout Benchmark** | Unseen problem family with zero domain-specific priors/templates | Demonstrates emergent organization satisfying stability + reproducibility + functional utility + predictive value + compression on unseen holdout tasks. |

---

## 7. Implementation Roadmap & Execution Gates

```
┌─────────────────────────────────────────────────────────────────────────┐
│ MILESTONE 0: Primitive Minimality & Epistemic Substrate                 │
│   • Validate PEB-0 (Primitive Minimality: Ablation / Merger / Sub)      │
│   • Implement Contextualized Catuṣkoṭi <E+, E-, F, Γ> in Core           │
│   • Validate PEB-1 (The Four Corners Challenge)                         │
├─────────────────────────────────────────────────────────────────────────┤
│ MILESTONE 1: Cognitive Regime & Continuous Dreaming                     │
│   • Implement Regime Vector R(t) and I/O Quiescence throttling          │
│   • Validate PEB-4 (Continuous Dream Transition)                        │
├─────────────────────────────────────────────────────────────────────────┤
│ MILESTONE 2: Homeostatic Arbitration & Reversible Quarantine            │
│   • Implement multi-actuator telemetry and SLA vs. Coverage arbiter     │
│   • Validate PEB-5 (Homeostatic Arbitration) & PEB-8 (Quarantine)       │
├─────────────────────────────────────────────────────────────────────────┤
│ MILESTONE 3: Causal Cladistics & Pareto Gated Shadow Clones             │
│   • Implement directed hyper-relations and Pareto admission filter      │
│   • Validate PEB-6 (Causal Cladistics & Pareto Gating)                  │
├─────────────────────────────────────────────────────────────────────────┤
│ MILESTONE 4: Spectroscopy Fidelity & Attractor Emergence                │
│   • Implement 22-motif spectrometer, multi-baseline benchmark, and L_s  │
│   • Validate PEB-7 (Spectroscopy Fidelity) & PEB-2/3 (Two-Arm Emergence)│
├─────────────────────────────────────────────────────────────────────────┤
│ MILESTONE 5: Attention Spotlight & Declarative Pulse Compilation        │
│   • Implement margin fast-path, spotlight decay, and graph compiler    │
│   • Validate PEB-9 (Attention/Speculation) & PEB-11 (Pulse Compilation) │
├─────────────────────────────────────────────────────────────────────────┤
│ MILESTONE 6: Sovereign Mesh & Conformal Invalidation Bounds             │
│   • Implement governed communicate verb, split-conformal recall & shift │
│   • Validate PEB-10 (Sovereign Mesh) & PEB-12 (Shift Invalidation)      │
├─────────────────────────────────────────────────────────────────────────┤
│ MILESTONE 7: Compositional Interference & De-Novo Holdout               │
│   • Validate PEB-13 (Phenotype Multi-Stress Interference / Thrashing)   │
│   • Validate PEB-14 (De-Novo Emergence on Unseen Holdout Workloads)     │
└─────────────────────────────────────────────────────────────────────────┘
```

Every milestone is gated by execution receipts adhering to the `docs/BENCHMARK_AND_VERIFICATION_PROTOCOL.md` standard. No capability is deemed complete until its corresponding PEB test suite passes with zero unearned assumptions.
